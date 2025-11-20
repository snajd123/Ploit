#!/usr/bin/env python3
"""
Extract hole cards from hand histories and populate player GTO analysis.

This script:
1. Queries all hands for a player
2. Parses hole cards from raw_hand_text
3. Maps preflop actions to GTO scenarios
4. Records actions in player_actions table
5. Updates player_gto_stats aggregates
"""

import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from decimal import Decimal

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

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


def parse_hole_cards(raw_text: str, player_name: str) -> Optional[str]:
    """
    Parse hole cards from raw hand text.

    Args:
        raw_text: Full hand history text
        player_name: Player to extract cards for

    Returns:
        Hole cards like "AhKd" or None if not found
    """
    if not raw_text:
        return None

    # Pattern: "Dealt to {player} [{card1} {card2}]"
    pattern = rf'Dealt to {re.escape(player_name)} \[([A-Z0-9]{{2}}) ([A-Z0-9]{{2}})\]'
    match = re.search(pattern, raw_text)

    if match:
        card1, card2 = match.groups()
        return f"{card1}{card2}"  # e.g., "AhKd"

    return None


def map_action_to_gto_scenario(
    position: str,
    action_type: str,
    preflop_actions: List[Dict],
    player_action_index: int
) -> Optional[str]:
    """
    Map a preflop action to a GTO scenario name.

    Args:
        position: Player's position (UTG, MP, CO, BTN, SB, BB)
        action_type: Action taken (fold, call, raise, bet, check, allin)
        preflop_actions: All preflop actions in order
        player_action_index: Index of current player's action

    Returns:
        Scenario name like 'BB_vs_UTG_call' or None if not mappable
    """
    # Analyze action context
    facing_raise = False
    raiser_position = None
    facing_3bet = False
    facing_4bet = False
    is_open = True

    # Look at all actions before this one
    for i, prior_action in enumerate(preflop_actions[:player_action_index]):
        prior_type = prior_action['action_type']
        prior_pos = prior_action['position']

        if prior_type in ['raise', 'bet']:
            if not facing_raise:
                # First raise
                facing_raise = True
                raiser_position = prior_pos
                is_open = False
            elif facing_raise and not facing_3bet:
                # Second raise (3bet)
                facing_3bet = True
            elif facing_3bet and not facing_4bet:
                # Third raise (4bet)
                facing_4bet = True

        if prior_type != 'fold':
            is_open = False

    # Opening scenarios
    if is_open and action_type == 'raise':
        if position in ['UTG', 'MP', 'CO', 'BTN', 'SB']:
            return f"{position}_open"
        return None

    # Defense scenarios (facing open raise)
    if facing_raise and not facing_3bet and raiser_position:
        if action_type == 'fold':
            return f"{position}_vs_{raiser_position}_fold"
        elif action_type == 'call':
            return f"{position}_vs_{raiser_position}_call"
        elif action_type == 'raise':
            return f"{position}_vs_{raiser_position}_3bet"

    # Facing 3bet scenarios
    if facing_3bet and not facing_4bet and raiser_position:
        if action_type == 'fold':
            return f"{position}_vs_{raiser_position}_3bet_fold"
        elif action_type == 'call':
            return f"{position}_vs_{raiser_position}_3bet_call"
        elif action_type in ['raise', 'allin']:
            return f"{position}_vs_{raiser_position}_3bet_4bet"

    # Facing 4bet scenarios
    if facing_4bet and raiser_position:
        if action_type == 'fold':
            return f"{position}_vs_{raiser_position}_4bet_fold"
        elif action_type == 'call':
            return f"{position}_vs_{raiser_position}_4bet_call"
        elif action_type in ['raise', 'allin']:
            return f"{position}_vs_{raiser_position}_4bet_allin"

    return None


def get_gto_frequency(db, scenario_name: str, hand: str, position: str) -> Optional[float]:
    """Get GTO frequency for a scenario/hand/position."""
    query = text("""
        SELECT gf.frequency
        FROM gto_frequencies gf
        JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
        WHERE gs.scenario_name = :scenario_name
          AND gf.hand = :hand
          AND gf.position = :position
    """)

    result = db.execute(query, {
        'scenario_name': scenario_name,
        'hand': hand,
        'position': position
    }).fetchone()

    return float(result[0]) if result else None


