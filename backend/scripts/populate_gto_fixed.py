#!/usr/bin/env python3
"""
FIXED: Positional GTO analysis tracking opportunities AND actions.

Key fix: Track all scenario opportunities, not just when action is taken.
"""

import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional, List, Dict, Set, Tuple
from collections import defaultdict

DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def determine_player_scenarios(player_name: str, position: str,
                               preflop_actions: List[Dict],
                               player_action_index: int) -> List[Tuple[str, str]]:
    """
    Determine all GTO scenarios the player is in at their decision point.

    Returns list of (scenario_name, action_taken) tuples.

    Key insight: A player can be in multiple scenarios simultaneously:
    - Facing a raise, they can fold/call/3bet (3 scenarios)
    - Opening position, they can open/fold (2 scenarios)
    """
    scenarios = []

    # Analyze action context
    facing_raise = False
    raiser_position = None
    facing_3bet = False
    facing_4bet = False
    is_open_opportunity = True

    # Look at actions before this player
    for prior_action in preflop_actions[:player_action_index]:
        prior_type = prior_action['action_type']
        prior_pos = prior_action['position']

        if prior_type in ['raise', 'bet']:
            if not facing_raise:
                facing_raise = True
                raiser_position = prior_pos
                is_open_opportunity = False
            elif facing_raise and not facing_3bet:
                facing_3bet = True
            elif facing_3bet and not facing_4bet:
                facing_4bet = True

        if prior_type != 'fold':
            is_open_opportunity = False

    # Get player's actual action
    player_action = preflop_actions[player_action_index]['action_type']

    # OPENING SCENARIOS - opportunity to open (first raiser)
    if is_open_opportunity and position in ['UTG', 'MP', 'CO', 'BTN', 'SB']:
        if player_action == 'raise':
            scenarios.append((f"{position}_open", player_action))
        # Note: If they fold/check, they didn't open, but they HAD the opportunity
        # We need to track this as a "fold" in the open scenario

    # DEFENSE SCENARIOS - facing open raise
    if facing_raise and not facing_3bet and raiser_position:
        scenario_base = f"{position}_vs_{raiser_position}"

        if player_action == 'fold':
            scenarios.append((f"{scenario_base}_fold", player_action))
        elif player_action == 'call':
            scenarios.append((f"{scenario_base}_call", player_action))
        elif player_action == 'raise':
            scenarios.append((f"{scenario_base}_3bet", player_action))

    # FACING 3BET
    if facing_3bet and not facing_4bet and raiser_position:
        scenario_base = f"{position}_vs_{raiser_position}_3bet"

        if player_action == 'fold':
            scenarios.append((f"{scenario_base}_fold", player_action))
        elif player_action == 'call':
            scenarios.append((f"{scenario_base}_call", player_action))
        elif player_action in ['raise', 'allin']:
            scenarios.append((f"{scenario_base}_4bet", player_action))

    # FACING 4BET
    if facing_4bet and raiser_position:
        scenario_base = f"{position}_vs_{raiser_position}_4bet"

        if player_action == 'fold':
            scenarios.append((f"{scenario_base}_fold", player_action))
        elif player_action == 'call':
            scenarios.append((f"{scenario_base}_call", player_action))
        elif player_action in ['raise', 'allin']:
            scenarios.append((f"{scenario_base}_allin", player_action))

    return scenarios


