"""
Priority Scoring for GTO Leaks

Shared utilities for calculating priority scores across player and session analysis.
This ensures consistent leak prioritization regardless of the analysis context.
"""

import math
from typing import Dict, Any, List

# Sample thresholds by scenario type (per poker professor recommendations)
SAMPLE_THRESHOLDS = {
    'opening': {'min_display': 30, 'confident': 75, 'very_confident': 150},
    'defense': {'min_display': 25, 'confident': 60, 'very_confident': 120},
    'facing_3bet': {'min_display': 20, 'confident': 50, 'very_confident': 100},
}

# Leak weights by position and scenario (based on EV impact)
# Higher weight = more important to fix
LEAK_WEIGHTS = {
    # Opening (RFI) - BTN most frequent, highest impact
    'opening_BTN': 1.5,
    'opening_CO': 1.3,
    'opening_SB': 1.4,
    'opening_MP': 1.1,
    'opening_UTG': 1.0,
    'opening_HJ': 1.0,
    # Defense - BB vs BTN highest frequency
    'defense_BB_fold': 1.6,
    'defense_BB_call': 1.4,
    'defense_BB_3bet': 1.3,
    'defense_SB_fold': 1.2,
    'defense_SB_call': 1.1,
    'defense_SB_3bet': 1.2,
    'defense_BTN_fold': 1.0,
    'defense_BTN_call': 0.9,
    'defense_BTN_3bet': 1.0,
    'defense_CO_fold': 0.9,
    'defense_CO_call': 0.8,
    'defense_CO_3bet': 0.9,
    'defense_MP_fold': 0.8,
    'defense_MP_call': 0.7,
    'defense_MP_3bet': 0.8,
    # Facing 3-bet - fold to 3bet is huge leak
    'facing_3bet_BTN_fold': 1.4,
    'facing_3bet_BTN_call': 1.2,
    'facing_3bet_BTN_4bet': 1.1,
    'facing_3bet_CO_fold': 1.3,
    'facing_3bet_CO_call': 1.1,
    'facing_3bet_CO_4bet': 1.0,
    'facing_3bet_SB_fold': 1.2,
    'facing_3bet_SB_call': 1.0,
    'facing_3bet_SB_4bet': 1.0,
    'facing_3bet_MP_fold': 1.0,
    'facing_3bet_MP_call': 0.9,
    'facing_3bet_MP_4bet': 0.9,
    'facing_3bet_UTG_fold': 0.9,
    'facing_3bet_UTG_call': 0.8,
    'facing_3bet_UTG_4bet': 0.8,
    'facing_3bet_HJ_fold': 1.0,
    'facing_3bet_HJ_call': 0.9,
    'facing_3bet_HJ_4bet': 0.9,
}

# Severity multipliers for improvement scoring
SEVERITY_MULTIPLIERS = {
    'none': 0.5,
    'minor': 0.8,
    'moderate': 1.0,
    'major': 1.3,
}


def get_leak_weight(scenario_id: str) -> float:
    """Get the EV-based weight for a leak scenario."""
    return LEAK_WEIGHTS.get(scenario_id, 1.0)


def get_leak_severity(deviation: float) -> str:
    """Determine leak severity based on deviation from GTO"""
    abs_dev = abs(deviation)
    if abs_dev < 5:
        return "none"
    elif abs_dev < 10:
        return "minor"
    elif abs_dev < 20:
        return "moderate"
    else:
        return "major"


def get_confidence_level(sample: int, scenario_type: str) -> str:
    """Determine confidence level based on sample size and scenario type"""
    thresholds = SAMPLE_THRESHOLDS.get(scenario_type, SAMPLE_THRESHOLDS['opening'])

    if sample < thresholds['min_display']:
        return "insufficient"
    elif sample < thresholds['confident']:
        return "low"
    elif sample < thresholds['very_confident']:
        return "moderate"
    else:
        return "high"


