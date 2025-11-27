"""
Fix position assignment bug in player_hand_summary table.

The bug: Sitting out players were included in position assignment,
causing positions to be offset incorrectly.

The fix: Reparse hands to correctly identify active players and positions.
"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.lyvnuiuatuggtirdxiht:SourBeer2027@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require')


def get_position_names(num_players: int) -> list:
    """Get position names based on number of active players."""
    if num_players == 6:
        return ["SB", "BB", "UTG", "MP", "CO", "BTN"]
    elif num_players == 5:
        return ["SB", "BB", "UTG", "CO", "BTN"]
    elif num_players == 4:
        return ["SB", "BB", "CO", "BTN"]
    elif num_players == 3:
        return ["SB", "BB", "BTN"]
    elif num_players == 2:
        return ["SB", "BB"]  # Heads up: BTN is SB
    elif num_players == 9:
        return ["SB", "BB", "UTG", "UTG+1", "UTG+2", "MP", "HJ", "CO", "BTN"]
    else:
        positions = ["SB", "BB"]
        for i in range(num_players - 3):
            positions.append(f"MP{i+1}")
        positions.append("BTN")
        return positions


def fix_positions():
    """Fix positions by reparsing all hands."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
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

        # Patterns
        button_pattern = re.compile(r"Seat #(\d+) is the button")
        seat_pattern = re.compile(r"Seat (\d+): ([^\(]+) \([\$€]?([\d.]+) in chips\)( is sitting out)?")

        for i, row in enumerate(hands):
            hand_id = row[0]
            raw_text = row[1]

            if i % 500 == 0:
                logger.info(f"Processing hand {i+1}/{total}...")

            try:
                # Find button
                btn_match = button_pattern.search(raw_text)
                if not btn_match:
                    continue
                button_seat = int(btn_match.group(1))

                # Extract active players (not sitting out)
                active_players = []
                for match in seat_pattern.finditer(raw_text):
                    seat_num = int(match.group(1))
                    player_name = match.group(2).strip()
                    is_sitting_out = match.group(4) is not None

                    if not is_sitting_out:
                        active_players.append({
                            'seat': seat_num,
                            'name': player_name
                        })

                # Sort by seat number
                active_players.sort(key=lambda p: p['seat'])
                num_players = len(active_players)

                if num_players < 2:
                    continue

                # Find button index in active players
                button_idx = next((i for i, p in enumerate(active_players)
                                   if p['seat'] == button_seat), 0)

                # Get position names
                position_names = get_position_names(num_players)

                # Assign positions starting from after button
                player_positions = {}
                for i in range(num_players):
                    pos_idx = (button_idx + 1 + i) % num_players
                    player_positions[active_players[pos_idx]['name']] = position_names[i]

                # Update positions in database
                for player_name, position in player_positions.items():
                    session.execute(text("""
                        UPDATE player_hand_summary
                        SET position = :position
                        WHERE hand_id = :hand_id AND player_name = :player_name
                    """), {
                        "hand_id": hand_id,
                        "player_name": player_name,
                        "position": position
                    })

                updated += 1

            except Exception as e:
                errors += 1
                if errors < 10:
                    logger.warning(f"Error processing hand {hand_id}: {e}")

        session.commit()
        logger.info(f"Done! Updated {updated} hands, {errors} errors")

        # Verify UTG RFI opportunities
        result = session.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE faced_raise = false) as rfi_opps,
                ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = false) / COUNT(*), 1) as rfi_pct
            FROM player_hand_summary
            WHERE player_name = 'snajd' AND position = 'UTG';
        """))
        row = result.fetchone()
        logger.info(f"\nUTG RFI check: {row[1]}/{row[0]} = {row[2]}% (should be close to 100%)")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    fix_positions()