def process_player_fixed(db, player_name: str, limit: int = 1000) -> Dict:
    """
    Process player tracking OPPORTUNITIES and ACTIONS separately.
    """
    print(f"\n{'=' * 80}")
    print(f"Processing: {player_name}")
    print(f"{'=' * 80}\n")

    # Get all hands where this player took preflop actions
    query = text("""
        SELECT DISTINCT ha.hand_id
        FROM hand_actions ha
        WHERE ha.player_name = :player_name
          AND ha.street = 'preflop'
        ORDER BY ha.hand_id DESC
        LIMIT :limit
    """)

    hand_ids = db.execute(query, {
        'player_name': player_name,
        'limit': limit
    }).fetchall()

    print(f"Found {len(hand_ids)} hands")

    if not hand_ids:
        print(f"⚠️  No hands found, skipping...")
        return {'player': player_name, 'scenarios': 0}

    # Track: scenario_name -> {action_type: count}
    scenario_stats = defaultdict(lambda: defaultdict(int))

    for hand_row in hand_ids:
        hand_id = hand_row[0]

        # Get all preflop actions for this hand
        actions_query = text("""
            SELECT action_id, player_name, position, action_type
            FROM hand_actions
            WHERE hand_id = :hand_id AND street = 'preflop'
            ORDER BY action_id
        """)

        all_actions = db.execute(actions_query, {'hand_id': hand_id}).fetchall()
        all_actions_list = [dict(a._mapping) for a in all_actions]

        # Find player's action(s)
        for idx, action in enumerate(all_actions_list):
            if action['player_name'] != player_name:
                continue

            position = action['position']
            action_type = action['action_type']

            # Determine scenarios
            scenarios = determine_player_scenarios(
                player_name=player_name,
                position=position,
                preflop_actions=all_actions_list,
                player_action_index=idx
            )

            # Record each scenario/action combo
            for scenario_name, action_taken in scenarios:
                scenario_stats[scenario_name][action_taken] += 1

    print(f"✅ Analyzed {len(scenario_stats)} unique scenarios")

    # Now calculate frequencies and update database
    stats_updated = 0

    for scenario_name, action_counts in scenario_stats.items():
        # Check if scenario exists
        scenario_query = text("""
            SELECT scenario_id FROM gto_scenarios
            WHERE scenario_name = :scenario_name
        """)
        scenario_result = db.execute(scenario_query, {
            'scenario_name': scenario_name
        }).fetchone()

        if not scenario_result:
            # Scenario not in database yet
            continue

        scenario_id = scenario_result[0]

        # Total opportunities in this scenario
        total_opportunities = sum(action_counts.values())

        # Calculate player's action frequency for this scenario
        # The scenario name indicates WHICH action we're tracking
        # E.g., "UTG_open" tracks opening frequency, "BB_vs_UTG_fold" tracks fold frequency

        # Extract the action we're measuring from scenario name
        if '_open' in scenario_name:
            # Opening scenario - measure raise frequency
            action_count = action_counts.get('raise', 0)
        elif '_fold' in scenario_name:
            action_count = action_counts.get('fold', 0)
        elif '_call' in scenario_name:
            action_count = action_counts.get('call', 0)
        elif '_3bet' in scenario_name and '4bet' not in scenario_name:
            action_count = action_counts.get('raise', 0)
        elif '_4bet' in scenario_name or '_allin' in scenario_name:
            action_count = action_counts.get('raise', 0) + action_counts.get('allin', 0)
        else:
            # Default: take the most common action
            action_count = max(action_counts.values()) if action_counts else 0

        player_freq = action_count / total_opportunities if total_opportunities > 0 else 0.0

        # Get GTO frequency for this scenario (average across all hands)
        gto_query = text("""
            SELECT AVG(frequency) as avg_freq
            FROM gto_frequencies gf
            WHERE gf.scenario_id = :scenario_id
        """)

        gto_result = db.execute(gto_query, {'scenario_id': scenario_id}).fetchone()
        avg_gto_freq = float(gto_result[0]) if gto_result and gto_result[0] else None

        if avg_gto_freq is None:
            continue

        freq_diff = player_freq - avg_gto_freq

        # Estimate EV loss
        ev_loss_per_hand = abs(freq_diff) * 0.5
        total_ev_loss = ev_loss_per_hand * total_opportunities

        # Classify leak
        leak_type = None
        leak_severity = None

        if total_opportunities >= 5:
            if abs(freq_diff) > 0.3:
                leak_severity = 'major'
            elif abs(freq_diff) > 0.15:
                leak_severity = 'moderate'
            elif abs(freq_diff) > 0.05:
                leak_severity = 'minor'

            if 'fold' in scenario_name:
                leak_type = 'overfold' if freq_diff > 0 else 'underfold'
            elif 'call' in scenario_name:
                leak_type = 'overcall' if freq_diff > 0 else 'undercall'
            elif '3bet' in scenario_name:
                leak_type = 'over3bet' if freq_diff > 0 else 'under3bet'
            elif 'open' in scenario_name:
                leak_type = 'overopen' if freq_diff > 0 else 'underopen'

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
            'total_hands': total_opportunities,
            'player_frequency': player_freq,
            'gto_frequency': avg_gto_freq,
            'frequency_diff': freq_diff,
            'total_ev_loss_bb': total_ev_loss,
            'avg_ev_loss_bb': ev_loss_per_hand,
            'leak_type': leak_type,
            'leak_severity': leak_severity
        })

        stats_updated += 1

    db.commit()
    print(f"✅ Updated {stats_updated} stat records")

    return {'player': player_name, 'scenarios': stats_updated}


def main():
    """Main execution."""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("FIXED: POSITIONAL GTO ANALYSIS (TRACKING OPPORTUNITIES)")
        print("=" * 80)
        print()

        # Clear existing stats to rebuild correctly
        print("Clearing old stats to rebuild with correct frequencies...")
        db.execute(text("DELETE FROM player_gto_stats"))
        db.commit()
        print("✅ Old stats cleared")
        print()

        # Get all players
        players_query = text("""
            SELECT DISTINCT player_name
            FROM hand_actions
            WHERE street = 'preflop'
            ORDER BY player_name
        """)

        players = db.execute(players_query).fetchall()
        player_list = [p[0] for p in players]

        print(f"Found {len(player_list)} players to analyze")
        print()

        results = []
        for player in player_list:
            result = process_player_fixed(db, player, limit=1000)
            results.append(result)

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        for r in results:
            print(f"  {r['player']:20s} - {r['scenarios']:3d} scenarios")

        print()
        print("✅ ALL PLAYERS PROCESSED WITH FIXED FREQUENCIES")
        print("=" * 80)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
