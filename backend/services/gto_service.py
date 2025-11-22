"""
GTO Service - Handles all GTO frequency queries, leak detection, and exploit finding.

Based on GTOWizard data architecture.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from decimal import Decimal

from backend.models.gto_models import (
    GTOScenario, GTOFrequency, PlayerAction, PlayerGTOStat, HandType
)


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

    # =========================================================================
    # LEAK DETECTION
    # =========================================================================

    def record_player_action(
        self,
        player_name: str,
        hand_id: str,
        scenario_name: str,
        hole_cards: str,
        action_taken: str,
        timestamp: Optional[datetime] = None
    ) -> PlayerAction:
        """
        Record a player action and analyze against GTO.

        Automatically:
        - Looks up GTO frequency
        - Calculates EV loss
        - Flags mistakes
        - Updates player_gto_stats

        Args:
            player_name: Player name
            hand_id: Unique hand identifier
            scenario_name: e.g., 'BB_vs_UTG_call'
            hole_cards: e.g., 'AKo'
            action_taken: e.g., 'fold', 'call', '3bet'
            timestamp: When action occurred (defaults to now)

        Returns:
            PlayerAction object

        Example:
            action = gto_service.record_player_action(
                player_name='Villain1',
                hand_id='PS123456',
                scenario_name='BB_vs_UTG_call',
                hole_cards='AKo',
                action_taken='fold'
            )
            # Automatically calculates: gto_frequency=0.395, is_mistake=True
        """
        # Get scenario
        scenario = self.db.query(GTOScenario).filter(
            GTOScenario.scenario_name == scenario_name
        ).first()

        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_name}")

        # Look up GTO frequency for this hand/action
        gto_freq = self.get_gto_frequency(scenario_name, hole_cards, scenario.position)

        # Calculate EV loss and mistake severity
        ev_loss = self._calculate_ev_loss(gto_freq, action_taken)
        is_mistake, severity = self._classify_mistake(ev_loss)

        # Create player action record
        action = PlayerAction(
            player_name=player_name,
            hand_id=hand_id,
            timestamp=timestamp or datetime.utcnow(),
            scenario_id=scenario.scenario_id,
            hole_cards=hole_cards,
            action_taken=action_taken,
            gto_frequency=gto_freq,
            ev_loss_bb=ev_loss,
            is_mistake=is_mistake,
            mistake_severity=severity
        )

        self.db.add(action)
        self.db.flush()

        # Update aggregated stats
        self._update_player_stats(player_name, scenario.scenario_id)

        self.db.commit()
        return action

    def get_player_leaks(
        self,
        player_name: str,
        min_hands: int = 20,
        sort_by: str = 'ev_loss',
        street: str = 'preflop'
    ) -> List[Dict]:
        """
        Get all leaks for a player, sorted by severity.

        Args:
            player_name: Player to analyze
            min_hands: Minimum sample size
            sort_by: 'ev_loss', 'frequency_diff', 'severity'
            street: 'preflop', 'flop', etc.

        Returns:
            List of leak dictionaries with scenario info

        Example:
            leaks = gto_service.get_player_leaks('Villain1', min_hands=20)
            # Returns top leaks sorted by EV loss
        """
        query = self.db.query(
            PlayerGTOStat,
            GTOScenario
        ).join(
            GTOScenario
        ).filter(
            PlayerGTOStat.player_name == player_name,
            PlayerGTOStat.total_hands >= min_hands,
            GTOScenario.street == street
        )

        # Sort by requested metric
        if sort_by == 'ev_loss':
            query = query.order_by(PlayerGTOStat.total_ev_loss_bb.desc())
        elif sort_by == 'frequency_diff':
            query = query.order_by(func.abs(PlayerGTOStat.frequency_diff).desc())
        elif sort_by == 'severity':
            # Order by severity: critical > major > moderate > minor
            severity_order = {
                'critical': 0,
                'major': 1,
                'moderate': 2,
                'minor': 3
            }
            query = query.order_by(
                func.coalesce(
                    func.nullif(PlayerGTOStat.leak_severity, ''),
                    'minor'
                )
            )

        results = query.all()

        leaks = []
        for stat, scenario in results:
            leak = stat.to_dict()
            leak['scenario_name'] = scenario.scenario_name
            leak['category'] = scenario.category
            leak['position'] = scenario.position
            leak['action'] = scenario.action
            leaks.append(leak)

        return leaks

    def get_biggest_leak(self, player_name: str) -> Optional[Dict]:
        """Get player's single biggest leak by EV loss."""
        leaks = self.get_player_leaks(player_name, min_hands=10, sort_by='ev_loss')
        return leaks[0] if leaks else None

    # =========================================================================
    # EXPLOIT FINDING
    # =========================================================================

    def calculate_exploits(
        self,
        player_name: str,
        min_confidence: float = 70.0
    ) -> List[Dict]:
        """
        Calculate exploitable patterns in player's game.

        Args:
            player_name: Player to analyze
            min_confidence: Minimum confidence threshold (0-100)

        Returns:
            List of exploits with recommendations

        Example:
            exploits = gto_service.calculate_exploits('Villain1', min_confidence=70)
            # Returns: [{scenario, leak_type, exploit, value_bb_100, confidence}, ...]
        """
        leaks = self.get_player_leaks(player_name, min_hands=10)

        exploits = []
        for leak in leaks:
            if leak.get('exploit_confidence', 0) >= min_confidence:
                exploit = {
                    'scenario': leak['scenario_name'],
                    'leak_type': leak['leak_type'],
                    'frequency_diff': leak['frequency_diff'],
                    'exploit': leak['exploit_description'],
                    'value_bb_100': leak['exploit_value_bb_100'],
                    'confidence': leak['exploit_confidence'],
                    'sample_size': leak['total_hands']
                }
                exploits.append(exploit)

        return sorted(exploits, key=lambda x: x['value_bb_100'], reverse=True)

    def get_counter_strategy(
        self,
        player_name: str,
        position: str
    ) -> Dict[str, Any]:
        """
        Generate counter-strategy for a player in a position.

        Args:
            player_name: Opponent to exploit
            position: Position we're playing from (e.g., 'UTG' when villain is in BB)

        Returns:
            Counter-strategy with specific adjustments

        Example:
            counter = gto_service.get_counter_strategy('Villain1', 'UTG')
            # Returns adjustments to make when opening UTG vs this villain in BB
        """
        # Find leaks where villain is defending from BB against our position
        leaks = self.db.query(
            PlayerGTOStat,
            GTOScenario
        ).join(
            GTOScenario
        ).filter(
            PlayerGTOStat.player_name == player_name,
            GTOScenario.opponent_position == position,
            PlayerGTOStat.total_hands >= 20
        ).all()

        adjustments = []
        total_value = 0.0

        for stat, scenario in leaks:
            if stat.frequency_diff and abs(float(stat.frequency_diff)) > 0.05:
                # Significant deviation
                adjustment = {
                    'scenario': scenario.scenario_name,
                    'villain_action': scenario.action,
                    'villain_frequency': float(stat.player_frequency) if stat.player_frequency else None,
                    'gto_frequency': float(stat.gto_frequency) if stat.gto_frequency else None,
                    'deviation': float(stat.frequency_diff) if stat.frequency_diff else None,
                    'exploit': stat.exploit_description,
                    'value_bb': float(stat.exploit_value_bb_100) if stat.exploit_value_bb_100 else None
                }
                adjustments.append(adjustment)
                if stat.exploit_value_bb_100:
                    total_value += float(stat.exploit_value_bb_100)

        return {
            'position': position,
            'vs_player': player_name,
            'adjustments': adjustments,
            'expected_value_bb_100': total_value
        }

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_player_gto_adherence(
        self,
        player_name: str,
        street: str = 'preflop'
    ) -> Dict[str, Any]:
        """
        Calculate how closely player follows GTO.

        Args:
            player_name: Player to analyze
            street: 'preflop', 'flop', etc.

        Returns:
            Adherence metrics

        Example:
            adherence = gto_service.get_player_gto_adherence('Hero')
            # Returns: {total_hands, avg_ev_loss, gto_adherence_score, ...}
        """
        stats = self.db.query(
            PlayerGTOStat
        ).join(
            GTOScenario
        ).filter(
            PlayerGTOStat.player_name == player_name,
            GTOScenario.street == street
        ).all()

        if not stats:
            return {
                'total_hands': 0,
                'gto_adherence_score': 0.0,
                'message': 'No data available'
            }

        total_hands = sum(s.total_hands for s in stats)
        total_ev_loss = sum(float(s.total_ev_loss_bb or 0) for s in stats)
        avg_ev_loss = total_ev_loss / total_hands if total_hands > 0 else 0

        # Calculate adherence score (0-100)
        # Score decreases with EV loss
        # Perfect GTO = 100, -0.5 BB/hand = 0
        adherence_score = max(0, 100 - (avg_ev_loss * 200))

        major_leaks = sum(1 for s in stats if s.leak_severity in ['major', 'critical'])

        return {
            'player': player_name,
            'street': street,
            'total_hands': total_hands,
            'gto_adherence_score': round(adherence_score, 1),
            'avg_ev_loss_per_hand': round(avg_ev_loss, 4),
            'total_ev_loss_bb': round(total_ev_loss, 2),
            'major_leaks_count': major_leaks,
            'scenarios_analyzed': len(stats)
        }

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    def _calculate_ev_loss(self, gto_frequency: Optional[float], action_taken: str) -> float:
        """
        Estimate EV loss from deviating from GTO.

        This is a simplified model. Real EV loss depends on game tree complexity.
        """
        if gto_frequency is None:
            return 0.0

        # Simplified EV loss model
        # If GTO says do action X with frequency F:
        # - If we always do X when F=0: lose ~0.5 BB
        # - If we never do X when F=1: lose ~1.0 BB
        # - Linear interpolation for mixed frequencies

        if gto_frequency > 0.5:
            # Should mostly take this action
            # Not taking it costs more
            return (1 - gto_frequency) * 0.5
        elif gto_frequency < 0.1:
            # Should rarely take this action
            # Taking it costs
            return gto_frequency * 0.5
        else:
            # Mixed strategy - small deviation cost
            return abs(0.5 - gto_frequency) * 0.2

    def _classify_mistake(self, ev_loss: float) -> Tuple[bool, str]:
        """Classify mistake severity based on EV loss."""
        if ev_loss < 0.05:
            return False, 'minor'
        elif ev_loss < 0.15:
            return True, 'moderate'
        elif ev_loss < 0.30:
            return True, 'major'
        else:
            return True, 'critical'

    def _update_player_stats(self, player_name: str, scenario_id: int):
        """Update aggregated player stats after recording an action."""
        # Get all actions for this player/scenario
        actions = self.db.query(PlayerAction).filter(
            PlayerAction.player_name == player_name,
            PlayerAction.scenario_id == scenario_id
        ).all()

        if not actions:
            return

        total_hands = len(actions)
        total_ev_loss = sum(float(a.ev_loss_bb or 0) for a in actions)
        avg_ev_loss = total_ev_loss / total_hands

        # Get GTO frequency (average across all hands)
        gto_freq = sum(float(a.gto_frequency or 0) for a in actions) / total_hands

        # Calculate player frequency (how often they took this action)
        # This is simplified - in reality we'd need to track all possible actions
        player_freq = 1.0  # Placeholder

        # Calculate frequency difference
        freq_diff = player_freq - gto_freq

        # Determine leak type
        scenario = self.db.query(GTOScenario).get(scenario_id)
        leak_type = self._determine_leak_type(freq_diff, scenario.action if scenario else None)

        # Determine severity
        severity = self._determine_severity(avg_ev_loss)

        # Generate exploit description
        exploit_desc = self._generate_exploit_description(scenario, freq_diff, leak_type)

        # Calculate exploit value
        exploit_value = abs(freq_diff) * 10  # Simplified: 10 BB/100 per 0.1 frequency deviation

        # Calculate confidence based on sample size
        confidence = min(100, (total_hands / 50) * 100)

        # Update or create stat
        stat = self.db.query(PlayerGTOStat).filter(
            PlayerGTOStat.player_name == player_name,
            PlayerGTOStat.scenario_id == scenario_id
        ).first()

        if stat:
            stat.total_hands = total_hands
            stat.player_frequency = player_freq
            stat.gto_frequency = gto_freq
            stat.frequency_diff = freq_diff
            stat.total_ev_loss_bb = total_ev_loss
            stat.avg_ev_loss_bb = avg_ev_loss
            stat.leak_type = leak_type
            stat.leak_severity = severity
            stat.exploit_description = exploit_desc
            stat.exploit_value_bb_100 = exploit_value
            stat.exploit_confidence = confidence
            stat.last_updated = datetime.utcnow()
        else:
            stat = PlayerGTOStat(
                player_name=player_name,
                scenario_id=scenario_id,
                total_hands=total_hands,
                player_frequency=player_freq,
                gto_frequency=gto_freq,
                frequency_diff=freq_diff,
                total_ev_loss_bb=total_ev_loss,
                avg_ev_loss_bb=avg_ev_loss,
                leak_type=leak_type,
                leak_severity=severity,
                exploit_description=exploit_desc,
                exploit_value_bb_100=exploit_value,
                exploit_confidence=confidence
            )
            self.db.add(stat)

    def _determine_leak_type(self, freq_diff: float, action: Optional[str]) -> str:
        """Determine leak type from frequency difference and action."""
        if not action:
            return 'unknown'

        if freq_diff < -0.05:
            return f'under{action}'
        elif freq_diff > 0.05:
            return f'over{action}'
        else:
            return 'no_leak'

    def _determine_severity(self, ev_loss: float) -> str:
        """Determine leak severity from EV loss."""
        if ev_loss < 0.05:
            return 'minor'
        elif ev_loss < 0.15:
            return 'moderate'
        elif ev_loss < 0.30:
            return 'major'
        else:
            return 'critical'

    def _generate_exploit_description(
        self,
        scenario: Optional[GTOScenario],
        freq_diff: float,
        leak_type: str
    ) -> str:
        """Generate human-readable exploit description."""
        if not scenario:
            return "Unknown scenario"

        position = scenario.position
        opponent = scenario.opponent_position
        action = scenario.action

        if freq_diff < -0.05:
            # Under-performing action
            if action == 'call':
                return f"Player underdefends {position} vs {opponent}. Open wider from {opponent}."
            elif action == 'fold':
                return f"Player doesn't fold enough in {position} vs {opponent}. Bluff more."
            elif action == '3bet':
                return f"Player doesn't 3bet enough. Open wider and call more vs 3bets."
        elif freq_diff > 0.05:
            # Over-performing action
            if action == 'fold':
                return f"Player overfolding in {position} vs {opponent}. Bet/raise more."
            elif action == 'call':
                return f"Player overcalling. Bluff more on later streets."

        return f"Frequency deviation of {freq_diff*100:.1f}% in {scenario.scenario_name}"

    def compare_player_to_gto(self, player_stats: Dict[str, Optional[float]]) -> Dict:
        """
        Compare player statistics to GTO baseline values.

        Args:
            player_stats: Dictionary with keys like vpip_pct, pfr_pct, three_bet_pct, etc.

        Returns:
            Dictionary with 'deviations' list containing exploitable tendencies
        """
        # GTO baseline ranges for common stats
        gto_ranges = {
            'vpip_pct': (20, 28),
            'pfr_pct': (15, 22),
            'three_bet_pct': (5, 9),
            'fold_to_three_bet_pct': (55, 65),
            'cbet_flop_pct': (50, 70),
            'fold_to_cbet_flop_pct': (40, 50),
            'wtsd_pct': (25, 35)
        }

        deviations = []

        for stat_name, (gto_min, gto_max) in gto_ranges.items():
            stat_value = player_stats.get(stat_name)

            if stat_value is None:
                continue

            # Convert Decimal to float for math operations
            stat_value = float(stat_value)

            gto_mid = (gto_min + gto_max) / 2
            deviation = stat_value - gto_mid
            abs_deviation = abs(deviation)

            # Only flag significant deviations (>10% from GTO midpoint)
            if abs_deviation > 10:
                exploitable = True

                # Generate exploit recommendation
                if stat_name == 'vpip_pct':
                    if deviation > 0:
                        exploit = f"Plays too many hands ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: 3-bet more, value bet thin."
                    else:
                        exploit = f"Too tight ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Steal their blinds, bluff more."
                elif stat_name == 'pfr_pct':
                    if deviation > 0:
                        exploit = f"Over-aggressive preflop ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Call wider, trap with premiums."
                    else:
                        exploit = f"Passive preflop ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Bet when checked to, barrel more."
                elif stat_name == 'three_bet_pct':
                    if deviation > 0:
                        exploit = f"3-bets too much ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Call down lighter, 4-bet bluff."
                    else:
                        exploit = f"Doesn't 3-bet enough ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Open wider, flat their 3-bets."
                elif stat_name == 'fold_to_three_bet_pct':
                    if deviation > 0:
                        exploit = f"Folds to 3-bets too much ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: 3-bet them liberally."
                    else:
                        exploit = f"Doesn't fold to 3-bets enough ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Value 3-bet, avoid bluffs."
                elif stat_name == 'cbet_flop_pct':
                    if deviation > 0:
                        exploit = f"C-bets too much ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Float more, raise as bluff."
                    else:
                        exploit = f"Doesn't c-bet enough ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Bet when checked to."
                elif stat_name == 'fold_to_cbet_flop_pct':
                    if deviation > 0:
                        exploit = f"Folds to c-bets too much ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: C-bet bluff more."
                    else:
                        exploit = f"Doesn't fold to c-bets enough ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: C-bet value hands only."
                elif stat_name == 'wtsd_pct':
                    if deviation > 0:
                        exploit = f"Goes to showdown too much ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Value bet thin, avoid bluffs."
                    else:
                        exploit = f"Folds too much ({stat_value:.1f}% vs GTO {gto_mid:.1f}%). Exploit: Bluff more on all streets."
                else:
                    exploit = f"Deviates {deviation:+.1f}% from GTO baseline."

                deviations.append({
                    'stat': stat_name,
                    'player_value': stat_value,
                    'gto_baseline': gto_mid,
                    'deviation': deviation,
                    'abs_deviation': abs_deviation,
                    'exploitable': exploitable,
                    'exploit_recommendation': exploit
                })

        return {'deviations': deviations}
