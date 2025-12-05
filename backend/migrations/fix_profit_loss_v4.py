"""
Migration: Simple P&L calculation from raw text

Simple logic:
- If hero collected: P&L = collected - invested
- If hero didn't collect: P&L = -invested

Invested = sum of what hero put in per street, minus uncalled returns
"""

import os
import sys
import re
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def calculate_pl_from_raw_text(hero_name: str, raw_text: str) -> tuple:
    """
    Simple P&L calculation from raw hand text.

    Returns (profit_loss, won_hand)
    """
    escaped = re.escape(hero_name)

    # Track investment per street
    # For raises "to €X" -> set position to X (cumulative)
    # For calls €X -> add X (additional)
    # For bets/posts €X -> set position to X

    current_street_investment = Decimal("0")
    total_invested = Decimal("0")
    current_street = None

    for line in raw_text.split('\n'):
        # Detect street changes
        if line.startswith('*** FLOP ***'):
            total_invested += current_street_investment
            current_street_investment = Decimal("0")
            current_street = 'flop'
        elif line.startswith('*** TURN ***'):
            total_invested += current_street_investment
            current_street_investment = Decimal("0")
            current_street = 'turn'
        elif line.startswith('*** RIVER ***'):
            total_invested += current_street_investment
            current_street_investment = Decimal("0")
            current_street = 'river'
        elif line.startswith('*** SHOW DOWN ***') or line.startswith('*** SUMMARY ***'):
            total_invested += current_street_investment
            current_street_investment = Decimal("0")
            break

        # Check if this is hero's action
        if not line.startswith(f'{hero_name}:'):
            continue

        # Parse the action
        # "raises €X to €Y" -> position = Y
        raise_match = re.search(r'raises .* to [$€£]?([\d.]+)', line)
        if raise_match:
            current_street_investment = Decimal(raise_match.group(1))
            continue

        # "bets €X" -> position = X (but add to existing if already bet)
        bet_match = re.search(r'bets [$€£]?([\d.]+)', line)
        if bet_match:
            # Bets start fresh, but if there's already investment it's a new bet
            current_street_investment = Decimal(bet_match.group(1))
            continue

        # "calls €X" -> add X
        call_match = re.search(r'calls [$€£]?([\d.]+)', line)
        if call_match:
            current_street_investment += Decimal(call_match.group(1))
            continue

        # "posts small blind €X" or "posts big blind €X"
        post_match = re.search(r'posts (?:small blind|big blind|the ante) [$€£]?([\d.]+)', line)
        if post_match:
            current_street_investment += Decimal(post_match.group(1))
            continue

    # Check for uncalled bet returned
    uncalled_match = re.search(rf'Uncalled bet \([$€£]?([\d.]+)\) returned to {escaped}', raw_text)
    if uncalled_match:
        total_invested -= Decimal(uncalled_match.group(1))

    # Check if hero collected
    collect_matches = re.findall(rf'{escaped} collected [$€£]?([\d.]+)', raw_text)
    total_collected = sum(Decimal(m) for m in collect_matches) if collect_matches else Decimal("0")

    if total_collected > 0:
        profit_loss = total_collected - total_invested
        return (float(profit_loss), True)
    else:
        profit_loss = -total_invested
        return (float(profit_loss), False)


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

        heroes_str = "', '".join(heroes)

        # Get all hero hands with raw text
        print("\nStep 2: Getting hero hands...")
        query = text(f"""
            SELECT phs.summary_id, phs.player_name, rh.raw_hand_text
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE phs.player_name IN ('{heroes_str}')
        """)
        result = session.execute(query)
        rows = result.fetchall()
        print(f"  Found {len(rows)} hero hands")

        print("\nStep 3: Recalculating P&L...")
        updates = []
        for i, row in enumerate(rows):
            summary_id, player_name, raw_text = row
            profit_loss, won_hand = calculate_pl_from_raw_text(player_name, raw_text)
            updates.append({
                'summary_id': summary_id,
                'profit_loss': profit_loss,
                'won_hand': won_hand
            })
            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(rows)}...")

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
                session.commit()
        session.commit()

        # Update session totals
        print("\nStep 5: Updating session totals...")
        session.execute(text("""
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
                WHERE phs.session_id = s.session_id AND phs.player_name = s.player_name
            )
        """))
        session.execute(text("""
            UPDATE sessions SET bb_100 = profit_loss_bb / NULLIF(total_hands, 0) * 100 WHERE total_hands > 0
        """))
        session.commit()

        # Verify with known hand
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Test hand 2324197450 - snajd all-in with flush
        result = session.execute(text("""
            SELECT phs.profit_loss, rh.raw_hand_text
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.hand_id = 2324197450 AND phs.player_name = 'snajd'
        """))
        row = result.fetchone()
        if row:
            print(f"\nHand 2324197450 (snajd all-in flush):")
            print(f"  Starting stack: €5.50")
            print(f"  Collected: €6.19 + €6.67 = €12.86")
            print(f"  Expected P&L: €12.86 - €5.50 = €7.36")
            print(f"  Calculated: €{row[0]:.2f}")

        # Show totals
        print("\n\nHero P&L Summary:")
        result = session.execute(text(f"""
            SELECT player_name, COUNT(*),
                   SUM(CASE WHEN won_hand THEN 1 ELSE 0 END),
                   SUM(profit_loss)
            FROM player_hand_summary
            WHERE player_name IN ('{heroes_str}')
            GROUP BY player_name
        """))
        for row in result:
            print(f"  {row[0]}: {row[1]} hands, {row[2]} wins, €{row[3]:.2f} total P&L")

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
    print("=" * 60)
    print("Migration: Simple P&L Calculation")
    print("=" * 60)
    success = run_migration()
    sys.exit(0 if success else 1)
