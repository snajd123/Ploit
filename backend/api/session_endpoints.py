"""
Session Analysis API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..services.session_detector import SessionDetector
from ..services.hero_gto_analyzer import HeroGTOAnalyzer
from ..services.opponent_analyzer import OpponentAnalyzer

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionResponse(BaseModel):
    """Session metadata response"""
    session_id: int
    player_name: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    total_hands: int
    profit_loss_bb: float
    bb_100: float
    table_stakes: str
    table_name: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class SessionCreateRequest(BaseModel):
    """Request to manually create/detect sessions"""
    player_name: str
    session_gap_minutes: Optional[int] = 30


@router.get("/", response_model=List[SessionResponse])
def list_sessions(
    player_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_hands: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List all sessions with optional filtering.
    """
    query = """
        SELECT
            session_id,
            player_name,
            start_time,
            end_time,
            duration_minutes,
            total_hands,
            profit_loss_bb,
            bb_100,
            table_stakes,
            table_name,
            notes,
            tags
        FROM sessions
        WHERE 1=1
    """

    params = {}

    if player_name:
        query += " AND player_name = :player_name"
        params["player_name"] = player_name

    if start_date:
        query += " AND start_time >= :start_date"
        params["start_date"] = start_date

    if end_date:
        query += " AND end_time <= :end_date"
        params["end_date"] = end_date

    if min_hands:
        query += " AND total_hands >= :min_hands"
        params["min_hands"] = min_hands

    query += " ORDER BY start_time DESC"

    result = db.execute(text(query), params)
    sessions = [dict(row._mapping) for row in result]

    return sessions


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific session.
    """
    query = text("""
        SELECT
            session_id,
            player_name,
            start_time,
            end_time,
            duration_minutes,
            total_hands,
            profit_loss_bb,
            bb_100,
            table_stakes,
            table_name,
            notes,
            tags
        FROM sessions
        WHERE session_id = :session_id
    """)

    result = db.execute(query, {"session_id": session_id})
    session = result.first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return dict(session._mapping)


@router.get("/{session_id}/hands")
def get_session_hands(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all hands in a session.
    """
    query = text("""
        SELECT
            phs.hand_id,
            phs.player_name,
            phs.position,
            phs.profit_loss,
            rh.timestamp,
            rh.table_name
        FROM player_hand_summary phs
        JOIN raw_hands rh ON phs.hand_id = rh.hand_id
        WHERE phs.session_id = :session_id
        ORDER BY rh.timestamp ASC
    """)

    result = db.execute(query, {"session_id": session_id})
    hands = [dict(row._mapping) for row in result]

    return {
        "session_id": session_id,
        "total_hands": len(hands),
        "hands": hands
    }


@router.post("/detect")
def detect_sessions(
    request: SessionCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Detect and create sessions for a player from unassigned hands.
    """
    detector = SessionDetector(db, session_gap_minutes=request.session_gap_minutes)
    sessions = detector.detect_sessions_for_player(request.player_name)

    return {
        "player_name": request.player_name,
        "sessions_created": len(sessions),
        "sessions": sessions
    }


@router.post("/detect-all")
def detect_all_sessions(
    session_gap_minutes: int = 30,
    db: Session = Depends(get_db)
):
    """
    Detect and create sessions for all players with unassigned hands.
    """
    detector = SessionDetector(db, session_gap_minutes=session_gap_minutes)
    all_sessions = detector.detect_all_sessions()

    total_sessions = sum(len(sessions) for sessions in all_sessions.values())

    return {
        "players_processed": len(all_sessions),
        "total_sessions_created": total_sessions,
        "sessions_by_player": all_sessions
    }


@router.put("/{session_id}")
def update_session(
    session_id: int,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    Update session notes and tags.
    """
    updates = []
    params = {"session_id": session_id}

    if notes is not None:
        updates.append("notes = :notes")
        params["notes"] = notes

    if tags is not None:
        updates.append("tags = :tags")
        params["tags"] = tags

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    query = f"""
        UPDATE sessions
        SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
        WHERE session_id = :session_id
        RETURNING session_id
    """

    result = db.execute(text(query), params)
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "updated": True}


