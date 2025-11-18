#!/usr/bin/env python3
"""
Import GTO Wizard preflop ranges directly to database.
Format: hand_combo:frequency pairs (e.g., "2d2c: 1,AhKs: 0.5")
"""

import sys
import os
import re
from typing import Dict, List, Tuple
import psycopg2

# Database connection
DB_URL = "postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"

# Scenario definitions (matching our 64 scenarios)
SCENARIOS = [
    # RFI scenarios (7)
    {"id": 1, "name": "RFI_UTG", "type": "preflop", "oop": "BB", "ip": "UTG", "pot": 1.5, "stack": 100},
    {"id": 2, "name": "RFI_MP", "type": "preflop", "oop": "BB", "ip": "MP", "pot": 1.5, "stack": 100},
    {"id": 3, "name": "RFI_CO", "type": "preflop", "oop": "BB", "ip": "CO", "pot": 1.5, "stack": 100},
    {"id": 4, "name": "RFI_BTN", "type": "preflop", "oop": "BB", "ip": "BTN", "pot": 1.5, "stack": 100},
    {"id": 5, "name": "SB_RFI", "type": "preflop", "oop": "BB", "ip": "SB", "pot": 1.5, "stack": 100},
    {"id": 6, "name": "SB_complete", "type": "preflop", "oop": "BB", "ip": "SB", "pot": 1.5, "stack": 100},
    {"id": 7, "name": "BB_vs_SB_limp", "type": "preflop", "oop": "BB", "ip": "SB", "pot": 1.5, "stack": 100},

    # 3bet scenarios (14)
    {"id": 100, "name": "UTG_open_MP_3bet", "type": "preflop", "oop": "UTG", "ip": "MP", "pot": 12.0, "stack": 100},
    {"id": 101, "name": "UTG_open_CO_3bet", "type": "preflop", "oop": "UTG", "ip": "CO", "pot": 12.0, "stack": 100},
    {"id": 102, "name": "UTG_open_BTN_3bet", "type": "preflop", "oop": "UTG", "ip": "BTN", "pot": 12.0, "stack": 100},
    {"id": 103, "name": "UTG_open_SB_3bet", "type": "preflop", "oop": "UTG", "ip": "SB", "pot": 12.0, "stack": 100},
    {"id": 104, "name": "UTG_open_BB_3bet", "type": "preflop", "oop": "UTG", "ip": "BB", "pot": 12.0, "stack": 100},
    {"id": 105, "name": "MP_open_CO_3bet", "type": "preflop", "oop": "MP", "ip": "CO", "pot": 12.0, "stack": 100},
    {"id": 106, "name": "MP_open_BTN_3bet", "type": "preflop", "oop": "MP", "ip": "BTN", "pot": 12.0, "stack": 100},
    {"id": 107, "name": "MP_open_SB_3bet", "type": "preflop", "oop": "MP", "ip": "SB", "pot": 12.0, "stack": 100},
    {"id": 108, "name": "MP_open_BB_3bet", "type": "preflop", "oop": "MP", "ip": "BB", "pot": 12.0, "stack": 100},
    {"id": 109, "name": "CO_open_BTN_3bet", "type": "preflop", "oop": "CO", "ip": "BTN", "pot": 12.0, "stack": 100},
    {"id": 110, "name": "CO_open_SB_3bet", "type": "preflop", "oop": "CO", "ip": "SB", "pot": 12.0, "stack": 100},
    {"id": 111, "name": "CO_open_BB_3bet", "type": "preflop", "oop": "CO", "ip": "BB", "pot": 12.0, "stack": 100},
    {"id": 112, "name": "BTN_open_SB_3bet", "type": "preflop", "oop": "BTN", "ip": "SB", "pot": 12.0, "stack": 100},
    {"id": 113, "name": "BTN_open_BB_3bet", "type": "preflop", "oop": "BTN", "ip": "BB", "pot": 12.0, "stack": 100},
]


def parse_gto_wizard_range(range_text: str) -> Tuple[List[str], int]:
    """
    Parse GTO Wizard range format: "2d2c: 1,AhKs: 0.5,..."
    Returns: (list of hands, total hand combos)
    """
    if not range_text or range_text.strip() == "":
        return [], 0

    hands = []
    total_combos = 0

    # Split by comma
    pairs = range_text.split(',')

    for pair in pairs:
        pair = pair.strip()
        if ':' not in pair:
            continue

        hand, freq_str = pair.split(':', 1)
        hand = hand.strip()

        try:
            freq = float(freq_str.strip())
            if freq > 0:
                hands.append(hand)
                total_combos += 1
        except ValueError:
            continue

    return hands, total_combos


def convert_to_range_string(hands: List[str]) -> str:
    """
    Convert list of hand combos to readable range string.
    For now, just return a summary. Could group into pairs/suited/offsuit.
    """
    if not hands:
        return "Empty range"

    return f"{len(hands)} hand combos"


