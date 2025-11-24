"""
GTO Browser API endpoints for interactive scenario building and range visualization.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from ..database import get_db
from ..models.gto_models import GTOScenario, PlayerGTOStat, GTOFrequency

router = APIRouter(prefix="/api/gto", tags=["gto_browser"])


class ActionStep(BaseModel):
    """Single action in the sequence"""
    position: str  # UTG, MP, CO, BTN, SB, BB
    action: str    # fold, raise, call, 3bet, 4bet, allin
    size_bb: Optional[float] = None  # Bet size in big blinds


class MatchScenarioRequest(BaseModel):
    """Request to match a scenario"""
    table_size: str = "6max"  # Currently only 6max
    actions: List[ActionStep]
    hero_position: str
    hero_action: str


class GTOAction(BaseModel):
    """GTO action with frequency and range"""
    action: str
    frequency: float
    range_string: Optional[str] = None
    range_matrix: Optional[Dict[str, float]] = None
    combos: Optional[int] = None


class MatchScenarioResponse(BaseModel):
    """Response with matched GTO solution"""
    found: bool
    scenario_id: Optional[int] = None
    scenario_name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    gto_actions: Optional[List[GTOAction]] = None
    message: Optional[str] = None
    searched_for: Optional[Dict[str, Any]] = None


def parse_range_to_matrix(range_string: str) -> Dict[str, float]:
    """
    Parse poker range string to hand matrix.
    Returns dict mapping hand notation to frequency (0.0-1.0).

    Example: "AA,KK,AKs" -> {"AA": 1.0, "KK": 1.0, "AKs": 1.0, ...}
    """
    if not range_string:
        return {}

    matrix = {}

    # Initialize all hands to 0
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

    # Parse range string
    # For now, return empty dict - will implement full parser
    # This would need to handle: "22+", "A2s+", "KTo+", etc.

    return matrix


def get_range_from_frequencies(db: Session, scenario_id: int) -> Dict[str, float]:
    """
    Fetch hand frequencies from gto_frequencies table and build range matrix.
    Returns dict mapping hand notation (e.g., 'AKo', 'JTs', '22') to frequency (0.0-1.0).
    """
    frequencies = db.query(GTOFrequency).filter(
        GTOFrequency.scenario_id == scenario_id
    ).all()

    if not frequencies:
        return {}

    # Build range matrix from frequency data
    range_matrix = {}
    for freq in frequencies:
        # Convert Decimal to float for JSON serialization
        range_matrix[freq.hand] = float(freq.frequency)

    return range_matrix


def calculate_combos_from_matrix(range_matrix: Dict[str, float]) -> int:
    """
    Calculate total combos from a range matrix.
    Pairs have 6 combos, unsuited hands have 12 combos, suited hands have 4 combos.
    """
    if not range_matrix:
        return 0

    total_combos = 0
    for hand, frequency in range_matrix.items():
        if len(hand) == 2:  # Pairs like "AA"
            total_combos += 6 * frequency
        elif hand.endswith('s'):  # Suited like "AKs"
            total_combos += 4 * frequency
        elif hand.endswith('o'):  # Offsuit like "AKo"
            total_combos += 12 * frequency
        else:  # Generic notation without s/o (treat as all combos)
            total_combos += 4 * frequency

    return int(round(total_combos))


def determine_scenario_type(actions: List[ActionStep], hero_position: str, hero_action: str) -> Dict[str, Any]:
    """
    Determine what type of scenario this is based on action sequence.
    Returns dict with category, scenario_name, and search criteria.
    """

    # Find the opener (first raise/open action)
    opener = None
    for action in actions:
        if action.action in ["raise", "open"] and action.position != hero_position:
            opener = action.position
            break

    # Find the 3-bettor (first 3bet action)
    three_bettor = None
    for action in actions:
        if action.action == "3bet" and action.position != hero_position:
            three_bettor = action.position
            break

    # Find the 4-bettor (first 4bet action)
    four_bettor = None
    for action in actions:
        if action.action == "4bet" and action.position != hero_position:
            four_bettor = action.position
            break

    # Find callers between opener and hero (for multiway scenarios)
    callers = []
    if opener:
        found_opener = False
        for action in actions:
            if action.position == opener and action.action in ["raise", "open"]:
                found_opener = True
            elif found_opener and action.position == hero_position:
                break
            elif found_opener and action.action == "call":
                callers.append(action.position)

    # Determine category and scenario name
    if hero_action in ["raise", "open"] and not opener:
        # Hero is opening (e.g., UTG_open)
        category = "opening"
        scenario_name = f"{hero_position}_open"

    elif hero_action in ["5bet", "allin"] and four_bettor:
        # Hero is facing a 4-bet (e.g., BB_vs_BTN_4bet_5bet, BB_vs_BTN_4bet_allin)
        category = "facing_4bet"
        scenario_name = f"{hero_position}_vs_{four_bettor}_4bet_{hero_action}"

    elif hero_action in ["fold", "call"] and four_bettor:
        # Hero is facing a 4-bet (e.g., BB_vs_BTN_4bet_fold, BB_vs_BTN_4bet_call)
        category = "facing_4bet"
        scenario_name = f"{hero_position}_vs_{four_bettor}_4bet_{hero_action}"

    elif hero_action in ["fold", "call", "4bet", "allin"] and three_bettor:
        # Hero is facing a 3-bet (e.g., BTN_vs_SB_3bet_fold, BTN_vs_SB_3bet_4bet)
        category = "facing_3bet"
        scenario_name = f"{hero_position}_vs_{three_bettor}_3bet_{hero_action}"

    elif hero_action == "3bet" and opener and callers:
        # Hero is 3-betting in a multiway pot (e.g., BB_vs_UTG_BTN_3bet)
        callers_str = "_".join(callers)
        category = "facing_3bet"
        scenario_name = f"{hero_position}_vs_{opener}_{callers_str}_3bet"

    elif hero_action == "3bet" and opener and not three_bettor:
        # Hero is 3-betting heads-up (e.g., BB_vs_UTG_3bet)
        category = "facing_3bet"
        scenario_name = f"{hero_position}_vs_{opener}_3bet"

    elif hero_action in ["fold", "call"] and opener and callers:
        # Hero is defending in a multiway pot (e.g., BB_vs_UTG_BTN_call)
        callers_str = "_".join(callers)
        category = "multiway"
        scenario_name = f"{hero_position}_vs_{opener}_{callers_str}_{hero_action}"

    elif hero_action in ["fold", "call"] and opener and not three_bettor:
        # Hero is defending heads-up (e.g., BB_vs_UTG_fold, BB_vs_UTG_call)
        category = "defense"
        scenario_name = f"{hero_position}_vs_{opener}_{hero_action}"

    else:
        return {
            "category": None,
            "scenario_name": None,
            "found": False,
            "message": "Could not determine scenario type from action sequence"
        }

    return {
        "category": category,
        "scenario_name": scenario_name,
        "position": hero_position,
        "action": hero_action
    }


@router.post("/match-scenario", response_model=MatchScenarioResponse)
def match_scenario(request: MatchScenarioRequest, db: Session = Depends(get_db)):
    """
    Match user's action sequence to a GTO scenario in the database.
    Returns GTO solution if found, or "not found" message.
    """

    # Determine what scenario we're looking for
    scenario_info = determine_scenario_type(
        request.actions,
        request.hero_position,
        request.hero_action
    )

    if not scenario_info.get("category"):
        return MatchScenarioResponse(
            found=False,
            message="Could not determine scenario type",
            searched_for=scenario_info
        )

    # Query database for matching scenario
    scenario = db.query(GTOScenario).filter(
        and_(
            GTOScenario.category == scenario_info["category"],
            GTOScenario.scenario_name == scenario_info["scenario_name"]
        )
    ).first()

    if not scenario:
        return MatchScenarioResponse(
            found=False,
            message=f"No GTO scenario found in database",
            searched_for={
                "category": scenario_info["category"],
                "scenario_name": scenario_info["scenario_name"],
                "position": request.hero_position,
                "action_sequence": [f"{a.position}: {a.action}" for a in request.actions]
            }
        )

    # Get all possible actions for this scenario
    # Group by action type to get all variations (fold/call/3bet/etc)
    related_scenarios = db.query(GTOScenario).filter(
        and_(
            GTOScenario.category == scenario.category,
            GTOScenario.position == scenario.position,
            GTOScenario.scenario_name.like(f"{scenario.scenario_name.split('_')[0]}_%")
        )
    ).all()

    # Get GTO stats for these scenarios
    gto_actions = []
    for scen in related_scenarios:
        stats = db.query(PlayerGTOStat).filter(
            PlayerGTOStat.scenario_id == scen.scenario_id
        ).first()

        if stats:
            action_name = scen.action or scen.scenario_name.split('_')[-1]

            # Fetch range data from gto_frequencies table
            range_matrix = get_range_from_frequencies(db, scen.scenario_id)
            combos = calculate_combos_from_matrix(range_matrix) if range_matrix else None

            gto_actions.append(GTOAction(
                action=action_name,
                frequency=float(stats.gto_frequency * 100) if stats.gto_frequency else 0.0,
                range_string=None,
                range_matrix=range_matrix if range_matrix else None,
                combos=combos
            ))

    # If we only found one scenario (the matched one), get its stats
    if not gto_actions:
        stats = db.query(PlayerGTOStat).filter(
            PlayerGTOStat.scenario_id == scenario.scenario_id
        ).first()

        if stats:
            # Fetch range data from gto_frequencies table
            range_matrix = get_range_from_frequencies(db, scenario.scenario_id)
            combos = calculate_combos_from_matrix(range_matrix) if range_matrix else None

            gto_actions.append(GTOAction(
                action=scenario.action or request.hero_action,
                frequency=float(stats.gto_frequency * 100) if stats.gto_frequency else 0.0,
                range_string=None,
                range_matrix=range_matrix if range_matrix else None,
                combos=combos
            ))

    return MatchScenarioResponse(
        found=True,
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.scenario_name,
        category=scenario.category,
        description=scenario.description,
        gto_actions=gto_actions
    )


@router.get("/scenarios", response_model=List[Dict[str, Any]])
def list_scenarios(
    category: Optional[str] = None,
    position: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all GTO scenarios with optional filtering.
    Useful for browsing available scenarios.
    """
    query = db.query(GTOScenario)

    if category:
        query = query.filter(GTOScenario.category == category)
    if position:
        query = query.filter(GTOScenario.position == position)

    scenarios = query.all()

    return [
        {
            "scenario_id": s.scenario_id,
            "scenario_name": s.scenario_name,
            "category": s.category,
            "position": s.position,
            "action": s.action,
            "opponent_position": s.opponent_position,
            "description": s.description
        }
        for s in scenarios
    ]


@router.get("/scenario/{scenario_id}")
def get_scenario_details(scenario_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific scenario including GTO actions and ranges.
    """
    scenario = db.query(GTOScenario).filter(GTOScenario.scenario_id == scenario_id).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Get GTO stats for this scenario
    stats = db.query(PlayerGTOStat).filter(
        PlayerGTOStat.scenario_id == scenario_id
    ).first()

    # Get range data
    range_matrix = get_range_from_frequencies(db, scenario_id)
    combos = calculate_combos_from_matrix(range_matrix) if range_matrix else None

    # Build GTO action
    gto_action = None
    if stats:
        gto_action = {
            "action": scenario.action or "unknown",
            "frequency": float(stats.gto_frequency * 100) if stats.gto_frequency else 0.0,
            "range_matrix": range_matrix if range_matrix else None,
            "combos": combos
        }

    return {
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "category": scenario.category,
        "position": scenario.position,
        "action": scenario.action,
        "opponent_position": scenario.opponent_position,
        "description": scenario.description,
        "gto_action": gto_action
    }