@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """
    Delete a session.
    """
    # First, unassign hands from this session
    unassign_query = text("""
        UPDATE raw_hands
        SET session_id = NULL
        WHERE session_id = :session_id
    """)
    db.execute(unassign_query, {"session_id": session_id})

    unassign_phs_query = text("""
        UPDATE player_hand_summary
        SET session_id = NULL
        WHERE session_id = :session_id
    """)
    db.execute(unassign_phs_query, {"session_id": session_id})

    # Delete session
    delete_query = text("""
        DELETE FROM sessions
        WHERE session_id = :session_id
        RETURNING session_id
    """)

    result = db.execute(delete_query, {"session_id": session_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "deleted": True}


@router.get("/{session_id}/stats")
def get_session_stats(session_id: int, db: Session = Depends(get_db)):
    """
    Get aggregated statistics for a session.
    """
    # Get basic session info
    session_query = text("""
        SELECT
            session_id,
            player_name,
            total_hands,
            profit_loss_bb,
            bb_100,
            duration_minutes
        FROM sessions
        WHERE session_id = :session_id
    """)

    session_result = db.execute(session_query, {"session_id": session_id})
    session = session_result.first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get aggregated stats from player_hand_summary
    # Note: postflop stats (saw_flop, cbet) not available - player_hand_summary is preflop-focused
    stats_query = text("""
        SELECT
            COUNT(*) as total_hands,
            SUM(CASE WHEN vpip THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as vpip_pct,
            SUM(CASE WHEN pfr THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as pfr_pct,
            SUM(CASE WHEN made_three_bet THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN faced_raise THEN 1 ELSE 0 END), 0) * 100 as three_bet_pct,
            SUM(CASE WHEN folded_to_three_bet THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN faced_three_bet THEN 1 ELSE 0 END), 0) * 100 as fold_to_3bet_pct,
            SUM(CASE WHEN went_to_showdown THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as wtsd_pct,
            SUM(CASE WHEN won_hand AND went_to_showdown THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN went_to_showdown THEN 1 ELSE 0 END), 0) * 100 as won_at_sd_pct,
            SUM(profit_loss) as total_profit_loss
        FROM player_hand_summary
        WHERE session_id = :session_id
    """)

    stats_result = db.execute(stats_query, {"session_id": session_id})
    stats = dict(stats_result.first()._mapping)

    return {
        "session_id": session._mapping["session_id"],
        "player_name": session._mapping["player_name"],
        "total_hands": session._mapping["total_hands"],
        "profit_loss_bb": float(session._mapping["profit_loss_bb"]) if session._mapping["profit_loss_bb"] else 0.0,
        "bb_100": float(session._mapping["bb_100"]) if session._mapping["bb_100"] else 0.0,
        "duration_minutes": session._mapping["duration_minutes"],
        "vpip_pct": round(float(stats["vpip_pct"] or 0), 1),
        "pfr_pct": round(float(stats["pfr_pct"] or 0), 1),
        "three_bet_pct": round(float(stats["three_bet_pct"] or 0), 1),
        "fold_to_3bet_pct": round(float(stats["fold_to_3bet_pct"] or 0), 1),
        "wtsd_pct": round(float(stats["wtsd_pct"] or 0), 1),
        "won_at_sd_pct": round(float(stats["won_at_sd_pct"] or 0), 1)
    }

@router.get("/{session_id}/gto-analysis")
def get_session_gto_analysis(session_id: int, db: Session = Depends(get_db)):
    """
    Get GTO analysis for a session - hero's mistakes and EV loss.
    """
    # Check if session exists
    session_query = text("SELECT session_id FROM sessions WHERE session_id = :session_id")
    result = db.execute(session_query, {"session_id": session_id})
    if not result.first():
        raise HTTPException(status_code=404, detail="Session not found")

    # Run GTO analysis
    analyzer = HeroGTOAnalyzer(db)
    analysis = analyzer.analyze_session(session_id)

    return analysis


@router.get("/{session_id}/opponents")
def get_session_opponents_analysis(session_id: int, db: Session = Depends(get_db)):
    """
    Get opponent frequency analysis for a session.

    Returns opponent stats, tendencies, and recommended exploits.
    """
    # Check if session exists
    session_query = text("SELECT session_id FROM sessions WHERE session_id = :session_id")
    result = db.execute(session_query, {"session_id": session_id})
    if not result.first():
        raise HTTPException(status_code=404, detail="Session not found")

    # Run opponent analysis
    analyzer = OpponentAnalyzer(db)
    analysis = analyzer.analyze_session_opponents(session_id)

    return {
        "session_id": session_id,
        "opponents_analyzed": len(analysis),
        "opponents": analysis
    }


# ============================================================================
# LEAK COMPARISON ENDPOINT - Compare session vs overall vs GTO
# ============================================================================

import math

# Sample thresholds by scenario type (per poker professor recommendations)
SAMPLE_THRESHOLDS = {
    'opening': {'min_display': 30, 'confident': 75, 'very_confident': 150},
    'defense': {'min_display': 25, 'confident': 60, 'very_confident': 120},
    'facing_3bet': {'min_display': 20, 'confident': 50, 'very_confident': 100},
}

# Leak weights by position and scenario (based on EV impact)
LEAK_WEIGHTS = {
    # Opening (RFI) - BTN most frequent, highest impact
    'opening_BTN': 1.5,
    'opening_CO': 1.3,
    'opening_SB': 1.4,
    'opening_MP': 1.1,
    'opening_UTG': 1.0,
    # Defense - BB vs BTN highest frequency
    'defense_BB_fold': 1.6,
    'defense_BB_call': 1.4,
    'defense_BB_3bet': 1.3,
    'defense_SB_fold': 1.2,
    'defense_SB_call': 1.1,
    'defense_SB_3bet': 1.2,
    'defense_BTN_fold': 1.0,
    'defense_BTN_call': 0.9,
    'defense_BTN_3bet': 1.0,
    'defense_CO_fold': 0.9,
    'defense_CO_call': 0.8,
    'defense_CO_3bet': 0.9,
    'defense_MP_fold': 0.8,
    'defense_MP_call': 0.7,
    'defense_MP_3bet': 0.8,
    # Facing 3-bet - fold to 3bet is huge leak
    'facing_3bet_BTN_fold': 1.4,
    'facing_3bet_BTN_call': 1.2,
    'facing_3bet_BTN_4bet': 1.1,
    'facing_3bet_CO_fold': 1.3,
    'facing_3bet_CO_call': 1.1,
    'facing_3bet_CO_4bet': 1.0,
    'facing_3bet_SB_fold': 1.2,
    'facing_3bet_SB_call': 1.0,
    'facing_3bet_SB_4bet': 1.0,
    'facing_3bet_MP_fold': 1.0,
    'facing_3bet_MP_call': 0.9,
    'facing_3bet_MP_4bet': 0.9,
    'facing_3bet_UTG_fold': 0.9,
    'facing_3bet_UTG_call': 0.8,
    'facing_3bet_UTG_4bet': 0.8,
}

# Severity multipliers for improvement scoring
SEVERITY_MULTIPLIERS = {
    'none': 0.5,
    'minor': 0.8,
    'moderate': 1.0,
    'major': 1.3,
}


def get_leak_weight(scenario_id: str) -> float:
    """Get the EV-based weight for a leak scenario."""
    return LEAK_WEIGHTS.get(scenario_id, 1.0)


def calculate_improvement_score(
    overall_value: float,
    session_value: float,
    gto_value: float,
    session_sample: int,
    min_sample: int,
    leak_severity: str = "moderate"
) -> float:
    """
    Calculate improvement score (0-100) with enhanced formula.
    50 = no change, >50 = improved, <50 = worse

    Features:
    - Zone bonus: +15% for landing within ±5% of GTO
    - Overcorrection penalty: -20% for crossing to wrong side
    - Severity weighting: Major leaks fixed = more credit
    - Sqrt confidence scaling: Diminishing returns on sample size
    """
    overall_distance = abs(overall_value - gto_value)
    session_distance = abs(session_value - gto_value)

    if overall_distance == 0:
        return 50.0  # No leak to improve

    # Base improvement ratio
    improvement_ratio = (overall_distance - session_distance) / overall_distance

    # Zone bonus: Extra credit for landing in GTO zone (±5%)
    in_gto_zone = session_distance <= 5.0
    zone_bonus = 0.15 if in_gto_zone else 0

    # Overcorrection penalty: Crossed GTO to other side
    overall_side = 1 if overall_value > gto_value else -1
    session_side = 1 if session_value > gto_value else -1
    overcorrected = overall_side != session_side and session_distance > 3
    overcorrection_penalty = -0.20 if overcorrected else 0

    # Severity multiplier (more credit for fixing major leaks)
    severity_mult = SEVERITY_MULTIPLIERS.get(leak_severity, 1.0)

    # Confidence using sqrt scaling (diminishing returns)
    confidence = min(1.0, math.sqrt(session_sample / min_sample) / math.sqrt(2))

    # Final score calculation
    raw_improvement = improvement_ratio + zone_bonus + overcorrection_penalty
    weighted_improvement = raw_improvement * severity_mult * confidence

    return 50 + (weighted_improvement * 50)


def get_improvement_status(
    overall_value: float,
    session_value: float,
    gto_value: float,
    session_sample: int,
    min_sample: int
) -> str:
    """Determine improvement status: improved, same, worse, or overcorrected"""
    # Check for overcorrection first
    overall_side = "high" if overall_value > gto_value else "low"
    session_side = "high" if session_value > gto_value else "low"

    if overall_side != session_side and abs(session_value - gto_value) > 3:
        return "overcorrected"

    # Insufficient sample
    if session_sample < min_sample:
        return "same"

    # Check if improved or worse
    overall_distance = abs(overall_value - gto_value)
    session_distance = abs(session_value - gto_value)

    if session_distance < overall_distance - 3:
        return "improved"
    elif session_distance > overall_distance + 3:
        return "worse"
    else:
        return "same"


def get_leak_severity(deviation: float) -> str:
    """Determine leak severity based on deviation from GTO"""
    abs_dev = abs(deviation)
    if abs_dev < 5:
        return "none"
    elif abs_dev < 10:
        return "minor"
    elif abs_dev < 20:
        return "moderate"
    else:
        return "major"


def get_confidence_level(sample: int, scenario_type: str) -> str:
    """Determine confidence level based on sample size and scenario type"""
    thresholds = SAMPLE_THRESHOLDS.get(scenario_type, SAMPLE_THRESHOLDS['opening'])

    if sample < thresholds['min_display']:
        return "insufficient"
    elif sample < thresholds['confident']:
        return "low"
    elif sample < thresholds['very_confident']:
        return "moderate"
    else:
        return "high"


def calculate_priority_score(scenario: dict) -> float:
    """
    Calculate priority score for sorting leaks by importance.
    Higher score = higher priority to fix.

    Factors:
    - Leak severity (major > moderate > minor)
    - EV weight (position importance)
    - Improvement potential (distance to GTO)
    - Sample confidence
    """
    if not scenario.get('is_leak'):
        return 0

    # Base priority from severity
    severity_scores = {'none': 0, 'minor': 1, 'moderate': 2, 'major': 3}
    severity_score = severity_scores.get(scenario.get('leak_severity', 'none'), 0)

    # EV weight
    ev_weight = get_leak_weight(scenario.get('scenario_id', ''))

    # Distance to GTO (improvement potential)
    deviation = abs(scenario.get('overall_deviation', 0))

    # Confidence factor
    confidence_scores = {'insufficient': 0.3, 'low': 0.6, 'moderate': 0.85, 'high': 1.0}
    conf_level = scenario.get('confidence_level', 'low')
    confidence = confidence_scores.get(conf_level, 0.5)

    # Combined priority score
    priority = (severity_score * 10 + deviation * 0.5) * ev_weight * confidence

    return round(priority, 2)


@router.get("/{session_id}/leak-comparison")
def get_session_leak_comparison(session_id: int, db: Session = Depends(get_db)):
    """
    Compare session performance vs overall player leaks vs GTO baselines.

    Returns scenario-level comparison for each GTO scenario (opening, defense, facing 3-bet)
    with improvement scores and status.
    """
    # Get session info
    session_query = text("""
        SELECT session_id, player_name, total_hands
        FROM sessions
        WHERE session_id = :session_id
    """)
    session_result = db.execute(session_query, {"session_id": session_id})
    session = session_result.first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    player_name = session._mapping["player_name"]
    session_hands = session._mapping["total_hands"]

    # Determine overall confidence
    if session_hands < 100:
        confidence = "low"
    elif session_hands < 300:
        confidence = "moderate"
    else:
        confidence = "high"

    scenarios = []

    # ============================================
    # 1. OPENING (RFI) - Compare by position
    # ============================================
    # Get GTO opening frequencies
    gto_opening_result = db.execute(text("""
        SELECT position, SUM(gto_aggregate_freq) * 100 as gto_freq
        FROM gto_scenarios WHERE category = 'opening'
        GROUP BY position
    """))
    gto_opening = {row[0]: float(row[1]) if row[1] else 0 for row in gto_opening_result}

    # Get overall player opening frequencies
    overall_opening_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_raise = false) as opportunities,
            COUNT(*) FILTER (WHERE pfr = true AND faced_raise = false) as opened
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND position IS NOT NULL
        AND position NOT IN ('BB')
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE faced_raise = false) >= 10
    """), {"player_name": player_name})
    overall_opening = {row[0]: {
        "sample": row[1],
        "value": (row[2] / row[1] * 100) if row[1] > 0 else 0
    } for row in overall_opening_result}

    # Get session opening frequencies
    session_opening_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_raise = false) as opportunities,
            COUNT(*) FILTER (WHERE pfr = true AND faced_raise = false) as opened
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND session_id = :session_id
        AND position IS NOT NULL
        AND position NOT IN ('BB')
        GROUP BY position
    """), {"player_name": player_name, "session_id": session_id})
    session_opening = {row[0]: {
        "sample": row[1],
        "value": (row[2] / row[1] * 100) if row[1] > 0 else 0
    } for row in session_opening_result}

    # Build opening scenarios
    min_sample_opening = SAMPLE_THRESHOLDS['opening']['min_display']
    for pos in ["UTG", "MP", "CO", "BTN", "SB"]:
        gto_value = gto_opening.get(pos, 0)
        overall_data = overall_opening.get(pos, {"sample": 0, "value": 0})
        session_data = session_opening.get(pos, {"sample": 0, "value": 0})

        overall_value = overall_data["value"]
        overall_sample = overall_data["sample"]
        session_value = session_data["value"]
        session_sample = session_data["sample"]

        overall_deviation = overall_value - gto_value
        session_deviation = session_value - gto_value
        is_leak = abs(overall_deviation) >= 5 and overall_sample >= 10

        scenario_id = f"opening_{pos}"
        leak_severity = get_leak_severity(overall_deviation) if is_leak else "none"
        ev_weight = get_leak_weight(scenario_id)

        scenario = {
            "scenario_id": scenario_id,
            "category": "opening",
            "position": pos,
            "vs_position": None,
            "action": "RFI",
            "display_name": f"{pos} Open (RFI)",

            "overall_value": round(overall_value, 1),
            "overall_sample": overall_sample,
            "overall_deviation": round(overall_deviation, 1),
            "is_leak": is_leak,
            "leak_direction": "too_loose" if overall_deviation > 0 else "too_tight" if overall_deviation < 0 else None,
            "leak_severity": leak_severity,
            "ev_weight": ev_weight,

            "gto_value": round(gto_value, 1),

            "session_value": round(session_value, 1) if session_sample > 0 else None,
            "session_sample": session_sample,
            "session_deviation": round(session_deviation, 1) if session_sample > 0 else None,

            "improvement_score": round(calculate_improvement_score(
                overall_value, session_value, gto_value, session_sample, min_sample_opening, leak_severity
            ), 1) if session_sample > 0 and is_leak else None,
            "improvement_status": get_improvement_status(
                overall_value, session_value, gto_value, session_sample, min_sample_opening
            ) if session_sample > 0 and is_leak else None,
            "within_gto_zone": abs(session_deviation) < 5 if session_sample > 0 else None,
            "overcorrected": get_improvement_status(
                overall_value, session_value, gto_value, session_sample, min_sample_opening
            ) == "overcorrected" if session_sample > 0 and is_leak else False,
            "confidence_level": get_confidence_level(session_sample, 'opening')
        }
        scenario["priority_score"] = calculate_priority_score(scenario)
        scenarios.append(scenario)

    # ============================================
    # 2. DEFENSE VS OPENS - Fold/Call/3bet by position
    # ============================================
    # Get GTO defense frequencies
    gto_defense_result = db.execute(text("""
        SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
        FROM gto_scenarios
        WHERE category = 'defense'
        AND action IN ('fold', 'call', '3bet')
        GROUP BY position, action
    """))
    gto_defense = {}
    for row in gto_defense_result:
        pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
        if pos not in gto_defense:
            gto_defense[pos] = {}
        gto_defense[pos][action] = freq

    # Get overall defense frequencies
    overall_defense_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) as folded,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) as called,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) as three_bets
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) >= 5
    """), {"player_name": player_name})

    overall_defense = {}
    for row in overall_defense_result:
        pos = row[0]
        total = row[1] or 0
        if total > 0:
            overall_defense[pos] = {
                "sample": total,
                "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100,
                "3bet": (row[4] or 0) / total * 100
            }

    # Get session defense frequencies
    session_defense_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) as folded,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) as called,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) as three_bets
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND session_id = :session_id
        AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position
    """), {"player_name": player_name, "session_id": session_id})

    session_defense = {}
    for row in session_defense_result:
        pos = row[0]
        total = row[1] or 0
        if total > 0:
            session_defense[pos] = {
                "sample": total,
                "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100,
                "3bet": (row[4] or 0) / total * 100
            }

    # Build defense scenarios
    min_sample_defense = SAMPLE_THRESHOLDS['defense']['min_display']
    for pos in ["BB", "SB", "BTN", "CO", "MP"]:
        gto_actions = gto_defense.get(pos, {})
        overall_data = overall_defense.get(pos, {})
        session_data = session_defense.get(pos, {})

        for action in ["fold", "call", "3bet"]:
            action_display = "Fold" if action == "fold" else "Call" if action == "call" else "3-Bet"
            gto_value = gto_actions.get(action, 0)

            # Calculate fold GTO if not directly available (100 - call - 3bet)
            if action == "fold" and gto_value == 0 and gto_actions:
                gto_value = 100 - gto_actions.get("call", 0) - gto_actions.get("3bet", 0)

            overall_value = overall_data.get(action, 0)
            overall_sample = overall_data.get("sample", 0)
            session_value = session_data.get(action, 0)
            session_sample = session_data.get("sample", 0)

            overall_deviation = overall_value - gto_value
            session_deviation = session_value - gto_value
            is_leak = abs(overall_deviation) >= 5 and overall_sample >= 5

            scenario_id = f"defense_{pos}_{action}"
            leak_severity = get_leak_severity(overall_deviation) if is_leak else "none"
            ev_weight = get_leak_weight(scenario_id)

            scenario = {
                "scenario_id": scenario_id,
                "category": "defense",
                "position": pos,
                "vs_position": None,
                "action": action_display,
                "display_name": f"{pos} Defense - {action_display}%",

                "overall_value": round(overall_value, 1),
                "overall_sample": overall_sample,
                "overall_deviation": round(overall_deviation, 1),
                "is_leak": is_leak,
                "leak_direction": "too_high" if overall_deviation > 0 else "too_low" if overall_deviation < 0 else None,
                "leak_severity": leak_severity,
                "ev_weight": ev_weight,

                "gto_value": round(gto_value, 1),

                "session_value": round(session_value, 1) if session_sample > 0 else None,
                "session_sample": session_sample,
                "session_deviation": round(session_deviation, 1) if session_sample > 0 else None,

                "improvement_score": round(calculate_improvement_score(
                    overall_value, session_value, gto_value, session_sample, min_sample_defense, leak_severity
                ), 1) if session_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_defense
                ) if session_sample > 0 and is_leak else None,
                "within_gto_zone": abs(session_deviation) < 5 if session_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_defense
                ) == "overcorrected" if session_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(session_sample, 'defense')
            }
            scenario["priority_score"] = calculate_priority_score(scenario)
            scenarios.append(scenario)

    # ============================================
    # 3. FACING 3-BET - Fold/Call/4bet by position
    # ============================================
    # Get GTO facing 3-bet frequencies
    gto_f3bet_result = db.execute(text("""
        SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
        FROM gto_scenarios
        WHERE category = 'facing_3bet'
        AND action IN ('fold', 'call', '4bet')
        GROUP BY position, action
    """))
    gto_f3bet = {}
    for row in gto_f3bet_result:
        pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
        if pos not in gto_f3bet:
            gto_f3bet[pos] = {}
        gto_f3bet[pos][action] = freq

    # Get overall facing 3-bet frequencies
    overall_f3bet_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
            COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) as folded,
            COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) as called,
            COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) as four_bet
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND position IS NOT NULL
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) >= 5
    """), {"player_name": player_name})

    overall_f3bet = {}
    for row in overall_f3bet_result:
        pos = row[0]
        total = row[1] or 0
        if total > 0:
            overall_f3bet[pos] = {
                "sample": total,
                "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100,
                "4bet": (row[4] or 0) / total * 100
            }

    # Get session facing 3-bet frequencies
    session_f3bet_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
            COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) as folded,
            COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) as called,
            COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) as four_bet
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND session_id = :session_id
        AND position IS NOT NULL
        GROUP BY position
    """), {"player_name": player_name, "session_id": session_id})

    session_f3bet = {}
    for row in session_f3bet_result:
        pos = row[0]
        total = row[1] or 0
        if total > 0:
            session_f3bet[pos] = {
                "sample": total,
                "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100,
                "4bet": (row[4] or 0) / total * 100
            }

    # Build facing 3-bet scenarios
    min_sample_f3bet = SAMPLE_THRESHOLDS['facing_3bet']['min_display']
    for pos in ["UTG", "MP", "CO", "BTN", "SB"]:
        gto_actions = gto_f3bet.get(pos, {})
        overall_data = overall_f3bet.get(pos, {})
        session_data = session_f3bet.get(pos, {})

        for action in ["fold", "call", "4bet"]:
            action_display = "Fold" if action == "fold" else "Call" if action == "call" else "4-Bet"
            gto_value = gto_actions.get(action, 0)

            overall_value = overall_data.get(action, 0)
            overall_sample = overall_data.get("sample", 0)
            session_value = session_data.get(action, 0)
            session_sample = session_data.get("sample", 0)

            overall_deviation = overall_value - gto_value
            session_deviation = session_value - gto_value
            is_leak = abs(overall_deviation) >= 5 and overall_sample >= 5

            scenario_id = f"facing_3bet_{pos}_{action}"
            leak_severity = get_leak_severity(overall_deviation) if is_leak else "none"
            ev_weight = get_leak_weight(scenario_id)

            scenario = {
                "scenario_id": scenario_id,
                "category": "facing_3bet",
                "position": pos,
                "vs_position": None,
                "action": action_display,
                "display_name": f"{pos} vs 3-Bet - {action_display}%",

                "overall_value": round(overall_value, 1),
                "overall_sample": overall_sample,
                "overall_deviation": round(overall_deviation, 1),
                "is_leak": is_leak,
                "leak_direction": "too_high" if overall_deviation > 0 else "too_low" if overall_deviation < 0 else None,
                "leak_severity": leak_severity,
                "ev_weight": ev_weight,

                "gto_value": round(gto_value, 1),

                "session_value": round(session_value, 1) if session_sample > 0 else None,
                "session_sample": session_sample,
                "session_deviation": round(session_deviation, 1) if session_sample > 0 else None,

                "improvement_score": round(calculate_improvement_score(
                    overall_value, session_value, gto_value, session_sample, min_sample_f3bet, leak_severity
                ), 1) if session_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_f3bet
                ) if session_sample > 0 and is_leak else None,
                "within_gto_zone": abs(session_deviation) < 5 if session_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_f3bet
                ) == "overcorrected" if session_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(session_sample, 'facing_3bet')
            }
            scenario["priority_score"] = calculate_priority_score(scenario)
            scenarios.append(scenario)

    # ============================================
    # CALCULATE SUMMARY
    # ============================================
    leaks_only = [s for s in scenarios if s["is_leak"]]
    leaks_with_session = [s for s in leaks_only if s["session_sample"] and s["session_sample"] > 0]

    improved = len([s for s in leaks_with_session if s["improvement_status"] == "improved"])
    same = len([s for s in leaks_with_session if s["improvement_status"] == "same"])
    worse = len([s for s in leaks_with_session if s["improvement_status"] == "worse"])
    overcorrected = len([s for s in leaks_with_session if s["improvement_status"] == "overcorrected"])

    # Calculate overall improvement score (weighted by priority)
    leak_scores = [s["improvement_score"] for s in leaks_with_session if s["improvement_score"] is not None]
    overall_score = sum(leak_scores) / len(leak_scores) if leak_scores else 50.0

    # Determine grade
    if overall_score >= 80:
        grade = "A"
    elif overall_score >= 65:
        grade = "B"
    elif overall_score >= 50:
        grade = "C"
    elif overall_score >= 35:
        grade = "D"
    else:
        grade = "F"

    # Priority leaks: sorted by priority_score descending
    priority_leaks = sorted(
        [s for s in leaks_only if s.get("priority_score", 0) > 0],
        key=lambda x: x.get("priority_score", 0),
        reverse=True
    )

    return {
        "session_id": session_id,
        "player_name": player_name,
        "session_hands": session_hands,
        "confidence": confidence,

        "scenarios": scenarios,
        "priority_leaks": priority_leaks,

        "summary": {
            "total_scenarios": len(scenarios),
            "scenarios_with_leaks": len(leaks_only),
            "scenarios_improved": improved,
            "scenarios_same": same,
            "scenarios_worse": worse,
            "scenarios_overcorrected": overcorrected,
            "overall_improvement_score": round(overall_score, 1),
            "session_grade": grade
        }
    }


