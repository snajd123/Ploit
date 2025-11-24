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
    stats_query = text("""
        SELECT
            COUNT(*) as total_hands,
            SUM(CASE WHEN vpip THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as vpip_pct,
            SUM(CASE WHEN pfr THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as pfr_pct,
            SUM(CASE WHEN made_three_bet THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN faced_raise THEN 1 ELSE 0 END), 0) * 100 as three_bet_pct,
            SUM(CASE WHEN folded_to_three_bet THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN faced_three_bet THEN 1 ELSE 0 END), 0) * 100 as fold_to_3bet_pct,
            SUM(CASE WHEN saw_flop THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as saw_flop_pct,
            SUM(CASE WHEN cbet_made_flop THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN cbet_opportunity_flop THEN 1 ELSE 0 END), 0) * 100 as cbet_flop_pct,
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
        "profit_loss_bb": float(session._mapping["profit_loss_bb"]),
        "bb_100": float(session._mapping["bb_100"]),
        "duration_minutes": session._mapping["duration_minutes"],
        "vpip_pct": round(float(stats["vpip_pct"] or 0), 1),
        "pfr_pct": round(float(stats["pfr_pct"] or 0), 1),
        "three_bet_pct": round(float(stats["three_bet_pct"] or 0), 1),
        "fold_to_3bet_pct": round(float(stats["fold_to_3bet_pct"] or 0), 1),
        "saw_flop_pct": round(float(stats["saw_flop_pct"] or 0), 1),
        "cbet_flop_pct": round(float(stats["cbet_flop_pct"] or 0), 1)
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
