"""
Board Categorizer Service

Analyzes poker boards and assigns them to multi-level categories for GTO solution matching.

Multi-level categorization:
- Level 1: 7 broad categories (Ace-high, King-high, etc.)
- Level 2: ~20 medium categories (Ace-high-rainbow, King-high-2tone, etc.)
- Level 3: ~100+ fine categories (Ace-high-rainbow-dry, etc.)
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass
class BoardAnalysis:
    """Complete analysis of a poker board."""
    board: str
    cards: List[str]

    # Card ranks and suits
    ranks: List[str]
    suits: List[str]
    sorted_ranks: List[str]

    # High-level properties
    high_card_rank: str
    middle_card_rank: str
    low_card_rank: str

    # Texture properties
    is_paired: bool
    is_rainbow: bool
    is_two_tone: bool
    is_monotone: bool
    is_connected: bool
    is_highly_connected: bool
    has_broadway: bool
    is_dry: bool
    is_wet: bool

    # Multi-level categories
    category_l1: str
    category_l2: str
    category_l3: str


class BoardCategorizer:
    """
    Analyzes poker boards and assigns multi-level categories.

    Example usage:
        categorizer = BoardCategorizer()
        analysis = categorizer.analyze("As8h3c")
        print(analysis.category_l1)  # "Ace-high"
        print(analysis.category_l2)  # "Ace-high-rainbow"
        print(analysis.category_l3)  # "Ace-high-rainbow-dry"
    """

    # Rank ordering (highest to lowest)
    RANK_ORDER = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    RANK_VALUES = {rank: idx for idx, rank in enumerate(RANK_ORDER)}

    # Broadway cards
    BROADWAY_RANKS = {'A', 'K', 'Q', 'J', 'T'}

    def __init__(self):
        pass

    def analyze(self, board: str) -> BoardAnalysis:
        """
        Analyze a board and return complete categorization.

        Args:
            board: Board string like "As8h3c" or "Ks9h4c"

        Returns:
            BoardAnalysis object with all categorization data
        """
        # Parse board
        cards = self._parse_board(board)
        ranks = [card[0] for card in cards]
        suits = [card[1] for card in cards]
        sorted_ranks = self._sort_ranks(ranks)

        # Analyze texture properties
        is_paired = self._is_paired(ranks)
        is_rainbow = self._is_rainbow(suits)
        is_two_tone = self._is_two_tone(suits)
        is_monotone = self._is_monotone(suits)
        is_connected = self._is_connected(sorted_ranks)
        is_highly_connected = self._is_highly_connected(sorted_ranks)
        has_broadway = self._has_broadway(ranks)
        is_wet = self._is_wet(sorted_ranks, is_connected, has_broadway)
        is_dry = not is_wet

        # Determine categories
        category_l1 = self._categorize_l1(sorted_ranks, is_paired)
        category_l2 = self._categorize_l2(category_l1, is_rainbow, is_two_tone, is_monotone, is_paired)
        category_l3 = self._categorize_l3(category_l2, is_dry, is_wet, is_connected,
                                          is_highly_connected, has_broadway, sorted_ranks)

        return BoardAnalysis(
            board=board,
            cards=cards,
            ranks=ranks,
            suits=suits,
            sorted_ranks=sorted_ranks,
            high_card_rank=sorted_ranks[0],
            middle_card_rank=sorted_ranks[1],
            low_card_rank=sorted_ranks[2],
            is_paired=is_paired,
            is_rainbow=is_rainbow,
            is_two_tone=is_two_tone,
            is_monotone=is_monotone,
            is_connected=is_connected,
            is_highly_connected=is_highly_connected,
            has_broadway=has_broadway,
            is_dry=is_dry,
            is_wet=is_wet,
            category_l1=category_l1,
            category_l2=category_l2,
            category_l3=category_l3
        )

    def _parse_board(self, board: str) -> List[str]:
        """Parse board string into list of cards."""
        # Remove commas and spaces
        board = board.replace(',', '').replace(' ', '')

        # Extract cards (2 characters each)
        cards = []
        for i in range(0, len(board), 2):
            if i + 1 < len(board):
                cards.append(board[i:i+2])

        if len(cards) != 3:
            raise ValueError(f"Board must have exactly 3 cards, got {len(cards)}: {board}")

        return cards

    def _sort_ranks(self, ranks: List[str]) -> List[str]:
        """Sort ranks from highest to lowest."""
        return sorted(ranks, key=lambda r: self.RANK_VALUES[r])

    def _is_paired(self, ranks: List[str]) -> bool:
        """Check if board has a pair."""
        return len(set(ranks)) < 3

    def _is_rainbow(self, suits: List[str]) -> bool:
        """Check if board is rainbow (3 different suits)."""
        return len(set(suits)) == 3

    def _is_two_tone(self, suits: List[str]) -> bool:
        """Check if board is two-tone (2 different suits)."""
        return len(set(suits)) == 2

    def _is_monotone(self, suits: List[str]) -> bool:
        """Check if board is monotone (1 suit)."""
        return len(set(suits)) == 1

    def _is_connected(self, sorted_ranks: List[str]) -> bool:
        """
        Check if any 2 cards are within 1 rank of each other.
        Examples: K-Q-4 (connected), 9-8-3 (connected), A-7-2 (not connected)
        """
        values = [self.RANK_VALUES[r] for r in sorted_ranks]
        for i in range(len(values) - 1):
            if abs(values[i] - values[i+1]) <= 1:
                return True
        return False

    def _is_highly_connected(self, sorted_ranks: List[str]) -> bool:
        """
        Check if all 3 cards are within 3 ranks.
        Examples: 9-8-7 (highly connected), Q-J-T (highly connected), K-9-4 (not)
        """
        values = [self.RANK_VALUES[r] for r in sorted_ranks]
        return max(values) - min(values) <= 3

    def _has_broadway(self, ranks: List[str]) -> bool:
        """Check if board contains any broadway card (T, J, Q, K, A)."""
        return any(r in self.BROADWAY_RANKS for r in ranks)

    def _is_wet(self, sorted_ranks: List[str], is_connected: bool, has_broadway: bool) -> bool:
        """
        Determine if board is wet (many possible draws).
        Wet boards: highly connected, or connected with broadway
        """
        is_highly_connected = self._is_highly_connected(sorted_ranks)
        return is_highly_connected or (is_connected and has_broadway)

    def _categorize_l1(self, sorted_ranks: List[str], is_paired: bool) -> str:
        """
        Level 1: Broad categorization (7 categories).

        Categories:
        - Paired
        - Ace-high
        - King-high
        - Queen-high
        - Jack-high
        - Ten-high
        - Nine-or-lower
        """
        if is_paired:
            return "Paired"

        high_card = sorted_ranks[0]

        if high_card == 'A':
            return "Ace-high"
        elif high_card == 'K':
            return "King-high"
        elif high_card == 'Q':
            return "Queen-high"
        elif high_card == 'J':
            return "Jack-high"
        elif high_card == 'T':
            return "Ten-high"
        else:
            return "Nine-or-lower"

    def _categorize_l2(self, category_l1: str, is_rainbow: bool, is_two_tone: bool,
                      is_monotone: bool, is_paired: bool) -> str:
        """
        Level 2: Medium granularity (~20 categories).

        Adds suit texture to L1 categories:
        - {L1}-rainbow
        - {L1}-2tone
        - {L1}-monotone

        For paired boards:
        - Paired-rainbow
        - Paired-2tone
        - Paired-monotone
        """
        if is_rainbow:
            suit_suffix = "rainbow"
        elif is_two_tone:
            suit_suffix = "2tone"
        elif is_monotone:
            suit_suffix = "monotone"
        else:
            suit_suffix = "unknown"

        return f"{category_l1}-{suit_suffix}"

    def _categorize_l3(self, category_l2: str, is_dry: bool, is_wet: bool,
                      is_connected: bool, is_highly_connected: bool,
                      has_broadway: bool, sorted_ranks: List[str]) -> str:
        """
        Level 3: Fine granularity (~100+ categories).

        Adds connectivity and specific properties:
        - {L2}-dry
        - {L2}-wet
        - {L2}-connected
        - {L2}-highlyconnected
        - {L2}-broadway
        - {L2}-lowconnected (connected but no broadway)
        - {L2}-disconnected

        Examples:
        - "Ace-high-rainbow-dry"
        - "King-high-2tone-wet"
        - "Queen-high-monotone-connected"
        - "Paired-rainbow-highcard" (for paired with high kicker)
        """
        # Special handling for paired boards
        if "Paired" in category_l2:
            high_unpaired = sorted_ranks[0] if sorted_ranks[0] != sorted_ranks[1] else sorted_ranks[2]
            if high_unpaired in self.BROADWAY_RANKS:
                return f"{category_l2}-highcard"
            else:
                return f"{category_l2}-lowcard"

        # For unpaired boards, add connectivity detail
        if is_highly_connected:
            return f"{category_l2}-highlyconnected"
        elif is_connected:
            if has_broadway:
                return f"{category_l2}-connected"
            else:
                return f"{category_l2}-lowconnected"
        elif is_wet:
            return f"{category_l2}-wet"
        elif is_dry:
            return f"{category_l2}-dry"
        else:
            return f"{category_l2}-disconnected"

    def normalize_board(self, board: str) -> str:
        """
        Normalize board to canonical form (suits removed, ranks only).

        Examples:
            "As8h3c" -> "A83r"
            "KsKh4c" -> "KK4r"
            "9s9h9d" -> "999m"
        """
        analysis = self.analyze(board)
        ranks = ''.join(analysis.sorted_ranks)

        if analysis.is_rainbow:
            suffix = 'r'
        elif analysis.is_two_tone:
            suffix = 't'
        elif analysis.is_monotone:
            suffix = 'm'
        else:
            suffix = ''

        return f"{ranks}{suffix}"

    def get_category_description(self, category: str) -> str:
        """Get human-readable description of a category."""
        descriptions = {
            # Level 1
            "Ace-high": "Boards with an Ace as the highest card",
            "King-high": "Boards with a King as the highest card",
            "Queen-high": "Boards with a Queen as the highest card",
            "Jack-high": "Boards with a Jack as the highest card",
            "Ten-high": "Boards with a Ten as the highest card",
            "Nine-or-lower": "Boards with 9 or lower as the highest card",
            "Paired": "Boards with a pair",

            # Level 2 examples
            "Ace-high-rainbow": "Ace-high boards with three different suits",
            "King-high-2tone": "King-high boards with two suits",
            "Paired-monotone": "Paired boards with all same suit (flush board)",

            # Level 3 examples
            "Ace-high-rainbow-dry": "Ace-high rainbow boards with low connectivity",
            "King-high-2tone-wet": "King-high two-tone boards with high connectivity",
            "Queen-high-monotone-connected": "Queen-high monotone boards with connected ranks",
        }

        return descriptions.get(category, f"Category: {category}")


def main():
    """Test the BoardCategorizer."""
    categorizer = BoardCategorizer()

    # Test boards
    test_boards = [
        "As8h3c",  # A83 rainbow
        "Ks9h4c",  # K94 rainbow
        "QsJhTc",  # QJT rainbow
        "9s8h7c",  # 987 rainbow (highly connected)
        "AsAhKc",  # AA pair with high kicker
        "7s7h2c",  # 77 pair with low kicker
        "KsKhKd",  # Trips
    ]

    print("=" * 80)
    print("BOARD CATEGORIZATION TEST")
    print("=" * 80)

    for board in test_boards:
        print(f"\nBoard: {board}")
        analysis = categorizer.analyze(board)
        print(f"  Normalized: {categorizer.normalize_board(board)}")
        print(f"  High/Mid/Low: {analysis.high_card_rank}/{analysis.middle_card_rank}/{analysis.low_card_rank}")
        print(f"  Properties: paired={analysis.is_paired}, rainbow={analysis.is_rainbow}, "
              f"connected={analysis.is_connected}, wet={analysis.is_wet}")
        print(f"  L1: {analysis.category_l1}")
        print(f"  L2: {analysis.category_l2}")
        print(f"  L3: {analysis.category_l3}")


if __name__ == "__main__":
    main()
