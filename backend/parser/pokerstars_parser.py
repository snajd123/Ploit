"""
PokerStars hand history parser.

Parses PokerStars .txt hand history files and extracts all relevant data
including players, positions, actions, pot sizes, and calculates boolean flags
for statistical analysis.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import logging

from backend.parser.data_structures import (
    Hand, Player, Action, PlayerHandSummaryFlags, ParseResult,
    Street, ActionType, Position
)
from backend.parser.action_parser import ActionParser
from backend.parser.flag_calculator import FlagCalculator

logger = logging.getLogger(__name__)


class PokerStarsParser:
    """
    Parser for PokerStars hand history format.

    Extracts all hand data and calculates player statistics flags.
    """

    # Regex patterns for parsing (supports both $ and € currencies)
    HAND_HEADER_PATTERN = r"PokerStars Hand #(\d+):\s+Hold'em No Limit \([\$€]?([\d.]+)/[\$€]?([\d.]+).*?\) - (.*?)$"
    TABLE_PATTERN = r"Table '([^']+)' (\d+)-max Seat #(\d+) is the button"
    SEAT_PATTERN = r"Seat (\d+): ([^\(]+) \([\$€]?([\d.]+) in chips\)"
    BLIND_PATTERN = r"([^:]+): posts (small blind|big blind|small & big blinds) [\$€]?([\d.]+)"
    ACTION_PATTERN = r"([^:]+): (folds|checks|calls|bets|raises)(?: [\$€]?([\d.]+))?(?: to [\$€]?([\d.]+))?( and is all-in)?"
    BOARD_PATTERN = r"\*\*\* (FLOP|TURN|RIVER) \*\*\* \[([^\]]+)\]"
    POT_PATTERN = r"Total pot [\$€]?([\d.]+)"
    RAKE_PATTERN = r"Rake [\$€]?([\d.]+)"
    UNCALLED_PATTERN = r"Uncalled bet \([\$€]?([\d.]+)\) returned to ([^\n]+)"
    COLLECTED_PATTERN = r"([^:]+) collected [\$€]?([\d.]+) from pot"
    SHOWDOWN_PATTERN = r"\*\*\* SHOW DOWN \*\*\*"
    SUMMARY_PATTERN = r"\*\*\* SUMMARY \*\*\*"

    def __init__(self):
        """Initialize parser"""
        self.current_hand: Optional[Hand] = None

    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse a complete PokerStars hand history file.

        Args:
            file_path: Path to .txt hand history file

        Returns:
            ParseResult with list of parsed hands and any errors

        Example:
            parser = PokerStarsParser()
            result = parser.parse_file("hands.txt")
            print(f"Parsed {result.successful} hands, {result.failed} failed")
        """
        result = ParseResult()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split file into individual hands
            hand_texts = self._split_hands(content)
            result.total_hands = len(hand_texts)

            logger.info(f"Found {len(hand_texts)} hands in {file_path}")

            for i, hand_text in enumerate(hand_texts):
                try:
                    hand = self.parse_single_hand(hand_text)
                    if hand:
                        result.add_hand(hand)
                except Exception as e:
                    error_msg = f"Failed to parse hand {i+1}: {str(e)}"
                    logger.error(error_msg)
                    result.add_error(error_msg)

            logger.info(f"Successfully parsed {result.successful}/{result.total_hands} hands")

        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            result.add_error(error_msg)
        except Exception as e:
            error_msg = f"Error reading file {file_path}: {str(e)}"
            logger.error(error_msg)
            result.add_error(error_msg)

        return result

    def _split_hands(self, content: str) -> List[str]:
        """
        Split file content into individual hand texts.

        Args:
            content: Full file content

        Returns:
            List of individual hand history strings
        """
        # Hands are separated by double newlines or start with "PokerStars Hand"
        hands = []
        current_hand = []

        for line in content.split('\n'):
            if line.startswith('PokerStars Hand #') and current_hand:
                # Start of new hand, save previous
                hands.append('\n'.join(current_hand))
                current_hand = [line]
            else:
                current_hand.append(line)

        # Don't forget the last hand
        if current_hand:
            hands.append('\n'.join(current_hand))

        return [h.strip() for h in hands if h.strip()]

    def parse_single_hand(self, hand_text: str) -> Optional[Hand]:
        """
        Parse a single hand history.

        Args:
            hand_text: Text of a single hand history

        Returns:
            Hand object with all parsed data, or None if parsing fails

        Raises:
            ValueError: If hand format is invalid
        """
        if not hand_text.strip():
            return None

        try:
            # Extract hand metadata
            hand_id, timestamp, table_name, stake_level, game_type, button_seat = self._extract_metadata(hand_text)

            # Create hand object
            hand = Hand(
                hand_id=hand_id,
                timestamp=timestamp,
                table_name=table_name,
                stake_level=stake_level,
                game_type=game_type,
                button_seat=button_seat,
                raw_text=hand_text
            )

            # Extract players and positions
            hand.players = self._extract_players(hand_text, button_seat, game_type)

            # Parse all actions
            hand.actions = self._parse_all_actions(hand_text, hand.players)

            # Extract board cards
            hand.board_cards = self._extract_board_cards(hand_text)

            # Extract pot and rake
            hand.pot_size, hand.rake = self._extract_pot_and_rake(hand_text)

            # Calculate player flags
            hand.player_flags = self._calculate_player_flags(hand)

            logger.debug(f"Successfully parsed hand {hand_id}")
            return hand

        except Exception as e:
            logger.error(f"Error parsing hand: {str(e)}")
            logger.debug(f"Hand text:\n{hand_text[:200]}...")
            raise

    def _extract_metadata(self, hand_text: str) -> Tuple[int, datetime, str, str, str, int]:
        """
        Extract hand metadata from header.

        Returns:
            Tuple of (hand_id, timestamp, table_name, stake_level, game_type, button_seat)
        """
        # Parse hand header
        header_match = re.search(self.HAND_HEADER_PATTERN, hand_text, re.MULTILINE)
        if not header_match:
            raise ValueError("Invalid hand header format")

        hand_id = int(header_match.group(1))
        small_blind = Decimal(header_match.group(2))
        big_blind = Decimal(header_match.group(3))
        timestamp_str = header_match.group(4)

        # Parse timestamp (format: "2025/11/17 10:30:15 ET")
        timestamp = self._parse_timestamp(timestamp_str)

        # Determine stake level from blinds
        stake_level = self._get_stake_level(small_blind, big_blind)

        # Parse table info
        table_match = re.search(self.TABLE_PATTERN, hand_text, re.MULTILINE)
        if not table_match:
            raise ValueError("Invalid table format")

        table_name = table_match.group(1)
        max_players = int(table_match.group(2))
        button_seat = int(table_match.group(3))

        game_type = f"{max_players}-max"

        return hand_id, timestamp, table_name, stake_level, game_type, button_seat

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse PokerStars timestamp string.

        Args:
            timestamp_str: String like "2025/11/17 10:30:15 ET"

        Returns:
            datetime object
        """
        # Remove timezone abbreviation for simplicity
        timestamp_str = re.sub(r'\s+[A-Z]{2,3}$', '', timestamp_str.strip())

        try:
            return datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            # Try alternative format
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"Could not parse timestamp: {timestamp_str}, using current time")
                return datetime.now()

    def _get_stake_level(self, small_blind: Decimal, big_blind: Decimal) -> str:
        """
        Determine stake level from blinds.

        Args:
            small_blind: Small blind amount
            big_blind: Big blind amount

        Returns:
            Stake level string like 'NL50', 'NL100', etc.
        """
        bb = int(big_blind * 100)  # Convert to cents/bb

        # Map blinds to stake names
        stake_map = {
            2: "NL2",
            5: "NL5",
            10: "NL10",
            25: "NL25",
            50: "NL50",
            100: "NL100",
            200: "NL200",
            400: "NL400",
            500: "NL500",
            1000: "NL1000"
        }

        return stake_map.get(bb, f"NL{bb}")

    def _extract_players(self, hand_text: str, button_seat: int, game_type: str) -> List[Player]:
        """
        Extract all players and assign positions.

        Args:
            hand_text: Hand history text
            button_seat: Button seat number
            game_type: Game type (e.g., '6-max', '9-max')

        Returns:
            List of Player objects with positions assigned
        """
        players = []
        # Pattern to match seat lines including sitting out status
        seat_pattern_full = r"Seat (\d+): ([^\(]+) \([\$€]?([\d.]+) in chips\)( is sitting out)?"
        seat_matches = re.finditer(seat_pattern_full, hand_text, re.MULTILINE)

        for match in seat_matches:
            seat_num = int(match.group(1))
            player_name = match.group(2).strip()
            stack = Decimal(match.group(3))
            is_sitting_out = match.group(4) is not None

            # Skip players who are sitting out - they don't get positions
            if is_sitting_out:
                continue

            player = Player(
                name=player_name,
                seat_number=seat_num,
                starting_stack=stack
            )
            players.append(player)

        # Sort by seat number
        players.sort(key=lambda p: p.seat_number)

        # Assign positions based on button
        players = self._assign_positions(players, button_seat, game_type)

        return players

    def _assign_positions(self, players: List[Player], button_seat: int, game_type: str) -> List[Player]:
        """
        Assign poker positions to players based on button.

        Args:
            players: List of players
            button_seat: Seat number of button
            game_type: Game type (affects position naming)

        Returns:
            Players with positions assigned
        """
        num_players = len(players)

        if num_players < 2:
            return players

        # Find button player
        button_idx = next((i for i, p in enumerate(players) if p.seat_number == button_seat), 0)

        if num_players == 2:
            # Heads up
            players[button_idx].position = "BTN"
            players[(button_idx + 1) % num_players].position = "BB"
        else:
            # Standard positions
            # Order after button: SB, BB, UTG, UTG+1, MP, HJ, CO, BTN
            position_names = self._get_position_names(num_players)

            for i in range(num_players):
                pos_idx = (button_idx + 1 + i) % num_players
                players[pos_idx].position = position_names[i]

        return players

    def _get_position_names(self, num_players: int) -> List[str]:
        """
        Get position names based on number of players.

        Args:
            num_players: Number of players at table

        Returns:
            List of position names in order from SB
        """
        if num_players == 6:
            # 6-max: SB, BB, UTG, MP, CO, BTN
            return ["SB", "BB", "UTG", "MP", "CO", "BTN"]
        elif num_players == 9:
            # 9-max: SB, BB, UTG, UTG+1, UTG+2, MP, HJ, CO, BTN
            return ["SB", "BB", "UTG", "UTG+1", "UTG+2", "MP", "HJ", "CO", "BTN"]
        elif num_players == 5:
            return ["SB", "BB", "UTG", "CO", "BTN"]
        elif num_players == 4:
            return ["SB", "BB", "CO", "BTN"]
        elif num_players == 3:
            return ["SB", "BB", "BTN"]
        else:
            # Generic positions
            positions = ["SB", "BB"]
            for i in range(num_players - 3):
                positions.append(f"MP{i+1}")
            positions.append("BTN")
            return positions

    def _parse_all_actions(self, hand_text: str, players: List[Player]) -> List[Action]:
        """
        Parse all actions from all streets.

        Args:
            hand_text: Hand history text
            players: List of players

        Returns:
            List of all actions in the hand
        """
        try:
            # Extract blinds from hand text
            header_match = re.search(self.HAND_HEADER_PATTERN, hand_text, re.MULTILINE)
            if not header_match:
                return []

            small_blind = Decimal(header_match.group(2))
            big_blind = Decimal(header_match.group(3))

            # Create action parser
            action_parser = ActionParser(players, small_blind, big_blind)

            # Parse all actions
            actions = action_parser.parse_actions(hand_text)

            logger.debug(f"Parsed {len(actions)} actions")
            return actions

        except Exception as e:
            logger.error(f"Error parsing actions: {str(e)}")
            return []

    def _extract_board_cards(self, hand_text: str) -> Dict[str, str]:
        """
        Extract community cards for each street.

        Args:
            hand_text: Hand history text

        Returns:
            Dictionary mapping street to cards (e.g., {'flop': 'Ah 7c 3d'})
        """
        board = {}
        board_matches = re.finditer(self.BOARD_PATTERN, hand_text)

        for match in board_matches:
            street = match.group(1).lower()
            cards = match.group(2).strip()

            if street == "flop":
                board['flop'] = cards
            elif street == "turn":
                # Turn shows all 4 cards, extract just the turn card
                all_cards = cards.split()
                if len(all_cards) >= 4:
                    board['turn'] = all_cards[3]
            elif street == "river":
                # River shows all 5 cards, extract just the river card
                all_cards = cards.split()
                if len(all_cards) >= 5:
                    board['river'] = all_cards[4]

        return board

    def _extract_pot_and_rake(self, hand_text: str) -> Tuple[Decimal, Decimal]:
        """
        Extract pot size and rake.

        Args:
            hand_text: Hand history text

        Returns:
            Tuple of (pot_size, rake)
        """
        pot_size = Decimal("0")
        rake = Decimal("0")

        pot_match = re.search(self.POT_PATTERN, hand_text)
        if pot_match:
            pot_size = Decimal(pot_match.group(1))

        rake_match = re.search(self.RAKE_PATTERN, hand_text)
        if rake_match:
            rake = Decimal(rake_match.group(1))

        return pot_size, rake

    def _calculate_player_flags(self, hand: Hand) -> Dict[str, PlayerHandSummaryFlags]:
        """
        Calculate all boolean flags for each player.

        Args:
            hand: Hand object with all data

        Returns:
            Dictionary mapping player name to their flags
        """
        try:
            calculator = FlagCalculator(hand)
            return calculator.calculate_all_flags()
        except Exception as e:
            logger.error(f"Error calculating player flags: {str(e)}")
            # Return empty flags on error
            return {player.name: PlayerHandSummaryFlags(player_name=player.name, position=player.position)
                    for player in hand.players}
