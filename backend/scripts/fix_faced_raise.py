"""
Fix faced_raise bug in player_hand_summary table.

The bug: faced_raise was being set incorrectly. Players who acted BEFORE
the first raise should have faced_raise=False (they had RFI opportunity).

Correct logic:
- Players who fold/limp BEFORE any raise: faced_raise = False (had RFI opp)
- The first raiser: faced_raise = False (had RFI opp and took it)
- Players who act AFTER the first raise: faced_raise = True (face a raise)
"""

import os
import sys
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.lyvnuiuatuggtirdxiht:SourBeer2027@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require')


def fix_faced_raise():
    """
    Fix faced_raise by reparsing all hands.

    For each hand:
    1. Get the raw_hand_text
    2. Parse preflop actions in order
    3. Track which players acted before vs after first raise
    4. Update faced_raise accordingly
    """
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all hands with their raw text
        logger.info("Fetching hands to process...")

        result = session.execute(text("""
            SELECT DISTINCT rh.hand_id, rh.raw_hand_text, rh.stake_level
            FROM raw_hands rh
            JOIN player_hand_summary phs ON rh.hand_id = phs.hand_id
            ORDER BY rh.hand_id
        """))

        hands = list(result)
        total = len(hands)
        logger.info(f"Found {total} hands to process")

        updated = 0
        errors = 0

        # Action patterns
        action_pattern = re.compile(r'([^:\n]+): (folds|checks|calls|bets|raises)')

        for i, row in enumerate(hands):
            hand_id = row[0]
            raw_text = row[1]
            stake_level = row[2]

            if i % 500 == 0:
                logger.info(f"Processing hand {i+1}/{total}...")

            try:
                # Find preflop section
                preflop_match = re.search(r'\*\*\* HOLE CARDS \*\*\*(.*?)(?:\*\*\* FLOP|\*\*\* SUMMARY)', raw_text, re.DOTALL)
                if not preflop_match:
                    continue

                preflop_text = preflop_match.group(1)

                # Parse actions in order to find who acted before/after first raise
                players_before_raise = set()  # Players who acted before any raise
                first_raiser = None

                for line in preflop_text.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('Dealt to') or line.startswith('***'):
                        continue

                    match = action_pattern.match(line)
                    if match:
                        player_name = match.group(1).strip()
                        action = match.group(2)

                        if action == 'raises':
                            # Found first raise - stop tracking
                            first_raiser = player_name
                            players_before_raise.add(player_name)  # Raiser also had RFI opp
                            break
                        else:
                            # Player acted before any raise (fold, call/limp, check)
                            players_before_raise.add(player_name)

                # Now update the database
                if first_raiser:
                    # There was a raise
                    # Players who acted before raise (including raiser): faced_raise = False
                    # Everyone else: faced_raise = True

                    if players_before_raise:
                        # Set faced_raise=False for players who acted before/at raise
                        placeholders = ', '.join([f':p{i}' for i in range(len(players_before_raise))])
                        params = {"hand_id": hand_id}
                        for i, p in enumerate(players_before_raise):
                            params[f'p{i}'] = p

                        session.execute(text(f"""
                            UPDATE player_hand_summary
                            SET faced_raise = false
                            WHERE hand_id = :hand_id AND player_name IN ({placeholders})
                        """), params)

                        # Set faced_raise=True for everyone else
                        session.execute(text(f"""
                            UPDATE player_hand_summary
                            SET faced_raise = true
                            WHERE hand_id = :hand_id AND player_name NOT IN ({placeholders})
                        """), params)

                    updated += 1
                else:
                    # No raise - everyone faced_raise=False (limped or folded to BB)
                    session.execute(text("""
                        UPDATE player_hand_summary
                        SET faced_raise = false
                        WHERE hand_id = :hand_id
                    """), {"hand_id": hand_id})
                    updated += 1

            except Exception as e:
                errors += 1
                if errors < 10:
                    logger.warning(f"Error processing hand {hand_id}: {e}")

        session.commit()
        logger.info(f"Done! Updated {updated} hands, {errors} errors")

        # Verify the fix
        result = session.execute(text("""
            SELECT position,
                   COUNT(*) FILTER (WHERE faced_raise = false) as rfi_opps,
                   COUNT(*) FILTER (WHERE faced_raise = false AND pfr = true) as rfi_raised,
                   COUNT(*) as total
            FROM player_hand_summary
            WHERE player_name = 'snajd'
            GROUP BY position
            ORDER BY CASE position
                WHEN 'UTG' THEN 1 WHEN 'MP' THEN 2 WHEN 'CO' THEN 3
                WHEN 'BTN' THEN 4 WHEN 'SB' THEN 5 WHEN 'BB' THEN 6
            END;
        """))

        logger.info("\nVerification for player 'snajd':")
        logger.info("Position | RFI Opps | RFI Raised | Total | RFI %")
        logger.info("-" * 55)
        total_rfi_opps = 0
        total_hands = 0
        for row in result:
            rfi_pct = round(100 * row[1] / row[3], 1) if row[3] > 0 else 0
            logger.info(f"{row[0]:8} | {row[1]:8} | {row[2]:10} | {row[3]:5} | {rfi_pct}%")
            total_rfi_opps += row[1]
            total_hands += row[3]

        logger.info("-" * 55)
        logger.info(f"Total RFI opps: {total_rfi_opps}, Total hands: {total_hands}")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    fix_faced_raise()
