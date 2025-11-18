"""
Comprehensive poker theory baselines for exploit detection.

This module contains ~150 baseline statistics derived from modern poker theory,
GTO approximations, and statistical analysis. Used when GTO solutions are not
available or as a fallback for exploit detection.

Sources:
- Modern Poker Theory (Acevedo)
- Upswing Poker Charts
- GTO Wizard Aggregates
- PokerStrategy.com Research
- Statistical analysis from millions of hands
"""

from typing import Dict, Optional, Tuple
from decimal import Decimal

# ============================================================================
# PREFLOP FREQUENCIES
# ============================================================================

# Raise First In (RFI) frequencies by position (% of hands opened)
RFI_FREQUENCIES = {
    "UTG": 14.5,
    "UTG+1": 16.0,
    "MP": 18.5,
    "LJ": 20.0,
    "HJ": 22.0,
    "CO": 26.5,
    "BTN": 47.0,
    "SB": 33.0,
}

# 3-bet frequencies when facing an open (% of time)
THREE_BET_FREQUENCIES = {
    "MP_vs_UTG": 5.5,
    "CO_vs_UTG": 6.0,
    "BTN_vs_UTG": 7.5,
    "SB_vs_UTG": 8.0,
    "BB_vs_UTG": 9.5,

    "CO_vs_MP": 7.0,
    "BTN_vs_MP": 9.0,
    "SB_vs_MP": 9.5,
    "BB_vs_MP": 11.0,

    "BTN_vs_CO": 10.5,
    "SB_vs_CO": 10.0,
    "BB_vs_CO": 12.5,

    "SB_vs_BTN": 9.0,
    "BB_vs_BTN": 12.0,

    "BB_vs_SB": 11.5,
}

# Fold to 3-bet frequencies (% of time original raiser folds)
FOLD_TO_3BET = {
    "UTG_vs_MP": 65,
    "UTG_vs_CO": 63,
    "UTG_vs_BTN": 61,
    "UTG_vs_SB": 59,
    "UTG_vs_BB": 58,

    "MP_vs_CO": 63,
    "MP_vs_BTN": 60,
    "MP_vs_SB": 58,
    "MP_vs_BB": 56,

    "CO_vs_BTN": 62,
    "CO_vs_SB": 59,
    "CO_vs_BB": 57,

    "BTN_vs_SB": 61,
    "BTN_vs_BB": 58,

    "SB_vs_BB": 60,

    # Averages by position
    "UTG_average": 61,
    "MP_average": 59,
    "CO_average": 59,
    "BTN_average": 60,
    "SB_average": 60,
}

# Cold call frequencies (calling an open without 3-betting)
COLD_CALL_FREQUENCIES = {
    "BB_vs_BTN": 32,
    "BB_vs_SB": 28,
    "SB_vs_BTN": 18,
    "BTN_vs_CO": 15,
    "CO_vs_MP": 12,
}

# 4-bet frequencies (when facing a 3-bet)
FOUR_BET_FREQUENCIES = {
    "vs_IP_3bet": 11,
    "vs_OOP_3bet": 13,
    "BTN_vs_BB_3bet": 12,
    "UTG_vs_MP_3bet": 14,
}

# Fold to 4-bet
FOLD_TO_4BET = {
    "IP_average": 68,
    "OOP_average": 72,
    "vs_tight_opener": 75,
    "vs_loose_opener": 65,
}

# ============================================================================
# POSTFLOP C-BETTING
# ============================================================================

# C-bet frequencies by street and position
CBET_FREQUENCIES = {
    # Flop
    "IP_flop_single_raised": 65,
    "IP_flop_3bet_pot": 70,
    "OOP_flop_single_raised": 55,
    "OOP_flop_3bet_pot": 60,
    "IP_flop_multiway": 40,
    "OOP_flop_multiway": 35,

    # Turn
    "IP_turn_after_cbet": 52,
    "OOP_turn_after_cbet": 42,
    "IP_turn_delayed": 35,
    "OOP_turn_delayed": 25,

    # River
    "IP_river_after_double_barrel": 45,
    "OOP_river_after_double_barrel": 38,
    "IP_river_delayed": 28,
}

# Fold to c-bet frequencies
FOLD_TO_CBET = {
    # Flop
    "OOP_flop_single_raised": 48,
    "OOP_flop_3bet_pot": 42,
    "IP_flop_single_raised": 42,
    "IP_flop_3bet_pot": 38,
    "multiway_flop": 52,

    # Turn
    "OOP_turn": 52,
    "IP_turn": 46,
    "turn_after_call_flop": 55,

    # River
    "OOP_river": 58,
    "IP_river": 52,
}

