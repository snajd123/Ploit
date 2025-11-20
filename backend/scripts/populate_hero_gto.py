#!/usr/bin/env python3
"""
Automatically detect hero player and populate GTO analysis.

This script:
1. Scans raw_hand_text to find which player has visible hole cards (the hero)
2. Populates GTO analysis only for the hero player(s)
"""

import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional, List, Dict, Set

# Import helper functions from populate_all_player_gto
import sys
sys.path.append(os.path.dirname(__file__))

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def find_hero_players(db) -> Set[str]:
    """
    Scan hand histories to find which players have visible hole cards.

    Returns:
        Set of player names who are heroes (have visible hole cards)
    """
    print("Scanning hand histories to find hero player(s)...")
    print()

    # Sample hands to find "Dealt to" patterns
    query = text("""
        SELECT raw_hand_text
        FROM raw_hands
        WHERE raw_hand_text LIKE '%Dealt to%'
        LIMIT 100
    """)

    results = db.execute(query).fetchall()

    heroes = set()
    for row in results:
        text_content = row[0]
        if not text_content:
            continue

        # Pattern: "Dealt to {player} [{card1} {card2}]"
        matches = re.findall(r'Dealt to (\w+) \[', text_content)
        heroes.update(matches)

    return heroes


def main():
    """Main execution."""
    from populate_all_player_gto import process_player

    db = SessionLocal()

    try:
        print("=" * 80)
        print("AUTO-DETECTING HERO AND POPULATING GTO ANALYSIS")
        print("=" * 80)
        print()

        # Find hero players
        heroes = find_hero_players(db)

        if not heroes:
            print("❌ No hero players found!")
            print("   Make sure hand histories contain 'Dealt to' lines showing hole cards.")
            return

        print(f"✅ Found {len(heroes)} hero player(s): {', '.join(sorted(heroes))}")
        print()

        # Process each hero
        results = []
        for hero in sorted(heroes):
            result = process_player(db, hero, limit=1000)
            results.append(result)

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        for r in results:
            print(f"  {r['player']:20s} - {r['actions']:4d} actions, {r['scenarios']:3d} scenarios")

        print()
        print("✅ HERO GTO ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print("NOTE: Only hero players (with visible hole cards) can be analyzed.")
        print("      Opponent hole cards are not visible in hand histories.")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
