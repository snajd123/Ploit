"""
GTO Baselines for 6-Max No-Limit Hold'em

These values are derived from solver outputs (GTOWizard, MonkerSolver, PioSOLVER)
for 100bb deep 6-max cash games. They represent theoretically optimal play
against an optimal opponent.

Note: Real-world population tendencies often deviate significantly from GTO,
so these baselines are used to identify exploitable deviations, not to grade
players as "good" or "bad".

Sources:
- GTOWizard 6-max 100bb preflop solutions
- Run It Once Poker training material
- 2+2 forums solver discussions
- MonkerSolver postflop solutions
"""

from typing import Dict, Any

# Position-specific preflop statistics for 6-max 100bb
PREFLOP_BASELINES_6MAX = {
    "UTG": {
        "open_raise_pct": 17.0,     # ~17% open raise
        "vpip": 17.0,               # VPIP = RFI from UTG
        "pfr": 17.0,                # PFR = RFI from UTG
        "fold_to_3bet": 43.0,       # Tighter range -> folds less to 3bet
        "4bet_pct": 3.5,            # 4-bet with QQ+, AK mainly
        "limp_pct": 0.0,            # Never limp in GTO
        "cold_call_pct": 0.0,       # First to act
    },
    "HJ": {
        "open_raise_pct": 21.0,
        "vpip": 21.0,
        "pfr": 21.0,
        "fold_to_3bet": 45.0,
        "4bet_pct": 3.0,
        "limp_pct": 0.0,
        "cold_call_pct": 2.0,       # Some calls vs UTG
    },
    "CO": {
        "open_raise_pct": 27.0,
        "vpip": 28.0,
        "pfr": 26.0,
        "fold_to_3bet": 48.0,       # Wider range -> folds more
        "4bet_pct": 2.5,
        "limp_pct": 0.0,
        "cold_call_pct": 4.0,
    },
    "BTN": {
        "open_raise_pct": 43.0,     # Very wide on button
        "vpip": 48.0,
        "pfr": 42.0,
        "fold_to_3bet": 52.0,       # Widest range -> highest fold to 3bet
        "4bet_pct": 2.0,
        "limp_pct": 0.0,
        "cold_call_pct": 8.0,
    },
    "SB": {
        "open_raise_pct": 40.0,     # Wide vs BB only
        "vpip": 42.0,
        "pfr": 38.0,
        "3bet_vs_btn": 12.0,        # 3-bet button wide
        "3bet_vs_co": 8.0,
        "3bet_vs_utg": 5.0,
        "fold_to_3bet": 50.0,
        "limp_pct": 5.0,            # Some limps allowed vs BB
        "cold_call_pct": 6.0,
    },
    "BB": {
        "vpip": 38.0,               # Defends wide from BB
        "pfr": 11.0,                # Only 3-bets, no open raising
        "3bet_vs_btn": 11.0,
        "3bet_vs_co": 8.0,
        "3bet_vs_hj": 6.0,
        "3bet_vs_utg": 4.5,
        "fold_to_open": 52.0,       # Defends ~48%
        "fold_to_steal": 45.0,      # Defends more vs steals
        "cold_call_vs_btn": 28.0,   # Lots of calling vs button
        "cold_call_vs_utg": 12.0,
    },
}

# Global preflop averages (all positions combined, weighted by frequency)
PREFLOP_GLOBAL = {
    "vpip": 24.0,           # Typical winning player
    "pfr": 20.0,
    "vpip_pfr_gap": 4.0,    # Healthy gap
    "three_bet": 7.0,       # Overall 3-bet %
    "fold_to_three_bet": 48.0,
    "four_bet": 2.5,
    "cold_call": 5.0,
    "limp": 1.0,            # Very rare
    "squeeze": 3.0,
}

# NOTE: Postflop baselines removed - currently preflop only
# Postflop GTO data will be added in a future update


# Deviation thresholds - how far from GTO before it's exploitable
DEVIATION_THRESHOLDS = {
    # Preflop deviations
    "vpip": {
        "minor": 5,             # ±5% is normal variance
        "moderate": 10,         # ±10% is noticeable
        "major": 15,            # ±15% is significant leak
        "critical": 25,         # ±25% is massive leak
    },
    "pfr": {
        "minor": 4,
        "moderate": 8,
        "major": 12,
        "critical": 20,
    },
    "three_bet": {
        "minor": 2,
        "moderate": 4,
        "major": 6,
        "critical": 10,
    },
    "fold_to_three_bet": {
        "minor": 8,
        "moderate": 15,
        "major": 22,
        "critical": 30,
    },
    "four_bet": {
        "minor": 1,
        "moderate": 2,
        "major": 4,
        "critical": 6,
    },
    "cold_call": {
        "minor": 3,
        "moderate": 6,
        "major": 10,
        "critical": 15,
    },
    "steal_attempt": {
        "minor": 5,
        "moderate": 10,
        "major": 15,
        "critical": 25,
    },
    "fold_to_steal": {
        "minor": 8,
        "moderate": 15,
        "major": 22,
        "critical": 30,
    },
}


