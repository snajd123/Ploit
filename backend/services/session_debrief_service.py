"""
Session Debrief Service

AI-powered session analysis from GTO and exploitative perspectives.
Uses ONLY data from our database - no AI assumptions.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging
import anthropic
import os

from backend.services.hero_gto_analyzer import HeroGTOAnalyzer
from backend.services.stats_calculator import StatsCalculator

logger = logging.getLogger(__name__)

# Confidence tiers based on sample size
CONFIDENCE_TIERS = {
    "insufficient": {"min": 0, "max": 30, "label": "Insufficient", "language": "Observation only - insufficient data"},
    "low": {"min": 30, "max": 100, "label": "Low", "language": "Preliminary pattern - may be variance"},
    "moderate": {"min": 100, "max": 300, "label": "Moderate", "language": "Emerging trend - worth monitoring"},
    "good": {"min": 300, "max": 1000, "label": "Good", "language": "Identified tendency"},
    "high": {"min": 1000, "max": float('inf'), "label": "High", "language": "Confirmed pattern"}
}


def get_confidence_tier(sample_size: int) -> Dict[str, str]:
    """Get confidence tier based on sample size."""
    for tier_name, tier in CONFIDENCE_TIERS.items():
        if tier["min"] <= sample_size < tier["max"]:
            return {"tier": tier_name, "label": tier["label"], "language": tier["language"]}
    return {"tier": "insufficient", "label": "Insufficient", "language": "Observation only"}


def get_gto_baselines(db: Session) -> Dict[str, Any]:
    """Get GTO baselines calculated from actual database data."""
    baselines = {}

    try:
        # GTO VPIP/PFR: Average of all opening ranges
        open_result = db.execute(text("""
            SELECT AVG(gto_aggregate_freq) as avg_open
            FROM gto_scenarios WHERE action = 'open' AND gto_aggregate_freq IS NOT NULL
        """)).fetchone()
        if open_result and open_result.avg_open:
            baselines["vpip"] = round(float(open_result.avg_open) * 100, 1)
            baselines["pfr"] = baselines["vpip"]

        # GTO 3-bet
        three_bet_result = db.execute(text("""
            SELECT AVG(gto_aggregate_freq) as avg_3bet
            FROM gto_scenarios WHERE action = '3bet' AND gto_aggregate_freq IS NOT NULL
        """)).fetchone()
        if three_bet_result and three_bet_result.avg_3bet:
            baselines["three_bet"] = round(float(three_bet_result.avg_3bet) * 100, 1)

        # GTO Fold to 3-bet (as % of opening range)
        fold_3bet_result = db.execute(text("""
            SELECT AVG(g1.gto_aggregate_freq) as avg_fold, AVG(g2.gto_aggregate_freq) as avg_open
            FROM gto_scenarios g1
            JOIN gto_scenarios g2 ON g2.scenario_name = g1.position || '_open'
            WHERE g1.action = 'fold' AND g1.category = 'facing_3bet'
            AND g1.gto_aggregate_freq IS NOT NULL AND g2.gto_aggregate_freq IS NOT NULL
        """)).fetchone()
        if fold_3bet_result and fold_3bet_result.avg_fold and fold_3bet_result.avg_open:
            gto_fold_pct = (float(fold_3bet_result.avg_fold) / float(fold_3bet_result.avg_open)) * 100
            baselines["fold_to_3bet"] = round(gto_fold_pct, 1)

        # GTO Cold Call
        cold_call_result = db.execute(text("""
            SELECT AVG(gto_aggregate_freq) as avg_cc
            FROM gto_scenarios WHERE action = 'call' AND category = 'defense' AND gto_aggregate_freq IS NOT NULL
        """)).fetchone()
        if cold_call_result and cold_call_result.avg_cc:
            baselines["cold_call"] = round(float(cold_call_result.avg_cc) * 100, 1)

        # GTO Limp (should be 0 or near 0)
        baselines["limp"] = 0.0

    except Exception as e:
        logger.error(f"Error calculating GTO baselines: {e}")

    return baselines


def get_session_metadata(db: Session, session_id: int) -> Optional[Dict[str, Any]]:
    """Get basic session information."""
    result = db.execute(text("""
        SELECT session_id, player_name, start_time, end_time, duration_minutes,
               total_hands, profit_loss_bb, bb_100, table_stakes
        FROM sessions
        WHERE session_id = :session_id
    """), {"session_id": session_id}).fetchone()

    if not result:
        return None

    return {
        "session_id": result.session_id,
        "player_name": result.player_name,
        "start_time": result.start_time.isoformat() if result.start_time else None,
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "duration_minutes": result.duration_minutes,
        "total_hands": result.total_hands,
        "profit_loss_bb": float(result.profit_loss_bb) if result.profit_loss_bb else 0,
        "bb_100": float(result.bb_100) if result.bb_100 else 0,
        "stake_level": result.table_stakes
    }


def get_hero_session_stats(db: Session, session_id: int) -> Dict[str, Any]:
    """Calculate hero's preflop stats for this session with sample sizes."""
    # Get hero name from session
    session_result = db.execute(text("""
        SELECT player_name FROM sessions WHERE session_id = :session_id
    """), {"session_id": session_id}).fetchone()

    if not session_result:
        return {"error": "Session not found"}

    hero_name = session_result.player_name

    result = db.execute(text("""
        SELECT
            COUNT(*) as total_hands,
            SUM(CASE WHEN vpip THEN 1 ELSE 0 END) as vpip_count,
            SUM(CASE WHEN pfr THEN 1 ELSE 0 END) as pfr_count,
            SUM(CASE WHEN made_three_bet THEN 1 ELSE 0 END) as three_bet_count,
            SUM(CASE WHEN three_bet_opportunity THEN 1 ELSE 0 END) as three_bet_opps,
            SUM(CASE WHEN folded_to_three_bet THEN 1 ELSE 0 END) as fold_to_3bet_count,
            SUM(CASE WHEN faced_three_bet THEN 1 ELSE 0 END) as facing_3bet_opps,
            SUM(CASE WHEN cold_call THEN 1 ELSE 0 END) as cold_call_count,
            SUM(CASE WHEN faced_raise AND NOT pfr THEN 1 ELSE 0 END) as cold_call_opps,
            SUM(CASE WHEN limp THEN 1 ELSE 0 END) as limp_count,
            SUM(CASE WHEN pot_unopened THEN 1 ELSE 0 END) as open_opps,
            SUM(CASE WHEN four_bet THEN 1 ELSE 0 END) as four_bet_count,
            SUM(CASE WHEN faced_three_bet THEN 1 ELSE 0 END) as four_bet_opps
        FROM player_hand_summary
        WHERE session_id = :session_id AND player_name = :hero_name
    """), {"session_id": session_id, "hero_name": hero_name}).fetchone()

    if not result or not result.total_hands:
        return {"error": "No hands found for session"}

    stats = {
        "total_hands": result.total_hands,
        "vpip": {
            "value": round(result.vpip_count / result.total_hands * 100, 1) if result.total_hands > 0 else 0,
            "sample": result.total_hands,
            "count": result.vpip_count
        },
        "pfr": {
            "value": round(result.pfr_count / result.total_hands * 100, 1) if result.total_hands > 0 else 0,
            "sample": result.total_hands,
            "count": result.pfr_count
        },
        "three_bet": {
            "value": round(result.three_bet_count / result.three_bet_opps * 100, 1) if result.three_bet_opps > 0 else 0,
            "sample": result.three_bet_opps or 0,
            "count": result.three_bet_count or 0
        },
        "fold_to_3bet": {
            "value": round(result.fold_to_3bet_count / result.facing_3bet_opps * 100, 1) if result.facing_3bet_opps > 0 else 0,
            "sample": result.facing_3bet_opps or 0,
            "count": result.fold_to_3bet_count or 0
        },
        "cold_call": {
            "value": round(result.cold_call_count / result.cold_call_opps * 100, 1) if result.cold_call_opps > 0 else 0,
            "sample": result.cold_call_opps or 0,
            "count": result.cold_call_count or 0
        },
        "limp": {
            "value": round(result.limp_count / result.open_opps * 100, 1) if result.open_opps > 0 else 0,
            "sample": result.open_opps or 0,
            "count": result.limp_count or 0
        },
        "four_bet": {
            "value": round(result.four_bet_count / result.four_bet_opps * 100, 1) if result.four_bet_opps > 0 else 0,
            "sample": result.four_bet_opps or 0,
            "count": result.four_bet_count or 0
        }
    }

    # Add confidence tiers
    for stat_name in ["vpip", "pfr", "three_bet", "fold_to_3bet", "cold_call", "limp", "four_bet"]:
        stats[stat_name]["confidence"] = get_confidence_tier(stats[stat_name]["sample"])

    return stats


