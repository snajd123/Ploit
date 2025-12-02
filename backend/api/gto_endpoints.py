"""
API endpoints for GTO analysis (GTOWizard-based).

Provides RESTful access to GTO frequencies and scenario data.

Note: Player-specific GTO analysis is handled by /api/players/{name}/gto-analysis
in main.py, which calculates on-the-fly from player_hand_summary.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.services.gto_service import GTOService
from backend.database import get_db

router = APIRouter(prefix="/api/gto", tags=["GTO Analysis"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class GTOFrequencyResponse(BaseModel):
    """GTO frequency response"""
    scenario: str
    hand: str
    position: str
    frequency: float
    percentage: float

    class Config:
        from_attributes = True


class ActionBreakdownResponse(BaseModel):
    """Action breakdown response"""
    position: str
    opponent: Optional[str]
    hand: str
    actions: Dict[str, float]

    class Config:
        from_attributes = True


class OpeningRangeResponse(BaseModel):
    """Opening range response"""
    position: str
    hands: Dict[str, float]
    total_hands: int
    vpip_percentage: float

    class Config:
        from_attributes = True


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_gto_service(db: Session = Depends(get_db)) -> GTOService:
    """Get GTO service instance"""
    return GTOService(db)


# ============================================================================
# GTO QUERY ENDPOINTS
# ============================================================================

@router.get("/frequency", response_model=GTOFrequencyResponse)
async def get_gto_frequency(
    scenario: str = Query(..., description="Scenario name (e.g., 'BB_vs_UTG_call')"),
    hand: str = Query(..., description="Hand type (e.g., 'AKo', 'JTs', '22')"),
    position: Optional[str] = Query(None, description="Position filter"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get GTO frequency for a specific hand in a scenario.

    Example: GET /api/gto/frequency?scenario=BB_vs_UTG_call&hand=AKo

    Returns the GTO frequency (0.0 to 1.0) for how often to take this action.
    """
    frequency = gto_service.get_gto_frequency(scenario, hand, position)

    if frequency is None:
        raise HTTPException(
            status_code=404,
            detail=f"No GTO data found for {hand} in scenario {scenario}"
        )

    return GTOFrequencyResponse(
        scenario=scenario,
        hand=hand,
        position=position or scenario.split('_')[0],
        frequency=frequency,
        percentage=frequency * 100
    )


