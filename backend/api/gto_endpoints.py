"""
API endpoints for GTO analysis (GTOWizard-based).

Provides RESTful access to GTO frequencies, leak detection, and exploit finding.
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


class RecordActionRequest(BaseModel):
    """Request to record a player action"""
    player_name: str = Field(..., description="Player name")
    hand_id: str = Field(..., description="Unique hand identifier")
    scenario_name: str = Field(..., description="Scenario name (e.g., 'BB_vs_UTG_call')")
    hole_cards: str = Field(..., description="Hand type (e.g., 'AKo', 'JTs')")
    action_taken: str = Field(..., description="Action taken (e.g., 'fold', 'call', '3bet')")
    timestamp: Optional[datetime] = Field(None, description="When action occurred")


class PlayerActionResponse(BaseModel):
    """Response after recording action"""
    action_id: int
    player_name: str
    hole_cards: str
    action_taken: str
    gto_frequency: Optional[float]
    ev_loss_bb: Optional[float]
    is_mistake: bool
    mistake_severity: str

    class Config:
        from_attributes = True


class LeakResponse(BaseModel):
    """Player leak response"""
    scenario_name: str
    category: str
    position: str
    action: str
    total_hands: int
    player_frequency: Optional[float]
    gto_frequency: Optional[float]
    frequency_diff: Optional[float]
    total_ev_loss_bb: Optional[float]
    avg_ev_loss_bb: Optional[float]
    leak_type: Optional[str]
    leak_severity: Optional[str]
    exploit_description: Optional[str]
    exploit_value_bb_100: Optional[float]
    exploit_confidence: Optional[float]


class ExploitResponse(BaseModel):
    """Exploit recommendation response"""
    scenario: str
    leak_type: str
    frequency_diff: Optional[float]
    exploit: str
    value_bb_100: Optional[float]
    confidence: float
    sample_size: int


class GTOAdherenceResponse(BaseModel):
    """GTO adherence response"""
    player: str
    street: str
    total_hands: int
    gto_adherence_score: float
    avg_ev_loss_per_hand: float
    total_ev_loss_bb: float
    major_leaks_count: int
    scenarios_analyzed: int


class CounterStrategyResponse(BaseModel):
    """Counter-strategy response"""
    position: str
    vs_player: str
    adjustments: List[Dict[str, Any]]
    expected_value_bb_100: float


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
        position=position or scenario.split('_')[0],  # Extract from scenario name
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

    # Calculate VPIP (sum of all frequencies)
    vpip = sum(hands.values())

    return OpeningRangeResponse(
        position=position,
        hands=hands,
        total_hands=len(hands),
        vpip_percentage=vpip * 100
    )


# ============================================================================
# LEAK DETECTION ENDPOINTS
# ============================================================================

@router.post("/action", response_model=PlayerActionResponse)
async def record_player_action(
    request: RecordActionRequest,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Record a player action and analyze against GTO.

    Example:
    ```json
    POST /api/gto/action
    {
        "player_name": "Villain1",
        "hand_id": "PS123456",
        "scenario_name": "BB_vs_UTG_call",
        "hole_cards": "AKo",
        "action_taken": "fold"
    }
    ```

    Automatically:
    - Looks up GTO frequency
    - Calculates EV loss
    - Flags mistakes
    - Updates player_gto_stats
    """
    try:
        action = gto_service.record_player_action(
            player_name=request.player_name,
            hand_id=request.hand_id,
            scenario_name=request.scenario_name,
            hole_cards=request.hole_cards,
            action_taken=request.action_taken,
            timestamp=request.timestamp
        )

        return PlayerActionResponse(
            action_id=action.action_id,
            player_name=action.player_name,
            hole_cards=action.hole_cards,
            action_taken=action.action_taken,
            gto_frequency=float(action.gto_frequency) if action.gto_frequency else None,
            ev_loss_bb=float(action.ev_loss_bb) if action.ev_loss_bb else None,
            is_mistake=action.is_mistake or False,
            mistake_severity=action.mistake_severity or 'minor'
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record action: {str(e)}")


@router.get("/leaks/{player}", response_model=List[LeakResponse])
async def get_player_leaks(
    player: str,
    min_hands: int = Query(20, ge=1, description="Minimum sample size"),
    sort_by: str = Query('ev_loss', regex='^(ev_loss|frequency_diff|severity)$'),
    street: str = Query('preflop', description="Street filter"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get all leaks for a player, sorted by severity.

    Example: GET /api/gto/leaks/Villain1?min_hands=20&sort_by=ev_loss

    Returns list of leaks with:
    - Scenario details
    - Frequency deviations
    - EV loss
    - Exploit recommendations
    """
    leaks = gto_service.get_player_leaks(
        player_name=player,
        min_hands=min_hands,
        sort_by=sort_by,
        street=street
    )

    return [LeakResponse(**leak) for leak in leaks]


@router.get("/leaks/{player}/biggest", response_model=Optional[LeakResponse])
async def get_biggest_leak(
    player: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get player's single biggest leak by EV loss.

    Example: GET /api/gto/leaks/Villain1/biggest

    Returns the most costly leak for quick analysis.
    """
    leak = gto_service.get_biggest_leak(player)

    if not leak:
        raise HTTPException(
            status_code=404,
            detail=f"No leaks found for player {player} (insufficient data)"
        )

    return LeakResponse(**leak)


@router.get("/adherence/{player}", response_model=GTOAdherenceResponse)
async def get_gto_adherence(
    player: str,
    street: str = Query('preflop', description="Street filter"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Calculate how closely player follows GTO.

    Example: GET /api/gto/adherence/Hero?street=preflop

    Returns:
    - GTO adherence score (0-100)
    - Average EV loss per hand
    - Total EV loss
    - Count of major leaks
    """
    adherence = gto_service.get_player_gto_adherence(
        player_name=player,
        street=street
    )

    if adherence.get('total_hands', 0) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No data available for player {player}"
        )

    return GTOAdherenceResponse(**adherence)


# ============================================================================
# EXPLOIT FINDING ENDPOINTS
# ============================================================================

@router.get("/exploits/{player}", response_model=List[ExploitResponse])
async def get_exploits(
    player: str,
    min_confidence: float = Query(70.0, ge=0.0, le=100.0, description="Minimum confidence %"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Calculate exploitable patterns in player's game.

    Example: GET /api/gto/exploits/Villain1?min_confidence=70

    Returns list of exploits with:
    - Leak type
    - Exploit recommendation
    - Expected value (BB/100)
    - Confidence level
    """
    exploits = gto_service.calculate_exploits(
        player_name=player,
        min_confidence=min_confidence
    )

    return [ExploitResponse(**exploit) for exploit in exploits]


@router.get("/counter/{player}/{position}", response_model=CounterStrategyResponse)
async def get_counter_strategy(
    player: str,
    position: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Generate counter-strategy for a player in a position.

    Example: GET /api/gto/counter/Villain1/UTG

    Returns specific adjustments to make when playing from this position
    against the villain, including:
    - Which scenarios to exploit
    - Frequency adjustments
    - Expected value of adjustments
    """
    counter = gto_service.get_counter_strategy(
        player_name=player,
        position=position
    )

    return CounterStrategyResponse(**counter)


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/scenarios")
async def list_scenarios(
    street: Optional[str] = Query(None, description="Filter by street"),
    category: Optional[str] = Query(None, description="Filter by category"),
    position: Optional[str] = Query(None, description="Filter by position"),
    limit: int = Query(100, ge=1, le=1000),
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
