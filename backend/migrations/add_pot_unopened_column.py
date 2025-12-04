"""
Migration: Add pot_unopened column to player_hand_summary

This migration:
1. Adds the pot_unopened column to player_hand_summary table
2. Backfills existing data using a reliable SQL-based approach

pot_unopened = true means all players before the hero folded (no limps, no raises)
This is the correct condition for RFI (Raise First In) opportunities.

The previous approach of using `faced_raise = false` was incorrect because it didn't
account for limpers - a pot with a limper is NOT an RFI opportunity.

Backfill approach:
- For each hand, check if any player in an earlier position has limp = true
- Use position order: UTG -> MP -> HJ -> CO -> BTN -> SB -> BB
- If any earlier-position player limped, pot_unopened = false
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Run the migration to add pot_unopened column and backfill data."""

    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Run: source backend/.env")
        return False

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Step 1: Add the pot_unopened column if it doesn't exist
        print("Step 1: Adding pot_unopened column...")

        check_column = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'player_hand_summary'
            AND column_name = 'pot_unopened'
        """)
        result = session.execute(check_column)
        column_exists = result.fetchone() is not None

        if not column_exists:
            add_column = text("""
                ALTER TABLE player_hand_summary
                ADD COLUMN pot_unopened BOOLEAN DEFAULT FALSE
            """)
            session.execute(add_column)
            session.commit()
            print("  Column added successfully")
        else:
            print("  Column already exists, skipping creation")

        # Step 2: Initial backfill - set pot_unopened based on faced_raise
        # This is a reasonable starting point: if faced_raise = false, there was no raise
        # We'll then correct for limps in the next step
        print("\nStep 2: Initial backfill (pot_unopened = NOT faced_raise)...")

        initial_backfill = text("""
            UPDATE player_hand_summary
            SET pot_unopened = (faced_raise = false)
            WHERE pot_unopened IS NULL OR pot_unopened = false
        """)
        result = session.execute(initial_backfill)
        session.commit()
        print(f"  Updated {result.rowcount} rows")

        # Step 3: Correct for limps - if any earlier-position player limped, set pot_unopened = false
        # Position order: UTG=1, MP=2, HJ=3, CO=4, BTN=5, SB=6, BB=7
        print("\nStep 3: Correcting for limps (checking if earlier-position player limped)...")

        # This query finds all hands where a player limped, and marks pot_unopened = false
        # for all players in later positions within the same hand
        correct_for_limps = text("""
            WITH position_order AS (
                SELECT position,
                    CASE position
                        WHEN 'UTG' THEN 1
                        WHEN 'MP' THEN 2
                        WHEN 'HJ' THEN 3
                        WHEN 'CO' THEN 4
                        WHEN 'BTN' THEN 5
                        WHEN 'SB' THEN 6
                        WHEN 'BB' THEN 7
                        ELSE 99
                    END as pos_order
                FROM (VALUES ('UTG'), ('MP'), ('HJ'), ('CO'), ('BTN'), ('SB'), ('BB')) AS t(position)
            ),
            limped_hands AS (
                -- Find all hands where someone limped, and the position of the limper
                SELECT DISTINCT
                    phs.hand_id,
                    po.pos_order as limper_pos_order
                FROM player_hand_summary phs
                JOIN position_order po ON phs.position = po.position
                WHERE phs.limp = true
            ),
            rows_to_update AS (
                -- Find rows that need to be set to pot_unopened = false
                SELECT phs.summary_id
                FROM player_hand_summary phs
                JOIN position_order po ON phs.position = po.position
                JOIN limped_hands lh ON phs.hand_id = lh.hand_id
                WHERE po.pos_order > lh.limper_pos_order
                AND phs.pot_unopened = true
            )
            UPDATE player_hand_summary
            SET pot_unopened = false
            WHERE summary_id IN (SELECT summary_id FROM rows_to_update)
        """)
        result = session.execute(correct_for_limps)
        session.commit()
        print(f"  Corrected {result.rowcount} rows (limped pots)")

        # Step 4: Create index for faster queries
        print("\nStep 4: Creating index on pot_unopened...")
        try:
            create_index = text("""
                CREATE INDEX IF NOT EXISTS idx_phs_pot_unopened_position
                ON player_hand_summary(pot_unopened, position)
                WHERE pot_unopened = true
            """)
            session.execute(create_index)
            session.commit()
            print("  Index created successfully")
        except Exception as e:
            print(f"  Index creation note: {e}")
            session.rollback()

        # Step 5: Verify the migration
        print("\nStep 5: Verifying migration...")
        verify = text("""
            SELECT
                position,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE pot_unopened = true) as rfi_opportunities,
                COUNT(*) FILTER (WHERE faced_raise = false) as old_method,
                COUNT(*) FILTER (WHERE pot_unopened = true AND pfr = true) as opened
            FROM player_hand_summary
            WHERE position IN ('UTG', 'MP', 'CO', 'BTN', 'SB')
            GROUP BY position
            ORDER BY CASE position
                WHEN 'UTG' THEN 1 WHEN 'MP' THEN 2 WHEN 'CO' THEN 4 WHEN 'BTN' THEN 5 WHEN 'SB' THEN 6
            END
        """)
        result = session.execute(verify)

        print("\n  Position | Total  | RFI Opps (new) | faced_raise=F (old) | Opened")
        print("  " + "-" * 65)
        for row in result:
            rfi_pct = round(row[4] / row[2] * 100, 1) if row[2] > 0 else 0
            print(f"  {row[0]:8} | {row[1]:6} | {row[2]:14} | {row[3]:19} | {row[4]:6} ({rfi_pct}%)")

        print("\n  Note: RFI Opps (new) should be <= faced_raise=F (old)")
        print("  The difference is due to excluding limped pots from RFI opportunities.")

        return True

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("Migration: Add pot_unopened column to player_hand_summary")
    print("=" * 70)
    print()

    success = run_migration()
    sys.exit(0 if success else 1)
