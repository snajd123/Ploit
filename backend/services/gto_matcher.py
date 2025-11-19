"""
GTO Matcher Service

Finds the best matching GTO solutions for a given board using multi-level categorization
and adaptive matching with confidence scoring.

Matching strategy:
1. Try exact board match (100% confidence)
2. Try L3 category match (80-90% confidence)
3. Try L2 category match (60-75% confidence)
4. Try L1 category match (40-55% confidence)
5. Use aggregated category data as fallback (20-35% confidence)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import json

# Try relative import first, fall back to absolute for testing
try:
    from .board_categorizer import BoardCategorizer, BoardAnalysis
except ImportError:
    from board_categorizer import BoardCategorizer, BoardAnalysis


@dataclass
class GTOMatch:
    """Represents a matched GTO solution with confidence score."""
    solution_id: int
    scenario_name: str
    board: str
    match_type: str  # "exact", "l3", "l2", "l1", "aggregate"
    confidence: float  # 0-100
    category_l1: str
    category_l2: str
    category_l3: str
    similarity_score: float  # 0-100, measures how similar boards are

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'solution_id': self.solution_id,
            'scenario_name': self.scenario_name,
            'board': self.board,
            'match_type': self.match_type,
            'confidence': round(self.confidence, 1),
            'category_l1': self.category_l1,
            'category_l2': self.category_l2,
            'category_l3': self.category_l3,
            'similarity_score': round(self.similarity_score, 1)
        }


class GTOMatcher:
    """
    Finds best matching GTO solutions for a given board.

    Uses multi-level categorization with adaptive matching:
    - Exact match (if available)
    - Category-based matching (L3 -> L2 -> L1)
    - Aggregated fallback

    Example usage:
        matcher = GTOMatcher(db_session)
        matches = matcher.find_matches("Ah9s4c", scenario_type="SRP", top_n=3)
        for match in matches:
            print(f"Board: {match.board}, Confidence: {match.confidence}%")
    """

    def __init__(self, db_session=None):
        """
        Initialize GTOMatcher.

        Args:
            db_session: SQLAlchemy database session (optional for now)
        """
        self.db_session = db_session
        self.categorizer = BoardCategorizer()

    def find_matches(
        self,
        board: str,
        scenario_type: Optional[str] = None,
        position_context: Optional[str] = None,
        action_sequence: Optional[str] = None,
        top_n: int = 5
    ) -> List[GTOMatch]:
        """
        Find best matching GTO solutions for a board.

        Args:
            board: Board string like "As8h3c"
            scenario_type: Optional scenario filter ("SRP", "3BP", etc.)
            position_context: Optional position filter ("IP", "OOP")
            action_sequence: Optional action filter ("cbet", "check", etc.)
            top_n: Number of top matches to return

        Returns:
            List of GTOMatch objects, sorted by confidence (highest first)
        """
        # Analyze the target board
        analysis = self.categorizer.analyze(board)

        matches = []

        # Try different matching strategies in order of preference
        # 1. Exact board match
        exact_matches = self._find_exact_matches(board, scenario_type, position_context, action_sequence)
        matches.extend(exact_matches)

        # 2. L3 category matches
        if len(matches) < top_n:
            l3_matches = self._find_category_matches(
                analysis.category_l3, "l3", scenario_type, position_context, action_sequence
            )
            matches.extend(l3_matches)

        # 3. L2 category matches
        if len(matches) < top_n:
            l2_matches = self._find_category_matches(
                analysis.category_l2, "l2", scenario_type, position_context, action_sequence
            )
            matches.extend(l2_matches)

        # 4. L1 category matches
        if len(matches) < top_n:
            l1_matches = self._find_category_matches(
                analysis.category_l1, "l1", scenario_type, position_context, action_sequence
            )
            matches.extend(l1_matches)

        # Calculate similarity scores for all matches
        for match in matches:
            match.similarity_score = self._calculate_similarity(analysis, match.board)

        # Sort by confidence (primary) and similarity (secondary)
        matches.sort(key=lambda m: (m.confidence, m.similarity_score), reverse=True)

        # Return top N
        return matches[:top_n]

    def _find_exact_matches(
        self,
        board: str,
        scenario_type: Optional[str],
        position_context: Optional[str],
        action_sequence: Optional[str]
    ) -> List[GTOMatch]:
        """
        Find exact board matches.

        For now, returns empty list (database integration needed).
        When DB is connected, this will query gto_solutions table.
        """
        # TODO: Implement database query
        # Example query:
        # SELECT * FROM gto_solutions
        # WHERE board = :board
        # AND scenario_type = :scenario_type (if provided)
        # ...

        # Placeholder for testing
        return []

    def _find_category_matches(
        self,
        category: str,
        level: str,
        scenario_type: Optional[str],
        position_context: Optional[str],
        action_sequence: Optional[str]
    ) -> List[GTOMatch]:
        """
        Find matches by category level.

        Args:
            category: Category name (e.g., "Ace-high-rainbow-dry")
            level: Category level ("l1", "l2", "l3")
            scenario_type, position_context, action_sequence: Optional filters

        Returns:
            List of GTOMatch objects
        """
        # TODO: Implement database query
        # Example query:
        # SELECT * FROM gto_solutions
        # WHERE board_category_{level} = :category
        # AND scenario_type = :scenario_type (if provided)
        # ...

        # Determine confidence based on level
        confidence_ranges = {
            "l3": (80, 90),
            "l2": (60, 75),
            "l1": (40, 55)
        }

        base_confidence = sum(confidence_ranges[level]) / 2

        # Placeholder for testing
        return []

    def _calculate_similarity(self, analysis: BoardAnalysis, match_board: str) -> float:
        """
        Calculate similarity score between target board and matched board.

        Similarity factors:
        - Same high card rank: +20
        - Same connectivity: +15
        - Same texture (rainbow/2tone/monotone): +15
        - Same paired status: +15
        - Same wetness: +10
        - Same broadway status: +10
        - Similar middle/low ranks: +15

        Args:
            analysis: BoardAnalysis of target board
            match_board: Matched board string

        Returns:
            Similarity score (0-100)
        """
        try:
            match_analysis = self.categorizer.analyze(match_board)
        except:
            return 50.0  # Default if analysis fails

        similarity = 0.0

        # High card rank match
        if analysis.high_card_rank == match_analysis.high_card_rank:
            similarity += 20

        # Connectivity match
        if analysis.is_connected == match_analysis.is_connected:
            similarity += 15

        # Texture match (rainbow/2tone/monotone)
        if analysis.is_rainbow == match_analysis.is_rainbow:
            similarity += 5
        if analysis.is_two_tone == match_analysis.is_two_tone:
            similarity += 5
        if analysis.is_monotone == match_analysis.is_monotone:
            similarity += 5

        # Paired status
        if analysis.is_paired == match_analysis.is_paired:
            similarity += 15

        # Wetness
        if analysis.is_wet == match_analysis.is_wet:
            similarity += 10

        # Broadway
        if analysis.has_broadway == match_analysis.has_broadway:
            similarity += 10

        # Middle/low rank similarity (within 2 ranks)
        mid_rank_diff = abs(
            self.categorizer.RANK_VALUES[analysis.middle_card_rank] -
            self.categorizer.RANK_VALUES[match_analysis.middle_card_rank]
        )
        low_rank_diff = abs(
            self.categorizer.RANK_VALUES[analysis.low_card_rank] -
            self.categorizer.RANK_VALUES[match_analysis.low_card_rank]
        )

        if mid_rank_diff <= 2:
            similarity += max(0, 7.5 - mid_rank_diff * 2.5)
        if low_rank_diff <= 2:
            similarity += max(0, 7.5 - low_rank_diff * 2.5)

        return min(100.0, similarity)

    def get_match_explanation(self, match: GTOMatch, target_board: str) -> str:
        """
        Generate human-readable explanation of why this match was selected.

        Args:
            match: GTOMatch object
            target_board: Original board being matched

        Returns:
            Explanation string
        """
        target_analysis = self.categorizer.analyze(target_board)
        match_analysis = self.categorizer.analyze(match.board)

        explanations = []

        if match.match_type == "exact":
            return f"Exact match: This GTO solution was solved for the identical board {match.board}"

        explanations.append(f"Category match ({match.match_type.upper()}): Both boards are in the '{match.category_l3}' category")

        # Add specific similarities
        if target_analysis.high_card_rank == match_analysis.high_card_rank:
            explanations.append(f"Same high card: {target_analysis.high_card_rank}")

        if target_analysis.is_rainbow == match_analysis.is_rainbow and target_analysis.is_rainbow:
            explanations.append("Both boards are rainbow")
        elif target_analysis.is_two_tone == match_analysis.is_two_tone and target_analysis.is_two_tone:
            explanations.append("Both boards are two-tone")
        elif target_analysis.is_monotone == match_analysis.is_monotone and target_analysis.is_monotone:
            explanations.append("Both boards are monotone")

        if target_analysis.is_wet == match_analysis.is_wet:
            if target_analysis.is_wet:
                explanations.append("Both boards are wet (high connectivity)")
            else:
                explanations.append("Both boards are dry (low connectivity)")

        if target_analysis.is_paired == match_analysis.is_paired and target_analysis.is_paired:
            explanations.append("Both boards are paired")

        explanation = ". ".join(explanations)
        return f"{explanation}. Confidence: {match.confidence:.1f}%, Similarity: {match.similarity_score:.1f}%"

    def get_aggregate_strategy(
        self,
        category: str,
        level: str = "l3"
    ) -> Optional[Dict]:
        """
        Get aggregated strategy data for a category when no exact match exists.

        Args:
            category: Category name
            level: Category level (1, 2, or 3)

        Returns:
            Dictionary with aggregated strategy data, or None if not found
        """
        # TODO: Implement database query
        # SELECT * FROM gto_category_aggregates
        # WHERE category_level = :level AND category_name = :category

        return None


def main():
    """Test the GTOMatcher."""
    matcher = GTOMatcher()

    # Test boards
    test_boards = [
        ("As8h3c", "SRP", "IP", "cbet"),
        ("Ks9h4c", "SRP", "OOP", "check"),
        ("QsJhTc", "3BP", "IP", "cbet"),
    ]

    print("=" * 80)
    print("GTO MATCHER TEST")
    print("=" * 80)

    for board, scenario, position, action in test_boards:
        print(f"\nTarget Board: {board}")
        print(f"Scenario: {scenario}, Position: {position}, Action: {action}")

        analysis = matcher.categorizer.analyze(board)
        print(f"  L1: {analysis.category_l1}")
        print(f"  L2: {analysis.category_l2}")
        print(f"  L3: {analysis.category_l3}")

        # Find matches (will be empty until DB is connected)
        matches = matcher.find_matches(board, scenario, position, action, top_n=3)

        if matches:
            print(f"\n  Top Matches:")
            for i, match in enumerate(matches, 1):
                print(f"    {i}. Board: {match.board}, Confidence: {match.confidence:.1f}%, "
                      f"Similarity: {match.similarity_score:.1f}%")
                print(f"       {matcher.get_match_explanation(match, board)}")
        else:
            print("  No matches found (database not connected)")


if __name__ == "__main__":
    main()
