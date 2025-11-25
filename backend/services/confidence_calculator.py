"""
Confidence Interval Calculator for Poker Statistics

Uses Wilson score interval for percentage-based statistics.
This provides more accurate confidence intervals for small samples
compared to normal approximation.
"""

import math
from typing import Optional, Tuple, Dict, Any


def wilson_score_interval(
    successes: int,
    trials: int,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate Wilson score confidence interval for a proportion.

    Args:
        successes: Number of successful events (e.g., VPIP hands)
        trials: Total number of trials (e.g., total hands)
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound) as percentages (0-100)
    """
    if trials == 0:
        return (0.0, 100.0)

    # Z-score for confidence level
    z_scores = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    z = z_scores.get(confidence, 1.96)

    p = successes / trials

    denominator = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator

    lower = max(0, (center - spread)) * 100
    upper = min(1, (center + spread)) * 100

    return (round(lower, 1), round(upper, 1))


def calculate_ci_width(lower: float, upper: float) -> float:
    """Calculate the width of a confidence interval."""
    return upper - lower


def get_reliability_level(ci_width: float) -> str:
    """
    Determine reliability level based on confidence interval width.

    Returns:
        One of: 'excellent', 'good', 'moderate', 'low', 'insufficient'
    """
    if ci_width <= 5:
        return "excellent"
    elif ci_width <= 10:
        return "good"
    elif ci_width <= 20:
        return "moderate"
    elif ci_width <= 40:
        return "low"
    else:
        return "insufficient"


def get_reliability_color(reliability: str) -> str:
    """Get color code for reliability level."""
    colors = {
        "excellent": "green",
        "good": "green",
        "moderate": "yellow",
        "low": "orange",
        "insufficient": "gray"
    }
    return colors.get(reliability, "gray")


def calculate_stat_confidence(
    successes: int,
    trials: int,
    stat_name: str = ""
) -> Dict[str, Any]:
    """
    Calculate comprehensive confidence metrics for a statistic.

    Args:
        successes: Number of successful events
        trials: Total number of opportunities
        stat_name: Name of the statistic (for context)

    Returns:
        Dictionary with:
        - value: The percentage value
        - ci_lower: Lower bound of 95% CI
        - ci_upper: Upper bound of 95% CI
        - ci_width: Width of confidence interval
        - reliability: Reliability level string
        - reliability_color: Color for UI display
        - sample_size: Number of trials
        - is_reliable: Boolean if stat is trustworthy
    """
    if trials == 0:
        return {
            "value": None,
            "ci_lower": 0,
            "ci_upper": 100,
            "ci_width": 100,
            "reliability": "insufficient",
            "reliability_color": "gray",
            "sample_size": 0,
            "is_reliable": False,
            "display": "N/A"
        }

    value = (successes / trials) * 100
    ci_lower, ci_upper = wilson_score_interval(successes, trials)
    ci_width = calculate_ci_width(ci_lower, ci_upper)
    reliability = get_reliability_level(ci_width)

    return {
        "value": round(value, 1),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "ci_width": round(ci_width, 1),
        "reliability": reliability,
        "reliability_color": get_reliability_color(reliability),
        "sample_size": trials,
        "is_reliable": reliability in ["excellent", "good", "moderate"],
        "display": f"{value:.1f}% ({ci_lower:.0f}-{ci_upper:.0f}%)"
    }


# Minimum sample sizes for reliable stats (based on achieving <15% CI width)
# These are calculated to achieve "moderate" reliability at 50% frequency
MINIMUM_SAMPLES = {
    # Preflop stats (high frequency)
    "vpip": 50,
    "pfr": 50,
    "limp": 100,

    # 3-bet stats (medium frequency)
    "three_bet": 150,
    "fold_to_three_bet": 80,
    "four_bet": 200,

    # Steal stats
    "steal_attempt": 100,
    "fold_to_steal": 80,

    # Postflop stats (situation dependent)
    "cbet_flop": 100,
    "cbet_turn": 150,
    "cbet_river": 200,
    "fold_to_cbet_flop": 100,
    "fold_to_cbet_turn": 150,
    "fold_to_cbet_river": 200,

    # Check-raise (rare)
    "check_raise_flop": 300,
    "check_raise_turn": 400,
    "check_raise_river": 500,

    # Showdown stats
    "wtsd": 200,
    "wsd": 150,

    # Default
    "default": 100
}


def get_minimum_sample(stat_name: str) -> int:
    """Get minimum sample size for a stat to be considered reliable."""
    return MINIMUM_SAMPLES.get(stat_name, MINIMUM_SAMPLES["default"])


def calculate_all_stat_confidences(
    stats_data: Dict[str, Tuple[int, int]]
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate confidence metrics for multiple statistics.

    Args:
        stats_data: Dictionary mapping stat_name to (successes, trials) tuples

    Returns:
        Dictionary mapping stat_name to confidence metrics
    """
    results = {}
    for stat_name, (successes, trials) in stats_data.items():
        results[stat_name] = calculate_stat_confidence(successes, trials, stat_name)
    return results


def aggregate_reliability(confidences: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate reliability across multiple stats to give overall assessment.

    Returns:
        Dictionary with:
        - reliable_stats: List of stat names that are reliable
        - preliminary_stats: List of stats with moderate confidence
        - insufficient_stats: List of stats with low/no confidence
        - overall_reliability: Overall assessment string
    """
    reliable = []
    preliminary = []
    insufficient = []

    for stat_name, conf in confidences.items():
        if conf["reliability"] in ["excellent", "good"]:
            reliable.append(stat_name)
        elif conf["reliability"] == "moderate":
            preliminary.append(stat_name)
        else:
            insufficient.append(stat_name)

    total = len(confidences)
    reliable_pct = len(reliable) / total * 100 if total > 0 else 0

    if reliable_pct >= 70:
        overall = "high"
    elif reliable_pct >= 40:
        overall = "moderate"
    else:
        overall = "low"

    return {
        "reliable_stats": reliable,
        "preliminary_stats": preliminary,
        "insufficient_stats": insufficient,
        "reliable_count": len(reliable),
        "total_count": total,
        "overall_reliability": overall
    }
