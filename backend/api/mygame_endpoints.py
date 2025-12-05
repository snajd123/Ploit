"""
My Game API Endpoints

Endpoints for hero-specific analysis with hole cards.
Returns data only for players matching configured hero nicknames.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
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
    fold_to_three_bet_pct: Optional[float]
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
            fold_to_three_bet_pct=float(row.fold_to_three_bet_pct) if row.fold_to_three_bet_pct else None,
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


@router.get("/gto-analysis")
def get_mygame_gto_analysis(db: Session = Depends(get_db)):
    """
    Get aggregated GTO analysis across all hero nicknames.
    Combines stats from all configured hero names into a single analysis.
    """
    from typing import Dict, Any

    hero_nicknames = list(get_hero_nicknames(db))

    if not hero_nicknames:
        raise HTTPException(
            status_code=404,
            detail="No hero nicknames configured. Add your screen names in Settings."
        )

    # ============================================
    # 1. OPENING RANGES (RFI - Raise First In)
    # ============================================
    # RFI (Raise First In) calculation
    # pot_unopened = true means all players before hero folded (no limps, no raises)
    # This is the correct condition for RFI opportunities
    opening_query = text("""
        SELECT
            position,
            COUNT(*) as total_hands,
            COUNT(*) FILTER (WHERE pot_unopened = true) as rfi_opportunities,
            COUNT(*) FILTER (WHERE pfr = true AND pot_unopened = true) as opened,
            ROUND(100.0 * COUNT(*) FILTER (WHERE pfr = true AND pot_unopened = true) /
                NULLIF(COUNT(*) FILTER (WHERE pot_unopened = true), 0), 1) as player_open_pct
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames)
        AND position IS NOT NULL
        AND position NOT IN ('BB')
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE pot_unopened = true) >= 10
        ORDER BY CASE position
            WHEN 'UTG' THEN 1 WHEN 'MP' THEN 2 WHEN 'HJ' THEN 3
            WHEN 'CO' THEN 4 WHEN 'BTN' THEN 5 WHEN 'SB' THEN 6
        END
    """)
    opening_result = db.execute(opening_query, {"nicknames": hero_nicknames})
    opening_rows = [dict(row._mapping) for row in opening_result]

    # Get GTO opening frequencies
    gto_opening_result = db.execute(text("""
        SELECT position, SUM(gto_aggregate_freq) as gto_aggregate_freq
        FROM gto_scenarios WHERE category = 'opening'
        GROUP BY position
    """))
    gto_opening = {row[0]: float(row[1]) * 100 if row[1] else 0 for row in gto_opening_result}

    opening_ranges = []
    for row in opening_rows:
        pos = row['position']
        player_freq = float(row['player_open_pct']) if row['player_open_pct'] else 0
        gto_freq = gto_opening.get(pos, 0)
        diff = player_freq - gto_freq
        severity = 'minor' if abs(diff) < 5 else 'moderate' if abs(diff) < 15 else 'major'
        opening_ranges.append({
            'position': pos,
            'total_hands': row['rfi_opportunities'],
            'player_frequency': player_freq,
            'gto_frequency': round(gto_freq, 1),
            'frequency_diff': round(diff, 1),
            'leak_severity': severity,
            'leak_type': 'Too Loose' if diff > 5 else 'Too Tight' if diff < -5 else None
        })

    # ============================================
    # 2. DEFENSE VS OPENS (call/3bet/fold)
    # ============================================
    defense_query = text("""
        SELECT
            position,
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
        WHERE LOWER(player_name) = ANY(:nicknames)
        AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) >= 5
        ORDER BY position
    """)
    defense_result = db.execute(defense_query, {"nicknames": hero_nicknames})
    defense_rows = [dict(row._mapping) for row in defense_result]

    # Get GTO defense frequencies
    gto_defense_result = db.execute(text("""
        SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
        FROM gto_scenarios
        WHERE category = 'defense'
        AND action IN ('call', '3bet')
        GROUP BY position, action
    """))
    gto_defense = {}
    for row in gto_defense_result:
        pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
        if pos not in gto_defense:
            gto_defense[pos] = {}
        gto_defense[pos][action] = freq

    defense_vs_open = []
    for row in defense_rows:
        pos = row['position']
        fold_freq = float(row['fold_pct']) if row['fold_pct'] else 0
        call_freq = float(row['call_pct']) if row['call_pct'] else 0
        threebet_freq = float(row['three_bet_pct']) if row['three_bet_pct'] else 0

        gto_call = gto_defense.get(pos, {}).get('call', 15)
        gto_3bet = gto_defense.get(pos, {}).get('3bet', 8)
        gto_fold = 100 - gto_call - gto_3bet

        defense_vs_open.append({
            'position': pos,
            'sample_size': row['faced_open'],
            # Action-specific counts for accurate hand counts in priority leaks
            'fold_count': row['folded'],
            'call_count': row['called'],
            '3bet_count': row['three_bets'],
            'player_fold': round(fold_freq, 1),
            'player_call': round(call_freq, 1),
            'player_3bet': round(threebet_freq, 1),
            'gto_fold': round(gto_fold, 1),
            'gto_call': round(gto_call, 1),
            'gto_3bet': round(gto_3bet, 1),
            'fold_diff': round(fold_freq - gto_fold, 1),
            'call_diff': round(call_freq - gto_call, 1),
            '3bet_diff': round(threebet_freq - gto_3bet, 1),
        })

    # ============================================
    # 3. FACING 3-BET (after opening)
    # ============================================
    facing_3bet_query = text("""
        SELECT
            position,
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
        WHERE LOWER(player_name) = ANY(:nicknames)
        AND position IS NOT NULL
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) >= 5
        ORDER BY position
    """)
    facing_3bet_result = db.execute(facing_3bet_query, {"nicknames": hero_nicknames})
    facing_3bet_rows = [dict(row._mapping) for row in facing_3bet_result]

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

    facing_3bet = []
    for row in facing_3bet_rows:
        pos = row['position']
        fold = float(row['fold_pct']) if row['fold_pct'] else 0
        call = float(row['call_pct']) if row['call_pct'] else 0
        four_bet = float(row['four_bet_pct']) if row['four_bet_pct'] else 0

        gto_fold = gto_f3bet.get(pos, {}).get('fold', 55)
        gto_call = gto_f3bet.get(pos, {}).get('call', 35)
        gto_4bet = gto_f3bet.get(pos, {}).get('4bet', 10)

        facing_3bet.append({
            'position': pos,
            'sample_size': row['faced_3bet'],
            # Action-specific counts for accurate hand counts in priority leaks
            'fold_count': row['folded'],
            'call_count': row['called'],
            '4bet_count': row['four_bet'],
            'player_fold': round(fold, 1),
            'player_call': round(call, 1),
            'player_4bet': round(four_bet, 1),
            'gto_fold': round(gto_fold, 1),
            'gto_call': round(gto_call, 1),
            'gto_4bet': round(gto_4bet, 1),
            'fold_diff': round(fold - gto_fold, 1),
            'call_diff': round(call - gto_call, 1),
            '4bet_diff': round(four_bet - gto_4bet, 1),
        })

    # ============================================
    # 3b. FACING 3-BET BY MATCHUP
    # ============================================
    gto_f3bet_matchups_result = db.execute(text("""
        SELECT position, opponent_position, action, gto_aggregate_freq * 100 as freq
        FROM gto_scenarios
        WHERE category = 'facing_3bet'
        AND opponent_position IS NOT NULL
        ORDER BY position, opponent_position, action
    """))
    gto_f3bet_matchups = {}
    for row in gto_f3bet_matchups_result:
        pos, opp, action, freq = row[0], row[1], row[2], float(row[3]) if row[3] else 0
        key = f"{pos}_vs_{opp}"
        if key not in gto_f3bet_matchups:
            gto_f3bet_matchups[key] = {}
        gto_f3bet_matchups[key][action] = freq

    player_f3bet_matchups_result = db.execute(text("""
        SELECT
            position,
            three_bettor_position,
            COUNT(*) as faced_3bet,
            COUNT(*) FILTER (WHERE folded_to_three_bet = true) as folded,
            COUNT(*) FILTER (WHERE called_three_bet = true) as called,
            COUNT(*) FILTER (WHERE four_bet = true) as four_bets
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames)
          AND faced_three_bet = true
          AND pfr = true
          AND three_bettor_position IS NOT NULL
          AND position IS NOT NULL
        GROUP BY position, three_bettor_position
        ORDER BY position, three_bettor_position
    """), {"nicknames": hero_nicknames})

    player_f3bet_stats = {}
    for row in player_f3bet_matchups_result.mappings():
        key = f"{row['position']}_vs_{row['three_bettor_position']}"
        total = row['faced_3bet'] or 0
        if total > 0:
            player_f3bet_stats[key] = {
                'sample_size': total,
                'fold_pct': (row['folded'] or 0) / total * 100,
                'call_pct': (row['called'] or 0) / total * 100,
                '4bet_pct': (row['four_bets'] or 0) / total * 100
            }

    facing_3bet_matchups = []
    for key, actions in sorted(gto_f3bet_matchups.items()):
        pos, opp = key.split('_vs_')
        player_stats = player_f3bet_stats.get(key, {})

        gto_fold = actions.get('fold', 0)
        gto_call = actions.get('call', 0)
        gto_4bet = actions.get('4bet', 0)

        player_fold = player_stats.get('fold_pct')
        player_call = player_stats.get('call_pct')
        player_4bet = player_stats.get('4bet_pct')

        facing_3bet_matchups.append({
            'position': pos,
            'vs_position': opp,
            'sample_size': player_stats.get('sample_size', 0),
            'player_fold': round(player_fold, 1) if player_fold is not None else None,
            'player_call': round(player_call, 1) if player_call is not None else None,
            'player_4bet': round(player_4bet, 1) if player_4bet is not None else None,
            'gto_fold': round(gto_fold, 1),
            'gto_call': round(gto_call, 1),
            'gto_4bet': round(gto_4bet, 1),
            'fold_diff': round(player_fold - gto_fold, 1) if player_fold is not None else None,
            'call_diff': round(player_call - gto_call, 1) if player_call is not None else None,
            '4bet_diff': round(player_4bet - gto_4bet, 1) if player_4bet is not None else None,
        })

    # ============================================
    # 4. BLIND DEFENSE (vs steals)
    # ============================================
    blind_defense_query = text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false) as faced_steal,
            COUNT(*) FILTER (WHERE fold_to_steal = true AND faced_three_bet = false) as folded,
            COUNT(*) FILTER (WHERE call_steal = true AND faced_three_bet = false) as called,
            COUNT(*) FILTER (WHERE three_bet_vs_steal = true AND faced_three_bet = false) as three_bet,
            ROUND(100.0 * COUNT(*) FILTER (WHERE fold_to_steal = true AND faced_three_bet = false) /
                NULLIF(COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false), 0), 1) as fold_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE call_steal = true AND faced_three_bet = false) /
                NULLIF(COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false), 0), 1) as call_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE three_bet_vs_steal = true AND faced_three_bet = false) /
                NULLIF(COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false), 0), 1) as three_bet_pct
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames)
        AND position IN ('BB', 'SB')
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false) >= 5
        ORDER BY position
    """)
    blind_result = db.execute(blind_defense_query, {"nicknames": hero_nicknames})
    blind_rows = [dict(row._mapping) for row in blind_result]

    gto_blind_result = db.execute(text("""
        SELECT position, action, gto_aggregate_freq * 100 as freq
        FROM gto_scenarios
        WHERE category = 'defense'
        AND position IN ('BB', 'SB')
        AND opponent_position = 'BTN'
    """))
    gto_blind = {}
    for row in gto_blind_result:
        pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
        if pos not in gto_blind:
            gto_blind[pos] = {}
        gto_blind[pos][action] = freq

    blind_defense = []
    for row in blind_rows:
        pos = row['position']
        fold = float(row['fold_pct']) if row['fold_pct'] else 0
        call = float(row['call_pct']) if row['call_pct'] else 0
        three_bet = float(row['three_bet_pct']) if row['three_bet_pct'] else 0

        gto_call = gto_blind.get(pos, {}).get('call', 30)
        gto_3bet = gto_blind.get(pos, {}).get('3bet', 15)
        gto_fold = gto_blind.get(pos, {}).get('fold', 55)

        blind_defense.append({
            'position': pos,
            'sample_size': row['faced_steal'],
            'player_fold': round(fold, 1),
            'player_call': round(call, 1),
            'player_3bet': round(three_bet, 1),
            'gto_fold': round(gto_fold, 1),
            'gto_call': round(gto_call, 1),
            'gto_3bet': round(gto_3bet, 1),
            'fold_diff': round(fold - gto_fold, 1),
            'call_diff': round(call - gto_call, 1),
            '3bet_diff': round(three_bet - gto_3bet, 1),
        })

    # ============================================
    # 5. STEAL ATTEMPTS
    # ============================================
    # Steals are RFI from late positions - use pot_unopened for accurate opportunity counting
    steal_query = text("""
        SELECT
            position,
            COUNT(*) FILTER (WHERE pot_unopened = true) as opportunities,
            COUNT(*) FILTER (WHERE steal_attempt = true) as steals,
            ROUND(100.0 * COUNT(*) FILTER (WHERE steal_attempt = true) /
                NULLIF(COUNT(*) FILTER (WHERE pot_unopened = true), 0), 1) as steal_pct
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames)
        AND position IN ('CO', 'BTN', 'SB')
        GROUP BY position
        HAVING COUNT(*) FILTER (WHERE pot_unopened = true) >= 10
        ORDER BY position
    """)
    steal_result = db.execute(steal_query, {"nicknames": hero_nicknames})
    steal_rows = [dict(row._mapping) for row in steal_result]

    gto_steal_result = db.execute(text("""
        SELECT position, gto_aggregate_freq * 100 as freq
        FROM gto_scenarios
        WHERE category = 'opening'
        AND position IN ('CO', 'BTN', 'SB')
    """))
    gto_steal = {row[0]: float(row[1]) if row[1] else 0 for row in gto_steal_result}

    steal_attempts = []
    for row in steal_rows:
        pos = row['position']
        player_freq = float(row['steal_pct']) if row['steal_pct'] else 0
        gto_freq = gto_steal.get(pos, 35)
        diff = player_freq - gto_freq

        steal_attempts.append({
            'position': pos,
            'opportunities': row['opportunities'],  # Match frontend expectation
            'player_frequency': round(player_freq, 1),
            'gto_frequency': round(gto_freq, 1),
            'steal_diff': round(diff, 1),  # Match frontend expectation
            'leak_type': 'Over-stealing' if diff > 10 else 'Under-stealing' if diff < -10 else None
        })

    # ============================================
    # 6. POSITION-SPECIFIC DEFENSE
    # ============================================
    gto_matchups_result = db.execute(text("""
        SELECT position, opponent_position, action, gto_aggregate_freq * 100 as freq
        FROM gto_scenarios
        WHERE category = 'defense'
        ORDER BY position, opponent_position, action
    """))
    gto_matchups = {}
    for row in gto_matchups_result:
        pos, opp, action, freq = row[0], row[1], row[2], float(row[3]) if row[3] else 0
        key = f"{pos}_vs_{opp}"
        if key not in gto_matchups:
            gto_matchups[key] = {}
        gto_matchups[key][action] = freq

    player_matchups_result = db.execute(text("""
        SELECT
            position,
            raiser_position,
            COUNT(*) as faced_open,
            COUNT(*) FILTER (WHERE vpip = false) as folded,
            COUNT(*) FILTER (WHERE vpip = true AND pfr = false) as called,
            COUNT(*) FILTER (WHERE made_three_bet = true) as three_bets
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames)
          AND faced_raise = true
          AND faced_three_bet = false
          AND raiser_position IS NOT NULL
          AND position IS NOT NULL
        GROUP BY position, raiser_position
        ORDER BY position, raiser_position
    """), {"nicknames": hero_nicknames})

    player_matchup_stats = {}
    for row in player_matchups_result.mappings():
        key = f"{row['position']}_vs_{row['raiser_position']}"
        total = row['faced_open'] or 0
        if total > 0:
            player_matchup_stats[key] = {
                'sample_size': total,
                'fold_pct': (row['folded'] or 0) / total * 100,
                'call_pct': (row['called'] or 0) / total * 100,
                '3bet_pct': (row['three_bets'] or 0) / total * 100
            }

    position_matchups = []
    for key, actions in sorted(gto_matchups.items()):
        pos, opp = key.split('_vs_')
        player_stats = player_matchup_stats.get(key, {})

        gto_fold = actions.get('fold', 0)
        gto_call = actions.get('call', 0)
        gto_3bet = actions.get('3bet', 0)

        player_fold = player_stats.get('fold_pct')
        player_call = player_stats.get('call_pct')
        player_3bet = player_stats.get('3bet_pct')

        position_matchups.append({
            'position': pos,
            'vs_position': opp,
            'sample_size': player_stats.get('sample_size', 0),
            'player_fold': round(player_fold, 1) if player_fold is not None else None,
            'player_call': round(player_call, 1) if player_call is not None else None,
            'player_3bet': round(player_3bet, 1) if player_3bet is not None else None,
            'gto_fold': round(gto_fold, 1),
            'gto_call': round(gto_call, 1),
            'gto_3bet': round(gto_3bet, 1),
            'fold_diff': round(player_fold - gto_fold, 1) if player_fold is not None else None,
            'call_diff': round(player_call - gto_call, 1) if player_call is not None else None,
            '3bet_diff': round(player_3bet - gto_3bet, 1) if player_3bet is not None else None,
        })

    # ============================================
    # 7. FACING 4-BET
    # ============================================
    gto_f4bet_result = db.execute(text("""
        SELECT position, opponent_position, action, gto_aggregate_freq * 100 as freq
        FROM gto_scenarios
        WHERE category = 'facing_4bet'
        ORDER BY position, opponent_position, action
    """))
    gto_facing_4bet = {}
    for row in gto_f4bet_result:
        pos, opp, action, freq = row[0], row[1], row[2], float(row[3]) if row[3] else 0
        key = f"{pos}_vs_{opp}"
        if key not in gto_facing_4bet:
            gto_facing_4bet[key] = {}
        gto_facing_4bet[key][action] = freq

    player_f4bet_result = db.execute(text("""
        SELECT
            position,
            raiser_position,
            COUNT(*) as faced_4bet,
            COUNT(*) FILTER (WHERE folded_to_four_bet = true) as folded,
            COUNT(*) FILTER (WHERE called_four_bet = true) as called,
            COUNT(*) FILTER (WHERE five_bet = true) as five_bets
        FROM player_hand_summary
        WHERE LOWER(player_name) = ANY(:nicknames)
          AND faced_four_bet = true
          AND raiser_position IS NOT NULL
          AND position IS NOT NULL
        GROUP BY position, raiser_position
        ORDER BY position, raiser_position
    """), {"nicknames": hero_nicknames})

    player_f4bet_stats = {}
    for row in player_f4bet_result.mappings():
        key = f"{row['position']}_vs_{row['raiser_position']}"
        total = row['faced_4bet'] or 0
        if total > 0:
            player_f4bet_stats[key] = {
                'sample_size': total,
                'fold_pct': (row['folded'] or 0) / total * 100,
                'call_pct': (row['called'] or 0) / total * 100,
                '5bet_pct': (row['five_bets'] or 0) / total * 100
            }

    facing_4bet_reference = []
    for key, actions in sorted(gto_facing_4bet.items()):
        pos, opp = key.split('_vs_')
        player_stats = player_f4bet_stats.get(key, {})

        gto_fold = actions.get('fold', 0)
        gto_call = actions.get('call', 0)
        gto_5bet = actions.get('5bet', 0) + actions.get('allin', 0)

        player_fold = player_stats.get('fold_pct')
        player_call = player_stats.get('call_pct')
        player_5bet = player_stats.get('5bet_pct')

        facing_4bet_reference.append({
            'position': pos,
            'vs_position': opp,
            'sample_size': player_stats.get('sample_size', 0),
            'player_fold': round(player_fold, 1) if player_fold is not None else None,
            'player_call': round(player_call, 1) if player_call is not None else None,
            'player_5bet': round(player_5bet, 1) if player_5bet is not None else None,
            'gto_fold': round(gto_fold, 1),
            'gto_call': round(gto_call, 1),
            'gto_5bet': round(gto_5bet, 1),
            'fold_diff': round(player_fold - gto_fold, 1) if player_fold is not None else None,
            'call_diff': round(player_call - gto_call, 1) if player_call is not None else None,
            '5bet_diff': round(player_5bet - gto_5bet, 1) if player_5bet is not None else None,
        })

    # ============================================
    # CALCULATE OVERALL ADHERENCE SCORE
    # ============================================
    all_deviations = []

    for r in opening_ranges:
        all_deviations.append(abs(r['frequency_diff']))
    for r in defense_vs_open:
        all_deviations.append(abs(r['call_diff']))
        all_deviations.append(abs(r['3bet_diff']))
    for r in facing_3bet:
        all_deviations.append(abs(r['fold_diff']))
        all_deviations.append(abs(r['call_diff']))
    for r in blind_defense:
        all_deviations.append(abs(r['fold_diff']))
        all_deviations.append(abs(r['3bet_diff']))
    for r in steal_attempts:
        all_deviations.append(abs(r['steal_diff']))

    avg_deviation = sum(all_deviations) / len(all_deviations) if all_deviations else 0
    adherence_score = max(0, 100 - avg_deviation * 1.5)

    major_leaks = sum(1 for d in all_deviations if d > 15)
    moderate_leaks = sum(1 for d in all_deviations if 8 < d <= 15)

    # Get total hands
    total_hands_result = db.execute(text("""
        SELECT COUNT(*) FROM player_hand_summary WHERE LOWER(player_name) = ANY(:nicknames)
    """), {"nicknames": hero_nicknames})
    total_hands = total_hands_result.scalar() or 0

    # Build response
    response_data = {
        'player': 'Hero (combined)',
        'hero_nicknames': [n for n in hero_nicknames],
        'adherence': {
            'gto_adherence_score': round(adherence_score, 1),
            'avg_deviation': round(avg_deviation, 1),
            'major_leaks_count': major_leaks,
            'moderate_leaks_count': moderate_leaks,
            'total_hands': total_hands
        },
        'opening_ranges': opening_ranges,
        'defense_vs_open': defense_vs_open,
        'facing_3bet': facing_3bet,
        'facing_3bet_matchups': facing_3bet_matchups,
        'blind_defense': blind_defense,
        'steal_attempts': steal_attempts,
        'position_matchups': position_matchups,
        'facing_4bet_reference': facing_4bet_reference
    }

    # Build priority leaks
    from backend.services.priority_scoring import build_priority_leaks_from_gto_analysis
    priority_leaks = build_priority_leaks_from_gto_analysis(response_data)
    response_data['priority_leaks'] = priority_leaks

    return response_data


