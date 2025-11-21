#!/usr/bin/env python3
"""
CORRECT: GTO analysis tracking opportunities vs actions.

Key insight: GTO scenario names like "UTG_open" refer to the ACTION, not the opportunity.
We need to track:
- Opportunity: "Player is in UTG, first to act"
- Action taken: Did they open (raise) or fold?
- Frequency: opens / opportunities

Then compare to GTO "UTG_open" frequency (which is the GTO opening frequency from UTG).
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional, List, Dict, Tuple
from collections import defaultdict

DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_action_context(preflop_actions: List[Dict], player_action_index: int) -> Dict:
    """Analyze the action context before player's decision."""
    ctx = {
        'is_first_to_act': True,
        'facing_raise': False,
        'raiser_position': None,
        'num_raises': 0,
        'facing_3bet': False,
        'facing_4bet': False,
    }

    for prior_action in preflop_actions[:player_action_index]:
        prior_type = prior_action['action_type']

        # Skip blind posts - these aren't voluntary actions
        if prior_type in ['post_sb', 'post_bb']:
            continue

        if prior_type in ['raise', 'bet']:
            ctx['num_raises'] += 1
            if ctx['num_raises'] == 1:
                ctx['facing_raise'] = True
                ctx['raiser_position'] = prior_action['position']
            elif ctx['num_raises'] == 2:
                ctx['facing_3bet'] = True
            elif ctx['num_raises'] == 3:
                ctx['facing_4bet'] = True

        # Only voluntary actions count
        if prior_type not in ['fold', 'check']:
            ctx['is_first_to_act'] = False

    return ctx


def get_player_scenarios_and_action(position: str, action_type: str, context: Dict) -> List[Tuple[str, bool]]:
    """
    Map player's situation to GTO scenarios and whether they took the scenario's action.

    Returns: [(scenario_name, took_action), ...]

    Example: Player in UTG, first to act, folds
    - Returns: [("UTG_open", False)] - they were in opening scenario but didn't open

    Example: Player in BB, facing UTG open, calls
    - Returns: [("BB_vs_UTG_call", True), ("BB_vs_UTG_fold", False), ("BB_vs_UTG_3bet", False)]
      - They took the call action, didn't fold, didn't 3bet
    """
    scenarios = []

    # OPENING SCENARIOS
    if context['is_first_to_act'] and position in ['UTG', 'MP', 'CO', 'BTN', 'SB']:
        # Player has opportunity to open
        took_action = (action_type == 'raise')
        scenarios.append((f"{position}_open", took_action))

    # DEFENSE SCENARIOS (facing open)
    elif context['facing_raise'] and not context['facing_3bet']:
        raiser = context['raiser_position']
        if raiser:
            # Player can fold, call, or 3bet
            scenarios.append((f"{position}_vs_{raiser}_fold", action_type == 'fold'))
            scenarios.append((f"{position}_vs_{raiser}_call", action_type == 'call'))
            scenarios.append((f"{position}_vs_{raiser}_3bet", action_type == 'raise'))

    # FACING 3BET
    elif context['facing_3bet'] and not context['facing_4bet']:
        raiser = context['raiser_position']
        if raiser:
            # Player can fold, call, or 4bet
            scenarios.append((f"{position}_vs_{raiser}_3bet_fold", action_type == 'fold'))
            scenarios.append((f"{position}_vs_{raiser}_3bet_call", action_type == 'call'))
            scenarios.append((f"{position}_vs_{raiser}_3bet_4bet", action_type in ['raise', 'allin']))

    # FACING 4BET
    elif context['facing_4bet']:
        raiser = context['raiser_position']
        if raiser:
            # Player can fold, call, or 5bet
            scenarios.append((f"{position}_vs_{raiser}_4bet_fold", action_type == 'fold'))
            scenarios.append((f"{position}_vs_{raiser}_4bet_call", action_type == 'call'))
            scenarios.append((f"{position}_vs_{raiser}_4bet_allin", action_type in ['raise', 'allin']))

    return scenarios