def get_session_gto_mistakes(db: Session, session_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get GTO mistakes by running the analyzer."""
    try:
        analyzer = HeroGTOAnalyzer(db)
        analysis = analyzer.analyze_session(session_id)

        biggest_mistakes = analysis.get("biggest_mistakes", [])

        # Map to expected format
        mistakes = []
        for m in biggest_mistakes[:limit]:
            hand_id = m.get("hand_id")
            mistakes.append({
                "hand_id": hand_id,
                "hand_number": str(hand_id) if hand_id else "Unknown",
                "scenario": m.get("scenario", ""),
                "hero_action": m.get("action_taken", ""),
                "gto_action": m.get("gto_action", ""),
                "gto_frequency": m.get("gto_frequency"),
                "ev_loss_bb": m.get("ev_loss_bb", 0),
                "severity": m.get("mistake_severity", ""),
                "explanation": f"{m.get('hero_hand', '')} from {m.get('position', '')}"
            })

        return mistakes
    except Exception as e:
        logger.error(f"Error analyzing GTO mistakes: {e}")
        return []


def get_session_opponents(db: Session, session_id: int) -> List[Dict[str, Any]]:
    """Get opponents from this session with their database stats."""
    # Get hero name from session
    session_result = db.execute(text("""
        SELECT player_name FROM sessions WHERE session_id = :session_id
    """), {"session_id": session_id}).fetchone()

    if not session_result:
        return []

    hero_name = session_result.player_name

    # Get unique opponents from session (excluding hero)
    session_opponents = db.execute(text("""
        SELECT DISTINCT player_name
        FROM player_hand_summary
        WHERE session_id = :session_id AND player_name != :hero_name
    """), {"session_id": session_id, "hero_name": hero_name}).fetchall()

    opponents = []
    for row in session_opponents:
        player_name = row.player_name

        # Get their database stats
        stats_result = db.execute(text("""
            SELECT
                total_hands, vpip_pct, pfr_pct, three_bet_pct,
                fold_to_three_bet_pct, cold_call_pct, limp_pct,
                steal_attempt_pct, fold_to_steal_pct, player_type
            FROM player_stats
            WHERE player_name = :player_name
        """), {"player_name": player_name}).fetchone()

        # Get hands in this session
        session_hands = db.execute(text("""
            SELECT COUNT(*) as hands
            FROM player_hand_summary
            WHERE session_id = :session_id AND player_name = :player_name
        """), {"session_id": session_id, "player_name": player_name}).fetchone()

        opponent_data = {
            "name": player_name,
            "hands_in_session": session_hands.hands if session_hands else 0,
            "db_total_hands": 0,
            "stats": None,
            "confidence": get_confidence_tier(0)
        }

        if stats_result and stats_result.total_hands:
            opponent_data["db_total_hands"] = stats_result.total_hands
            opponent_data["confidence"] = get_confidence_tier(stats_result.total_hands)
            opponent_data["stats"] = {
                "vpip": float(stats_result.vpip_pct) if stats_result.vpip_pct else None,
                "pfr": float(stats_result.pfr_pct) if stats_result.pfr_pct else None,
                "three_bet": float(stats_result.three_bet_pct) if stats_result.three_bet_pct else None,
                "fold_to_3bet": float(stats_result.fold_to_three_bet_pct) if stats_result.fold_to_three_bet_pct else None,
                "cold_call": float(stats_result.cold_call_pct) if stats_result.cold_call_pct else None,
                "limp": float(stats_result.limp_pct) if stats_result.limp_pct else None,
                "player_type": stats_result.player_type
            }

        opponents.append(opponent_data)

    # Sort by database hands (most data first)
    opponents.sort(key=lambda x: x["db_total_hands"], reverse=True)
    return opponents


def classify_exploit(
    hero_action: str,
    gto_action: str,
    gto_frequency: float,
    opponent_stats: Optional[Dict],
    opponent_sample: int
) -> Dict[str, Any]:
    """
    Classify a GTO deviation as mistake, potential exploit, or validated exploit.
    """
    # If actions match or GTO is mixed (30-70%), it's acceptable
    if hero_action == gto_action:
        return {"classification": "gto_compliant"}

    if gto_frequency and 0.30 <= gto_frequency <= 0.70:
        return {"classification": "acceptable_mixed", "note": "GTO plays mixed strategy here"}

    # No opponent data - it's a GTO mistake
    if opponent_stats is None or opponent_sample < 30:
        return {
            "classification": "gto_mistake",
            "reason": f"Insufficient opponent data ({opponent_sample} hands)"
        }

    # Check if opponent tendency justifies deviation
    # Map hero actions to relevant opponent stats
    exploit_mappings = {
        "fold_vs_3bet": "fold_to_3bet",  # If opponent folds a lot to 3bet, hero should 3bet bluff more
        "3bet_bluff": "fold_to_3bet",
        "call_vs_3bet": "three_bet",  # If opponent 3bets wide, hero should call/4bet more
        "fold_vs_cbet": "cbet_flop",
    }

    # Simplified logic - check fold_to_3bet for now
    if opponent_stats.get("fold_to_3bet") and opponent_stats["fold_to_3bet"] > 65:
        if opponent_sample >= 100:
            return {
                "classification": "validated_exploit",
                "opponent_tendency": f"Folds {opponent_stats['fold_to_3bet']:.1f}% to 3-bet",
                "confidence": "high" if opponent_sample >= 300 else "moderate"
            }
        else:
            return {
                "classification": "potential_exploit",
                "opponent_tendency": f"Folds {opponent_stats['fold_to_3bet']:.1f}% to 3-bet",
                "confidence": "low",
                "note": f"Need {100 - opponent_sample} more hands to confirm"
            }

    return {"classification": "gto_mistake", "reason": "No exploitable tendency identified"}


def find_missed_opportunities(
    db: Session,
    session_id: int,
    opponents: List[Dict[str, Any]],
    gto_baselines: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Find spots where hero played GTO but could have exploited."""
    missed = []

    # Get hero name from session
    session_result = db.execute(text("""
        SELECT player_name FROM sessions WHERE session_id = :session_id
    """), {"session_id": session_id}).fetchone()

    if not session_result:
        return missed

    hero_name = session_result.player_name

    # Find opponents with exploitable tendencies (100+ hands)
    exploitable_opponents = {
        opp["name"]: opp for opp in opponents
        if opp["db_total_hands"] >= 100 and opp["stats"]
    }

    if not exploitable_opponents:
        return missed

    gto_vpip = gto_baselines.get("vpip", 22)
    gto_pfr = gto_baselines.get("pfr", 18)
    gto_f3b = gto_baselines.get("fold_to_3bet", 52)
    gto_3bet = gto_baselines.get("three_bet", 7)

    for opp_name, opp_data in exploitable_opponents.items():
        stats = opp_data["stats"]
        if not stats:
            continue

        # 1. Missed 3-bet bluff vs overfolders
        if stats.get("fold_to_3bet") and stats["fold_to_3bet"] > gto_f3b + 15:
            hands = db.execute(text("""
                SELECT phs.hand_id
                FROM player_hand_summary phs
                WHERE phs.session_id = :session_id
                AND phs.player_name = :hero_name
                AND phs.cold_call = true
                AND EXISTS (
                    SELECT 1 FROM player_hand_summary opp
                    WHERE opp.hand_id = phs.hand_id
                    AND opp.player_name = :opp_name
                    AND opp.pfr = true
                )
                LIMIT 2
            """), {"session_id": session_id, "hero_name": hero_name, "opp_name": opp_name}).fetchall()

            for hand in hands:
                missed.append({
                    "hand_id": hand.hand_id,
                    "hand_number": str(hand.hand_id),
                    "opponent": opp_name,
                    "opportunity": "3-bet bluff",
                    "opponent_tendency": f"Folds {stats['fold_to_3bet']:.1f}% to 3-bet (GTO: {gto_f3b}%)",
                    "opponent_sample": opp_data["db_total_hands"],
                    "hero_action": "Called",
                    "confidence": opp_data["confidence"]["label"]
                })

        # 2. Calling station detection - value bet thinner
        if stats.get("vpip") and stats["vpip"] > gto_vpip + 20:
            missed.append({
                "hand_id": None,
                "hand_number": "General",
                "opponent": opp_name,
                "opportunity": "Value bet thinner",
                "opponent_tendency": f"VPIP {stats['vpip']:.1f}% (GTO: {gto_vpip}%) - calling station",
                "opponent_sample": opp_data["db_total_hands"],
                "hero_action": "Consider wider value range",
                "confidence": opp_data["confidence"]["label"]
            })

        # 3. Nit detection - steal more / bluff more
        if stats.get("vpip") and stats["vpip"] < gto_vpip - 10:
            pfr_val = stats.get("pfr", 0)
            missed.append({
                "hand_id": None,
                "hand_number": "General",
                "opponent": opp_name,
                "opportunity": "Steal / bluff more",
                "opponent_tendency": f"VPIP {stats['vpip']:.1f}%, PFR {pfr_val:.1f}% - tight/nitty player",
                "opponent_sample": opp_data["db_total_hands"],
                "hero_action": "Attack their blinds, bluff more",
                "confidence": opp_data["confidence"]["label"]
            })

        # 4. Over-aggressive 3-bettor - widen 4-bet range or call more
        if stats.get("three_bet") and stats["three_bet"] > gto_3bet + 5:
            missed.append({
                "hand_id": None,
                "hand_number": "General",
                "opponent": opp_name,
                "opportunity": "Defend vs aggressive 3-bettor",
                "opponent_tendency": f"3-bet {stats['three_bet']:.1f}% (GTO: {gto_3bet}%) - likely over-bluffing",
                "opponent_sample": opp_data["db_total_hands"],
                "hero_action": "4-bet bluff more, call wider",
                "confidence": opp_data["confidence"]["label"]
            })

        # 5. Tight 3-bettor - fold more vs their 3-bets
        if stats.get("three_bet") and stats["three_bet"] < gto_3bet - 3:
            missed.append({
                "hand_id": None,
                "hand_number": "General",
                "opponent": opp_name,
                "opportunity": "Respect tight 3-bets",
                "opponent_tendency": f"3-bet only {stats['three_bet']:.1f}% (GTO: {gto_3bet}%) - value-heavy",
                "opponent_sample": opp_data["db_total_hands"],
                "hero_action": "Fold more marginal hands vs their 3-bet",
                "confidence": opp_data["confidence"]["label"]
            })

    return missed[:8]  # Limit to top 8


def get_session_strategy(db: Session, session_id: int) -> Optional[Dict[str, Any]]:
    """Get pre-game strategy that was generated for this session (if any).

    Links strategy to session by checking if the strategy's hand_id belongs to this session.
    """
    # Find strategy where the hand_id is in this session
    strategy_result = db.execute(text("""
        SELECT ps.id, ps.created_at, ps.strategy, ps.opponents,
               ps.table_classification, ps.softness_score, ps.hand_id
        FROM pregame_strategies ps
        JOIN raw_hands rh ON ps.hand_id = rh.hand_id
        WHERE rh.session_id = :session_id
        ORDER BY ps.created_at DESC
        LIMIT 1
    """), {"session_id": session_id}).fetchone()

    if not strategy_result:
        return None

    try:
        strategy_data = json.loads(strategy_result.strategy) if isinstance(strategy_result.strategy, str) else strategy_result.strategy
        opponents_data = json.loads(strategy_result.opponents) if isinstance(strategy_result.opponents, str) else strategy_result.opponents

        return {
            "strategy_id": strategy_result.id,
            "created_at": strategy_result.created_at.isoformat() if strategy_result.created_at else None,
            "table_classification": strategy_result.table_classification,
            "softness_score": float(strategy_result.softness_score) if strategy_result.softness_score else None,
            "general_strategy": strategy_data.get("general_strategy", {}),
            "opponent_exploits": strategy_data.get("opponent_exploits", []),
            "priority_actions": strategy_data.get("priority_actions", []),
            "opponents_snapshot": opponents_data
        }
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error parsing strategy data: {e}")
        return None


def get_hero_lifetime_priority_leaks(db: Session, hero_name: str) -> List[Dict[str, Any]]:
    """
    Get hero's lifetime priority leaks using the same scenario-based analysis as My Game.
    This returns the same data structure as the My Game GTO Analysis priority_leaks.

    Uses lower sample thresholds than My Game since we're comparing session trends,
    not making absolute claims about leaks.
    """
    from backend.services.priority_scoring import (
        get_leak_severity, get_leak_weight, calculate_priority_score
    )
    from backend.services.hero_detection import get_hero_nicknames

    # Use ALL configured hero nicknames (same as My Game), not just session player_name
    configured_nicknames = get_hero_nicknames(db)
    if configured_nicknames:
        hero_nicknames = list(configured_nicknames)
    else:
        # Fallback to session player_name if no nicknames configured
        hero_nicknames = [hero_name.lower()]

    # Get GTO frequencies for scenarios
    gto_opening_result = db.execute(text("""
        SELECT position, SUM(gto_aggregate_freq) as gto_aggregate_freq
        FROM gto_scenarios WHERE category = 'opening'
        GROUP BY position
    """))
    gto_opening = {row[0]: float(row[1]) * 100 if row[1] else 0 for row in gto_opening_result}

    gto_defense_result = db.execute(text("""
        SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
        FROM gto_scenarios
        WHERE category = 'defense' AND action IN ('call', '3bet')
        GROUP BY position, action
    """))
    gto_defense = {}
    for row in gto_defense_result:
        pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
        if pos not in gto_defense:
            gto_defense[pos] = {}
        gto_defense[pos][action] = freq

    gto_f3bet_result = db.execute(text("""
        SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
        FROM gto_scenarios
        WHERE category = 'facing_3bet' AND action IN ('fold', 'call', '4bet')
        GROUP BY position, action
    """))
    gto_f3bet = {}
    for row in gto_f3bet_result:
        pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
        if pos not in gto_f3bet:
            gto_f3bet[pos] = {}
        gto_f3bet[pos][action] = freq

    # Build GTO data structure similar to My Game
    gto_data = {"opening_ranges": [], "defense_vs_open": [], "facing_3bet": []}

    # 1. Opening ranges
    opening_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE pot_unopened = true) as rfi_opportunities,
            ROUND(100.0 * COUNT(*) FILTER (WHERE pfr = true AND pot_unopened = true) /
                NULLIF(COUNT(*) FILTER (WHERE pot_unopened = true), 0), 1) as player_open_pct
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames) AND position IS NOT NULL AND position NOT IN ('BB')
        GROUP BY position HAVING COUNT(*) FILTER (WHERE pot_unopened = true) >= 10
    """), {"nicknames": hero_nicknames})

    for row in opening_result:
        pos = row[0]
        player_freq = float(row[2]) if row[2] else 0
        gto_freq = gto_opening.get(pos, 0)
        gto_data["opening_ranges"].append({
            'position': pos,
            'total_hands': row[1],
            'player_frequency': player_freq,
            'gto_frequency': round(gto_freq, 1),
            'frequency_diff': round(player_freq - gto_freq, 1),
        })

    # 2. Defense vs opens
    defense_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) as folded,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) as called,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) as three_bets,
            ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) /
                NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as fold_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) /
                NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as call_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as three_bet_pct
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames) AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position HAVING COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) >= 5
    """), {"nicknames": hero_nicknames})

    for row in defense_result:
        pos = row[0]
        fold_freq = float(row[5]) if row[5] else 0
        call_freq = float(row[6]) if row[6] else 0
        threebet_freq = float(row[7]) if row[7] else 0
        gto_call = gto_defense.get(pos, {}).get('call', 15)
        gto_3bet = gto_defense.get(pos, {}).get('3bet', 8)
        gto_fold = 100 - gto_call - gto_3bet

        gto_data["defense_vs_open"].append({
            'position': pos,
            'sample_size': row[1],
            'fold_count': row[2], 'call_count': row[3], '3bet_count': row[4],
            'player_fold': round(fold_freq, 1), 'player_call': round(call_freq, 1), 'player_3bet': round(threebet_freq, 1),
            'gto_fold': round(gto_fold, 1), 'gto_call': round(gto_call, 1), 'gto_3bet': round(gto_3bet, 1),
            'fold_diff': round(fold_freq - gto_fold, 1),
            'call_diff': round(call_freq - gto_call, 1),
            '3bet_diff': round(threebet_freq - gto_3bet, 1),
        })

    # 3. Facing 3-bet
    f3bet_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
            COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) as folded,
            COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) as called,
            COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) as four_bet,
            ROUND(100.0 * COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as fold_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as call_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as four_bet_pct
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames) AND position IS NOT NULL
        GROUP BY position HAVING COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) >= 5
    """), {"nicknames": hero_nicknames})

    for row in f3bet_result:
        pos = row[0]
        fold = float(row[5]) if row[5] else 0
        call = float(row[6]) if row[6] else 0
        four_bet = float(row[7]) if row[7] else 0
        gto_fold = gto_f3bet.get(pos, {}).get('fold', 55)
        gto_call = gto_f3bet.get(pos, {}).get('call', 35)
        gto_4bet = gto_f3bet.get(pos, {}).get('4bet', 10)

        gto_data["facing_3bet"].append({
            'position': pos,
            'sample_size': row[1],
            'fold_count': row[2], 'call_count': row[3], '4bet_count': row[4],
            'player_fold': round(fold, 1), 'player_call': round(call, 1), 'player_4bet': round(four_bet, 1),
            'gto_fold': round(gto_fold, 1), 'gto_call': round(gto_call, 1), 'gto_4bet': round(gto_4bet, 1),
            'fold_diff': round(fold - gto_fold, 1),
            'call_diff': round(call - gto_call, 1),
            '4bet_diff': round(four_bet - gto_4bet, 1),
        })

    # Build priority leaks with lower thresholds for debrief
    # Lower sample (15 instead of 100) and deviation (5% instead of 8%) thresholds
    # This allows showing progress on borderline leaks, not just major ones
    DEBRIEF_MIN_SAMPLE = 15
    DEBRIEF_LEAK_THRESHOLD = 5  # 5% deviation to be considered a leak (vs 8% in My Game)

    def get_confidence(sample: int) -> str:
        if sample < DEBRIEF_MIN_SAMPLE:
            return "insufficient"
        elif sample < 50:
            return "low"
        elif sample < 100:
            return "moderate"
        else:
            return "high"

    def is_leak_for_debrief(deviation: float) -> bool:
        return abs(deviation) >= DEBRIEF_LEAK_THRESHOLD

    scenarios = []

    # 1. Opening ranges
    for r in gto_data.get('opening_ranges', []):
        pos = r.get('position', '')
        deviation = r.get('frequency_diff', 0)
        sample = r.get('total_hands', 0)
        severity = get_leak_severity(deviation)
        is_leak = is_leak_for_debrief(deviation)  # Use lower threshold for debrief

        scenario = {
            'scenario_id': f"opening_{pos}",
            'category': 'opening',
            'position': pos,
            'action': 'open',
            'display_name': f"{pos} Open (RFI)",
            'overall_value': r.get('player_frequency', 0),
            'overall_sample': sample,
            'overall_deviation': deviation,
            'gto_value': r.get('gto_frequency', 0),
            'is_leak': is_leak,
            'leak_severity': severity if severity != 'none' else 'minor',  # At least minor if is_leak
            'leak_direction': 'too_loose' if deviation > DEBRIEF_LEAK_THRESHOLD else 'too_tight' if deviation < -DEBRIEF_LEAK_THRESHOLD else None,
            'confidence_level': get_confidence(sample),
            'ev_weight': get_leak_weight(f"opening_{pos}"),
        }
        scenario['priority_score'] = calculate_priority_score(scenario)
        scenarios.append(scenario)

    # 2. Defense vs opens
    for r in gto_data.get('defense_vs_open', []):
        pos = r.get('position', '')
        total_sample = r.get('sample_size', 0)

        for action, player_key, gto_key, diff_key in [
            ('fold', 'player_fold', 'gto_fold', 'fold_diff'),
            ('call', 'player_call', 'gto_call', 'call_diff'),
            ('3bet', 'player_3bet', 'gto_3bet', '3bet_diff'),
        ]:
            deviation = r.get(diff_key, 0)
            severity = get_leak_severity(deviation)
            is_leak = is_leak_for_debrief(deviation)  # Use lower threshold for debrief
            scenario = {
                'scenario_id': f"defense_{pos}_{action}",
                'category': 'defense',
                'position': pos,
                'action': action,
                'display_name': f"{action.capitalize()} in {pos}",
                'overall_value': r.get(player_key, 0),
                'overall_sample': total_sample,
                'overall_deviation': deviation,
                'gto_value': r.get(gto_key, 0),
                'is_leak': is_leak,
                'leak_severity': severity if severity != 'none' else 'minor',  # At least minor if is_leak
                'leak_direction': 'too_high' if deviation > DEBRIEF_LEAK_THRESHOLD else 'too_low' if deviation < -DEBRIEF_LEAK_THRESHOLD else None,
                'confidence_level': get_confidence(total_sample),
                'ev_weight': get_leak_weight(f"defense_{pos}_{action}"),
            }
            scenario['priority_score'] = calculate_priority_score(scenario)
            scenarios.append(scenario)

    # 3. Facing 3-bet
    for r in gto_data.get('facing_3bet', []):
        pos = r.get('position', '')
        total_sample = r.get('sample_size', 0)

        for action, player_key, gto_key, diff_key in [
            ('fold', 'player_fold', 'gto_fold', 'fold_diff'),
            ('call', 'player_call', 'gto_call', 'call_diff'),
            ('4bet', 'player_4bet', 'gto_4bet', '4bet_diff'),
        ]:
            deviation = r.get(diff_key, 0)
            severity = get_leak_severity(deviation)
            is_leak = is_leak_for_debrief(deviation)  # Use lower threshold for debrief
            scenario = {
                'scenario_id': f"facing_3bet_{pos}_{action}",
                'category': 'facing_3bet',
                'position': pos,
                'action': action,
                'display_name': f"{action.capitalize()} 3-Bet in {pos}",
                'overall_value': r.get(player_key, 0),
                'overall_sample': total_sample,
                'overall_deviation': deviation,
                'gto_value': r.get(gto_key, 0),
                'is_leak': is_leak,
                'leak_severity': severity if severity != 'none' else 'minor',  # At least minor if is_leak
                'leak_direction': 'too_high' if deviation > DEBRIEF_LEAK_THRESHOLD else 'too_low' if deviation < -DEBRIEF_LEAK_THRESHOLD else None,
                'confidence_level': get_confidence(total_sample),
                'ev_weight': get_leak_weight(f"facing_3bet_{pos}_{action}"),
            }
            scenario['priority_score'] = calculate_priority_score(scenario)
            scenarios.append(scenario)

    # Filter to leaks only and sort by priority
    leaks_only = [
        s for s in scenarios
        if s.get('is_leak')
        and s.get('priority_score', 0) > 0
        and s.get('confidence_level') != 'insufficient'
    ]
    priority_leaks = sorted(leaks_only, key=lambda x: x.get('priority_score', 0), reverse=True)

    return priority_leaks


def get_session_scenario_stats(db: Session, session_id: int, hero_name: str) -> Dict[str, Dict[str, float]]:
    """
    Get session-specific stats for each scenario (opening, defense, facing_3bet).
    Returns a dict keyed by scenario_id with session values.
    """
    session_stats = {}

    # 1. Opening ranges by position
    opening_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE pot_unopened = true) as rfi_opportunities,
            ROUND(100.0 * COUNT(*) FILTER (WHERE pfr = true AND pot_unopened = true) /
                NULLIF(COUNT(*) FILTER (WHERE pot_unopened = true), 0), 1) as player_open_pct
        FROM player_hand_summary
        WHERE session_id = :session_id AND player_name = :hero_name
        AND position IS NOT NULL AND position NOT IN ('BB')
        GROUP BY position
    """), {"session_id": session_id, "hero_name": hero_name})

    for row in opening_result:
        pos, sample, value = row[0], row[1] or 0, float(row[2]) if row[2] else 0
        session_stats[f"opening_{pos}"] = {"value": value, "sample": sample}

    # 2. Defense vs opens by position
    defense_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
            ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) /
                NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as fold_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) /
                NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as call_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as three_bet_pct
        FROM player_hand_summary
        WHERE session_id = :session_id AND player_name = :hero_name
        AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position
    """), {"session_id": session_id, "hero_name": hero_name})

    for row in defense_result:
        pos = row[0]
        sample = row[1] or 0
        session_stats[f"defense_{pos}_fold"] = {"value": float(row[2]) if row[2] else 0, "sample": sample}
        session_stats[f"defense_{pos}_call"] = {"value": float(row[3]) if row[3] else 0, "sample": sample}
        session_stats[f"defense_{pos}_3bet"] = {"value": float(row[4]) if row[4] else 0, "sample": sample}

    # 3. Facing 3-bet by position
    f3bet_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
            ROUND(100.0 * COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as fold_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as call_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) /
                NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as four_bet_pct
        FROM player_hand_summary
        WHERE session_id = :session_id AND player_name = :hero_name AND position IS NOT NULL
        GROUP BY position
    """), {"session_id": session_id, "hero_name": hero_name})

    for row in f3bet_result:
        pos = row[0]
        sample = row[1] or 0
        session_stats[f"facing_3bet_{pos}_fold"] = {"value": float(row[2]) if row[2] else 0, "sample": sample}
        session_stats[f"facing_3bet_{pos}_call"] = {"value": float(row[3]) if row[3] else 0, "sample": sample}
        session_stats[f"facing_3bet_{pos}_4bet"] = {"value": float(row[4]) if row[4] else 0, "sample": sample}

    return session_stats


