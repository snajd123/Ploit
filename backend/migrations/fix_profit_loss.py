"""
Migration: Fix profit_loss and won_hand for all hands

This migration re-calculates profit_loss and won_hand for all hands
by parsing the "collected" amounts from raw_hand_text.

The previous parser didn't handle Euro (€) currency symbol, so all
hands using € showed negative P&L even when the player won.
"""

import os
import sys
import re
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Run the migration to fix profit_loss and won_hand."""

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Run: source backend/.env")
        return False

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("Step 1: Finding hands with 'collected' in raw text...")

        # Get all hands where someone collected
        query = text("""
            SELECT
                phs.summary_id,
                phs.player_name,
                phs.profit_loss,
                phs.won_hand,
                rh.raw_hand_text
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.raw_hand_text LIKE '%collected%'
        """)

        result = session.execute(query)
        rows = result.fetchall()
        print(f"  Found {len(rows)} hands with 'collected'")

        # Currency pattern: $, €, £
        currency_pattern = r'[$€£]'

        updates = []
        fixed_count = 0

        print("\nStep 2: Checking each hand for collection by player...")

        for row in rows:
            summary_id = row[0]
            player_name = row[1]
            current_profit = row[2]
            current_won = row[3]
            raw_text = row[4]

            # Check if this player collected
            # Pattern: "PlayerName collected €X.XX" or "PlayerName collected $X.XX from pot"
            escaped_name = re.escape(player_name)
            collect_pattern = rf"{escaped_name} collected {currency_pattern}?([\d.]+)"
            collect_match = re.search(collect_pattern, raw_text)

            if collect_match:
                collected_amount = Decimal(collect_match.group(1))

                # If won_hand is False or profit is negative, this needs fixing
                if not current_won or (current_profit is not None and current_profit < 0):
                    # Calculate total invested from actions
                    # We can approximate: if they collected X and current P/L is -Y,
                    # they invested (X - actual_profit). But we don't know actual_profit.
                    # Better approach: new_profit = collected - invested = collected - (-current_profit) = collected + current_profit
                    # Wait, that's not right either.

                    # Current logic (wrong): profit_loss = -total_invested (because collect wasn't found)
                    # So current_profit = -total_invested
                    # Therefore: total_invested = -current_profit
                    # Correct profit = collected - total_invested = collected - (-current_profit) = collected + current_profit

                    if current_profit is not None:
                        total_invested = -Decimal(str(current_profit))
                        correct_profit = collected_amount - total_invested

                        updates.append({
                            'summary_id': summary_id,
                            'profit_loss': float(correct_profit),
                            'won_hand': True
                        })
                        fixed_count += 1

        print(f"  Found {fixed_count} hands that need P/L correction")

        if updates:
            print("\nStep 3: Applying corrections...")

            update_query = text("""
                UPDATE player_hand_summary
                SET profit_loss = :profit_loss, won_hand = :won_hand
                WHERE summary_id = :summary_id
            """)

            for i, update in enumerate(updates):
                session.execute(update_query, update)
                if (i + 1) % 100 == 0:
                    print(f"  Updated {i + 1}/{len(updates)} hands...")

            session.commit()
            print(f"  Completed! Updated {len(updates)} hands")

        # Step 4: Recalculate session P/L
        print("\nStep 4: Recalculating session P/L totals...")

        update_sessions = text("""
            UPDATE sessions s
            SET profit_loss_bb = (
                SELECT COALESCE(SUM(phs.profit_loss), 0) /
                    CASE
                        WHEN s.table_stakes LIKE 'NL%' THEN
                            CAST(SUBSTRING(s.table_stakes FROM 3) AS DECIMAL) / 100
                        ELSE 0.04
                    END
                FROM player_hand_summary phs
                WHERE phs.session_id = s.session_id
                AND phs.player_name = s.player_name
            ),
            bb_100 = (
                SELECT COALESCE(SUM(phs.profit_loss), 0) /
                    CASE
                        WHEN s.table_stakes LIKE 'NL%' THEN
                            CAST(SUBSTRING(s.table_stakes FROM 3) AS DECIMAL) / 100
                        ELSE 0.04
                    END / NULLIF(s.total_hands, 0) * 100
                FROM player_hand_summary phs
                WHERE phs.session_id = s.session_id
                AND phs.player_name = s.player_name
            )
        """)

        result = session.execute(update_sessions)
        session.commit()
        print(f"  Updated {result.rowcount} sessions")

        # Verify
        print("\nStep 5: Verifying results...")
        verify = text("""
            SELECT
                session_id,
                player_name,
                total_hands,
                profit_loss_bb,
                bb_100
            FROM sessions
            ORDER BY session_id DESC
            LIMIT 10
        """)
        result = session.execute(verify)

        print("\nSession P/L after fix:")
        print("ID   | Player     | Hands | P&L (bb) | bb/100")
        print("-" * 55)
        for row in result:
            pl = row[3] if row[3] else 0
            bb100 = row[4] if row[4] else 0
            print(f"{row[0]:4} | {row[1][:10]:10} | {row[2]:5} | {pl:8.1f} | {bb100:6.1f}")

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
    print("Migration: Fix profit_loss and won_hand for Euro hands")
    print("=" * 70)
    print()

    success = run_migration()
    sys.exit(0 if success else 1)