@router.get("/breakdown", response_model=ActionBreakdownResponse)
async def get_action_breakdown(
    position: str = Query(..., description="Position (e.g., 'BB', 'UTG')"),
    opponent: Optional[str] = Query(None, description="Opponent position (None for opens)"),
    hand: str = Query(..., description="Hand type (e.g., 'AKo')"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get all action frequencies for a hand in a situation.

    Example: GET /api/gto/breakdown?position=BB&opponent=UTG&hand=AKo

    Returns all possible actions (fold/call/3bet) with their GTO frequencies.
    """
    actions = gto_service.get_action_breakdown(position, opponent, hand)

    if not actions:
        raise HTTPException(
            status_code=404,
            detail=f"No GTO data found for {hand} in {position} vs {opponent}"
        )

    return ActionBreakdownResponse(
        position=position,
        opponent=opponent,
        hand=hand,
        actions=actions
    )


@router.get("/range/{position}", response_model=OpeningRangeResponse)
async def get_opening_range(
    position: str,
    min_frequency: float = Query(0.0, ge=0.0, le=1.0, description="Minimum frequency filter"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get full opening range for a position.

    Example: GET /api/gto/range/UTG?min_frequency=0.5

    Returns all hands opened with frequency >= min_frequency.
    """
    hands = gto_service.get_opening_range(position, min_frequency)

    if not hands:
        raise HTTPException(
            status_code=404,
            detail=f"No opening range found for position {position}"
        )

    vpip = sum(hands.values())

    return OpeningRangeResponse(
        position=position,
        hands=hands,
        total_hands=len(hands),
        vpip_percentage=vpip * 100
    )


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/scenarios")
async def list_scenarios(
    street: Optional[str] = Query(None, description="Filter by street"),
    category: Optional[str] = Query(None, description="Filter by category"),
    position: Optional[str] = Query(None, description="Filter by position"),
    limit: int = Query(500, ge=1, le=1000),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    List available GTO scenarios.

    Example: GET /api/gto/scenarios?street=preflop&category=defense

    Returns list of scenarios with metadata.
    """
    from backend.models.gto_models import GTOScenario

    query = gto_service.db.query(GTOScenario)

    if street:
        query = query.filter(GTOScenario.street == street)
    if category:
        query = query.filter(GTOScenario.category == category)
    if position:
        query = query.filter(GTOScenario.position == position)

    scenarios = query.limit(limit).all()

    return [s.to_dict() for s in scenarios]


@router.get("/range-matrix")
async def get_scenario_range_matrix(
    category: str = Query(..., description="Category: opening, defense, facing_3bet, facing_4bet"),
    position: str = Query(..., description="Player position: UTG, MP, CO, BTN, SB, BB"),
    opponent_position: Optional[str] = Query(None, description="Opponent position for defense scenarios"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get complete GTO action matrix for all 169 hands in a scenario.

    Returns a matrix suitable for the RangeGrid component with actions
    for each hand combo (e.g., AKo, JTs, 22).

    Example: GET /api/gto/range-matrix?category=defense&position=BB&opponent_position=BTN

    Returns:
        {
            "AKo": {"fold": 0.0, "call": 0.35, "3bet": 0.65},
            "AKs": {"fold": 0.0, "call": 0.15, "3bet": 0.85},
            ...
        }
    """
    from backend.models.gto_models import GTOScenario, GTOFrequency
    from sqlalchemy import text
    import re

    try:
        # Get all scenarios for this category/position/opponent combo
        query = gto_service.db.query(GTOScenario).filter(
            GTOScenario.category == category,
            GTOScenario.position == position.upper()
        )

        if opponent_position:
            query = query.filter(GTOScenario.opponent_position == opponent_position.upper())
        elif category == 'opening':
            # Opening scenarios have no opponent - filter for NULL
            query = query.filter(GTOScenario.opponent_position.is_(None))
        # For defense/facing_3bet/facing_4bet without specific opponent:
        # Don't filter by opponent - aggregate all opponent positions

        scenarios = query.all()

        if not scenarios:
            # Return empty matrix if no scenarios found
            return {}

        # Build action matrix - track all frequencies for proper averaging
        # Structure: {hand_combo: {action: [list of frequencies]}}
        action_freq_lists: Dict[str, Dict[str, List[float]]] = {}

        # Helper to normalize card combo to standard format (e.g., "Ah Kd" -> "AKo")
        def normalize_hand(hand: str) -> str:
            # Handle format like "AhKd" or "Ah Kd"
            hand = hand.replace(' ', '')
            if len(hand) < 4:
                return hand

            rank1, suit1 = hand[0].upper(), hand[1].lower()
            rank2, suit2 = hand[2].upper(), hand[3].lower()

            # Rank ordering for comparison
            rank_order = "23456789TJQKA"

            # Pairs
            if rank1 == rank2:
                return f"{rank1}{rank2}"

            # Ensure higher rank comes first
            if rank_order.index(rank1) < rank_order.index(rank2):
                rank1, rank2 = rank2, rank1
                suit1, suit2 = suit2, suit1

            # Suited or offsuit
            if suit1 == suit2:
                return f"{rank1}{rank2}s"
            else:
                return f"{rank1}{rank2}o"

        # Process each scenario (fold, call, 3bet, etc.)
        for scenario in scenarios:
            action = scenario.action
            if not action:
                continue

            # Get all frequencies for this scenario
            frequencies = gto_service.db.query(GTOFrequency).filter(
                GTOFrequency.scenario_id == scenario.scenario_id
            ).all()

            # Collect frequencies by normalized hand combo
            for freq in frequencies:
                try:
                    normalized = normalize_hand(freq.hand)
                    if normalized not in action_freq_lists:
                        action_freq_lists[normalized] = {}
                    if action not in action_freq_lists[normalized]:
                        action_freq_lists[normalized][action] = []
                    action_freq_lists[normalized][action].append(float(freq.frequency))
                except (ValueError, IndexError):
                    continue

        # Average the frequencies for each hand combo and action
        action_matrix: Dict[str, Dict[str, float]] = {}
        for hand_combo, actions in action_freq_lists.items():
            action_matrix[hand_combo] = {}
            for action, freqs in actions.items():
                action_matrix[hand_combo][action] = sum(freqs) / len(freqs) if freqs else 0

        # Normalize frequencies to ensure they sum to ~1.0 for each hand
        for hand_combo, actions in action_matrix.items():
            total = sum(actions.values())
            if total > 0 and total != 1.0:
                # Normalize
                for action in actions:
                    actions[action] = actions[action] / total

        return action_matrix

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving range matrix: {str(e)}"
        )


@router.get("/health")
async def health_check(gto_service: GTOService = Depends(get_gto_service)):
    """
    Health check for GTO service.

    Returns:
    - Database connectivity
    - Number of scenarios loaded
    - System status
    """
    from backend.models.gto_models import GTOScenario, GTOFrequency

    try:
        scenario_count = gto_service.db.query(GTOScenario).count()
        frequency_count = gto_service.db.query(GTOFrequency).count()

        return {
            "status": "healthy",
            "database": "connected",
            "scenarios_loaded": scenario_count,
            "frequencies_loaded": frequency_count,
            "service": "operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# ============================================================================
# OPTIMAL RANGES ENDPOINT
# ============================================================================

class OptimalRangeItem(BaseModel):
    """Single optimal range for a stat"""
    stat_key: str
    optimal_low: float
    optimal_high: float
    gto_value: Optional[float] = None
    source: str = "gto_database"
    description: Optional[str] = None


class PositionalOptimalRange(BaseModel):
    """Optimal range for a specific position"""
    position: str
    vpip_pct: float
    three_bet_pct: Optional[float] = None
    fold_to_3bet_pct: Optional[float] = None


class OptimalRangesResponse(BaseModel):
    """All optimal ranges from GTO database"""
    overall: Dict[str, OptimalRangeItem]
    positional: List[PositionalOptimalRange]
    scenarios_count: int
    frequencies_count: int
    last_updated: Optional[str] = None


@router.get("/optimal-ranges", response_model=OptimalRangesResponse)
async def get_optimal_ranges(
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get optimal stat ranges for player statistics.

    Returns:
    - Overall optimal ranges for player stats (VPIP, PFR, 3-bet%, etc.)
    - Position-specific RFI (raise first in) frequencies from GTO

    Example: GET /api/gto/optimal-ranges
    """
    from backend.models.gto_models import GTOScenario, GTOFrequency

    try:
        overall = {
            'vpip_pct': OptimalRangeItem(
                stat_key='vpip_pct',
                optimal_low=18,
                optimal_high=25,
                gto_value=22,
                source='poker_theory',
                description='Voluntarily put money in pot - overall player tendency'
            ),
            'pfr_pct': OptimalRangeItem(
                stat_key='pfr_pct',
                optimal_low=13,
                optimal_high=20,
                gto_value=17,
                source='poker_theory',
                description='Pre-flop raise percentage - overall player tendency'
            ),
            'three_bet_pct': OptimalRangeItem(
                stat_key='three_bet_pct',
                optimal_low=6,
                optimal_high=12,
                gto_value=8,
                source='poker_theory',
                description='3-bet percentage when facing a raise'
            ),
            'fold_to_three_bet_pct': OptimalRangeItem(
                stat_key='fold_to_three_bet_pct',
                optimal_low=50,
                optimal_high=60,
                gto_value=55,
                source='poker_theory',
                description='Fold to 3-bet after opening'
            ),
            'vpip_btn': OptimalRangeItem(
                stat_key='vpip_btn',
                optimal_low=43,
                optimal_high=51,
                gto_value=47,
                source='poker_theory',
                description='VPIP from button position'
            )
        }

        opening_scenarios = gto_service.db.query(GTOScenario).filter(
            GTOScenario.category == 'opening'
        ).all()

        # Aggregate by position (SB has separate raise/limp scenarios)
        position_freqs: Dict[str, float] = {}
        for scenario in opening_scenarios:
            pos = scenario.position
            rfi_freq = float(scenario.gto_aggregate_freq) * 100 if scenario.gto_aggregate_freq else 0
            position_freqs[pos] = position_freqs.get(pos, 0) + rfi_freq

        positional_data = []
        for pos, freq in position_freqs.items():
            positional_data.append(PositionalOptimalRange(
                position=pos,
                vpip_pct=round(freq, 1),
            ))

        position_order = {'UTG': 1, 'MP': 2, 'CO': 3, 'BTN': 4, 'SB': 5, 'BB': 6}
        positional_data.sort(key=lambda x: position_order.get(x.position, 99))

        scenario_count = gto_service.db.query(GTOScenario).count()
        freq_count = gto_service.db.query(GTOFrequency).count()

        return OptimalRangesResponse(
            overall=overall,
            positional=positional_data,
            scenarios_count=scenario_count,
            frequencies_count=freq_count,
            last_updated=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate optimal ranges: {str(e)}"
        )
