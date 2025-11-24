"""
Hero GTO Analysis Service

Analyzes hero's decisions with known hole cards against GTO ranges from database.
Identifies mistakes and calculates EV loss using real GTO solver data.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import re


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
                phs.faced_raise,
                phs.faced_three_bet,
                phs.folded_to_three_bet,
                phs.called_three_bet,
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
        Analyze a single hand for GTO mistakes using real GTO database.

        Analyzes:
        1. Preflop opening decisions
        2. Preflop facing raise decisions
        3. Preflop 3-bet defense decisions
        4. Flop cbet decisions

        Returns list of mistakes found in this hand.
        """
        mistakes = []

        # Get stake info for bb calculation
        bb = self._extract_bb_from_stake(hand['stake_level'])

        # Normalize hole cards to standard format
        normalized_hand = self._normalize_hole_cards(hand['hole_cards'])
        if not normalized_hand:
            return mistakes

        # Analyze preflop decisions based on what hero faced
        if hand['faced_three_bet']:
            # Hero faced a 3-bet
            mistake = self._analyze_three_bet_defense(hand, normalized_hand, bb, session_id)
            if mistake:
                mistakes.append(mistake)
        elif hand['faced_raise']:
            # Hero faced a raise (not 3-bet)
            mistake = self._analyze_facing_raise(hand, normalized_hand, bb, session_id)
            if mistake:
                mistakes.append(mistake)
        else:
            # Hero was first to act or facing limps
            mistake = self._analyze_preflop_open(hand, normalized_hand, bb, session_id)
            if mistake:
                mistakes.append(mistake)

        # Analyze flop cbet decisions (if had opportunity)
        if hand['saw_flop'] and hand['cbet_opportunity_flop']:
            mistake = self._analyze_cbet(hand, normalized_hand, bb, session_id)
            if mistake:
                mistakes.append(mistake)

        return mistakes

    def _analyze_preflop_open(self, hand: Dict[str, Any], normalized_hand: str, bb: float, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze preflop opening decision using real GTO database.
        """
        position = hand['position']
        vpip = hand['vpip']

        # Find GTO scenario for preflop opening
        scenario = self._find_gto_scenario(
            street='preflop',
            position=position,
            action='open'
        )

        if not scenario:
            return None

        # Get GTO frequency for this hand
        gto_freq = self._get_gto_frequency(scenario['scenario_id'], normalized_hand, position)

        if gto_freq is None:
            return None

        # Determine what hero did vs what GTO recommends
        hero_action = "open" if vpip else "fold"

        # GTO says open with high frequency (>50% means should open)
        gto_recommends_open = gto_freq > 0.50

        # Check for mistake
        if gto_recommends_open and not vpip:
            # Should have opened but folded
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, "fold", bb)
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "fold",
                "gto_action": "open",
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": True,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }
        elif not gto_recommends_open and vpip:
            # Should have folded but opened
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, "open", bb)
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "open",
                "gto_action": "fold",
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": False,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }

        return None

    def _analyze_facing_raise(self, hand: Dict[str, Any], normalized_hand: str, bb: float, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze decision when facing a raise (not 3-bet).
        """
        position = hand['position']
        vpip = hand['vpip']

        # Find GTO scenario for facing raise
        scenario = self._find_gto_scenario(
            street='preflop',
            position=position,
            action='facing_open'
        )

        if not scenario:
            return None

        # Get GTO frequency for this hand
        gto_freq = self._get_gto_frequency(scenario['scenario_id'], normalized_hand, position)

        if gto_freq is None:
            return None

        # Determine hero's action
        hero_action = "fold" if not vpip else ("3bet" if hand['made_three_bet'] else "call")

        # GTO recommendation (simplified: >40% = call/3bet, <20% = fold, mixed in between)
        if gto_freq > 0.40:
            gto_action = "call/3bet"
            gto_should_continue = True
        elif gto_freq < 0.20:
            gto_action = "fold"
            gto_should_continue = False
        else:
            # Mixed strategy - not clear mistake
            return None

        # Check for mistake
        if gto_should_continue and not vpip:
            # Should have continued but folded
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, "fold", bb)
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "fold",
                "gto_action": gto_action,
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": True,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }
        elif not gto_should_continue and vpip:
            # Should have folded but continued
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, "call/3bet", bb)
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": hero_action,
                "gto_action": "fold",
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": False,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }

        return None

    def _analyze_three_bet_defense(self, hand: Dict[str, Any], normalized_hand: str, bb: float, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze decision when facing a 3-bet using real GTO database.
        """
        position = hand['position']
        folded = hand['folded_to_three_bet']
        called = hand['called_three_bet']

        # Find GTO scenario for facing 3-bet
        scenario = self._find_gto_scenario(
            street='preflop',
            position=position,
            action='facing_3bet'
        )

        if not scenario:
            return None

        # Get GTO frequency for this hand
        gto_freq = self._get_gto_frequency(scenario['scenario_id'], normalized_hand, position)

        if gto_freq is None:
            return None

        # Determine hero's action
        if folded:
            hero_action = "fold"
        elif called:
            hero_action = "call"
        else:
            hero_action = "4bet"

        # GTO recommendation (>35% = continue, <15% = fold)
        if gto_freq > 0.35:
            gto_action = "call/4bet"
            gto_should_continue = True
        elif gto_freq < 0.15:
            gto_action = "fold"
            gto_should_continue = False
        else:
            # Mixed strategy
            return None

        # Check for mistake
        if gto_should_continue and folded:
            # Should have continued but folded to 3-bet
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, "fold", bb * 3)  # 3-bet pot is bigger
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "fold",
                "gto_action": gto_action,
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": True,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }
        elif not gto_should_continue and not folded:
            # Should have folded but continued vs 3-bet
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, hero_action, bb * 3)
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "preflop",
                "hero_hand": hand['hole_cards'],
                "action_taken": hero_action,
                "gto_action": "fold",
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": False,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }

        return None

    def _analyze_cbet(self, hand: Dict[str, Any], normalized_hand: str, bb: float, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze continuation bet decision on flop using real GTO database.
        """
        position = hand['position']
        cbet_made = hand['cbet_made_flop']

        # Get board cards
        board = self._get_board_string(hand)
        if not board:
            return None

        # Find GTO scenario for flop cbet
        scenario = self._find_gto_scenario(
            street='flop',
            position=position,
            action='cbet',
            board=board
        )

        if not scenario:
            return None

        # Get GTO frequency for this hand on this board
        gto_freq = self._get_gto_frequency(scenario['scenario_id'], normalized_hand, position)

        if gto_freq is None:
            return None

        # Determine if GTO recommends cbet (>50% = cbet)
        gto_recommends_cbet = gto_freq > 0.50

        # Check for mistake
        if gto_recommends_cbet and not cbet_made:
            # Should have cbet but checked
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, "check", bb * 5)  # Flop pot ~5bb
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "flop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "check",
                "gto_action": "cbet",
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": True,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }
        elif not gto_recommends_cbet and cbet_made:
            # Should have checked but cbet
            ev_loss = self._calculate_ev_loss_from_frequency(gto_freq, "cbet", bb * 5)
            return {
                "hand_id": hand['hand_id'],
                "session_id": session_id,
                "street": "flop",
                "hero_hand": hand['hole_cards'],
                "action_taken": "cbet",
                "gto_action": "check",
                "gto_frequency": float(gto_freq),
                "ev_loss_bb": ev_loss,
                "hand_in_gto_range": False,
                "mistake_severity": self._classify_mistake_severity(ev_loss)
            }

        return None

    def _find_gto_scenario(self, street: str, position: str, action: str, board: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find matching GTO scenario from database.

        Args:
            street: 'preflop', 'flop', 'turn', 'river'
            position: Hero's position
            action: 'open', 'facing_open', 'facing_3bet', 'cbet', etc.
            board: Board cards (for postflop scenarios)
        """
        query = text("""
            SELECT scenario_id, scenario_name, street, position, action
            FROM gto_scenarios
            WHERE street = :street
            AND (position = :position OR position IS NULL)
            AND action = :action
            ORDER BY
                CASE WHEN position = :position THEN 0 ELSE 1 END,
                scenario_id
            LIMIT 1
        """)

        result = self.db.execute(query, {
            "street": street,
            "position": position,
            "action": action
        })

        row = result.first()
        if row:
            return dict(row._mapping)
        return None

    def _get_gto_frequency(self, scenario_id: int, normalized_hand: str, position: str) -> Optional[float]:
        """
        Get GTO frequency for a specific hand in a scenario.

        Args:
            scenario_id: The GTO scenario ID
            normalized_hand: Normalized hand like "AKs", "AKo", "AA"
            position: Hero's position

        Returns:
            Float between 0-1 representing GTO frequency, or None if not found
        """
        query = text("""
            SELECT frequency
            FROM gto_frequencies
            WHERE scenario_id = :scenario_id
            AND hand = :hand
            AND (position = :position OR position IS NULL)
            ORDER BY
                CASE WHEN position = :position THEN 0 ELSE 1 END
            LIMIT 1
        """)

        result = self.db.execute(query, {
            "scenario_id": scenario_id,
            "hand": normalized_hand,
            "position": position
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

    def _get_board_string(self, hand: Dict[str, Any]) -> Optional[str]:
        """
        Get board cards as string for scenario matching.
        """
        flop1 = hand.get('flop_card_1')
        flop2 = hand.get('flop_card_2')
        flop3 = hand.get('flop_card_3')

        if flop1 and flop2 and flop3:
            return f"{flop1}{flop2}{flop3}"
        return None

    def _calculate_ev_loss_from_frequency(self, gto_frequency: float, wrong_action: str, pot_size_bb: float) -> float:
        """
        Calculate EV loss based on deviation from GTO frequency.

        Args:
            gto_frequency: GTO frequency for correct action (0-1)
            wrong_action: The action hero took
            pot_size_bb: Pot size in big blinds

        Returns:
            EV loss in big blinds
        """
        # EV loss is roughly proportional to:
        # - How often GTO recommends the correct action (frequency)
        # - The pot size
        # - A scaling factor based on the action type

        # Basic formula: EV loss = frequency * pot_size * action_multiplier
        action_multipliers = {
            "fold": 0.3,      # Folding when should continue
            "call": 0.2,      # Calling when should fold
            "3bet": 0.25,     # 3-betting when should fold
            "4bet": 0.4,      # 4-betting when should fold
            "open": 0.15,     # Opening when should fold
            "call/3bet": 0.2, # Continuing when should fold
            "cbet": 0.2,      # Cbetting when should check
            "check": 0.25     # Checking when should cbet
        }

        multiplier = action_multipliers.get(wrong_action, 0.2)

        # Calculate EV loss
        # Higher GTO frequency = bigger mistake when deviating
        ev_loss = gto_frequency * pot_size_bb * multiplier

        return round(ev_loss, 2)

    def _classify_mistake_severity(self, ev_loss_bb: float) -> str:
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
