"""
Data structures for poker hand parsing.

These classes represent the parsed components of a poker hand and are used
throughout the parsing pipeline before being converted to database records.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from enum import Enum


class Street(Enum):
    """Poker betting streets"""
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(Enum):
    """Player action types"""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all-in"
    POST_SB = "post_sb"
    POST_BB = "post_bb"
    POST_ANTE = "post_ante"


class Position(Enum):
    """Player positions at the table"""
    BTN = "BTN"  # Button
    SB = "SB"    # Small Blind
    BB = "BB"    # Big Blind
    UTG = "UTG"  # Under the Gun
    UTG1 = "UTG+1"
    UTG2 = "UTG+2"
    MP = "MP"    # Middle Position
    HJ = "HJ"    # Hijack
    CO = "CO"    # Cutoff


@dataclass
class Player:
    """
    Represents a player in a hand.

    Attributes:
        name: Player's screen name
        seat_number: Seat number (1-9)
        position: Position relative to button
        starting_stack: Stack size at start of hand
        hole_cards: Player's hole cards if shown (optional)
    """
    name: str
    seat_number: int
    position: Optional[str] = None
    starting_stack: Decimal = Decimal("0")
    hole_cards: Optional[str] = None

    def __repr__(self) -> str:
        return f"Player({self.name}, {self.position}, ${self.starting_stack})"


@dataclass
class Action:
    """
    Represents a single action in a hand.

    Attributes:
        player_name: Name of player taking action
        street: Which street the action occurred on
        action_type: Type of action (fold, call, raise, etc.)
        amount: Amount bet/raised/called (0 for check/fold)
        pot_size_before: Pot size before this action
        pot_size_after: Pot size after this action
        is_aggressive: True if bet or raise
        facing_bet: True if action was in response to a bet
        stack_size: Player's stack before this action
        is_all_in: True if action was all-in
    """
    player_name: str
    street: Street
    action_type: ActionType
    amount: Decimal = Decimal("0")
    pot_size_before: Decimal = Decimal("0")
    pot_size_after: Decimal = Decimal("0")
    is_aggressive: bool = False
    facing_bet: bool = False
    stack_size: Decimal = Decimal("0")
    is_all_in: bool = False

    def __repr__(self) -> str:
        return f"Action({self.player_name}, {self.street.value}, {self.action_type.value}, ${self.amount})"


@dataclass
class PlayerHandSummaryFlags:
    """
    Boolean flags for a player's activity in a single hand.

    These flags are used to calculate statistics and are stored in the
    player_hand_summary database table.
    """
    # Basic info
    player_name: str
    position: Optional[str] = None

    # Preflop flags
    vpip: bool = False
    pfr: bool = False
    limp: bool = False
    faced_raise: bool = False
    three_bet_opportunity: bool = False
    faced_three_bet: bool = False
    folded_to_three_bet: bool = False
    called_three_bet: bool = False
    made_three_bet: bool = False
    four_bet: bool = False
    cold_call: bool = False
    squeeze: bool = False

    # Position-specific tracking
    raiser_position: Optional[str] = None  # Position of the first raiser (opener)

    # Facing 4-bet tracking
    faced_four_bet: bool = False
    folded_to_four_bet: bool = False
    called_four_bet: bool = False
    five_bet: bool = False

    # Street visibility
    saw_flop: bool = False
    saw_turn: bool = False
    saw_river: bool = False

    # Continuation bet opportunities (as aggressor)
    cbet_opportunity_flop: bool = False
    cbet_made_flop: bool = False
    cbet_opportunity_turn: bool = False
    cbet_made_turn: bool = False
    cbet_opportunity_river: bool = False
    cbet_made_river: bool = False

    # Facing continuation bets
    faced_cbet_flop: bool = False
    folded_to_cbet_flop: bool = False
    called_cbet_flop: bool = False
    raised_cbet_flop: bool = False

    faced_cbet_turn: bool = False
    folded_to_cbet_turn: bool = False
    called_cbet_turn: bool = False
    raised_cbet_turn: bool = False

    faced_cbet_river: bool = False
    folded_to_cbet_river: bool = False
    called_cbet_river: bool = False
    raised_cbet_river: bool = False

    # Check-raise opportunities
    check_raise_opportunity_flop: bool = False
    check_raised_flop: bool = False
    check_raise_opportunity_turn: bool = False
    check_raised_turn: bool = False
    check_raise_opportunity_river: bool = False
    check_raised_river: bool = False

    # Donk bets
    donk_bet_flop: bool = False
    donk_bet_turn: bool = False
    donk_bet_river: bool = False

    # Float plays
    float_flop: bool = False

    # Steal and blind defense
    steal_attempt: bool = False
    faced_steal: bool = False
    fold_to_steal: bool = False
    call_steal: bool = False
    three_bet_vs_steal: bool = False

    # Showdown
    went_to_showdown: bool = False
    won_at_showdown: bool = False
    showed_bluff: bool = False

    # Hand result
    won_hand: bool = False
    profit_loss: Decimal = Decimal("0")


@dataclass
class Hand:
    """
    Represents a complete poker hand with all its data.

    This is the main data structure that holds all parsed information
    from a hand history.

    Attributes:
        hand_id: Unique PokerStars hand ID
        timestamp: When the hand was played
        table_name: Name of the table
        stake_level: Stakes (e.g., 'NL50', 'NL100')
        game_type: Game format (e.g., '6-max', '9-max')
        button_seat: Seat number of the button
        players: List of players in the hand
        actions: All actions taken in the hand
        board_cards: Community cards (flop, turn, river)
        pot_size: Final pot size
        rake: Rake taken by site
        raw_text: Original hand history text
        player_flags: Calculated boolean flags for each player
    """
    hand_id: int
    timestamp: datetime
    table_name: str
    stake_level: str
    game_type: str
    button_seat: int
    players: List[Player] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    board_cards: Dict[str, str] = field(default_factory=dict)  # {'flop': 'Ah 7c 3d', 'turn': 'Ks', ...}
    pot_size: Decimal = Decimal("0")
    rake: Decimal = Decimal("0")
    raw_text: str = ""
    player_flags: Dict[str, PlayerHandSummaryFlags] = field(default_factory=dict)

    def get_player(self, player_name: str) -> Optional[Player]:
        """Get player by name"""
        for player in self.players:
            if player.name == player_name:
                return player
        return None

    def get_actions_for_street(self, street: Street) -> List[Action]:
        """Get all actions for a specific street"""
        return [action for action in self.actions if action.street == street]

    def get_player_actions(self, player_name: str, street: Optional[Street] = None) -> List[Action]:
        """Get all actions for a specific player, optionally filtered by street"""
        actions = [action for action in self.actions if action.player_name == player_name]
        if street:
            actions = [action for action in actions if action.street == street]
        return actions

    def __repr__(self) -> str:
        return f"Hand(id={self.hand_id}, stake={self.stake_level}, players={len(self.players)})"


@dataclass
class ParseResult:
    """
    Result of parsing a hand history file.

    Attributes:
        hands: Successfully parsed hands
        errors: List of error messages for failed hands
        total_hands: Total number of hands in file
        successful: Number successfully parsed
        failed: Number that failed to parse
    """
    hands: List[Hand] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_hands: int = 0
    successful: int = 0
    failed: int = 0

    def add_hand(self, hand: Hand) -> None:
        """Add a successfully parsed hand"""
        self.hands.append(hand)
        self.successful += 1

    def add_error(self, error_msg: str) -> None:
        """Add an error for a failed hand"""
        self.errors.append(error_msg)
        self.failed += 1

    def __repr__(self) -> str:
        return f"ParseResult(total={self.total_hands}, successful={self.successful}, failed={self.failed})"
