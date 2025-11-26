"""
GTO Service - Handles GTO frequency queries for preflop scenarios.

Based on GTOWizard data architecture.

Note: Player-specific GTO analysis (leak detection, adherence scoring) is handled
directly in main.py endpoints using on-the-fly calculations from player_hand_summary.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.models.database_models import GTOScenario, GTOFrequency


class GTOService:
    """Service for GTO frequency queries and comparisons."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # PREFLOP GTO QUERIES
    # =========================================================================

    def get_gto_frequency(
        self,
        scenario_name: str,
        hand: str,
        position: Optional[str] = None
    ) -> Optional[float]:
        """
        Get GTO frequency for a specific hand in a scenario.

        Args:
            scenario_name: e.g., 'BB_vs_UTG_call'
            hand: e.g., 'AKo', 'JTs', '22'
            position: Optional position filter (inferred from scenario if not provided)

        Returns:
            float: Frequency (0.0 to 1.0) or None if not found

        Example:
            freq = gto_service.get_gto_frequency('BB_vs_UTG_call', 'AKo')
            # Returns 0.395 (39.5% call frequency)
        """
        query = self.db.query(GTOFrequency).join(
            GTOScenario
        ).filter(
            GTOScenario.scenario_name == scenario_name,
            GTOFrequency.hand == hand
        )

        if position:
            query = query.filter(GTOFrequency.position == position)

        result = query.first()
        return float(result.frequency) if result else None

    def get_action_breakdown(
        self,
        position: str,
        opponent: Optional[str],
        hand: str
    ) -> Dict[str, float]:
        """
        Get all action frequencies for a hand in a situation.

        Args:
            position: e.g., 'BB'
            opponent: e.g., 'UTG' (None for opening ranges)
            hand: e.g., 'AKo'

        Returns:
            {'fold': 0.0, 'call': 0.595, '3bet': 0.405, ...}

        Example:
            breakdown = gto_service.get_action_breakdown('BB', 'UTG', 'AKo')
            # Returns {'fold': 0.0, 'call': 0.395, '3bet': 0.605}
        """
        query = self.db.query(
            GTOScenario.action,
            GTOFrequency.frequency
        ).join(
            GTOFrequency
        ).filter(
            GTOScenario.position == position,
            GTOFrequency.hand == hand,
            GTOFrequency.position == position
        )

        if opponent:
            query = query.filter(GTOScenario.opponent_position == opponent)
        else:
            query = query.filter(GTOScenario.opponent_position.is_(None))

        results = query.all()
        return {action: float(freq) for action, freq in results}

    def get_opening_range(
        self,
        position: str,
        min_frequency: float = 0.0
    ) -> Dict[str, float]:
        """
        Get full opening range for a position.

        Args:
            position: e.g., 'UTG', 'BTN'
            min_frequency: Only return hands with frequency >= this value

        Returns:
            {'AA': 1.0, 'KK': 1.0, 'AKo': 1.0, '22': 0.285, ...}

        Example:
            range = gto_service.get_opening_range('UTG', min_frequency=0.5)
            # Returns all hands opened >50% of the time
        """
        scenario_name = f"{position}_open"

        results = self.db.query(
            GTOFrequency.hand,
            GTOFrequency.frequency
        ).join(
            GTOScenario
        ).filter(
            GTOScenario.scenario_name == scenario_name,
            GTOFrequency.frequency >= min_frequency
        ).all()

        return {hand: float(freq) for hand, freq in results}

    def get_gto_aggregate_frequency(
        self,
        scenario_name: str
    ) -> Optional[float]:
        """
        Get aggregate GTO frequency for a scenario (for VILLAIN analysis without hole cards).

        This uses the pre-calculated average frequency across all combos,
        stored in gto_scenarios.gto_aggregate_freq.

        Args:
            scenario_name: e.g., 'BB_vs_UTG_call'

        Returns:
            float: Aggregate frequency (0.0 to 1.0) or None if not found

        Example:
            freq = gto_service.get_gto_aggregate_frequency('BB_vs_UTG_call')
            # Returns ~0.64 (64% call frequency on average)
        """
        scenario = self.db.query(GTOScenario).filter(
            GTOScenario.scenario_name == scenario_name
        ).first()

        if scenario and scenario.gto_aggregate_freq is not None:
            return float(scenario.gto_aggregate_freq)
        return None

    def get_all_scenario_aggregates(
        self,
        category: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get all aggregate frequencies for villain analysis.

        Args:
            category: Optional filter by category ('opening', 'defense', 'facing_3bet', 'facing_4bet')

        Returns:
            Dictionary of scenario_name -> aggregate_frequency

        Example:
            aggregates = gto_service.get_all_scenario_aggregates('defense')
            # Returns {'BB_vs_UTG_call': 0.64, 'BB_vs_UTG_3bet': 0.29, ...}
        """
        query = self.db.query(
            GTOScenario.scenario_name,
            GTOScenario.gto_aggregate_freq
        ).filter(
            GTOScenario.gto_aggregate_freq.isnot(None)
        )

        if category:
            query = query.filter(GTOScenario.category == category)

        results = query.all()
        return {name: float(freq) for name, freq in results if freq is not None}

    def analyze_villain_action(
        self,
        scenario_name: str,
        action_taken: bool
    ) -> Dict[str, Any]:
        """
        Analyze a villain's action against aggregate GTO (without knowing hole cards).

        Args:
            scenario_name: e.g., 'BB_vs_UTG_call'
            action_taken: True if villain took the action, False if not

        Returns:
            Analysis with GTO comparison

        Example:
            analysis = gto_service.analyze_villain_action('BB_vs_UTG_call', True)
            # Returns comparison to 64% aggregate call frequency
        """
        gto_freq = self.get_gto_aggregate_frequency(scenario_name)

        if gto_freq is None:
            return {'error': f'Scenario not found: {scenario_name}'}

        return {
            'scenario': scenario_name,
            'action_taken': action_taken,
            'gto_aggregate_freq': gto_freq,
            'gto_expected': gto_freq > 0.5,
            'note': 'Aggregate frequency used (villain hole cards unknown)'
        }

    def get_scenario_by_context(
        self,
        position: str,
        action: str,
        opponent: Optional[str] = None,
        street: str = 'preflop'
    ) -> Optional[GTOScenario]:
        """
        Find scenario by context.

        Args:
            position: e.g., 'BB'
            action: e.g., 'call', '3bet'
            opponent: e.g., 'UTG'
            street: 'preflop', 'flop', etc.

        Returns:
            GTOScenario or None
        """
        query = self.db.query(GTOScenario).filter(
            GTOScenario.position == position,
            GTOScenario.action == action,
            GTOScenario.street == street
        )

        if opponent:
            query = query.filter(GTOScenario.opponent_position == opponent)

        return query.first()

    def get_scenarios_for_category(
        self,
        category: str,
        position: Optional[str] = None
    ) -> List[GTOScenario]:
        """
        Get all scenarios in a category.

        Args:
            category: 'opening', 'defense', 'facing_3bet', 'facing_4bet'
            position: Optional position filter

        Returns:
            List of GTOScenario objects
        """
        query = self.db.query(GTOScenario).filter(
            GTOScenario.category == category
        )

        if position:
            query = query.filter(GTOScenario.position == position)

        return query.all()

    def get_gto_frequencies_for_scenario(
        self,
        scenario_id: int
    ) -> Dict[str, float]:
        """
        Get all hand frequencies for a scenario.

        Args:
            scenario_id: The scenario ID

        Returns:
            Dict of hand -> frequency
        """
        results = self.db.query(
            GTOFrequency.hand,
            GTOFrequency.frequency
        ).filter(
            GTOFrequency.scenario_id == scenario_id
        ).all()

        return {hand: float(freq) for hand, freq in results}
