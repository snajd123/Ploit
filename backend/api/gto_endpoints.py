"""
API endpoints for GTO solution queries.

Provides RESTful access to pre-computed GTO solutions and
player deviation analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.services.gto_service import GTOService
from backend.database import get_db
from backend.models.database_models import PlayerStats

router = APIRouter(prefix="/api/gto", tags=["GTO Analysis"])


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
    scenarios: Optional[List[str]] = None,
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

    for scenario in scenarios:
        comparison = service.compare_player_to_gto(player_dict, scenario)

        if 'error' not in comparison:
            results.append(comparison)
            total_ev += comparison.get('total_estimated_ev', 0)

    return {
        "player_name": player_name,
        "scenarios_analyzed": len(results),
        "total_estimated_ev": round(total_ev, 2),
        "analyses": results,
        "summary": f"Found {sum(r['exploitable_count'] for r in results)} exploitable deviations across {len(results)} scenarios"
    }
