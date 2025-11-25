#!/usr/bin/env python3
"""
Import GTOWizard preflop ranges from text file into database.

Parses gtowizard_preflop_ranges.txt and populates:
- gto_scenarios: Scenario metadata
- gto_frequencies: Hand frequencies for each scenario
"""

import os
import re
import decimal
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://postgres.lyvnuiuatuggtirdxiht:SourBeer2027@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def combo_to_hand_type(combo: str) -> str:
    """
    Convert a specific combo (e.g., 'AhKd') to hand type (e.g., 'AKo').

    Args:
        combo: 4-char combo like 'AhKd', '2c2d', 'JsTs'

    Returns:
        Hand type like 'AKo', '22', 'JTs'
    """
    if len(combo) != 4:
        return combo

    rank1, suit1, rank2, suit2 = combo[0], combo[1], combo[2], combo[3]

    # Rank order for sorting (A high)
    rank_order = '23456789TJQKA'

    # Ensure higher rank comes first
    if rank_order.index(rank1) < rank_order.index(rank2):
        rank1, rank2 = rank2, rank1
        suit1, suit2 = suit2, suit1

    # Pair
    if rank1 == rank2:
        return f"{rank1}{rank2}"

    # Suited vs offsuit
    if suit1 == suit2:
        return f"{rank1}{rank2}s"
    else:
        return f"{rank1}{rank2}o"


def parse_scenario_name(scenario_name: str) -> Dict:
    """
    Parse scenario name to extract metadata.

    Examples:
        'UTG_open' -> position='UTG', action='open', category='opening'
        'BB_vs_BTN_call' -> position='BB', opponent='BTN', action='call', category='defense'
        'UTG_vs_CO_3bet_fold' -> position='UTG', opponent='CO', action='fold', category='facing_3bet'
    """
    parts = scenario_name.split('_')

    result = {
        'position': parts[0],
        'action': parts[-1],
        'opponent_position': None,
        'category': 'unknown',
        'street': 'preflop'
    }

    # Opening ranges
    if scenario_name.endswith('_open'):
        result['category'] = 'opening'
        result['action'] = 'open'

    # Defense vs open (e.g., BB_vs_UTG_call, BB_vs_UTG_fold, BB_vs_UTG_3bet)
    # Note: BB_vs_UTG_3bet means BB is 3-betting vs UTG open (defense category)
    elif '_vs_' in scenario_name and '4bet' not in scenario_name and '_3bet_' not in scenario_name:
        result['category'] = 'defense'
        # Find opponent position (after 'vs_')
        vs_idx = parts.index('vs')
        result['opponent_position'] = parts[vs_idx + 1]

    # Facing 3-bet (e.g., UTG_vs_CO_3bet_fold, UTG_vs_CO_3bet_call, UTG_vs_CO_3bet_4bet)
    # The opener faces a 3-bet and responds with fold/call/4bet
    elif '_3bet_' in scenario_name:
        result['category'] = 'facing_3bet'
        vs_idx = parts.index('vs')
        result['opponent_position'] = parts[vs_idx + 1]

    # Facing 4-bet (e.g., BB_vs_BTN_4bet_call, BB_vs_BTN_4bet_fold, BB_vs_BTN_4bet_allin)
    elif '_4bet_' in scenario_name:
        result['category'] = 'facing_4bet'
        vs_idx = parts.index('vs')
        result['opponent_position'] = parts[vs_idx + 1]

    # Squeeze scenarios (e.g., SB_vs_UTG_BTN_call - 3-way pot where SB faces open from UTG and call from BTN)
    elif len(parts) == 5 and parts[1] == 'vs' and parts[-1] in ['fold', 'call', '3bet']:
        result['category'] = 'squeeze'
        result['opponent_position'] = f"{parts[2]}_{parts[3]}"

    return result


