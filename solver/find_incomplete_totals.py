#!/usr/bin/env python3
"""
Find all hands where action frequencies don't sum to 100%
This helps identify missing or incorrect data
"""

import re
from collections import defaultdict

def parse_combo_range(range_str):
    """Parse combo range string into dict"""
    combos = {}
    if not range_str.strip():
        return combos

    for item in range_str.split(','):
        item = item.strip()
        if ':' not in item or not item:
            continue
        try:
            combo, freq = item.split(':')
            combos[combo.strip()] = float(freq.strip())
        except ValueError:
            continue

    return combos


def combo_to_hand(combo):
    """Convert combo like 'AhKd' to hand type like 'AKo'"""
    if len(combo) != 4:
        return None

    rank1, suit1, rank2, suit2 = combo[0], combo[1], combo[2], combo[3]
    rank_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
                  '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

    r1 = rank_order.get(rank1, 0)
    r2 = rank_order.get(rank2, 0)

    if r1 > r2:
        high, low = rank1, rank2
        high_suit, low_suit = suit1, suit2
    else:
        high, low = rank2, rank1
        high_suit, low_suit = suit2, suit1

    if high == low:
        return f"{high}{low}"
    elif high_suit == low_suit:
        return f"{high}{low}s"
    else:
        return f"{high}{low}o"


def extract_ranges_from_file(filename):
    """Extract all [DONE] ranges from file"""
    with open(filename, 'r') as f:
        content = f.read()

    pattern = r'\[DONE\]\s+(\w+)\s*\n#\s*GTOWizard:\s*(.*?)\n(.*?)\n\n'
    matches = re.finditer(pattern, content, re.DOTALL)

    ranges = {}
    for match in matches:
        scenario_name = match.group(1)
        range_data = match.group(3).strip()
        combos = parse_combo_range(range_data)

        if combos:
            ranges[scenario_name] = combos

    return ranges


def check_scenario_group(ranges, base_scenarios, group_name):
    """Check if all hands in a scenario group sum to 100%"""

    # Collect all hands that appear in any action
    all_hands = defaultdict(lambda: defaultdict(float))

    for scenario in base_scenarios:
        if scenario not in ranges:
            continue

        combos = ranges[scenario]

        # Group by hand
        for combo, freq in combos.items():
            hand = combo_to_hand(combo)
            if hand:
                if hand not in all_hands[scenario]:
                    all_hands[scenario][hand] = []
                all_hands[scenario][hand].append(freq)

    # Calculate average frequency per hand per action
    hand_totals = defaultdict(lambda: defaultdict(float))

    for scenario in base_scenarios:
        if scenario not in all_hands:
            continue

        for hand, freqs in all_hands[scenario].items():
            avg_freq = sum(freqs) / len(freqs)
            hand_totals[hand][scenario] = avg_freq

    # Find hands that don't sum to 100%
    incomplete = []

    # Get all unique hands across all actions
    all_unique_hands = set()
    for hand_dict in hand_totals.values():
        for hand in hand_dict.keys():
            all_unique_hands.add(hand)

    for hand in sorted(all_unique_hands):
        total = 0.0
        actions = {}

        for scenario in base_scenarios:
            if hand in hand_totals and scenario in hand_totals[hand]:
                freq = hand_totals[hand][scenario]
                total += freq
                actions[scenario] = freq

        # Check if total is NOT ~100% (allow 0.5% tolerance for rounding)
        if abs(total - 1.0) > 0.005:
            incomplete.append({
                'hand': hand,
                'total': total * 100,
                'actions': actions,
                'missing': (1.0 - total) * 100
            })

    return incomplete


