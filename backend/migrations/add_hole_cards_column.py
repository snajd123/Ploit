"""
Migration: Add hole_cards column to player_hand_summary

This migration:
1. Adds hole_cards VARCHAR(10) column to player_hand_summary
2. Creates index on hole_cards for better query performance
3. Backfills hole_cards from raw_hand_text for existing hands
"""

import os
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def extract_hole_cards(raw_text: str, player_name: str) -> str | None:
    """
    Extract hole cards for a specific player from raw hand text.
    Format: "Dealt to player_name [Ah Kd]"
    Returns: "AhKd" or None if not found
    """
    if not raw_text or not player_name:
        return None

    # Pattern: Dealt to player_name [card1 card2]
    pattern = rf"Dealt to {re.escape(player_name)} \[([^\]]+)\]"
    match = re.search(pattern, raw_text)

    if match:
        cards = match.group(1).strip()
        # Remove spaces: "Ah Kd" -> "AhKd"
        return cards.replace(' ', '')

    return None

def run_migration():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("=" * 60)
        print("Adding hole_cards column to player_hand_summary")
        print("=" * 60)

        # 1. Add hole_cards column
        print("\n1. Adding hole_cards column...")
        conn.execute(text("""
            ALTER TABLE player_hand_summary
            ADD COLUMN IF NOT EXISTS hole_cards VARCHAR(10);
        """))
        conn.commit()
        print("✓ Added hole_cards column")

        # 2. Create index
        print("\n2. Creating index on hole_cards...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_player_hand_summary_hole_cards
            ON player_hand_summary(hole_cards);
        """))
        conn.commit()
        print("✓ Created index")

        # 3. Backfill hole_cards from raw_hand_text
        print("\n3. Backfilling hole_cards from existing hands...")

        # Get all hands where hole_cards is null
        result = conn.execute(text("""
            SELECT phs.summary_id, phs.player_name, rh.raw_hand_text
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE phs.hole_cards IS NULL
            AND rh.raw_hand_text IS NOT NULL
        """))

        hands_to_update = list(result)
        total = len(hands_to_update)
        print(f"   Found {total} hands to process")

        updated = 0
        for i, (summary_id, player_name, raw_text) in enumerate(hands_to_update):
            if (i + 1) % 500 == 0:
                print(f"   Processing {i + 1}/{total}...")

            hole_cards = extract_hole_cards(raw_text, player_name)

            if hole_cards:
                conn.execute(text("""
                    UPDATE player_hand_summary
                    SET hole_cards = :hole_cards
                    WHERE summary_id = :summary_id
                """), {"hole_cards": hole_cards, "summary_id": summary_id})
                updated += 1

        conn.commit()
        print(f"\n✓ Updated {updated} hands with hole cards")
        print(f"✓ {total - updated} hands had no visible hole cards (opponent hands)")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)

        # Summary
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_hands,
                COUNT(hole_cards) as hands_with_cards,
                COUNT(DISTINCT player_name) as unique_players
            FROM player_hand_summary
        """))

        row = result.first()
        print(f"\nSummary:")
        print(f"  Total hands: {row[0]}")
        print(f"  Hands with hole cards: {row[1]}")
        print(f"  Hero hands (with cards): {row[1]}")
        print(f"  Opponent hands (no cards): {row[0] - row[1]}")
        print(f"  Unique players: {row[2]}")

if __name__ == "__main__":
    run_migration()
