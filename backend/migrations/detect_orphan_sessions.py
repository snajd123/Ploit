"""
Migration: Detect sessions for hands without session_id

Runs session detection for all hands that have NULL session_id.
"""

import os
import sys
from datetime import timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


class SessionDetector:
    """Inline session detector to avoid import issues."""

    def __init__(self, db, session_gap_minutes=30):
        self.db = db
        self.session_gap_minutes = session_gap_minutes

    def detect_sessions_for_player(self, player_name):
        """Detect and create sessions for a player from their hands."""
        hands = self._get_player_hands(player_name)

        if not hands:
            return []

        session_groups = self._group_hands_into_sessions(hands)

        created_sessions = []
        for hand_group in session_groups:
            session = self._create_session_from_hands(hand_group, player_name)
            if session:
                created_sessions.append(session)

        return created_sessions

    def _get_player_hands(self, player_name):
        """Get all hands for a player from player_hand_summary."""
        query = text("""
            SELECT
                phs.hand_id,
                rh.timestamp,
                rh.table_name,
                rh.stake_level,
                phs.position,
                phs.profit_loss
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE phs.player_name = :player_name
            AND phs.session_id IS NULL
            ORDER BY rh.timestamp ASC
        """)

        result = self.db.execute(query, {"player_name": player_name})
        return [dict(row._mapping) for row in result]

    def _group_hands_into_sessions(self, hands):
        """Group hands into sessions based on time gaps."""
        if not hands:
            return []

        sessions = []
        current_session = [hands[0]]

        for i in range(1, len(hands)):
            current_hand = hands[i]
            previous_hand = hands[i - 1]

            time_diff = current_hand['timestamp'] - previous_hand['timestamp']

            if time_diff > timedelta(minutes=self.session_gap_minutes):
                sessions.append(current_session)
                current_session = [current_hand]
            else:
                current_session.append(current_hand)

        if current_session:
            sessions.append(current_session)

        return sessions

    def _create_session_from_hands(self, hands, player_name):
        """Create session record from grouped hands."""
        if not hands:
            return None

        start_time = hands[0]['timestamp']
        end_time = hands[-1]['timestamp']
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        total_hands = len(hands)

        total_profit_loss = sum(float(h.get('profit_loss', 0) or 0) for h in hands)

        table_name = self._get_most_common_table(hands)
        stake_level = hands[0].get('stake_level', '')

        bb = self._extract_bb_from_stake(stake_level)
        profit_loss_bb = total_profit_loss / bb if bb > 0 else 0
        bb_100 = (profit_loss_bb / total_hands * 100) if total_hands > 0 else 0

        insert_query = text("""
            INSERT INTO sessions (
                player_name, start_time, end_time, duration_minutes,
                total_hands, profit_loss_bb, bb_100, table_stakes, table_name
            ) VALUES (
                :player_name, :start_time, :end_time, :duration_minutes,
                :total_hands, :profit_loss_bb, :bb_100, :table_stakes, :table_name
            ) RETURNING session_id
        """)

        result = self.db.execute(insert_query, {
            "player_name": player_name,
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": duration_minutes,
            "total_hands": total_hands,
            "profit_loss_bb": profit_loss_bb,
            "bb_100": bb_100,
            "table_stakes": stake_level,
            "table_name": table_name
        })

        session_id = result.scalar()

        hand_ids = [h['hand_id'] for h in hands]
        self._assign_hands_to_session(hand_ids, session_id)

        self.db.commit()

        return {
            "session_id": session_id,
            "player_name": player_name,
            "start_time": start_time,
            "end_time": end_time,
            "total_hands": total_hands,
            "profit_loss_bb": profit_loss_bb,
            "bb_100": bb_100
        }

    def _get_most_common_table(self, hands):
        """Get the most frequently occurring table name."""
        table_counts = {}
        for hand in hands:
            table = hand.get('table_name', '')
            table_counts[table] = table_counts.get(table, 0) + 1

        if not table_counts:
            return ''

        return max(table_counts, key=table_counts.get)

    def _extract_bb_from_stake(self, stake_level):
        """Extract big blind value from stake string."""
        if not stake_level:
            return 1.0

        if stake_level.startswith('NL'):
            try:
                amount = float(stake_level[2:])
                return amount / 100
            except ValueError:
                pass

        if '/' in stake_level:
            try:
                parts = stake_level.replace('€', '').replace('$', '').split('/')
                return float(parts[1])
            except (ValueError, IndexError):
                pass

        return 1.0

    def _assign_hands_to_session(self, hand_ids, session_id):
        """Update both raw_hands and player_hand_summary with session_id."""
        update_raw_hands = text("""
            UPDATE raw_hands
            SET session_id = :session_id
            WHERE hand_id = ANY(:hand_ids)
        """)

        self.db.execute(update_raw_hands, {
            "session_id": session_id,
            "hand_ids": hand_ids
        })

        update_phs = text("""
            UPDATE player_hand_summary
            SET session_id = :session_id
            WHERE hand_id = ANY(:hand_ids)
        """)

        self.db.execute(update_phs, {
            "session_id": session_id,
            "hand_ids": hand_ids
        })


