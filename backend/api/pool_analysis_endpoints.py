"""
Pool analysis endpoints for comprehensive player pool statistics.
Provides aggregated data for Claude to perform efficient pool analysis.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_, desc
from typing import Dict, List, Any, Optional
import logging
from decimal import Decimal

from ..database import get_db
from ..models.database_models import PlayerStats, GTOScenario

logger = logging.getLogger(__name__)

router = APIRouter()


def convert_decimals(obj):
    """Recursively convert Decimal values to float in nested structures."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals(val) for key, val in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    else:
        return obj


@router.get("/pool-analysis/comprehensive")
def get_comprehensive_pool_analysis(
    min_hands: int = 100,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive pool analysis data in a single endpoint.
    This aggregates all the key data Claude needs for pool analysis.

    Args:
        min_hands: Minimum hands required for a player to be included (default 100)
        db: Database session

    Returns:
        Comprehensive pool analysis including:
        - Pool overview statistics
        - Player type distribution
        - Top exploitable players
        - Common pool leaks (GTO deviations)
        - Aggression patterns
        - Positional tendencies
        - Profit/loss distribution
    """
    try:
        # 1. Pool Overview Statistics
        pool_stats_query = db.query(
            func.count(PlayerStats.player_name).label("total_players"),
            func.avg(PlayerStats.vpip_pct).label("avg_vpip"),
            func.avg(PlayerStats.pfr_pct).label("avg_pfr"),
            func.avg(PlayerStats.three_bet_pct).label("avg_3bet"),
            func.avg(PlayerStats.cbet_flop_pct).label("avg_cbet"),
            func.avg(PlayerStats.fold_to_three_bet_pct).label("avg_fold_to_3bet"),
            func.avg(PlayerStats.wtsd_pct).label("avg_wtsd"),
            func.avg(PlayerStats.wsd_pct).label("avg_wsd"),
            func.avg(PlayerStats.exploitability_index).label("avg_exploitability"),
            func.avg(PlayerStats.pressure_vulnerability_score).label("avg_pressure_vulnerability"),
            func.avg(PlayerStats.aggression_consistency_ratio).label("avg_aggression_consistency"),
            func.sum(PlayerStats.total_hands).label("total_hands_in_database")
        ).filter(PlayerStats.total_hands >= min_hands).first()

        pool_overview = {
            "total_players": pool_stats_query.total_players or 0,
            "total_hands": pool_stats_query.total_hands_in_database or 0,
            "average_stats": {
                "vpip": float(pool_stats_query.avg_vpip or 0),
                "pfr": float(pool_stats_query.avg_pfr or 0),
                "3bet": float(pool_stats_query.avg_3bet or 0),
                "cbet": float(pool_stats_query.avg_cbet or 0),
                "fold_to_3bet": float(pool_stats_query.avg_fold_to_3bet or 0),
                "wtsd": float(pool_stats_query.avg_wtsd or 0),
                "wsd": float(pool_stats_query.avg_wsd or 0)
            },
            "average_composite_metrics": {
                "exploitability": float(pool_stats_query.avg_exploitability or 0),
                "pressure_vulnerability": float(pool_stats_query.avg_pressure_vulnerability or 0),
                "aggression_consistency": float(pool_stats_query.avg_aggression_consistency or 0)
            }
        }

        # 2. Player Type Distribution
        player_types = db.query(
            PlayerStats.player_type,
            func.count(PlayerStats.player_name).label("count")
        ).filter(
            PlayerStats.total_hands >= min_hands
        ).group_by(PlayerStats.player_type).all()

        type_distribution = {
            pt.player_type: pt.count for pt in player_types if pt.player_type
        }

        # 3. Top 10 Most Exploitable Players
        exploitable_players = db.query(
            PlayerStats.player_name,
            PlayerStats.player_type,
            PlayerStats.exploitability_index,
            PlayerStats.total_hands,
            PlayerStats.vpip_pct,
            PlayerStats.pfr_pct,
            PlayerStats.pressure_vulnerability_score,
            PlayerStats.value_bluff_imbalance_ratio
        ).filter(
            PlayerStats.total_hands >= min_hands
        ).order_by(
            desc(PlayerStats.exploitability_index)
        ).limit(10).all()

        top_exploitable = []
        for player in exploitable_players:
            # Identify primary weakness
            weakness = ""
            if player.pressure_vulnerability_score and player.pressure_vulnerability_score > 70:
                weakness = "Folds too much to aggression"
            elif player.value_bluff_imbalance_ratio and player.value_bluff_imbalance_ratio > 70:
                weakness = "Too value-heavy (rarely bluffs)"
            elif player.value_bluff_imbalance_ratio and player.value_bluff_imbalance_ratio < 30:
                weakness = "Bluffs too much"
            elif player.vpip_pct and player.vpip_pct > 35:
                weakness = "Plays too many hands"
            else:
                weakness = "Multiple exploitable tendencies"

            top_exploitable.append({
                "player_name": player.player_name,
                "player_type": player.player_type,
                "exploitability_index": float(player.exploitability_index or 0),
                "total_hands": player.total_hands,
                "primary_weakness": weakness,
                "key_stats": {
                    "vpip": float(player.vpip_pct or 0),
                    "pfr": float(player.pfr_pct or 0),
                    "pressure_vulnerability": float(player.pressure_vulnerability_score or 0),
                    "value_bluff_imbalance": float(player.value_bluff_imbalance_ratio or 0)
                }
            })

        # 4. Common Pool GTO Deviations
        # Note: GTO deviations data requires player_gto_stats table which was removed
        # This section returns empty data - GTO analysis is now done on-the-fly per player
        common_leaks = []

        # 5. Aggression Patterns by Street
        aggression_by_street = db.query(
            func.avg(PlayerStats.cbet_flop_pct).label("flop_aggression"),
            func.avg(PlayerStats.cbet_turn_pct).label("turn_aggression"),
            func.avg(PlayerStats.cbet_river_pct).label("river_aggression"),
            func.avg(PlayerStats.aggression_consistency_ratio).label("aggression_consistency")
        ).filter(
            PlayerStats.total_hands >= min_hands
        ).first()

        # Calculate overall aggression as average of street c-bets
        avg_cbet = (
            float(aggression_by_street.flop_aggression or 0) +
            float(aggression_by_street.turn_aggression or 0) +
            float(aggression_by_street.river_aggression or 0)
        ) / 3

        aggression_patterns = {
            "flop_cbet": float(aggression_by_street.flop_aggression or 0),
            "turn_cbet": float(aggression_by_street.turn_aggression or 0),
            "river_cbet": float(aggression_by_street.river_aggression or 0),
            "overall_aggression": avg_cbet,
            "aggression_consistency": float(aggression_by_street.aggression_consistency or 0),
            "tendency": "Aggressive" if avg_cbet > 60 else
                       "Passive" if avg_cbet < 45 else "Balanced"
        }

        # 6. Positional Play Analysis
        # Note: GTO positional data requires player_gto_stats table which was removed
        # This section returns empty data - GTO analysis is now done on-the-fly per player
        positional_tendencies = {}

        # 7. Profit Distribution
        profit_distribution = db.query(
            func.count(case((PlayerStats.total_hands >= min_hands, 1))).label("total"),
            func.count(
                case((and_(PlayerStats.total_hands >= min_hands,
                          PlayerStats.wsd_pct > 55), 1))
            ).label("winners"),
            func.count(
                case((and_(PlayerStats.total_hands >= min_hands,
                          PlayerStats.wsd_pct <= 45), 1))
            ).label("losers")
        ).first()

        # 8. Generate Pool-Wide Exploit Strategy
        pool_exploits = []

        # Based on average stats
        if pool_overview["average_stats"]["fold_to_3bet"] > 65:
            pool_exploits.append({
                "weakness": "Pool folds too much to 3-bets",
                "exploit": "3-bet bluff frequently with suited connectors and weak aces",
                "expected_profit": "High",
                "frequency": f"{pool_overview['average_stats']['fold_to_3bet']:.1f}% fold to 3-bet"
            })

        if pool_overview["average_composite_metrics"]["pressure_vulnerability"] > 60:
            pool_exploits.append({
                "weakness": "Pool is vulnerable to pressure",
                "exploit": "Triple barrel bluff more often, especially on scary runouts",
                "expected_profit": "High",
                "frequency": f"{pool_overview['average_composite_metrics']['pressure_vulnerability']:.1f} vulnerability score"
            })

        if aggression_patterns["flop_cbet"] > 65:
            pool_exploits.append({
                "weakness": "Pool c-bets too frequently on flop",
                "exploit": "Check-raise flops with draws and air, float more often",
                "expected_profit": "Medium-High",
                "frequency": f"{aggression_patterns['flop_cbet']:.1f}% flop c-bet"
            })

        # Compile final response
        analysis_result = {
            "pool_overview": pool_overview,
            "player_type_distribution": type_distribution,
            "top_exploitable_players": top_exploitable,
            "common_gto_leaks": common_leaks,
            "aggression_patterns": aggression_patterns,
            "positional_tendencies": positional_tendencies,
            "profit_distribution": {
                "total_players": profit_distribution.total if profit_distribution else 0,
                "likely_winners": profit_distribution.winners if profit_distribution else 0,
                "likely_losers": profit_distribution.losers if profit_distribution else 0,
                "breakeven_players": (profit_distribution.total - profit_distribution.winners - profit_distribution.losers)
                                    if profit_distribution else 0
            },
            "recommended_pool_exploits": pool_exploits,
            "summary": {
                "pool_classification": type_distribution.get("LAG", 0) > type_distribution.get("TAG", 0)
                                      if type_distribution else False,
                "overall_skill_level": "Weak" if pool_overview["average_composite_metrics"]["exploitability"] > 60
                                      else "Average" if pool_overview["average_composite_metrics"]["exploitability"] > 40
                                      else "Strong",
                "best_exploit_angle": "Aggression" if pool_overview["average_composite_metrics"]["pressure_vulnerability"] > 60
                                     else "Value betting" if len([p for p in top_exploitable if "station" in (p.get("player_type") or "").lower()]) > 3
                                     else "Balanced exploitation"
            }
        }

        # Convert all Decimal values to float
        return convert_decimals(analysis_result)

    except Exception as e:
        logger.error(f"Error in comprehensive pool analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pool analysis error: {str(e)}")


@router.get("/pool-analysis/quick-summary")
def get_quick_pool_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get a quick summary of the player pool for Claude's initial assessment.
    Lighter weight than comprehensive analysis.

    Returns:
        Quick summary with key pool metrics
    """
    try:
        # Basic pool stats
        summary = db.query(
            func.count(PlayerStats.player_name).label("total_players"),
            func.avg(PlayerStats.exploitability_index).label("avg_exploitability"),
            func.max(PlayerStats.exploitability_index).label("max_exploitability"),
            func.avg(PlayerStats.vpip_pct).label("avg_vpip"),
            func.avg(PlayerStats.pfr_pct).label("avg_pfr")
        ).filter(PlayerStats.total_hands >= 100).first()

        # Most common player type
        most_common_type = db.query(
            PlayerStats.player_type,
            func.count(PlayerStats.player_name).label("count")
        ).filter(
            PlayerStats.total_hands >= 100
        ).group_by(
            PlayerStats.player_type
        ).order_by(
            desc(func.count(PlayerStats.player_name))
        ).first()

        return {
            "total_players": summary.total_players or 0,
            "avg_exploitability": float(summary.avg_exploitability or 0),
            "max_exploitability": float(summary.max_exploitability or 0),
            "avg_vpip": float(summary.avg_vpip or 0),
            "avg_pfr": float(summary.avg_pfr or 0),
            "most_common_type": most_common_type.player_type if most_common_type else "Unknown",
            "pool_tendency": "Loose" if (summary.avg_vpip or 0) > 28 else
                           "Tight" if (summary.avg_vpip or 0) < 20 else "Standard"
        }

    except Exception as e:
        logger.error(f"Error in quick pool summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pool summary error: {str(e)}")