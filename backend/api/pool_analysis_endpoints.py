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
from ..models.database_models import PlayerStat
from ..models.gto_models import PlayerGTOStat, GTOScenario

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
            func.count(PlayerStat.player_name).label("total_players"),
            func.avg(PlayerStat.vpip_pct).label("avg_vpip"),
            func.avg(PlayerStat.pfr_pct).label("avg_pfr"),
            func.avg(PlayerStat.three_bet_pct).label("avg_3bet"),
            func.avg(PlayerStat.cbet_flop_pct).label("avg_cbet"),
            func.avg(PlayerStat.fold_to_three_bet_pct).label("avg_fold_to_3bet"),
            func.avg(PlayerStat.wtsd_pct).label("avg_wtsd"),
            func.avg(PlayerStat.wsd_pct).label("avg_wsd"),
            func.avg(PlayerStat.exploitability_index).label("avg_exploitability"),
            func.avg(PlayerStat.pressure_vulnerability_score).label("avg_pressure_vulnerability"),
            func.avg(PlayerStat.aggression_consistency_ratio).label("avg_aggression_consistency"),
            func.sum(PlayerStat.total_hands).label("total_hands_in_database")
        ).filter(PlayerStat.total_hands >= min_hands).first()

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
            PlayerStat.player_type,
            func.count(PlayerStat.player_name).label("count")
        ).filter(
            PlayerStat.total_hands >= min_hands
        ).group_by(PlayerStat.player_type).all()

        type_distribution = {
            pt.player_type: pt.count for pt in player_types if pt.player_type
        }

        # 3. Top 10 Most Exploitable Players
        exploitable_players = db.query(
            PlayerStat.player_name,
            PlayerStat.player_type,
            PlayerStat.exploitability_index,
            PlayerStat.total_hands,
            PlayerStat.vpip_pct,
            PlayerStat.pfr_pct,
            PlayerStat.pressure_vulnerability_score,
            PlayerStat.value_bluff_imbalance_ratio
        ).filter(
            PlayerStat.total_hands >= min_hands
        ).order_by(
            desc(PlayerStat.exploitability_index)
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
        # Get top 10 most common GTO leaks across the pool
        gto_deviations = db.query(
            GTOScenario.scenario_name,
            GTOScenario.position,
            GTOScenario.action,
            GTOScenario.gto_frequency,
            func.avg(PlayerGTOStat.player_frequency).label("avg_player_freq"),
            func.avg(PlayerGTOStat.ev_loss).label("avg_ev_loss"),
            func.count(PlayerGTOStat.player_name).label("num_players"),
            func.avg(
                func.abs(PlayerGTOStat.player_frequency - GTOScenario.gto_frequency)
            ).label("avg_deviation")
        ).join(
            PlayerGTOStat, PlayerGTOStat.scenario_id == GTOScenario.id
        ).group_by(
            GTOScenario.id,
            GTOScenario.scenario_name,
            GTOScenario.position,
            GTOScenario.action,
            GTOScenario.gto_frequency
        ).having(
            func.avg(func.abs(PlayerGTOStat.player_frequency - GTOScenario.gto_frequency)) > 0.10
        ).order_by(
            desc(func.avg(PlayerGTOStat.ev_loss))
        ).limit(10).all()

        common_leaks = []
        for leak in gto_deviations:
            # Format the scenario name for readability
            scenario_parts = leak.scenario_name.split('_')
            if len(scenario_parts) >= 3:
                position_action = f"{scenario_parts[0]} {scenario_parts[-1]}"
            else:
                position_action = leak.scenario_name

            # Determine exploit recommendation based on deviation
            deviation = float(leak.avg_player_freq or 0) - float(leak.gto_frequency or 0)
            if abs(deviation) < 0.1:
                exploit = "Minor deviation - no major exploit"
            elif deviation > 0.3:
                if "open" in leak.scenario_name.lower():
                    exploit = "Pool opens way too much from this position - 3-bet them aggressively"
                elif "3bet" in leak.scenario_name.lower():
                    exploit = "Pool 3-bets too much - 4-bet light or call with wider range"
                elif "cbet" in leak.scenario_name.lower():
                    exploit = "Pool c-bets too frequently - call down lighter and raise as bluff-catch"
                else:
                    exploit = f"Pool over-does this action by {deviation*100:.1f}% - exploit by defending wider"
            elif deviation > 0.15:
                exploit = f"Pool slightly over-aggressive here (+{deviation*100:.1f}%) - defend a bit wider"
            elif deviation < -0.3:
                if "open" in leak.scenario_name.lower():
                    exploit = "Pool doesn't open enough - steal their blinds relentlessly"
                elif "3bet" in leak.scenario_name.lower():
                    exploit = "Pool doesn't 3-bet enough - open wider and fold less to their 3-bets"
                elif "fold" in leak.scenario_name.lower():
                    exploit = "Pool folds way too much - bluff them aggressively"
                else:
                    exploit = f"Pool under-does this action by {abs(deviation)*100:.1f}% - attack them when they show weakness"
            else:
                exploit = f"Pool slightly passive here ({deviation*100:.1f}%) - apply more pressure"

            common_leaks.append({
                "scenario": position_action,
                "position": leak.position,
                "action": leak.action,
                "pool_frequency": float(leak.avg_player_freq or 0) * 100,
                "gto_frequency": float(leak.gto_frequency or 0) * 100,
                "deviation_percentage": abs(deviation) * 100,
                "avg_ev_loss": float(leak.avg_ev_loss or 0),
                "num_players_with_leak": leak.num_players,
                "exploit_recommendation": exploit
            })

        # 5. Aggression Patterns by Street
        aggression_by_street = db.query(
            func.avg(PlayerStat.cbet_flop_pct).label("flop_aggression"),
            func.avg(PlayerStat.cbet_turn_pct).label("turn_aggression"),
            func.avg(PlayerStat.aggression_frequency).label("overall_aggression"),
            func.avg(PlayerStat.aggression_factor).label("aggression_factor")
        ).filter(
            PlayerStat.total_hands >= min_hands
        ).first()

        aggression_patterns = {
            "flop_cbet": float(aggression_by_street.flop_aggression or 0),
            "turn_cbet": float(aggression_by_street.turn_aggression or 0),
            "overall_aggression": float(aggression_by_street.overall_aggression or 0),
            "aggression_factor": float(aggression_by_street.aggression_factor or 0),
            "tendency": "Aggressive" if (aggression_by_street.overall_aggression or 0) > 35 else
                       "Passive" if (aggression_by_street.overall_aggression or 0) < 25 else "Balanced"
        }

        # 6. Positional Play Analysis
        # Get GTO stats grouped by position to see where pool is weakest
        positional_analysis = db.query(
            GTOScenario.position,
            func.avg(
                func.abs(PlayerGTOStat.player_frequency - GTOScenario.gto_frequency)
            ).label("avg_deviation"),
            func.avg(PlayerGTOStat.ev_loss).label("avg_ev_loss"),
            func.count(func.distinct(PlayerGTOStat.player_name)).label("sample_size")
        ).join(
            PlayerGTOStat, PlayerGTOStat.scenario_id == GTOScenario.id
        ).filter(
            GTOScenario.position.in_(['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'])
        ).group_by(
            GTOScenario.position
        ).all()

        positional_tendencies = {}
        for pos in positional_analysis:
            if pos.position:
                deviation = float(pos.avg_deviation or 0)
                positional_tendencies[pos.position] = {
                    "avg_gto_deviation": deviation * 100,
                    "avg_ev_loss": float(pos.avg_ev_loss or 0),
                    "sample_size": pos.sample_size,
                    "assessment": "Major leaks" if deviation > 0.20 else
                                 "Exploitable" if deviation > 0.10 else "Solid"
                }

        # 7. Profit Distribution
        profit_distribution = db.query(
            func.count(case((PlayerStat.total_hands >= min_hands, 1))).label("total"),
            func.count(
                case((and_(PlayerStat.total_hands >= min_hands,
                          PlayerStat.wsd_pct > 55), 1))
            ).label("winners"),
            func.count(
                case((and_(PlayerStat.total_hands >= min_hands,
                          PlayerStat.wsd_pct <= 45), 1))
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
            func.count(PlayerStat.player_name).label("total_players"),
            func.avg(PlayerStat.exploitability_index).label("avg_exploitability"),
            func.max(PlayerStat.exploitability_index).label("max_exploitability"),
            func.avg(PlayerStat.vpip_pct).label("avg_vpip"),
            func.avg(PlayerStat.pfr_pct).label("avg_pfr")
        ).filter(PlayerStat.total_hands >= 100).first()

        # Most common player type
        most_common_type = db.query(
            PlayerStat.player_type,
            func.count(PlayerStat.player_name).label("count")
        ).filter(
            PlayerStat.total_hands >= 100
        ).group_by(
            PlayerStat.player_type
        ).order_by(
            desc(func.count(PlayerStat.player_name))
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