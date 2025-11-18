"""
Statistical calculator for composite poker metrics.

Implements 12 advanced composite metrics for exploitative poker strategy.
All metrics are calculated from traditional statistics and stored in the
player_stats table for fast querying.
"""

from decimal import Decimal
from typing import Dict, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class StatsCalculator:
    """
    Calculator for composite poker statistics.

    Implements all 12 composite metrics as specified in the project plan.
    Each metric includes calculation, interpretation, and reliability assessment.
    """

    # Optimal VPIP ranges by position (for PAI calculation)
    OPTIMAL_VPIP = {
        'UTG': (13, 18),
        'HJ': (17, 22),
        'MP': (17, 22),
        'CO': (25, 30),
        'BTN': (43, 51),
        'SB': (30, 36),
        'BB': (35, 42)
    }

    def __init__(self, stats: Dict[str, Any]):
        """
        Initialize calculator with player statistics.

        Args:
            stats: Dictionary of traditional statistics from player_stats table
        """
        self.stats = stats
        self.total_hands = stats.get('total_hands', 0)

    def calculate_all_metrics(self) -> Dict[str, Any]:
        """
        Calculate all 12 composite metrics.

        Returns:
            Dictionary with all calculated metrics ready for database storage
        """
        metrics = {}

        # Calculate each metric
        metrics['exploitability_index'] = self.calculate_exploitability_index()
        metrics['pressure_vulnerability_score'] = self.calculate_pressure_vulnerability_score()
        metrics['aggression_consistency_ratio'] = self.calculate_aggression_consistency_ratio()
        metrics['positional_awareness_index'] = self.calculate_positional_awareness_index()
        metrics['blind_defense_efficiency'] = self.calculate_blind_defense_efficiency()
        metrics['value_bluff_imbalance_ratio'] = self.calculate_value_bluff_imbalance_ratio()
        metrics['range_polarization_factor'] = self.calculate_range_polarization_factor()
        metrics['street_fold_gradient'] = self.calculate_street_fold_gradient()
        metrics['delayed_aggression_coefficient'] = self.calculate_delayed_aggression_coefficient()
        metrics['multi_street_persistence_score'] = self.calculate_multi_street_persistence_score()
        metrics['optimal_stake_skill_rating'] = self.calculate_optimal_stake_skill_rating()
        metrics['player_type'] = self.classify_player_type()

        return metrics

    # ========================================
    # Metric 1: Exploitability Index (EI)
    # ========================================

    def calculate_exploitability_index(self) -> Optional[Decimal]:
        """
        Calculate Exploitability Index (0-100 scale).

        Formula:
        EI = (Preflop_Score × 0.35) + (Postflop_Score × 0.40) + (Showdown_Score × 0.25)

        Where:
        - Preflop_Score = |VPIP/PFR Gap - 3| × 2 + |Fold to 3bet - 55| × 0.5 + |3bet% - 7| × 1.5
        - Postflop_Score = |Flop Cbet - Turn Cbet| × 1.5 + |Fold to Cbet Flop - 55| × 0.8 + |CR Flop - 5| × 2
        - Showdown_Score = |WTSD - 27| × 1.2 + |W$SD - 51| × 0.8

        Minimum sample: 200 hands

        Returns:
            EI score (0-100) or None if insufficient data
        """
        if self.total_hands < 200:
            return None

        try:
            vpip = self._get_decimal('vpip_pct')
            pfr = self._get_decimal('pfr_pct')
            fold_to_3bet = self._get_decimal('fold_to_three_bet_pct', default=Decimal('55'))
            three_bet = self._get_decimal('three_bet_pct', default=Decimal('7'))
            cbet_flop = self._get_decimal('cbet_flop_pct', default=Decimal('65'))
            cbet_turn = self._get_decimal('cbet_turn_pct', default=Decimal('50'))
            fold_to_cbet_flop = self._get_decimal('fold_to_cbet_flop_pct', default=Decimal('55'))
            check_raise_flop = self._get_decimal('check_raise_flop_pct', default=Decimal('5'))
            wtsd = self._get_decimal('wtsd_pct', default=Decimal('27'))
            wsd = self._get_decimal('wsd_pct', default=Decimal('51'))

            if vpip is None or pfr is None:
                return None

            # Preflop Score
            vpip_pfr_gap = abs((vpip - pfr) - Decimal('3'))
            fold_3bet_dev = abs(fold_to_3bet - Decimal('55'))
            three_bet_dev = abs(three_bet - Decimal('7'))

            preflop_score = (vpip_pfr_gap * Decimal('2')) + \
                          (fold_3bet_dev * Decimal('0.5')) + \
                          (three_bet_dev * Decimal('1.5'))

            # Postflop Score
            cbet_consistency = abs(cbet_flop - cbet_turn)
            fold_cbet_dev = abs(fold_to_cbet_flop - Decimal('55'))
            cr_dev = abs(check_raise_flop - Decimal('5'))

            postflop_score = (cbet_consistency * Decimal('1.5')) + \
                           (fold_cbet_dev * Decimal('0.8')) + \
                           (cr_dev * Decimal('2'))

            # Showdown Score
            wtsd_dev = abs(wtsd - Decimal('27'))
            wsd_dev = abs(wsd - Decimal('51'))

            showdown_score = (wtsd_dev * Decimal('1.2')) + (wsd_dev * Decimal('0.8'))

            # Final EI
            ei = (preflop_score * Decimal('0.35')) + \
                 (postflop_score * Decimal('0.40')) + \
                 (showdown_score * Decimal('0.25'))

            # Clamp to 0-100
            ei = max(Decimal('0'), min(Decimal('100'), ei))

            return round(ei, 2)

        except Exception as e:
            logger.error(f"Error calculating EI: {e}")
            return None

    # ========================================
    # Metric 2: Pressure Vulnerability Score (PVS)
    # ========================================

    def calculate_pressure_vulnerability_score(self) -> Optional[Decimal]:
        """
        Calculate Pressure Vulnerability Score (0-100 scale).

        Measures susceptibility to aggressive pressure.

        Formula:
        PVS = (Fold to 3bet × 0.25) + (Fold Flop Cbet × 0.20) +
              (Fold Turn Cbet × 0.25) + (Fold River Cbet × 0.30)

        Minimum sample: 300 hands

        Returns:
            PVS score (0-100) or None
        """
        if self.total_hands < 300:
            return None

        try:
            fold_3bet = self._get_decimal('fold_to_three_bet_pct', default=Decimal('50'))
            fold_cbet_flop = self._get_decimal('fold_to_cbet_flop_pct', default=Decimal('50'))
            fold_cbet_turn = self._get_decimal('fold_to_cbet_turn_pct', default=Decimal('50'))
            fold_cbet_river = self._get_decimal('fold_to_cbet_river_pct', default=Decimal('50'))

            pvs = (fold_3bet * Decimal('0.25')) + \
                  (fold_cbet_flop * Decimal('0.20')) + \
                  (fold_cbet_turn * Decimal('0.25')) + \
                  (fold_cbet_river * Decimal('0.30'))

            return round(pvs, 2)

        except Exception as e:
            logger.error(f"Error calculating PVS: {e}")
            return None

    # ========================================
    # Metric 3: Aggression Consistency Ratio (ACR)
    # ========================================

    def calculate_aggression_consistency_ratio(self) -> Optional[Decimal]:
        """
        Calculate Aggression Consistency Ratio.

        Identifies players who give up on later streets.

        Formula:
        ACR = (Turn Cbet / Flop Cbet) × (River Cbet / Turn Cbet)

        Perfect consistency = 1.0

        Minimum sample: 250 hands

        Returns:
            ACR score or None
        """
        if self.total_hands < 250:
            return None

        try:
            cbet_flop = self._get_decimal('cbet_flop_pct')
            cbet_turn = self._get_decimal('cbet_turn_pct')
            cbet_river = self._get_decimal('cbet_river_pct')

            if not cbet_flop or cbet_flop == 0:
                return None

            if not cbet_turn or cbet_turn == 0:
                # Give up immediately after flop
                return Decimal('0.0')

            ratio1 = cbet_turn / cbet_flop
            ratio2 = cbet_river / cbet_turn if cbet_river else Decimal('0')

            acr = ratio1 * ratio2

            return round(acr, 3)

        except Exception as e:
            logger.error(f"Error calculating ACR: {e}")
            return None

    # ========================================
    # Metric 4: Positional Awareness Index (PAI)
    # ========================================

    def calculate_positional_awareness_index(self) -> Optional[Decimal]:
        """
        Calculate Positional Awareness Index.

        Measures how well player adjusts play by position.

        Formula:
        PAI = Σ |Position_VPIP - Optimal_VPIP| for all positions

        Lower score = better positional awareness

        Minimum sample: 500 hands

        Returns:
            PAI score or None
        """
        if self.total_hands < 500:
            return None

        try:
            total_deviation = Decimal('0')
            positions_checked = 0

            for pos, (opt_min, opt_max) in self.OPTIMAL_VPIP.items():
                pos_vpip = self._get_decimal(f'vpip_{pos.lower()}')

                if pos_vpip is not None:
                    optimal_mid = Decimal(str((opt_min + opt_max) / 2))
                    deviation = abs(pos_vpip - optimal_mid)
                    total_deviation += deviation
                    positions_checked += 1

            if positions_checked == 0:
                return None

            pai = total_deviation

            return round(pai, 2)

        except Exception as e:
            logger.error(f"Error calculating PAI: {e}")
            return None

    # ========================================
    # Metric 5: Blind Defense Efficiency (BDE)
    # ========================================

    def calculate_blind_defense_efficiency(self) -> Optional[Decimal]:
        """
        Calculate Blind Defense Efficiency.

        Measures quality of blind defense vs steals.

        Formula:
        BDE = (BB VPIP × 0.4) + ((100 - Fold to Steal) × 0.3) + (BB 3bet × 0.3)

        Optimal BDE: 40-50

        Minimum sample: 200 hands

        Returns:
            BDE score or None
        """
        if self.total_hands < 200:
            return None

        try:
            bb_vpip = self._get_decimal('vpip_bb', default=Decimal('35'))
            fold_to_steal = self._get_decimal('fold_to_steal_pct', default=Decimal('70'))
            three_bet_vs_steal = self._get_decimal('three_bet_vs_steal_pct', default=Decimal('10'))

            defense_rate = Decimal('100') - fold_to_steal

            bde = (bb_vpip * Decimal('0.4')) + \
                  (defense_rate * Decimal('0.3')) + \
                  (three_bet_vs_steal * Decimal('0.3'))

            return round(bde, 2)

        except Exception as e:
            logger.error(f"Error calculating BDE: {e}")
            return None

    # ========================================
    # Metric 6: Value-Bluff Imbalance Ratio (VBIR)
    # ========================================

    def calculate_value_bluff_imbalance_ratio(self) -> Optional[Decimal]:
        """
        Calculate Value-Bluff Imbalance Ratio.

        Identifies showdown value vs bluffing balance.

        Formula:
        VBIR = (W$SD - 50) / (WTSD - 27)

        Optimal: -0.5 to +0.5

        Minimum sample: 1000 hands

        Returns:
            VBIR score or None
        """
        if self.total_hands < 1000:
            return None

        try:
            wsd = self._get_decimal('wsd_pct')
            wtsd = self._get_decimal('wtsd_pct')

            if wtsd is None or wsd is None:
                return None

            wtsd_diff = wtsd - Decimal('27')

            if wtsd_diff == 0:
                return Decimal('0')

            vbir = (wsd - Decimal('50')) / wtsd_diff

            return round(vbir, 3)

        except Exception as e:
            logger.error(f"Error calculating VBIR: {e}")
            return None

    # ========================================
    # Metric 7: Range Polarization Factor (RPF)
    # ========================================

    def calculate_range_polarization_factor(self) -> Optional[Decimal]:
        """
        Calculate Range Polarization Factor.

        Measures bet sizing and range construction.

        Formula:
        RPF = (River Bet Freq / Flop Bet Freq)

        Note: Simplified version (full version requires bet sizing data)

        Minimum sample: 500 hands

        Returns:
            RPF score or None
        """
        if self.total_hands < 500:
            return None

        try:
            cbet_flop = self._get_decimal('cbet_flop_pct')
            cbet_river = self._get_decimal('cbet_river_pct')

            if not cbet_flop or cbet_flop == 0:
                return None

            rpf = cbet_river / cbet_flop if cbet_river else Decimal('0')

            return round(rpf, 3)

        except Exception as e:
            logger.error(f"Error calculating RPF: {e}")
            return None

    # ========================================
    # Metric 8: Street-by-Street Fold Gradient (SFG)
    # ========================================

    def calculate_street_fold_gradient(self) -> Optional[Decimal]:
        """
        Calculate Street-by-Street Fold Gradient.

        Measures how folding frequency changes across streets.

        Formula:
        SFG = [(Fold Flop - Fold Turn) + (Fold Turn - Fold River)] / 2

        Minimum sample: 500 hands

        Returns:
            SFG score or None
        """
        if self.total_hands < 500:
            return None

        try:
            fold_flop = self._get_decimal('fold_to_cbet_flop_pct', default=Decimal('50'))
            fold_turn = self._get_decimal('fold_to_cbet_turn_pct', default=Decimal('45'))
            fold_river = self._get_decimal('fold_to_cbet_river_pct', default=Decimal('40'))

            gradient1 = fold_flop - fold_turn
            gradient2 = fold_turn - fold_river

            sfg = (gradient1 + gradient2) / Decimal('2')

            return round(sfg, 2)

        except Exception as e:
            logger.error(f"Error calculating SFG: {e}")
            return None

    # ========================================
    # Metric 9: Delayed Aggression Coefficient (DAC)
    # ========================================

    def calculate_delayed_aggression_coefficient(self) -> Optional[Decimal]:
        """
        Calculate Delayed Aggression Coefficient.

        Measures check-raise and trap play frequency.

        Formula:
        DAC = (CR Flop × 2) + (CR Turn × 1.5) + (Float × 1)

        Optimal: 8-15

        Minimum sample: 500 hands

        Returns:
            DAC score or None
        """
        if self.total_hands < 500:
            return None

        try:
            cr_flop = self._get_decimal('check_raise_flop_pct', default=Decimal('5'))
            cr_turn = self._get_decimal('check_raise_turn_pct', default=Decimal('4'))
            float_flop = self._get_decimal('float_flop_pct', default=Decimal('3'))

            dac = (cr_flop * Decimal('2')) + \
                  (cr_turn * Decimal('1.5')) + \
                  (float_flop * Decimal('1'))

            return round(dac, 2)

        except Exception as e:
            logger.error(f"Error calculating DAC: {e}")
            return None

    # ========================================
    # Metric 10: Quick Exploit Matrix (QEM)
    # ========================================

    def classify_player_type(self) -> Optional[str]:
        """
        Classify player type using Quick Exploit Matrix.

        Classifications:
        - NIT: VPIP < 15%, PFR < 12%
        - TAG: VPIP 15-25%, PFR 12-20%, Gap < 5
        - LAG: VPIP 25-35%, PFR 18-28%, Gap < 7
        - CALLING_STATION: VPIP > 35%, Gap > 15
        - MANIAC: VPIP > 45%, PFR > 35%
        - FISH: EI > 60

        Minimum sample: 20 hands (preliminary)

        Returns:
            Player type string or None
        """
        if self.total_hands < 20:
            return None

        try:
            vpip = self._get_decimal('vpip_pct')
            pfr = self._get_decimal('pfr_pct')

            if vpip is None or pfr is None:
                return None

            gap = vpip - pfr
            ei = self.calculate_exploitability_index()

            # Check for FISH first (high EI)
            if ei and ei > Decimal('60'):
                return 'FISH'

            # MANIAC
            if vpip > Decimal('45') and pfr > Decimal('35'):
                return 'MANIAC'

            # CALLING STATION (loose passive)
            if vpip > Decimal('35') and gap > Decimal('12'):
                return 'CALLING_STATION'

            # LAG (loose aggressive)
            if vpip >= Decimal('25') and \
               pfr >= Decimal('18') and \
               gap < Decimal('12'):
                return 'LAG'

            # TAG (tight aggressive)
            if Decimal('15') <= vpip <= Decimal('25') and \
               Decimal('12') <= pfr <= Decimal('20') and \
               gap < Decimal('8'):
                return 'TAG'

            # NIT (tight passive)
            if vpip < Decimal('20') and pfr < Decimal('15') and gap > Decimal('5'):
                return 'NIT'

            # LOOSE_PASSIVE (doesn't fit other categories but loose)
            if vpip > Decimal('30'):
                return 'LOOSE_PASSIVE'

            # TIGHT (doesn't fit other categories but tight)
            if vpip < Decimal('25'):
                return 'TIGHT'

            # Unknown / Balanced
            return 'UNKNOWN'

        except Exception as e:
            logger.error(f"Error classifying player type: {e}")
            return None

    # ========================================
    # Metric 11: Multi-Street Persistence Score (MPS)
    # ========================================

    def calculate_multi_street_persistence_score(self) -> Optional[Decimal]:
        """
        Calculate Multi-Street Persistence Score.

        Measures commitment level across betting streets.

        Formula (simplified):
        MPS = (Turn Cbet / Flop Cbet + River Cbet / Turn Cbet) / 2 × 100

        Optimal: 55-65%

        Minimum sample: 350 hands

        Returns:
            MPS percentage or None
        """
        if self.total_hands < 350:
            return None

        try:
            cbet_flop = self._get_decimal('cbet_flop_pct')
            cbet_turn = self._get_decimal('cbet_turn_pct')
            cbet_river = self._get_decimal('cbet_river_pct')

            if not cbet_flop or cbet_flop == 0:
                return None

            persistence1 = (cbet_turn / cbet_flop) if cbet_turn else Decimal('0')
            persistence2 = (cbet_river / cbet_turn) if cbet_turn and cbet_river else Decimal('0')

            mps = ((persistence1 + persistence2) / Decimal('2')) * Decimal('100')

            return round(mps, 2)

        except Exception as e:
            logger.error(f"Error calculating MPS: {e}")
            return None

    # ========================================
    # Metric 12: Optimal Stake Threshold Model
    # ========================================

    def calculate_optimal_stake_skill_rating(self) -> Optional[Decimal]:
        """
        Calculate Optimal Stake Skill Rating.

        Determines skill level for stake matching.

        Formula:
        Skill = (100 - EI) + (PAI × -5) + (BDE - 30) + (|W$SD - 51| × -2)

        Minimum sample: 1000 hands

        Returns:
            Skill rating (0-100) or None
        """
        if self.total_hands < 1000:
            return None

        try:
            ei = self.calculate_exploitability_index()
            pai = self.calculate_positional_awareness_index()
            bde = self.calculate_blind_defense_efficiency()
            wsd = self._get_decimal('wsd_pct')

            if ei is None:
                return None

            skill = Decimal('100') - ei

            if pai:
                skill += pai * Decimal('-5')

            if bde:
                skill += bde - Decimal('30')

            if wsd:
                wsd_dev = abs(wsd - Decimal('51'))
                skill += wsd_dev * Decimal('-2')

            # Clamp to 0-100
            skill = max(Decimal('0'), min(Decimal('100'), skill))

            return round(skill, 2)

        except Exception as e:
            logger.error(f"Error calculating skill rating: {e}")
            return None

    # ========================================
    # Helper Methods
    # ========================================

    def _get_decimal(self, key: str, default: Optional[Decimal] = None) -> Optional[Decimal]:
        """
        Get statistic as Decimal, with optional default.

        Args:
            key: Statistic key
            default: Default value if missing

        Returns:
            Decimal value or None
        """
        value = self.stats.get(key)

        if value is None:
            return default

        if isinstance(value, Decimal):
            return value

        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return default

    def get_sample_reliability(self, metric: str) -> str:
        """
        Get reliability level for a metric based on sample size.

        Args:
            metric: Metric name

        Returns:
            Reliability level string
        """
        # Sample size requirements from project plan
        requirements = {
            'exploitability_index': 200,
            'pressure_vulnerability_score': 300,
            'aggression_consistency_ratio': 250,
            'positional_awareness_index': 500,
            'blind_defense_efficiency': 200,
            'value_bluff_imbalance_ratio': 1000,
            'range_polarization_factor': 500,
            'street_fold_gradient': 500,
            'delayed_aggression_coefficient': 500,
            'player_type': 20,
            'multi_street_persistence_score': 350,
            'optimal_stake_skill_rating': 1000
        }

        required = requirements.get(metric, 500)

        if self.total_hands < required * 0.5:
            return 'insufficient'
        elif self.total_hands < required:
            return 'preliminary'
        elif self.total_hands < required * 2:
            return 'moderate'
        elif self.total_hands < required * 3:
            return 'high'
        else:
            return 'very_high'