def analyze_leak_progress(
    db: Session,
    session_id: int,
    hero_name: str,
    lifetime_priority_leaks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Compare session performance to lifetime priority leaks from GTO analysis.
    Uses the same scenario-based analysis as My Game.
    """
    if not lifetime_priority_leaks:
        return []

    # Get session-specific scenario stats
    session_stats = get_session_scenario_stats(db, session_id, hero_name)

    progress = []

    # Compare ALL lifetime priority leaks to session performance
    # (don't limit to top 10 - include all leaks where session data exists)
    for leak in lifetime_priority_leaks:
        scenario_id = leak.get("scenario_id", "")
        session_data = session_stats.get(scenario_id)

        if not session_data or session_data["sample"] < 1:
            # No session data for this scenario
            continue

        session_value = session_data["value"]
        session_sample = session_data["sample"]
        lifetime_value = leak.get("overall_value", 0)
        gto_value = leak.get("gto_value", 0)
        leak_direction = leak.get("leak_direction", "")  # "too_high", "too_low", "too_loose", "too_tight"

        # Determine if session shows improvement (closer to GTO than lifetime)
        session_deviation = abs(session_value - gto_value)
        lifetime_deviation = abs(lifetime_value - gto_value)
        closer_to_gto = session_deviation < lifetime_deviation

        # Determine if going in the right direction based on leak type
        if leak_direction in ["too_high", "too_loose"]:
            # Player was doing something too much - lower is better
            improved = session_value < lifetime_value
        elif leak_direction in ["too_low", "too_tight"]:
            # Player was doing something too little - higher is better
            improved = session_value > lifetime_value
        else:
            improved = closer_to_gto

        progress.append({
            "scenario_id": scenario_id,
            "leak_name": leak.get("display_name", scenario_id),
            "category": leak.get("category", ""),
            "position": leak.get("position", ""),
            "action": leak.get("action", ""),
            "lifetime_value": lifetime_value,
            "session_value": session_value,
            "gto_value": gto_value,
            "session_sample": session_sample,
            "lifetime_sample": leak.get("overall_sample", 0),
            "improved": improved,
            "closer_to_gto": closer_to_gto,
            "severity": leak.get("leak_severity", "moderate"),
            "direction": leak_direction,
            "priority_score": leak.get("priority_score", 0)
        })

    # Sort by priority score (highest first)
    progress.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    return progress


def generate_ai_debrief(
    session_meta: Dict[str, Any],
    hero_stats: Dict[str, Any],
    gto_baselines: Dict[str, Any],
    gto_mistakes: List[Dict[str, Any]],
    opponents: List[Dict[str, Any]],
    missed_opportunities: List[Dict[str, Any]],
    pregame_strategy: Optional[Dict[str, Any]] = None,
    leak_progress: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Generate AI debrief using single-shot approach with all data."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Format hero stats with sample sizes
    hero_stats_text = ""
    for stat_name in ["vpip", "pfr", "three_bet", "fold_to_3bet", "cold_call", "limp"]:
        if stat_name in hero_stats:
            s = hero_stats[stat_name]
            hero_stats_text += f"  {stat_name.upper()}: {s['value']}% ({s['count']}/{s['sample']} - {s['confidence']['label']} confidence)\n"

    # Format GTO baselines
    gto_text = "\n".join([f"  {k}: {v}%" for k, v in gto_baselines.items() if v is not None])

    # Format mistakes
    mistakes_text = ""
    for m in gto_mistakes[:5]:
        mistakes_text += f"""
  Hand #{m['hand_number']}: {m['scenario']}
    Hero: {m['hero_action']} | GTO: {m['gto_action']} ({m['gto_frequency']*100 if m['gto_frequency'] else 'N/A'}%)
    EV Loss: {m['ev_loss_bb']:.2f}bb | {m['explanation'] or ''}
"""

    # Format opponents (only those with 50+ hands)
    opponents_text = ""
    for opp in opponents:
        if opp["db_total_hands"] >= 50 and opp["stats"]:
            s = opp["stats"]
            opponents_text += f"""
  {opp['name']} ({opp['db_total_hands']} hands - {opp['confidence']['label']} confidence):
    VPIP: {s.get('vpip', 'N/A')}% | PFR: {s.get('pfr', 'N/A')}% | 3bet: {s.get('three_bet', 'N/A')}%
    Fold to 3bet: {s.get('fold_to_3bet', 'N/A')}% | Type: {s.get('player_type', 'Unknown')}
"""

    # Format missed opportunities
    missed_text = ""
    for m in missed_opportunities:
        missed_text += f"  Hand #{m['hand_number']}: {m['opportunity']} vs {m['opponent']} ({m['opponent_tendency']})\n"

    # Format pre-game strategy if available
    strategy_text = ""
    if pregame_strategy:
        general = pregame_strategy.get("general_strategy", {})
        exploits = pregame_strategy.get("opponent_exploits", [])
        priority = pregame_strategy.get("priority_actions", [])

        strategy_text = f"""
=== PRE-GAME STRATEGY (generated before session) ===
Table Classification: {pregame_strategy.get('table_classification', 'Unknown')}
Softness Score: {pregame_strategy.get('softness_score', 'N/A')}/10

Key Principle: {general.get('key_principle', 'N/A')}
Overview: {general.get('overview', 'N/A')}

Priority Actions:
{chr(10).join(f'  - {a}' for a in priority[:3]) if priority else '  None specified'}

Opponent Exploits Recommended:
{chr(10).join(f'  - {e.get("name", "Unknown")}: {e.get("exploit", "N/A")}' for e in exploits[:5]) if exploits else '  None specified'}
"""

    # Format leak progress if available
    leak_progress_text = ""
    if leak_progress:
        improved = [l for l in leak_progress if l.get("improved")]
        not_improved = [l for l in leak_progress if not l.get("improved")]

        if improved or not_improved:
            leak_progress_text = "\n=== LEAK PROGRESS (vs lifetime stats) ===\n"

            if improved:
                leak_progress_text += "IMPROVED this session:\n"
                for l in improved:
                    leak_progress_text += f"  - {l['leak_name']}: Session {l['session_value']:.1f}% vs Lifetime {l['lifetime_value']:.1f}% (GTO: {l['gto_value']:.1f}%)\n"

            if not_improved:
                leak_progress_text += "NEEDS WORK:\n"
                for l in not_improved:
                    leak_progress_text += f"  - {l['leak_name']}: Session {l['session_value']:.1f}% vs Lifetime {l['lifetime_value']:.1f}% (GTO: {l['gto_value']:.1f}%)\n"

    system_prompt = """You are a professional poker coach providing a session debrief.

CRITICAL RULES:
1. ONLY reference numbers from the data provided - NEVER invent statistics
2. ALWAYS note sample sizes when discussing patterns
3. NEVER claim a "leak" exists from session data alone - use "observation" or "pattern to monitor"
4. Distinguish between GTO mistakes and potential exploitative adjustments
5. For opponent reads, always state the sample size and confidence level
6. Be encouraging but honest about limitations
7. If a pre-game strategy was provided, comment on how well it was executed
8. If leak progress data is provided, acknowledge improvements and areas still needing work

Format your response as JSON with these exact keys:
{
  "executive_summary": "2-3 sentence overview",
  "went_well": ["list of 2-3 things that went well with specific numbers"],
  "areas_for_improvement": ["list of 2-3 areas to work on with specific numbers"],
  "opponent_insights": [{"name": "...", "tendency": "...", "recommendation": "..."}],
  "strategy_execution": "If strategy was provided, brief assessment of execution. Otherwise null.",
  "leak_progress_summary": "If leak data was provided, brief summary of progress. Otherwise null.",
  "study_recommendations": ["1-3 actionable study items"]
}"""

    user_message = f"""Generate a session debrief based on this data:

=== SESSION SUMMARY ===
Hands: {session_meta['total_hands']}
Profit: {session_meta['profit_loss_bb']:.1f}bb ({session_meta['bb_100']:.1f} bb/100)
Duration: {session_meta['duration_minutes']} minutes
Stakes: {session_meta['stake_level']}

=== GTO BASELINES (from database) ===
{gto_text}

=== HERO SESSION STATS (with sample sizes) ===
{hero_stats_text}

=== TOP GTO MISTAKES ===
{mistakes_text if mistakes_text else "No significant GTO mistakes identified"}

=== OPPONENT DATABASE STATS ===
{opponents_text if opponents_text else "No opponents with sufficient data (50+ hands)"}

=== MISSED EXPLOIT OPPORTUNITIES ===
{missed_text if missed_text else "No clear missed opportunities identified"}
{strategy_text}{leak_progress_text}
=== INSTRUCTIONS ===
Generate a constructive debrief. For EVERY number you cite, it must appear in the data above.
Note sample size limitations honestly. Do not claim patterns without sufficient data.
If strategy execution data is available, assess how well the strategy was followed.
If leak progress data is available, acknowledge improvements and remaining work.
Return ONLY valid JSON."""

    logger.info("Generating AI debrief...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )

    response_text = ""
    for block in response.content:
        if hasattr(block, 'text'):
            response_text += block.text

    # Build full prompt for debug output
    full_prompt = f"System: {system_prompt}\n\nUser: {user_message}"

    # Parse JSON response
    try:
        # Clean markdown if present
        clean_response = response_text.strip()
        if clean_response.startswith("```"):
            clean_response = clean_response.split("```")[1]
            if clean_response.startswith("json"):
                clean_response = clean_response[4:]
        clean_response = clean_response.strip()

        ai_analysis = json.loads(clean_response)
        # Return analysis with debug info
        return {
            "analysis": ai_analysis,
            "ai_prompt": full_prompt,
            "ai_response": response_text
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {e}")
        logger.error(f"Response: {response_text[:500]}")
        return {
            "analysis": {
                "executive_summary": "Session analysis completed. Review the detailed stats below.",
                "went_well": ["Session completed"],
                "areas_for_improvement": ["Review hand histories for specific spots"],
                "opponent_insights": [],
                "strategy_execution": None,
                "leak_progress_summary": None,
                "study_recommendations": ["Continue tracking your play"]
            },
            "ai_prompt": full_prompt,
            "ai_response": response_text
        }


def generate_session_debrief(db: Session, session_id: int) -> Dict[str, Any]:
    """Main entry point - generate complete session debrief."""
    logger.info(f"Generating debrief for session {session_id}")

    # 1. Get session metadata
    session_meta = get_session_metadata(db, session_id)
    if not session_meta:
        raise ValueError(f"Session {session_id} not found")

    hero_name = session_meta.get("player_name", "")

    # 2. Get GTO baselines from database
    gto_baselines = get_gto_baselines(db)

    # 3. Get hero's session stats with sample sizes
    hero_stats = get_hero_session_stats(db, session_id)

    # 4. Get existing GTO mistakes
    gto_mistakes = get_session_gto_mistakes(db, session_id)

    # 5. Get opponent stats
    opponents = get_session_opponents(db, session_id)

    # 6. Find missed opportunities
    missed_opportunities = find_missed_opportunities(db, session_id, opponents, gto_baselines)

    # 7. Get pre-game strategy if one was generated for this session
    pregame_strategy = get_session_strategy(db, session_id)

    # 8. Get lifetime priority leaks and analyze session progress (scenario-based)
    lifetime_priority_leaks = get_hero_lifetime_priority_leaks(db, hero_name) if hero_name else []
    leak_progress = analyze_leak_progress(db, session_id, hero_name, lifetime_priority_leaks) if lifetime_priority_leaks else []

    # 9. Generate AI debrief with all data
    ai_result = generate_ai_debrief(
        session_meta=session_meta,
        hero_stats=hero_stats,
        gto_baselines=gto_baselines,
        gto_mistakes=gto_mistakes,
        opponents=opponents,
        missed_opportunities=missed_opportunities,
        pregame_strategy=pregame_strategy,
        leak_progress=leak_progress
    )

    # 10. Compile final response
    return {
        "session_summary": session_meta,
        "gto_analysis": {
            "baselines": gto_baselines,
            "hero_stats": hero_stats,
            "mistakes": gto_mistakes,
            "mistake_count": len(gto_mistakes)
        },
        "exploit_analysis": {
            "missed_opportunities": missed_opportunities
        },
        "opponents": [
            opp for opp in opponents if opp["db_total_hands"] >= 50
        ],
        "pregame_strategy": pregame_strategy,
        "leak_progress": leak_progress,
        "ai_debrief": ai_result.get("analysis", {}),
        "ai_debug": {
            "prompt": ai_result.get("ai_prompt", ""),
            "response": ai_result.get("ai_response", "")
        },
        "disclaimers": {
            "session_sample": f"Based on {session_meta['total_hands']} hands. Session stats have high variance.",
            "gto_comparison": "GTO baselines assume 100bb stacks and standard 6-max play.",
            "opponent_confidence": "Opponent reads require 100+ hands for moderate confidence, 300+ for high confidence.",
            "strategy_note": "Strategy execution assessment is qualitative based on session actions." if pregame_strategy else None,
            "leak_note": "Leak progress comparison uses lifetime stats as baseline." if leak_progress else None
        }
    }


def generate_multi_session_debrief(db: Session, session_ids: List[int]) -> Dict[str, Any]:
    """Generate debrief for multiple sessions combined."""
    # For now, just aggregate the data and generate a single debrief
    # TODO: Implement proper multi-session aggregation
    if len(session_ids) == 1:
        return generate_session_debrief(db, session_ids[0])

    # Get combined stats across sessions
    total_hands = 0
    total_profit = 0
    all_mistakes = []
    all_opponents = {}

    for session_id in session_ids:
        meta = get_session_metadata(db, session_id)
        if meta:
            total_hands += meta["total_hands"]
            total_profit += meta["profit_loss_bb"]

        mistakes = get_session_gto_mistakes(db, session_id, limit=5)
        all_mistakes.extend(mistakes)

        opponents = get_session_opponents(db, session_id)
        for opp in opponents:
            if opp["name"] not in all_opponents:
                all_opponents[opp["name"]] = opp

    # Sort mistakes by EV loss
    all_mistakes.sort(key=lambda x: x.get("ev_loss_bb", 0), reverse=True)

    combined_meta = {
        "session_id": f"combined_{len(session_ids)}",
        "total_hands": total_hands,
        "profit_loss_bb": total_profit,
        "bb_100": (total_profit / total_hands * 100) if total_hands > 0 else 0,
        "duration_minutes": 0,
        "stake_level": "Mixed"
    }

    gto_baselines = get_gto_baselines(db)

    # Generate combined AI debrief
    ai_result = generate_ai_debrief(
        session_meta=combined_meta,
        hero_stats={},  # TODO: Aggregate hero stats
        gto_baselines=gto_baselines,
        gto_mistakes=all_mistakes[:10],
        opponents=list(all_opponents.values()),
        missed_opportunities=[]
    )

    return {
        "session_summary": combined_meta,
        "sessions_included": session_ids,
        "gto_analysis": {
            "baselines": gto_baselines,
            "mistakes": all_mistakes[:10],
            "mistake_count": len(all_mistakes)
        },
        "opponents": [opp for opp in all_opponents.values() if opp["db_total_hands"] >= 50],
        "ai_debrief": ai_result.get("analysis", {}),
        "ai_debug": {
            "prompt": ai_result.get("ai_prompt", ""),
            "response": ai_result.get("ai_response", "")
        },
        "disclaimers": {
            "combined_analysis": f"Combined analysis of {len(session_ids)} sessions ({total_hands} hands).",
            "gto_comparison": "GTO baselines assume 100bb stacks and standard 6-max play."
        }
    }
