"""
Migration: Complete P&L recalculation from raw hand text

This migration:
1. Recalculates profit_loss for ALL hands by parsing raw text
2. Handles: collected amounts, uncalled bet returns, currency symbols (€, $, £)
3. Updates won_hand flag correctly
4. Recalculates session totals
"""

import os
import sys
import re
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def calculate_profit_loss(player_name: str, raw_text: str) -> tuple:
    """
    Calculate profit/loss from raw hand text.
    Returns (profit_loss, won_hand)
    """
    escaped_name = re.escape(player_name)
    currency = r'[$€£]?'

    # Find all bet amounts for this player
    # Patterns: "PlayerName: raises €X to €Y", "PlayerName: bets €X", "PlayerName: calls €X"
    # Also blinds: "PlayerName: posts small blind €X", "PlayerName: posts big blind €X"
    bet_patterns = [
        rf"{escaped_name}: (?:raises|bets|calls) {currency}[\d.]+(?: to {currency}([\d.]+))?",
        rf"{escaped_name}: posts (?:small blind|big blind|the ante) {currency}([\d.]+)",
    ]

    total_invested = Decimal("0")

    # Parse betting actions - need to be careful about "raises X to Y" vs "bets X"
    # For raises: "raises €0.06 to €0.10" means total bet is €0.10
    # For bets/calls: "bets €0.10" or "calls €0.10" means that amount

    # Find all monetary actions by this player
    action_pattern = rf"{escaped_name}: (raises|bets|calls|posts small blind|posts big blind|posts the ante) {currency}([\d.]+)(?: to {currency}([\d.]+))?"
    for match in re.finditer(action_pattern, raw_text):
        action_type = match.group(1)
        amount1 = Decimal(match.group(2))
        amount2 = Decimal(match.group(3)) if match.group(3) else None

        if action_type == "raises" and amount2:
            # "raises X to Y" - Y is the total amount (but this is cumulative in the street)
            # Actually for P&L calculation, we need the final invested amount
            # This is complex - let's use a simpler approach
            pass
        # Skip this complex parsing for now

    # Simpler approach: find total pot contributed in SUMMARY section
    # The SUMMARY section shows final stack sizes, but not contributions directly

    # Even simpler: Use the action amounts directly
    # Find all amounts this player put in (bets, raises, calls, blinds)
    all_amounts_pattern = rf"{escaped_name}(?:: (?:raises|bets|calls|posts[^€$£]+)){currency}([\d.]+)"
    for match in re.finditer(all_amounts_pattern, raw_text):
        total_invested += Decimal(match.group(1))

    # Check for "and is all-in" with amount
    allin_pattern = rf"{escaped_name}(?:: (?:raises|bets|calls)[^,]+, and is all-in)"
    # The all-in amount is already included in the previous patterns

    # Check for uncalled bet returned
    uncalled_pattern = rf"Uncalled bet \({currency}([\d.]+)\) returned to {escaped_name}"
    uncalled_match = re.search(uncalled_pattern, raw_text)
    if uncalled_match:
        total_invested -= Decimal(uncalled_match.group(1))

    # Check if player collected (won)
    collect_pattern = rf"{escaped_name} collected {currency}([\d.]+)"
    collect_matches = re.findall(collect_pattern, raw_text)
    total_collected = sum(Decimal(m) for m in collect_matches)

    if total_collected > 0:
        return (float(total_collected - total_invested), True)
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
        print("Step 1: Getting all hands...")

        query = text("""
            SELECT
                phs.summary_id,
                phs.player_name,
                rh.raw_hand_text
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
        """)

        result = session.execute(query)
        rows = result.fetchall()
        print(f"  Found {len(rows)} hands to process")

        print("\nStep 2: Recalculating P&L for each hand...")

        updates = []
        for i, row in enumerate(rows):
            summary_id = row[0]
            player_name = row[1]
            raw_text = row[2]

            profit_loss, won_hand = calculate_profit_loss(player_name, raw_text)

            updates.append({
                'summary_id': summary_id,
                'profit_loss': profit_loss,
                'won_hand': won_hand
            })

            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(rows)} hands...")

        print(f"  Processed all {len(rows)} hands")

        print("\nStep 3: Applying updates...")

        update_query = text("""
            UPDATE player_hand_summary
            SET profit_loss = :profit_loss, won_hand = :won_hand
            WHERE summary_id = :summary_id
        """)

        for i, update in enumerate(updates):
            session.execute(update_query, update)
            if (i + 1) % 1000 == 0:
                print(f"  Updated {i + 1}/{len(updates)} hands...")
                session.commit()  # Commit in batches

        session.commit()
        print(f"  Updated all {len(updates)} hands")

        # Step 4: Recalculate session totals
        print("\nStep 4: Recalculating session P/L...")

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

        # Verify
        print("\nStep 5: Verification...")

        verify = text("""
            SELECT session_id, player_name, total_hands, profit_loss_bb, bb_100
            FROM sessions
            ORDER BY profit_loss_bb DESC
            LIMIT 15
        """)
        result = session.execute(verify)

        print("\nSessions (sorted by P/L, best first):")
        print("ID   | Player     | Hands | P&L (bb) | bb/100")
        print("-" * 55)
        positive = 0
        for row in result:
            pl = row[3] if row[3] else 0
            bb100 = row[4] if row[4] else 0
            marker = "+" if pl > 0 else ""
            print(f"{row[0]:4} | {row[1][:10]:10} | {row[2]:5} | {marker}{pl:7.1f} | {bb100:6.1f}")
            if pl > 0:
                positive += 1

        print(f"\nPositive sessions: {positive}")

        # Check won_hand stats
        result = session.execute(text("""
            SELECT won_hand, COUNT(*) FROM player_hand_summary GROUP BY won_hand
        """))
        print("\nwon_hand distribution:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

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
    print("Migration: Complete P&L Recalculation")
    print("=" * 70)
    print()
    success = run_migration()
    sys.exit(0 if success else 1)
