"""
Fix faced_three_bet bug in player_hand_summary table.

The bug: faced_three_bet was being set to True even when the player
MADE the 3-bet (they can't "face" a raise they made themselves).

Also recalculates folded_to_three_bet, called_three_bet, and four_bet flags.
"""

import os
import sys
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL
# Use transaction mode (port 6543) to avoid session pool limits
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.lyvnuiuatuggtirdxiht:SourBeer2027@aws-1-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require')


def fix_faced_three_bet():
    """
    Fix faced_three_bet and response flags by reparsing all hands.
    """
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all hands with their raw text
        logger.info("Fetching hands to process...")

        result = session.execute(text("""
            SELECT DISTINCT rh.hand_id, rh.raw_hand_text
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
        raise_pattern = re.compile(r'([^:\n]+): raises [\$€]?[\d.]+ to [\$€]?([\d.]+)')
        action_pattern = re.compile(r'([^:\n]+): (folds|checks|calls|bets|raises)')

        for i, row in enumerate(hands):
            hand_id = row[0]
            raw_text = row[1]

            if i % 500 == 0:
                logger.info(f"Processing hand {i+1}/{total}...")

            try:
                # Find preflop section
                preflop_match = re.search(r'\*\*\* HOLE CARDS \*\*\*(.*?)(?:\*\*\* FLOP|\*\*\* SUMMARY)', raw_text, re.DOTALL)
                if not preflop_match:
                    continue

                preflop_text = preflop_match.group(1)

                # Find all raises in order
                raises = list(raise_pattern.finditer(preflop_text))

                # Reset all 3-bet and 4-bet related flags for all players in this hand
                session.execute(text("""
                    UPDATE player_hand_summary
                    SET faced_three_bet = false,
                        folded_to_three_bet = false,
                        called_three_bet = false,
                        faced_four_bet = false,
                        folded_to_four_bet = false,
                        called_four_bet = false
                    WHERE hand_id = :hand_id
                """), {"hand_id": hand_id})

                # If there's a 3-bet (2nd raise), process it
                if len(raises) >= 2:
                    three_bettor = raises[1].group(1).strip()
                    three_bet_end = raises[1].end()

                    # Get text after the 3-bet to find responses
                    text_after_3bet = preflop_text[three_bet_end:]

                    # Track each player's FIRST action after facing the 3-bet
                    player_responses = {}
                    for match in action_pattern.finditer(text_after_3bet):
                        player = match.group(1).strip()
                        action = match.group(2)

                        # Skip the 3-bettor's own later actions
                        if player == three_bettor:
                            continue

                        # Only record first action after 3-bet
                        if player not in player_responses:
                            player_responses[player] = action

                    # Update flags for players who faced the 3-bet
                    for player, action in player_responses.items():
                        faced_3bet = True
                        folded = action == 'folds'
                        called = action == 'calls'
                        four_bet = action == 'raises'

                        session.execute(text("""
                            UPDATE player_hand_summary
                            SET faced_three_bet = :faced,
                                folded_to_three_bet = :folded,
                                called_three_bet = :called,
                                four_bet = :four_bet
                            WHERE hand_id = :hand_id AND player_name = :player_name
                        """), {
                            "hand_id": hand_id,
                            "player_name": player,
                            "faced": faced_3bet,
                            "folded": folded,
                            "called": called,
                            "four_bet": four_bet
                        })

                # If there's a 4-bet (3rd raise), process it
                if len(raises) >= 3:
                    four_bettor = raises[2].group(1).strip()
                    four_bet_end = raises[2].end()

                    # Get text after the 4-bet
                    text_after_4bet = preflop_text[four_bet_end:]

                    # Track each player's FIRST action after facing the 4-bet
                    player_responses_4bet = {}
                    for match in action_pattern.finditer(text_after_4bet):
                        player = match.group(1).strip()
                        action = match.group(2)

                        if player == four_bettor:
                            continue

                        if player not in player_responses_4bet:
                            player_responses_4bet[player] = action

                    # Update flags for players who faced the 4-bet
                    for player, action in player_responses_4bet.items():
                        faced_4bet = True
                        folded = action == 'folds'
                        called = action == 'calls'

                        session.execute(text("""
                            UPDATE player_hand_summary
                            SET faced_four_bet = :faced,
                                folded_to_four_bet = :folded,
                                called_four_bet = :called
                            WHERE hand_id = :hand_id AND player_name = :player_name
                        """), {
                            "hand_id": hand_id,
                            "player_name": player,
                            "faced": faced_4bet,
                            "folded": folded,
                            "called": called
                        })

                updated += 1

            except Exception as e:
                errors += 1
                if errors < 10:
                    logger.warning(f"Error processing hand {hand_id}: {e}")
                    import traceback
                    traceback.print_exc()

        session.commit()
        logger.info(f"Done! Updated {updated} hands, {errors} errors")

        # Verify the fix - facing 3-bet should now sum to 100%
        result = session.execute(text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_three_bet = true) as faced_3bet,
                ROUND(100.0 * COUNT(*) FILTER (WHERE folded_to_three_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true), 0), 1) as fold_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE called_three_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true), 0), 1) as call_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE four_bet = true AND faced_three_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true), 0), 1) as four_bet_pct
            FROM player_hand_summary
            WHERE player_name = 'snajd'
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_three_bet = true) >= 1
            ORDER BY position;
        """))

        logger.info("\nVerification - Facing 3-bet stats:")
        logger.info("Position | Faced 3bet | Fold% | Call% | 4bet% | Total%")
        logger.info("-" * 60)
        for row in result:
            total = (row[2] or 0) + (row[3] or 0) + (row[4] or 0)
            logger.info(f"{row[0]:8} | {row[1]:10} | {row[2] or 0:5} | {row[3] or 0:5} | {row[4] or 0:5} | {total}")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    fix_faced_three_bet()
