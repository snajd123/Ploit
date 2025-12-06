"""
Pre-Game Strategy Tools for Claude

Provides database query tools that Claude can use to gather information
for generating exploitation strategies.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


# Tool definitions for Claude
PREGAME_TOOLS = [
    {
        "name": "get_player_full_stats",
        "description": "Get comprehensive stats for a specific player including all preflop and postflop metrics. Use this to understand a player's complete tendencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "The exact player name to look up"
                }
            },
            "required": ["player_name"]
        }
    },
    {
        "name": "get_player_positional_stats",
        "description": "Get position-specific VPIP stats for a player (UTG, HJ, CO, BTN, SB, BB). Use this to understand how a player's range changes by position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "The exact player name to look up"
                }
            },
            "required": ["player_name"]
        }
    },
    {
        "name": "get_gto_scenario_frequency",
        "description": "Get GTO frequency for a specific preflop scenario. Scenarios follow pattern: POSITION_vs_OPPONENT_action (e.g., 'BB_vs_BTN_3bet', 'CO_open', 'SB_vs_UTG_call')",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "The scenario name (e.g., 'BB_vs_BTN_3bet', 'UTG_open')"
                }
            },
            "required": ["scenario_name"]
        }
    },
    {
        "name": "list_gto_scenarios",
        "description": "List all available GTO scenarios, optionally filtered by position or action type. Use this to discover what GTO data is available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "position": {
                    "type": "string",
                    "description": "Filter by position (UTG, HJ, CO, BTN, SB, BB)"
                },
                "action": {
                    "type": "string",
                    "description": "Filter by action type (open, call, 3bet, fold)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_pool_statistics",
        "description": "Get aggregate statistics for all players at a specific stake level. Returns weighted averages for VPIP, PFR, 3-bet, fold to 3-bet, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stake_level": {
                    "type": "string",
                    "description": "The stake level (NL2, NL4, NL5, NL10, NL25, NL50)"
                }
            },
            "required": ["stake_level"]
        }
    },
    {
        "name": "find_similar_players",
        "description": "Find players in the database with similar stats to a given player. Useful for understanding player types.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vpip_min": {"type": "number", "description": "Minimum VPIP %"},
                "vpip_max": {"type": "number", "description": "Maximum VPIP %"},
                "pfr_min": {"type": "number", "description": "Minimum PFR %"},
                "pfr_max": {"type": "number", "description": "Maximum PFR %"},
                "min_hands": {"type": "integer", "description": "Minimum hands required (default 50)"}
            },
            "required": []
        }
    },
    {
        "name": "get_player_type_distribution",
        "description": "Get the distribution of player types (TAG, LAG, NIT, FISH, etc.) at a specific stake level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stake_level": {
                    "type": "string",
                    "description": "The stake level (NL2, NL4, NL5, NL10, NL25, NL50)"
                }
            },
            "required": ["stake_level"]
        }
    },
    {
        "name": "compare_player_to_gto",
        "description": "Compare a player's stats against GTO baselines and identify their biggest leaks/deviations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "The player name to analyze"
                }
            },
            "required": ["player_name"]
        }
    }
]


def execute_tool(db: Session, tool_name: str, tool_input: Dict[str, Any], hero_nicknames: List[str] = None) -> str:
    """Execute a tool and return the result as a string."""
    try:
        if tool_name == "get_player_full_stats":
            return _get_player_full_stats(db, tool_input["player_name"])
        elif tool_name == "get_player_positional_stats":
            return _get_player_positional_stats(db, tool_input["player_name"])
        elif tool_name == "get_gto_scenario_frequency":
            return _get_gto_scenario_frequency(db, tool_input["scenario_name"])
        elif tool_name == "list_gto_scenarios":
            return _list_gto_scenarios(db, tool_input.get("position"), tool_input.get("action"))
        elif tool_name == "get_pool_statistics":
            return _get_pool_statistics(db, tool_input["stake_level"], hero_nicknames or [])
        elif tool_name == "find_similar_players":
            return _find_similar_players(db, tool_input)
        elif tool_name == "get_player_type_distribution":
            return _get_player_type_distribution(db, tool_input["stake_level"])
        elif tool_name == "compare_player_to_gto":
            return _compare_player_to_gto(db, tool_input["player_name"])
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.error(f"Tool execution error for {tool_name}: {e}")
        # Rollback to clear failed transaction state
        try:
            db.rollback()
        except:
            pass
        return json.dumps({"error": str(e)})


def _get_player_full_stats(db: Session, player_name: str) -> str:
    """Get comprehensive stats for a player."""
    result = db.execute(text("""
        SELECT
            player_name, total_hands, player_type,
            vpip_pct, pfr_pct, three_bet_pct, fold_to_three_bet_pct,
            four_bet_pct, cold_call_pct, squeeze_pct, limp_pct,
            steal_attempt_pct, fold_to_steal_pct, three_bet_vs_steal_pct,
            cbet_flop_pct, cbet_turn_pct, cbet_river_pct,
            fold_to_cbet_flop_pct, fold_to_cbet_turn_pct,
            wtsd_pct, wsd_pct, wwsf_pct,
            total_profit_loss, bb_per_100
        FROM player_stats
        WHERE player_name = :name
    """), {"name": player_name}).fetchone()

    if not result:
        return json.dumps({"error": f"Player '{player_name}' not found in database"})

    return json.dumps({
        "player_name": result.player_name,
        "total_hands": result.total_hands,
        "player_type": result.player_type,
        "preflop": {
            "vpip": float(result.vpip_pct) if result.vpip_pct else None,
            "pfr": float(result.pfr_pct) if result.pfr_pct else None,
            "vpip_pfr_gap": float(result.vpip_pct - result.pfr_pct) if result.vpip_pct and result.pfr_pct else None,
            "three_bet": float(result.three_bet_pct) if result.three_bet_pct else None,
            "fold_to_3bet": float(result.fold_to_three_bet_pct) if result.fold_to_three_bet_pct else None,
            "four_bet": float(result.four_bet_pct) if result.four_bet_pct else None,
            "cold_call": float(result.cold_call_pct) if result.cold_call_pct else None,
            "squeeze": float(result.squeeze_pct) if result.squeeze_pct else None,
            "limp": float(result.limp_pct) if result.limp_pct else None,
            "steal_attempt": float(result.steal_attempt_pct) if result.steal_attempt_pct else None,
            "fold_to_steal": float(result.fold_to_steal_pct) if result.fold_to_steal_pct else None,
            "three_bet_vs_steal": float(result.three_bet_vs_steal_pct) if result.three_bet_vs_steal_pct else None
        },
        "postflop": {
            "cbet_flop": float(result.cbet_flop_pct) if result.cbet_flop_pct else None,
            "cbet_turn": float(result.cbet_turn_pct) if result.cbet_turn_pct else None,
            "cbet_river": float(result.cbet_river_pct) if result.cbet_river_pct else None,
            "fold_to_cbet_flop": float(result.fold_to_cbet_flop_pct) if result.fold_to_cbet_flop_pct else None,
            "fold_to_cbet_turn": float(result.fold_to_cbet_turn_pct) if result.fold_to_cbet_turn_pct else None,
            "wtsd": float(result.wtsd_pct) if result.wtsd_pct else None,
            "wsd": float(result.wsd_pct) if result.wsd_pct else None,
            "wwsf": float(result.wwsf_pct) if result.wwsf_pct else None
        },
        "results": {
            "total_profit_loss": float(result.total_profit_loss) if result.total_profit_loss else None,
            "bb_per_100": float(result.bb_per_100) if result.bb_per_100 else None
        }
    })


def _get_player_positional_stats(db: Session, player_name: str) -> str:
    """Get position-specific VPIP for a player."""
    result = db.execute(text("""
        SELECT
            player_name, total_hands,
            vpip_utg, vpip_hj, vpip_mp, vpip_co, vpip_btn, vpip_sb, vpip_bb
        FROM player_stats
        WHERE player_name = :name
    """), {"name": player_name}).fetchone()

    if not result:
        return json.dumps({"error": f"Player '{player_name}' not found"})

    return json.dumps({
        "player_name": result.player_name,
        "total_hands": result.total_hands,
        "vpip_by_position": {
            "UTG": float(result.vpip_utg) if result.vpip_utg else None,
            "HJ": float(result.vpip_hj) if result.vpip_hj else None,
            "MP": float(result.vpip_mp) if result.vpip_mp else None,
            "CO": float(result.vpip_co) if result.vpip_co else None,
            "BTN": float(result.vpip_btn) if result.vpip_btn else None,
            "SB": float(result.vpip_sb) if result.vpip_sb else None,
            "BB": float(result.vpip_bb) if result.vpip_bb else None
        }
    })


def _get_gto_scenario_frequency(db: Session, scenario_name: str) -> str:
    """Get GTO aggregate frequency for a scenario."""
    result = db.execute(text("""
        SELECT scenario_name, position, action, opponent_position,
               gto_aggregate_freq, category
        FROM gto_scenarios
        WHERE scenario_name = :name
    """), {"name": scenario_name}).fetchone()

    if not result:
        # Try partial match
        results = db.execute(text("""
            SELECT scenario_name, position, action, opponent_position,
                   gto_aggregate_freq, category
            FROM gto_scenarios
            WHERE scenario_name ILIKE :pattern
            LIMIT 5
        """), {"pattern": f"%{scenario_name}%"}).fetchall()

        if results:
            suggestions = [r.scenario_name for r in results]
            return json.dumps({
                "error": f"Exact scenario '{scenario_name}' not found",
                "suggestions": suggestions
            })
        return json.dumps({"error": f"Scenario '{scenario_name}' not found"})

    return json.dumps({
        "scenario_name": result.scenario_name,
        "position": result.position,
        "action": result.action,
        "vs_position": result.opponent_position,
        "gto_frequency_pct": round(float(result.gto_aggregate_freq) * 100, 1) if result.gto_aggregate_freq else None,
        "category": result.category
    })


def _list_gto_scenarios(db: Session, position: str = None, action: str = None) -> str:
    """List available GTO scenarios."""
    query = "SELECT scenario_name, position, action, opponent_position, gto_aggregate_freq FROM gto_scenarios WHERE 1=1"
    params = {}

    if position:
        query += " AND position = :position"
        params["position"] = position.upper()
    if action:
        query += " AND action ILIKE :action"
        params["action"] = f"%{action}%"

    query += " ORDER BY scenario_name LIMIT 30"

    results = db.execute(text(query), params).fetchall()

    scenarios = []
    for r in results:
        scenarios.append({
            "name": r.scenario_name,
            "position": r.position,
            "action": r.action,
            "vs": r.opponent_position,
            "gto_freq_pct": round(float(r.gto_aggregate_freq) * 100, 1) if r.gto_aggregate_freq else None
        })

    return json.dumps({"scenarios": scenarios, "count": len(scenarios)})


def _get_pool_statistics(db: Session, stake_level: str, hero_nicknames: List[str]) -> str:
    """Get pool statistics for a stake level."""
    stake = stake_level.upper()
    hero_lower = [n.lower() for n in hero_nicknames] if hero_nicknames else []

    hero_exclusion = ""
    params = {"stake_level": stake}
    if hero_lower:
        placeholders = ", ".join([f":hero_{i}" for i in range(len(hero_lower))])
        hero_exclusion = f"AND LOWER(phs.player_name) NOT IN ({placeholders})"
        for i, name in enumerate(hero_lower):
            params[f"hero_{i}"] = name

    query = f"""
        WITH player_stake_hands AS (
            SELECT phs.player_name, COUNT(*) as hands_at_stake
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.stake_level = :stake_level
            {hero_exclusion}
            GROUP BY phs.player_name
        ),
        player_with_stats AS (
            SELECT psh.player_name, psh.hands_at_stake,
                   ps.vpip_pct, ps.pfr_pct, ps.three_bet_pct,
                   ps.fold_to_three_bet_pct, ps.cold_call_pct, ps.limp_pct,
                   ps.cbet_flop_pct, ps.wtsd_pct, ps.player_type
            FROM player_stake_hands psh
            JOIN player_stats ps ON psh.player_name = ps.player_name
        )
        SELECT
            COUNT(*) as player_count,
            SUM(hands_at_stake) as total_hands,
            SUM(vpip_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_vpip,
            SUM(pfr_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_pfr,
            SUM(three_bet_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_3bet,
            SUM(fold_to_three_bet_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_f3b,
            SUM(cold_call_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_cold_call,
            SUM(limp_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_limp,
            SUM(cbet_flop_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_cbet,
            SUM(wtsd_pct * hands_at_stake) / NULLIF(SUM(hands_at_stake), 0) as avg_wtsd
        FROM player_with_stats
    """

    result = db.execute(text(query), params).fetchone()

    if not result or not result.player_count:
        return json.dumps({"error": f"No data for stake level {stake}"})

    return json.dumps({
        "stake_level": stake,
        "player_count": result.player_count,
        "total_hands": result.total_hands,
        "weighted_averages": {
            "vpip": round(float(result.avg_vpip), 1) if result.avg_vpip else None,
            "pfr": round(float(result.avg_pfr), 1) if result.avg_pfr else None,
            "vpip_pfr_gap": round(float(result.avg_vpip - result.avg_pfr), 1) if result.avg_vpip and result.avg_pfr else None,
            "three_bet": round(float(result.avg_3bet), 1) if result.avg_3bet else None,
            "fold_to_3bet": round(float(result.avg_f3b), 1) if result.avg_f3b else None,
            "cold_call": round(float(result.avg_cold_call), 1) if result.avg_cold_call else None,
            "limp": round(float(result.avg_limp), 1) if result.avg_limp else None,
            "cbet_flop": round(float(result.avg_cbet), 1) if result.avg_cbet else None,
            "wtsd": round(float(result.avg_wtsd), 1) if result.avg_wtsd else None
        }
    })


def _find_similar_players(db: Session, params: Dict[str, Any]) -> str:
    """Find players with similar stats."""
    vpip_min = params.get("vpip_min", 0)
    vpip_max = params.get("vpip_max", 100)
    pfr_min = params.get("pfr_min", 0)
    pfr_max = params.get("pfr_max", 100)
    min_hands = params.get("min_hands", 50)

    results = db.execute(text("""
        SELECT player_name, total_hands, player_type, vpip_pct, pfr_pct, three_bet_pct
        FROM player_stats
        WHERE vpip_pct BETWEEN :vpip_min AND :vpip_max
        AND pfr_pct BETWEEN :pfr_min AND :pfr_max
        AND total_hands >= :min_hands
        ORDER BY total_hands DESC
        LIMIT 10
    """), {
        "vpip_min": vpip_min, "vpip_max": vpip_max,
        "pfr_min": pfr_min, "pfr_max": pfr_max,
        "min_hands": min_hands
    }).fetchall()

    players = []
    for r in results:
        players.append({
            "name": r.player_name,
            "hands": r.total_hands,
            "type": r.player_type,
            "vpip": float(r.vpip_pct) if r.vpip_pct else None,
            "pfr": float(r.pfr_pct) if r.pfr_pct else None,
            "3bet": float(r.three_bet_pct) if r.three_bet_pct else None
        })

    return json.dumps({"matching_players": players, "count": len(players)})


def _get_player_type_distribution(db: Session, stake_level: str) -> str:
    """Get player type distribution at a stake level."""
    stake = stake_level.upper()

    results = db.execute(text("""
        WITH stake_players AS (
            SELECT DISTINCT phs.player_name
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.stake_level = :stake
        )
        SELECT ps.player_type, COUNT(*) as count
        FROM player_stats ps
        JOIN stake_players sp ON ps.player_name = sp.player_name
        WHERE ps.player_type IS NOT NULL
        GROUP BY ps.player_type
        ORDER BY count DESC
    """), {"stake": stake}).fetchall()

    distribution = {}
    total = 0
    for r in results:
        distribution[r.player_type] = r.count
        total += r.count

    # Add percentages
    dist_with_pct = {}
    for ptype, count in distribution.items():
        dist_with_pct[ptype] = {
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0
        }

    return json.dumps({
        "stake_level": stake,
        "total_players": total,
        "distribution": dist_with_pct
    })


def _compare_player_to_gto(db: Session, player_name: str) -> str:
    """Compare player stats to GTO baselines."""
    # Get player stats
    player = db.execute(text("""
        SELECT vpip_pct, pfr_pct, three_bet_pct, fold_to_three_bet_pct,
               steal_attempt_pct, fold_to_steal_pct, cbet_flop_pct, total_hands
        FROM player_stats WHERE player_name = :name
    """), {"name": player_name}).fetchone()

    if not player:
        return json.dumps({"error": f"Player '{player_name}' not found"})

    # Get GTO baselines
    gto_scenarios = db.execute(text("""
        SELECT scenario_name, gto_aggregate_freq
        FROM gto_scenarios
        WHERE scenario_name IN ('BTN_open', 'CO_open', 'BB_vs_BTN_fold', 'BB_vs_BTN_3bet')
    """)).fetchall()

    gto_baselines = {r.scenario_name: float(r.gto_aggregate_freq) * 100 for r in gto_scenarios}

    # GTO approximations for common stats
    gto_approx = {
        "vpip": 22,  # Approximate GTO VPIP for 6-max
        "pfr": 18,
        "three_bet": 8,
        "fold_to_3bet": 55,
        "steal": 40,  # BTN + CO + SB
        "cbet_flop": 65
    }

    deviations = []

    if player.vpip_pct:
        diff = float(player.vpip_pct) - gto_approx["vpip"]
        if abs(diff) > 5:
            deviations.append({
                "stat": "VPIP",
                "player": round(float(player.vpip_pct), 1),
                "gto_approx": gto_approx["vpip"],
                "deviation": round(diff, 1),
                "leak": "Plays too loose" if diff > 0 else "Plays too tight"
            })

    if player.pfr_pct:
        diff = float(player.pfr_pct) - gto_approx["pfr"]
        if abs(diff) > 4:
            deviations.append({
                "stat": "PFR",
                "player": round(float(player.pfr_pct), 1),
                "gto_approx": gto_approx["pfr"],
                "deviation": round(diff, 1),
                "leak": "Too aggressive preflop" if diff > 0 else "Too passive preflop"
            })

    if player.three_bet_pct:
        diff = float(player.three_bet_pct) - gto_approx["three_bet"]
        if abs(diff) > 3:
            deviations.append({
                "stat": "3-bet",
                "player": round(float(player.three_bet_pct), 1),
                "gto_approx": gto_approx["three_bet"],
                "deviation": round(diff, 1),
                "leak": "3-bets too much" if diff > 0 else "3-bets too little (exploitable)"
            })

    if player.fold_to_three_bet_pct:
        diff = float(player.fold_to_three_bet_pct) - gto_approx["fold_to_3bet"]
        if abs(diff) > 8:
            deviations.append({
                "stat": "Fold to 3-bet",
                "player": round(float(player.fold_to_three_bet_pct), 1),
                "gto_approx": gto_approx["fold_to_3bet"],
                "deviation": round(diff, 1),
                "leak": "Overfolds to 3-bets (bluff more)" if diff > 0 else "Underfolds (value bet wider)"
            })

    if player.cbet_flop_pct:
        diff = float(player.cbet_flop_pct) - gto_approx["cbet_flop"]
        if abs(diff) > 10:
            deviations.append({
                "stat": "Flop C-bet",
                "player": round(float(player.cbet_flop_pct), 1),
                "gto_approx": gto_approx["cbet_flop"],
                "deviation": round(diff, 1),
                "leak": "C-bets too much (raise/float more)" if diff > 0 else "C-bets too little (can stab more)"
            })

    return json.dumps({
        "player_name": player_name,
        "total_hands": player.total_hands,
        "significant_deviations": deviations,
        "deviation_count": len(deviations),
        "exploitability": "High" if len(deviations) >= 3 else "Medium" if len(deviations) >= 1 else "Low"
    })