# Check-raise frequencies
CHECK_RAISE_FREQUENCIES = {
    "flop_OOP_SRP": 8,
    "flop_OOP_3bet": 10,
    "turn_OOP_SRP": 6,
    "turn_OOP_3bet": 8,
    "river_OOP": 5,
}

# ============================================================================
# AGGRESSION METRICS
# ============================================================================

AGGRESSION_BASELINES = {
    # Aggression Factor (AF) by street
    "AF_overall": 2.5,
    "AF_preflop": 3.0,
    "AF_flop": 2.8,
    "AF_turn": 2.3,
    "AF_river": 2.0,

    # Bet vs Check when IP
    "IP_flop_bet_frequency": 58,
    "IP_turn_bet_frequency": 48,
    "IP_river_bet_frequency": 42,

    # Donk bet frequencies (betting OOP into IP)
    "donk_bet_flop": 5,
    "donk_bet_turn": 7,
    "donk_bet_river": 9,
}

# ============================================================================
# SHOWDOWN & OVERALL METRICS
# ============================================================================

SHOWDOWN_BASELINES = {
    "VPIP": 23,                    # Voluntarily Put $ In Pot
    "PFR": 18,                     # Pre-flop Raise
    "VPIP_PFR_gap": 5,             # Optimal gap between VPIP and PFR

    "WTSD": 27,                    # Went to Showdown
    "W$SD": 51,                    # Won $ at Showdown

    "steal_attempt": 38,           # Steal from CO/BTN/SB
    "fold_to_steal": 67,           # Fold when facing steal

    "limp_percentage": 3,          # Optimal limp % (very low)
    "limp_fold": 85,               # Fold after limping when raised
}

# ============================================================================
# POSITION-SPECIFIC RANGES (String notation)
# ============================================================================

OPENING_RANGES = {
    "UTG": "88+,A9s+,KTs+,QTs+,JTs,ATo+,KQo",
    "MP": "77+,A7s+,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo",
    "CO": "66+,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,65s,A9o+,KTo+,QTo+,JTo",
    "BTN": "22+,A2s+,K2s+,Q6s+,J7s+,T7s+,97s+,86s+,75s+,64s+,54s,A2o+,K9o+,Q9o+,J9o+,T9o",
    "SB": "22+,A2s+,K2s+,Q2s+,J6s+,T6s+,96s+,85s+,75s+,64s+,54s,A2o+,K8o+,Q9o+,J9o+,T9o",
}

DEFENSE_RANGES = {
    "BB_vs_UTG": "99+,ATs+,KQs,AJo+,KQo",
    "BB_vs_MP": "88+,A9s+,KTs+,QJs,ATo+,KJo+",
    "BB_vs_CO": "77+,A7s+,K9s+,Q9s+,J9s+,T9s,A9o+,KTo+,QJo",
    "BB_vs_BTN": "22+,A2s+,K5s+,Q8s+,J8s+,T7s+,96s+,86s+,75s+,65s,54s,A7o+,K9o+,Q9o+,JTo",
    "BB_vs_SB": "22+,A2s+,K2s+,Q5s+,J7s+,T7s+,96s+,86s+,75s+,65s,54s,A5o+,K8o+,Q9o+,JTo",
    "SB_vs_BTN": "55+,A3s+,K7s+,Q8s+,J8s+,T8s+,97s+,87s,76s,A7o+,K9o+,Q9o+,JTo",
}

THREE_BET_RANGES = {
    "BB_vs_BTN": "77+,A7s+,K9s+,Q9s+,J9s+,T9s,A9o+,KTo+,QJo",
    "BB_vs_CO": "88+,A9s+,KTs+,QJs,ATo+,KJo+",
    "BB_vs_MP": "99+,ATs+,KQs,AJo+,KQo",
    "SB_vs_BTN": "66+,A5s+,K8s+,Q9s+,J8s+,T8s+,97s+,A8o+,K9o+,Q9o+",
}

# ============================================================================
# EXPLOIT-SPECIFIC BASELINES
# ============================================================================

