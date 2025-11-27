"""
Boolean flag calculation for player hand summaries.

Analyzes hand actions and calculates all statistical flags for each player.
These flags are used to compute player statistics like VPIP, PFR, cbet%, etc.
"""

from decimal import Decimal
from typing import List, Dict, Optional
import logging

from backend.parser.data_structures import (
    Hand, Action, Player, PlayerHandSummaryFlags,
    Street, ActionType
)

logger = logging.getLogger(__name__)


class FlagCalculator:
    """
    Calculates boolean flags for player hand summaries.

    Analyzes all actions in a hand and determines which statistical
    flags should be set for each player.
    """

    def __init__(self, hand: Hand):
        """
        Initialize flag calculator.

        Args:
            hand: Hand object with all parsed data
        """
        self.hand = hand
        self.preflop_aggressor: Optional[str] = None

    def calculate_all_flags(self) -> Dict[str, PlayerHandSummaryFlags]:
        """
        Calculate all flags for all players in the hand.

        Returns:
            Dictionary mapping player name to their flags
        """
        flags_dict = {}

        # Initialize flags for each player
        for player in self.hand.players:
            flags = PlayerHandSummaryFlags(
                player_name=player.name,
                position=player.position
            )
            flags_dict[player.name] = flags

        # Identify preflop aggressor
        self.preflop_aggressor = self._identify_preflop_aggressor()

        # Calculate flags for each player
        for player_name in flags_dict.keys():
            self._calculate_preflop_flags(player_name, flags_dict[player_name])
            self._calculate_street_visibility(player_name, flags_dict[player_name])
            self._calculate_cbet_flags(player_name, flags_dict[player_name])
            self._calculate_facing_cbet_flags(player_name, flags_dict[player_name])
            self._calculate_check_raise_flags(player_name, flags_dict[player_name])
            self._calculate_donk_bet_flags(player_name, flags_dict[player_name])
            self._calculate_float_flags(player_name, flags_dict[player_name])
            self._calculate_steal_flags(player_name, flags_dict[player_name])
            self._calculate_showdown_flags(player_name, flags_dict[player_name])
            self._calculate_profit_loss(player_name, flags_dict[player_name])

        return flags_dict

    def _identify_preflop_aggressor(self) -> Optional[str]:
        """
        Find the last preflop aggressor (raiser).

        Returns:
            Player name of last preflop raiser, or None
        """
        preflop_actions = [a for a in self.hand.actions if a.street == Street.PREFLOP]

        for action in reversed(preflop_actions):
            if action.is_aggressive and action.action_type not in [ActionType.POST_SB, ActionType.POST_BB]:
                return action.player_name

        return None

    def _identify_first_raiser(self) -> Optional[tuple]:
        """
        Find the first raiser (opener) preflop.

        Returns:
            Tuple of (player_name, position) of first raiser, or (None, None)
        """
        preflop_actions = [a for a in self.hand.actions if a.street == Street.PREFLOP]

        for action in preflop_actions:
            if action.action_type == ActionType.RAISE and action.is_aggressive:
                player = self.hand.get_player(action.player_name)
                if player:
                    return (action.player_name, player.position)
        return (None, None)

    def _calculate_preflop_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate preflop behavior flags.

        Sets: vpip, pfr, limp, faced_raise, faced_three_bet, folded_to_three_bet,
              called_three_bet, made_three_bet, four_bet, cold_call, squeeze
        """
        preflop_actions = [a for a in self.hand.actions
                          if a.street == Street.PREFLOP and a.player_name == player_name]

        if not preflop_actions:
            return

        # Filter out blind posts
        voluntary_actions = [a for a in preflop_actions
                            if a.action_type not in [ActionType.POST_SB, ActionType.POST_BB, ActionType.POST_ANTE]]

        if not voluntary_actions:
            return

        # VPIP: Voluntarily put money in pot
        # True if called, bet, or raised (not just posted blinds)
        vpip_actions = [a for a in voluntary_actions
                       if a.action_type in [ActionType.CALL, ActionType.BET, ActionType.RAISE]]
        flags.vpip = len(vpip_actions) > 0

        # PFR: Preflop raise
        # True if raised or bet preflop
        pfr_actions = [a for a in voluntary_actions
                      if a.action_type in [ActionType.RAISE, ActionType.BET]]
        flags.pfr = len(pfr_actions) > 0

        # Limp: Called preflop without facing a raise
        # True if called but wasn't facing a bet
        limp_actions = [a for a in voluntary_actions
                       if a.action_type == ActionType.CALL and not a.facing_bet]
        flags.limp = len(limp_actions) > 0

        # Count raises in preflop
        raise_count = self._count_preflop_raises()

        # Faced raise
        faced_raise = any(a.facing_bet for a in voluntary_actions)
        flags.faced_raise = faced_raise

        # Track who opened (first raiser position) for position-specific defense
        first_raiser_name, first_raiser_pos = self._identify_first_raiser()
        if faced_raise and first_raiser_pos:
            flags.raiser_position = first_raiser_pos

        # 3-bet opportunity: player faced the first raise but didn't make it
        if raise_count >= 1:
            made_first_raise = self._player_made_raise_number(player_name, 1)
            faced_first_raise = self._player_faced_raise_number(player_name, 1)
            flags.three_bet_opportunity = faced_first_raise and not made_first_raise

        # 3-bet: Check if player made the 2nd raise
        if raise_count >= 2:
            made_3bet = self._player_made_raise_number(player_name, 2)
            flags.made_three_bet = made_3bet

            # Check if player faced a 3-bet (faced the 2nd raise)
            # Note: A player can both make a 3-bet AND face a 4-bet in the same hand
            faced_3bet = self._player_faced_raise_number(player_name, 2)
            flags.faced_three_bet = faced_3bet

            # Track who 3-bet us (position of the 2nd raiser)
            if faced_3bet:
                preflop_all = [a for a in self.hand.actions if a.street == Street.PREFLOP]
                raises = [a for a in preflop_all if a.action_type == ActionType.RAISE and a.is_aggressive]
                if len(raises) >= 2:
                    three_bettor = self.hand.get_player(raises[1].player_name)
                    if three_bettor:
                        flags.three_bettor_position = three_bettor.position

            if faced_3bet:
                # How did they respond to the 3-bet?
                # Get actions AFTER they faced the 3-bet
                preflop_all = [a for a in self.hand.actions if a.street == Street.PREFLOP]
                raises = [a for a in preflop_all if a.action_type == ActionType.RAISE and a.is_aggressive]

                if len(raises) >= 2:
                    second_raise_idx = preflop_all.index(raises[1])
                    actions_after_3bet = [a for a in preflop_all[second_raise_idx + 1:]
                                         if a.player_name == player_name and
                                         a.action_type not in [ActionType.POST_SB, ActionType.POST_BB]]

                    if actions_after_3bet:
                        last_action = actions_after_3bet[-1]
                        if last_action.action_type == ActionType.FOLD:
                            flags.folded_to_three_bet = True
                        elif last_action.action_type == ActionType.CALL:
                            flags.called_three_bet = True

        # 4-bet
        if raise_count >= 3:
            made_4bet = self._player_made_raise_number(player_name, 3)
            flags.four_bet = made_4bet

            # Check if player faced a 4-bet (faced the 3rd raise)
            # This happens when player 3-bet and then faced a 4-bet
            faced_4bet = self._player_faced_raise_number(player_name, 3)
            flags.faced_four_bet = faced_4bet

            if faced_4bet:
                # How did they respond to the 4-bet?
                preflop_all = [a for a in self.hand.actions if a.street == Street.PREFLOP]
                raises = [a for a in preflop_all if a.action_type == ActionType.RAISE and a.is_aggressive]

                if len(raises) >= 3:
                    third_raise_idx = preflop_all.index(raises[2])
                    actions_after_4bet = [a for a in preflop_all[third_raise_idx + 1:]
                                         if a.player_name == player_name and
                                         a.action_type not in [ActionType.POST_SB, ActionType.POST_BB]]

                    if actions_after_4bet:
                        last_action = actions_after_4bet[-1]
                        if last_action.action_type == ActionType.FOLD:
                            flags.folded_to_four_bet = True
                        elif last_action.action_type == ActionType.CALL:
                            flags.called_four_bet = True

        # 5-bet (4th raise)
        if raise_count >= 4:
            made_5bet = self._player_made_raise_number(player_name, 4)
            flags.five_bet = made_5bet

        # Cold call: Called a raise without having invested yet
        # (didn't post blind or wasn't in the pot yet)
        posted_blind = any(a.action_type in [ActionType.POST_SB, ActionType.POST_BB]
                          for a in preflop_actions)
        called_raise = any(a.action_type == ActionType.CALL and a.facing_bet
                          for a in voluntary_actions)
        flags.cold_call = called_raise and not posted_blind

        # Squeeze: 3-bet after there was a raise and call(s)
        # This is complex - simplified version: made 3-bet after multiple players in
        if flags.made_three_bet:
            players_before_3bet = self._count_players_before_action(player_name, ActionType.RAISE)
            flags.squeeze = players_before_3bet >= 2

    def _calculate_street_visibility(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate which streets player saw.

        Sets: saw_flop, saw_turn, saw_river
        """
        # Check if player has actions on each street
        player_actions = [a for a in self.hand.actions if a.player_name == player_name]

        # Player saw flop if they have any flop actions or later actions
        postflop_streets = [Street.FLOP, Street.TURN, Street.RIVER]
        has_postflop = any(a.street in postflop_streets for a in player_actions)

        # Also check if they didn't fold preflop
        preflop_folded = any(a.street == Street.PREFLOP and a.action_type == ActionType.FOLD
                            for a in player_actions)

        flags.saw_flop = has_postflop and not preflop_folded

        # Saw turn
        turn_river_streets = [Street.TURN, Street.RIVER]
        has_turn_river = any(a.street in turn_river_streets for a in player_actions)
        flop_folded = any(a.street == Street.FLOP and a.action_type == ActionType.FOLD
                         for a in player_actions)

        flags.saw_turn = has_turn_river and not flop_folded

        # Saw river
        has_river = any(a.street == Street.RIVER for a in player_actions)
        turn_folded = any(a.street == Street.TURN and a.action_type == ActionType.FOLD
                         for a in player_actions)

        flags.saw_river = has_river and not turn_folded

    def _calculate_cbet_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate continuation bet flags (as the aggressor).

        Sets: cbet_opportunity_*, cbet_made_*
        """
        # Only the preflop aggressor has cbet opportunities
        if player_name != self.preflop_aggressor:
            return

        if not flags.saw_flop:
            return

        # Flop cbet opportunity
        flags.cbet_opportunity_flop = True

        # Check if made cbet on flop (first to act and bet)
        flop_actions = [a for a in self.hand.actions
                       if a.street == Street.FLOP and a.player_name == player_name]
        if flop_actions:
            # Cbet if bet or raised on flop
            made_cbet_flop = any(a.action_type in [ActionType.BET, ActionType.RAISE]
                                for a in flop_actions)
            flags.cbet_made_flop = made_cbet_flop

            # Turn cbet opportunity (if made flop cbet and saw turn)
            if made_cbet_flop and flags.saw_turn:
                flags.cbet_opportunity_turn = True

                turn_actions = [a for a in self.hand.actions
                               if a.street == Street.TURN and a.player_name == player_name]
                made_cbet_turn = any(a.action_type in [ActionType.BET, ActionType.RAISE]
                                    for a in turn_actions)
                flags.cbet_made_turn = made_cbet_turn

                # River cbet opportunity
                if made_cbet_turn and flags.saw_river:
                    flags.cbet_opportunity_river = True

                    river_actions = [a for a in self.hand.actions
                                    if a.street == Street.RIVER and a.player_name == player_name]
                    made_cbet_river = any(a.action_type in [ActionType.BET, ActionType.RAISE]
                                         for a in river_actions)
                    flags.cbet_made_river = made_cbet_river

    def _calculate_facing_cbet_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate flags for facing continuation bets.

        Sets: faced_cbet_*, folded_to_cbet_*, called_cbet_*, raised_cbet_*
        """
        # Skip the preflop aggressor (they can't face their own cbet)
        if player_name == self.preflop_aggressor:
            return

        for street, street_enum in [('flop', Street.FLOP), ('turn', Street.TURN), ('river', Street.RIVER)]:
            # Get actions for this player on this street
            street_actions = [a for a in self.hand.actions
                             if a.street == street_enum and a.player_name == player_name]

            if not street_actions:
                continue

            # Check if facing a bet (likely a cbet from preflop aggressor)
            facing_bet = any(a.facing_bet for a in street_actions)

            if facing_bet:
                setattr(flags, f'faced_cbet_{street}', True)

                # How did they respond? Check in order of severity (can have multiple responses)
                # e.g., player can call then raise (check-raise), so check last action
                last_action = street_actions[-1]

                if last_action.action_type == ActionType.FOLD:
                    setattr(flags, f'folded_to_cbet_{street}', True)
                elif last_action.action_type == ActionType.CALL:
                    setattr(flags, f'called_cbet_{street}', True)
                elif last_action.action_type == ActionType.RAISE:
                    setattr(flags, f'raised_cbet_{street}', True)

    def _calculate_check_raise_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate check-raise flags.

        Sets: check_raise_opportunity_*, check_raised_*
        """
        for street_enum in [Street.FLOP, Street.TURN, Street.RIVER]:
            street_name = street_enum.value

            player_actions = [a for a in self.hand.actions
                             if a.street == street_enum and a.player_name == player_name]

            if not player_actions:
                continue

            # Check if player checked first
            checked = any(a.action_type == ActionType.CHECK for a in player_actions)

            if checked:
                # Opportunity exists if they checked
                setattr(flags, f'check_raise_opportunity_{street_name}', True)

                # Did they raise after checking?
                actions_ordered = [a for a in self.hand.actions if a.street == street_enum]
                player_check_idx = next((i for i, a in enumerate(actions_ordered)
                                        if a.player_name == player_name and a.action_type == ActionType.CHECK), None)

                if player_check_idx is not None:
                    # Check for a raise by this player after their check
                    later_actions = actions_ordered[player_check_idx + 1:]
                    raised = any(a.player_name == player_name and a.action_type == ActionType.RAISE
                                for a in later_actions)
                    setattr(flags, f'check_raised_{street_name}', raised)

    def _calculate_donk_bet_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate donk bet flags (betting into the preflop aggressor).

        Sets: donk_bet_flop, donk_bet_turn, donk_bet_river
        """
        # Can't donk if you are the aggressor
        if player_name == self.preflop_aggressor:
            return

        for street_enum in [Street.FLOP, Street.TURN, Street.RIVER]:
            street_name = street_enum.value

            # Get first action on this street
            street_actions = [a for a in self.hand.actions if a.street == street_enum]
            if not street_actions:
                continue

            first_action = street_actions[0]

            # Donk bet if this player bet/raised first on the street
            if first_action.player_name == player_name and first_action.action_type in [ActionType.BET, ActionType.RAISE]:
                setattr(flags, f'donk_bet_{street_name}', True)

    def _calculate_float_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate float flags (call flop cbet, bet when checked to later).

        Sets: float_flop
        """
        # Float: called flop cbet, then bet turn when checked to
        if not flags.called_cbet_flop:
            return

        if not flags.saw_turn:
            return

        turn_actions = [a for a in self.hand.actions if a.street == Street.TURN]
        if not turn_actions:
            return

        # Check if aggressor checked turn
        aggressor_turn_actions = [a for a in turn_actions if a.player_name == self.preflop_aggressor]
        aggressor_checked = any(a.action_type == ActionType.CHECK for a in aggressor_turn_actions)

        if aggressor_checked:
            # Did this player bet after aggressor checked?
            player_turn_actions = [a for a in turn_actions if a.player_name == player_name]
            player_bet = any(a.action_type in [ActionType.BET, ActionType.RAISE] for a in player_turn_actions)

            if player_bet:
                flags.float_flop = True

    def _calculate_steal_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate steal attempt and blind defense flags.

        Sets: steal_attempt, faced_steal, fold_to_steal, call_steal, three_bet_vs_steal
        """
        player = self.hand.get_player(player_name)
        if not player:
            return

        # Steal attempt: raise first in from CO, BTN, or SB
        steal_positions = ['CO', 'BTN', 'SB']
        if player.position in steal_positions:
            # Check if first raiser preflop
            preflop_actions = [a for a in self.hand.actions if a.street == Street.PREFLOP]
            voluntary_actions = [a for a in preflop_actions
                                if a.action_type not in [ActionType.POST_SB, ActionType.POST_BB]]

            if voluntary_actions:
                first_voluntary = voluntary_actions[0]
                if first_voluntary.player_name == player_name and first_voluntary.action_type == ActionType.RAISE:
                    flags.steal_attempt = True

        # Blind defense: in SB or BB facing a steal attempt
        if player.position in ['SB', 'BB']:
            # Check if someone attempted steal
            steal_attempted = any(self.hand.get_player(a.player_name).position in steal_positions
                                 and a.action_type == ActionType.RAISE
                                 for a in [act for act in self.hand.actions if act.street == Street.PREFLOP]
                                 if self.hand.get_player(a.player_name))

            if steal_attempted:
                flags.faced_steal = True

                player_preflop = [a for a in self.hand.actions
                                 if a.street == Street.PREFLOP and a.player_name == player_name
                                 and a.action_type not in [ActionType.POST_SB, ActionType.POST_BB]]

                if player_preflop:
                    action = player_preflop[0]
                    if action.action_type == ActionType.FOLD:
                        flags.fold_to_steal = True
                    elif action.action_type == ActionType.CALL:
                        flags.call_steal = True
                    elif action.action_type == ActionType.RAISE:
                        flags.three_bet_vs_steal = True

    def _calculate_showdown_flags(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate showdown flags.

        Sets: went_to_showdown, won_at_showdown
        """
        # Check if hand text contains SHOW DOWN
        if "*** SHOW DOWN ***" in self.hand.raw_text:
            # Check if this player showed cards (more specific pattern)
            shows_pattern = f"{player_name}: shows ["
            mucked_pattern = f"{player_name}: mucks ["

            # Player went to showdown if they showed or mucked cards
            if shows_pattern in self.hand.raw_text or mucked_pattern in self.hand.raw_text:
                flags.went_to_showdown = True
            # Also check if they saw river but didn't fold (they went to showdown passively)
            elif flags.saw_river:
                # Check if they didn't fold on river
                river_actions = [a for a in self.hand.actions
                                if a.street == Street.RIVER and a.player_name == player_name]
                folded_river = any(a.action_type == ActionType.FOLD for a in river_actions)
                if not folded_river:
                    flags.went_to_showdown = True

        # Won at showdown: check if they collected from pot
        # Check both "collected" and "wins" patterns
        collect_pattern = f"{player_name} collected"
        wins_pattern = f"{player_name} wins"
        if (collect_pattern in self.hand.raw_text or wins_pattern in self.hand.raw_text) and flags.went_to_showdown:
            flags.won_at_showdown = True

    def _calculate_profit_loss(self, player_name: str, flags: PlayerHandSummaryFlags) -> None:
        """
        Calculate profit/loss for the hand.

        Sets: won_hand, profit_loss
        """
        # Sum all amounts this player put in
        player_actions = [a for a in self.hand.actions if a.player_name == player_name]

        total_invested = Decimal("0")
        for action in player_actions:
            if action.amount > Decimal("0"):
                total_invested += action.amount

        # Check if player won (collected from pot)
        import re
        collect_pattern = rf"{re.escape(player_name)} collected \$?([\d.]+)"
        collect_match = re.search(collect_pattern, self.hand.raw_text)

        if collect_match:
            won_amount = Decimal(collect_match.group(1))
            flags.won_hand = True
            flags.profit_loss = won_amount - total_invested
        else:
            # Lost what they invested
            flags.profit_loss = -total_invested

    # Helper methods

    def _count_preflop_raises(self) -> int:
        """Count number of raises preflop"""
        preflop_actions = [a for a in self.hand.actions if a.street == Street.PREFLOP]
        raises = [a for a in preflop_actions
                 if a.action_type == ActionType.RAISE and a.is_aggressive]
        return len(raises)

    def _player_faced_raise_number(self, player_name: str, raise_num: int) -> bool:
        """Check if player faced the Nth raise (but didn't make it themselves)"""
        preflop_actions = [a for a in self.hand.actions if a.street == Street.PREFLOP]

        raises = []
        for action in preflop_actions:
            if action.action_type == ActionType.RAISE and action.is_aggressive:
                raises.append(action)

        if len(raises) < raise_num:
            return False

        nth_raise = raises[raise_num - 1]

        # If player made this raise, they didn't "face" it
        if nth_raise.player_name == player_name:
            return False

        # Check if player acted after the Nth raise
        nth_raise_idx = preflop_actions.index(nth_raise)

        player_actions_after = [a for a in preflop_actions[nth_raise_idx + 1:]
                               if a.player_name == player_name]

        return len(player_actions_after) > 0

    def _player_made_raise_number(self, player_name: str, raise_num: int) -> bool:
        """Check if player made the Nth raise"""
        preflop_actions = [a for a in self.hand.actions if a.street == Street.PREFLOP]

        raises = [a for a in preflop_actions
                 if a.action_type == ActionType.RAISE and a.is_aggressive]

        if len(raises) < raise_num:
            return False

        return raises[raise_num - 1].player_name == player_name

    def _count_players_before_action(self, player_name: str, action_type: ActionType) -> int:
        """Count how many players acted before this player's action"""
        preflop_actions = [a for a in self.hand.actions if a.street == Street.PREFLOP]

        # Find this player's action of this type
        player_action_idx = None
        for i, action in enumerate(preflop_actions):
            if action.player_name == player_name and action.action_type == action_type:
                player_action_idx = i
                break

        if player_action_idx is None:
            return 0

        # Count unique players who acted before
        players_before = set()
        for action in preflop_actions[:player_action_idx]:
            if action.action_type not in [ActionType.POST_SB, ActionType.POST_BB]:
                players_before.add(action.player_name)

        return len(players_before)