# ============================================================================
# GROUP ANALYSIS ENDPOINT - Analyze multiple sessions with trends
# ============================================================================

class GroupAnalysisRequest(BaseModel):
    """Request body for group analysis"""
    session_ids: List[int]


def get_session_stats(db: Session, session_id: int, player_name: str) -> Dict[str, Any]:
    """Get basic stats for a single session"""
    stats_query = text("""
        SELECT
            COUNT(*) as total_hands,
            SUM(CASE WHEN vpip THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as vpip_pct,
            SUM(CASE WHEN pfr THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as pfr_pct,
            SUM(CASE WHEN made_three_bet THEN 1 ELSE 0 END)::float /
                NULLIF(SUM(CASE WHEN faced_raise THEN 1 ELSE 0 END), 0) * 100 as three_bet_pct,
            SUM(CASE WHEN folded_to_three_bet THEN 1 ELSE 0 END)::float /
                NULLIF(SUM(CASE WHEN faced_three_bet THEN 1 ELSE 0 END), 0) * 100 as fold_to_3bet_pct,
            SUM(CASE WHEN went_to_showdown THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as wtsd_pct,
            SUM(CASE WHEN won_hand AND went_to_showdown THEN 1 ELSE 0 END)::float /
                NULLIF(SUM(CASE WHEN went_to_showdown THEN 1 ELSE 0 END), 0) * 100 as won_at_sd_pct
        FROM player_hand_summary
        WHERE session_id = :session_id AND player_name = :player_name
    """)
    result = db.execute(stats_query, {"session_id": session_id, "player_name": player_name})
    row = result.first()
    if not row:
        return {}

    return {
        "hands": row[0] or 0,
        "vpip_pct": round(float(row[1] or 0), 1),
        "pfr_pct": round(float(row[2] or 0), 1),
        "three_bet_pct": round(float(row[3] or 0), 1),
        "fold_to_3bet_pct": round(float(row[4] or 0), 1),
        "wtsd_pct": round(float(row[5] or 0), 1),
        "won_at_sd_pct": round(float(row[6] or 0), 1)
    }


