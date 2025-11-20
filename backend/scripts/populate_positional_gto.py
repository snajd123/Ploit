#!/usr/bin/env python3
"""
Populate GTO analysis for ALL players (both hero and opponents).

- Hero (with visible hole cards): Hand-specific GTO analysis
- Opponents (no hole cards): Positional frequency analysis

Opponent analysis tracks:
- Opening frequencies by position
- Defense frequencies (fold/call/3bet vs raises)
- 3bet/4bet frequencies
- Overall tendencies compared to GTO
"""

import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional, List, Dict, Set
from decimal import Decimal

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def find_hero_players(db) -> Set[str]:
    """Find players with visible hole cards."""
    query = text("""
        SELECT raw_hand_text
        FROM raw_hands
        WHERE raw_hand_text LIKE '%Dealt to%'
        LIMIT 100
    """)

    results = db.execute(query).fetchall()

    heroes = set()
    for row in results:
        text_content = row[0]
        if not text_content:
            continue

        matches = re.findall(r'Dealt to (\w+) \[', text_content)
        heroes.update(matches)

    return heroes


def map_action_to_gto_scenario(position: str, action_type: str,
                                preflop_actions: List[Dict],
                                player_action_index: int) -> Optional[str]:
    """Map a preflop action to a GTO scenario name."""
    facing_raise = False
    raiser_position = None
    facing_3bet = False
    facing_4bet = False
    is_open = True

    # Analyze actions before this one
    for prior_action in preflop_actions[:player_action_index]:
        prior_type = prior_action['action_type']
        prior_pos = prior_action['position']

        if prior_type in ['raise', 'bet']:
            if not facing_raise:
                facing_raise = True
                raiser_position = prior_pos
                is_open = False
            elif facing_raise and not facing_3bet:
                facing_3bet = True
            elif facing_3bet and not facing_4bet:
                facing_4bet = True

        if prior_type != 'fold':
            is_open = False

    # Opening scenarios
    if is_open and action_type == 'raise':
        if position in ['UTG', 'MP', 'CO', 'BTN', 'SB']:
            return f"{position}_open"

    # Defense scenarios
    if facing_raise and not facing_3bet and raiser_position:
        if action_type == 'fold':
            return f"{position}_vs_{raiser_position}_fold"
        elif action_type == 'call':
            return f"{position}_vs_{raiser_position}_call"
        elif action_type == 'raise':
            return f"{position}_vs_{raiser_position}_3bet"

    # Facing 3bet
    if facing_3bet and not facing_4bet and raiser_position:
        if action_type == 'fold':
            return f"{position}_vs_{raiser_position}_3bet_fold"
        elif action_type == 'call':
            return f"{position}_vs_{raiser_position}_3bet_call"
        elif action_type in ['raise', 'allin']:
            return f"{position}_vs_{raiser_position}_3bet_4bet"

    # Facing 4bet
    if facing_4bet and raiser_position:
        if action_type == 'fold':
            return f"{position}_vs_{raiser_position}_4bet_fold"
        elif action_type == 'call':
            return f"{position}_vs_{raiser_position}_4bet_call"
        elif action_type in ['raise', 'allin']:
            return f"{position}_vs_{raiser_position}_4bet_allin"

    return None


def process_opponent_positional(db, player_name: str, limit: int = 1000) -> Dict:
    """
    Process opponent using positional frequency analysis (no hole cards needed).

    Tracks how often they take each action in each scenario.
    """
    print(f"\n{'=' * 80}")
    print(f"Processing (Positional): {player_name}")
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

    # Track scenario counts
    scenario_actions = {}  # scenario_name -> {action_taken -> count}

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

            # Track this scenario/action combination
            if scenario_name not in scenario_actions:
                scenario_actions[scenario_name] = {}

            if action_type not in scenario_actions[scenario_name]:
                scenario_actions[scenario_name][action_type] = 0

            scenario_actions[scenario_name][action_type] += 1

    db.commit()
    print(f"✅ Analyzed {len(scenario_actions)} scenarios")

    # Now update player_gto_stats with positional frequencies
    stats_updated = 0

    for scenario_name, actions in scenario_actions.items():
        # Check if scenario exists in database
        scenario_query = text("""
            SELECT scenario_id FROM gto_scenarios
            WHERE scenario_name = :scenario_name
        """)
        scenario_result = db.execute(scenario_query, {
            'scenario_name': scenario_name
        }).fetchone()

        if not scenario_result:
            continue

        scenario_id = scenario_result[0]

        # Calculate player frequency (how often they take this action)
        total_hands = sum(actions.values())

        # For each action type, calculate frequency
        for action_type, count in actions.items():
            player_freq = count / total_hands if total_hands > 0 else 0.0

            # Get average GTO frequency for this scenario
            # (aggregate across all hands since we don't have specific hole cards)
            gto_query = text("""
                SELECT AVG(frequency) as avg_freq
                FROM gto_frequencies gf
                JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
                WHERE gs.scenario_name = :scenario_name
            """)

            gto_result = db.execute(gto_query, {
                'scenario_name': scenario_name
            }).fetchone()

            avg_gto_freq = float(gto_result[0]) if gto_result and gto_result[0] else None

            if avg_gto_freq is None:
                continue

            freq_diff = player_freq - avg_gto_freq

            # Estimate EV loss (simplified)
            ev_loss_per_hand = abs(freq_diff) * 0.5  # Rough estimate
            total_ev_loss = ev_loss_per_hand * total_hands

            # Classify leak
            leak_type = None
            leak_severity = None

            if total_hands >= 5:
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
                'total_hands': total_hands,
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

    return {'player': player_name, 'scenarios': len(scenario_actions)}


def main():
    """Main execution."""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("POPULATING POSITIONAL GTO ANALYSIS FOR ALL PLAYERS")
        print("=" * 80)
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

        # Find heroes
        heroes = find_hero_players(db)

        print(f"Found {len(player_list)} total players")
        print(f"Hero players (with hole cards): {', '.join(sorted(heroes)) if heroes else 'None'}")
        print(f"Opponent players: {len(player_list) - len(heroes)}")
        print()
        print("All players will be analyzed using positional frequencies.")
        print("(Hero players could also be analyzed hand-specifically in the future)")
        print()

        results = []
        for player in player_list:
            result = process_opponent_positional(db, player, limit=1000)
            results.append(result)

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        for r in results:
            is_hero = " (HERO)" if r['player'] in heroes else ""
            print(f"  {r['player']:20s}{is_hero:8s} - {r['scenarios']:3d} scenarios analyzed")

        print()
        print("✅ ALL PLAYERS PROCESSED")
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