def run_migration():
    """Run session detection for orphaned hands."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return False

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Check how many orphaned hands exist
        print("Step 1: Checking orphaned hands...")
        result = db.execute(text("""
            SELECT COUNT(*) FROM player_hand_summary WHERE session_id IS NULL
        """))
        orphan_phs = result.scalar()
        print(f"  player_hand_summary with NULL session_id: {orphan_phs}")

        result = db.execute(text("""
            SELECT COUNT(*) FROM raw_hands WHERE session_id IS NULL
        """))
        orphan_rh = result.scalar()
        print(f"  raw_hands with NULL session_id: {orphan_rh}")

        if orphan_phs == 0 and orphan_rh == 0:
            print("  No orphaned hands found!")
            return True

        # Get hero nicknames
        print("\nStep 2: Getting hero nicknames...")
        result = db.execute(text("SELECT nickname FROM hero_nicknames"))
        heroes = [row[0] for row in result]
        print(f"  Heroes: {heroes}")

        if not heroes:
            print("  No hero nicknames configured!")
            return False

        # Check which heroes have orphaned hands
        print("\nStep 3: Checking heroes with orphaned hands...")
        for hero in heroes:
            result = db.execute(text("""
                SELECT COUNT(*)
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                WHERE phs.player_name = :hero
                AND phs.session_id IS NULL
            """), {"hero": hero})
            count = result.scalar()
            print(f"  {hero}: {count} orphaned hands")

        # Run session detection
        print("\nStep 4: Running session detection...")
        detector = SessionDetector(db, session_gap_minutes=30)

        for hero in heroes:
            print(f"\n  Processing {hero}...")
            sessions = detector.detect_sessions_for_player(hero)
            if sessions:
                print(f"    Created {len(sessions)} sessions:")
                for s in sessions:
                    print(f"      Session {s['session_id']}: {s['total_hands']} hands, {s['profit_loss_bb']:.1f} bb")
            else:
                print(f"    No new sessions created")

        # Verify
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        result = db.execute(text("""
            SELECT COUNT(*) FROM player_hand_summary WHERE session_id IS NULL
        """))
        remaining_phs = result.scalar()
        print(f"  Remaining orphaned player_hand_summary: {remaining_phs}")

        result = db.execute(text("""
            SELECT COUNT(*) FROM raw_hands WHERE session_id IS NULL
        """))
        remaining_rh = result.scalar()
        print(f"  Remaining orphaned raw_hands: {remaining_rh}")

        # Show recent sessions
        print("\n  Recent sessions:")
        result = db.execute(text("""
            SELECT session_id, player_name, total_hands, profit_loss_bb, start_time
            FROM sessions
            ORDER BY session_id DESC
            LIMIT 5
        """))
        for row in result:
            print(f"    Session {row[0]}: {row[1]}, {row[2]} hands, {row[3]:.1f} bb, {row[4]}")

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Detect Sessions for Orphaned Hands")
    print("=" * 60)
    success = run_migration()
    sys.exit(0 if success else 1)
