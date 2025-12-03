"""
Hero GTO Analysis Service

Analyzes hero's decisions with known hole cards against GTO ranges from database.
Identifies mistakes and calculates EV loss using real GTO solver data.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from functools import lru_cache
import re
import time

# Module-level cache for session analysis results
# TTL: 60 seconds (results are cached briefly to avoid re-parsing during same request cycle)
_session_analysis_cache: Dict[int, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL = 60  # seconds


def _get_cached_analysis(session_id: int) -> Optional[Dict[str, Any]]:
    """Get cached analysis if still valid."""
    if session_id in _session_analysis_cache:
        cached_time, cached_result = _session_analysis_cache[session_id]
        if time.time() - cached_time < _CACHE_TTL:
            return cached_result
        else:
            del _session_analysis_cache[session_id]
    return None


def _set_cached_analysis(session_id: int, result: Dict[str, Any]) -> None:
    """Cache analysis result."""
    # Limit cache size to prevent memory issues
    if len(_session_analysis_cache) > 100:
        # Remove oldest entries
        oldest = sorted(_session_analysis_cache.items(), key=lambda x: x[1][0])[:50]
        for sid, _ in oldest:
            del _session_analysis_cache[sid]
    _session_analysis_cache[session_id] = (time.time(), result)


class HeroGTOAnalyzer:
    """
    Analyzes hero's play against GTO strategies using real GTO database data.
    """

    def __init__(self, db: Session):
        self.db = db

    def analyze_session(self, session_id: int) -> Dict[str, Any]:
        """
        Analyze all hero hands in a session for GTO mistakes.

        Returns:
            Dictionary with analysis results including total mistakes,
            total EV loss, and breakdown by street/position
        """
        # Check cache first
        cached = _get_cached_analysis(session_id)
        if cached is not None:
            return cached

        # Get all hero hands from session (hands with hole cards)
        hero_hands = self._get_hero_hands(session_id)

        if not hero_hands:
            result = {
                "session_id": session_id,
                "total_mistakes": 0,
                "total_ev_loss_bb": 0.0,
                "mistakes_by_street": {},
                "mistakes_by_severity": {},
                "biggest_mistakes": []
            }
            _set_cached_analysis(session_id, result)
            return result

        # Analyze each hand
        mistakes = []
        for hand in hero_hands:
            hand_mistakes = self._analyze_hand(hand, session_id)
            mistakes.extend(hand_mistakes)

        # Aggregate results
        result = self._aggregate_mistakes(mistakes, session_id)
        _set_cached_analysis(session_id, result)
        return result

    def _get_hero_hands(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Get all hands where hero has visible hole cards for this session.

        Uses fast regex extraction for hole cards instead of full parsing.
        """
        # Get all hands for this session with raw text
        query = text("""
            SELECT
                phs.hand_id,
                phs.player_name,
                phs.position,
                phs.profit_loss,
                phs.vpip,
                phs.pfr,
                phs.made_three_bet,
                phs.faced_raise,
                phs.faced_three_bet,
                phs.folded_to_three_bet,
                phs.called_three_bet,
                rh.stake_level,
                rh.timestamp,
                rh.raw_hand_text
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE phs.session_id = :session_id
            ORDER BY rh.timestamp ASC
        """)

        result = self.db.execute(query, {"session_id": session_id})
        rows = [dict(row._mapping) for row in result]

        # Fast regex pattern to extract hole cards for a player
        # Pattern: "Dealt to PlayerName [Ac Kd]" or "Dealt to PlayerName [AcKd]"
        hole_card_pattern = re.compile(r'Dealt to ([^\[]+)\s*\[([^\]]+)\]')

        hero_hands = []

        for row in rows:
            raw_text = row.get('raw_hand_text')
            if not raw_text:
                continue

            try:
                # Fast regex extraction instead of full parsing
                match = hole_card_pattern.search(raw_text)
                if not match:
                    continue

                dealt_to_player = match.group(1).strip()
                hole_cards_str = match.group(2).strip()

                # Only include if this row is for the hero player (the one dealt cards)
                if row['player_name'] == dealt_to_player:
                    # Normalize hole cards format (e.g., "Ac Kd" -> "AcKd")
                    hole_cards = hole_cards_str.replace(' ', '')
                    row['hole_cards'] = hole_cards
                    hero_hands.append(row)
            except Exception:
                continue

        return hero_hands

    def _analyze_hand(self, hand: Dict[str, Any], session_id: int) -> List[Dict[str, Any]]:
        """
        Analyze a single hand for GTO mistakes using real GTO database.

        Analyzes preflop decisions only (database has no postflop data).

        Returns list of mistakes found in this hand.
        """
        mistakes = []

        # Get stake info for bb calculation
        bb = self._extract_bb_from_stake(hand['stake_level'])

        # Normalize hole cards to standard format
        normalized_hand = self._normalize_hole_cards(hand['hole_cards'])
        if not normalized_hand:
            return mistakes

        # Get opponents for this hand
        opponents = self._get_opponents_in_hand(hand['hand_id'], hand['player_name'])

        # Analyze preflop decisions based on what hero faced
        if hand['faced_three_bet']:
            # Hero faced a 3-bet (category: facing_4bet in database)
            mistake = self._analyze_vs_three_bet(hand, normalized_hand, bb, session_id, opponents)
            if mistake:
                mistakes.append(mistake)
        elif hand['faced_raise']:
            # Hero faced an open (category: defense + facing_3bet in database)
            mistake = self._analyze_vs_open(hand, normalized_hand, bb, session_id, opponents)
            if mistake:
                mistakes.append(mistake)
        else:
            # Hero was first to act (category: opening in database)
            mistake = self._analyze_opening(hand, normalized_hand, bb, session_id, opponents)
            if mistake:
                mistakes.append(mistake)

        return mistakes

    def _get_opponents_in_hand(self, hand_id: int, hero_name: str) -> List[str]:
        """
        Get list of opponent names in this hand.
        """
        query = text("""
            SELECT DISTINCT player_name
            FROM player_hand_summary
            WHERE hand_id = :hand_id
            AND player_name != :hero_name
            ORDER BY player_name
        """)

        result = self.db.execute(query, {"hand_id": hand_id, "hero_name": hero_name})
        return [row[0] for row in result]

    def _get_raiser_position(self, hand_id: int, hero_name: str) -> Optional[str]:
        """
        Get position of the player who opened (pfr but not 3-bet).
        """
        query = text("""
            SELECT position
            FROM player_hand_summary
            WHERE hand_id = :hand_id
            AND player_name != :hero_name
            AND pfr = true
            AND made_three_bet = false
            LIMIT 1
        """)

        result = self.db.execute(query, {"hand_id": hand_id, "hero_name": hero_name})
        row = result.fetchone()
        return row[0] if row else None

    def _get_three_bettor_position(self, hand_id: int, hero_name: str) -> Optional[str]:
        """
        Get position of the player who 3-bet.
        """
        query = text("""
            SELECT position
            FROM player_hand_summary
            WHERE hand_id = :hand_id
            AND player_name != :hero_name
            AND made_three_bet = true
            LIMIT 1
        """)

        result = self.db.execute(query, {"hand_id": hand_id, "hero_name": hero_name})
        row = result.fetchone()
        return row[0] if row else None

    def _analyze_opening(self, hand: Dict[str, Any], normalized_hand: str, bb: float, session_id: int, opponents: List[str]) -> Optional[Dict[str, Any]]:
        """
        Analyze preflop opening decision using real GTO database.
        """
        position = hand['position']
        vpip = hand['vpip']

        # Find opening scenario(s) for this position
        # SB has separate raise/limp scenarios that need to be combined
        query = text("""
            SELECT scenario_id, action
            FROM gto_scenarios
            WHERE category = 'opening'
            AND position = :position
        """)

        result = self.db.execute(query, {"position": position})
        rows = result.fetchall()

        if not rows:
            return None

        # Sum frequencies across all opening actions (raise + limp for SB)
        # Use raw hole cards format (e.g., "KhQd") for database lookup, not normalized type ("KQo")
        raw_hand = hand['hole_cards'].replace(' ', '') if hand.get('hole_cards') else None
        gto_freq = 0.0
        for row in rows:
            scenario_id = row[0]
            freq = self._get_hand_frequency(scenario_id, raw_hand) if raw_hand else None
            if freq is not None:
                gto_freq += freq

        # Determine mistake
        # GTO says open with frequency > 50%
        gto_recommends_open = gto_freq > 0.50

        if gto_recommends_open and not vpip:
            # Should have opened but folded
            ev_loss = gto_freq * bb * 0.3
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "fold",
                "gto_action": "open",
                "gto_frequency": round(gto_freq, 3),
                "ev_loss_bb": round(ev_loss, 2),
                "hand_in_gto_range": True,
                "mistake_severity": self._classify_severity(ev_loss),
                "opponents": ", ".join(opponents) if opponents else "None",
                "timestamp": str(hand.get('timestamp', '')),
                "position": position,
                "scenario": f"{position} open"
            }
        elif not gto_recommends_open and vpip:
            # Should have folded but opened
            # EV loss is inversely related to frequency (opening 0% hand is worse than opening 20% hand)
            ev_loss = (1.0 - gto_freq) * bb * 0.15
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "open",
                "gto_action": "fold",
                "gto_frequency": round(gto_freq, 3),
                "ev_loss_bb": round(ev_loss, 2),
                "hand_in_gto_range": False,
                "mistake_severity": self._classify_severity(ev_loss),
                "opponents": ", ".join(opponents) if opponents else "None",
                "timestamp": str(hand.get('timestamp', '')),
                "position": position,
                "scenario": f"{position} open"
            }

        return None

    def _analyze_vs_open(self, hand: Dict[str, Any], normalized_hand: str, bb: float, session_id: int, opponents: List[str]) -> Optional[Dict[str, Any]]:
        """
        Analyze decision when facing an open.
        Need to check both "defense" (fold/call) and "facing_3bet" (3bet) categories.
        """
        position = hand['position']
        vpip = hand['vpip']
        made_three_bet = hand['made_three_bet']

        # Get all scenarios for facing open from this position
        query = text("""
            SELECT scenario_id, action, category
            FROM gto_scenarios
            WHERE position = :position
            AND category IN ('defense', 'facing_3bet')
            ORDER BY scenario_id
        """)

        result = self.db.execute(query, {"position": position})
        scenarios = [dict(row._mapping) for row in result]

        if not scenarios:
            return None

        # Get frequencies for each action
        # Use raw hole cards format (e.g., "KhQd") for database lookup
        raw_hand = hand['hole_cards'].replace(' ', '') if hand.get('hole_cards') else None
        action_frequencies = {}
        for scenario in scenarios:
            freq = self._get_hand_frequency(scenario['scenario_id'], raw_hand) if raw_hand else None
            if freq is None:
                freq = 0.0

            action = scenario['action']
            action_frequencies[action] = freq

        # Determine GTO action (highest frequency)
        if not action_frequencies:
            return None

        gto_action = max(action_frequencies, key=action_frequencies.get)
        gto_freq = action_frequencies[gto_action]

        # Determine hero's action
        if not vpip:
            hero_action = "fold"
        elif made_three_bet:
            hero_action = "3bet"
        else:
            hero_action = "call"

        # Check for mistake
        if gto_action != hero_action and gto_freq > 0.40:
            # Clear mistake: GTO recommends different action with >40% frequency
            ev_loss = gto_freq * bb * 0.25
            # Build scenario description with raiser's position
            raiser_pos = self._get_raiser_position(hand['hand_id'], hand['player_name'])
            scenario_desc = f"{position} vs {raiser_pos or 'Unknown'} open"

            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": hero_action,
                "gto_action": gto_action,
                "gto_frequency": round(gto_freq, 3),
                "ev_loss_bb": round(ev_loss, 2),
                "hand_in_gto_range": gto_freq > 0.20,
                "mistake_severity": self._classify_severity(ev_loss),
                "opponents": ", ".join(opponents) if opponents else "None",
                "timestamp": str(hand.get('timestamp', '')),
                "position": position,
                "scenario": scenario_desc
            }

        return None

    def _analyze_vs_three_bet(self, hand: Dict[str, Any], normalized_hand: str, bb: float, session_id: int, opponents: List[str]) -> Optional[Dict[str, Any]]:
        """
        Analyze decision when facing a 3-bet.
        Category "facing_4bet" in database (confusing naming).
        """
        position = hand['position']
        folded = hand['folded_to_three_bet']
        called = hand['called_three_bet']

        # Get all scenarios for facing 3-bet from this position
        query = text("""
            SELECT scenario_id, action
            FROM gto_scenarios
            WHERE position = :position
            AND category = 'facing_4bet'
            ORDER BY scenario_id
        """)

        result = self.db.execute(query, {"position": position})
        scenarios = [dict(row._mapping) for row in result]

        if not scenarios:
            return None

        # Get frequencies for each action
        # Use raw hole cards format (e.g., "KhQd") for database lookup
        raw_hand = hand['hole_cards'].replace(' ', '') if hand.get('hole_cards') else None
        action_frequencies = {}
        for scenario in scenarios:
            freq = self._get_hand_frequency(scenario['scenario_id'], raw_hand) if raw_hand else None
            if freq is None:
                freq = 0.0

            action = scenario['action']
            action_frequencies[action] = freq

        if not action_frequencies:
            return None

        # Determine GTO action (highest frequency)
        gto_action = max(action_frequencies, key=action_frequencies.get)
        gto_freq = action_frequencies[gto_action]

        # Determine hero's action
        if folded:
            hero_action = "fold"
        elif called:
            hero_action = "call"
        else:
            hero_action = "4bet"

        # Check for mistake
        if gto_action != hero_action and gto_freq > 0.35:
            # Clear mistake facing 3-bet
            ev_loss = gto_freq * bb * 3 * 0.30  # Bigger pot
            # Build scenario description with 3-bettor's position
            three_bettor_pos = self._get_three_bettor_position(hand['hand_id'], hand['player_name'])
            scenario_desc = f"{position} vs {three_bettor_pos or 'Unknown'} 3-bet"

            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": hero_action,
                "gto_action": gto_action,
                "gto_frequency": round(gto_freq, 3),
                "ev_loss_bb": round(ev_loss, 2),
                "hand_in_gto_range": gto_freq > 0.15,
                "mistake_severity": self._classify_severity(ev_loss),
                "opponents": ", ".join(opponents) if opponents else "None",
                "timestamp": str(hand.get('timestamp', '')),
                "position": position,
                "scenario": scenario_desc
            }

        return None

    def _get_hand_frequency(self, scenario_id: int, normalized_hand: str) -> Optional[float]:
        """
        Get GTO frequency for a specific hand in a scenario.

        Returns:
            Float between 0-1, or None if hand not found (should treat as 0.0)
        """
        query = text("""
            SELECT frequency
            FROM gto_frequencies
            WHERE scenario_id = :scenario_id
            AND hand = :hand
            LIMIT 1
        """)

        result = self.db.execute(query, {
            "scenario_id": scenario_id,
            "hand": normalized_hand
        })

        row = result.first()
        if row:
            return float(row[0])
        return None

    def _normalize_hole_cards(self, hole_cards: str) -> Optional[str]:
        """
        Convert hole cards from format like "AhKd" to "AKs" or "AKo".

        Args:
            hole_cards: Raw hole cards like "AhKd", "QsQc", "7c2d"

        Returns:
            Normalized format: "AKs" (suited), "AKo" (offsuit), "AA" (pair)
        """
        if not hole_cards or len(hole_cards) < 4:
            return None

        # Parse rank and suit
        rank1 = hole_cards[0]
        suit1 = hole_cards[1]
        rank2 = hole_cards[2]
        suit2 = hole_cards[3]

        # Rank order for comparison
        rank_order = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
                     '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}

        val1 = rank_order.get(rank1, 0)
        val2 = rank_order.get(rank2, 0)

        # Pair
        if rank1 == rank2:
            return f"{rank1}{rank2}"

        # Put higher rank first
        if val1 > val2:
            high_rank = rank1
            low_rank = rank2
        else:
            high_rank = rank2
            low_rank = rank1

        # Check if suited
        suited = suit1 == suit2

        return f"{high_rank}{low_rank}{'s' if suited else 'o'}"

    def _classify_severity(self, ev_loss_bb: float) -> str:
        """
        Classify mistake severity based on EV loss.
        """
        if ev_loss_bb >= 2.0:
            return "major"
        elif ev_loss_bb >= 0.8:
            return "moderate"
        else:
            return "minor"

    def _extract_bb_from_stake(self, stake_level: str) -> float:
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
                parts = stake_level.split('/')
                return float(parts[1])
            except (ValueError, IndexError):
                pass

        return 1.0

    def _aggregate_mistakes(self, mistakes: List[Dict[str, Any]], session_id: int) -> Dict[str, Any]:
        """
        Aggregate mistakes into summary statistics.
        """
        if not mistakes:
            return {
                "session_id": session_id,
                "total_mistakes": 0,
                "total_ev_loss_bb": 0.0,
                "mistakes_by_street": {},
                "mistakes_by_severity": {},
                "biggest_mistakes": []
            }

        # Note: _store_mistakes disabled - hero_gto_mistakes table was dropped
        # self._store_mistakes(mistakes)

        # Calculate aggregates
        total_ev_loss = sum(m.get('ev_loss_bb', 0) for m in mistakes)

        mistakes_by_street = {}
        for m in mistakes:
            street = m.get('street', 'unknown')
            mistakes_by_street[street] = mistakes_by_street.get(street, 0) + 1

        mistakes_by_severity = {}
        for m in mistakes:
            severity = m.get('mistake_severity', 'unknown')
            mistakes_by_severity[severity] = mistakes_by_severity.get(severity, 0) + 1

        # Get biggest mistakes
        biggest = sorted(mistakes, key=lambda m: m.get('ev_loss_bb', 0), reverse=True)[:5]

        return {
            "session_id": session_id,
            "total_mistakes": len(mistakes),
            "total_ev_loss_bb": round(total_ev_loss, 2),
            "mistakes_by_street": mistakes_by_street,
            "mistakes_by_severity": mistakes_by_severity,
            "biggest_mistakes": biggest
        }

    def _store_mistakes(self, mistakes: List[Dict[str, Any]]):
        """
        Store mistakes in hero_gto_mistakes table.
        """
        if not mistakes:
            return

        session_id = mistakes[0]['session_id']

        # Delete existing mistakes for this session
        delete_query = text("""
            DELETE FROM hero_gto_mistakes
            WHERE session_id = :session_id
        """)
        self.db.execute(delete_query, {"session_id": session_id})

        # Insert new mistakes
        insert_query = text("""
            INSERT INTO hero_gto_mistakes (
                hand_id, session_id, street, hero_hand, action_taken,
                gto_action, gto_frequency, ev_loss_bb, hand_in_gto_range, mistake_severity
            ) VALUES (
                :hand_id, :session_id, :street, :hero_hand, :action_taken,
                :gto_action, :gto_frequency, :ev_loss_bb, :hand_in_gto_range, :mistake_severity
            )
        """)

        for mistake in mistakes:
            self.db.execute(insert_query, mistake)

        self.db.commit()
