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


@router.get("/dashboard/{player}")
async def get_gto_dashboard(
    player: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get comprehensive GTO dashboard data for a player.

    Returns:
    - Overall adherence score
    - Top leaks
    - Opening ranges analysis
    - Defense stats
    - Position-by-position breakdown
    """
    from backend.models.gto_models import PlayerGTOStat, GTOScenario
    from sqlalchemy import func, desc

    try:
        # Get overall adherence
        adherence = gto_service.get_player_gto_adherence(player, 'preflop')

        # Get top 10 leaks
        leaks = gto_service.get_player_leaks(
            player_name=player,
            min_hands=10,
            sort_by='ev_loss',
            street='preflop'
        )[:10]

        # Convert leak frequencies to percentages
        for leak in leaks:
            if leak.get('player_frequency') is not None:
                leak['player_frequency'] = float(leak['player_frequency']) * 100
            if leak.get('gto_frequency') is not None:
                leak['gto_frequency'] = float(leak['gto_frequency']) * 100
            if leak.get('frequency_diff') is not None:
                leak['frequency_diff'] = float(leak['frequency_diff']) * 100

        # Get opening ranges summary
        opening_scenarios = gto_service.db.query(PlayerGTOStat, GTOScenario).join(
            GTOScenario,
            PlayerGTOStat.scenario_id == GTOScenario.scenario_id
        ).filter(
            PlayerGTOStat.player_name == player,
            GTOScenario.scenario_name.like('%_open')
        ).all()

        opening_ranges = []
        for stat, scenario in opening_scenarios:
            position = scenario.scenario_name.replace('_open', '')
            opening_ranges.append({
                'position': position,
                'total_hands': stat.total_hands,
                'player_frequency': float(stat.player_frequency) * 100,
                'gto_frequency': float(stat.gto_frequency) * 100,
                'frequency_diff': float(stat.frequency_diff) * 100,
                'leak_severity': stat.leak_severity,
                'ev_loss_bb': float(stat.total_ev_loss_bb) if stat.total_ev_loss_bb else 0
            })

        # Sort by position order
        position_order = {'UTG': 1, 'MP': 2, 'CO': 3, 'BTN': 4, 'SB': 5}
        opening_ranges.sort(key=lambda x: position_order.get(x['position'], 99))

        # Get defense stats summary
        defense_scenarios = gto_service.db.query(PlayerGTOStat, GTOScenario).join(
            GTOScenario,
            PlayerGTOStat.scenario_id == GTOScenario.scenario_id
        ).filter(
            PlayerGTOStat.player_name == player,
            GTOScenario.category == 'defense',
            PlayerGTOStat.total_hands >= 10
        ).order_by(desc(PlayerGTOStat.total_ev_loss_bb)).limit(10).all()

        defense_stats = []
        for stat, scenario in defense_scenarios:
            defense_stats.append({
                'scenario_name': scenario.scenario_name,
                'total_hands': stat.total_hands,
                'player_frequency': float(stat.player_frequency) * 100,
                'gto_frequency': float(stat.gto_frequency) * 100,
                'frequency_diff': float(stat.frequency_diff) * 100,
                'leak_type': stat.leak_type,
                'leak_severity': stat.leak_severity
            })

        # Get 3-bet stats (facing_3bet category)
        threebet_scenarios = gto_service.db.query(PlayerGTOStat, GTOScenario).join(
            GTOScenario,
            PlayerGTOStat.scenario_id == GTOScenario.scenario_id
        ).filter(
            PlayerGTOStat.player_name == player,
            GTOScenario.scenario_name.like('%_3bet')
        ).order_by(desc(PlayerGTOStat.total_hands)).all()

        threebet_stats = []
        for stat, scenario in threebet_scenarios:
            # Parse scenario name to get position and vs_position
            # e.g., "BB_vs_UTG_3bet" -> position=BB, vs_position=UTG
            parts = scenario.scenario_name.split('_')
            if len(parts) >= 3 and parts[-1] == '3bet':
                position = parts[0]
                vs_position = parts[2] if parts[1] == 'vs' else None

                threebet_stats.append({
                    'scenario_name': scenario.scenario_name,
                    'position': position,
                    'vs_position': vs_position,
                    'total_hands': stat.total_hands,
                    'player_frequency': float(stat.player_frequency) * 100,
                    'gto_frequency': float(stat.gto_frequency) * 100,
                    'frequency_diff': float(stat.frequency_diff) * 100,
                    'leak_type': stat.leak_type,
                    'leak_severity': stat.leak_severity
                })

        return {
            'player': player,
            'adherence': adherence,
            'opening_ranges': opening_ranges,
            'defense_stats': defense_stats,
            'threebet_stats': threebet_stats,
            'top_leaks': leaks,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dashboard: {str(e)}"
        )


# ============================================================================
# ANALYZE ENDPOINT (Missing - needed by frontend)
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request for player exploit analysis"""
    scenarios: Optional[List[str]] = Field(None, description="Specific scenarios to analyze")


class DeviationItem(BaseModel):
    """A single deviation from baseline/GTO"""
    stat: str
    player: float
    baseline: Optional[float] = None
    gto: Optional[float] = None
    deviation: float
    abs_deviation: float
    severity: str  # negligible, minor, moderate, severe, extreme
    exploitable: bool
    direction: str  # over, under
    exploit_direction: Optional[str] = None
    exploit: Optional[str] = None
    estimated_ev: Optional[float] = None


class ScenarioAnalysis(BaseModel):
    """Analysis for a single scenario"""
    comparison_type: Optional[str] = 'gto'
    scenario: str
    baseline_type: Optional[str] = None
    baseline_source: Optional[str] = None
    position: Optional[str] = None
    gto_baseline: Optional[Dict[str, Any]] = None
    deviations: List[DeviationItem]
    exploitable_count: int
    total_estimated_ev: float
    summary: str


class PlayerExploitAnalysisResponse(BaseModel):
    """Complete exploit analysis response"""
    player_name: str
    scenarios_analyzed: int
    total_estimated_ev: float
    analyses: List[ScenarioAnalysis]
    summary: str


@router.post("/analyze/{player_name}", response_model=PlayerExploitAnalysisResponse)
async def analyze_player_exploits(
    player_name: str,
    request: Optional[AnalyzeRequest] = None,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Comprehensive exploit analysis for a player.

    Analyzes player against GTO baselines and returns exploitable patterns.

    Example: POST /api/gto/analyze/Villain1

    Returns:
    - All scenario analyses
    - Deviation details
    - Exploit recommendations
    - Total expected value
    """
    from backend.models.gto_models import PlayerGTOStat, GTOScenario
    from sqlalchemy import desc

    try:
        analyses = []
        total_ev = 0.0

        # Get all player's GTO stats
        query = gto_service.db.query(PlayerGTOStat, GTOScenario).join(
            GTOScenario,
            PlayerGTOStat.scenario_id == GTOScenario.scenario_id
        ).filter(
            PlayerGTOStat.player_name == player_name,
            PlayerGTOStat.total_hands >= 10
        )

        # Filter by specific scenarios if provided
        if request and request.scenarios:
            query = query.filter(GTOScenario.scenario_name.in_(request.scenarios))

        results = query.order_by(desc(PlayerGTOStat.total_ev_loss_bb)).all()

        for stat, scenario in results:
            player_freq = float(stat.player_frequency) * 100 if stat.player_frequency else 0
            gto_freq = float(stat.gto_frequency) * 100 if stat.gto_frequency else 0
            freq_diff = float(stat.frequency_diff) * 100 if stat.frequency_diff else 0
            ev_loss = float(stat.total_ev_loss_bb) if stat.total_ev_loss_bb else 0

            # Determine severity
            abs_diff = abs(freq_diff)
            if abs_diff < 5:
                severity = 'negligible'
            elif abs_diff < 10:
                severity = 'minor'
            elif abs_diff < 20:
                severity = 'moderate'
            elif abs_diff < 35:
                severity = 'severe'
            else:
                severity = 'extreme'

            # Determine direction
            direction = 'over' if freq_diff > 0 else 'under'

            # Generate exploit recommendation
            exploit = None
            exploit_direction = None
            if abs_diff >= 10:
                if stat.leak_type and 'over' in stat.leak_type:
                    exploit = f"Counter by calling/raising lighter when they {scenario.action or 'act'}"
                    exploit_direction = "call down lighter"
                elif stat.leak_type and 'under' in stat.leak_type:
                    exploit = f"Apply pressure - they fold too much in this spot"
                    exploit_direction = "bluff more"
                else:
                    exploit = stat.exploit_description

            deviation = DeviationItem(
                stat=f"{scenario.scenario_name} ({scenario.action or 'action'})",
                player=player_freq,
                gto=gto_freq,
                deviation=freq_diff,
                abs_deviation=abs_diff,
                severity=severity,
                exploitable=abs_diff >= 10,
                direction=direction,
                exploit_direction=exploit_direction,
                exploit=exploit,
                estimated_ev=ev_loss
            )

            scenario_analysis = ScenarioAnalysis(
                comparison_type='gto',
                scenario=scenario.scenario_name,
                position=scenario.position,
                gto_baseline={
                    'scenario_type': scenario.category,
                    'description': scenario.description,
                    'gto_frequency': gto_freq
                },
                deviations=[deviation],
                exploitable_count=1 if abs_diff >= 10 else 0,
                total_estimated_ev=ev_loss,
                summary=f"{severity.capitalize()} deviation ({freq_diff:+.1f}%)" if abs_diff >= 5 else "Within GTO range"
            )

            analyses.append(scenario_analysis)
            total_ev += ev_loss

        # Generate overall summary
        severe_count = sum(1 for a in analyses if any(d.severity in ['severe', 'extreme'] for d in a.deviations))
        if severe_count == 0:
            summary = f"Player {player_name} plays relatively close to GTO with minor leaks"
        elif severe_count <= 3:
            summary = f"Player {player_name} has {severe_count} significant leaks to exploit"
        else:
            summary = f"Player {player_name} is highly exploitable with {severe_count} major deviations from GTO"

        return PlayerExploitAnalysisResponse(
            player_name=player_name,
            scenarios_analyzed=len(analyses),
            total_estimated_ev=total_ev,
            analyses=analyses,
            summary=summary
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze player: {str(e)}"
        )


# ============================================================================
# BOARD MATCH ENDPOINT (Missing - needed by GTOBoardMatch component)
# ============================================================================

class GTOMatchResponse(BaseModel):
    """GTO match response for board matching"""
    board: str
    matches: List[Dict[str, Any]]
    best_match: Optional[Dict[str, Any]] = None
    board_category: Optional[str] = None


@router.get("/match")
async def match_board_to_gto(
    board: str = Query(..., description="Board cards (e.g., 'Ks7c3d')"),
    top_n: int = Query(5, ge=1, le=20, description="Number of matches to return"),
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Match a board to GTO solutions.

    Example: GET /api/gto/match?board=Ks7c3d&top_n=5

    Returns GTO solutions that match or are similar to the given board texture.
    """
    from backend.models.gto_models import GTOScenario
    from backend.services.board_categorizer import BoardCategorizer

    try:
        # Categorize the input board
        categorizer = BoardCategorizer()
        board_clean = board.replace(' ', '')

        # Get board category
        category_l1, category_l2, category_l3 = categorizer.categorize_board(board_clean)

        # Find matching GTO solutions
        # First try exact board match
        matches = []

        # Query gto_solutions table for similar boards
        from sqlalchemy import text

        # Search for boards with similar category
        query = text("""
            SELECT scenario_name, board, board_category_l1, board_category_l2, board_category_l3,
                   gto_bet_frequency, gto_check_frequency, gto_fold_frequency,
                   position_oop, position_ip, scenario_type
            FROM gto_solutions
            WHERE board_category_l1 = :cat1
            ORDER BY
                CASE
                    WHEN board = :board THEN 0
                    WHEN board_category_l2 = :cat2 THEN 1
                    WHEN board_category_l3 = :cat3 THEN 2
                    ELSE 3
                END
            LIMIT :limit
        """)

        result = gto_service.db.execute(query, {
            'board': board_clean,
            'cat1': category_l1,
            'cat2': category_l2,
            'cat3': category_l3,
            'limit': top_n
        })

        rows = result.fetchall()

        for row in rows:
            match = {
                'scenario_name': row[0],
                'board': row[1],
                'board_category_l1': row[2],
                'board_category_l2': row[3],
                'board_category_l3': row[4],
                'gto_bet_frequency': float(row[5]) if row[5] else None,
                'gto_check_frequency': float(row[6]) if row[6] else None,
                'gto_fold_frequency': float(row[7]) if row[7] else None,
                'position_oop': row[8],
                'position_ip': row[9],
                'scenario_type': row[10],
                'match_quality': 'exact' if row[1] == board_clean else 'similar'
            }
            matches.append(match)

        return GTOMatchResponse(
            board=board_clean,
            matches=matches,
            best_match=matches[0] if matches else None,
            board_category=f"{category_l1} / {category_l2} / {category_l3}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to match board: {str(e)}"
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
    gto_value: Optional[float] = None  # Single GTO value if applicable
    source: str = "gto_database"
    description: Optional[str] = None


class PositionalOptimalRange(BaseModel):
    """Optimal range for a specific position"""
    position: str
    vpip_pct: float  # Opening/RFI frequency
    three_bet_pct: Optional[float] = None  # Average 3-bet frequency
    fold_to_3bet_pct: Optional[float] = None  # Average fold to 3-bet


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

    Note: Overall player stat ranges are based on poker theory for 6-max cash.
    The GTO scenario data represents action frequencies for SPECIFIC scenarios,
    not overall player tendencies. A player's VPIP is ~22% because they fold
    most hands, even though BTN should open 93% when folded to.

    Example: GET /api/gto/optimal-ranges
    """
    from backend.models.gto_models import GTOScenario, GTOFrequency

    try:
        # Overall optimal ranges for PLAYER STATS (not scenario frequencies)
        # These are standard ranges for winning 6-max cash game players
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

        # Get position-specific RFI (raise first in) frequencies from GTO
        # These show optimal OPENING ranges when folded to in each position
        opening_scenarios = gto_service.db.query(GTOScenario).filter(
            GTOScenario.category == 'opening'
        ).all()

        positional_data = []
        for scenario in opening_scenarios:
            pos = scenario.position
            # RFI frequency - how often to open when folded to
            rfi_freq = float(scenario.gto_aggregate_freq) * 100 if scenario.gto_aggregate_freq else 0

            positional_data.append(PositionalOptimalRange(
                position=pos,
                vpip_pct=round(rfi_freq, 1),  # This is RFI, not overall VPIP from this position
            ))

        # Sort by position order
        position_order = {'UTG': 1, 'MP': 2, 'CO': 3, 'BTN': 4, 'SB': 5, 'BB': 6}
        positional_data.sort(key=lambda x: position_order.get(x.position, 99))

        # Get counts
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