@router.get("/scenario-hands")
def get_mygame_scenario_hands(
    scenario: str = Query(..., description="Scenario type: opening, defense, facing_3bet, facing_4bet"),
    position: str = Query(..., description="Player's position: UTG, MP, CO, BTN, SB, BB"),
    vs_position: Optional[str] = Query(None, description="Opponent position for matchup scenarios"),
    action: Optional[str] = Query(None, description="Filter by action: fold, call, raise, 3bet, 4bet, 5bet"),
    deviation: Optional[float] = Query(None, description="Deviation from GTO. If < 0 (under-doing), show hands where player DIDN'T do action (mistakes). If > 0 (over-doing), show hands where player DID the action."),
    limit: int = Query(1000, ge=1, le=5000, description="Max hands to return"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get scenario hands aggregated across all hero nicknames.
    Returns hands where any hero was in the specified scenario with GTO deviation analysis.

    When deviation is provided:
    - deviation < 0 (under-doing action): Shows hands where player DIDN'T do the action but should have (mistakes)
    - deviation > 0 (over-doing action): Shows hands where player DID the action but shouldn't have (mistakes)
    """
    hero_nicknames = list(get_hero_nicknames(db))

    if not hero_nicknames:
        raise HTTPException(
            status_code=404,
            detail="No hero nicknames configured. Add your screen names in Settings."
        )

    # Validate inputs
    valid_scenarios = ['opening', 'defense', 'facing_3bet', 'facing_4bet']
    if scenario not in valid_scenarios:
        raise HTTPException(status_code=400, detail=f"Invalid scenario. Must be one of: {valid_scenarios}")

    valid_positions = ['UTG', 'MP', 'HJ', 'CO', 'BTN', 'SB', 'BB']
    if position.upper() not in valid_positions:
        raise HTTPException(status_code=400, detail=f"Invalid position. Must be one of: {valid_positions}")

    position = position.upper()
    if vs_position:
        vs_position = vs_position.upper()

    # Get GTO frequencies for this scenario
    gto_query = text("""
        SELECT action, gto_aggregate_freq * 100 as freq
        FROM gto_scenarios
        WHERE category = :scenario
        AND position = :position
        AND (opponent_position = :vs_position OR (:vs_position IS NULL AND opponent_position IS NULL))
    """)
    gto_result = db.execute(gto_query, {
        "scenario": scenario,
        "position": position,
        "vs_position": vs_position
    })
    gto_freqs = {row[0]: float(row[1]) if row[1] else 0 for row in gto_result}

    # If no specific GTO found, get average for position
    if not gto_freqs:
        gto_avg_query = text("""
            SELECT action, AVG(gto_aggregate_freq) * 100 as freq
            FROM gto_scenarios
            WHERE category = :scenario
            AND position = :position
            GROUP BY action
        """)
        gto_avg_result = db.execute(gto_avg_query, {"scenario": scenario, "position": position})
        gto_freqs = {row[0]: float(row[1]) if row[1] else 0 for row in gto_avg_result}

    # Build the query based on scenario type - using LOWER(player_name) = ANY(:nicknames) for all heroes
    if scenario == 'opening':
        hands_query = text("""
            SELECT
                phs.hand_id,
                phs.player_name,
                rh.timestamp,
                rh.stake_level,
                phs.pfr as raised,
                phs.vpip,
                CASE
                    WHEN phs.pfr = true THEN 'open'
                    WHEN phs.vpip = false THEN 'fold'
                    ELSE 'limp'
                END as player_action,
                (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                ha.stack_size,
                ha.stack_size / NULLIF(
                    (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                    0
                ) as effective_stack_bb,
                NULL as vs_pos
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            LEFT JOIN (
                SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                FROM hand_actions
                WHERE street = 'preflop'
                ORDER BY hand_id, player_name, action_id
            ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
            WHERE LOWER(phs.player_name) = ANY(:nicknames)
            AND phs.position = :position
            AND phs.pot_unopened = true
            ORDER BY rh.timestamp DESC
            LIMIT :limit
        """)
        params = {"nicknames": hero_nicknames, "position": position, "limit": limit}

    elif scenario == 'defense':
        if vs_position:
            hands_query = text("""
                SELECT
                    phs.hand_id,
                    phs.player_name,
                    rh.timestamp,
                    rh.stake_level,
                    phs.raiser_position as vs_pos,
                    CASE
                        WHEN phs.vpip = false THEN 'fold'
                        WHEN phs.made_three_bet = true THEN '3bet'
                        ELSE 'call'
                    END as player_action,
                    (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                    ha.stack_size,
                    ha.stack_size / NULLIF(
                        (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                        0
                    ) as effective_stack_bb
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                LEFT JOIN (
                    SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                    FROM hand_actions WHERE street = 'preflop'
                    ORDER BY hand_id, player_name, action_id
                ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                WHERE LOWER(phs.player_name) = ANY(:nicknames)
                AND phs.position = :position
                AND phs.faced_raise = true
                AND phs.faced_three_bet = false
                AND phs.raiser_position = :vs_position
                ORDER BY rh.timestamp DESC
                LIMIT :limit
            """)
            params = {"nicknames": hero_nicknames, "position": position, "vs_position": vs_position, "limit": limit}
        else:
            hands_query = text("""
                SELECT
                    phs.hand_id,
                    phs.player_name,
                    rh.timestamp,
                    rh.stake_level,
                    phs.raiser_position as vs_pos,
                    CASE
                        WHEN phs.vpip = false THEN 'fold'
                        WHEN phs.made_three_bet = true THEN '3bet'
                        ELSE 'call'
                    END as player_action,
                    (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                    ha.stack_size,
                    ha.stack_size / NULLIF(
                        (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                        0
                    ) as effective_stack_bb
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                LEFT JOIN (
                    SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                    FROM hand_actions WHERE street = 'preflop'
                    ORDER BY hand_id, player_name, action_id
                ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                WHERE LOWER(phs.player_name) = ANY(:nicknames)
                AND phs.position = :position
                AND phs.faced_raise = true
                AND phs.faced_three_bet = false
                ORDER BY rh.timestamp DESC
                LIMIT :limit
            """)
            params = {"nicknames": hero_nicknames, "position": position, "limit": limit}

    elif scenario == 'facing_3bet':
        if vs_position:
            hands_query = text("""
                SELECT
                    phs.hand_id,
                    phs.player_name,
                    rh.timestamp,
                    rh.stake_level,
                    phs.three_bettor_position as vs_pos,
                    CASE
                        WHEN phs.folded_to_three_bet = true THEN 'fold'
                        WHEN phs.four_bet = true THEN '4bet'
                        ELSE 'call'
                    END as player_action,
                    (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                    ha.stack_size,
                    ha.stack_size / NULLIF(
                        (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                        0
                    ) as effective_stack_bb
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                LEFT JOIN (
                    SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                    FROM hand_actions WHERE street = 'preflop'
                    ORDER BY hand_id, player_name, action_id
                ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                WHERE LOWER(phs.player_name) = ANY(:nicknames)
                AND phs.position = :position
                AND phs.pfr = true
                AND phs.faced_three_bet = true
                AND phs.three_bettor_position = :vs_position
                ORDER BY rh.timestamp DESC
                LIMIT :limit
            """)
            params = {"nicknames": hero_nicknames, "position": position, "vs_position": vs_position, "limit": limit}
        else:
            hands_query = text("""
                SELECT
                    phs.hand_id,
                    phs.player_name,
                    rh.timestamp,
                    rh.stake_level,
                    phs.three_bettor_position as vs_pos,
                    CASE
                        WHEN phs.folded_to_three_bet = true THEN 'fold'
                        WHEN phs.four_bet = true THEN '4bet'
                        ELSE 'call'
                    END as player_action,
                    (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                    ha.stack_size,
                    ha.stack_size / NULLIF(
                        (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                        0
                    ) as effective_stack_bb
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                LEFT JOIN (
                    SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                    FROM hand_actions WHERE street = 'preflop'
                    ORDER BY hand_id, player_name, action_id
                ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                WHERE LOWER(phs.player_name) = ANY(:nicknames)
                AND phs.position = :position
                AND phs.pfr = true
                AND phs.faced_three_bet = true
                ORDER BY rh.timestamp DESC
                LIMIT :limit
            """)
            params = {"nicknames": hero_nicknames, "position": position, "limit": limit}

    elif scenario == 'facing_4bet':
        hands_query = text("""
            SELECT
                phs.hand_id,
                phs.player_name,
                rh.timestamp,
                rh.stake_level,
                phs.raiser_position as vs_pos,
                CASE
                    WHEN phs.folded_to_four_bet = true THEN 'fold'
                    WHEN phs.five_bet = true THEN '5bet'
                    ELSE 'call'
                END as player_action,
                (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                ha.stack_size,
                ha.stack_size / NULLIF(
                    (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                    0
                ) as effective_stack_bb
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            LEFT JOIN (
                SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                FROM hand_actions WHERE street = 'preflop'
                ORDER BY hand_id, player_name, action_id
            ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
            WHERE LOWER(phs.player_name) = ANY(:nicknames)
            AND phs.position = :position
            AND phs.made_three_bet = true
            AND phs.faced_four_bet = true
            ORDER BY rh.timestamp DESC
            LIMIT :limit
        """)
        params = {"nicknames": hero_nicknames, "position": position, "limit": limit}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario}")

    # Execute query
    result = db.execute(hands_query, params)
    rows = result.fetchall()

    # Filter by action if specified
    # When deviation is provided, we want to show MISTAKES:
    # - deviation < 0 (under-doing action): Show hands where player DIDN'T do the action (but should have)
    # - deviation > 0 (over-doing action): Show hands where player DID the action (but shouldn't have)
    # NOTE: The action-based filter is a first pass. When deviation is provided, we'll also
    # filter at the combo level later to show only actual GTO mistakes.
    leak_action = None  # Store for combo-level filtering
    if action:
        # Normalize action names (e.g., 'raise' -> '3bet' for defense)
        action_lower = action.lower()
        leak_action = action_lower  # Store for later GTO lookup
        # Map common names to what's stored in results
        action_map = {
            'raise': ['raise', '3bet', '4bet', '5bet'],
            '3bet': ['3bet'],
            '4bet': ['4bet'],
            '5bet': ['5bet'],
            'fold': ['fold'],
            'call': ['call'],
            'open': ['open'],
        }
        valid_actions = action_map.get(action_lower, [action_lower])

        # Determine if we should invert the filter based on deviation
        if deviation is not None and deviation < 0:
            # Under-doing the action: Show hands where player DIDN'T do this action (mistakes)
            # e.g., "Fold in BB: 47% vs 68% GTO" - show hands where player called/raised but should have folded
            rows = [row for row in rows if row.player_action.lower() not in valid_actions]
        else:
            # Over-doing the action OR no deviation: Show hands where player DID this action
            # e.g., "Fold in BB: 80% vs 68% GTO" - show hands where player folded but shouldn't have
            rows = [row for row in rows if row.player_action.lower() in valid_actions]

    # Hand categorization helper
    def categorize_hand(hole_cards: Optional[str]) -> tuple:
        if not hole_cards:
            return None, None, None

        cards = hole_cards.strip().split()
        if len(cards) != 2:
            return None, None, None

        ranks = '23456789TJQKA'
        rank1 = cards[0][0].upper()
        rank2 = cards[1][0].upper()
        suit1 = cards[0][-1].lower()
        suit2 = cards[1][-1].lower()

        r1_idx = ranks.index(rank1) if rank1 in ranks else -1
        r2_idx = ranks.index(rank2) if rank2 in ranks else -1

        if r1_idx < r2_idx:
            rank1, rank2 = rank2, rank1
            r1_idx, r2_idx = r2_idx, r1_idx

        suited = suit1 == suit2
        suited_str = 's' if suited else 'o' if rank1 != rank2 else ''
        hand_combo = f"{rank1}{rank2}{suited_str}"

        # Tier assignment
        premium = ['AA', 'KK', 'QQ', 'AKs', 'AKo']
        strong = ['JJ', 'TT', 'AQs', 'AQo', 'AJs', 'KQs']
        playable = ['99', '88', '77', 'ATs', 'A9s', 'A8s', 'KJs', 'KTs', 'QJs', 'QTs', 'JTs', 'AJo', 'KQo']
        speculative = ['66', '55', '44', '33', '22', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s', 'K9s', 'Q9s', 'J9s', 'T9s', '98s', '87s', '76s']

        if hand_combo in premium:
            tier = 1
        elif hand_combo in strong:
            tier = 2
        elif hand_combo in playable:
            tier = 3
        elif hand_combo in speculative:
            tier = 4
        else:
            tier = 5

        # Category
        if rank1 == rank2:
            cat = f"Pair ({rank1}{rank1})"
        elif suited:
            cat = f"Suited ({rank1}{rank2}s)"
        else:
            cat = f"Offsuit ({rank1}{rank2}o)"

        return hand_combo, tier, cat

    # Helper to convert GTO database combo (e.g., "Ad3h") to hand type (e.g., "A3o")
    def combo_to_hand_type(combo: str) -> Optional[str]:
        """Convert full combo like 'Ad3h' or '3dAh' to hand type like 'A3o'."""
        if not combo or len(combo) != 4:
            return None

        ranks = '23456789TJQKA'
        # GTO combos are stored as 4 chars: rank1+suit1+rank2+suit2
        rank1 = combo[0].upper()
        suit1 = combo[1].lower()
        rank2 = combo[2].upper()
        suit2 = combo[3].lower()

        if rank1 not in ranks or rank2 not in ranks:
            return None

        r1_idx = ranks.index(rank1)
        r2_idx = ranks.index(rank2)

        # Normalize so higher rank comes first
        if r1_idx < r2_idx:
            rank1, rank2 = rank2, rank1
            suit1, suit2 = suit2, suit1

        suited = suit1 == suit2
        suited_str = 's' if suited else 'o' if rank1 != rank2 else ''
        return f"{rank1}{rank2}{suited_str}"

    # Build GTO lookup table keyed by (hand_type, opponent_position)
    # This allows us to look up GTO for each hand using its actual opponent position
    # Fetch ALL opponent positions so we can use per-hand lookup
    hand_gto_query = text("""
        SELECT gf.hand, gs.action, gs.opponent_position, gf.frequency * 100 as freq
        FROM gto_frequencies gf
        JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
        WHERE gs.category = :scenario
        AND gs.position = :position
    """)
    try:
        hand_gto_result = db.execute(hand_gto_query, {
            "scenario": scenario,
            "position": position
        })
        # Build lookup: (hand_type, opponent_position) -> {action: avg_freq}
        # Track sums and counts for averaging combos of the same hand type
        temp_lookup = {}  # {(hand_type, opp_pos): {action: [freqs]}}

        for row in hand_gto_result:
            combo = row[0]
            action = row[1]
            opp_pos = row[2]
            freq = float(row[3]) if row[3] else 0

            # Convert full combo to hand type
            hand_type = combo_to_hand_type(combo)
            if not hand_type:
                continue

            key = (hand_type, opp_pos)
            if key not in temp_lookup:
                temp_lookup[key] = {}
            if action not in temp_lookup[key]:
                temp_lookup[key][action] = []
            temp_lookup[key][action].append(freq)

        # Average frequencies for each (hand_type, opponent_position, action)
        hand_gto_lookup = {}  # {(hand_type, opp_pos): {action: avg_freq}}
        for key, actions in temp_lookup.items():
            hand_gto_lookup[key] = {}
            for action, freqs in actions.items():
                hand_gto_lookup[key][action] = sum(freqs) / len(freqs) if freqs else 0
    except Exception as e:
        # GTO data may not be available - proceed without it
        hand_gto_lookup = {}

    # Process hands
    hands = []
    summary_correct = 0
    summary_suboptimal = 0
    summary_mistakes = 0
    hands_with_hole_cards = 0
    total_hands_evaluated = 0  # Track total before filtering

    for row in rows:
        total_hands_evaluated += 1
        hole_cards = row.hole_cards
        hand_combo, hand_tier, hand_category = categorize_hand(hole_cards)

        if hole_cards:
            hands_with_hole_cards += 1

        action = row.player_action
        action_gto_freq = 0
        deviation_type = 'unknown'
        deviation_description = None
        deviation_severity = None

        # Get actual opponent position for this specific hand
        actual_vs_pos = row.vs_pos if hasattr(row, 'vs_pos') else vs_position

        # Look up hand-specific GTO using (hand_type, opponent_position)
        hand_specific_gto = None
        if hand_combo:
            # Try exact matchup lookup first
            hand_specific_gto = hand_gto_lookup.get((hand_combo, actual_vs_pos))

            # For opening scenarios, opponent_position is NULL in GTO data
            if not hand_specific_gto and scenario == 'opening':
                hand_specific_gto = hand_gto_lookup.get((hand_combo, None))

        # For combo-level filtering when showing leak mistakes:
        # Check if GTO wanted the leak action, not just the action taken
        leak_action_gto_freq = None
        if deviation is not None and leak_action and hand_combo and not hand_specific_gto:
            # Hand has hole cards but is NOT in the GTO range
            # This means GTO never plays this hand aggressively → fold is 100%
            if leak_action == 'fold':
                leak_action_gto_freq = 100  # Fold is always correct for hands not in range
            else:
                leak_action_gto_freq = 0  # No aggressive action for hands not in range
        elif deviation is not None and leak_action and hand_specific_gto:
            # Map leak_action to GTO action name (handle variations)
            gto_action_names = {
                'fold': ['fold', 'Fold'],
                'call': ['call', 'Call'],
                'raise': ['raise', 'Raise', '3bet', '3-bet', '3Bet'],
                '3bet': ['3bet', '3-bet', '3Bet', 'raise', 'Raise'],
                '4bet': ['4bet', '4-bet', '4Bet'],
                'open': ['open', 'Open', 'raise', 'Raise'],
            }
            possible_names = gto_action_names.get(leak_action, [leak_action])
            for name in possible_names:
                if name in hand_specific_gto:
                    leak_action_gto_freq = hand_specific_gto.get(name, 0)
                    break

            # If leak action not found directly, calculate it from remaining frequency
            # e.g., if GTO says call 66% + 3bet 34% = 100%, then fold = 0%
            if leak_action_gto_freq is None and leak_action == 'fold':
                # For fold: fold% = 100 - (call% + raise%)
                total_other = sum(hand_specific_gto.values())
                leak_action_gto_freq = max(0, 100 - total_other)
            elif leak_action_gto_freq is None and leak_action == 'call':
                # For call: calculate remaining after fold + raise
                fold_freq = hand_specific_gto.get('fold', hand_specific_gto.get('Fold', 0))
                raise_freq = hand_specific_gto.get('3bet', hand_specific_gto.get('raise', hand_specific_gto.get('Raise', 0)))
                leak_action_gto_freq = max(0, 100 - fold_freq - raise_freq)

        if hand_specific_gto:
            action_gto_freq = hand_specific_gto.get(action, 0)
            if action_gto_freq >= 50:
                deviation_type = 'correct'
                summary_correct += 1
            elif action_gto_freq >= 15:
                deviation_type = 'suboptimal'
                deviation_severity = 'minor'
                deviation_description = f"GTO plays this {action_gto_freq:.0f}% of time"
                summary_suboptimal += 1
            else:
                deviation_type = 'mistake'
                best_action = max(hand_specific_gto.items(), key=lambda x: x[1]) if hand_specific_gto else (None, 0)
                deviation_severity = 'major' if action_gto_freq < 5 else 'moderate'
                if best_action[0]:
                    deviation_description = f"GTO prefers {best_action[0]} ({best_action[1]:.0f}%)"
                summary_mistakes += 1
        elif hand_combo:
            # Hand has hole cards but is NOT in the GTO range
            # This means GTO never plays this hand aggressively → fold is 100% correct
            if action == 'fold':
                # Folding a hand that's not in range = correct play
                action_gto_freq = 100  # Implicitly 100% fold frequency
                deviation_type = 'correct'
                summary_correct += 1
            else:
                # Playing a hand that's not in range = mistake
                action_gto_freq = 0  # 0% frequency for this action
                deviation_type = 'mistake'
                deviation_severity = 'major'
                deviation_description = "Hand not in GTO range - should fold"
                summary_mistakes += 1
        elif gto_freqs:
            # No hole cards available - fall back to aggregate frequencies
            action_gto_freq = gto_freqs.get(action, 0)
            if action_gto_freq >= 50:
                deviation_type = 'correct'
                summary_correct += 1
            elif action_gto_freq >= 15:
                deviation_type = 'suboptimal'
                summary_suboptimal += 1
            else:
                deviation_type = 'mistake'
                summary_mistakes += 1

        # Combo-level filtering for leak mistakes
        # Skip hands where GTO doesn't support the leak action being a mistake
        if deviation is not None and leak_action_gto_freq is not None:
            if deviation < 0:
                # Under-doing: Show hands where GTO wanted the leak action (>= 50%)
                # e.g., Under-folding: only show hands where GTO says fold >= 50%
                if leak_action_gto_freq < 50:
                    continue  # Skip - GTO didn't want this action, so not a mistake
            else:
                # Over-doing: Show hands where GTO didn't want the leak action (< 50%)
                # e.g., Over-folding: only show hands where GTO says fold < 50%
                if leak_action_gto_freq >= 50:
                    continue  # Skip - GTO wanted this action, so not a mistake

        hands.append({
            'hand_id': row.hand_id,
            'player_name': row.player_name,
            'timestamp': row.timestamp.isoformat() if row.timestamp else None,
            'hole_cards': hole_cards,
            'hand_combo': hand_combo,
            'hand_tier': hand_tier,
            'hand_category': hand_category,
            'effective_stack_bb': float(row.effective_stack_bb) if row.effective_stack_bb else None,
            'player_action': action,
            'vs_position': row.vs_pos if hasattr(row, 'vs_pos') else None,
            'action_gto_freq': action_gto_freq,
            'leak_action_gto_freq': leak_action_gto_freq,  # Include for transparency
            'deviation_type': deviation_type,
            'deviation_description': deviation_description,
            'deviation_severity': deviation_severity
        })

    # Recalculate summary from actual hands returned (since we may have skipped some)
    summary_correct = sum(1 for h in hands if h['deviation_type'] == 'correct')
    summary_suboptimal = sum(1 for h in hands if h['deviation_type'] == 'suboptimal')
    summary_mistakes = sum(1 for h in hands if h['deviation_type'] == 'mistake')
    total_assessed = summary_correct + summary_suboptimal + summary_mistakes

    return {
        'scenario': scenario,
        'position': position,
        'vs_position': vs_position,
        'hero_nicknames': hero_nicknames,
        'total_hands_evaluated': total_hands_evaluated,  # All hands analyzed before filtering
        'total_hands': len(hands),  # Hands shown after filtering (mistakes only when deviation provided)
        'hands_with_hole_cards': sum(1 for h in hands if h.get('hole_cards')),
        'gto_frequencies': gto_freqs,
        'summary': {
            'correct': summary_correct,
            'suboptimal': summary_suboptimal,
            'mistakes': summary_mistakes,
            'correct_pct': round(summary_correct / total_assessed * 100, 1) if total_assessed else 0,
            'suboptimal_pct': round(summary_suboptimal / total_assessed * 100, 1) if total_assessed else 0,
            'mistake_pct': round(summary_mistakes / total_assessed * 100, 1) if total_assessed else 0
        },
        'hands': hands
    }


@router.get("/leaks")
def get_mygame_leaks(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get aggregated leak analysis for all hero nicknames.

    Combines stats from all configured hero nicknames and runs leak analysis.
    Returns same format as /api/players/{name}/leaks for consistency.
    """
    from ..services.stats_calculator import StatsCalculator
    from ..models.database_models import PlayerStats

    hero_nicknames = list(get_hero_nicknames(db))

    if not hero_nicknames:
        return {
            "player_name": "Hero",
            "total_hands": 0,
            "player_type": None,
            "core_metrics": {},
            "leaks": [],
            "leak_summary": {
                "total_leaks": 0,
                "critical_leaks": 0,
                "major_leaks": 0,
                "total_ev_opportunity": 0,
                "reliability": "insufficient_data"
            }
        }

    # Query player_stats for all hero nicknames
    hero_stats_list = db.query(PlayerStats).filter(
        PlayerStats.player_name.in_(hero_nicknames)
    ).all()

    if not hero_stats_list:
        return {
            "player_name": "Hero",
            "total_hands": 0,
            "player_type": None,
            "core_metrics": {},
            "leaks": [],
            "leak_summary": {
                "total_leaks": 0,
                "critical_leaks": 0,
                "major_leaks": 0,
                "total_ev_opportunity": 0,
                "reliability": "insufficient_data"
            }
        }

    # Aggregate stats across all heroes (weighted by total_hands)
    total_hands = sum(ps.total_hands or 0 for ps in hero_stats_list)

    if total_hands == 0:
        return {
            "player_name": "Hero",
            "total_hands": 0,
            "player_type": None,
            "core_metrics": {},
            "leaks": [],
            "leak_summary": {
                "total_leaks": 0,
                "critical_leaks": 0,
                "major_leaks": 0,
                "total_ev_opportunity": 0,
                "reliability": "insufficient_data"
            }
        }

    def weighted_avg(attr_name):
        """Calculate weighted average of an attribute across all hero stats."""
        total = 0.0
        total_weight = 0
        for ps in hero_stats_list:
            val = getattr(ps, attr_name, None)
            hands = ps.total_hands or 0
            if val is not None and hands > 0:
                total += float(val) * hands
                total_weight += hands
        return total / total_weight if total_weight > 0 else None

    # Build aggregated stats dictionary matching player_stats structure
    aggregated_stats = {
        'player_name': 'Hero',
        'total_hands': total_hands,
        'vpip_pct': weighted_avg('vpip_pct'),
        'pfr_pct': weighted_avg('pfr_pct'),
        'three_bet_pct': weighted_avg('three_bet_pct'),
        'fold_to_three_bet_pct': weighted_avg('fold_to_three_bet_pct'),
        'four_bet_pct': weighted_avg('four_bet_pct'),
        'cold_call_pct': weighted_avg('cold_call_pct'),
        'limp_pct': weighted_avg('limp_pct'),
        'squeeze_pct': weighted_avg('squeeze_pct'),
        'steal_pct': weighted_avg('steal_pct'),
        'bb_fold_to_steal_pct': weighted_avg('bb_fold_to_steal_pct'),
        'sb_fold_to_steal_pct': weighted_avg('sb_fold_to_steal_pct'),
        'bb_three_bet_vs_steal_pct': weighted_avg('bb_three_bet_vs_steal_pct'),
        'sb_three_bet_vs_steal_pct': weighted_avg('sb_three_bet_vs_steal_pct'),
        # Positional VPIP
        'vpip_utg': weighted_avg('vpip_utg'),
        'vpip_hj': weighted_avg('vpip_hj'),
        'vpip_mp': weighted_avg('vpip_mp'),
        'vpip_co': weighted_avg('vpip_co'),
        'vpip_btn': weighted_avg('vpip_btn'),
        'vpip_sb': weighted_avg('vpip_sb'),
        'vpip_bb': weighted_avg('vpip_bb'),
        # Positional PFR
        'pfr_utg': weighted_avg('pfr_utg'),
        'pfr_hj': weighted_avg('pfr_hj'),
        'pfr_mp': weighted_avg('pfr_mp'),
        'pfr_co': weighted_avg('pfr_co'),
        'pfr_btn': weighted_avg('pfr_btn'),
        'pfr_sb': weighted_avg('pfr_sb'),
        'pfr_bb': weighted_avg('pfr_bb'),
    }

    # Create StatsCalculator and get leak analysis
    calculator = StatsCalculator(aggregated_stats)
    leak_analysis = calculator.get_leak_analysis()
    core_metrics = calculator.get_core_metrics()
    player_type_info = calculator.get_player_type_details()

    # Extract the leaks list from the analysis result
    leaks_list = leak_analysis.get("leaks", [])

    return {
        "player_name": "Hero",
        "hero_nicknames": hero_nicknames,
        "total_hands": total_hands,
        "player_type": player_type_info,
        "core_metrics": core_metrics,
        "leaks": leaks_list,
        "leak_summary": {
            "total_leaks": leak_analysis.get("total_leaks", 0),
            "critical_leaks": leak_analysis.get("critical_leaks", 0),
            "major_leaks": leak_analysis.get("major_leaks", 0),
            "total_ev_opportunity": leak_analysis.get("total_ev_opportunity_bb_100", 0),
            "reliability": leak_analysis.get("reliability", "low")
        }
    }