EXPLOIT_BASELINES = {
    # Steal scenarios
    "BTN_steal_success": 67,
    "CO_steal_success": 65,
    "SB_steal_success": 62,

    # Squeeze scenarios
    "squeeze_frequency": 8,
    "fold_to_squeeze": 72,

    # Multi-way
    "multiway_showdown_rate": 35,
    "multiway_fold_to_cbet": 55,

    # Stack depth adjustments (BB)
    "short_stack_VPIP": 15,      # <30BB
    "medium_stack_VPIP": 23,     # 30-100BB
    "deep_stack_VPIP": 28,       # >100BB
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

class BaselineProvider:
    """Provides baseline poker statistics for exploit detection"""

    @staticmethod
    def get_rfi_frequency(position: str) -> Optional[float]:
        """Get optimal RFI frequency for position"""
        return RFI_FREQUENCIES.get(position.upper())

    @staticmethod
    def get_3bet_frequency(hero_pos: str, villain_pos: str) -> Optional[float]:
        """Get optimal 3bet frequency for hero vs villain position"""
        key = f"{hero_pos.upper()}_vs_{villain_pos.upper()}"
        return THREE_BET_FREQUENCIES.get(key)

    @staticmethod
    def get_fold_to_3bet(position: str, vs_position: Optional[str] = None) -> float:
        """Get optimal fold to 3bet frequency"""
        if vs_position:
            key = f"{position.upper()}_vs_{vs_position.upper()}"
            baseline = FOLD_TO_3BET.get(key)
            if baseline:
                return baseline

        # Fall back to position average
        avg_key = f"{position.upper()}_average"
        return FOLD_TO_3BET.get(avg_key, 60)

    @staticmethod
    def get_cbet_frequency(position: str, street: str, pot_type: str = "single_raised") -> float:
        """Get optimal cbet frequency"""
        key = f"{position.lower()}_{street.lower()}_{pot_type}"
        return CBET_FREQUENCIES.get(key, 50)

    @staticmethod
    def get_fold_to_cbet(position: str, street: str, pot_type: str = "single_raised") -> float:
        """Get optimal fold to cbet frequency"""
        key = f"{position.lower()}_{street.lower()}_{pot_type}"
        return FOLD_TO_CBET.get(key, 50)

    @staticmethod
    def get_opening_range(position: str) -> Optional[str]:
        """Get opening range for position"""
        return OPENING_RANGES.get(position.upper())

    @staticmethod
    def get_defense_range(position: str, vs_position: str) -> Optional[str]:
        """Get defense range"""
        key = f"{position.upper()}_vs_{vs_position.upper()}"
        return DEFENSE_RANGES.get(key)

    @staticmethod
    def get_vpip_range(position: str) -> Tuple[float, float]:
        """Get optimal VPIP range for position"""
        vpip_ranges = {
            'UTG': (13, 18),
            'UTG+1': (15, 20),
            'MP': (17, 22),
            'HJ': (19, 24),
            'LJ': (19, 24),
            'CO': (25, 30),
            'BTN': (43, 51),
            'SB': (30, 36),
            'BB': (35, 42)
        }
        return vpip_ranges.get(position.upper(), (20, 25))

    @staticmethod
    def get_baseline_stats() -> Dict:
        """Get all baseline statistics"""
        return {
            "rfi_frequencies": RFI_FREQUENCIES,
            "three_bet_frequencies": THREE_BET_FREQUENCIES,
            "fold_to_3bet": FOLD_TO_3BET,
            "cbet_frequencies": CBET_FREQUENCIES,
            "fold_to_cbet": FOLD_TO_CBET,
            "aggression": AGGRESSION_BASELINES,
            "showdown": SHOWDOWN_BASELINES,
            "opening_ranges": OPENING_RANGES,
            "defense_ranges": DEFENSE_RANGES,
        }

    @staticmethod
    def calculate_deviation(
        player_stat: float,
        baseline_stat: float,
        threshold: float = 10
    ) -> Dict:
        """
        Calculate deviation from baseline and classify severity.

        Args:
            player_stat: Player's actual statistic
            baseline_stat: Baseline/optimal statistic
            threshold: Threshold for "exploitable" deviation (default 10%)

        Returns:
            Dict with deviation info
        """
        deviation = player_stat - baseline_stat
        abs_deviation = abs(deviation)

        if abs_deviation < 5:
            severity = 'negligible'
        elif abs_deviation < 10:
            severity = 'minor'
        elif abs_deviation < 15:
            severity = 'moderate'
        elif abs_deviation < 25:
            severity = 'severe'
        else:
            severity = 'extreme'

        return {
            'player': round(player_stat, 2),
            'baseline': round(baseline_stat, 2),
            'deviation': round(deviation, 2),
            'abs_deviation': round(abs_deviation, 2),
            'severity': severity,
            'exploitable': abs_deviation > threshold,
            'direction': 'over' if deviation > 0 else 'under'
        }
