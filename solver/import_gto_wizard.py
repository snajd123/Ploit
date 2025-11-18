"""
Import GTO ranges and frequencies from GTO Wizard via CSV template.

Usage:
1. Fill out gto_wizard_import_template.csv with ranges and frequencies
2. Run: python3 import_gto_wizard.py
3. Script generates SQL to import to database
"""

import csv
import sys
from pathlib import Path


def parse_range(range_text: str) -> dict:
    """Parse pasted GTO Wizard range text into structured format"""
    if not range_text or range_text == "PASTE_RANGE_HERE":
        return None

    # Clean up the range text
    range_text = range_text.strip().replace('\n', ',').replace('  ', ' ')

    return {
        "range_string": range_text,
        "hand_count": len([h for h in range_text.split(',') if h.strip()])
    }


def generate_sql_insert(row: dict) -> str:
    """Generate SQL INSERT for a single scenario"""

    # Parse range if provided
    range_data = parse_range(row['gto_range'])
    range_string = range_data['range_string'] if range_data else None

    # Format values for SQL
    def fmt(val):
        if val == '' or val is None:
            return 'NULL'
        try:
            float(val)
            return val
        except:
            return f"'{val}'"

    sql = f"""
INSERT INTO gto_solutions (
    scenario_name, scenario_type, board,
    position_oop, position_ip,
    pot_size, stack_depth,
    gto_bet_frequency, gto_check_frequency,
    gto_fold_frequency, gto_call_frequency, gto_raise_frequency,
    description, solver_version
) VALUES (
    '{row['scenario_name']}',
    '{row['scenario_type']}',
    {fmt(row['board'])},
    {fmt(row['position_oop'])},
    {fmt(row['position_ip'])},
    {fmt(row['pot_size'])},
    {fmt(row['stack_depth'])},
    {fmt(row['gto_bet_frequency'])},
    {fmt(row['gto_check_frequency'])},
    {fmt(row['gto_fold_frequency'])},
    {fmt(row['gto_call_frequency'])},
    {fmt(row['gto_raise_frequency'])},
    '{row['description']}',
    'GTO-Wizard'
)
ON CONFLICT (scenario_name) DO UPDATE SET
    gto_bet_frequency = EXCLUDED.gto_bet_frequency,
    gto_check_frequency = EXCLUDED.gto_check_frequency,
    gto_fold_frequency = EXCLUDED.gto_fold_frequency,
    gto_call_frequency = EXCLUDED.gto_call_frequency,
    gto_raise_frequency = EXCLUDED.gto_raise_frequency;
"""

    return sql


def main():
    csv_file = Path(__file__).parent / "gto_wizard_import_template.csv"
    output_file = Path(__file__).parent / "gto_wizard_import.sql"

    if not csv_file.exists():
        print(f"Error: {csv_file} not found")
        return 1

    print("=" * 60)
    print("GTO Wizard Import - CSV to SQL")
    print("=" * 60)

    imported = 0
    skipped = 0
    sql_statements = []

    sql_statements.append("-- GTO Wizard Import")
    sql_statements.append("-- Generated from gto_wizard_import_template.csv\n")

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip if range not filled in
            if row['gto_range'] == 'PASTE_RANGE_HERE' or not row['gto_range']:
                skipped += 1
                print(f"⊘ {row['scenario_name']:40s} - No range provided")
                continue

            sql = generate_sql_insert(row)
            sql_statements.append(sql)
            imported += 1
            print(f"✓ {row['scenario_name']:40s} - Ready to import")

    # Write SQL file
    with open(output_file, 'w') as f:
        f.write('\n'.join(sql_statements))

    print("\n" + "=" * 60)
    print(f"Import Summary:")
    print(f"  Imported: {imported}")
    print(f"  Skipped:  {skipped}")
    print(f"\nSQL file generated: {output_file}")
    print(f"\nTo import to database:")
    print(f'  psql "YOUR_DATABASE_URL" -f {output_file}')
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
