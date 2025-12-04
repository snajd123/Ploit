"""
Priority Scoring for GTO Leaks

Shared utilities for calculating priority scores across player and session analysis.
This ensures consistent leak prioritization regardless of the analysis context.
"""

import math
from typing import Dict, Any, List

# Sample thresholds by scenario type (per poker professor recommendations)
# Updated for statistical significance - original values were too aggressive
# With 20 samples, cannot reliably distinguish 20% RFI from 30% RFI
# Aligned with PlayerProfile.tsx SAMPLE_THRESHOLDS
SAMPLE_THRESHOLDS = {
    'opening': {'min_display': 50, 'confident': 100, 'very_confident': 200},
    'defense': {'min_display': 50, 'confident': 100, 'very_confident': 200},
    'facing_3bet': {'min_display': 40, 'confident': 80, 'very_confident': 150},
    'facing_4bet': {'min_display': 50, 'confident': 100, 'very_confident': 200},
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
    # Facing 4-bet - rare but high EV spots
    'facing_4bet_BTN_fold': 1.3,
    'facing_4bet_BTN_call': 1.2,
    'facing_4bet_BTN_5bet': 1.1,
    'facing_4bet_CO_fold': 1.2,
    'facing_4bet_CO_call': 1.1,
    'facing_4bet_CO_5bet': 1.0,
    'facing_4bet_SB_fold': 1.1,
    'facing_4bet_SB_call': 1.0,
    'facing_4bet_SB_5bet': 1.0,
    'facing_4bet_MP_fold': 1.0,
    'facing_4bet_MP_call': 0.9,
    'facing_4bet_MP_5bet': 0.9,
    'facing_4bet_UTG_fold': 0.9,
    'facing_4bet_UTG_call': 0.8,
    'facing_4bet_UTG_5bet': 0.8,
    'facing_4bet_HJ_fold': 1.0,
    'facing_4bet_HJ_call': 0.9,
    'facing_4bet_HJ_5bet': 0.9,
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
    """Determine leak severity based on deviation from GTO.

    Thresholds aligned with PlayerProfile.tsx:
    - MODERATE_THRESHOLD = 8 (was 5)
    - MAJOR_THRESHOLD = 15
    """
    abs_dev = abs(deviation)
    if abs_dev < 8:
        return "none"
    elif abs_dev < 15:
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
        deviation = r.get('frequency_diff', 0)
        sample = r.get('total_hands', 0)  # Use total_hands field
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
            'leak_direction': 'too_loose' if deviation > 8 else 'too_tight' if deviation < -8 else None,
            'confidence_level': get_confidence_level(sample, 'opening'),
            'ev_weight': get_leak_weight(f"opening_{pos}"),
        }
        scenario['priority_score'] = calculate_priority_score(scenario)
        scenarios.append(scenario)

    # 2. Defense vs opens
    for r in gto_data.get('defense_vs_open', []):
        pos = r.get('position', '')
        total_sample = r.get('sample_size', 0)  # Field name from mygame_endpoints

        # Fold action - use action-specific count if available
        fold_count = r.get('fold_count', total_sample)
        fold_dev = r.get('fold_diff', 0)
        fold_severity = get_leak_severity(fold_dev)
        fold_scenario = {
            'scenario_id': f"defense_{pos}_fold",
            'category': 'defense',
            'position': pos,
            'action': 'fold',
            'display_name': f"Fold in {pos}",
            'overall_value': r.get('player_fold', 0),
            'overall_sample': fold_count,  # Action-specific count
            'total_opportunities': total_sample,  # Keep total for context
            'overall_deviation': fold_dev,
            'gto_value': r.get('gto_fold', 0),
            'is_leak': fold_severity != 'none',
            'leak_severity': fold_severity,
            'leak_direction': 'too_high' if fold_dev > 8 else 'too_low' if fold_dev < -8 else None,
            'confidence_level': get_confidence_level(total_sample, 'defense'),
            'ev_weight': get_leak_weight(f"defense_{pos}_fold"),
        }
        fold_scenario['priority_score'] = calculate_priority_score(fold_scenario)
        scenarios.append(fold_scenario)

        # Call action - use action-specific count if available
        call_count = r.get('call_count', total_sample)
        call_dev = r.get('call_diff', 0)
        call_severity = get_leak_severity(call_dev)
        call_scenario = {
            'scenario_id': f"defense_{pos}_call",
            'category': 'defense',
            'position': pos,
            'action': 'call',
            'display_name': f"Call in {pos}",
            'overall_value': r.get('player_call', 0),
            'overall_sample': call_count,  # Action-specific count
            'total_opportunities': total_sample,  # Keep total for context
            'overall_deviation': call_dev,
            'gto_value': r.get('gto_call', 0),
            'is_leak': call_severity != 'none',
            'leak_severity': call_severity,
            'leak_direction': 'too_high' if call_dev > 8 else 'too_low' if call_dev < -8 else None,
            'confidence_level': get_confidence_level(total_sample, 'defense'),
            'ev_weight': get_leak_weight(f"defense_{pos}_call"),
        }
        call_scenario['priority_score'] = calculate_priority_score(call_scenario)
        scenarios.append(call_scenario)

        # 3-bet action - use action-specific count if available
        threebet_count = r.get('3bet_count', total_sample)
        threebet_dev = r.get('3bet_diff', 0)
        threebet_severity = get_leak_severity(threebet_dev)
        threebet_scenario = {
            'scenario_id': f"defense_{pos}_3bet",
            'category': 'defense',
            'position': pos,
            'action': '3bet',
            'display_name': f"3-Bet in {pos}",
            'overall_value': r.get('player_3bet', 0),
            'overall_sample': threebet_count,  # Action-specific count
            'total_opportunities': total_sample,  # Keep total for context
            'overall_deviation': threebet_dev,
            'gto_value': r.get('gto_3bet', 0),
            'is_leak': threebet_severity != 'none',
            'leak_severity': threebet_severity,
            'leak_direction': 'too_high' if threebet_dev > 8 else 'too_low' if threebet_dev < -8 else None,
            'confidence_level': get_confidence_level(total_sample, 'defense'),
            'ev_weight': get_leak_weight(f"defense_{pos}_3bet"),
        }
        threebet_scenario['priority_score'] = calculate_priority_score(threebet_scenario)
        scenarios.append(threebet_scenario)

    # 3. Facing 3-bet
    for r in gto_data.get('facing_3bet', []):
        pos = r.get('position', '')
        total_sample = r.get('sample_size', 0)  # Field name from mygame_endpoints

        # Fold action - use action-specific count if available
        fold_count = r.get('fold_count', total_sample)
        fold_dev = r.get('fold_diff', 0)
        fold_severity = get_leak_severity(fold_dev)
        fold_scenario = {
            'scenario_id': f"facing_3bet_{pos}_fold",
            'category': 'facing_3bet',
            'position': pos,
            'action': 'fold',
            'display_name': f"Fold to 3-Bet in {pos}",
            'overall_value': r.get('player_fold', 0),
            'overall_sample': fold_count,  # Action-specific count
            'total_opportunities': total_sample,
            'overall_deviation': fold_dev,
            'gto_value': r.get('gto_fold', 0),
            'is_leak': fold_severity != 'none',
            'leak_severity': fold_severity,
            'leak_direction': 'too_high' if fold_dev > 8 else 'too_low' if fold_dev < -8 else None,
            'confidence_level': get_confidence_level(total_sample, 'facing_3bet'),
            'ev_weight': get_leak_weight(f"facing_3bet_{pos}_fold"),
        }
        fold_scenario['priority_score'] = calculate_priority_score(fold_scenario)
        scenarios.append(fold_scenario)

        # Call action - use action-specific count if available
        call_count = r.get('call_count', total_sample)
        call_dev = r.get('call_diff', 0)
        call_severity = get_leak_severity(call_dev)
        call_scenario = {
            'scenario_id': f"facing_3bet_{pos}_call",
            'category': 'facing_3bet',
            'position': pos,
            'action': 'call',
            'display_name': f"Call 3-Bet in {pos}",
            'overall_value': r.get('player_call', 0),
            'overall_sample': call_count,  # Action-specific count
            'total_opportunities': total_sample,
            'overall_deviation': call_dev,
            'gto_value': r.get('gto_call', 0),
            'is_leak': call_severity != 'none',
            'leak_severity': call_severity,
            'leak_direction': 'too_high' if call_dev > 8 else 'too_low' if call_dev < -8 else None,
            'confidence_level': get_confidence_level(total_sample, 'facing_3bet'),
            'ev_weight': get_leak_weight(f"facing_3bet_{pos}_call"),
        }
        call_scenario['priority_score'] = calculate_priority_score(call_scenario)
        scenarios.append(call_scenario)

        # 4-bet action - use action-specific count if available
        fourbet_count = r.get('4bet_count', total_sample)
        fourbet_dev = r.get('4bet_diff', 0)
        fourbet_severity = get_leak_severity(fourbet_dev)
        fourbet_scenario = {
            'scenario_id': f"facing_3bet_{pos}_4bet",
            'category': 'facing_3bet',
            'position': pos,
            'action': '4bet',
            'display_name': f"4-Bet in {pos}",
            'overall_value': r.get('player_4bet', 0),
            'overall_sample': fourbet_count,  # Action-specific count
            'total_opportunities': total_sample,
            'overall_deviation': fourbet_dev,
            'gto_value': r.get('gto_4bet', 0),
            'is_leak': fourbet_severity != 'none',
            'leak_severity': fourbet_severity,
            'leak_direction': 'too_high' if fourbet_dev > 8 else 'too_low' if fourbet_dev < -8 else None,
            'confidence_level': get_confidence_level(total_sample, 'facing_3bet'),
            'ev_weight': get_leak_weight(f"facing_3bet_{pos}_4bet"),
        }
        fourbet_scenario['priority_score'] = calculate_priority_score(fourbet_scenario)
        scenarios.append(fourbet_scenario)

    # 4. Facing 4-bet
    for r in gto_data.get('facing_4bet_reference', []):
        pos = r.get('position', '')
        vs_pos = r.get('vs_position', '')
        sample = r.get('sample_size', 0)

        # Fold action
        fold_dev = r.get('fold_diff')
        if fold_dev is not None:
            fold_severity = get_leak_severity(fold_dev)
            fold_scenario = {
                'scenario_id': f"facing_4bet_{pos}_fold",
                'category': 'facing_4bet',
                'position': pos,
                'vs_position': vs_pos,
                'action': 'fold',
                'display_name': f"{pos} vs 4-Bet - Fold%",
                'overall_value': r.get('player_fold', 0),
                'overall_sample': sample,
                'overall_deviation': fold_dev,
                'gto_value': r.get('gto_fold', 0),
                'is_leak': fold_severity != 'none',
                'leak_severity': fold_severity,
                'leak_direction': 'too_high' if fold_dev > 8 else 'too_low' if fold_dev < -8 else None,
                'confidence_level': get_confidence_level(sample, 'facing_4bet'),
                'ev_weight': get_leak_weight(f"facing_4bet_{pos}_fold"),
            }
            fold_scenario['priority_score'] = calculate_priority_score(fold_scenario)
            scenarios.append(fold_scenario)

        # Call action
        call_dev = r.get('call_diff')
        if call_dev is not None:
            call_severity = get_leak_severity(call_dev)
            call_scenario = {
                'scenario_id': f"facing_4bet_{pos}_call",
                'category': 'facing_4bet',
                'position': pos,
                'vs_position': vs_pos,
                'action': 'call',
                'display_name': f"{pos} vs 4-Bet - Call%",
                'overall_value': r.get('player_call', 0),
                'overall_sample': sample,
                'overall_deviation': call_dev,
                'gto_value': r.get('gto_call', 0),
                'is_leak': call_severity != 'none',
                'leak_severity': call_severity,
                'leak_direction': 'too_high' if call_dev > 8 else 'too_low' if call_dev < -8 else None,
                'confidence_level': get_confidence_level(sample, 'facing_4bet'),
                'ev_weight': get_leak_weight(f"facing_4bet_{pos}_call"),
            }
            call_scenario['priority_score'] = calculate_priority_score(call_scenario)
            scenarios.append(call_scenario)

        # 5-bet action
        fivebet_dev = r.get('5bet_diff')
        if fivebet_dev is not None:
            fivebet_severity = get_leak_severity(fivebet_dev)
            fivebet_scenario = {
                'scenario_id': f"facing_4bet_{pos}_5bet",
                'category': 'facing_4bet',
                'position': pos,
                'vs_position': vs_pos,
                'action': '5bet',
                'display_name': f"{pos} vs 4-Bet - 5-Bet%",
                'overall_value': r.get('player_5bet', 0),
                'overall_sample': sample,
                'overall_deviation': fivebet_dev,
                'gto_value': r.get('gto_5bet', 0),
                'is_leak': fivebet_severity != 'none',
                'leak_severity': fivebet_severity,
                'leak_direction': 'too_high' if fivebet_dev > 8 else 'too_low' if fivebet_dev < -8 else None,
                'confidence_level': get_confidence_level(sample, 'facing_4bet'),
                'ev_weight': get_leak_weight(f"facing_4bet_{pos}_5bet"),
            }
            fivebet_scenario['priority_score'] = calculate_priority_score(fivebet_scenario)
            scenarios.append(fivebet_scenario)

    # Filter to leaks only with sufficient sample size, and sort by priority
    # Exclude "insufficient" confidence scenarios - they have no statistical significance
    leaks_only = [
        s for s in scenarios
        if s.get('is_leak')
        and s.get('priority_score', 0) > 0
        and s.get('confidence_level') != 'insufficient'
    ]
    priority_leaks = sorted(leaks_only, key=lambda x: x.get('priority_score', 0), reverse=True)

    return priority_leaks
