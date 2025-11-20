#!/usr/bin/env python3
"""
Import GTOWizard preflop ranges to new GTO database.
"""
import re
import psycopg2
from psycopg2.extras import execute_batch
from typing import Dict, Tuple, List
from collections import defaultdict

# Database connection string
DATABASE_URL = "postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"


def parse_combo_range(range_str: str) -> Dict[str, float]:
    """Parse GTOWizard combo range string into dict."""
    combos = {}
    if not range_str.strip():
        return combos

    for item in range_str.split(','):
        if ':' not in item:
            continue
        try:
            combo, freq = item.split(':')
            combos[combo.strip()] = float(freq.strip())
        except:
            continue

    return combos


def combo_to_hand(combo: str) -> str:
    """Convert combo to hand type."""
    if len(combo) != 4:
        return None

    rank1, suit1, rank2, suit2 = combo[0], combo[1], combo[2], combo[3]
    rank_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
                  '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

    r1 = rank_order.get(rank1, 0)
    r2 = rank_order.get(rank2, 0)

    if r1 > r2:
        high, low = rank1, rank2
        high_suit, low_suit = suit1, suit2
    else:
        high, low = rank2, rank1
        high_suit, low_suit = suit2, suit1

    is_pair = (high == low)
    is_suited = (high_suit == low_suit)

    if is_pair:
        return f"{high}{low}"
    elif is_suited:
        return f"{high}{low}s"
    else:
        return f"{high}{low}o"


def parse_gtowizard_file(filepath: str) -> Dict[str, Dict[str, float]]:
    """Parse gtowizard_ranges.txt file."""
    with open(filepath, 'r') as f:
        content = f.read()

    pattern = r'\[DONE\]\s+(\w+)\s*\n#\s*GTOWizard:\s*(.*?)\n(.*?)\n\n'
    ranges = {}

    for match in re.finditer(pattern, content, re.DOTALL):
        scenario_name = match.group(1)
        range_data = match.group(3).strip()
        combos = parse_combo_range(range_data)

        if combos:
            ranges[scenario_name] = combos

    return ranges


def categorize_scenario(scenario_name: str) -> Tuple[str, str, str, str]:
    """
    Extract metadata from scenario name.
    Returns: (category, position, action, opponent)
    """
    parts = scenario_name.split('_')

    # Opening ranges
    if scenario_name.endswith('_open'):
        return 'opening', parts[0], 'open', None

    # Defense and facing bets
    if 'vs' in scenario_name:
        position = parts[0]
        opponent = parts[2]
        action = parts[-1]

        if '3bet' in scenario_name and len(parts) > 3:
            category = 'facing_3bet'
        elif '4bet' in scenario_name and len(parts) > 3:
            category = 'facing_4bet'
        elif action in ['fold', 'call', '3bet']:
            if 'BTN' in parts and len(parts) > 3:  # Multiway
                category = 'multiway'
            else:
                category = 'defense'
        else:
            category = 'multiway'

        return category, position, action, opponent

    return 'unknown', 'unknown', 'unknown', None


def generate_all_combos() -> List[Tuple[str, str, bool, bool]]:
    """Generate all 1326 possible combos with metadata."""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    suits = ['c', 'd', 'h', 's']

    combos = []
    for i, rank1 in enumerate(ranks):
        for suit1 in suits:
            for j, rank2 in enumerate(ranks):
                if j > i:  # Avoid duplicates
                    continue
                for suit2 in suits:
                    if rank1 == rank2 and suit1 >= suit2:
                        continue  # Avoid duplicate pairs

                    combo = f"{rank1}{suit1}{rank2}{suit2}"
                    hand = combo_to_hand(combo)

                    is_pair = (rank1 == rank2)
                    is_suited = (suit1 == suit2)

                    if hand:
                        combos.append((combo, hand, rank1, rank2, suit1, suit2, is_pair, is_suited))

    return combos