def calculate_priority_score(scenario: Dict[str, Any]) -> float:
    """
    Calculate priority score for sorting leaks by importance.
    Higher score = higher priority to fix.

    Factors:
    - Leak severity (major > moderate > minor)
    - EV weight (position importance)
    - Improvement potential (distance to GTO)
    - Sample confidence
    """
    if not scenario.get('is_leak'):
        return 0

    # Base priority from severity
    severity_scores = {'none': 0, 'minor': 1, 'moderate': 2, 'major': 3}
    severity_score = severity_scores.get(scenario.get('leak_severity', 'none'), 0)

    # EV weight
    ev_weight = get_leak_weight(scenario.get('scenario_id', ''))

    # Distance to GTO (improvement potential)
    deviation = abs(scenario.get('overall_deviation', 0))

    # Confidence factor
    confidence_scores = {'insufficient': 0.3, 'low': 0.6, 'moderate': 0.85, 'high': 1.0}
    conf_level = scenario.get('confidence_level', 'low')
    confidence = confidence_scores.get(conf_level, 0.5)

    # Combined priority score
    priority = (severity_score * 10 + deviation * 0.5) * ev_weight * confidence

    return round(priority, 2)


def build_priority_leaks_from_gto_analysis(gto_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build priority_leaks list from player GTO analysis data.

    This converts the existing GTO analysis response format into the scenario-based
    priority scoring format used by session analysis.

    Args:
        gto_data: The response from get_player_gto_analysis endpoint

    Returns:
        List of scenarios sorted by priority_score descending
    """
    scenarios = []

    # 1. Opening ranges (RFI)
    for r in gto_data.get('opening_ranges', []):
        pos = r.get('position', '')
        deviation = r.get('open_diff', 0)
        sample = r.get('opportunities', 0)
        severity = get_leak_severity(deviation)
        is_leak = severity != 'none'

        scenario = {
            'scenario_id': f"opening_{pos}",
            'category': 'opening',
            'position': pos,
            'action': 'open',
            'display_name': f"{pos} Open (RFI)",
            'overall_value': r.get('player_frequency', 0),
            'overall_sample': sample,
            'overall_deviation': deviation,
            'gto_value': r.get('gto_frequency', 0),
            'is_leak': is_leak,
            'leak_severity': severity,
            'leak_direction': 'too_loose' if deviation > 5 else 'too_tight' if deviation < -5 else None,
            'confidence_level': get_confidence_level(sample, 'opening'),
            'ev_weight': get_leak_weight(f"opening_{pos}"),
        }
        scenario['priority_score'] = calculate_priority_score(scenario)
        scenarios.append(scenario)

    # 2. Defense vs opens
    for r in gto_data.get('defense_vs_open', []):
        pos = r.get('position', '')
        sample = r.get('total_opportunities', 0)

        # Fold action
        fold_dev = r.get('fold_diff', 0)
        fold_severity = get_leak_severity(fold_dev)
        fold_scenario = {
            'scenario_id': f"defense_{pos}_fold",
            'category': 'defense',
            'position': pos,
            'action': 'fold',
            'display_name': f"{pos} Defense - Fold%",
            'overall_value': r.get('player_fold', 0),
            'overall_sample': sample,
            'overall_deviation': fold_dev,
            'gto_value': r.get('gto_fold', 0),
            'is_leak': fold_severity != 'none',
            'leak_severity': fold_severity,
            'leak_direction': 'too_high' if fold_dev > 5 else 'too_low' if fold_dev < -5 else None,
            'confidence_level': get_confidence_level(sample, 'defense'),
            'ev_weight': get_leak_weight(f"defense_{pos}_fold"),
        }
        fold_scenario['priority_score'] = calculate_priority_score(fold_scenario)
        scenarios.append(fold_scenario)

        # Call action
        call_dev = r.get('call_diff', 0)
        call_severity = get_leak_severity(call_dev)
        call_scenario = {
            'scenario_id': f"defense_{pos}_call",
            'category': 'defense',
            'position': pos,
            'action': 'call',
            'display_name': f"{pos} Defense - Call%",
            'overall_value': r.get('player_call', 0),
            'overall_sample': sample,
            'overall_deviation': call_dev,
            'gto_value': r.get('gto_call', 0),
            'is_leak': call_severity != 'none',
            'leak_severity': call_severity,
            'leak_direction': 'too_high' if call_dev > 5 else 'too_low' if call_dev < -5 else None,
            'confidence_level': get_confidence_level(sample, 'defense'),
            'ev_weight': get_leak_weight(f"defense_{pos}_call"),
        }
        call_scenario['priority_score'] = calculate_priority_score(call_scenario)
        scenarios.append(call_scenario)

        # 3-bet action
        threebet_dev = r.get('raise_diff', 0)
        threebet_severity = get_leak_severity(threebet_dev)
        threebet_scenario = {
            'scenario_id': f"defense_{pos}_3bet",
            'category': 'defense',
            'position': pos,
            'action': '3bet',
            'display_name': f"{pos} Defense - 3-Bet%",
            'overall_value': r.get('player_3bet', 0),
            'overall_sample': sample,
            'overall_deviation': threebet_dev,
            'gto_value': r.get('gto_3bet', 0),
            'is_leak': threebet_severity != 'none',
            'leak_severity': threebet_severity,
            'leak_direction': 'too_high' if threebet_dev > 5 else 'too_low' if threebet_dev < -5 else None,
            'confidence_level': get_confidence_level(sample, 'defense'),
            'ev_weight': get_leak_weight(f"defense_{pos}_3bet"),
        }
        threebet_scenario['priority_score'] = calculate_priority_score(threebet_scenario)
        scenarios.append(threebet_scenario)

    # 3. Facing 3-bet
    for r in gto_data.get('facing_3bet', []):
        pos = r.get('position', '')
        sample = r.get('times_opened', 0)

        # Fold action
        fold_dev = r.get('fold_diff', 0)
        fold_severity = get_leak_severity(fold_dev)
        fold_scenario = {
            'scenario_id': f"facing_3bet_{pos}_fold",
            'category': 'facing_3bet',
            'position': pos,
            'action': 'fold',
            'display_name': f"{pos} vs 3-Bet - Fold%",
            'overall_value': r.get('player_fold', 0),
            'overall_sample': sample,
            'overall_deviation': fold_dev,
            'gto_value': r.get('gto_fold', 0),
            'is_leak': fold_severity != 'none',
            'leak_severity': fold_severity,
            'leak_direction': 'too_high' if fold_dev > 5 else 'too_low' if fold_dev < -5 else None,
            'confidence_level': get_confidence_level(sample, 'facing_3bet'),
            'ev_weight': get_leak_weight(f"facing_3bet_{pos}_fold"),
        }
        fold_scenario['priority_score'] = calculate_priority_score(fold_scenario)
        scenarios.append(fold_scenario)

        # Call action
        call_dev = r.get('call_diff', 0)
        call_severity = get_leak_severity(call_dev)
        call_scenario = {
            'scenario_id': f"facing_3bet_{pos}_call",
            'category': 'facing_3bet',
            'position': pos,
            'action': 'call',
            'display_name': f"{pos} vs 3-Bet - Call%",
            'overall_value': r.get('player_call', 0),
            'overall_sample': sample,
            'overall_deviation': call_dev,
            'gto_value': r.get('gto_call', 0),
            'is_leak': call_severity != 'none',
            'leak_severity': call_severity,
            'leak_direction': 'too_high' if call_dev > 5 else 'too_low' if call_dev < -5 else None,
            'confidence_level': get_confidence_level(sample, 'facing_3bet'),
            'ev_weight': get_leak_weight(f"facing_3bet_{pos}_call"),
        }
        call_scenario['priority_score'] = calculate_priority_score(call_scenario)
        scenarios.append(call_scenario)

        # 4-bet action
        fourbet_dev = r.get('4bet_diff', 0)
        fourbet_severity = get_leak_severity(fourbet_dev)
        fourbet_scenario = {
            'scenario_id': f"facing_3bet_{pos}_4bet",
            'category': 'facing_3bet',
            'position': pos,
            'action': '4bet',
            'display_name': f"{pos} vs 3-Bet - 4-Bet%",
            'overall_value': r.get('player_4bet', 0),
            'overall_sample': sample,
            'overall_deviation': fourbet_dev,
            'gto_value': r.get('gto_4bet', 0),
            'is_leak': fourbet_severity != 'none',
            'leak_severity': fourbet_severity,
            'leak_direction': 'too_high' if fourbet_dev > 5 else 'too_low' if fourbet_dev < -5 else None,
            'confidence_level': get_confidence_level(sample, 'facing_3bet'),
            'ev_weight': get_leak_weight(f"facing_3bet_{pos}_4bet"),
        }
        fourbet_scenario['priority_score'] = calculate_priority_score(fourbet_scenario)
        scenarios.append(fourbet_scenario)

    # Filter to leaks only and sort by priority
    leaks_only = [s for s in scenarios if s.get('is_leak') and s.get('priority_score', 0) > 0]
    priority_leaks = sorted(leaks_only, key=lambda x: x.get('priority_score', 0), reverse=True)

    return priority_leaks
