"""
Session Debrief Service

AI-powered session analysis from GTO and exploitative perspectives.
Uses ONLY data from our database - no AI assumptions.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import logging
import anthropic
import os

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
    result = db.execute(text("""
        SELECT
            COUNT(*) as total_hands,
            SUM(CASE WHEN vpip THEN 1 ELSE 0 END) as vpip_count,
            SUM(CASE WHEN pfr THEN 1 ELSE 0 END) as pfr_count,
            SUM(CASE WHEN three_bet THEN 1 ELSE 0 END) as three_bet_count,
            SUM(CASE WHEN three_bet_opportunity THEN 1 ELSE 0 END) as three_bet_opps,
            SUM(CASE WHEN fold_to_three_bet THEN 1 ELSE 0 END) as fold_to_3bet_count,
            SUM(CASE WHEN facing_three_bet THEN 1 ELSE 0 END) as facing_3bet_opps,
            SUM(CASE WHEN cold_call THEN 1 ELSE 0 END) as cold_call_count,
            SUM(CASE WHEN cold_call_opportunity THEN 1 ELSE 0 END) as cold_call_opps,
            SUM(CASE WHEN limp THEN 1 ELSE 0 END) as limp_count,
            SUM(CASE WHEN open_opportunity THEN 1 ELSE 0 END) as open_opps,
            SUM(CASE WHEN four_bet THEN 1 ELSE 0 END) as four_bet_count,
            SUM(CASE WHEN four_bet_opportunity THEN 1 ELSE 0 END) as four_bet_opps
        FROM player_hand_summary
        WHERE session_id = :session_id AND is_hero = true
    """), {"session_id": session_id}).fetchone()

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
    """Get pre-analyzed GTO mistakes from hero_gto_mistakes table."""
    result = db.execute(text("""
        SELECT
            m.hand_id, m.scenario, m.hero_action, m.gto_action,
            m.gto_frequency, m.ev_loss_bb, m.severity, m.explanation,
            rh.hand_number
        FROM hero_gto_mistakes m
        JOIN raw_hands rh ON m.hand_id = rh.hand_id
        WHERE rh.session_id = :session_id
        ORDER BY m.ev_loss_bb DESC
        LIMIT :limit
    """), {"session_id": session_id, "limit": limit}).fetchall()

    mistakes = []
    for row in result:
        mistakes.append({
            "hand_id": row.hand_id,
            "hand_number": row.hand_number,
            "scenario": row.scenario,
            "hero_action": row.hero_action,
            "gto_action": row.gto_action,
            "gto_frequency": float(row.gto_frequency) if row.gto_frequency else None,
            "ev_loss_bb": float(row.ev_loss_bb) if row.ev_loss_bb else 0,
            "severity": row.severity,
            "explanation": row.explanation
        })

    return mistakes


def get_session_opponents(db: Session, session_id: int) -> List[Dict[str, Any]]:
    """Get opponents from this session with their database stats."""
    # First get unique opponents from session
    session_opponents = db.execute(text("""
        SELECT DISTINCT player_name
        FROM player_hand_summary
        WHERE session_id = :session_id AND is_hero = false
    """), {"session_id": session_id}).fetchall()

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

    # Find opponents with exploitable tendencies (100+ hands)
    exploitable_opponents = {
        opp["name"]: opp for opp in opponents
        if opp["db_total_hands"] >= 100 and opp["stats"]
    }

    if not exploitable_opponents:
        return missed

    # Check for missed 3-bet bluff opportunities
    for opp_name, opp_data in exploitable_opponents.items():
        stats = opp_data["stats"]
        gto_f3b = gto_baselines.get("fold_to_3bet", 52)

        # If opponent overfolds to 3bet significantly
        if stats.get("fold_to_3bet") and stats["fold_to_3bet"] > gto_f3b + 15:
            # Find hands where hero called vs this opponent's open instead of 3-betting
            hands = db.execute(text("""
                SELECT phs.hand_id, rh.hand_number
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                WHERE phs.session_id = :session_id
                AND phs.is_hero = true
                AND phs.cold_call = true
                AND EXISTS (
                    SELECT 1 FROM player_hand_summary opp
                    WHERE opp.hand_id = phs.hand_id
                    AND opp.player_name = :opp_name
                    AND opp.pfr = true
                )
                LIMIT 3
            """), {"session_id": session_id, "opp_name": opp_name}).fetchall()

            for hand in hands:
                missed.append({
                    "hand_id": hand.hand_id,
                    "hand_number": hand.hand_number,
                    "opponent": opp_name,
                    "opportunity": "3-bet bluff",
                    "opponent_tendency": f"Folds {stats['fold_to_3bet']:.1f}% to 3-bet (GTO: {gto_f3b}%)",
                    "opponent_sample": opp_data["db_total_hands"],
                    "hero_action": "Called",
                    "confidence": opp_data["confidence"]["label"]
                })

    return missed[:5]  # Limit to top 5


def generate_ai_debrief(
    session_meta: Dict[str, Any],
    hero_stats: Dict[str, Any],
    gto_baselines: Dict[str, Any],
    gto_mistakes: List[Dict[str, Any]],
    opponents: List[Dict[str, Any]],
    missed_opportunities: List[Dict[str, Any]]
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

    system_prompt = """You are a professional poker coach providing a session debrief.