def import_preflop_ranges():
    """Import all 147 preflop scenarios."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("=" * 80)
        print("IMPORTING GTOWIZARD RANGES TO DATABASE")
        print("=" * 80)
        print()

        # Step 1: Populate hand_types table
        print("Step 1: Populating hand_types table...")
        all_combos = generate_all_combos()

        execute_batch(cur, """
            INSERT INTO hand_types (combo, hand, rank1, rank2, suit1, suit2, is_pair, is_suited)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (combo) DO NOTHING
        """, all_combos, page_size=1000)

        print(f"  ✅ Inserted {len(all_combos)} combos\n")

        # Step 2: Parse ranges file
        print("Step 2: Parsing GTOWizard ranges file...")
        ranges = parse_gtowizard_file('/root/Documents/Ploit/solver/gtowizard_ranges.txt')
        print(f"  ✅ Found {len(ranges)} scenarios\n")

        # Step 3: Insert scenarios
        print("Step 3: Inserting scenarios...")
        scenario_map = {}

        for scenario_name in ranges.keys():
            category, position, action, opponent = categorize_scenario(scenario_name)

            cur.execute("""
                INSERT INTO gto_scenarios (scenario_name, street, category, position, action, opponent_position, board, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (scenario_name) DO UPDATE SET
                    category = EXCLUDED.category,
                    position = EXCLUDED.position,
                    action = EXCLUDED.action,
                    opponent_position = EXCLUDED.opponent_position,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING scenario_id
            """, (scenario_name, 'preflop', category, position, action, opponent, 'PREFLOP', 'gtowizard'))

            scenario_map[scenario_name] = cur.fetchone()[0]

        conn.commit()
        print(f"  ✅ Inserted {len(scenario_map)} scenarios\n")

        # Step 4: Aggregate combos to hands and insert frequencies
        print("Step 4: Inserting GTO frequencies...")

        total_frequencies = 0
        for scenario_name, combos in ranges.items():
            scenario_id = scenario_map[scenario_name]

            # Get position from scenario metadata
            category, position, action, opponent = categorize_scenario(scenario_name)

            # Aggregate combos to hands
            hand_frequencies = defaultdict(list)
            for combo, freq in combos.items():
                hand = combo_to_hand(combo)
                if hand:
                    hand_frequencies[hand].append(freq)

            # Calculate average frequency per hand and insert
            frequency_data = []
            for hand, freqs in hand_frequencies.items():
                avg_freq = sum(freqs) / len(freqs)
                # Clamp to [0, 1] to handle floating point precision issues
                avg_freq = max(0.0, min(1.0, avg_freq))
                frequency_data.append((scenario_id, hand, position, avg_freq))

            execute_batch(cur, """
                INSERT INTO gto_frequencies (scenario_id, hand, position, frequency)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (scenario_id, hand, position) DO UPDATE SET
                    frequency = EXCLUDED.frequency
            """, frequency_data, page_size=1000)

            total_frequencies += len(frequency_data)
            print(f"  ✅ {scenario_name}: {len(frequency_data)} hands")

        conn.commit()
        print(f"\n  Total frequencies inserted: {total_frequencies}\n")

        # Verification
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)

        cur.execute("SELECT COUNT(*) FROM gto_scenarios")
        scenario_count = cur.fetchone()[0]
        print(f"✅ Scenarios in database: {scenario_count}")

        cur.execute("SELECT COUNT(*) FROM gto_frequencies")
        frequency_count = cur.fetchone()[0]
        print(f"✅ Total frequencies in database: {frequency_count}")

        cur.execute("SELECT COUNT(DISTINCT hand) FROM hand_types")
        hand_count = cur.fetchone()[0]
        print(f"✅ Unique hand types: {hand_count}")

        # Sample query
        print("\nSample query: Get GTO frequency for BB calling vs UTG with AKo")
        cur.execute("""
            SELECT gf.frequency
            FROM gto_frequencies gf
            JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
            WHERE gs.scenario_name = 'BB_vs_UTG_call' AND gf.hand = 'AKo' AND gf.position = 'BB'
        """)
        result = cur.fetchone()
        if result:
            print(f"  Result: {result[0]:.4f} ({result[0]*100:.2f}%)")
        else:
            print("  Result: Not found (0%)")

        print("\n" + "=" * 80)
        print("✅ IMPORT COMPLETE!")
        print("=" * 80)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    import_preflop_ranges()