def parse_combo_data(data_line: str) -> List[Tuple[str, Decimal]]:
    """
    Parse a line of combo:frequency data.

    Args:
        data_line: Line like "AhKd: 0.5,AhKc: 0.75,..."

    Returns:
        List of (combo, frequency) tuples
    """
    combos = []

    # Handle "0 FREQUENCY" marker (GTO says never take this action)
    if data_line.strip() == '0 FREQUENCY':
        return combos

    # Skip comment lines or empty
    if data_line.strip().startswith('#') or not data_line.strip():
        return combos

    # Parse comma-separated combo:freq pairs
    pairs = data_line.strip().split(',')

    for pair in pairs:
        pair = pair.strip()
        if ':' not in pair:
            continue

        try:
            parts = pair.split(':')
            if len(parts) != 2:
                continue

            combo = parts[0].strip()
            freq_str = parts[1].strip()

            # Skip empty frequencies
            if not freq_str:
                continue

            # Parse frequency as float first, then convert to Decimal
            freq_float = float(freq_str)
            # Clamp to valid range [0.0, 1.0] to handle floating point precision issues
            freq_float = max(0.0, min(1.0, freq_float))
            freq = Decimal(str(round(freq_float, 8)))

            # Validate combo format (4 chars)
            if len(combo) == 4:
                combos.append((combo, freq))
        except (ValueError, IndexError, decimal.InvalidOperation) as e:
            # Skip malformed entries
            continue

    return combos