def main():
    print("=" * 80)
    print("CHECKING ALL SCENARIOS FOR INCOMPLETE TOTALS")
    print("=" * 80)
    print()

    ranges = extract_ranges_from_file('/root/Documents/Ploit/solver/gtowizard_ranges.txt')

    # Define scenario groups
    scenario_groups = {
        'BB vs UTG': ['BB_vs_UTG_fold', 'BB_vs_UTG_call', 'BB_vs_UTG_3bet'],
        'BB vs MP': ['BB_vs_MP_fold', 'BB_vs_MP_call', 'BB_vs_MP_3bet'],
        'BB vs CO': ['BB_vs_CO_fold', 'BB_vs_CO_call', 'BB_vs_CO_3bet'],
        'BB vs BTN': ['BB_vs_BTN_fold', 'BB_vs_BTN_call', 'BB_vs_BTN_3bet'],
        'BB vs SB': ['BB_vs_SB_fold', 'BB_vs_SB_call', 'BB_vs_SB_3bet'],
        'SB vs UTG': ['SB_vs_UTG_fold', 'SB_vs_UTG_call', 'SB_vs_UTG_3bet'],
        'SB vs MP': ['SB_vs_MP_fold', 'SB_vs_MP_call', 'SB_vs_MP_3bet'],
        'SB vs CO': ['SB_vs_CO_fold', 'SB_vs_CO_call', 'SB_vs_CO_3bet'],
        'SB vs BTN': ['SB_vs_BTN_fold', 'SB_vs_BTN_call', 'SB_vs_BTN_3bet'],
        'CO vs UTG': ['CO_vs_UTG_fold', 'CO_vs_UTG_call', 'CO_vs_UTG_3bet'],
        'CO vs MP': ['CO_vs_MP_fold', 'CO_vs_MP_call', 'CO_vs_MP_3bet'],
        'BTN vs UTG': ['BTN_vs_UTG_fold', 'BTN_vs_UTG_call', 'BTN_vs_UTG_3bet'],
        'BTN vs MP': ['BTN_vs_MP_fold', 'BTN_vs_MP_call', 'BTN_vs_MP_3bet'],
        'BTN vs CO': ['BTN_vs_CO_fold', 'BTN_vs_CO_call', 'BTN_vs_CO_3bet'],
        'UTG vs CO 3bet': ['UTG_vs_CO_3bet_fold', 'UTG_vs_CO_3bet_call', 'UTG_vs_CO_3bet_4bet'],
        'UTG vs BTN 3bet': ['UTG_vs_BTN_3bet_fold', 'UTG_vs_BTN_3bet_call', 'UTG_vs_BTN_3bet_4bet'],
        'UTG vs SB 3bet': ['UTG_vs_SB_3bet_fold', 'UTG_vs_SB_3bet_call', 'UTG_vs_SB_3bet_4bet'],
        'UTG vs BB 3bet': ['UTG_vs_BB_3bet_fold', 'UTG_vs_BB_3bet_call', 'UTG_vs_BB_3bet_4bet'],
        'MP vs BTN 3bet': ['MP_vs_BTN_3bet_fold', 'MP_vs_BTN_3bet_call', 'MP_vs_BTN_3bet_4bet'],
        'MP vs SB 3bet': ['MP_vs_SB_3bet_fold', 'MP_vs_SB_3bet_call', 'MP_vs_SB_3bet_4bet'],
        'MP vs BB 3bet': ['MP_vs_BB_3bet_fold', 'MP_vs_BB_3bet_call', 'MP_vs_BB_3bet_4bet'],
        'CO vs BTN 3bet': ['CO_vs_BTN_3bet_fold', 'CO_vs_BTN_3bet_call', 'CO_vs_BTN_3bet_4bet'],
        'CO vs SB 3bet': ['CO_vs_SB_3bet_fold', 'CO_vs_SB_3bet_call', 'CO_vs_SB_3bet_4bet'],
        'CO vs BB 3bet': ['CO_vs_BB_3bet_fold', 'CO_vs_BB_3bet_call', 'CO_vs_BB_3bet_4bet'],
        'BTN vs SB 3bet': ['BTN_vs_SB_3bet_fold', 'BTN_vs_SB_3bet_call', 'BTN_vs_SB_3bet_4bet'],
        'BTN vs BB 3bet': ['BTN_vs_BB_3bet_fold', 'BTN_vs_BB_3bet_call', 'BTN_vs_BB_3bet_4bet'],
        'SB vs BB 3bet': ['SB_vs_BB_3bet_fold', 'SB_vs_BB_3bet_call', 'SB_vs_BB_3bet_4bet'],
        'BB vs BTN 4bet': ['BB_vs_BTN_4bet_fold', 'BB_vs_BTN_4bet_call', 'BB_vs_BTN_4bet_5bet'],
        'BB vs CO 4bet': ['BB_vs_CO_4bet_fold', 'BB_vs_CO_4bet_call', 'BB_vs_CO_4bet_5bet'],
        'SB vs BTN 4bet': ['SB_vs_BTN_4bet_fold', 'SB_vs_BTN_4bet_call', 'SB_vs_BTN_4bet_5bet'],
        'SB vs UTG+BTN': ['SB_vs_UTG_BTN_fold', 'SB_vs_UTG_BTN_call', 'SB_vs_UTG_BTN_3bet'],
        'BB vs UTG+BTN': ['BB_vs_UTG_BTN_fold', 'BB_vs_UTG_BTN_call', 'BB_vs_UTG_BTN_3bet'],
        'SB vs MP+BTN': ['SB_vs_MP_BTN_fold', 'SB_vs_MP_BTN_call', 'SB_vs_MP_BTN_3bet'],
        'BB vs MP+BTN': ['BB_vs_MP_BTN_fold', 'BB_vs_MP_BTN_call', 'BB_vs_MP_BTN_3bet'],
        'SB vs CO+BTN': ['SB_vs_CO_BTN_fold', 'SB_vs_CO_BTN_call', 'SB_vs_CO_BTN_3bet'],
        'BB vs CO+BTN': ['BB_vs_CO_BTN_fold', 'BB_vs_CO_BTN_call', 'BB_vs_CO_BTN_3bet'],
    }

    all_incomplete = {}
    total_issues = 0

    for group_name, scenarios in scenario_groups.items():
        incomplete = check_scenario_group(ranges, scenarios, group_name)

        if incomplete:
            all_incomplete[group_name] = incomplete
            total_issues += len(incomplete)

    # Print results
    if not all_incomplete:
        print("✅ ALL SCENARIOS SUM TO 100%!")
        print("No issues found - all data is complete and consistent.")
        return

    print(f"⚠️  Found {total_issues} hands with incomplete totals")
    print()

    for group_name, hands in sorted(all_incomplete.items()):
        print("=" * 80)
        print(f"GROUP: {group_name}")
        print("=" * 80)
        print()

        for item in hands:
            hand = item['hand']
            total = item['total']
            missing = item['missing']
            actions = item['actions']

            print(f"Hand: {hand:<6} Total: {total:>6.1f}%  Missing: {missing:>6.1f}%")

            for action, freq in sorted(actions.items()):
                action_name = action.split('_')[-1].capitalize()
                print(f"  {action_name:<10} {freq*100:>6.1f}%")

            print()

    # Save to file
    with open('/root/Documents/Ploit/solver/INCOMPLETE_TOTALS.txt', 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("HANDS WITH INCOMPLETE ACTION TOTALS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total issues found: {total_issues}\n\n")

        for group_name, hands in sorted(all_incomplete.items()):
            f.write("=" * 80 + "\n")
            f.write(f"GROUP: {group_name}\n")
            f.write("=" * 80 + "\n\n")

            for item in hands:
                hand = item['hand']
                total = item['total']
                missing = item['missing']
                actions = item['actions']

                f.write(f"Hand: {hand:<6} Total: {total:>6.1f}%  Missing: {missing:>6.1f}%\n")

                for action, freq in sorted(actions.items()):
                    action_name = action.split('_')[-1].capitalize()
                    f.write(f"  {action_name:<10} {freq*100:>6.1f}%\n")

                f.write("\n")

    print("=" * 80)
    print(f"Report saved to: /root/Documents/Ploit/solver/INCOMPLETE_TOTALS.txt")
    print("=" * 80)


if __name__ == '__main__':
    main()
