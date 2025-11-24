"""
Hero GTO Analysis Service

Analyzes hero's decisions with known hole cards against GTO ranges.
Identifies mistakes and calculates EV loss.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from decimal import Decimal
import re


class HeroGTOAnalyzer:
    """
    Analyzes hero's play against GTO strategies for a session.
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
        # Get all hero hands from session (hands with hole cards)
        hero_hands = self._get_hero_hands(session_id)

        if not hero_hands:
            return {
                "session_id": session_id,
                "total_mistakes": 0,
                "total_ev_loss_bb": 0.0,
                "mistakes_by_street": {},
                "mistakes_by_severity": {},
                "biggest_mistakes": []
            }

        # Analyze each hand
        mistakes = []
        for hand in hero_hands:
            hand_mistakes = self._analyze_hand(hand, session_id)
            mistakes.extend(hand_mistakes)

        # Aggregate results
        return self._aggregate_mistakes(mistakes, session_id)

    def _get_hero_hands(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Get all hands where hero has visible hole cards for this session.
        """
        query = text("""
            SELECT
                phs.hand_id,
                phs.player_name,
                phs.position,
                phs.hole_cards,
                phs.profit_loss,
                phs.vpip,
                phs.pfr,
                phs.made_three_bet,
                phs.faced_three_bet,
                phs.folded_to_three_bet,
                phs.saw_flop,
                phs.cbet_made_flop,
                phs.cbet_opportunity_flop,
                rh.stake_level,
                rh.flop_card_1,
                rh.flop_card_2,
                rh.flop_card_3,
                rh.turn_card,
                rh.river_card
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE phs.session_id = :session_id
            AND phs.hole_cards IS NOT NULL
            ORDER BY rh.timestamp ASC
        """)

        result = self.db.execute(query, {"session_id": session_id})
        return [dict(row._mapping) for row in result]

    def _analyze_hand(self, hand: Dict[str, Any], session_id: int) -> List[Dict[str, Any]]:
        """
        Analyze a single hand for GTO mistakes.

        For now, this is a simplified analysis focusing on:
        1. Preflop VPIP decisions
        2. Preflop 3-bet decisions
        3. Flop cbet decisions

        Returns list of mistakes found in this hand.
        """
        mistakes = []

        # Get stake info for bb calculation
        bb = self._extract_bb_from_stake(hand['stake_level'])

        # Analyze preflop decisions
        preflop_mistake = self._analyze_preflop(hand, bb)
        if preflop_mistake:
            preflop_mistake['session_id'] = session_id
            mistakes.append(preflop_mistake)

        # Analyze 3-bet decisions (if faced 3-bet)
        if hand['faced_three_bet']:
            three_bet_mistake = self._analyze_three_bet_defense(hand, bb)
            if three_bet_mistake:
                three_bet_mistake['session_id'] = session_id
                mistakes.append(three_bet_mistake)

        # Analyze flop cbet decisions (if had opportunity)
        if hand['saw_flop'] and hand['cbet_opportunity_flop']:
            cbet_mistake = self._analyze_cbet(hand, bb)
            if cbet_mistake:
                cbet_mistake['session_id'] = session_id
                mistakes.append(cbet_mistake)

        return mistakes

    def _analyze_preflop(self, hand: Dict[str, Any], bb: float) -> Optional[Dict[str, Any]]:
        """
        Analyze preflop VPIP decision.

        Simplified logic:
        - Premium hands (AA, KK, QQ, AK) should always VPIP
        - Trash hands (72o, 83o, etc.) should rarely VPIP
        """
        hole_cards = hand['hole_cards']
        vpip = hand['vpip']
        position = hand['position']

        hand_strength = self._classify_hand_strength(hole_cards)

        # Premium hands that folded preflop = mistake
        if hand_strength == 'premium' and not vpip:
            return {
                "hand_id": hand['hand_id'],
                "street": "preflop",
                "hero_hand": hole_cards,
                "action_taken": "fold",
                "gto_action": "raise/call",
                "gto_frequency": 1.0,
                "ev_loss_bb": 1.5,  # Estimated
                "hand_in_gto_range": True,
                "mistake_severity": "major"
            }

        # Trash hands that VPIP'd = potential mistake (position dependent)
        if hand_strength == 'trash' and vpip and position in ['UTG', 'MP']:
            return {
                "hand_id": hand['hand_id'],
                "street": "preflop",
                "hero_hand": hole_cards,
                "action_taken": "call/raise",
                "gto_action": "fold",
                "gto_frequency": 0.95,
                "ev_loss_bb": 0.5,  # Estimated
                "hand_in_gto_range": False,
                "mistake_severity": "minor"
            }

        return None

    def _analyze_three_bet_defense(self, hand: Dict[str, Any], bb: float) -> Optional[Dict[str, Any]]:
        """
        Analyze facing 3-bet decision.

        Simplified: Premium hands should not fold to 3-bet
        """
        hole_cards = hand['hole_cards']
        folded = hand['folded_to_three_bet']

        hand_strength = self._classify_hand_strength(hole_cards)

        # Premium hands that folded to 3-bet = mistake
        if hand_strength == 'premium' and folded:
            return {
                "hand_id": hand['hand_id'],
                "street": "preflop",
                "hero_hand": hole_cards,
                "action_taken": "fold",
                "gto_action": "4-bet/call",
                "gto_frequency": 0.95,
                "ev_loss_bb": 2.0,  # Bigger mistake
                "hand_in_gto_range": True,
                "mistake_severity": "major"
            }

        return None

    def _analyze_cbet(self, hand: Dict[str, Any], bb: float) -> Optional[Dict[str, Any]]:
        """
        Analyze continuation bet decision on flop.

        Simplified: If you were preflop aggressor and didn't cbet,
        check if board favors your range.
        """
        # This is a placeholder - full implementation would check board texture
        # and range advantage
        return None

    def _classify_hand_strength(self, hole_cards: str) -> str:
        """
        Classify hand into strength categories.

        Args:
            hole_cards: e.g., "AhKd", "7c2d"

        Returns:
            'premium', 'strong', 'medium', 'weak', or 'trash'
        """
        if not hole_cards or len(hole_cards) < 4:
            return 'unknown'

        # Parse cards
        rank1 = hole_cards[0]
        rank2 = hole_cards[2]

        # Define rank values
        rank_values = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
                      '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}

        val1 = rank_values.get(rank1, 0)
        val2 = rank_values.get(rank2, 0)

        # Check if pair
        is_pair = rank1 == rank2

        # Premium: AA, KK, QQ, AK
        if is_pair and val1 >= 12:  # QQ+
            return 'premium'
        if sorted([val1, val2]) == [13, 14]:  # AK
            return 'premium'

        # Strong: JJ, TT, AQ, AJ
        if is_pair and val1 >= 10:
            return 'strong'
        if 14 in [val1, val2] and max(val1, val2) >= 11:
            return 'strong'

        # Weak/Trash: Low cards
        if max(val1, val2) <= 7:
            return 'trash'
        if max(val1, val2) <= 9 and min(val1, val2) <= 5:
            return 'trash'

        return 'medium'

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

        # Store mistakes in database
        self._store_mistakes(mistakes)

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
        # First, delete existing mistakes for these hands to avoid duplicates
        if not mistakes:
            return

        session_id = mistakes[0]['session_id']

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