def estimate_ev_loss(gto_frequency: float, action_taken: str) -> float:
    """
    Estimate EV loss in BB based on GTO frequency deviation.

    This is a simplified model. Real EV calculation requires solver data.
    """
    if gto_frequency is None:
        return 0.0

    # If action was taken but GTO never does it (freq = 0), major mistake
    if gto_frequency == 0.0:
        return 2.0  # ~2BB loss for taking 0% GTO action

    # If action wasn't taken but GTO always does it (freq = 1.0), major mistake
    if gto_frequency == 1.0:
        return 2.0  # ~2BB loss for not taking 100% GTO action

    # For mixed strategies, estimate based on deviation
    # GTO mixes optimally, so deviating from mix loses EV
    deviation = abs(gto_frequency - 0.5)  # How far from 50/50

    if deviation > 0.4:  # Strong preference (>90% or <10%)
        return 1.5
    elif deviation > 0.2:  # Moderate preference (>70% or <30%)
        return 0.8
    else:  # Weak preference (near 50/50)
        return 0.3

    return 0.0


def populate_player_gto(player_name: Optional[str] = None, limit: int = 1000):
    """
    Populate GTO analysis for player(s).

    Args:
        player_name: Specific player to analyze (None = all players)
        limit: Maximum number of hands to process per player
    """
    db = SessionLocal()

    try:
        # Get list of players to process
        if player_name:
            players_to_process = [player_name]
        else:
            # Get all players with preflop actions
            players_query = text("""
                SELECT DISTINCT player_name
                FROM hand_actions
                WHERE street = 'preflop'
                ORDER BY player_name
            """)
            players_result = db.execute(players_query).fetchall()
            players_to_process = [p[0] for p in players_result]

        print(f"=" * 80)
        print(f"POPULATING GTO ANALYSIS")
        print(f"=" * 80)
        print(f"Players to process: {len(players_to_process)}")
        print()

        for current_player in players_to_process:
            print(f"\n{'=' * 80}")
            print(f"Processing: {current_player}")
            print(f"{'=' * 80}\n")

            # Get all hands for this player with preflop actions
            query = text("""
                SELECT DISTINCT
                    rh.hand_id,
                    rh.raw_hand_text,
                    rh.timestamp
                FROM raw_hands rh
                JOIN hand_actions ha ON rh.hand_id = ha.hand_id
                WHERE ha.player_name = :player_name
                  AND ha.street = 'preflop'
                  AND rh.raw_hand_text IS NOT NULL
                ORDER BY rh.timestamp DESC
                LIMIT :limit
            """)

            hands = db.execute(query, {
                'player_name': current_player,
                'limit': limit
            }).fetchall()

            print(f"Found {len(hands)} hands for {current_player}")
            print()

            if not hands:
                print(f"⚠️  No hands found for {current_player}, skipping...")
                continue

            actions_recorded = 0
            actions_skipped = 0
            hands_processed = 0

            for hand_row in hands:
            hand_id = hand_row.hand_id
            raw_text = hand_row.raw_hand_text
            timestamp = hand_row.timestamp

            # Parse hole cards
            hole_cards = parse_hole_cards(raw_text, player_name)
            if not hole_cards:
                actions_skipped += 1
                continue

            # Normalize to hand notation
            hand_notation = normalize_hand(hole_cards)
            if not hand_notation:
                actions_skipped += 1
                continue

            # Get all preflop actions for this hand
            actions_query = text("""
                SELECT action_id, player_name, position, action_type, amount
                FROM hand_actions
                WHERE hand_id = :hand_id AND street = 'preflop'
                ORDER BY action_id
            """)

            all_actions = db.execute(actions_query, {'hand_id': hand_id}).fetchall()
            all_actions_list = [dict(a._mapping) for a in all_actions]

            # Find player's actions
            for idx, action in enumerate(all_actions_list):
                if action['player_name'] != player_name:
                    continue

                position = action['position']
                action_type = action['action_type']

                # Map to GTO scenario
                scenario_name = map_action_to_gto_scenario(
                    position=position,
                    action_type=action_type,
                    preflop_actions=all_actions_list,
                    player_action_index=idx
                )

                if not scenario_name:
                    continue

                # Check if scenario exists
                scenario_query = text("""
                    SELECT scenario_id FROM gto_scenarios
                    WHERE scenario_name = :scenario_name
                """)
                scenario_result = db.execute(scenario_query, {
                    'scenario_name': scenario_name
                }).fetchone()

                if not scenario_result:
                    # Scenario not in database (e.g., not yet imported)
                    continue

                scenario_id = scenario_result[0]

                # Get GTO frequency
                gto_freq = get_gto_frequency(db, scenario_name, hand_notation, position)

                # Estimate EV loss
                ev_loss = estimate_ev_loss(gto_freq, action_type) if gto_freq is not None else None

                # Determine if mistake
                is_mistake = False
                mistake_severity = 'minor'

                if gto_freq is not None:
                    if gto_freq == 0.0:
                        is_mistake = True
                        mistake_severity = 'major'
                    elif gto_freq < 0.1:
                        is_mistake = True
                        mistake_severity = 'moderate'
                    elif gto_freq < 0.3:
                        is_mistake = True
                        mistake_severity = 'minor'

                # Insert into player_actions
                insert_action = text("""
                    INSERT INTO player_actions
                    (player_name, hand_id, timestamp, scenario_id, hole_cards, action_taken,
                     gto_frequency, ev_loss_bb, is_mistake, mistake_severity)
                    VALUES
                    (:player_name, :hand_id, :timestamp, :scenario_id, :hole_cards, :action_taken,
                     :gto_frequency, :ev_loss_bb, :is_mistake, :mistake_severity)
                    ON CONFLICT DO NOTHING
                """)

                db.execute(insert_action, {
                    'player_name': player_name,
                    'hand_id': hand_id,
                    'timestamp': timestamp,
                    'scenario_id': scenario_id,
                    'hole_cards': hand_notation,
                    'action_taken': action_type,
                    'gto_frequency': gto_freq,
                    'ev_loss_bb': ev_loss,
                    'is_mistake': is_mistake,
                    'mistake_severity': mistake_severity
                })

                actions_recorded += 1

            hands_processed += 1

            if hands_processed % 50 == 0:
                print(f"Processed {hands_processed} hands, recorded {actions_recorded} actions...")
                db.commit()

        db.commit()

        print()
        print(f"✅ Processed {hands_processed} hands")
        print(f"✅ Recorded {actions_recorded} player actions")
        print(f"⚠️  Skipped {actions_skipped} actions (no hole cards or scenario)")
        print()

        # Now update player_gto_stats aggregates
        print("Updating player_gto_stats aggregates...")
        print()

        # Get all scenarios with actions
        scenarios_query = text("""
            SELECT DISTINCT scenario_id
            FROM player_actions
            WHERE player_name = :player_name
        """)

        scenarios = db.execute(scenarios_query, {'player_name': player_name}).fetchall()

        for scenario_row in scenarios:
            scenario_id = scenario_row[0]

            # Calculate aggregates
            agg_query = text("""
                SELECT
                    COUNT(*) as total_hands,
                    AVG(gto_frequency) as avg_gto_freq,
                    SUM(ev_loss_bb) as total_ev_loss,
                    AVG(ev_loss_bb) as avg_ev_loss
                FROM player_actions
                WHERE player_name = :player_name
                  AND scenario_id = :scenario_id
            """)

            agg = db.execute(agg_query, {
                'player_name': player_name,
                'scenario_id': scenario_id
            }).fetchone()

            total_hands = agg.total_hands
            avg_gto_freq = float(agg.avg_gto_freq) if agg.avg_gto_freq else None
            total_ev_loss = float(agg.total_ev_loss) if agg.total_ev_loss else 0.0
            avg_ev_loss = float(agg.avg_ev_loss) if agg.avg_ev_loss else 0.0

            # Player frequency = how often they took this action
            player_freq = 1.0  # Simplified: all recorded actions were taken

            # Frequency difference
            freq_diff = (player_freq - avg_gto_freq) if avg_gto_freq else None

            # Classify leak
            leak_type = None
            leak_severity = None

            if avg_gto_freq is not None and total_hands >= 5:
                if freq_diff and abs(freq_diff) > 0.3:
                    leak_severity = 'major'
                elif freq_diff and abs(freq_diff) > 0.15:
                    leak_severity = 'moderate'
                elif freq_diff and abs(freq_diff) > 0.05:
                    leak_severity = 'minor'

                # Determine leak type from scenario name
                scenario_name_query = text("SELECT scenario_name FROM gto_scenarios WHERE scenario_id = :id")
                scenario_name = db.execute(scenario_name_query, {'id': scenario_id}).fetchone()[0]

                if 'fold' in scenario_name and freq_diff and freq_diff > 0:
                    leak_type = 'overfold'
                elif 'fold' in scenario_name and freq_diff and freq_diff < 0:
                    leak_type = 'underfold'
                elif 'call' in scenario_name and freq_diff and freq_diff > 0:
                    leak_type = 'overcall'
                elif 'call' in scenario_name and freq_diff and freq_diff < 0:
                    leak_type = 'undercall'
                elif '3bet' in scenario_name and freq_diff and freq_diff > 0:
                    leak_type = 'over3bet'
                elif '3bet' in scenario_name and freq_diff and freq_diff < 0:
                    leak_type = 'under3bet'

            # Upsert player_gto_stats
            upsert_stats = text("""
                INSERT INTO player_gto_stats
                (player_name, scenario_id, total_hands, player_frequency, gto_frequency,
                 frequency_diff, total_ev_loss_bb, avg_ev_loss_bb, leak_type, leak_severity)
                VALUES
                (:player_name, :scenario_id, :total_hands, :player_frequency, :gto_frequency,
                 :frequency_diff, :total_ev_loss_bb, :avg_ev_loss_bb, :leak_type, :leak_severity)
                ON CONFLICT (player_name, scenario_id)
                DO UPDATE SET
                    total_hands = EXCLUDED.total_hands,
                    player_frequency = EXCLUDED.player_frequency,
                    gto_frequency = EXCLUDED.gto_frequency,
                    frequency_diff = EXCLUDED.frequency_diff,
                    total_ev_loss_bb = EXCLUDED.total_ev_loss_bb,
                    avg_ev_loss_bb = EXCLUDED.avg_ev_loss_bb,
                    leak_type = EXCLUDED.leak_type,
                    leak_severity = EXCLUDED.leak_severity,
                    last_updated = CURRENT_TIMESTAMP
            """)

            db.execute(upsert_stats, {
                'player_name': player_name,
                'scenario_id': scenario_id,
                'total_hands': total_hands,
                'player_frequency': player_freq,
                'gto_frequency': avg_gto_freq,
                'frequency_diff': freq_diff,
                'total_ev_loss_bb': total_ev_loss,
                'avg_ev_loss_bb': avg_ev_loss,
                'leak_type': leak_type,
                'leak_severity': leak_severity
            })

        db.commit()

        print(f"✅ Updated {len(scenarios)} scenario aggregates in player_gto_stats")
        print()

        # Show summary
        print("=" * 80)
        print("GTO ANALYSIS SUMMARY")
        print("=" * 80)
        print()

        summary_query = text("""
            SELECT
                gs.scenario_name,
                pgs.total_hands,
                pgs.leak_type,
                pgs.leak_severity,
                pgs.total_ev_loss_bb
            FROM player_gto_stats pgs
            JOIN gto_scenarios gs ON pgs.scenario_id = gs.scenario_id
            WHERE pgs.player_name = :player_name
              AND pgs.total_hands >= 5
            ORDER BY pgs.total_ev_loss_bb DESC NULLS LAST
            LIMIT 10
        """)

        leaks = db.execute(summary_query, {'player_name': player_name}).fetchall()

        if leaks:
            print(f"Top leaks for {player_name}:")
            print()
            for leak in leaks:
                scenario = leak.scenario_name
                hands = leak.total_hands
                leak_type = leak.leak_type or 'N/A'
                severity = leak.leak_severity or 'N/A'
                ev_loss = leak.total_ev_loss_bb or 0.0

                print(f"  {scenario:30s} | {hands:3d} hands | {leak_type:12s} | "
                      f"{severity:8s} | {ev_loss:6.2f} BB loss")
        else:
            print(f"No major leaks detected for {player_name} (need more hands)")

        print()
        print("=" * 80)
        print("✅ GTO ANALYSIS COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python populate_player_gto.py <player_name> [limit]")
        print()
        print("Example: python populate_player_gto.py snajd 500")
        sys.exit(1)

    player_name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 500

    populate_player_gto(player_name, limit)
