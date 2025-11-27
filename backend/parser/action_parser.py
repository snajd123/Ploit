"""
Action parsing logic for poker hands.

Parses player actions from hand history text and tracks pot sizes,
betting rounds, and aggression.
"""

import re
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import logging

from backend.parser.data_structures import Action, Player, Street, ActionType

logger = logging.getLogger(__name__)


class ActionParser:
    """
    Parses player actions from hand history text.

    Tracks pot sizes, current bets, and identifies action types.
    """

    def __init__(self, players: List[Player], small_blind: Decimal, big_blind: Decimal):
        """
        Initialize action parser.

        Args:
            players: List of players in the hand
            small_blind: Small blind amount
            big_blind: Big blind amount
        """
        self.players = {p.name: p for p in players}
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.pot = Decimal("0")
        self.current_bet = Decimal("0")
        self.player_investments: Dict[str, Decimal] = {p.name: Decimal("0") for p in players}
        self.player_stacks: Dict[str, Decimal] = {p.name: p.starting_stack for p in players}
        # Track if there's been a raise above the big blind (for RFI detection)
        self.has_preflop_raise = False

    def parse_actions(self, hand_text: str) -> List[Action]:
        """
        Parse all actions from hand history.

        Args:
            hand_text: Complete hand history text

        Returns:
            List of Action objects in chronological order
        """
        actions = []

        # Split into street sections
        sections = self._split_into_streets(hand_text)

        # Parse blinds first
        blind_actions = self._parse_blinds(sections.get('preflop', ''))
        actions.extend(blind_actions)

        # Parse preflop actions (after blinds)
        preflop_actions = self._parse_street_actions(sections.get('preflop', ''), Street.PREFLOP)
        actions.extend(preflop_actions)

        # Reset for postflop
        self.current_bet = Decimal("0")

        # Parse postflop streets
        for street_name, street_enum in [('flop', Street.FLOP), ('turn', Street.TURN), ('river', Street.RIVER)]:
            if street_name in sections:
                street_actions = self._parse_street_actions(sections[street_name], street_enum)
                actions.extend(street_actions)
                self.current_bet = Decimal("0")  # Reset bet for next street

        return actions

    def _split_into_streets(self, hand_text: str) -> Dict[str, str]:
        """
        Split hand text into street sections.

        Args:
            hand_text: Complete hand history

        Returns:
            Dictionary mapping street names to their text sections
        """
        sections = {}

        # Find preflop (including blinds which come before HOLE CARDS)
        # Extract from after player seats to FLOP or SUMMARY
        preflop_match = re.search(r'in chips\)(.*?)(?:\*\*\* FLOP \*\*\*|\*\*\* SUMMARY \*\*\*|$)',
                                  hand_text, re.DOTALL)
        if preflop_match:
            sections['preflop'] = preflop_match.group(1)

        # Find FLOP
        flop_match = re.search(r'\*\*\* FLOP \*\*\* \[[^\]]+\](.*?)(?:\*\*\* TURN \*\*\*|\*\*\* SUMMARY \*\*\*|$)',
                              hand_text, re.DOTALL)
        if flop_match:
            sections['flop'] = flop_match.group(1)

        # Find TURN
        turn_match = re.search(r'\*\*\* TURN \*\*\* \[[^\]]+\](.*?)(?:\*\*\* RIVER \*\*\*|\*\*\* SUMMARY \*\*\*|$)',
                              hand_text, re.DOTALL)
        if turn_match:
            sections['turn'] = turn_match.group(1)

        # Find RIVER
        river_match = re.search(r'\*\*\* RIVER \*\*\* \[[^\]]+\](.*?)(?:\*\*\* SHOW DOWN \*\*\*|\*\*\* SUMMARY \*\*\*|$)',
                               hand_text, re.DOTALL)
        if river_match:
            sections['river'] = river_match.group(1)

        return sections

    def _parse_blinds(self, preflop_section: str) -> List[Action]:
        """
        Parse blind posts.

        Args:
            preflop_section: Preflop text section

        Returns:
            List of blind post actions
        """
        actions = []
        blind_pattern = r'([^\n:]+): posts (small blind|big blind|small & big blinds) [\$€]?([\d.]+)'

        for match in re.finditer(blind_pattern, preflop_section):
            player_name = match.group(1).strip()
            blind_type = match.group(2)
            amount = Decimal(match.group(3))

            if player_name not in self.players:
                continue

            # Determine action type
            if 'small' in blind_type and 'big' not in blind_type:
                action_type = ActionType.POST_SB
            else:
                action_type = ActionType.POST_BB

            # Update tracking
            self.pot += amount
            self.player_investments[player_name] += amount
            self.player_stacks[player_name] -= amount

            if amount > self.current_bet:
                self.current_bet = amount

            action = Action(
                player_name=player_name,
                street=Street.PREFLOP,
                action_type=action_type,
                amount=amount,
                pot_size_before=self.pot - amount,
                pot_size_after=self.pot,
                is_aggressive=False,
                facing_bet=False,
                stack_size=self.players[player_name].starting_stack,
                is_all_in=False
            )
            actions.append(action)

        return actions

    def _parse_street_actions(self, section_text: str, street: Street) -> List[Action]:
        """
        Parse actions for a specific street.

        Args:
            section_text: Text for this street
            street: Which street (preflop, flop, turn, river)

        Returns:
            List of actions for this street
        """
        actions = []

        # Action patterns (supports both $ and € currencies)
        patterns = [
            (r'([^:]+): folds', 'fold'),
            (r'([^:]+): checks', 'check'),
            (r'([^:]+): calls [\$€]?([\d.]+)', 'call'),
            (r'([^:]+): bets [\$€]?([\d.]+)', 'bet'),
            (r'([^:]+): raises [\$€]?[\d.]+ to [\$€]?([\d.]+)', 'raise'),
            (r'Uncalled bet \([\$€]?([\d.]+)\) returned to ([^\n]+)', 'uncalled'),
        ]

        for line in section_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('***'):
                continue

            # Try each pattern
            for pattern, action_name in patterns:
                match = re.match(pattern, line)
                if match:
                    if action_name == 'uncalled':
                        # Handle uncalled bet (not really an action, but affects pot)
                        amount = Decimal(match.group(1))
                        player_name = match.group(2).strip()
                        if player_name in self.player_investments:
                            self.pot -= amount
                            self.player_investments[player_name] -= amount
                    else:
                        action = self._create_action(match, action_name, street, line)
                        if action:
                            actions.append(action)
                    break

        return actions

    def _create_action(self, match: re.Match, action_name: str, street: Street, full_line: str) -> Optional[Action]:
        """
        Create Action object from parsed data.

        Args:
            match: Regex match object
            action_name: Type of action (fold, call, bet, etc.)
            street: Current street
            full_line: Full line of text (for all-in detection)

        Returns:
            Action object or None if invalid
        """
        player_name = match.group(1).strip()

        if player_name not in self.players:
            logger.warning(f"Unknown player in action: {player_name}")
            return None

        # Check if all-in
        is_all_in = 'all-in' in full_line.lower()

        # Get amount and determine action details
        amount = Decimal("0")
        action_type = None
        is_aggressive = False

        # For preflop, facing_bet should only be True if someone RAISED (above BB)
        # For postflop, facing_bet is True if current_bet > 0
        if street == Street.PREFLOP:
            facing_bet = self.has_preflop_raise
        else:
            facing_bet = self.current_bet > Decimal("0")

        if action_name == 'fold':
            action_type = ActionType.FOLD
        elif action_name == 'check':
            action_type = ActionType.CHECK
        elif action_name == 'call':
            amount = Decimal(match.group(2))
            action_type = ActionType.CALL
        elif action_name == 'bet':
            amount = Decimal(match.group(2))
            action_type = ActionType.BET
            is_aggressive = True
        elif action_name == 'raise':
            amount = Decimal(match.group(2))
            action_type = ActionType.RAISE
            is_aggressive = True
            # Mark that there's been a preflop raise (for future actions)
            if street == Street.PREFLOP:
                self.has_preflop_raise = True

        if action_type is None:
            return None

        # Record state before action
        pot_before = self.pot
        stack_before = self.player_stacks[player_name]

        # Update state
        if amount > Decimal("0"):
            # Calculate actual amount this player needs to put in
            already_invested_this_street = self.player_investments.get(player_name, Decimal("0"))
            additional_amount = amount - already_invested_this_street

            self.pot += additional_amount
            self.player_stacks[player_name] -= additional_amount
            self.player_investments[player_name] = amount

            if amount > self.current_bet:
                self.current_bet = amount

        pot_after = self.pot

        action = Action(
            player_name=player_name,
            street=street,
            action_type=action_type,
            amount=amount,
            pot_size_before=pot_before,
            pot_size_after=pot_after,
            is_aggressive=is_aggressive,
            facing_bet=facing_bet,
            stack_size=stack_before,
            is_all_in=is_all_in
        )

        return action

    def get_preflop_aggressor(self, actions: List[Action]) -> Optional[str]:
        """
        Identify the last preflop aggressor (for cbet opportunities).

        Args:
            actions: List of all actions

        Returns:
            Name of last preflop aggressor, or None
        """
        preflop_actions = [a for a in actions if a.street == Street.PREFLOP]

        # Find last aggressive action preflop
        for action in reversed(preflop_actions):
            if action.is_aggressive and action.action_type not in [ActionType.POST_SB, ActionType.POST_BB]:
                return action.player_name

        return None
