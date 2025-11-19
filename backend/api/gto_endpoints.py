"""
API endpoints for GTO solution queries.

Provides RESTful access to pre-computed GTO solutions and
player deviation analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.services.gto_service import GTOService
from backend.services.poker_baselines import BaselineProvider
from backend.database import get_db
from backend.models.database_models import PlayerStats
import psycopg2
import os

baseline_provider = BaselineProvider()

router = APIRouter(prefix="/api/gto", tags=["GTO Analysis"])


def get_db_connection():
    """Get database connection for GTO matcher."""
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    return None


# Response models
class GTOSolutionResponse(BaseModel):
    """GTO solution response model"""
    scenario_name: str
    scenario_type: str
    board: Optional[str] = None
    position_oop: Optional[str] = None
    position_ip: Optional[str] = None
    pot_size: float
    stack_depth: float
    gto_bet_frequency: Optional[float] = None
    gto_fold_frequency: Optional[float] = None
    gto_raise_frequency: Optional[float] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DeviationDetail(BaseModel):
    """Individual deviation detail"""
    stat: str
    player: float
    gto: float
    deviation: float
    severity: str
    exploitable: bool
    exploit_direction: str
    estimated_ev: Optional[float] = None


class DeviationAnalysisResponse(BaseModel):
    """Player vs GTO deviation analysis"""
    scenario: str
    gto_baseline: dict
    deviations: List[DeviationDetail]
    exploitable_count: int
    total_estimated_ev: float
    summary: str


class ScenarioListItem(BaseModel):
    """Scenario list item"""
    scenario_name: str
    scenario_type: str
    board: Optional[str] = None
    description: Optional[str] = None


class AnalyzePlayerRequest(BaseModel):
    """Request body for player analysis"""
    scenarios: Optional[List[str]] = None


# Endpoints
@router.get("/scenarios", response_model=List[ScenarioListItem])
async def list_scenarios(
    scenario_type: Optional[str] = Query(
        None,
        description="Filter by type: preflop, srp_flop, 3bet_pot, etc."
    ),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    db: Session = Depends(get_db)
):
    """
    List available GTO scenarios.

    Returns list of all pre-computed GTO solutions, optionally filtered by type.
    """
    service = GTOService(db)
    scenarios = service.list_scenarios(scenario_type=scenario_type, limit=limit)

    return scenarios


@router.get("/solution/{scenario_name}", response_model=GTOSolutionResponse)
async def get_gto_solution(
    scenario_name: str,
    db: Session = Depends(get_db)
):
    """
    Get GTO solution for a specific scenario.

    Example: /api/gto/solution/BTN_steal_vs_BB

    Returns the pre-computed GTO frequencies and strategy for this spot.
    """
    service = GTOService(db)
    solution = service.get_gto_solution(scenario_name)

    if not solution:
        raise HTTPException(
            status_code=404,
            detail=f"GTO solution not found for scenario: {scenario_name}"
        )

    return solution


@router.get("/compare/{player_name}/{scenario_name}")
async def compare_player_to_gto(
    player_name: str,
    scenario_name: str,
    db: Session = Depends(get_db)
):
    """
    Compare player statistics to GTO baseline.

    Example: /api/gto/compare/snajd/BTN_steal_vs_BB

    Returns deviation analysis showing how the player differs from GTO
    and identifies exploitable patterns.
    """
    service = GTOService(db)

    # Get player stats
    player = db.query(PlayerStats).filter(
        PlayerStats.player_name == player_name
    ).first()

    if not player:
        raise HTTPException(
            status_code=404,
            detail=f"Player not found: {player_name}"
        )

    # Convert to dict
    player_dict = {
        'fold_to_three_bet_pct': player.fold_to_three_bet_pct,
        'cbet_flop_pct': player.cbet_flop_pct,
        'fold_to_cbet_flop_pct': player.fold_to_cbet_flop_pct,
        'vpip_pct': player.vpip_pct,
        'pfr_pct': player.pfr_pct
    }

    # Compare to GTO
    comparison = service.compare_player_to_gto(player_dict, scenario_name)

    if 'error' in comparison:
        raise HTTPException(
            status_code=404,
            detail=comparison['error']
        )

    return comparison


@router.get("/stats")
async def get_gto_stats(db: Session = Depends(get_db)):
    """
    Get statistics about available GTO solutions.

    Returns counts by scenario type and total coverage.
    """
    service = GTOService(db)
    counts = service.get_scenario_count()

    return {
        "scenario_counts": counts,
        "message": "GTO solution database statistics"
    }


@router.post("/analyze/{player_name}")
async def analyze_player_exploits(
    player_name: str,
    request_body: AnalyzePlayerRequest = Body(default=AnalyzePlayerRequest()),
    db: Session = Depends(get_db)
):
    """
    Analyze player against multiple GTO scenarios to identify exploits.

    Body (optional):
    {
        "scenarios": ["BTN_steal_vs_BB", "SRP_Ks7c3d_cbet", "3BET_AhKs9d_cbet"]
    }

    If no scenarios provided, uses default set of common scenarios.
    """
    service = GTOService(db)

    # Get player
    player = db.query(PlayerStats).filter(
        PlayerStats.player_name == player_name
    ).first()

    if not player:
        raise HTTPException(
            status_code=404,
            detail=f"Player not found: {player_name}"
        )

    # Default scenarios if none provided
    scenarios = request_body.scenarios
    if not scenarios:
        scenarios = [
            'BTN_steal_vs_BB',
            'SRP_Ks7c3d_cbet',
            'SRP_Ah9s3h_cbet',
            '3BET_AhKs9d_cbet'
        ]

    # Analyze each scenario
    player_dict = {
        'fold_to_three_bet_pct': player.fold_to_three_bet_pct,
        'cbet_flop_pct': player.cbet_flop_pct,
        'fold_to_cbet_flop_pct': player.fold_to_cbet_flop_pct,
        'vpip_pct': player.vpip_pct,
        'pfr_pct': player.pfr_pct
    }

    results = []
    total_ev = 0
    using_baselines = False

    for scenario in scenarios:
        comparison = service.compare_player_to_gto(player_dict, scenario)

        if 'error' not in comparison:
            # Check if this is a baseline comparison (no GTO solution)
            if comparison.get('comparison_type') == 'baseline':
                # Only add baseline comparison once
                if not using_baselines:
                    results.append(comparison)
                    total_ev += comparison.get('total_estimated_ev', 0)
                    using_baselines = True
            else:
                # Add GTO solution comparisons normally
                results.append(comparison)
                total_ev += comparison.get('total_estimated_ev', 0)

    # Adjust summary based on comparison type
    if using_baselines and len(results) == 1:
        summary = f"Using poker theory baselines - found {results[0]['exploitable_count']} exploitable deviations"
    else:
        summary = f"Found {sum(r['exploitable_count'] for r in results)} exploitable deviations across {len(results)} scenarios"

    return {
        "player_name": player_name,
        "scenarios_analyzed": len(results),
        "total_estimated_ev": round(total_ev, 2),
        "analyses": results,
        "summary": summary
    }


@router.get("/baselines")
async def get_baselines():
    """
    Get all poker theory baselines.
    
    Returns comprehensive baseline statistics for exploit detection.
    """
    baselines = baseline_provider.get_baseline_stats()
    
    return {
        "baseline_type": "poker_theory",
        "source": "Modern Poker Theory + GTO Approximations",
        "baselines": baselines,
        "stat_count": len(baselines),
        "message": "Comprehensive poker theory baselines for exploit detection"
    }


@router.get("/baselines/position/{position}")
async def get_position_baselines(position: str):
    """
    Get position-specific baselines.

    Returns RFI frequencies, VPIP ranges, and opening ranges for a position.
    """
    return {
        "position": position.upper(),
        "rfi_frequency": baseline_provider.get_rfi_frequency(position),
        "vpip_range": baseline_provider.get_vpip_range(position),
        "opening_range": baseline_provider.get_opening_range(position),
        "fold_to_3bet_average": baseline_provider.get_fold_to_3bet(position)
    }


# New board-based GTO matching endpoints
class GTOMatchResponse(BaseModel):
    """Single GTO match response"""
    solution_id: int
    scenario_name: str
    board: str
    match_type: str
    confidence: float
    similarity_score: float
    category_l1: str
    category_l2: str
    category_l3: str


class BoardMatchResponse(BaseModel):
    """Board-based GTO matching response"""
    target_board: str
    board_category_l1: str
    board_category_l2: str
    board_category_l3: str
    matches: List[GTOMatchResponse]
    total_matches: int
    best_match: Optional[GTOMatchResponse] = None


@router.get("/match", response_model=BoardMatchResponse)
async def find_gto_matches(
    board: str = Query(..., description="Board string (e.g., 'As8h3c')"),
    scenario_type: Optional[str] = Query(None, description="Scenario type filter (SRP, 3BP, 4BP)"),
    position: Optional[str] = Query(None, description="Position filter (IP, OOP)"),
    action: Optional[str] = Query(None, description="Action sequence filter (cbet, check, etc.)"),
    top_n: int = Query(3, ge=1, le=10, description="Number of matches to return")
):
    """
    Find best matching GTO solutions for a given board.

    Uses multi-level categorization with adaptive matching:
    - Tries exact board match first (100% confidence)
    - Falls back to L3 category (80-90% confidence)
    - Falls back to L2 category (60-75% confidence)
    - Falls back to L1 category (40-55% confidence)

    Example: /api/gto/match?board=As8h3c&scenario_type=SRP&top_n=3

    Returns ranked list of matching GTO solutions with confidence scores.
    """
    try:
        # Import here to avoid circular imports
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "services"))
        from gto_matcher import GTOMatcher

        # Get database connection
        db_conn = get_db_connection()
        if not db_conn:
            raise HTTPException(
                status_code=500,
                detail="Database connection not available"
            )

        # Create matcher and find matches
        matcher = GTOMatcher(db_conn=db_conn)
        matches = matcher.find_matches(
            board=board,
            scenario_type=scenario_type,
            position_context=position,
            action_sequence=action,
            top_n=top_n
        )

        # Categorize the target board
        analysis = matcher.categorizer.analyze(board)

        # Convert matches to response format
        match_responses = [
            GTOMatchResponse(
                solution_id=m.solution_id,
                scenario_name=m.scenario_name,
                board=m.board,
                match_type=m.match_type,
                confidence=round(m.confidence, 1),
                similarity_score=round(m.similarity_score, 1),
                category_l1=m.category_l1,
                category_l2=m.category_l2,
                category_l3=m.category_l3
            )
            for m in matches
        ]

        # Close connection
        db_conn.close()

        return BoardMatchResponse(
            target_board=board,
            board_category_l1=analysis.category_l1,
            board_category_l2=analysis.category_l2,
            board_category_l3=analysis.category_l3,
            matches=match_responses,
            total_matches=len(match_responses),
            best_match=match_responses[0] if match_responses else None
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding GTO matches: {str(e)}"
        )