def parse_gtowizard_file(filepath: str) -> List[Dict]:
    """
    Parse the GTOWizard preflop ranges file.

    Returns:
        List of scenario dictionaries with 'name', 'metadata', and 'combos'
    """
    scenarios = []

    with open(filepath, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for [DONE] markers
        if line.startswith('[DONE]'):
            scenario_name = line.replace('[DONE]', '').strip()

            # Skip comment line
            i += 1
            while i < len(lines) and lines[i].strip().startswith('#'):
                i += 1

            # Parse combo data (next non-empty, non-comment line)
            combo_data = []
            if i < len(lines):
                data_line = lines[i].strip()
                if data_line and not data_line.startswith('#') and not data_line.startswith('['):
                    combo_data = parse_combo_data(data_line)

            # Parse scenario metadata
            metadata = parse_scenario_name(scenario_name)

            scenarios.append({
                'name': scenario_name,
                'metadata': metadata,
                'combos': combo_data
            })

        i += 1

    return scenarios


def create_description(scenario_name: str, metadata: Dict) -> str:
    """Generate human-readable description for scenario."""
    pos = metadata['position']
    action = metadata['action']
    opp = metadata.get('opponent_position', '')
    cat = metadata['category']

    if cat == 'opening':
        return f"{pos} opens (RFI)"
    elif cat == 'defense':
        return f"{pos} vs {opp} open: {action}"
    elif cat == 'facing_3bet':
        return f"{pos} opened, faces {opp} 3-bet: {action}"
    elif cat == 'facing_4bet':
        return f"{pos} 3-bet, faces {opp} 4-bet: {action}"
    elif cat == 'squeeze':
        return f"{pos} squeeze vs {opp}: {action}"
    else:
        return scenario_name


def import_scenarios(db, scenarios: List[Dict], clear_existing: bool = False) -> Dict:
    """
    Import scenarios into database.

    Args:
        db: Database session
        scenarios: List of parsed scenarios
        clear_existing: If True, delete existing data first

    Returns:
        Statistics dictionary
    """
    stats = {
        'scenarios_created': 0,
        'scenarios_updated': 0,
        'frequencies_inserted': 0,
        'zero_frequency_scenarios': 0
    }

    if clear_existing:
        print("Clearing existing preflop GTO data...")
        db.execute(text("""
            DELETE FROM gto_frequencies
            WHERE scenario_id IN (
                SELECT scenario_id FROM gto_scenarios WHERE street = 'preflop'
            )
        """))
        db.execute(text("DELETE FROM gto_scenarios WHERE street = 'preflop'"))
        db.commit()
        print("Cleared existing data")

    for scenario in scenarios:
        name = scenario['name']
        metadata = scenario['metadata']
        combos = scenario['combos']

        description = create_description(name, metadata)

        # Check if scenario exists
        existing = db.execute(text("""
            SELECT scenario_id FROM gto_scenarios WHERE scenario_name = :name
        """), {'name': name}).fetchone()

        if existing:
            scenario_id = existing[0]
            # Update existing
            db.execute(text("""
                UPDATE gto_scenarios SET
                    category = :category,
                    position = :position,
                    action = :action,
                    opponent_position = :opponent_position,
                    description = :description,
                    updated_at = CURRENT_TIMESTAMP
                WHERE scenario_id = :scenario_id
            """), {
                'scenario_id': scenario_id,
                'category': metadata['category'],
                'position': metadata['position'],
                'action': metadata['action'],
                'opponent_position': metadata.get('opponent_position'),
                'description': description
            })
            stats['scenarios_updated'] += 1

            # Delete existing frequencies for this scenario
            db.execute(text("""
                DELETE FROM gto_frequencies WHERE scenario_id = :scenario_id
            """), {'scenario_id': scenario_id})
        else:
            # Insert new scenario
            result = db.execute(text("""
                INSERT INTO gto_scenarios
                (scenario_name, street, category, position, action, opponent_position,
                 data_source, description)
                VALUES
                (:name, :street, :category, :position, :action, :opponent_position,
                 'gtowizard', :description)
                RETURNING scenario_id
            """), {
                'name': name,
                'street': metadata['street'],
                'category': metadata['category'],
                'position': metadata['position'],
                'action': metadata['action'],
                'opponent_position': metadata.get('opponent_position'),
                'description': description
            })
            scenario_id = result.fetchone()[0]
            stats['scenarios_created'] += 1

        # Insert frequencies
        if not combos:
            stats['zero_frequency_scenarios'] += 1
            print(f"  {name}: 0 FREQUENCY (GTO never takes this action)")
        else:
            # Batch insert frequencies
            freq_values = []
            for combo, freq in combos:
                hand_type = combo_to_hand_type(combo)
                freq_values.append({
                    'scenario_id': scenario_id,
                    'hand': combo,  # Store full combo for precision
                    'position': metadata['position'],
                    'frequency': freq
                })

            if freq_values:
                # Dedupe freq_values by (scenario_id, hand, position) - keep last occurrence
                seen = {}
                for fv in freq_values:
                    key = (fv['scenario_id'], fv['hand'], fv['position'])
                    seen[key] = fv
                deduped_values = list(seen.values())

                # Batch insert with executemany
                db.execute(text("""
                    INSERT INTO gto_frequencies (scenario_id, hand, position, frequency)
                    VALUES (:scenario_id, :hand, :position, :frequency)
                """), deduped_values)
                stats['frequencies_inserted'] += len(deduped_values)

        db.commit()

    return stats


def main():
    """Main execution."""
    print("=" * 80)
    print("GTOWizard Preflop Ranges Import")
    print("=" * 80)
    print()

    # Path to ranges file
    filepath = '/root/Documents/Ploit/gtowizard_preflop_ranges.txt'

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return

    print(f"Parsing: {filepath}")
    scenarios = parse_gtowizard_file(filepath)
    print(f"Found {len(scenarios)} scenarios")
    print()

    # Show breakdown by category
    categories = {}
    for s in scenarios:
        cat = s['metadata']['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("Scenario breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print()

    # Connect to database and import
    db = SessionLocal()

    try:
        print("Importing to database...")
        stats = import_scenarios(db, scenarios, clear_existing=True)

        print()
        print("=" * 80)
        print("IMPORT COMPLETE")
        print("=" * 80)
        print(f"  Scenarios created:  {stats['scenarios_created']}")
        print(f"  Scenarios updated:  {stats['scenarios_updated']}")
        print(f"  Frequencies inserted: {stats['frequencies_inserted']}")
        print(f"  Zero-frequency scenarios: {stats['zero_frequency_scenarios']}")
        print()

        # Verify
        count = db.execute(text("""
            SELECT COUNT(*) FROM gto_scenarios WHERE street = 'preflop'
        """)).fetchone()[0]
        print(f"Total preflop scenarios in database: {count}")

        freq_count = db.execute(text("""
            SELECT COUNT(*) FROM gto_frequencies gf
            JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
            WHERE gs.street = 'preflop'
        """)).fetchone()[0]
        print(f"Total preflop frequencies in database: {freq_count}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
