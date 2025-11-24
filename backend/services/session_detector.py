"""
Session Detection Service

Automatically groups hands into sessions based on time proximity.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

class SessionDetector:
    """
    Detects and creates sessions from uploaded hands.
    """

    def __init__(self, db: Session, session_gap_minutes: int = 30):
        """
        Initialize session detector.

        Args:
            db: Database session
            session_gap_minutes: Gap in minutes to consider new session (default: 30)
        """
        self.db = db
        self.session_gap_minutes = session_gap_minutes

    def detect_sessions_for_player(self, player_name: str) -> List[Dict[str, Any]]:
        """
        Detect and create sessions for a player from their hands.

        Returns list of created session IDs with metadata.
        """
        # Get all hands for player ordered by timestamp
        hands = self._get_player_hands(player_name)

        if not hands:
            return []

        # Group hands into sessions
        session_groups = self._group_hands_into_sessions(hands)

        # Create session records in database
        created_sessions = []
        for hand_group in session_groups:
            session = self._create_session_from_hands(hand_group, player_name)
            created_sessions.append(session)

        return created_sessions

    def _get_player_hands(self, player_name: str) -> List[Dict[str, Any]]:
        """
        Get all hands for a player from player_hand_summary.
        """
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

    def _group_hands_into_sessions(self, hands: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group hands into sessions based on time gaps.
        """
        if not hands:
            return []

        sessions = []
        current_session = [hands[0]]

        for i in range(1, len(hands)):
            current_hand = hands[i]
            previous_hand = hands[i - 1]

            time_diff = current_hand['timestamp'] - previous_hand['timestamp']

            # If gap is too large, start new session
            if time_diff > timedelta(minutes=self.session_gap_minutes):
                sessions.append(current_session)
                current_session = [current_hand]
            else:
                current_session.append(current_hand)

        # Add final session
        if current_session:
            sessions.append(current_session)

        return sessions

    def _create_session_from_hands(self, hands: List[Dict[str, Any]], player_name: str) -> Dict[str, Any]:
        """
        Create session record from grouped hands.
        """
        if not hands:
            return None

        start_time = hands[0]['timestamp']
        end_time = hands[-1]['timestamp']
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        total_hands = len(hands)

        # Calculate profit/loss
        total_profit_loss = sum(h.get('profit_loss', 0) or 0 for h in hands)

        # Get table info from most common table
        table_name = self._get_most_common_table(hands)
        stake_level = hands[0].get('stake_level', '')

        # Extract stake amount for bb calculation
        bb = self._extract_bb_from_stake(stake_level)
        profit_loss_bb = total_profit_loss / bb if bb > 0 else 0
        bb_100 = (profit_loss_bb / total_hands * 100) if total_hands > 0 else 0

        # Insert session
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

        # Update hand records with session_id
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

    def _get_most_common_table(self, hands: List[Dict[str, Any]]) -> str:
        """Get the most frequently occurring table name."""
        table_counts = {}
        for hand in hands:
            table = hand.get('table_name', '')
            table_counts[table] = table_counts.get(table, 0) + 1

        if not table_counts:
            return ''

        return max(table_counts, key=table_counts.get)

    def _extract_bb_from_stake(self, stake_level: str) -> float:
        """
        Extract big blind value from stake string.
        Examples: "NL50" -> 0.50, "NL200" -> 2.00, "1/2" -> 2.00
        """
        if not stake_level:
            return 1.0

        # Handle NLxx format
        if stake_level.startswith('NL'):
            try:
                amount = float(stake_level[2:])
                return amount / 100  # NL50 = 0.50 bb
            except ValueError:
                pass

        # Handle x/y format
        if '/' in stake_level:
            try:
                parts = stake_level.split('/')
                return float(parts[1])
            except (ValueError, IndexError):
                pass

        return 1.0  # Default

    def _assign_hands_to_session(self, hand_ids: List[int], session_id: int):
        """
        Update raw_hands and player_hand_summary with session_id.
        """
        # Update raw_hands
        update_raw_hands = text("""
            UPDATE raw_hands
            SET session_id = :session_id
            WHERE hand_id = ANY(:hand_ids)
        """)

        self.db.execute(update_raw_hands, {
            "session_id": session_id,
            "hand_ids": hand_ids
        })

        # Update player_hand_summary
        update_phs = text("""
            UPDATE player_hand_summary
            SET session_id = :session_id
            WHERE hand_id = ANY(:hand_ids)
        """)

        self.db.execute(update_phs, {
            "session_id": session_id,
            "hand_ids": hand_ids
        })

    def detect_all_sessions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect sessions for all players who have hands without session_id.
        """
        # Get all players with unassigned hands
        query = text("""
            SELECT DISTINCT player_name
            FROM player_hand_summary
            WHERE session_id IS NULL
        """)

        result = self.db.execute(query)
        players = [row[0] for row in result]

        all_sessions = {}
        for player in players:
            sessions = self.detect_sessions_for_player(player)
            if sessions:
                all_sessions[player] = sessions

        return all_sessions
