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

def calculate_improvement_score(
    overall_value: float,
    session_value: float,
    gto_value: float,
    session_sample: int,
    min_sample: int
) -> float:
    """
    Calculate improvement score (0-100).
    50 = no change, >50 = improved, <50 = worse
    """
    overall_distance = abs(overall_value - gto_value)
    session_distance = abs(session_value - gto_value)

    if overall_distance == 0:
        return 50.0  # No leak to improve

    improvement_ratio = (overall_distance - session_distance) / overall_distance
    confidence = min(1.0, session_sample / (min_sample * 2))

    return 50 + (improvement_ratio * 50 * confidence)


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

    if overall_side != session_side and abs(session_value - gto_value) > 5:
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


def get_confidence_level(sample: int, min_sample: int) -> str:
    """Determine confidence level based on sample size"""
    if sample < min_sample:
        return "insufficient"
    elif sample < min_sample * 2:
        return "low"
    elif sample < min_sample * 4:
        return "moderate"
    else:
        return "high"


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
    min_sample_opening = 15
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

        scenarios.append({
            "scenario_id": f"opening_{pos}",
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
            "leak_severity": get_leak_severity(overall_deviation) if is_leak else "none",

            "gto_value": round(gto_value, 1),

            "session_value": round(session_value, 1) if session_sample > 0 else None,
            "session_sample": session_sample,
            "session_deviation": round(session_deviation, 1) if session_sample > 0 else None,

            "improvement_score": round(calculate_improvement_score(
                overall_value, session_value, gto_value, session_sample, min_sample_opening
            ), 1) if session_sample > 0 and is_leak else None,
            "improvement_status": get_improvement_status(
                overall_value, session_value, gto_value, session_sample, min_sample_opening
            ) if session_sample > 0 and is_leak else None,
            "within_gto_zone": abs(session_deviation) < 5 if session_sample > 0 else None,
            "overcorrected": get_improvement_status(
                overall_value, session_value, gto_value, session_sample, min_sample_opening
            ) == "overcorrected" if session_sample > 0 and is_leak else False,
            "confidence_level": get_confidence_level(session_sample, min_sample_opening)
        })

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
    min_sample_defense = 10
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

            scenarios.append({
                "scenario_id": f"defense_{pos}_{action}",
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
                "leak_severity": get_leak_severity(overall_deviation) if is_leak else "none",

                "gto_value": round(gto_value, 1),

                "session_value": round(session_value, 1) if session_sample > 0 else None,
                "session_sample": session_sample,
                "session_deviation": round(session_deviation, 1) if session_sample > 0 else None,

                "improvement_score": round(calculate_improvement_score(
                    overall_value, session_value, gto_value, session_sample, min_sample_defense
                ), 1) if session_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_defense
                ) if session_sample > 0 and is_leak else None,
                "within_gto_zone": abs(session_deviation) < 5 if session_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_defense
                ) == "overcorrected" if session_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(session_sample, min_sample_defense)
            })

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
    min_sample_f3bet = 8
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

            scenarios.append({
                "scenario_id": f"facing_3bet_{pos}_{action}",
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
                "leak_severity": get_leak_severity(overall_deviation) if is_leak else "none",

                "gto_value": round(gto_value, 1),

                "session_value": round(session_value, 1) if session_sample > 0 else None,
                "session_sample": session_sample,
                "session_deviation": round(session_deviation, 1) if session_sample > 0 else None,

                "improvement_score": round(calculate_improvement_score(
                    overall_value, session_value, gto_value, session_sample, min_sample_f3bet
                ), 1) if session_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_f3bet
                ) if session_sample > 0 and is_leak else None,
                "within_gto_zone": abs(session_deviation) < 5 if session_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, session_value, gto_value, session_sample, min_sample_f3bet
                ) == "overcorrected" if session_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(session_sample, min_sample_f3bet)
            })

    # ============================================
    # CALCULATE SUMMARY
    # ============================================
    leaks_only = [s for s in scenarios if s["is_leak"]]
    leaks_with_session = [s for s in leaks_only if s["session_sample"] and s["session_sample"] > 0]

    improved = len([s for s in leaks_with_session if s["improvement_status"] == "improved"])
    same = len([s for s in leaks_with_session if s["improvement_status"] == "same"])
    worse = len([s for s in leaks_with_session if s["improvement_status"] == "worse"])
    overcorrected = len([s for s in leaks_with_session if s["improvement_status"] == "overcorrected"])

    # Calculate overall improvement score (average of leak improvement scores)
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

    return {
        "session_id": session_id,
        "player_name": player_name,
        "session_hands": session_hands,
        "confidence": confidence,

        "scenarios": scenarios,

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
    min_sample_opening = 15
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

        scenarios.append({
            "scenario_id": f"opening_{pos}",
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
            "leak_severity": get_leak_severity(overall_deviation) if is_leak else "none",
            "gto_value": round(gto_value, 1),
            "session_value": round(combined_value, 1) if combined_sample > 0 else None,
            "session_sample": combined_sample,
            "session_deviation": round(combined_deviation, 1) if combined_sample > 0 else None,
            "improvement_score": round(calculate_improvement_score(
                overall_value, combined_value, gto_value, combined_sample, min_sample_opening
            ), 1) if combined_sample > 0 and is_leak else None,
            "improvement_status": get_improvement_status(
                overall_value, combined_value, gto_value, combined_sample, min_sample_opening
            ) if combined_sample > 0 and is_leak else None,
            "within_gto_zone": abs(combined_deviation) < 5 if combined_sample > 0 else None,
            "overcorrected": get_improvement_status(
                overall_value, combined_value, gto_value, combined_sample, min_sample_opening
            ) == "overcorrected" if combined_sample > 0 and is_leak else False,
            "confidence_level": get_confidence_level(combined_sample, min_sample_opening)
        })

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

    min_sample_defense = 10
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

            scenarios.append({
                "scenario_id": f"defense_{pos}_{action}",
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
                "leak_severity": get_leak_severity(overall_deviation) if is_leak else "none",
                "gto_value": round(gto_value, 1),
                "session_value": round(combined_value, 1) if combined_sample > 0 else None,
                "session_sample": combined_sample,
                "session_deviation": round(combined_deviation, 1) if combined_sample > 0 else None,
                "improvement_score": round(calculate_improvement_score(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_defense
                ), 1) if combined_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_defense
                ) if combined_sample > 0 and is_leak else None,
                "within_gto_zone": abs(combined_deviation) < 5 if combined_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_defense
                ) == "overcorrected" if combined_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(combined_sample, min_sample_defense)
            })

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

    min_sample_f3bet = 8
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

            scenarios.append({
                "scenario_id": f"facing_3bet_{pos}_{action}",
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
                "leak_severity": get_leak_severity(overall_deviation) if is_leak else "none",
                "gto_value": round(gto_value, 1),
                "session_value": round(combined_value, 1) if combined_sample > 0 else None,
                "session_sample": combined_sample,
                "session_deviation": round(combined_deviation, 1) if combined_sample > 0 else None,
                "improvement_score": round(calculate_improvement_score(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_f3bet
                ), 1) if combined_sample > 0 and is_leak else None,
                "improvement_status": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_f3bet
                ) if combined_sample > 0 and is_leak else None,
                "within_gto_zone": abs(combined_deviation) < 5 if combined_sample > 0 else None,
                "overcorrected": get_improvement_status(
                    overall_value, combined_value, gto_value, combined_sample, min_sample_f3bet
                ) == "overcorrected" if combined_sample > 0 and is_leak else False,
                "confidence_level": get_confidence_level(combined_sample, min_sample_f3bet)
            })

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
