"""
Migration: Correct P&L calculation for hero nicknames

The correct P&L calculation:
1. For each street, the investment is the FINAL bet amount (cumulative), not the sum
2. Sum final bets across all streets = total invested
3. Subtract any uncalled bet returned
4. Profit = collected - net_invested

Only processes hero nicknames from hero_nicknames table.
"""

import os
import sys
import re
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def calculate_profit_loss(player_name: str, hand_id: int, session, raw_text: str) -> tuple:
    """
    Calculate profit/loss correctly.
    Returns (profit_loss, won_hand)
    """
    # Get all actions for this player in this hand, grouped by street
    result = session.execute(text("""
        SELECT street, MAX(amount) as max_bet
        FROM hand_actions
        WHERE hand_id = :hand_id AND player_name = :player_name AND amount > 0
        GROUP BY street
    """), {'hand_id': hand_id, 'player_name': player_name})

    # Sum the final bet per street = total invested
    total_invested = Decimal("0")
    for row in result:
        if row[1]:  # max_bet
            total_invested += Decimal(str(row[1]))

    # Check for uncalled bet returned
    escaped_name = re.escape(player_name)
    uncalled_pattern = rf"Uncalled bet \([$€£]?([\d.]+)\) returned to {escaped_name}"
    uncalled_match = re.search(uncalled_pattern, raw_text)
    if uncalled_match:
        returned_amount = Decimal(uncalled_match.group(1))
        total_invested -= returned_amount

    # Check if player collected (won)
    collect_pattern = rf"{escaped_name} collected [$€£]?([\d.]+)"
    collect_matches = re.findall(collect_pattern, raw_text)
    total_collected = sum(Decimal(m) for m in collect_matches)

    if total_collected > 0:
        profit = total_collected - total_invested
        return (float(profit), True)
    else:
        return (float(-total_invested), False)


def run_migration():
    """Run the migration."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return False

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get hero nicknames
        print("Step 1: Getting hero nicknames...")
        result = session.execute(text("SELECT nickname FROM hero_nicknames"))
        heroes = [row[0] for row in result]
        print(f"  Heroes: {heroes}")

        if not heroes:
            print("  No hero nicknames configured!")
            return False

        # Get all hero hands
        print("\nStep 2: Getting hero hands...")
        heroes_str = "', '".join(heroes)

        query = text(f"""
            SELECT
                phs.summary_id,
                phs.hand_id,
                phs.player_name,
                rh.raw_hand_text
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE phs.player_name IN ('{heroes_str}')
        """)

        result = session.execute(query)
        rows = result.fetchall()
        print(f"  Found {len(rows)} hero hands to process")

        print("\nStep 3: Recalculating P&L for each hero hand...")

        updates = []
        for i, row in enumerate(rows):
            summary_id = row[0]
            hand_id = row[1]
            player_name = row[2]
            raw_text = row[3]

            profit_loss, won_hand = calculate_profit_loss(player_name, hand_id, session, raw_text)

            updates.append({
                'summary_id': summary_id,
                'profit_loss': profit_loss,
                'won_hand': won_hand
            })

            if (i + 1) % 200 == 0:
                print(f"  Processed {i + 1}/{len(rows)} hands...")

        print(f"  Processed all {len(rows)} hands")

        print("\nStep 4: Applying updates...")

        update_query = text("""
            UPDATE player_hand_summary
            SET profit_loss = :profit_loss, won_hand = :won_hand
            WHERE summary_id = :summary_id
        """)

        for i, update in enumerate(updates):
            session.execute(update_query, update)
            if (i + 1) % 500 == 0:
                print(f"  Updated {i + 1}/{len(updates)} hands...")
                session.commit()

        session.commit()
        print(f"  Updated all {len(updates)} hands")

        # Step 5: Recalculate session totals
        print("\nStep 5: Recalculating session P/L...")

        update_sessions = text("""
            UPDATE sessions s
            SET profit_loss_bb = (
                SELECT COALESCE(SUM(phs.profit_loss), 0) /
                    CASE
                        WHEN s.table_stakes LIKE 'NL%' THEN
                            CAST(SUBSTRING(s.table_stakes FROM 3) AS DECIMAL) / 100
                        WHEN s.table_stakes LIKE '%/%' THEN
                            CAST(SPLIT_PART(REPLACE(REPLACE(s.table_stakes, '€', ''), '$', ''), '/', 2) AS DECIMAL)
                        ELSE 0.04
                    END
                FROM player_hand_summary phs
                WHERE phs.session_id = s.session_id
                AND phs.player_name = s.player_name
            )
        """)
        session.execute(update_sessions)

        # Update bb_100
        update_bb100 = text("""
            UPDATE sessions
            SET bb_100 = profit_loss_bb / NULLIF(total_hands, 0) * 100
            WHERE total_hands > 0
        """)
        session.execute(update_bb100)
        session.commit()

        print("  Session totals updated")

        # Verify with sample hand
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Check the specific hand we know the answer for
        print("\nHand 2323273080 (snajd's AA 5-bet shove):")
        print("  Expected: ~€0.53 profit (collected €1.06, invested €0.53)")
        result = session.execute(text("""
            SELECT profit_loss, won_hand
            FROM player_hand_summary
            WHERE hand_id = 2323273080 AND player_name = 'snajd'
        """))
        row = result.fetchone()
        if row:
            print(f"  Calculated: €{row[0]:.2f} profit, won_hand={row[1]}")

        # Show session totals
        print("\nSessions (sorted by P/L):")
        verify = text("""
            SELECT session_id, player_name, total_hands, profit_loss_bb, bb_100
            FROM sessions
            ORDER BY profit_loss_bb DESC
            LIMIT 10
        """)
        result = session.execute(verify)

        print("ID   | Player     | Hands | P&L (bb) | bb/100")
        print("-" * 55)
        for row in result:
            pl = row[3] if row[3] else 0
            bb100 = row[4] if row[4] else 0
            marker = "+" if pl > 0 else ""
            print(f"{row[0]:4} | {row[1][:10]:10} | {row[2]:5} | {marker}{pl:7.1f} | {bb100:6.1f}")

        # Show hero P&L totals
        print("\n\nHero P&L totals:")
        result = session.execute(text(f"""
            SELECT
                player_name,
                COUNT(*) as hands,
                SUM(CASE WHEN won_hand THEN 1 ELSE 0 END) as wins,
                SUM(profit_loss) as total_pl
            FROM player_hand_summary
            WHERE player_name IN ('{heroes_str}')
            GROUP BY player_name
        """))
        for row in result:
            win_rate = row[2] / row[1] * 100 if row[1] > 0 else 0
            print(f"  {row[0]}: {row[1]} hands, {row[2]} wins ({win_rate:.1f}%), €{row[3]:.2f} total P&L")

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("Migration: Correct P&L Calculation (Hero Nicknames Only)")
    print("=" * 70)
    print()
    success = run_migration()
    sys.exit(0 if success else 1)