def get_session_scenario_values(db: Session, session_id: int, player_name: str) -> Dict[str, Dict[str, Any]]:
    """Get scenario values for a single session (for trend data)"""
    scenarios = {}

    # Opening (RFI) by position
    opening_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_raise = false) as opportunities,
            COUNT(*) FILTER (WHERE pfr = true AND faced_raise = false) as opened
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND session_id = :session_id
        AND position IS NOT NULL
        AND position NOT IN ('BB')
        GROUP BY position
    """), {"player_name": player_name, "session_id": session_id})

    for row in opening_result:
        pos, opps, opened = row[0], row[1] or 0, row[2] or 0
        if opps > 0:
            scenarios[f"opening_{pos}"] = {
                "value": round((opened / opps) * 100, 1),
                "sample": opps
            }

    # Defense by position
    defense_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) as folded,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) as called,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) as three_bets
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND session_id = :session_id
        AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position
    """), {"player_name": player_name, "session_id": session_id})

    for row in defense_result:
        pos, total = row[0], row[1] or 0
        if total > 0:
            scenarios[f"defense_{pos}_fold"] = {"value": round((row[2] or 0) / total * 100, 1), "sample": total}
            scenarios[f"defense_{pos}_call"] = {"value": round((row[3] or 0) / total * 100, 1), "sample": total}
            scenarios[f"defense_{pos}_3bet"] = {"value": round((row[4] or 0) / total * 100, 1), "sample": total}

    # Facing 3-bet by position
    f3bet_result = db.execute(text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
            COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) as folded,
            COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) as called,
            COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) as four_bet
        FROM player_hand_summary
        WHERE player_name = :player_name
        AND session_id = :session_id
        AND position IS NOT NULL
        GROUP BY position
    """), {"player_name": player_name, "session_id": session_id})

    for row in f3bet_result:
        pos, total = row[0], row[1] or 0
        if total > 0:
            scenarios[f"facing_3bet_{pos}_fold"] = {"value": round((row[2] or 0) / total * 100, 1), "sample": total}
            scenarios[f"facing_3bet_{pos}_call"] = {"value": round((row[3] or 0) / total * 100, 1), "sample": total}
            scenarios[f"facing_3bet_{pos}_4bet"] = {"value": round((row[4] or 0) / total * 100, 1), "sample": total}

    return scenarios


@router.post("/group-analysis")
def get_session_group_analysis(request: GroupAnalysisRequest, db: Session = Depends(get_db)):
    """
    Analyze multiple sessions together with trend data.

    Returns:
    - Aggregated leak comparison (combined data vs GTO)
    - Per-session trend data for charts
    - Basic stats trends (VPIP, PFR, etc.)
    """
    session_ids = request.session_ids

    if not session_ids:
        raise HTTPException(status_code=400, detail="No session IDs provided")

    if len(session_ids) < 1:
        raise HTTPException(status_code=400, detail="At least one session ID required")

    # Get session info and validate all belong to same player
    sessions_query = text("""
        SELECT session_id, player_name, start_time, total_hands, profit_loss_bb
        FROM sessions
        WHERE session_id = ANY(:session_ids)
        ORDER BY start_time ASC
    """)
    sessions_result = db.execute(sessions_query, {"session_ids": session_ids})
    sessions = [dict(row._mapping) for row in sessions_result]

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")

    # Validate all sessions belong to same player
    player_names = set(s["player_name"] for s in sessions)
    if len(player_names) > 1:
        raise HTTPException(status_code=400, detail="All sessions must belong to the same player")

    player_name = sessions[0]["player_name"]
    total_hands = sum(s["total_hands"] or 0 for s in sessions)
    total_profit_bb = sum(float(s["profit_loss_bb"] or 0) for s in sessions)

    # Date range
    date_range = {
        "start": sessions[0]["start_time"].isoformat() if sessions[0]["start_time"] else None,
        "end": sessions[-1]["start_time"].isoformat() if sessions[-1]["start_time"] else None
    }

    # ============================================
    # GET PER-SESSION TREND DATA
    # ============================================
    session_trends = []
    for sess in sessions:
        sid = sess["session_id"]
        stats = get_session_stats(db, sid, player_name)
        scenario_values = get_session_scenario_values(db, sid, player_name)

        session_trends.append({
            "session_id": sid,
            "date": sess["start_time"].strftime("%Y-%m-%d") if sess["start_time"] else None,
            "hands": sess["total_hands"] or 0,
            "profit_bb": float(sess["profit_loss_bb"] or 0),
            "stats": stats,
            "scenarios": scenario_values
        })

    # ============================================
    # GET AGGREGATED DATA (combined sessions vs GTO)
    # ============================================
    # This is similar to single session leak comparison but with multiple session_ids

    # Determine overall confidence
    if total_hands < 200:
        confidence = "low"
    elif total_hands < 500:
        confidence = "moderate"
    else:
        confidence = "high"

    scenarios = []

    # Get GTO baselines (same as single session)
    gto_opening_result = db.execute(text("""
        SELECT position, SUM(gto_aggregate_freq) * 100 as gto_freq
        FROM gto_scenarios WHERE category = 'opening'
        GROUP BY position
    """))
    gto_opening = {row[0]: float(row[1]) if row[1] else 0 for row in gto_opening_result}

    gto_defense_result = db.execute(text("""
        SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
        FROM gto_scenarios
        WHERE category = 'defense' AND action IN ('fold', 'call', '3bet')
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

    # Get overall player frequencies (lifetime)
    overall_opening_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_raise = false) as opportunities,
            COUNT(*) FILTER (WHERE pfr = true AND faced_raise = false) as opened
        FROM player_hand_summary
        WHERE player_name = :player_name AND position IS NOT NULL AND position NOT IN ('BB')
        GROUP BY position HAVING COUNT(*) FILTER (WHERE faced_raise = false) >= 10
    """), {"player_name": player_name})
    overall_opening = {row[0]: {"sample": row[1], "value": (row[2] / row[1] * 100) if row[1] > 0 else 0}
                       for row in overall_opening_result}

    # Get combined sessions frequencies (using IN clause)
    combined_opening_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_raise = false) as opportunities,
            COUNT(*) FILTER (WHERE pfr = true AND faced_raise = false) as opened
        FROM player_hand_summary
        WHERE player_name = :player_name AND session_id = ANY(:session_ids)
        AND position IS NOT NULL AND position NOT IN ('BB')
        GROUP BY position
    """), {"player_name": player_name, "session_ids": session_ids})
    combined_opening = {row[0]: {"sample": row[1], "value": (row[2] / row[1] * 100) if row[1] > 0 else 0}
                        for row in combined_opening_result}

    # Build opening scenarios
    min_sample_opening = SAMPLE_THRESHOLDS['opening']['min_display']
    for pos in ["UTG", "MP", "CO", "BTN", "SB"]:
        gto_value = gto_opening.get(pos, 0)
        overall_data = overall_opening.get(pos, {"sample": 0, "value": 0})
        combined_data = combined_opening.get(pos, {"sample": 0, "value": 0})

        overall_value = overall_data["value"]
        overall_sample = overall_data["sample"]
        combined_value = combined_data["value"]
        combined_sample = combined_data["sample"]

        overall_deviation = overall_value - gto_value
        combined_deviation = combined_value - gto_value
        is_leak = abs(overall_deviation) >= 5 and overall_sample >= 10

        scenario_id = f"opening_{pos}"
        leak_severity = get_leak_severity(overall_deviation) if is_leak else "none"
        ev_weight = get_leak_weight(scenario_id)

        scenario = {
            "scenario_id": scenario_id,
            "category": "opening",
            "position": pos,
            "vs_position": None,
            "action": "RFI",
            "display_name": f"{pos} Open (RFI)",
            "overall_value": round(overall_value, 1),
            "overall_sample": overall_sample,
            "overall_deviation": round(overall_deviation, 1),
            "is_leak": is_leak,
            "leak_direction": "too_loose" if overall_deviation > 0 else "too_tight" if overall_deviation < 0 else None,
            "leak_severity": leak_severity,
            "ev_weight": ev_weight,
            "gto_value": round(gto_value, 1),
            "session_value": round(combined_value, 1) if combined_sample > 0 else None,
            "session_sample": combined_sample,
            "session_deviation": round(combined_deviation, 1) if combined_sample > 0 else None,
            "improvement_score": round(calculate_improvement_score(
                overall_value, combined_value, gto_value, combined_sample, min_sample_opening, leak_severity
            ), 1) if combined_sample > 0 and is_leak else None,
            "improvement_status": get_improvement_status(
                overall_value, combined_value, gto_value, combined_sample, min_sample_opening
            ) if combined_sample > 0 and is_leak else None,
            "within_gto_zone": abs(combined_deviation) < 5 if combined_sample > 0 else None,
            "overcorrected": get_improvement_status(
                overall_value, combined_value, gto_value, combined_sample, min_sample_opening
            ) == "overcorrected" if combined_sample > 0 and is_leak else False,
            "confidence_level": get_confidence_level(combined_sample, 'opening')
        }
        scenario["priority_score"] = calculate_priority_score(scenario)
        scenarios.append(scenario)

    # Defense scenarios
    overall_defense_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) as folded,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) as called,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) as three_bets
        FROM player_hand_summary
        WHERE player_name = :player_name AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position HAVING COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) >= 5
    """), {"player_name": player_name})
    overall_defense = {}
    for row in overall_defense_result:
        pos, total = row[0], row[1] or 0
        if total > 0:
            overall_defense[pos] = {
                "sample": total, "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100, "3bet": (row[4] or 0) / total * 100
            }

    combined_defense_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) as folded,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) as called,
            COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) as three_bets
        FROM player_hand_summary
        WHERE player_name = :player_name AND session_id = ANY(:session_ids)
        AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position
    """), {"player_name": player_name, "session_ids": session_ids})
    combined_defense = {}
    for row in combined_defense_result:
        pos, total = row[0], row[1] or 0
        if total > 0:
            combined_defense[pos] = {
                "sample": total, "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100, "3bet": (row[4] or 0) / total * 100
            }

    min_sample_defense = SAMPLE_THRESHOLDS['defense']['min_display']
    for pos in ["BB", "SB", "BTN", "CO", "MP"]:
        gto_actions = gto_defense.get(pos, {})
        overall_data = overall_defense.get(pos, {})
        combined_data = combined_defense.get(pos, {})

        for action in ["fold", "call", "3bet"]:
            action_display = "Fold" if action == "fold" else "Call" if action == "call" else "3-Bet"
            gto_value = gto_actions.get(action, 0)
            if action == "fold" and gto_value == 0 and gto_actions:
                gto_value = 100 - gto_actions.get("call", 0) - gto_actions.get("3bet", 0)

            overall_value = overall_data.get(action, 0)
            overall_sample = overall_data.get("sample", 0)
            combined_value = combined_data.get(action, 0)
            combined_sample = combined_data.get("sample", 0)

            overall_deviation = overall_value - gto_value
            combined_deviation = combined_value - gto_value
            is_leak = abs(overall_deviation) >= 5 and overall_sample >= 5

            scenario_id = f"defense_{pos}_{action}"
            leak_severity = get_leak_severity(overall_deviation) if is_leak else "none"
            ev_weight = get_leak_weight(scenario_id)

            scenario = {
                "scenario_id": scenario_id,
                "category": "defense",
                "position": pos,
                "vs_position": None,
                "action": action_display,
                "display_name": f"{pos} Defense - {action_display}%",
                "overall_value": round(overall_value, 1),
                "overall_sample": overall_sample,
                "overall_deviation": round(overall_deviation, 1),
                "is_leak": is_leak,
                "leak_direction": "too_high" if overall_deviation > 0 else "too_low" if overall_deviation < 0 else None,
                "leak_severity": leak_severity,
                "ev_weight": ev_weight,
                "gto_value": round(gto_value, 1),
                "session_value": round(combined_value, 1) if combined_sample > 0 else None,
                "session_sample": combined_sample,
                "session_deviation": round(combined_deviation, 1) if combined_sample > 0 else None,
                "improvement_score": round(calculate_improvement_score(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_defense, leak_severity
                ), 1) if combined_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_defense
                ) if combined_sample > 0 and is_leak else None,
                "within_gto_zone": abs(combined_deviation) < 5 if combined_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_defense
                ) == "overcorrected" if combined_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(combined_sample, 'defense')
            }
            scenario["priority_score"] = calculate_priority_score(scenario)
            scenarios.append(scenario)

    # Facing 3-bet scenarios
    overall_f3bet_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
            COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) as folded,
            COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) as called,
            COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) as four_bet
        FROM player_hand_summary
        WHERE player_name = :player_name AND position IS NOT NULL
        GROUP BY position HAVING COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) >= 5
    """), {"player_name": player_name})
    overall_f3bet = {}
    for row in overall_f3bet_result:
        pos, total = row[0], row[1] or 0
        if total > 0:
            overall_f3bet[pos] = {
                "sample": total, "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100, "4bet": (row[4] or 0) / total * 100
            }

    combined_f3bet_result = db.execute(text("""
        SELECT position,
            COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
            COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) as folded,
            COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) as called,
            COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) as four_bet
        FROM player_hand_summary
        WHERE player_name = :player_name AND session_id = ANY(:session_ids)
        AND position IS NOT NULL
        GROUP BY position
    """), {"player_name": player_name, "session_ids": session_ids})
    combined_f3bet = {}
    for row in combined_f3bet_result:
        pos, total = row[0], row[1] or 0
        if total > 0:
            combined_f3bet[pos] = {
                "sample": total, "fold": (row[2] or 0) / total * 100,
                "call": (row[3] or 0) / total * 100, "4bet": (row[4] or 0) / total * 100
            }

    min_sample_f3bet = SAMPLE_THRESHOLDS['facing_3bet']['min_display']
    for pos in ["UTG", "MP", "CO", "BTN", "SB"]:
        gto_actions = gto_f3bet.get(pos, {})
        overall_data = overall_f3bet.get(pos, {})
        combined_data = combined_f3bet.get(pos, {})

        for action in ["fold", "call", "4bet"]:
            action_display = "Fold" if action == "fold" else "Call" if action == "call" else "4-Bet"
            gto_value = gto_actions.get(action, 0)

            overall_value = overall_data.get(action, 0)
            overall_sample = overall_data.get("sample", 0)
            combined_value = combined_data.get(action, 0)
            combined_sample = combined_data.get("sample", 0)

            overall_deviation = overall_value - gto_value
            combined_deviation = combined_value - gto_value
            is_leak = abs(overall_deviation) >= 5 and overall_sample >= 5

            scenario_id = f"facing_3bet_{pos}_{action}"
            leak_severity = get_leak_severity(overall_deviation) if is_leak else "none"
            ev_weight = get_leak_weight(scenario_id)

            scenario = {
                "scenario_id": scenario_id,
                "category": "facing_3bet",
                "position": pos,
                "vs_position": None,
                "action": action_display,
                "display_name": f"{pos} vs 3-Bet - {action_display}%",
                "overall_value": round(overall_value, 1),
                "overall_sample": overall_sample,
                "overall_deviation": round(overall_deviation, 1),
                "is_leak": is_leak,
                "leak_direction": "too_high" if overall_deviation > 0 else "too_low" if overall_deviation < 0 else None,
                "leak_severity": leak_severity,
                "ev_weight": ev_weight,
                "gto_value": round(gto_value, 1),
                "session_value": round(combined_value, 1) if combined_sample > 0 else None,
                "session_sample": combined_sample,
                "session_deviation": round(combined_deviation, 1) if combined_sample > 0 else None,
                "improvement_score": round(calculate_improvement_score(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_f3bet, leak_severity
                ), 1) if combined_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_f3bet
                ) if combined_sample > 0 and is_leak else None,
                "within_gto_zone": abs(combined_deviation) < 5 if combined_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_f3bet
                ) == "overcorrected" if combined_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(combined_sample, 'facing_3bet')
            }
            scenario["priority_score"] = calculate_priority_score(scenario)
            scenarios.append(scenario)

    # ============================================
    # CALCULATE SUMMARY
    # ============================================
    leaks_only = [s for s in scenarios if s["is_leak"]]
    leaks_with_data = [s for s in leaks_only if s["session_sample"] and s["session_sample"] > 0]

    improved = len([s for s in leaks_with_data if s["improvement_status"] == "improved"])
    same = len([s for s in leaks_with_data if s["improvement_status"] == "same"])
    worse = len([s for s in leaks_with_data if s["improvement_status"] == "worse"])
    overcorrected = len([s for s in leaks_with_data if s["improvement_status"] == "overcorrected"])

    leak_scores = [s["improvement_score"] for s in leaks_with_data if s["improvement_score"] is not None]
    overall_score = sum(leak_scores) / len(leak_scores) if leak_scores else 50.0

    if overall_score >= 80:
        grade = "A"
    elif overall_score >= 65:
        grade = "B"
    elif overall_score >= 50:
        grade = "C"
    elif overall_score >= 35:
        grade = "D"
    else:
        grade = "F"

    # Priority leaks: sorted by priority_score descending
    priority_leaks = sorted(
        [s for s in leaks_only if s.get("priority_score", 0) > 0],
        key=lambda x: x.get("priority_score", 0),
        reverse=True
    )

    return {
        "session_ids": session_ids,
        "player_name": player_name,
        "total_hands": total_hands,
        "total_profit_bb": round(total_profit_bb, 2),
        "session_count": len(sessions),
        "date_range": date_range,
        "confidence": confidence,

        "aggregated": {
            "scenarios": scenarios,
            "priority_leaks": priority_leaks,
            "summary": {
                "total_scenarios": len(scenarios),
                "scenarios_with_leaks": len(leaks_only),
                "scenarios_improved": improved,
                "scenarios_same": same,
                "scenarios_worse": worse,
                "scenarios_overcorrected": overcorrected,
                "overall_improvement_score": round(overall_score, 1),
                "session_grade": grade
            }
        },

        "session_trends": session_trends
    }


# ============================================================================
# POSITIONAL P/L BREAKDOWN - Phase 1 Feature
# ============================================================================

@router.get("/{session_id}/positional-pl")
def get_session_positional_pl(session_id: int, db: Session = Depends(get_db)):
    """
    Get profit/loss breakdown by position for a session.

    Returns bb won/lost by position with hand counts and bb/100 rates.
    Includes comparison to expected values (BTN should be most profitable).
    """
    # Get session info including big blind size
    session_query = text("""
        SELECT s.session_id, s.player_name, s.total_hands, s.table_stakes,
               rh.big_blind
        FROM sessions s
        LEFT JOIN player_hand_summary phs ON phs.session_id = s.session_id
        LEFT JOIN raw_hands rh ON rh.hand_id = phs.hand_id
        WHERE s.session_id = :session_id
        LIMIT 1
    """)
    session_result = db.execute(session_query, {"session_id": session_id})
    session = session_result.first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    player_name = session._mapping["player_name"]
    big_blind = float(session._mapping["big_blind"] or 0.02)  # Default to 0.02

    # Get positional P/L data
    pl_query = text("""
        SELECT
            phs.position,
            COUNT(*) as hands,
            COALESCE(SUM(phs.profit_loss), 0) as total_profit,
            COALESCE(SUM(CASE WHEN phs.won_hand THEN 1 ELSE 0 END), 0) as hands_won
        FROM player_hand_summary phs
        WHERE phs.session_id = :session_id
        AND phs.player_name = :player_name
        AND phs.position IS NOT NULL
        GROUP BY phs.position
        ORDER BY
            CASE phs.position
                WHEN 'BTN' THEN 1
                WHEN 'CO' THEN 2
                WHEN 'MP' THEN 3
                WHEN 'UTG' THEN 4
                WHEN 'SB' THEN 5
                WHEN 'BB' THEN 6
                ELSE 7
            END
    """)

    pl_result = db.execute(pl_query, {"session_id": session_id, "player_name": player_name})

    # Expected profit rates by position (bb/100 in typical cash game)
    # These are rough GTO expectations for winning players
    EXPECTED_BB_100 = {
        'BTN': 35,   # Most profitable position
        'CO': 15,    # Second most profitable
        'MP': 5,     # Slightly profitable
        'UTG': 0,    # Break-even on average
        'SB': -25,   # Loses money (posting blinds)
        'BB': -40,   # Loses most (posting blinds, OOP)
    }

    positions = []
    total_profit = 0
    total_hands = 0

    for row in pl_result:
        pos = row[0]
        hands = row[1] or 0
        profit_dollars = float(row[2] or 0)
        hands_won = row[3] or 0

        # Convert to bb
        profit_bb = profit_dollars / big_blind if big_blind > 0 else 0

        # Calculate bb/100
        bb_100 = (profit_bb / hands * 100) if hands > 0 else 0

        # Win rate
        win_rate = (hands_won / hands * 100) if hands > 0 else 0

        # Expected bb/100 for this position
        expected_bb_100 = EXPECTED_BB_100.get(pos, 0)

        # Performance vs expected
        vs_expected = bb_100 - expected_bb_100
        performance = "above" if vs_expected > 5 else "below" if vs_expected < -5 else "expected"

        positions.append({
            "position": pos,
            "hands": hands,
            "profit_bb": round(profit_bb, 1),
            "profit_dollars": round(profit_dollars, 2),
            "bb_100": round(bb_100, 1),
            "expected_bb_100": expected_bb_100,
            "vs_expected": round(vs_expected, 1),
            "performance": performance,
            "win_rate": round(win_rate, 1),
            "hands_won": hands_won
        })

        total_profit += profit_bb
        total_hands += hands

    # Sort positions in standard order
    position_order = ['BTN', 'CO', 'MP', 'UTG', 'SB', 'BB']
    positions_sorted = sorted(
        positions,
        key=lambda x: position_order.index(x['position']) if x['position'] in position_order else 99
    )

    # Find best and worst positions
    best_position = max(positions, key=lambda x: x['profit_bb']) if positions else None
    worst_position = min(positions, key=lambda x: x['profit_bb']) if positions else None

    return {
        "session_id": session_id,
        "player_name": player_name,
        "total_hands": total_hands,
        "total_profit_bb": round(total_profit, 1),
        "big_blind": big_blind,
        "positions": positions_sorted,
        "best_position": best_position["position"] if best_position else None,
        "worst_position": worst_position["position"] if worst_position else None,
        "summary": {
            "profitable_positions": len([p for p in positions if p['profit_bb'] > 0]),
            "losing_positions": len([p for p in positions if p['profit_bb'] < 0]),
            "above_expected": len([p for p in positions if p['performance'] == 'above']),
            "below_expected": len([p for p in positions if p['performance'] == 'below'])
        }
    }


# ============================================================================
# BIGGEST PREFLOP MISTAKES - Phase 1 Feature
# ============================================================================

@router.get("/{session_id}/preflop-mistakes")
def get_session_preflop_mistakes(session_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """
    Get the biggest preflop mistakes in a session based on GTO analysis.

    Returns hands where hero deviated from GTO, sorted by EV loss.
    """
    # Check if session exists
    session_query = text("SELECT session_id, player_name FROM sessions WHERE session_id = :session_id")
    result = db.execute(session_query, {"session_id": session_id})
    session = result.first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    player_name = session._mapping["player_name"]

    # Run GTO analysis
    analyzer = HeroGTOAnalyzer(db)
    analysis = analyzer.analyze_session(session_id)

    biggest_mistakes = analysis.get("biggest_mistakes", [])[:limit]

    # Enrich mistake data with additional context
    enriched_mistakes = []
    for mistake in biggest_mistakes:
        enriched = {
            "hand_id": mistake.get("hand_id"),
            "timestamp": mistake.get("timestamp"),
            "position": mistake.get("position"),
            "scenario": mistake.get("scenario"),
            "hole_cards": mistake.get("hero_hand"),
            "action_taken": mistake.get("action_taken"),
            "gto_action": mistake.get("gto_action"),
            "gto_frequency": mistake.get("gto_frequency"),
            "ev_loss_bb": mistake.get("ev_loss_bb"),
            "severity": mistake.get("mistake_severity"),
            "in_gto_range": mistake.get("hand_in_gto_range", False),
            "description": _generate_mistake_description(mistake)
        }
        enriched_mistakes.append(enriched)

    return {
        "session_id": session_id,
        "player_name": player_name,
        "total_mistakes": analysis.get("total_mistakes", 0),
        "total_ev_loss_bb": analysis.get("total_ev_loss_bb", 0),
        "mistakes_by_severity": analysis.get("mistakes_by_severity", {}),
        "mistakes": enriched_mistakes
    }


def _generate_mistake_description(mistake: dict) -> str:
    """Generate a human-readable description of the mistake."""
    action_taken = mistake.get("action_taken", "unknown")
    gto_action = mistake.get("gto_action", "unknown")
    gto_freq = mistake.get("gto_frequency", 0)
    position = mistake.get("position", "")
    scenario = mistake.get("scenario", "")
    hole_cards = mistake.get("hero_hand", "??")
    in_range = mistake.get("hand_in_gto_range", False)

    if action_taken == "fold" and gto_action in ["open", "call", "3bet", "4bet"]:
        if in_range:
            return f"Folded {hole_cards} in {scenario} when GTO says {gto_action} {gto_freq*100:.0f}% of the time"
        else:
            return f"Folded {hole_cards} in {scenario}, but GTO suggests {gto_action} {gto_freq*100:.0f}%"
    elif gto_action == "fold" and action_taken in ["open", "call", "3bet", "4bet"]:
        return f"Played {hole_cards} aggressively ({action_taken}) in {scenario}, but hand is outside GTO range"
    elif action_taken != gto_action:
        return f"Chose {action_taken} with {hole_cards} in {scenario}, but GTO prefers {gto_action} ({gto_freq*100:.0f}%)"
    else:
        return f"GTO deviation with {hole_cards} in {scenario}"


# ============================================================================
# GTO DEVIATION SCORE - Phase 1 Feature
# ============================================================================

@router.get("/{session_id}/gto-score")
def get_session_gto_score(session_id: int, db: Session = Depends(get_db)):
    """
    Calculate an overall GTO Deviation Score for a session.

    The score represents how closely the player's preflop decisions adhered to GTO.
    Score of 100 = perfect GTO play, 0 = completely off GTO.

    Components:
    1. Frequency Accuracy: How close player frequencies are to GTO (weighted by position importance)
    2. Mistake Penalty: Deductions based on number and severity of mistakes
    3. Range Compliance: Percentage of hands played that are in GTO range
    """
    # Get session info
    session_query = text("""
        SELECT s.session_id, s.player_name, s.total_hands
        FROM sessions s
        WHERE s.session_id = :session_id
    """)
    session_result = db.execute(session_query, {"session_id": session_id})
    session = session_result.first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    player_name = session._mapping["player_name"]
    total_hands = session._mapping["total_hands"] or 0

    # Get leak comparison data to calculate frequency accuracy
    leak_data = get_session_leak_comparison(session_id, db)
    scenarios = leak_data.get("scenarios", [])

    # Calculate Frequency Accuracy Score (0-100)
    frequency_scores = []
    position_weights = {
        'BTN': 1.5, 'CO': 1.3, 'SB': 1.4, 'BB': 1.6,
        'MP': 1.1, 'UTG': 1.0
    }

    for scenario in scenarios:
        if scenario.get("session_sample", 0) < 3:
            continue

        session_val = scenario.get("session_value")
        gto_val = scenario.get("gto_value")

        if session_val is None or gto_val is None or gto_val == 0:
            continue

        # Calculate accuracy (100 - percentage deviation, capped at 0)
        deviation = abs(session_val - gto_val)
        accuracy = max(0, 100 - deviation * 2)  # 50% deviation = 0 score

        # Apply position weight
        pos = scenario.get("position", "")
        weight = position_weights.get(pos, 1.0)

        frequency_scores.append({
            "score": accuracy,
            "weight": weight,
            "sample": scenario.get("session_sample", 0)
        })

    # Weighted average of frequency scores
    if frequency_scores:
        total_weighted_score = sum(s["score"] * s["weight"] * s["sample"] for s in frequency_scores)
        total_weight = sum(s["weight"] * s["sample"] for s in frequency_scores)
        frequency_accuracy = total_weighted_score / total_weight if total_weight > 0 else 50
    else:
        frequency_accuracy = 50  # Default if no data

    # Get mistake data
    analyzer = HeroGTOAnalyzer(db)
    gto_analysis = analyzer.analyze_session(session_id)

    total_mistakes = gto_analysis.get("total_mistakes", 0)
    total_ev_loss = gto_analysis.get("total_ev_loss_bb", 0)
    mistakes_by_severity = gto_analysis.get("mistakes_by_severity", {})

    # Calculate Mistake Penalty Score (0-100, where 100 = no mistakes)
    # Penalize based on mistakes per 100 hands and severity
    hands_analyzed = max(total_hands, 1)
    mistake_rate = (total_mistakes / hands_analyzed) * 100

    # Severity weights for penalty
    major_mistakes = mistakes_by_severity.get("major", 0)
    moderate_mistakes = mistakes_by_severity.get("moderate", 0)
    minor_mistakes = mistakes_by_severity.get("minor", 0)

    # Weighted mistake count
    weighted_mistakes = (major_mistakes * 3) + (moderate_mistakes * 2) + (minor_mistakes * 1)
    weighted_mistake_rate = (weighted_mistakes / hands_analyzed) * 100

    # Convert to score (exponential decay)
    mistake_penalty_score = max(0, 100 * math.exp(-weighted_mistake_rate * 0.1))

    # Calculate EV Loss Score (0-100)
    # Based on EV loss per 100 hands
    ev_loss_per_100 = (total_ev_loss / hands_analyzed) * 100 if hands_analyzed > 0 else 0
    ev_score = max(0, 100 - ev_loss_per_100 * 5)  # 20bb/100 loss = 0 score

    # Calculate Overall GTO Score (weighted combination)
    overall_score = (
        frequency_accuracy * 0.40 +  # 40% weight on frequency accuracy
        mistake_penalty_score * 0.35 +  # 35% weight on avoiding mistakes
        ev_score * 0.25  # 25% weight on EV preservation
    )

    # Determine grade
    if overall_score >= 90:
        grade = "A+"
        rating = "Elite GTO"
    elif overall_score >= 80:
        grade = "A"
        rating = "Strong GTO"
    elif overall_score >= 70:
        grade = "B+"
        rating = "Good GTO"
    elif overall_score >= 60:
        grade = "B"
        rating = "Above Average"
    elif overall_score >= 50:
        grade = "C"
        rating = "Average"
    elif overall_score >= 40:
        grade = "D"
        rating = "Below Average"
    else:
        grade = "F"
        rating = "Needs Work"

    # Identify weakest area
    component_scores = {
        "frequency_accuracy": frequency_accuracy,
        "mistake_avoidance": mistake_penalty_score,
        "ev_preservation": ev_score
    }
    weakest_area = min(component_scores, key=component_scores.get)

    # Generate improvement suggestion
    improvement_suggestions = {
        "frequency_accuracy": "Focus on adjusting your opening and defense frequencies to match GTO ranges",
        "mistake_avoidance": "Review the biggest mistakes and focus on those specific spots in study",
        "ev_preservation": "Your EV leaks are significant - prioritize fixing high-EV situations"
    }

    return {
        "session_id": session_id,
        "player_name": player_name,
        "total_hands": total_hands,

        # Overall score
        "gto_score": round(overall_score, 1),
        "grade": grade,
        "rating": rating,

        # Component scores
        "components": {
            "frequency_accuracy": {
                "score": round(frequency_accuracy, 1),
                "weight": 0.40,
                "description": "How close your frequencies are to GTO"
            },
            "mistake_avoidance": {
                "score": round(mistake_penalty_score, 1),
                "weight": 0.35,
                "description": "Penalty for GTO deviations"
            },
            "ev_preservation": {
                "score": round(ev_score, 1),
                "weight": 0.25,
                "description": "EV lost due to mistakes"
            }
        },

        # Mistake summary
        "mistakes_summary": {
            "total": total_mistakes,
            "major": major_mistakes,
            "moderate": moderate_mistakes,
            "minor": minor_mistakes,
            "ev_loss_bb": round(total_ev_loss, 2)
        },

        # Improvement info
        "weakest_area": weakest_area,
        "improvement_suggestion": improvement_suggestions.get(weakest_area, ""),

        # Confidence
        "confidence": "high" if total_hands >= 100 else "moderate" if total_hands >= 50 else "low"
    }


# ============================================================================
# MULTI-SESSION AGGREGATE ENDPOINTS
# ============================================================================

class MultiSessionRequest(BaseModel):
    session_ids: List[int]


@router.post("/aggregate/positional-pl")
def get_aggregate_positional_pl(request: MultiSessionRequest, db: Session = Depends(get_db)):
    """
    Get aggregated positional P/L across multiple sessions.
    """
    session_ids = request.session_ids
    if not session_ids:
        raise HTTPException(status_code=400, detail="No session IDs provided")

    # Get session info
    session_query = text("""
        SELECT s.player_name, rh.big_blind
        FROM sessions s
        LEFT JOIN player_hand_summary phs ON phs.session_id = s.session_id
        LEFT JOIN raw_hands rh ON rh.hand_id = phs.hand_id
        WHERE s.session_id = ANY(:session_ids)
        LIMIT 1
    """)
    session_result = db.execute(session_query, {"session_ids": session_ids})
    session = session_result.first()

    if not session:
        raise HTTPException(status_code=404, detail="No sessions found")

    player_name = session._mapping["player_name"]
    big_blind = float(session._mapping["big_blind"] or 0.02)

    # Get aggregated positional P/L
    pl_query = text("""
        SELECT
            phs.position,
            COUNT(*) as hands,
            COALESCE(SUM(phs.profit_loss), 0) as total_profit,
            COALESCE(SUM(CASE WHEN phs.won_hand THEN 1 ELSE 0 END), 0) as hands_won
        FROM player_hand_summary phs
        JOIN sessions s ON s.session_id = phs.session_id
        WHERE phs.session_id = ANY(:session_ids)
        AND phs.player_name = s.player_name
        AND phs.position IS NOT NULL
        GROUP BY phs.position
    """)

    pl_result = db.execute(pl_query, {"session_ids": session_ids})

    EXPECTED_BB_100 = {
        'BTN': 35, 'CO': 15, 'MP': 5, 'UTG': 0, 'SB': -25, 'BB': -40,
    }

    positions = []
    total_profit = 0
    total_hands = 0

    for row in pl_result:
        pos = row[0]
        hands = row[1] or 0
        profit_dollars = float(row[2] or 0)
        hands_won = row[3] or 0

        profit_bb = profit_dollars / big_blind if big_blind > 0 else 0
        bb_100 = (profit_bb / hands * 100) if hands > 0 else 0
        win_rate = (hands_won / hands * 100) if hands > 0 else 0
        expected_bb_100 = EXPECTED_BB_100.get(pos, 0)
        vs_expected = bb_100 - expected_bb_100
        performance = "above" if vs_expected > 5 else "below" if vs_expected < -5 else "expected"

        positions.append({
            "position": pos,
            "hands": hands,
            "profit_bb": round(profit_bb, 1),
            "profit_dollars": round(profit_dollars, 2),
            "bb_100": round(bb_100, 1),
            "expected_bb_100": expected_bb_100,
            "vs_expected": round(vs_expected, 1),
            "performance": performance,
            "win_rate": round(win_rate, 1),
            "hands_won": hands_won
        })

        total_profit += profit_bb
        total_hands += hands

    position_order = ['BTN', 'CO', 'MP', 'UTG', 'SB', 'BB']
    positions_sorted = sorted(
        positions,
        key=lambda x: position_order.index(x['position']) if x['position'] in position_order else 99
    )

    best_position = max(positions, key=lambda x: x['profit_bb']) if positions else None
    worst_position = min(positions, key=lambda x: x['profit_bb']) if positions else None

    return {
        "session_count": len(session_ids),
        "player_name": player_name,
        "total_hands": total_hands,
        "total_profit_bb": round(total_profit, 1),
        "big_blind": big_blind,
        "positions": positions_sorted,
        "best_position": best_position["position"] if best_position else None,
        "worst_position": worst_position["position"] if worst_position else None,
        "summary": {
            "profitable_positions": len([p for p in positions if p['profit_bb'] > 0]),
            "losing_positions": len([p for p in positions if p['profit_bb'] < 0]),
            "above_expected": len([p for p in positions if p['performance'] == 'above']),
            "below_expected": len([p for p in positions if p['performance'] == 'below'])
        }
    }


@router.post("/aggregate/preflop-mistakes")
def get_aggregate_preflop_mistakes(request: MultiSessionRequest, limit: int = 10, db: Session = Depends(get_db)):
    """
    Get aggregated biggest preflop mistakes across multiple sessions.
    """
    session_ids = request.session_ids
    if not session_ids:
        raise HTTPException(status_code=400, detail="No session IDs provided")

    # Get player name
    session_query = text("SELECT player_name FROM sessions WHERE session_id = ANY(:session_ids) LIMIT 1")
    result = db.execute(session_query, {"session_ids": session_ids})
    session = result.first()
    if not session:
        raise HTTPException(status_code=404, detail="No sessions found")

    player_name = session._mapping["player_name"]

    # Analyze all sessions
    analyzer = HeroGTOAnalyzer(db)
    all_mistakes = []
    total_ev_loss = 0
    mistakes_by_severity = {"major": 0, "moderate": 0, "minor": 0}

    for session_id in session_ids:
        analysis = analyzer.analyze_session(session_id)
        all_mistakes.extend(analysis.get("biggest_mistakes", []))
        total_ev_loss += analysis.get("total_ev_loss_bb", 0)
        for sev, count in analysis.get("mistakes_by_severity", {}).items():
            mistakes_by_severity[sev] = mistakes_by_severity.get(sev, 0) + count

    # Sort by EV loss and take top N
    all_mistakes.sort(key=lambda x: x.get('ev_loss_bb', 0), reverse=True)
    biggest_mistakes = all_mistakes[:limit]

    enriched_mistakes = []
    for mistake in biggest_mistakes:
        enriched = {
            "hand_id": mistake.get("hand_id"),
            "timestamp": mistake.get("timestamp"),
            "position": mistake.get("position"),
            "scenario": mistake.get("scenario"),
            "hole_cards": mistake.get("hero_hand"),
            "action_taken": mistake.get("action_taken"),
            "gto_action": mistake.get("gto_action"),
            "gto_frequency": mistake.get("gto_frequency"),
            "ev_loss_bb": mistake.get("ev_loss_bb"),
            "severity": mistake.get("mistake_severity"),
            "in_gto_range": mistake.get("hand_in_gto_range", False),
            "description": _generate_mistake_description(mistake)
        }
        enriched_mistakes.append(enriched)

    return {
        "session_count": len(session_ids),
        "player_name": player_name,
        "total_mistakes": len(all_mistakes),
        "total_ev_loss_bb": round(total_ev_loss, 2),
        "mistakes_by_severity": mistakes_by_severity,
        "mistakes": enriched_mistakes
    }


@router.post("/aggregate/gto-score")
def get_aggregate_gto_score(request: MultiSessionRequest, db: Session = Depends(get_db)):
    """
    Get aggregated GTO score across multiple sessions.
    """
    session_ids = request.session_ids
    if not session_ids:
        raise HTTPException(status_code=400, detail="No session IDs provided")

    # Get total hands and player name
    session_query = text("""
        SELECT s.player_name, COALESCE(SUM(s.total_hands), 0) as total_hands
        FROM sessions s
        WHERE s.session_id = ANY(:session_ids)
        GROUP BY s.player_name
        LIMIT 1
    """)
    result = db.execute(session_query, {"session_ids": session_ids})
    session = result.first()

    if not session:
        raise HTTPException(status_code=404, detail="No sessions found")

    player_name = session._mapping["player_name"]
    total_hands = int(session._mapping["total_hands"] or 0)

    # Get aggregated leak comparison using existing group analysis
    group_data = get_session_group_analysis(MultiSessionRequest(session_ids=session_ids), db)
    scenarios = group_data.get("aggregated", {}).get("scenarios", [])

    # Calculate Frequency Accuracy Score
    frequency_scores = []
    position_weights = {
        'BTN': 1.5, 'CO': 1.3, 'SB': 1.4, 'BB': 1.6,
        'MP': 1.1, 'UTG': 1.0
    }

    for scenario in scenarios:
        if scenario.get("session_sample", 0) < 3:
            continue

        session_val = scenario.get("session_value")
        gto_val = scenario.get("gto_value")

        if session_val is None or gto_val is None or gto_val == 0:
            continue

        deviation = abs(session_val - gto_val)
        accuracy = max(0, 100 - deviation * 2)

        pos = scenario.get("position", "")
        weight = position_weights.get(pos, 1.0)

        frequency_scores.append({
            "score": accuracy,
            "weight": weight,
            "sample": scenario.get("session_sample", 0)
        })

    if frequency_scores:
        total_weighted_score = sum(s["score"] * s["weight"] * s["sample"] for s in frequency_scores)
        total_weight = sum(s["weight"] * s["sample"] for s in frequency_scores)
        frequency_accuracy = total_weighted_score / total_weight if total_weight > 0 else 50
    else:
        frequency_accuracy = 50

    # Get aggregated mistake data
    total_mistakes = 0
    total_ev_loss = 0
    mistakes_by_severity = {"major": 0, "moderate": 0, "minor": 0}

    analyzer = HeroGTOAnalyzer(db)
    for session_id in session_ids:
        analysis = analyzer.analyze_session(session_id)
        total_mistakes += analysis.get("total_mistakes", 0)
        total_ev_loss += analysis.get("total_ev_loss_bb", 0)
        for sev, count in analysis.get("mistakes_by_severity", {}).items():
            mistakes_by_severity[sev] = mistakes_by_severity.get(sev, 0) + count

    major_mistakes = mistakes_by_severity.get("major", 0)
    moderate_mistakes = mistakes_by_severity.get("moderate", 0)
    minor_mistakes = mistakes_by_severity.get("minor", 0)

    hands_analyzed = max(total_hands, 1)
    weighted_mistakes = (major_mistakes * 3) + (moderate_mistakes * 2) + (minor_mistakes * 1)
    weighted_mistake_rate = (weighted_mistakes / hands_analyzed) * 100
    mistake_penalty_score = max(0, 100 * math.exp(-weighted_mistake_rate * 0.1))

    ev_loss_per_100 = (total_ev_loss / hands_analyzed) * 100 if hands_analyzed > 0 else 0
    ev_score = max(0, 100 - ev_loss_per_100 * 5)

    overall_score = (
        frequency_accuracy * 0.40 +
        mistake_penalty_score * 0.35 +
        ev_score * 0.25
    )

    if overall_score >= 90:
        grade, rating = "A+", "Elite GTO"
    elif overall_score >= 80:
        grade, rating = "A", "Strong GTO"
    elif overall_score >= 70:
        grade, rating = "B+", "Good GTO"
    elif overall_score >= 60:
        grade, rating = "B", "Above Average"
    elif overall_score >= 50:
        grade, rating = "C", "Average"
    elif overall_score >= 40:
        grade, rating = "D", "Below Average"
    else:
        grade, rating = "F", "Needs Work"

    component_scores = {
        "frequency_accuracy": frequency_accuracy,
        "mistake_avoidance": mistake_penalty_score,
        "ev_preservation": ev_score
    }
    weakest_area = min(component_scores, key=component_scores.get)

    improvement_suggestions = {
        "frequency_accuracy": "Focus on adjusting your opening and defense frequencies to match GTO ranges",
        "mistake_avoidance": "Review the biggest mistakes and focus on those specific spots in study",
        "ev_preservation": "Your EV leaks are significant - prioritize fixing high-EV situations"
    }

    return {
        "session_count": len(session_ids),
        "player_name": player_name,
        "total_hands": total_hands,
        "gto_score": round(overall_score, 1),
        "grade": grade,
        "rating": rating,
        "components": {
            "frequency_accuracy": {
                "score": round(frequency_accuracy, 1),
                "weight": 0.40,
                "description": "How close your frequencies are to GTO"
            },
            "mistake_avoidance": {
                "score": round(mistake_penalty_score, 1),
                "weight": 0.35,
                "description": "Penalty for GTO deviations"
            },
            "ev_preservation": {
                "score": round(ev_score, 1),
                "weight": 0.25,
                "description": "EV lost due to mistakes"
            }
        },
        "mistakes_summary": {
            "total": total_mistakes,
            "major": major_mistakes,
            "moderate": moderate_mistakes,
            "minor": minor_mistakes,
            "ev_loss_bb": round(total_ev_loss, 2)
        },
        "weakest_area": weakest_area,
        "improvement_suggestion": improvement_suggestions.get(weakest_area, ""),
        "confidence": "high" if total_hands >= 200 else "moderate" if total_hands >= 100 else "low"
    }
