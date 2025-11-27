"""
Fix faced_raise bug in player_hand_summary table.

The bug: faced_raise was being set to True for ALL preflop actions because
current_bet > 0 (due to big blind). This meant RFI (raise first in) hands
were incorrectly marked as facing a raise.

The fix: Reparse all hands and recalculate the faced_raise flag properly.
"""

import os
import sys

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
    2. Find first raise action (above BB)
    3. Mark faced_raise=False for the raiser
    4. Mark faced_raise=True for everyone who acted after the raise
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

        for i, row in enumerate(hands):
            hand_id = row[0]
            raw_text = row[1]
            stake_level = row[2]

            if i % 500 == 0:
                logger.info(f"Processing hand {i+1}/{total}...")

            try:
                # Parse the hand to find first raiser
                import re

                # Find all preflop actions before FLOP
                preflop_match = re.search(r'\*\*\* HOLE CARDS \*\*\*(.*?)(?:\*\*\* FLOP|\*\*\* SUMMARY)', raw_text, re.DOTALL)
                if not preflop_match:
                    continue

                preflop_text = preflop_match.group(1)

                # Find the first raise action
                raise_pattern = r'([^:\n]+): raises [\$€]?[\d.]+ to [\$€]?([\d.]+)'
                first_raise_match = re.search(raise_pattern, preflop_text)

                if first_raise_match:
                    first_raiser = first_raise_match.group(1).strip()

                    # Get all players who acted before the first raise
                    lines_before_raise = preflop_text[:first_raise_match.start()]

                    # Players who acted before the raise faced_raise=False
                    # Players who acted after (or at) the raise faced_raise=True (except the raiser)

                    # Update the first raiser: faced_raise should be False (they opened)
                    session.execute(text("""
                        UPDATE player_hand_summary
                        SET faced_raise = false
                        WHERE hand_id = :hand_id AND player_name = :player_name
                    """), {"hand_id": hand_id, "player_name": first_raiser})

                    # Update everyone else who VPIP'd or folded after the raise: faced_raise=True
                    session.execute(text("""
                        UPDATE player_hand_summary
                        SET faced_raise = true
                        WHERE hand_id = :hand_id AND player_name != :player_name
                    """), {"hand_id": hand_id, "player_name": first_raiser})

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
            ORDER BY position;
        """))

        logger.info("\nVerification for player 'snajd':")
        logger.info("Position | RFI Opps | RFI Raised | Total")
        logger.info("-" * 45)
        for row in result:
            logger.info(f"{row[0]:8} | {row[1]:8} | {row[2]:10} | {row[3]}")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    fix_faced_raise()
