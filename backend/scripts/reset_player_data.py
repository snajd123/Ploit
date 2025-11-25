#!/usr/bin/env python3
"""
Reset Player Data Script

Clears all imported hand history data and calculated player stats,
while preserving GTO reference data (scenarios and frequencies).

Usage:
    python reset_player_data.py [--confirm]

    Without --confirm: Shows what will be deleted (dry run)
    With --confirm: Actually deletes the data
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, text

def get_database_url():
    """Get database URL from environment."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    return url

def show_current_counts(conn):
    """Show current row counts for all tables."""
    tables = [
        ('raw_hands', 'Hand histories'),
        ('hand_actions', 'Hand actions'),
        ('player_preflop_actions', 'Player preflop actions'),
        ('player_scenario_stats', 'Player scenario stats'),
        ('player_stats', 'Player stats'),
        ('upload_sessions', 'Upload sessions'),
        ('gto_scenarios', 'GTO scenarios (PRESERVED)'),
        ('gto_frequencies', 'GTO frequencies (PRESERVED)'),
    ]

    print("\n" + "=" * 60)
    print("CURRENT DATABASE STATE")
    print("=" * 60)

    for table_name, description in tables:
        try:
            count = conn.execute(text(f'SELECT COUNT(*) FROM {table_name}')).scalar()
            preserved = "(PRESERVED)" in description
            marker = "  [KEEP]" if preserved else "  [DELETE]"
            print(f"{marker} {description}: {count:,} rows")
        except Exception as e:
            print(f"  [N/A]  {description}: table does not exist")

    print("=" * 60)

def reset_player_data(conn, dry_run=True):
    """Reset all player data tables."""

    # Tables to clear (in order to respect foreign keys)
    tables_to_clear = [
        ('hand_actions', 'Hand actions'),
        ('player_preflop_actions', 'Player preflop actions'),
        ('player_scenario_stats', 'Player scenario stats'),
        ('raw_hands', 'Hand histories'),
        ('player_stats', 'Player stats'),
        ('upload_sessions', 'Upload sessions'),
    ]

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No data will be deleted")
        print("=" * 60)
        print("\nThe following tables would be cleared:")
        for table_name, description in tables_to_clear:
            try:
                count = conn.execute(text(f'SELECT COUNT(*) FROM {table_name}')).scalar()
                print(f"  - {description} ({table_name}): {count:,} rows")
            except:
                print(f"  - {description} ({table_name}): table does not exist")

        print("\nThe following tables will be PRESERVED:")
        print("  - GTO scenarios (gto_scenarios)")
        print("  - GTO frequencies (gto_frequencies)")
        print("\nTo actually delete, run with --confirm flag")
        return

    print("\n" + "=" * 60)
    print("RESETTING DATABASE")
    print("=" * 60)

    total_deleted = 0

    for table_name, description in tables_to_clear:
        try:
            # Get count before delete
            count = conn.execute(text(f'SELECT COUNT(*) FROM {table_name}')).scalar()

            if count > 0:
                # Delete all rows
                conn.execute(text(f'DELETE FROM {table_name}'))
                print(f"  Deleted {count:,} rows from {description}")
                total_deleted += count
            else:
                print(f"  {description}: already empty")

        except Exception as e:
            print(f"  {description}: skipped ({str(e)[:50]})")

    conn.commit()

    print("\n" + "=" * 60)
    print(f"RESET COMPLETE - {total_deleted:,} total rows deleted")
    print("=" * 60)

    # Show preserved data
    gto_scenarios = conn.execute(text('SELECT COUNT(*) FROM gto_scenarios')).scalar()
    gto_freqs = conn.execute(text('SELECT COUNT(*) FROM gto_frequencies')).scalar()
    print(f"\nPreserved GTO data:")
    print(f"  - {gto_scenarios:,} scenarios")
    print(f"  - {gto_freqs:,} frequencies")

def main():
    parser = argparse.ArgumentParser(
        description='Reset player data in the poker analysis database'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Actually delete the data (without this flag, only shows what would be deleted)'
    )
    parser.add_argument(
        '--show-only',
        action='store_true',
        help='Only show current database state, no deletion'
    )

    args = parser.parse_args()

    # Connect to database
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # Always show current state
        show_current_counts(conn)

        if args.show_only:
            return

        # Confirm if not dry run
        if args.confirm:
            print("\n⚠️  WARNING: This will DELETE all player data!")
            response = input("Type 'YES' to confirm: ")
            if response != 'YES':
                print("Aborted.")
                return

        # Run reset
        reset_player_data(conn, dry_run=not args.confirm)

if __name__ == '__main__':
    main()