CRITICAL RULES:
1. ONLY reference numbers from the data provided - NEVER invent statistics
2. ALWAYS note sample sizes when discussing patterns
3. NEVER claim a "leak" exists from session data alone - use "observation" or "pattern to monitor"
4. Distinguish between GTO mistakes and potential exploitative adjustments
5. For opponent reads, always state the sample size and confidence level
6. Be encouraging but honest about limitations

Format your response as JSON with these exact keys:
{
  "executive_summary": "2-3 sentence overview",
  "went_well": ["list of 2-3 things that went well with specific numbers"],
  "areas_for_improvement": ["list of 2-3 areas to work on with specific numbers"],
  "opponent_insights": [{"name": "...", "tendency": "...", "recommendation": "..."}],
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

=== INSTRUCTIONS ===
Generate a constructive debrief. For EVERY number you cite, it must appear in the data above.
Note sample size limitations honestly. Do not claim patterns without sufficient data.
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
        return ai_analysis
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {e}")
        logger.error(f"Response: {response_text[:500]}")
        return {
            "executive_summary": "Session analysis completed. Review the detailed stats below.",
            "went_well": ["Session completed"],
            "areas_for_improvement": ["Review hand histories for specific spots"],
            "opponent_insights": [],
            "study_recommendations": ["Continue tracking your play"]
        }


def generate_session_debrief(db: Session, session_id: int) -> Dict[str, Any]:
    """Main entry point - generate complete session debrief."""
    logger.info(f"Generating debrief for session {session_id}")

    # 1. Get session metadata
    session_meta = get_session_metadata(db, session_id)
    if not session_meta:
        raise ValueError(f"Session {session_id} not found")

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

    # 7. Generate AI debrief
    ai_analysis = generate_ai_debrief(
        session_meta=session_meta,
        hero_stats=hero_stats,
        gto_baselines=gto_baselines,
        gto_mistakes=gto_mistakes,
        opponents=opponents,
        missed_opportunities=missed_opportunities
    )

    # 8. Compile final response
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
        "ai_debrief": ai_analysis,
        "disclaimers": {
            "session_sample": f"Based on {session_meta['total_hands']} hands. Session stats have high variance.",
            "gto_comparison": "GTO baselines assume 100bb stacks and standard 6-max play.",
            "opponent_confidence": "Opponent reads require 100+ hands for moderate confidence, 300+ for high confidence."
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
    ai_analysis = generate_ai_debrief(
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
        "ai_debrief": ai_analysis,
        "disclaimers": {
            "combined_analysis": f"Combined analysis of {len(session_ids)} sessions ({total_hands} hands).",
            "gto_comparison": "GTO baselines assume 100bb stacks and standard 6-max play."
        }
    }