def get_baseline(stat_name: str, position: str = None) -> float:
    """
    Get the GTO baseline for a preflop statistic.

    Args:
        stat_name: Name of the statistic
        position: Optional position for position-specific stats

    Returns:
        The GTO baseline value as a percentage
    """
    # Check position-specific first
    if position and position.upper() in PREFLOP_BASELINES_6MAX:
        pos_stats = PREFLOP_BASELINES_6MAX[position.upper()]
        if stat_name in pos_stats:
            return pos_stats[stat_name]

    # Check global preflop
    if stat_name in PREFLOP_GLOBAL:
        return PREFLOP_GLOBAL[stat_name]

    return None


def get_deviation_severity(stat_name: str, deviation: float) -> str:
    """
    Get the severity of a deviation from GTO.

    Args:
        stat_name: Name of the statistic
        deviation: Absolute deviation from baseline

    Returns:
        Severity level: 'none', 'minor', 'moderate', 'major', 'critical'
    """
    thresholds = DEVIATION_THRESHOLDS.get(stat_name)
    if not thresholds:
        # Default thresholds
        thresholds = {"minor": 5, "moderate": 10, "major": 20, "critical": 30}

    if deviation < thresholds["minor"]:
        return "none"
    elif deviation < thresholds["moderate"]:
        return "minor"
    elif deviation < thresholds["major"]:
        return "moderate"
    elif deviation < thresholds["critical"]:
        return "major"
    else:
        return "critical"


def analyze_deviation(
    stat_name: str,
    player_value: float,
    position: str = None
) -> Dict[str, Any]:
    """
    Analyze how a player's stat deviates from GTO.

    Returns:
        Dictionary with deviation analysis
    """
    baseline = get_baseline(stat_name, position)
    if baseline is None or player_value is None:
        return {"has_baseline": False}

    deviation = player_value - baseline
    abs_deviation = abs(deviation)
    severity = get_deviation_severity(stat_name, abs_deviation)

    direction = "high" if deviation > 0 else "low" if deviation < 0 else "neutral"

    return {
        "has_baseline": True,
        "baseline": baseline,
        "player_value": player_value,
        "deviation": round(deviation, 1),
        "abs_deviation": round(abs_deviation, 1),
        "direction": direction,
        "severity": severity,
        "is_exploitable": severity in ["moderate", "major", "critical"],
        "display": f"{player_value:.1f}% (GTO: {baseline:.0f}%, {'+' if deviation >= 0 else ''}{deviation:.0f}%)"
    }


# Exploit recommendations based on preflop deviations
EXPLOIT_RECOMMENDATIONS = {
    "vpip_high": {
        "tendency": "Plays too many hands preflop",
        "exploit": "Value bet thinner, 3-bet for value more often",
        "ev_factor": 0.03,  # EV per % deviation per 100 hands
    },
    "vpip_low": {
        "tendency": "Plays too few hands preflop",
        "exploit": "Steal more often, fold to their raises",
        "ev_factor": 0.02,
    },
    "pfr_high": {
        "tendency": "Raises too aggressively preflop",
        "exploit": "3-bet wider for value, call down lighter",
        "ev_factor": 0.025,
    },
    "pfr_low": {
        "tendency": "Raises too passively preflop",
        "exploit": "Steal blinds more, respect their raises",
        "ev_factor": 0.02,
    },
    "fold_to_three_bet_high": {
        "tendency": "Folds too much to 3-bets",
        "exploit": "3-bet wider for value, include more bluffs",
        "ev_factor": 0.04,
    },
    "fold_to_three_bet_low": {
        "tendency": "Defends too much vs 3-bets",
        "exploit": "3-bet tighter for value, reduce bluff 3-bets",
        "ev_factor": 0.03,
    },
    "three_bet_high": {
        "tendency": "3-bets too aggressively",
        "exploit": "Call wider in position, 4-bet bluff more",
        "ev_factor": 0.03,
    },
    "three_bet_low": {
        "tendency": "3-bets too passively",
        "exploit": "Open wider vs them, iso-raise more",
        "ev_factor": 0.025,
    },
    "cold_call_high": {
        "tendency": "Cold calls too much (capped range)",
        "exploit": "Squeeze more, value bet thinner postflop",
        "ev_factor": 0.03,
    },
    "cold_call_low": {
        "tendency": "Rarely cold calls (polarized 3-bet or fold)",
        "exploit": "Open tighter when they're behind, respect 3-bets",
        "ev_factor": 0.02,
    },
    "steal_attempt_high": {
        "tendency": "Steals blinds too aggressively",
        "exploit": "Defend wider from blinds, 3-bet light",
        "ev_factor": 0.025,
    },
    "steal_attempt_low": {
        "tendency": "Steals blinds too infrequently",
        "exploit": "Fold blinds more, wait for premium holdings",
        "ev_factor": 0.02,
    },
    "fold_to_steal_high": {
        "tendency": "Folds to steals too often",
        "exploit": "Steal wider from late position",
        "ev_factor": 0.035,
    },
    "fold_to_steal_low": {
        "tendency": "Defends vs steals too much",
        "exploit": "Steal tighter, value bet postflop",
        "ev_factor": 0.025,
    },
}


def get_exploit_recommendation(stat_name: str, direction: str) -> Dict[str, Any]:
    """Get exploit recommendation for a specific deviation."""
    key = f"{stat_name}_{direction}"
    return EXPLOIT_RECOMMENDATIONS.get(key, {})
