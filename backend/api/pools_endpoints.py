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
    avg_fold_to_3bet: float
    avg_4bet: float
    avg_cold_call: float
    avg_squeeze: float
    avg_limp: float
    avg_steal_attempt: float
    avg_fold_to_steal: float
    avg_3bet_vs_steal: float
    avg_exploitability: float
    player_type_distribution: Dict[str, int]


class PoolPlayer(BaseModel):
    """Player within a pool"""
    player_name: str
    total_hands: int
    vpip_pct: float
    pfr_pct: float
    three_bet_pct: float
    fold_to_three_bet_pct: Optional[float]
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
    Uses raw_hands.stake_level to determine which stake each player plays at.
    """
    hero_nicknames = list(get_hero_nicknames(db))

    # Get stake levels from raw_hands via player_hand_summary
    # This correctly links opponent players to stakes through the hands they played
    query = """
        WITH player_stakes AS (
            -- Get the most common stake level for each player
            SELECT
                phs.player_name,
                rh.stake_level,
                COUNT(*) as hands_at_stake
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.stake_level IS NOT NULL
    """

    params = {}
    if hero_nicknames:
        query += " AND LOWER(phs.player_name) != ALL(:hero_nicknames)"
        params["hero_nicknames"] = hero_nicknames

    query += """
            GROUP BY phs.player_name, rh.stake_level
        ),
        player_primary_stake AS (
            -- Pick the stake where each player has the most hands
            SELECT DISTINCT ON (player_name)
                player_name,
                stake_level,
                hands_at_stake
            FROM player_stakes
            ORDER BY player_name, hands_at_stake DESC
        ),
        player_with_stats AS (
            -- Join with player_stats for all stats
            SELECT
                pps.player_name,
                pps.stake_level,
                pps.hands_at_stake,
                ps.vpip_pct,
                ps.pfr_pct,
                ps.three_bet_pct,
                ps.fold_to_three_bet_pct,
                ps.four_bet_pct,
                ps.cold_call_pct,
                ps.squeeze_pct,
                ps.limp_pct,
                ps.steal_attempt_pct,
                ps.fold_to_steal_pct,
                ps.three_bet_vs_steal_pct,
                ps.exploitability_index,
                ps.player_type
            FROM player_primary_stake pps
            LEFT JOIN player_stats ps ON pps.player_name = ps.player_name
        )
        SELECT
            stake_level,
            COUNT(*) as player_count,
            COALESCE(SUM(hands_at_stake), 0) as total_hands,
            COALESCE(AVG(vpip_pct), 0) as avg_vpip,
            COALESCE(AVG(pfr_pct), 0) as avg_pfr,
            COALESCE(AVG(three_bet_pct), 0) as avg_3bet,
            COALESCE(AVG(fold_to_three_bet_pct), 0) as avg_fold_to_3bet,
            COALESCE(AVG(four_bet_pct), 0) as avg_4bet,
            COALESCE(AVG(cold_call_pct), 0) as avg_cold_call,
            COALESCE(AVG(squeeze_pct), 0) as avg_squeeze,
            COALESCE(AVG(limp_pct), 0) as avg_limp,
            COALESCE(AVG(steal_attempt_pct), 0) as avg_steal_attempt,
            COALESCE(AVG(fold_to_steal_pct), 0) as avg_fold_to_steal,
            COALESCE(AVG(three_bet_vs_steal_pct), 0) as avg_3bet_vs_steal,
            COALESCE(AVG(exploitability_index), 0) as avg_exploitability,
            COUNT(*) FILTER (WHERE player_type = 'NIT') as nit_count,
            COUNT(*) FILTER (WHERE player_type = 'TAG') as tag_count,
            COUNT(*) FILTER (WHERE player_type = 'LAG') as lag_count,
            COUNT(*) FILTER (WHERE player_type = 'FISH') as fish_count,
            COUNT(*) FILTER (WHERE player_type = 'CALLING_STATION') as station_count,
            COUNT(*) FILTER (WHERE player_type = 'MANIAC') as maniac_count,
            COUNT(*) FILTER (WHERE player_type IS NULL OR player_type = 'UNKNOWN') as unknown_count
        FROM player_with_stats
        GROUP BY stake_level
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

        # Build player type distribution
        type_distribution = {}
        if row.nit_count > 0:
            type_distribution['NIT'] = row.nit_count
        if row.tag_count > 0:
            type_distribution['TAG'] = row.tag_count
        if row.lag_count > 0:
            type_distribution['LAG'] = row.lag_count
        if row.fish_count > 0:
            type_distribution['FISH'] = row.fish_count
        if row.station_count > 0:
            type_distribution['CALLING_STATION'] = row.station_count
        if row.maniac_count > 0:
            type_distribution['MANIAC'] = row.maniac_count
        if row.unknown_count > 0:
            type_distribution['UNKNOWN'] = row.unknown_count

        pools.append(PoolSummary(
            pool_id=pool_id,
            display_name=display_name,
            site=site,
            stake_level=stake,
            player_count=row.player_count,
            total_hands=row.total_hands,
            avg_vpip=round(float(row.avg_vpip), 1),
            avg_pfr=round(float(row.avg_pfr), 1),
            avg_3bet=round(float(row.avg_3bet), 1),
            avg_fold_to_3bet=round(float(row.avg_fold_to_3bet), 1),
            avg_4bet=round(float(row.avg_4bet), 1),
            avg_cold_call=round(float(row.avg_cold_call), 1),
            avg_squeeze=round(float(row.avg_squeeze), 1),
            avg_limp=round(float(row.avg_limp), 1),
            avg_steal_attempt=round(float(row.avg_steal_attempt), 1),
            avg_fold_to_steal=round(float(row.avg_fold_to_steal), 1),
            avg_3bet_vs_steal=round(float(row.avg_3bet_vs_steal), 1),
            avg_exploitability=round(float(row.avg_exploitability), 1),
            player_type_distribution=type_distribution
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
    Uses raw_hands.stake_level to determine which stake each player plays at.
    """
    hero_nicknames = list(get_hero_nicknames(db))

    # Get all players in this stake level via raw_hands
    query = """
        WITH player_stake_hands AS (
            -- Get hand counts per player at the requested stake
            SELECT
                phs.player_name,
                COUNT(*) as hands_at_stake
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.stake_level = :stake_level
    """

    params = {"stake_level": stake_level, "limit": limit}
    if hero_nicknames:
        query += " AND LOWER(phs.player_name) != ALL(:hero_nicknames)"
        params["hero_nicknames"] = hero_nicknames

    query += """
            GROUP BY phs.player_name
        ),
        player_with_stats AS (
            -- Join with player_stats for detailed stats
            SELECT
                psh.player_name,
                psh.hands_at_stake as total_hands,
                ps.vpip_pct,
                ps.pfr_pct,
                ps.three_bet_pct,
                ps.fold_to_three_bet_pct,
                ps.four_bet_pct,
                ps.cold_call_pct,
                ps.squeeze_pct,
                ps.limp_pct,
                ps.steal_attempt_pct,
                ps.fold_to_steal_pct,
                ps.three_bet_vs_steal_pct,
                ps.exploitability_index,
                ps.player_type
            FROM player_stake_hands psh
            LEFT JOIN player_stats ps ON psh.player_name = ps.player_name
        )
        SELECT * FROM player_with_stats
    """

    # Add sorting
    valid_sort = {"total_hands", "vpip_pct", "pfr_pct", "three_bet_pct", "fold_to_three_bet_pct", "exploitability_index", "player_name"}
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
    # Weighted sums for all stats
    sums = {
        'vpip': 0.0, 'pfr': 0.0, '3bet': 0.0, 'fold_to_3bet': 0.0,
        '4bet': 0.0, 'cold_call': 0.0, 'squeeze': 0.0, 'limp': 0.0,
        'steal_attempt': 0.0, 'fold_to_steal': 0.0, '3bet_vs_steal': 0.0,
        'exploitability': 0.0
    }

    for row in rows:
        hands = row.total_hands or 0
        total_hands += hands

        # Accumulate weighted sums
        sums['vpip'] += float(row.vpip_pct or 0) * hands
        sums['pfr'] += float(row.pfr_pct or 0) * hands
        sums['3bet'] += float(row.three_bet_pct or 0) * hands
        sums['fold_to_3bet'] += float(row.fold_to_three_bet_pct or 0) * hands
        sums['4bet'] += float(row.four_bet_pct or 0) * hands
        sums['cold_call'] += float(row.cold_call_pct or 0) * hands
        sums['squeeze'] += float(row.squeeze_pct or 0) * hands
        sums['limp'] += float(row.limp_pct or 0) * hands
        sums['steal_attempt'] += float(row.steal_attempt_pct or 0) * hands
        sums['fold_to_steal'] += float(row.fold_to_steal_pct or 0) * hands
        sums['3bet_vs_steal'] += float(row.three_bet_vs_steal_pct or 0) * hands
        sums['exploitability'] += float(row.exploitability_index or 0) * hands

        players.append(PoolPlayer(
            player_name=row.player_name,
            total_hands=hands,
            vpip_pct=round(float(row.vpip_pct or 0), 1),
            pfr_pct=round(float(row.pfr_pct or 0), 1),
            three_bet_pct=round(float(row.three_bet_pct or 0), 1),
            fold_to_three_bet_pct=round(float(row.fold_to_three_bet_pct), 1) if row.fold_to_three_bet_pct else None,
            player_type=row.player_type
        ))

    # Weighted averages for all stats
    avg_stats = {}
    if total_hands > 0:
        avg_stats = {
            "vpip": round(sums['vpip'] / total_hands, 1),
            "pfr": round(sums['pfr'] / total_hands, 1),
            "3bet": round(sums['3bet'] / total_hands, 1),
            "fold_to_3bet": round(sums['fold_to_3bet'] / total_hands, 1),
            "4bet": round(sums['4bet'] / total_hands, 1),
            "cold_call": round(sums['cold_call'] / total_hands, 1),
            "squeeze": round(sums['squeeze'] / total_hands, 1),
            "limp": round(sums['limp'] / total_hands, 1),
            "steal_attempt": round(sums['steal_attempt'] / total_hands, 1),
            "fold_to_steal": round(sums['fold_to_steal'] / total_hands, 1),
            "3bet_vs_steal": round(sums['3bet_vs_steal'] / total_hands, 1),
            "exploitability": round(sums['exploitability'] / total_hands, 1)
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