def import_scenario(scenario_id: int, range_text: str, action_frequencies: Dict[str, float] = None):
    """
    Import a single scenario to database.

    Args:
        scenario_id: Scenario ID (1-113)
        range_text: GTO Wizard range format
        action_frequencies: Dict with keys like 'raise', 'call', 'fold'
    """
    # Find scenario
    scenario = next((s for s in SCENARIOS if s['id'] == scenario_id), None)
    if not scenario:
        print(f"❌ Unknown scenario ID: {scenario_id}")
        return False

    # Parse range
    hands, combo_count = parse_gto_wizard_range(range_text)
    range_summary = convert_to_range_string(hands)

    print(f"📊 {scenario['name']}: {combo_count} combos")

    # Default action frequencies (can be overridden)
    if action_frequencies is None:
        action_frequencies = {}

    raise_freq = action_frequencies.get('raise', None)
    call_freq = action_frequencies.get('call', None)
    fold_freq = action_frequencies.get('fold', None)
    bet_freq = action_frequencies.get('bet', None)
    check_freq = action_frequencies.get('check', None)

    # Insert to database
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        sql = """
        INSERT INTO gto_solutions (
            scenario_name, scenario_type,
            position_oop, position_ip,
            pot_size, stack_depth,
            gto_raise_frequency, gto_call_frequency, gto_fold_frequency,
            gto_bet_frequency, gto_check_frequency,
            description, solver_version
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (scenario_name) DO UPDATE SET
            gto_raise_frequency = EXCLUDED.gto_raise_frequency,
            gto_call_frequency = EXCLUDED.gto_call_frequency,
            gto_fold_frequency = EXCLUDED.gto_fold_frequency,
            gto_bet_frequency = EXCLUDED.gto_bet_frequency,
            gto_check_frequency = EXCLUDED.gto_check_frequency,
            description = EXCLUDED.description
        """

        cur.execute(sql, (
            scenario['name'],
            scenario['type'],
            scenario['oop'],
            scenario['ip'],
            scenario['pot'],
            scenario['stack'],
            raise_freq,
            call_freq,
            fold_freq,
            bet_freq,
            check_freq,
            range_summary,
            'GTO-Wizard'
        ))

        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ {scenario['name']} imported successfully")
        return True

    except Exception as e:
        print(f"❌ Error importing {scenario['name']}: {e}")
        return False


def interactive_import():
    """Interactive mode - prompt user for each scenario"""
    print("=" * 70)
    print("GTO Wizard Preflop Import - Interactive Mode")
    print("=" * 70)
    print()
    print("Instructions:")
    print("1. Go to GTO Wizard and select a scenario")
    print("2. Copy the range data (format: 2d2c: 1,AhKs: 0.5,...)")
    print("3. Paste here when prompted")
    print("4. Enter action frequencies if available")
    print()
    print("Type 'q' to quit, 's' to skip a scenario")
    print()

    imported = 0
    skipped = 0

    for scenario in SCENARIOS:
        print("=" * 70)
        print(f"Scenario: {scenario['name']}")
        print(f"Description: {scenario['oop']} vs {scenario['ip']}")
        print("=" * 70)

        # Get range
        print("\nPaste GTO Wizard range (or 's' to skip, 'q' to quit):")
        range_input = input("> ").strip()

        if range_input.lower() == 'q':
            break

        if range_input.lower() == 's' or range_input == '':
            print(f"⊘ Skipped {scenario['name']}")
            skipped += 1
            continue

        # Get action frequencies (optional)
        print("\nEnter action frequencies (optional, press Enter to skip):")
        print("Format: raise=30,call=50,fold=20")
        freq_input = input("> ").strip()

        action_freqs = {}
        if freq_input:
            for pair in freq_input.split(','):
                if '=' in pair:
                    action, freq = pair.split('=')
                    action_freqs[action.strip()] = float(freq.strip())

        # Import
        if import_scenario(scenario['id'], range_input, action_freqs):
            imported += 1

        print()

    print("=" * 70)
    print(f"Import Complete: {imported} imported, {skipped} skipped")
    print("=" * 70)


def batch_import_from_file(filepath: str):
    """
    Batch import from a file.
    Format: Each line is "scenario_id|range_text|raise=X,call=Y,fold=Z"
    """
    print("=" * 70)
    print("GTO Wizard Preflop Import - Batch Mode")
    print("=" * 70)

    imported = 0
    failed = 0

    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('|')
            if len(parts) < 2:
                print(f"⊘ Line {line_num}: Invalid format")
                failed += 1
                continue

            scenario_id = int(parts[0])
            range_text = parts[1]

            action_freqs = {}
            if len(parts) >= 3:
                for pair in parts[2].split(','):
                    if '=' in pair:
                        action, freq = pair.split('=')
                        action_freqs[action.strip()] = float(freq.strip())

            if import_scenario(scenario_id, range_text, action_freqs):
                imported += 1
            else:
                failed += 1

    print("=" * 70)
    print(f"Batch Import Complete: {imported} imported, {failed} failed")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Batch mode
        batch_import_from_file(sys.argv[1])
    else:
        # Interactive mode
        interactive_import()
