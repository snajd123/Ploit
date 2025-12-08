"""
Migration: Add strategy_id column to player_hand_summary

This migration:
1. Adds the strategy_id column to player_hand_summary table
2. Creates an index for efficient lookups
3. Backfills existing hands by assigning the most recent strategy
   that was created BEFORE the hand was played

This enables tracking which pre-game strategy was active for each hand,
allowing the session debrief to compare performance against specific
strategy goals.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Run the migration to add strategy_id column and backfill data."""

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
        # Step 1: Add the strategy_id column if it doesn't exist
        print("Step 1: Adding strategy_id column...")

        check_column = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'player_hand_summary'
            AND column_name = 'strategy_id'
        """)
        result = session.execute(check_column)
        column_exists = result.fetchone() is not None

        if not column_exists:
            add_column = text("""
                ALTER TABLE player_hand_summary
                ADD COLUMN strategy_id INTEGER
            """)
            session.execute(add_column)
            session.commit()
            print("  Column added successfully")
        else:
            print("  Column already exists, skipping creation")

        # Step 2: Create index for efficient lookups
        print("\nStep 2: Creating index on strategy_id...")
        try:
            create_index = text("""
                CREATE INDEX IF NOT EXISTS idx_phs_strategy_id
                ON player_hand_summary(strategy_id)
            """)
            session.execute(create_index)
            session.commit()
            print("  Index created successfully")
        except Exception as e:
            print(f"  Index creation note: {e}")
            session.rollback()

        # Step 3: Check how many strategies and hands we have
        print("\nStep 3: Checking data...")

        count_strategies = text("SELECT COUNT(*) FROM pregame_strategies")
        strategy_count = session.execute(count_strategies).scalar()
        print(f"  Found {strategy_count} strategies")

        count_hands = text("SELECT COUNT(*) FROM player_hand_summary WHERE strategy_id IS NULL")
        hands_without_strategy = session.execute(count_hands).scalar()
        print(f"  Found {hands_without_strategy} hands without strategy_id")

        if strategy_count == 0:
            print("\n  No strategies found - skipping backfill")
            print("  Hands will get strategy_id assigned when uploaded after a strategy is generated")
            return True

        # Step 4: Backfill strategy_id based on hand timestamp
        # For each hand, find the most recent strategy created BEFORE the hand was played
        print("\nStep 4: Backfilling strategy_id for existing hands...")

        backfill_query = text("""
            UPDATE player_hand_summary phs
            SET strategy_id = subq.strategy_id
            FROM (
                SELECT
                    phs_inner.summary_id,
                    (
                        SELECT ps.id
                        FROM pregame_strategies ps
                        WHERE ps.created_at <= rh.timestamp
                        ORDER BY ps.created_at DESC
                        LIMIT 1
                    ) as strategy_id
                FROM player_hand_summary phs_inner
                JOIN raw_hands rh ON phs_inner.hand_id = rh.hand_id
                WHERE phs_inner.strategy_id IS NULL
            ) subq
            WHERE phs.summary_id = subq.summary_id
            AND subq.strategy_id IS NOT NULL
        """)
        result = session.execute(backfill_query)
        session.commit()
        print(f"  Updated {result.rowcount} hands with strategy_id")

        # Step 5: Verify the migration
        print("\nStep 5: Verifying migration...")

        verify_query = text("""
            SELECT
                ps.id as strategy_id,
                ps.created_at,
                COUNT(phs.summary_id) as hands_assigned
            FROM pregame_strategies ps
            LEFT JOIN player_hand_summary phs ON phs.strategy_id = ps.id
            GROUP BY ps.id, ps.created_at
            ORDER BY ps.created_at DESC
            LIMIT 10
        """)
        result = session.execute(verify_query)

        print("\n  Strategy ID | Created At           | Hands Assigned")
        print("  " + "-" * 55)
        for row in result:
            created_str = row[1].strftime("%Y-%m-%d %H:%M") if row[1] else "N/A"
            print(f"  {row[0]:11} | {created_str:20} | {row[2]}")

        # Count hands still without strategy
        remaining = text("SELECT COUNT(*) FROM player_hand_summary WHERE strategy_id IS NULL")
        remaining_count = session.execute(remaining).scalar()
        print(f"\n  Hands without strategy_id: {remaining_count}")
        print("  (These are hands played before any strategy was generated)")

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
    print("Migration: Add strategy_id column to player_hand_summary")
    print("=" * 70)
    print()

    success = run_migration()
    sys.exit(0 if success else 1)
