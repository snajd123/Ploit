#!/usr/bin/env python3
"""
Analyze preflop actions from hand histories and compare to GTO.

This script:
1. Reads preflop actions from hand_actions table
2. Maps them to GTO scenarios
3. Records them in player_actions and updates player_gto_stats
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Optional, Tuple
from datetime import datetime

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def normalize_hand(cards: str) -> str:
    """
    Convert hole cards to hand notation (AKo, JTs, 22, etc.)

    Args:
        cards: e.g., "AhKd", "JsTs", "2c2d"

    Returns:
        Hand notation like "AKo", "JTs", "22"
    """
    if not cards or len(cards) != 4:
        return None

    rank1, suit1, rank2, suit2 = cards[0], cards[1], cards[2], cards[3]

    # Rank order for comparison
    rank_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
                  '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

    r1 = rank_order.get(rank1, 0)
    r2 = rank_order.get(rank2, 0)

    # Always put higher rank first
    if r1 > r2:
        high, low = rank1, rank2
        high_suit, low_suit = suit1, suit2
    else:
        high, low = rank2, rank1
        high_suit, low_suit = suit2, suit1

    # Determine hand type
    is_pair = (high == low)
    is_suited = (high_suit == low_suit)

    if is_pair:
        return f"{high}{low}"
    elif is_suited:
        return f"{high}{low}s"
    else:
        return f"{high}{low}o"


def map_action_to_gto_scenario(
    position: str,
    action_type: str,
    facing_raise: bool,
    raiser_position: Optional[str],
    facing_3bet: bool,
    facing_4bet: bool
) -> Optional[str]:
    """
    Map a preflop action to a GTO scenario name.

    Args:
        position: Player's position (UTG, MP, CO, BTN, SB, BB)
        action_type: fold, call, raise, bet, check, allin
        facing_raise: Is player facing a raise?
        raiser_position: Position of the raiser (if any)
        facing_3bet: Is player facing a 3bet?
        facing_4bet: Is player facing a 4bet?

    Returns:
        Scenario name like 'BB_vs_UTG_call' or None if not mappable
    """
    # Opening scenarios
    if not facing_raise and action_type == 'raise':
        if position in ['UTG', 'MP', 'CO', 'BTN', 'SB']:
            return f"{position}_open"
        return None

    # Defense scenarios (facing open raise)
    if facing_raise and not facing_3bet and raiser_position:
        action_map = {
            'fold': 'fold',
            'call': 'call',
            'raise': '3bet'
        }
        action = action_map.get(action_type)
        if action and position in ['BB', 'SB', 'BTN', 'CO']:
            return f"{position}_vs_{raiser_position}_{action}"

    # Facing 3bet scenarios
    if facing_3bet and not facing_4bet and raiser_position:
        action_map = {
            'fold': 'fold',
            'call': 'call',
            'raise': '4bet',
            'allin': 'allin'
        }
        action = action_map.get(action_type)
        if action:
            return f"{position}_vs_{raiser_position}_3bet_{action}"

    # Facing 4bet scenarios
    if facing_4bet and raiser_position:
        action_map = {
            'fold': 'fold',
            'call': 'call',
            'raise': '5bet',
            'allin': 'allin'
        }
        action = action_map.get(action_type)
        if action:
            return f"{position}_vs_{raiser_position}_4bet_{action}"

    return None


def analyze_preflop_actions(player_name: str):
    """Analyze preflop actions for a player and populate GTO stats."""

    db = SessionLocal()

    try:
        print(f"=" * 80)
        print(f"ANALYZING PREFLOP GTO FOR PLAYER: {player_name}")
        print(f"=" * 80)
        print()

        # Get all preflop actions for this player from hand_actions table
        query = text("""
            SELECT
                ha.hand_id,
                ha.player_name,
                ha.position,
                ha.action_type,
                ha.amount,
                rh.timestamp,
                -- Get hole cards from somewhere (need to add this to schema)
                -- For now, we'll need to parse from raw_hand_text or use a different approach
                NULL as hole_cards
            FROM hand_actions ha
            JOIN raw_hands rh ON ha.hand_id = rh.hand_id
            WHERE ha.player_name = :player_name
              AND ha.street = 'preflop'
            ORDER BY ha.hand_id, ha.action_id
        """)

        results = db.execute(query, {"player_name": player_name}).fetchall()

        print(f"Found {len(results)} preflop actions for {player_name}")
        print()

        if not results:
            print(f"❌ No preflop actions found for {player_name}")
            print("   Make sure hand histories have been imported first.")
            return

        # For now, let's create a simpler analysis using player_hand_summary
        # This table has boolean flags we can use

        print("Analyzing using player_hand_summary table...")
        print()

        summary_query = text("""
            SELECT
                phs.hand_id,
                phs.player_name,
                phs.position,
                phs.vpip,
                phs.pfr,
                phs.limp,
                phs.faced_raise_preflop,
                phs.three_bet,
                phs.faced_three_bet,
                phs.fold_to_three_bet,
                phs.call_three_bet,
                phs.four_bet,
                rh.timestamp
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE phs.player_name = :player_name
            ORDER BY rh.timestamp DESC
            LIMIT 100
        """)

        summaries = db.execute(summary_query, {"player_name": player_name}).fetchall()

        print(f"Analyzing {len(summaries)} hands...")
        print()

        # Analyze opening frequencies by position
        position_opens = {}
        position_totals = {}

        for row in summaries:
            pos = row.position
            if pos not in position_totals:
                position_totals[pos] = 0
                position_opens[pos] = 0

            position_totals[pos] += 1
            if row.pfr:  # Player raised first in
                position_opens[pos] += 1

        print("OPENING FREQUENCIES BY POSITION:")
        print("-" * 80)
        for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB']:
            if pos in position_totals and position_totals[pos] > 0:
                player_open_pct = (position_opens[pos] / position_totals[pos]) * 100
                print(f"{pos:4s}: {player_open_pct:5.1f}% ({position_opens[pos]}/{position_totals[pos]} hands)")

        print()
        print("=" * 80)
        print("⚠️  PREFLOP GTO ANALYSIS INCOMPLETE")
        print("=" * 80)
        print()
        print("ISSUE: The hand_actions table doesn't store hole cards, so we can't")
        print("       map specific actions to GTO scenarios (need to know the hand).")
        print()
        print("SOLUTION OPTIONS:")
        print("1. Add hole_cards column to hand_actions table")
        print("2. Parse hole cards from raw_hand_text when needed")
        print("3. Add hole_cards to player_hand_summary table")
        print()
        print("For now, here's what we found about overall tendencies:")
        print(f"- {player_name} plays {len(summaries)} hands in sample")
        print(f"- Opening frequencies shown above")
        print()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_preflop_gto.py <player_name>")
        sys.exit(1)

    player_name = sys.argv[1]
    analyze_preflop_actions(player_name)
