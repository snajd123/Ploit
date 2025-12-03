"""
My Game API Endpoints

Endpoints for hero-specific analysis with hole cards.
Returns data only for players matching configured hero nicknames.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..services.hero_detection import get_hero_nicknames, is_hero

router = APIRouter(prefix="/api/my-game", tags=["my-game"])


class HeroSessionResponse(BaseModel):
    """Session response for hero"""
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


class HeroStatsResponse(BaseModel):
    """Hero's aggregated stats"""
    player_name: str
    total_hands: int
    sessions_count: int
    total_profit_bb: float
    avg_bb_100: float
    vpip_pct: float
    pfr_pct: float
    three_bet_pct: float
    fold_to_3bet_pct: Optional[float]
    player_type: Optional[str]
    first_session: Optional[datetime]
    last_session: Optional[datetime]


class MyGameOverview(BaseModel):
    """Overview of hero's performance across all nicknames"""
    hero_nicknames: List[str]
    total_sessions: int
    total_hands: int
    total_profit_bb: float
    avg_bb_100: float
    stats_by_nickname: List[HeroStatsResponse]


@router.get("/overview")
def get_mygame_overview(db: Session = Depends(get_db)) -> MyGameOverview:
    """
    Get overview of hero's performance across all configured nicknames.
    """
    hero_nicknames = get_hero_nicknames(db)

    if not hero_nicknames:
        return MyGameOverview(
            hero_nicknames=[],
            total_sessions=0,
            total_hands=0,
            total_profit_bb=0,
            avg_bb_100=0,
            stats_by_nickname=[]
        )

    # Convert to list for SQL IN clause
    nicknames_list = list(hero_nicknames)

    # Get aggregated session stats for all heroes
    result = db.execute(text("""
        SELECT
            s.player_name,
            COUNT(s.session_id) as sessions_count,
            COALESCE(SUM(s.total_hands), 0) as total_hands,
            COALESCE(SUM(s.profit_loss_bb), 0) as total_profit_bb,
            MIN(s.start_time) as first_session,
            MAX(s.end_time) as last_session,
            ps.vpip_pct,
            ps.pfr_pct,
            ps.three_bet_pct,
            ps.fold_to_three_bet_pct,
            ps.player_type
        FROM sessions s
        LEFT JOIN player_stats ps ON ps.player_name = s.player_name
        WHERE LOWER(s.player_name) = ANY(:nicknames)
        GROUP BY s.player_name, ps.vpip_pct, ps.pfr_pct, ps.three_bet_pct, ps.fold_to_three_bet_pct, ps.player_type
    """), {"nicknames": nicknames_list})

    rows = result.fetchall()

    stats_by_nickname = []
    total_sessions = 0
    total_hands = 0
    total_profit_bb = 0.0

    for row in rows:
        hands = row.total_hands or 0
        profit = float(row.total_profit_bb or 0)
        sessions = row.sessions_count or 0

        total_sessions += sessions
        total_hands += hands
        total_profit_bb += profit

        stats_by_nickname.append(HeroStatsResponse(
            player_name=row.player_name,
            total_hands=hands,
            sessions_count=sessions,
            total_profit_bb=profit,
            avg_bb_100=round((profit / hands * 100), 2) if hands > 0 else 0,
            vpip_pct=float(row.vpip_pct or 0),
            pfr_pct=float(row.pfr_pct or 0),
            three_bet_pct=float(row.three_bet_pct or 0),
            fold_to_3bet_pct=float(row.fold_to_three_bet_pct) if row.fold_to_three_bet_pct else None,
            player_type=row.player_type,
            first_session=row.first_session,
            last_session=row.last_session
        ))

    avg_bb_100 = round((total_profit_bb / total_hands * 100), 2) if total_hands > 0 else 0

    return MyGameOverview(
        hero_nicknames=[n for n in nicknames_list],
        total_sessions=total_sessions,
        total_hands=total_hands,
        total_profit_bb=round(total_profit_bb, 2),
        avg_bb_100=avg_bb_100,
        stats_by_nickname=stats_by_nickname
    )


@router.get("/sessions")
def get_mygame_sessions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
) -> List[HeroSessionResponse]:
    """
    Get all sessions for hero nicknames.
    """
    hero_nicknames = list(get_hero_nicknames(db))

    if not hero_nicknames:
        return []

    result = db.execute(text("""
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
            table_name
        FROM sessions
        WHERE LOWER(player_name) = ANY(:nicknames)
        ORDER BY start_time DESC
        LIMIT :limit OFFSET :offset
    """), {"nicknames": hero_nicknames, "limit": limit, "offset": offset})

    return [
        HeroSessionResponse(
            session_id=row.session_id,
            player_name=row.player_name,
            start_time=row.start_time,
            end_time=row.end_time,
            duration_minutes=row.duration_minutes or 0,
            total_hands=row.total_hands or 0,
            profit_loss_bb=float(row.profit_loss_bb or 0),
            bb_100=float(row.bb_100 or 0),
            table_stakes=row.table_stakes or 'Unknown',
            table_name=row.table_name
        )
        for row in result.fetchall()
    ]


@router.get("/check/{player_name}")
def check_if_my_player(player_name: str, db: Session = Depends(get_db)):
    """
    Check if a player name belongs to the hero.
    """
    return {
        "is_hero": is_hero(player_name, db),
        "player_name": player_name
    }