def process_player_correct(db, player_name: str, limit: int = 1000) -> Dict:
    """Process player with correct opportunity tracking."""
    print(f"\n{'=' * 80}")
    print(f"Processing: {player_name}")
    print(f"{'=' * 80}\n")

    # Get all hands
    query = text("""
        SELECT DISTINCT ha.hand_id
        FROM hand_actions ha
        WHERE ha.player_name = :player_name
          AND ha.street = 'preflop'
        ORDER BY ha.hand_id DESC
        LIMIT :limit
    """)

    hand_ids = db.execute(query, {'player_name': player_name, 'limit': limit}).fetchall()
    print(f"Found {len(hand_ids)} hands")

    if not hand_ids:
        print(f"⚠️  No hands found, skipping...")
        return {'player': player_name, 'scenarios': 0}

    # Track: scenario_name -> {'opportunities': count, 'actions_taken': count}
    scenario_tracking = defaultdict(lambda: {'opportunities': 0, 'actions_taken': 0})

    for hand_row in hand_ids:
        hand_id = hand_row[0]

        # Get all preflop actions
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

            # Skip blind posts - not strategic decisions
            if action_type in ['post_sb', 'post_bb']:
                continue

            # Get action context
            context = get_action_context(all_actions_list, idx)

            # Get scenarios and whether player took the action
            scenarios = get_player_scenarios_and_action(position, action_type, context)

            for scenario_name, took_action in scenarios:
                scenario_tracking[scenario_name]['opportunities'] += 1
                if took_action:
                    scenario_tracking[scenario_name]['actions_taken'] += 1

    print(f"✅ Tracked {len(scenario_tracking)} scenarios")

    # Calculate frequencies and update database
    stats_updated = 0

    for scenario_name, tracking in scenario_tracking.items():
        opportunities = tracking['opportunities']
        actions_taken = tracking['actions_taken']

        if opportunities == 0:
            continue

        # Player frequency = how often they took this action
        player_freq = actions_taken / opportunities

        # Check if scenario exists in database
        scenario_query = text("""
            SELECT scenario_id FROM gto_scenarios
            WHERE scenario_name = :scenario_name
        """)
        scenario_result = db.execute(scenario_query, {'scenario_name': scenario_name}).fetchone()

        if not scenario_result:
            continue

        scenario_id = scenario_result[0]

        # Get GTO frequency (weighted by combo count)
        # Pairs: 6 combos, Suited: 4 combos, Offsuit: 12 combos
        # Total combos: 1326
        gto_query = text("""
            SELECT SUM(
                frequency * CASE
                    WHEN hand ~ '^([AKQJT2-9])\\1$' THEN 6   -- Pairs: 6 combos
                    WHEN hand ~ 's$' THEN 4                   -- Suited: 4 combos
                    ELSE 12                                   -- Offsuit: 12 combos
                END
            ) / 1326.0 as weighted_freq
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
        total_ev_loss = ev_loss_per_hand * opportunities

        # Classify leak - use both absolute and relative deviation
        leak_type = None
        leak_severity = None

        if opportunities >= 5:
            abs_diff = abs(freq_diff)

            # Calculate relative deviation (% change from GTO)
            # Avoid division by zero - if GTO is 0, use absolute thresholds only
            if avg_gto_freq > 0.01:  # GTO frequency is at least 1%
                relative_diff = abs_diff / avg_gto_freq

                # Use relative thresholds for low-frequency actions (like 3-bets)
                # Major: >40% relative deviation OR >30% absolute
                # Moderate: >25% relative deviation OR >15% absolute
                # Minor: >15% relative deviation OR >5% absolute
                if (relative_diff > 0.40) or (abs_diff > 0.30):
                    leak_severity = 'major'
                elif (relative_diff > 0.25) or (abs_diff > 0.15):
                    leak_severity = 'moderate'
                elif (relative_diff > 0.15) or (abs_diff > 0.05):
                    leak_severity = 'minor'
            else:
                # For very low or zero GTO frequencies, use absolute thresholds only
                if abs_diff > 0.30:
                    leak_severity = 'major'
                elif abs_diff > 0.15:
                    leak_severity = 'moderate'
                elif abs_diff > 0.05:
                    leak_severity = 'minor'

            if 'fold' in scenario_name:
                leak_type = 'overfold' if freq_diff > 0 else 'underfold'
            elif 'call' in scenario_name:
                leak_type = 'overcall' if freq_diff > 0 else 'undercall'
            elif '3bet' in scenario_name:
                leak_type = 'over3bet' if freq_diff > 0 else 'under3bet'
            elif '4bet' in scenario_name:
                leak_type = 'over4bet' if freq_diff > 0 else 'under4bet'
            elif 'open' in scenario_name:
                leak_type = 'tight' if freq_diff < 0 else 'loose'

        # Upsert
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
            'total_hands': opportunities,
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
    print(f"✅ Updated {stats_updated} scenarios")

    return {'player': player_name, 'scenarios': stats_updated}


def main():
    """Main execution."""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("CORRECT GTO ANALYSIS - TRACKING OPPORTUNITIES VS ACTIONS")
        print("=" * 80)
        print()

        # Clear old stats
        print("Clearing old incorrect stats...")
        db.execute(text("DELETE FROM player_gto_stats"))
        db.commit()
        print("✅ Cleared")
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

        print(f"Processing {len(player_list)} players...")
        print()

        results = []
        for player in player_list:
            result = process_player_correct(db, player, limit=1000)
            results.append(result)

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        for r in results[:10]:  # Show first 10
            print(f"  {r['player']:20s} - {r['scenarios']:3d} scenarios")
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more players")

        print()
        print(f"✅ COMPLETE - {sum(r['scenarios'] for r in results)} total scenario stats")
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
