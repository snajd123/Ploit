"""
Statistical calculator for composite poker metrics.

Implements 5 core composite metrics for exploitative poker strategy.
All metrics are calculated from traditional statistics and stored in the
player_stats table for fast querying.

Version 2.0 - Recalibrated with real GTO baselines and confidence intervals.
"""

from decimal import Decimal
from typing import Dict, Optional, Any, Tuple, List
import logging

from backend.services.gto_baselines import (
    PREFLOP_GLOBAL,
    get_baseline, analyze_deviation, get_exploit_recommendation,
    DEVIATION_THRESHOLDS
)
from backend.services.confidence_calculator import (
    calculate_stat_confidence, wilson_score_interval, get_reliability_level
)

logger = logging.getLogger(__name__)


class StatsCalculator:
    """
    Calculator for composite poker statistics.

    Version 2.0 - Implements 5 core metrics with:
    - Calibrated GTO baselines from real solver output
    - Confidence interval support
    - Non-overlapping player classification

    Core Metrics:
    1. Exploitability Score (0-100) - Overall exploitability
    2. Aggression Profile - Passive/Balanced/Aggressive classification
    3. Positional Awareness Index - How well they adjust by position
    4. Showdown Tendencies - Station/Balanced/Nitty
    5. Pressure Response - How they respond to aggression

    Legacy metrics (ACR, RPF, SFG, etc.) still calculated for compatibility.
    """

    # Calibrated VPIP ranges by position (from GTOWizard 6-max 100bb)
    OPTIMAL_VPIP = {
        'UTG': (15, 19),    # ~17% GTO
        'HJ': (19, 23),     # ~21% GTO
        'MP': (19, 23),     # ~21% GTO (same as HJ for 6-max)
        'CO': (25, 31),     # ~28% GTO
        'BTN': (42, 52),    # ~47% GTO
        'SB': (38, 46),     # ~42% GTO
        'BB': (35, 42)      # ~38% GTO (defense rate)
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
        Calculate preflop-focused composite metrics.

        Returns:
            Dictionary with all calculated metrics ready for database storage
        """
        metrics = {}

        # Calculate preflop-only metrics
        metrics['exploitability_index'] = self.calculate_exploitability_index()
        metrics['positional_awareness_index'] = self.calculate_positional_awareness_index()
        metrics['blind_defense_efficiency'] = self.calculate_blind_defense_efficiency()
        metrics['optimal_stake_skill_rating'] = self.calculate_optimal_stake_skill_rating()
        metrics['player_type'] = self.classify_player_type()

        return metrics

    # ========================================
    # Metric 1: Exploitability Index (EI) - RECALIBRATED
    # ========================================

    def calculate_exploitability_index(self) -> Optional[Decimal]:
        """
        Calculate Exploitability Index (0-100 scale) using calibrated GTO baselines.

        PREFLOP-ONLY VERSION:
        EI = Preflop_Score (100% weight)

        Calibrated baselines (from GTOWizard 6-max 100bb):
        - VPIP/PFR gap: GTO ~4%
        - Fold to 3bet: GTO ~48%
        - 3-bet%: GTO ~7%
        - 4-bet%: GTO ~2.5%
        - Cold call: GTO ~5%

        Minimum sample: 200 hands

        Returns:
            EI score (0-100) or None if insufficient data
        """
        if self.total_hands < 200:
            return None

        try:
            vpip = self._get_decimal('vpip_pct')
            pfr = self._get_decimal('pfr_pct')

            if vpip is None or pfr is None:
                return None

            # Get player stats with defaults from calibrated baselines
            fold_to_3bet = self._get_decimal('fold_to_three_bet_pct',
                default=Decimal(str(PREFLOP_GLOBAL['fold_to_three_bet'])))
            three_bet = self._get_decimal('three_bet_pct',
                default=Decimal(str(PREFLOP_GLOBAL['three_bet'])))
            four_bet = self._get_decimal('four_bet_pct',
                default=Decimal(str(PREFLOP_GLOBAL['four_bet'])))
            cold_call = self._get_decimal('cold_call_pct',
                default=Decimal(str(PREFLOP_GLOBAL['cold_call'])))

            # === VPIP/PFR Gap Score (25% weight) ===
            gto_gap = Decimal(str(PREFLOP_GLOBAL['vpip_pfr_gap']))
            actual_gap = vpip - pfr
            gap_deviation = abs(actual_gap - gto_gap)
            gap_score = min(gap_deviation / Decimal('10'), Decimal('1')) * Decimal('100')

            # === Fold to 3-bet Score (25% weight) ===
            gto_fold_3bet = Decimal(str(PREFLOP_GLOBAL['fold_to_three_bet']))
            fold_3bet_deviation = abs(fold_to_3bet - gto_fold_3bet)
            fold_3bet_score = min(fold_3bet_deviation / Decimal('20'), Decimal('1')) * Decimal('100')

            # === 3-bet Score (20% weight) ===
            gto_3bet = Decimal(str(PREFLOP_GLOBAL['three_bet']))
            three_bet_deviation = abs(three_bet - gto_3bet)
            three_bet_score = min(three_bet_deviation / Decimal('5'), Decimal('1')) * Decimal('100')

            # === 4-bet Score (15% weight) ===
            gto_4bet = Decimal(str(PREFLOP_GLOBAL['four_bet']))
            four_bet_deviation = abs(four_bet - gto_4bet)
            four_bet_score = min(four_bet_deviation / Decimal('3'), Decimal('1')) * Decimal('100')

            # === Cold Call Score (15% weight) ===
            gto_cold_call = Decimal(str(PREFLOP_GLOBAL['cold_call']))
            cold_call_deviation = abs(cold_call - gto_cold_call)
            cold_call_score = min(cold_call_deviation / Decimal('5'), Decimal('1')) * Decimal('100')

            # === Final EI (weighted sum) ===
            ei = (
                gap_score * Decimal('0.25') +
                fold_3bet_score * Decimal('0.25') +
                three_bet_score * Decimal('0.20') +
                four_bet_score * Decimal('0.15') +
                cold_call_score * Decimal('0.15')
            )

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
    # Metric 10: Player Type Classification - FIXED V2.0
    # ========================================

    def classify_player_type(self) -> Optional[str]:
        """
        Classify player type using non-overlapping decision tree.

        V2.0 - Fixed overlapping criteria using clear decision boundaries:

        Step 1: Check for extreme exploitable (FISH) - EI > 60
        Step 2: Determine tightness (VPIP threshold: 22% = boundary)
        Step 3: Determine aggression (PFR/VPIP ratio threshold: 0.65)
        Step 4: Combine into player type

        Classifications (non-overlapping):
        - FISH: EI > 60 (regardless of other stats)
        - MANIAC: VPIP > 40 AND PFR > 32
        - CALLING_STATION: VPIP > 28 AND PFR/VPIP < 0.5 (very passive loose)
        - LAG: VPIP > 28 AND PFR/VPIP >= 0.65
        - LOOSE_PASSIVE: VPIP > 28 AND 0.5 <= PFR/VPIP < 0.65
        - TAG: VPIP 18-28 AND PFR/VPIP >= 0.70
        - NIT: VPIP < 18 AND PFR/VPIP >= 0.65
        - TIGHT_PASSIVE: VPIP < 28 AND PFR/VPIP < 0.65
        - UNKNOWN: Insufficient data or edge cases

        Minimum sample: 100 hands (was 20 - too unreliable)

        Returns:
            Player type string or None
        """
        if self.total_hands < 100:
            return 'UNKNOWN'  # Need at least 100 hands for any classification

        try:
            vpip = self._get_decimal('vpip_pct')
            pfr = self._get_decimal('pfr_pct')

            if vpip is None or pfr is None:
                return 'UNKNOWN'

            # Calculate aggression ratio (PFR/VPIP)
            aggression_ratio = float(pfr / vpip) if vpip > 0 else 0.0
            vpip_f = float(vpip)
            pfr_f = float(pfr)
            gap = vpip_f - pfr_f

            # Step 1: Check for extreme exploitable (FISH)
            # Only check EI if we have enough hands
            if self.total_hands >= 200:
                ei = self.calculate_exploitability_index()
                if ei and float(ei) > 60:
                    return 'FISH'

            # Step 2: Check for extreme aggression (MANIAC)
            if vpip_f > 40 and pfr_f > 32:
                return 'MANIAC'

            # Step 3: Classify based on tightness and aggression
            # Using clear, non-overlapping boundaries

            # LOOSE players (VPIP > 28%)
            if vpip_f > 28:
                if aggression_ratio < 0.50:
                    # Very passive - calls too much
                    return 'CALLING_STATION'
                elif aggression_ratio >= 0.65:
                    # Aggressive but wide
                    return 'LAG'
                else:
                    # In between - loose but not super passive or aggressive
                    return 'LOOSE_PASSIVE'

            # TIGHT/NORMAL players (VPIP <= 28%)
            else:
                # Very tight (VPIP < 18%)
                if vpip_f < 18:
                    if aggression_ratio >= 0.65:
                        # Tight but aggressive when playing
                        return 'NIT'  # Traditional NIT (tight, but raises when entering)
                    else:
                        # Tight AND passive - super nit
                        return 'NIT'

                # Normal range (VPIP 18-28%)
                else:
                    if aggression_ratio >= 0.70:
                        # Standard tight-aggressive
                        return 'TAG'
                    elif aggression_ratio >= 0.55:
                        # Slightly passive but acceptable
                        return 'TAG'  # Still TAG, just not optimal
                    else:
                        # Too passive for the VPIP
                        return 'TIGHT_PASSIVE'

        except Exception as e:
            logger.error(f"Error classifying player type: {e}")
            return 'UNKNOWN'

    def get_player_type_details(self) -> Dict[str, Any]:
        """
        Get detailed player type analysis with confidence and exploits.

        Returns:
            Dictionary with type, confidence, and recommended exploits
        """
        player_type = self.classify_player_type()
        vpip = self._get_decimal('vpip_pct')
        pfr = self._get_decimal('pfr_pct')

        if vpip is None or pfr is None:
            return {"type": "UNKNOWN", "confidence": "insufficient", "exploits": []}

        aggression_ratio = float(pfr / vpip) if vpip > 0 else 0.0

        # Type-specific exploit recommendations
        exploits_by_type = {
            'FISH': [
                "Value bet relentlessly - they call too much",
                "Reduce bluffing frequency significantly",
                "Isolate them preflop with wider value range"
            ],
            'MANIAC': [
                "Tighten up and let them hang themselves",
                "Call down lighter with medium-strength hands",
                "Trap with strong hands instead of raising"
            ],
            'CALLING_STATION': [
                "Never bluff - they don't fold",
                "Value bet thinner (top pair is usually good)",
                "Size up your value bets"
            ],
            'LAG': [
                "3-bet lighter for value",
                "Don't give them free cards",
                "Be prepared to call down wider"
            ],
            'LOOSE_PASSIVE': [
                "Value bet aggressively on all streets",
                "Reduce bluffs but don't eliminate",
                "Isolate preflop"
            ],
            'TAG': [
                "Respect their raises more",
                "Look for small exploits in specific spots",
                "Avoid marginal situations"
            ],
            'NIT': [
                "Steal relentlessly",
                "Fold to their aggression (they have it)",
                "Don't pay off their value bets"
            ],
            'TIGHT_PASSIVE': [
                "Steal more preflop",
                "Bluff more postflop (they fold too much)",
                "Respect their rare raises"
            ],
        }

        # Confidence based on sample size
        if self.total_hands < 200:
            confidence = "low"
        elif self.total_hands < 500:
            confidence = "moderate"
        elif self.total_hands < 1000:
            confidence = "good"
        else:
            confidence = "high"

        return {
            "type": player_type,
            "confidence": confidence,
            "sample_size": self.total_hands,
            "vpip": float(vpip) if vpip else None,
            "pfr": float(pfr) if pfr else None,
            "aggression_ratio": round(aggression_ratio, 2),
            "exploits": exploits_by_type.get(player_type, [])
        }

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

    # ========================================
    # NEW V2.0: Core Metrics Summary
    # ========================================

    def get_core_metrics(self) -> Dict[str, Any]:
        """
        Get the 5 core metrics that matter most for exploit finding.

        Returns a simplified, actionable summary instead of 12+ confusing metrics.

        Core Metrics:
        1. exploitability_score: Overall how exploitable (0-100)
        2. aggression_profile: passive/balanced/aggressive
        3. positional_awareness: poor/average/good
        4. showdown_tendency: station/balanced/folder
        5. pressure_response: folds/calls/fights

        Returns:
            Dictionary with 5 core metrics and their interpretations
        """
        vpip = self._get_decimal('vpip_pct')
        pfr = self._get_decimal('pfr_pct')
        fold_to_3bet = self._get_decimal('fold_to_three_bet_pct')
        fold_to_cbet = self._get_decimal('fold_to_cbet_flop_pct')
        wtsd = self._get_decimal('wtsd_pct')
        wsd = self._get_decimal('wsd_pct')

        # 1. Exploitability Score
        ei = self.calculate_exploitability_index()
        ei_interpretation = "unknown"
        if ei is not None:
            ei_val = float(ei)
            if ei_val < 25:
                ei_interpretation = "tough"
            elif ei_val < 40:
                ei_interpretation = "solid"
            elif ei_val < 55:
                ei_interpretation = "exploitable"
            else:
                ei_interpretation = "very_exploitable"

        # 2. Aggression Profile
        aggression_ratio = float(pfr / vpip) if vpip and vpip > 0 else 0.5
        if aggression_ratio < 0.55:
            aggression_profile = "passive"
        elif aggression_ratio < 0.75:
            aggression_profile = "balanced"
        else:
            aggression_profile = "aggressive"

        # 3. Positional Awareness
        pai = self.calculate_positional_awareness_index()
        if pai is None:
            positional_awareness = "unknown"
        elif float(pai) < 15:
            positional_awareness = "good"
        elif float(pai) < 30:
            positional_awareness = "average"
        else:
            positional_awareness = "poor"

        # 4. Showdown Tendency (preflop-only: using fixed baseline)
        if wtsd is None:
            showdown_tendency = "unknown"
        else:
            wtsd_val = float(wtsd)
            gto_wtsd = 28.0  # GTO WTSD baseline
            if wtsd_val > gto_wtsd + 8:
                showdown_tendency = "station"  # Goes to showdown too much
            elif wtsd_val < gto_wtsd - 8:
                showdown_tendency = "folder"  # Gives up too easily
            else:
                showdown_tendency = "balanced"

        # 5. Pressure Response
        if fold_to_3bet is None and fold_to_cbet is None:
            pressure_response = "unknown"
        else:
            avg_fold = 0
            count = 0
            if fold_to_3bet:
                avg_fold += float(fold_to_3bet)
                count += 1
            if fold_to_cbet:
                avg_fold += float(fold_to_cbet)
                count += 1
            avg_fold = avg_fold / count if count > 0 else 50

            if avg_fold > 55:
                pressure_response = "folds"
            elif avg_fold < 40:
                pressure_response = "fights"
            else:
                pressure_response = "balanced"

        return {
            "exploitability_score": {
                "value": float(ei) if ei else None,
                "interpretation": ei_interpretation,
                "description": self._get_ei_description(ei_interpretation)
            },
            "aggression_profile": {
                "value": round(aggression_ratio, 2),
                "interpretation": aggression_profile,
                "description": self._get_aggression_description(aggression_profile)
            },
            "positional_awareness": {
                "value": float(pai) if pai else None,
                "interpretation": positional_awareness,
                "description": self._get_position_description(positional_awareness)
            },
            "showdown_tendency": {
                "value": float(wtsd) if wtsd else None,
                "interpretation": showdown_tendency,
                "description": self._get_showdown_description(showdown_tendency)
            },
            "pressure_response": {
                "value": round(avg_fold, 1) if 'avg_fold' in dir() else None,
                "interpretation": pressure_response,
                "description": self._get_pressure_description(pressure_response)
            },
            "sample_size": self.total_hands,
            "overall_reliability": self._get_overall_reliability()
        }

    def _get_ei_description(self, interpretation: str) -> str:
        descriptions = {
            "tough": "Solid player with few exploitable tendencies",
            "solid": "Good fundamentals, minor leaks possible",
            "exploitable": "Multiple exploitable tendencies identified",
            "very_exploitable": "Significant leaks - high profit potential",
            "unknown": "Insufficient data"
        }
        return descriptions.get(interpretation, "")

    def _get_aggression_description(self, interpretation: str) -> str:
        descriptions = {
            "passive": "Calls more than raises - value bet wider",
            "balanced": "Healthy aggression ratio",
            "aggressive": "Raises frequently - trap more, call down lighter"
        }
        return descriptions.get(interpretation, "")

    def _get_position_description(self, interpretation: str) -> str:
        descriptions = {
            "good": "Adjusts well by position",
            "average": "Some positional awareness",
            "poor": "Plays same range regardless of position",
            "unknown": "Insufficient data"
        }
        return descriptions.get(interpretation, "")

    def _get_showdown_description(self, interpretation: str) -> str:
        descriptions = {
            "station": "Goes to showdown too often - value bet thin, don't bluff",
            "balanced": "Reasonable showdown frequency",
            "folder": "Gives up before showdown - bluff more on later streets",
            "unknown": "Insufficient data"
        }
        return descriptions.get(interpretation, "")

    def _get_pressure_description(self, interpretation: str) -> str:
        descriptions = {
            "folds": "Folds too much to aggression - apply pressure",
            "balanced": "Reasonable defense frequency",
            "fights": "Rarely folds to aggression - value bet only",
            "unknown": "Insufficient data"
        }
        return descriptions.get(interpretation, "")

    def _get_overall_reliability(self) -> str:
        if self.total_hands < 100:
            return "insufficient"
        elif self.total_hands < 300:
            return "low"
        elif self.total_hands < 700:
            return "moderate"
        elif self.total_hands < 1500:
            return "good"
        else:
            return "high"

    # ========================================
    # NEW V2.0: Detailed Leak Analysis
    # ========================================

    def get_leak_analysis(self) -> Dict[str, Any]:
        """
        Analyze player leaks using calibrated GTO baselines.

        Returns prioritized list of leaks with:
        - Deviation from GTO
        - Severity (minor/moderate/major/critical)
        - Specific exploit recommendations
        - Estimated EV impact

        Returns:
            Dictionary with leak analysis and recommendations
        """
        leaks = []

        # Preflop-only stats with GTO baselines
        stat_mappings = [
            ('vpip_pct', 'vpip', PREFLOP_GLOBAL['vpip']),
            ('pfr_pct', 'pfr', PREFLOP_GLOBAL['pfr']),
            ('three_bet_pct', 'three_bet', PREFLOP_GLOBAL['three_bet']),
            ('fold_to_three_bet_pct', 'fold_to_three_bet', PREFLOP_GLOBAL['fold_to_three_bet']),
            ('four_bet_pct', 'four_bet', PREFLOP_GLOBAL['four_bet']),
            ('cold_call_pct', 'cold_call', PREFLOP_GLOBAL['cold_call']),
        ]

        for db_key, stat_name, baseline in stat_mappings:
            player_val = self._get_decimal(db_key)
            if player_val is None:
                continue

            deviation = float(player_val) - baseline
            abs_deviation = abs(deviation)
            direction = "high" if deviation > 0 else "low"

            # Get severity thresholds
            thresholds = DEVIATION_THRESHOLDS.get(stat_name, {
                "minor": 5, "moderate": 10, "major": 20, "critical": 30
            })

            if abs_deviation < thresholds.get("minor", 5):
                continue  # Not a leak

            if abs_deviation >= thresholds.get("critical", 30):
                severity = "critical"
            elif abs_deviation >= thresholds.get("major", 20):
                severity = "major"
            elif abs_deviation >= thresholds.get("moderate", 10):
                severity = "moderate"
            else:
                severity = "minor"

            # Get exploit recommendation
            recommendation = get_exploit_recommendation(stat_name, direction)

            # Estimate EV impact (simplified)
            ev_factor = recommendation.get("ev_factor", 0.02)
            ev_impact = abs_deviation * ev_factor

            leaks.append({
                "stat": stat_name,
                "player_value": float(player_val),
                "gto_baseline": baseline,
                "deviation": round(deviation, 1),
                "direction": direction,
                "severity": severity,
                "tendency": recommendation.get("tendency", f"{stat_name} is {direction}"),
                "exploit": recommendation.get("exploit", "Adjust accordingly"),
                "ev_impact_bb_100": round(ev_impact, 2)
            })

        # Sort by severity and EV impact
        severity_order = {"critical": 0, "major": 1, "moderate": 2, "minor": 3}
        leaks.sort(key=lambda x: (severity_order.get(x["severity"], 4), -x["ev_impact_bb_100"]))

        # Calculate total exploitable EV
        total_ev = sum(leak["ev_impact_bb_100"] for leak in leaks)

        return {
            "leaks": leaks[:10],  # Top 10 leaks
            "total_leaks": len(leaks),
            "critical_leaks": len([l for l in leaks if l["severity"] == "critical"]),
            "major_leaks": len([l for l in leaks if l["severity"] == "major"]),
            "total_ev_opportunity_bb_100": round(total_ev, 2),
            "sample_size": self.total_hands,
            "reliability": self._get_overall_reliability()
        }
