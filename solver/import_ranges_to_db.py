#!/usr/bin/env python3
"""
Import GTOWizard preflop ranges to PostgreSQL database
"""

import re
import psycopg2
from psycopg2.extras import execute_batch
from typing import Dict, List, Tuple

# Database connection string
DATABASE_URL = "postgresql://postgres:password@localhost:5432/ploit_gto"

def parse_combo_range(range_str: str) -> Dict[str, float]:
    """Parse GTOWizard combo range string into dict"""
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


def combo_to_hand(combo: str) -> Tuple[str, bool, bool]:
    """
    Convert combo to hand type
    Returns: (hand, is_pair, is_suited)
    """
    if len(combo) != 4:
        return None, None, None

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
        hand = f"{high}{low}"
    elif is_suited:
        hand = f"{high}{low}s"
    else:
        hand = f"{high}{low}o"

    return hand, is_pair, is_suited


def extract_ranges_from_file(filename: str) -> Dict[str, Dict[str, float]]:
    """Extract all [DONE] ranges from GTOWizard file"""
    with open(filename, 'r') as f:
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
    Extract metadata from scenario name
    Returns: (category, position, action, opponent_position)
    """
    parts = scenario_name.split('_')

    # Opening ranges
    if scenario_name.endswith('_open'):
        return 'opening', parts[0], 'open', None

    # Defense scenarios
    if 'vs' in scenario_name:
        position = parts[0]
        opponent = parts[2]

        # Facing 3bets
        if '3bet' in scenario_name and len(parts) > 3:
            action = parts[-1]
            category = 'facing_3bet'
        # Facing 4bets
        elif '4bet' in scenario_name and len(parts) > 3:
            action = parts[-1]
            category = 'facing_4bet'
        # Regular defense
        else:
            action = parts[-1]
            if 'BTN' in opponent and len(parts) > 3:  # Multiway
                category = 'multiway'
            elif position in ['CO', 'BTN'] and action in ['fold', '3bet']:
                category = 'cold_call'
            else:
                category = 'defense'

        return category, position, action, opponent

    return 'unknown', 'unknown', 'unknown', None


def generate_all_combos() -> List[Tuple[str, str, bool, bool]]:
    """Generate all 1326 possible combos with metadata"""
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
                    hand, is_pair, is_suited = combo_to_hand(combo)

                    combos.append((combo, hand, is_pair, is_suited))

    return combos


def import_to_database(ranges: Dict[str, Dict[str, float]], db_url: str):
    """Import ranges to PostgreSQL database"""

    conn = psycopg2.connect(db_url)
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
        """, [(c[0], c[1], c[0][0], c[0][2], c[0][1], c[0][3], c[2], c[3]) for c in all_combos])

        print(f"  ✅ Inserted {len(all_combos)} combos")

        # Step 2: Insert scenarios
        print("\nStep 2: Inserting scenarios...")
        scenario_ids = {}

        for scenario_name in ranges.keys():
            category, position, action, opponent = categorize_scenario(scenario_name)

            cur.execute("""
                INSERT INTO scenarios (scenario_name, category, position, action, opponent_position)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (scenario_name) DO UPDATE SET
                    category = EXCLUDED.category,
                    position = EXCLUDED.position,
                    action = EXCLUDED.action,
                    opponent_position = EXCLUDED.opponent_position,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (scenario_name, category, position, action, opponent))

            scenario_ids[scenario_name] = cur.fetchone()[0]

        print(f"  ✅ Inserted {len(scenario_ids)} scenarios")

        # Step 3: Insert combo frequencies
        print("\nStep 3: Inserting combo frequencies...")

        total_combos = 0
        for scenario_name, combos in ranges.items():
            scenario_id = scenario_ids[scenario_name]

            combo_data = [(scenario_id, combo, freq) for combo, freq in combos.items()]

            execute_batch(cur, """
                INSERT INTO preflop_combos (scenario_id, combo, frequency)
                VALUES (%s, %s, %s)
                ON CONFLICT (scenario_id, combo) DO UPDATE SET
                    frequency = EXCLUDED.frequency
            """, combo_data, page_size=1000)

            total_combos += len(combo_data)
            print(f"  ✅ {scenario_name}: {len(combo_data)} combos")

        print(f"\n  Total combos inserted: {total_combos}")

        # Commit transaction
        conn.commit()

        # Step 4: Verify import
        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)

        cur.execute("SELECT COUNT(*) FROM scenarios")
        scenario_count = cur.fetchone()[0]
        print(f"✅ Scenarios in database: {scenario_count}")

        cur.execute("SELECT COUNT(*) FROM preflop_combos")
        combo_count = cur.fetchone()[0]
        print(f"✅ Total combos in database: {combo_count}")

        cur.execute("SELECT COUNT(DISTINCT hand) FROM hand_types")
        hand_count = cur.fetchone()[0]
        print(f"✅ Unique hand types: {hand_count}")

        # Sample query
        print("\nSample query: Get GTO frequency for BB calling vs UTG with AKo")
        cur.execute("SELECT get_gto_frequency('BB_vs_UTG_call', 'AKo')")
        result = cur.fetchone()[0]
        if result:
            print(f"  Result: {result:.4f} ({result*100:.2f}%)")
        else:
            print("  Result: Not found (0%)")

        print("\n" + "=" * 80)
        print("✅ IMPORT COMPLETE!")
        print("=" * 80)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        raise

    finally:
        cur.close()
        conn.close()


def main():
    """Main import process"""
    print("Loading GTOWizard ranges from file...")
    ranges = extract_ranges_from_file('/root/Documents/Ploit/solver/gtowizard_ranges.txt')
    print(f"Found {len(ranges)} scenarios\n")

    print("Connecting to database...")
    print(f"Database URL: {DATABASE_URL}\n")

    import_to_database(ranges, DATABASE_URL)


if __name__ == '__main__':
    main()
