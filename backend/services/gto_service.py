"""
Service for querying GTO solutions and comparing to player stats.

This service provides access to pre-computed GTO solutions and calculates
deviations between player statistics and optimal GTO frequencies.
"""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class GTOService:
    """Service for GTO solution queries and player comparisons"""

    def __init__(self, db: Session):
        self.db = db

    def get_gto_solution(self, scenario_name: str) -> Optional[Dict]:
        """
        Get GTO solution by scenario name.

        Args:
            scenario_name: Exact scenario name (e.g., 'BTN_steal_vs_BB')

        Returns:
            GTO solution dict or None if not found
        """
        query = text("""
            SELECT
                scenario_name,
                scenario_type,
                board,
                position_oop,
                position_ip,
                pot_size,
                stack_depth,
                gto_bet_frequency,
                gto_check_frequency,
                gto_fold_frequency,
                gto_call_frequency,
                gto_raise_frequency,
                gto_bet_size_small,
                gto_bet_size_medium,
                gto_bet_size_large,
                ev_oop,
                ev_ip,
                description
            FROM gto_solutions
            WHERE scenario_name = :scenario_name
        """)

        result = self.db.execute(query, {'scenario_name': scenario_name}).fetchone()

        if not result:
            logger.warning(f"GTO solution not found: {scenario_name}")
            return None

        return dict(result._mapping)

    def list_scenarios(
        self,
        scenario_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        List available GTO scenarios.

        Args:
            scenario_type: Filter by type ('preflop', 'srp_flop', etc.)
            limit: Maximum scenarios to return

        Returns:
            List of scenario summaries
        """
        if scenario_type:
            query = text("""
                SELECT
                    scenario_name,
                    scenario_type,
                    board,
                    description,
                    solved_at
                FROM gto_solutions
                WHERE scenario_type = :scenario_type
                ORDER BY solved_at DESC
                LIMIT :limit
            """)
            results = self.db.execute(
                query,
                {'scenario_type': scenario_type, 'limit': limit}
            ).fetchall()
        else:
            query = text("""
                SELECT
                    scenario_name,
                    scenario_type,
                    board,
                    description,
                    solved_at
                FROM gto_solutions
                ORDER BY solved_at DESC
                LIMIT :limit
            """)
            results = self.db.execute(query, {'limit': limit}).fetchall()

        return [dict(r._mapping) for r in results]

    def compare_player_to_gto(
        self,
        player_stats: Dict,
        scenario_name: str
    ) -> Dict:
        """
        Compare player statistics to GTO baseline.

        Args:
            player_stats: Player stats dict from player_stats table
            scenario_name: GTO scenario to compare against

        Returns:
            Comparison dict with deviations and exploits
        """
        gto = self.get_gto_solution(scenario_name)

        if not gto:
            return {
                'error': f'GTO solution not found: {scenario_name}',
                'available_scenarios': self.list_scenarios(limit=10)
            }

        deviations = []

        # Compare fold to 3-bet
        if 'fold_to_three_bet_pct' in player_stats and gto.get('gto_fold_frequency') is not None:
            player_fold = float(player_stats['fold_to_three_bet_pct'] or 0)
            gto_fold = float(gto['gto_fold_frequency'])
            deviation = player_fold - gto_fold

            deviations.append({
                'stat': 'fold_to_3bet',
                'player': player_fold,
                'gto': gto_fold,
                'deviation': round(deviation, 2),
                'severity': self._classify_deviation(abs(deviation)),
                'exploitable': abs(deviation) > 10,
                'exploit_direction': 'over-folding' if deviation > 0 else 'under-folding'
            })

        # Compare cbet frequency
        if 'cbet_flop_pct' in player_stats and gto.get('gto_bet_frequency') is not None:
            player_cbet = float(player_stats['cbet_flop_pct'] or 0)
            gto_cbet = float(gto['gto_bet_frequency'])
            deviation = player_cbet - gto_cbet

            deviations.append({
                'stat': 'cbet_flop',
                'player': player_cbet,
                'gto': gto_cbet,
                'deviation': round(deviation, 2),
                'severity': self._classify_deviation(abs(deviation)),
                'exploitable': abs(deviation) > 10,
                'exploit_direction': 'over-betting' if deviation > 0 else 'under-betting'
            })

        # Compare fold to cbet
        if 'fold_to_cbet_flop_pct' in player_stats and gto.get('gto_fold_frequency') is not None:
            player_fold_cbet = float(player_stats['fold_to_cbet_flop_pct'] or 0)
            gto_fold_cbet = float(gto['gto_fold_frequency'])
            deviation = player_fold_cbet - gto_fold_cbet

            deviations.append({
                'stat': 'fold_to_cbet',
                'player': player_fold_cbet,
                'gto': gto_fold_cbet,
                'deviation': round(deviation, 2),
                'severity': self._classify_deviation(abs(deviation)),
                'exploitable': abs(deviation) > 10,
                'exploit_direction': 'over-folding' if deviation > 0 else 'under-folding'
            })

        # Calculate exploit value
        exploitable_devs = [d for d in deviations if d['exploitable']]
        total_exploit_value = 0

        for dev in exploitable_devs:
            # Simplified EV calculation
            # In reality, this would be more complex
            ev = self.calculate_exploit_ev(
                deviation=abs(dev['deviation']),
                frequency=10,  # Assume 10% frequency for now
                pot_size=float(gto.get('pot_size', 7))
            )
            dev['estimated_ev'] = ev
            total_exploit_value += ev

        return {
            'scenario': scenario_name,
            'gto_baseline': {
                'scenario_type': gto.get('scenario_type'),
                'board': gto.get('board'),
                'description': gto.get('description'),
                'gto_bet_freq': gto.get('gto_bet_frequency'),
                'gto_fold_freq': gto.get('gto_fold_frequency'),
                'gto_raise_freq': gto.get('gto_raise_frequency')
            },
            'deviations': deviations,
            'exploitable_count': len(exploitable_devs),
            'total_estimated_ev': round(total_exploit_value, 2),
            'summary': self._generate_exploit_summary(deviations)
        }

    def calculate_exploit_ev(
        self,
        deviation: float,
        frequency: float,
        pot_size: float = 7.0
    ) -> float:
        """
        Calculate expected value of exploiting a deviation.

        Args:
            deviation: Percentage point deviation from GTO
            frequency: How often this spot occurs (per 100 hands)
            pot_size: Average pot size for this spot

        Returns:
            Expected value in BB per 100 hands
        """
        # Simplified EV calculation
        # Real calculation would be more complex based on game theory

        # Base EV per exploit
        base_ev_per_exploit = (deviation / 100) * pot_size * 0.5

        # Total EV per 100 hands
        total_ev = base_ev_per_exploit * frequency

        return round(total_ev, 2)

    def _classify_deviation(self, deviation: float) -> str:
        """Classify deviation severity"""
        if deviation < 5:
            return 'negligible'
        elif deviation < 10:
            return 'minor'
        elif deviation < 15:
            return 'moderate'
        elif deviation < 25:
            return 'severe'
        else:
            return 'extreme'

    def _generate_exploit_summary(self, deviations: List[Dict]) -> str:
        """Generate human-readable exploit summary"""
        exploitable = [d for d in deviations if d['exploitable']]

        if not exploitable:
            return "No significant exploitable deviations found"

        # Sort by deviation magnitude
        exploitable.sort(key=lambda x: abs(x['deviation']), reverse=True)

        summaries = []
        for dev in exploitable[:3]:  # Top 3 exploits
            direction = dev['exploit_direction']
            stat = dev['stat'].replace('_', ' ').title()
            deviation = abs(dev['deviation'])
            summaries.append(
                f"{stat}: {direction} by {deviation:.1f}% ({dev['severity']})"
            )

        return "; ".join(summaries)

    def get_scenario_count(self) -> Dict:
        """Get count of scenarios by type"""
        query = text("""
            SELECT
                scenario_type,
                COUNT(*) as count
            FROM gto_solutions
            GROUP BY scenario_type
            ORDER BY count DESC
        """)

        results = self.db.execute(query).fetchall()

        counts = {r.scenario_type: r.count for r in results}
        counts['total'] = sum(counts.values())

        return counts
