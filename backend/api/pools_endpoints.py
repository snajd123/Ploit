"""
Pools API Endpoints

Endpoints for opponent analysis grouped by site + stakes.
Uses aggregate GTO frequencies (no hole cards required).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..services.hero_detection import get_hero_nicknames, detect_site_from_hand_text, get_pool_id, get_pool_display_name

router = APIRouter(prefix="/api/pools", tags=["pools"])


class PoolSummary(BaseModel):
    """Summary of a player pool"""
    pool_id: str
    display_name: str
    site: str
    stake_level: str
    player_count: int
    total_hands: int
    avg_vpip: float
    avg_pfr: float
    avg_3bet: float


class PoolPlayer(BaseModel):
    """Player within a pool"""
    player_name: str
    total_hands: int
    vpip_pct: float
    pfr_pct: float
    three_bet_pct: float
    fold_to_3bet_pct: Optional[float]
    player_type: Optional[str]


class PoolDetail(BaseModel):
    """Detailed pool information"""
    pool_id: str
    display_name: str
    site: str
    stake_level: str
    player_count: int
    total_hands: int
    avg_stats: Dict[str, float]
    players: List[PoolPlayer]


@router.get("/", response_model=List[PoolSummary])
def get_pools(db: Session = Depends(get_db)) -> List[PoolSummary]:
    """
    Get all pools (grouped by site + stake level), excluding hero players.
    """
    hero_nicknames = list(get_hero_nicknames(db))

    # Get all non-hero players with their stats and stake level
    query = """
        WITH player_stakes AS (
            SELECT DISTINCT ON (ps.player_name)
                ps.player_name,
                ps.total_hands,
                ps.vpip_pct,
                ps.pfr_pct,
                ps.three_bet_pct,
                s.table_stakes
            FROM player_stats ps
            LEFT JOIN sessions s ON s.player_name = ps.player_name
            WHERE ps.total_hands > 0
    """

    params = {}
    if hero_nicknames:
        query += " AND LOWER(ps.player_name) != ALL(:hero_nicknames)"
        params["hero_nicknames"] = hero_nicknames

    query += """
            ORDER BY ps.player_name, s.start_time DESC
        )
        SELECT
            COALESCE(table_stakes, 'Unknown') as stake_level,
            COUNT(*) as player_count,
            COALESCE(SUM(total_hands), 0) as total_hands,
            COALESCE(AVG(vpip_pct), 0) as avg_vpip,
            COALESCE(AVG(pfr_pct), 0) as avg_pfr,
            COALESCE(AVG(three_bet_pct), 0) as avg_3bet
        FROM player_stakes
        GROUP BY table_stakes
        ORDER BY total_hands DESC
    """

    result = db.execute(text(query), params)

    pools = []
    for row in result.fetchall():
        stake = row.stake_level or 'Unknown'
        # For now, assume PokerStars since that's what the data shows
        site = 'PokerStars'
        pool_id = get_pool_id(site, stake)
        display_name = get_pool_display_name(site, stake)

        pools.append(PoolSummary(
            pool_id=pool_id,
            display_name=display_name,
            site=site,
            stake_level=stake,
            player_count=row.player_count,
            total_hands=row.total_hands,
            avg_vpip=round(float(row.avg_vpip), 1),
            avg_pfr=round(float(row.avg_pfr), 1),
            avg_3bet=round(float(row.avg_3bet), 1)
        ))

    return pools


@router.get("/{stake_level}", response_model=PoolDetail)
def get_pool_detail(
    stake_level: str,
    limit: int = 50,
    sort_by: str = "total_hands",
    db: Session = Depends(get_db)
) -> PoolDetail:
    """
    Get detailed information about a specific pool.
    """
    hero_nicknames = list(get_hero_nicknames(db))

    # Get all players in this stake level
    query = """
        WITH player_stakes AS (
            SELECT DISTINCT ON (ps.player_name)
                ps.player_name,
                ps.total_hands,
                ps.vpip_pct,
                ps.pfr_pct,
                ps.three_bet_pct,
                ps.fold_to_three_bet_pct,
                ps.player_type,
                s.table_stakes
            FROM player_stats ps
            LEFT JOIN sessions s ON s.player_name = ps.player_name
            WHERE ps.total_hands > 0 AND COALESCE(s.table_stakes, 'Unknown') = :stake_level
    """

    params = {"stake_level": stake_level, "limit": limit}
    if hero_nicknames:
        query += " AND LOWER(ps.player_name) != ALL(:hero_nicknames)"
        params["hero_nicknames"] = hero_nicknames

    query += """
            ORDER BY ps.player_name, s.start_time DESC
        )
        SELECT * FROM player_stakes
    """

    # Add sorting
    valid_sort = {"total_hands", "vpip_pct", "pfr_pct", "three_bet_pct", "player_name"}
    if sort_by in valid_sort:
        query += f" ORDER BY {sort_by} DESC"
    else:
        query += " ORDER BY total_hands DESC"

    query += " LIMIT :limit"

    result = db.execute(text(query), params)
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Pool not found for stake level: {stake_level}")

    players = []
    total_hands = 0
    sum_vpip = 0.0
    sum_pfr = 0.0
    sum_3bet = 0.0

    for row in rows:
        hands = row.total_hands or 0
        vpip = float(row.vpip_pct or 0)
        pfr = float(row.pfr_pct or 0)
        three_bet = float(row.three_bet_pct or 0)

        total_hands += hands
        sum_vpip += vpip * hands
        sum_pfr += pfr * hands
        sum_3bet += three_bet * hands

        players.append(PoolPlayer(
            player_name=row.player_name,
            total_hands=hands,
            vpip_pct=round(vpip, 1),
            pfr_pct=round(pfr, 1),
            three_bet_pct=round(three_bet, 1),
            fold_to_3bet_pct=round(float(row.fold_to_three_bet_pct), 1) if row.fold_to_three_bet_pct else None,
            player_type=row.player_type
        ))

    # Weighted averages
    avg_stats = {}
    if total_hands > 0:
        avg_stats = {
            "vpip": round(sum_vpip / total_hands, 1),
            "pfr": round(sum_pfr / total_hands, 1),
            "3bet": round(sum_3bet / total_hands, 1)
        }

    site = 'PokerStars'  # Default for now
    pool_id = get_pool_id(site, stake_level)
    display_name = get_pool_display_name(site, stake_level)

    return PoolDetail(
        pool_id=pool_id,
        display_name=display_name,
        site=site,
        stake_level=stake_level,
        player_count=len(players),
        total_hands=total_hands,
        avg_stats=avg_stats,
        players=players
    )


@router.get("/{stake_level}/players/{player_name}")
def get_pool_player_detail(
    stake_level: str,
    player_name: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed stats for a specific player in a pool.
    This uses aggregate GTO analysis (no hole cards).
    """
    hero_nicknames = list(get_hero_nicknames(db))

    # Check if player is a hero (shouldn't be in pools)
    if player_name.lower() in hero_nicknames:
        raise HTTPException(
            status_code=400,
            detail="This player is configured as a hero. View in 'My Game' instead."
        )

    # Get player stats
    result = db.execute(text("""
        SELECT
            ps.*,
            (SELECT COUNT(*) FROM player_hand_summary WHERE player_name = :player_name) as hands_analyzed,
            (SELECT MIN(s.start_time) FROM sessions s WHERE s.player_name = :player_name) as first_seen,
            (SELECT MAX(s.end_time) FROM sessions s WHERE s.player_name = :player_name) as last_seen
        FROM player_stats ps
        WHERE ps.player_name = :player_name
    """), {"player_name": player_name})

    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Player not found: {player_name}")

    return {
        "player_name": player_name,
        "pool_stake": stake_level,
        "total_hands": row.total_hands,
        "hands_analyzed": row.hands_analyzed,
        "first_seen": row.first_seen,
        "last_seen": row.last_seen,
        "stats": {
            "vpip_pct": float(row.vpip_pct) if row.vpip_pct else None,
            "pfr_pct": float(row.pfr_pct) if row.pfr_pct else None,
            "three_bet_pct": float(row.three_bet_pct) if row.three_bet_pct else None,
            "fold_to_3bet_pct": float(row.fold_to_three_bet_pct) if row.fold_to_three_bet_pct else None,
            "four_bet_pct": float(row.four_bet_pct) if row.four_bet_pct else None,
            "cold_call_pct": float(row.cold_call_pct) if row.cold_call_pct else None,
            "steal_attempt_pct": float(row.steal_attempt_pct) if row.steal_attempt_pct else None,
            "fold_to_steal_pct": float(row.fold_to_steal_pct) if row.fold_to_steal_pct else None,
        },
        "player_type": row.player_type,
        "positional_vpip": {
            "UTG": float(row.vpip_utg) if row.vpip_utg else None,
            "MP": float(row.vpip_mp) if row.vpip_mp else None,
            "CO": float(row.vpip_co) if row.vpip_co else None,
            "BTN": float(row.vpip_btn) if row.vpip_btn else None,
            "SB": float(row.vpip_sb) if row.vpip_sb else None,
            "BB": float(row.vpip_bb) if row.vpip_bb else None,
        }
    }
