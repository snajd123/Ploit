#!/usr/bin/env python3
"""
Comprehensive Range Analysis for Cross-Verification
Analyzes all completed GTOWizard ranges and generates detailed report
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
        return f"{high}{low}"  # Pair
    elif high_suit == low_suit:
        return f"{high}{low}s"  # Suited
    else:
        return f"{high}{low}o"  # Offsuit


def analyze_range(combos, name):
    """Analyze a range and return detailed statistics"""
    if not combos:
        return None

    # Group by hand type
    hands = defaultdict(list)
    for combo, freq in combos.items():
        hand = combo_to_hand(combo)
        if hand:
            hands[hand].append(freq)

    # Calculate average frequency per hand
    hand_freqs = {}
    for hand, freqs in hands.items():
        hand_freqs[hand] = sum(freqs) / len(freqs)

    # Total combos weighted
    total_combos = sum(combos.values())
    max_combos = 1326
    range_percent = (total_combos / max_combos) * 100

    # Count pure vs mixed
    pure = sum(1 for f in combos.values() if f >= 0.999)
    mixed = sum(1 for f in combos.values() if 0 < f < 0.999)

    # Categorize hands
    pairs = sorted([h for h in hand_freqs if len(h) == 2],
                   key=lambda x: -hand_freqs[x])
    suited = sorted([h for h in hand_freqs if h.endswith('s')],
                    key=lambda x: -hand_freqs[x])
    offsuit = sorted([h for h in hand_freqs if h.endswith('o')],
                     key=lambda x: -hand_freqs[x])

    return {
        'name': name,
        'total_combos': total_combos,
        'percent': range_percent,
        'hand_freqs': hand_freqs,
        'pure_combos': pure,
        'mixed_combos': mixed,
        'pairs': pairs,
        'suited': suited,
        'offsuit': offsuit,
        'num_hands': len(hand_freqs)
    }


def format_hand_list(hands, hand_freqs, max_show=15):
    """Format hand list with frequencies"""
    result = []
    for i, hand in enumerate(hands[:max_show]):
        freq = hand_freqs[hand]
        if freq >= 0.999:
            result.append(hand)
        else:
            result.append(f"{hand}:{freq:.3f}")

    if len(hands) > max_show:
        result.append(f"... +{len(hands) - max_show} more")

    return result


def extract_ranges_from_file(filename):
    """Extract all [DONE] ranges from file"""
    with open(filename, 'r') as f:
        content = f.read()

    # Find all [DONE] scenarios
    pattern = r'\[DONE\]\s+(\w+)\s*\n#\s*GTOWizard:\s*(.*?)\n(.*?)\n\n'
    matches = re.finditer(pattern, content, re.DOTALL)

    ranges = []
    for match in matches:
        scenario_name = match.group(1)
        gto_path = match.group(2).strip()
        range_data = match.group(3).strip()

        combos = parse_combo_range(range_data)
        analysis = analyze_range(combos, scenario_name)

        if analysis:
            analysis['gto_path'] = gto_path
            ranges.append(analysis)

    return ranges


def generate_report(ranges):
    """Generate comprehensive verification report"""
    report = []

    report.append("=" * 80)
    report.append("COMPREHENSIVE RANGE ANALYSIS - CROSS-VERIFICATION REPORT")
    report.append("=" * 80)
    report.append("")
    report.append(f"Total scenarios analyzed: {len(ranges)}")
    report.append("")

    # Group by scenario type
    opening_ranges = [r for r in ranges if '_open' in r['name']]
    defense_ranges = [r for r in ranges if '_vs_' in r['name'] and '_fold' in r['name']]
    call_ranges = [r for r in ranges if '_vs_' in r['name'] and '_call' in r['name']]

    report.append("=" * 80)
    report.append("SECTION 1: OPENING RANGES (RFI)")
    report.append("=" * 80)
    report.append("")

    for r in opening_ranges:
        report.append(f"┌─ {r['name'].upper()}")
        report.append(f"│  Path: {r['gto_path']}")
        report.append(f"│  Range Size: {r['percent']:.1f}% ({r['total_combos']:.1f} combos)")
        report.append(f"│  Unique Hands: {r['num_hands']}")
        report.append(f"│  Pure (100%): {r['pure_combos']} combos | Mixed: {r['mixed_combos']} combos")
        report.append(f"│")

        if r['pairs']:
            pairs_str = ', '.join(format_hand_list(r['pairs'], r['hand_freqs'], 13))
            report.append(f"│  Pairs: {pairs_str}")

        if r['suited']:
            suited_str = ', '.join(format_hand_list(r['suited'], r['hand_freqs'], 20))
            report.append(f"│  Suited: {suited_str}")

        if r['offsuit']:
            offsuit_str = ', '.join(format_hand_list(r['offsuit'], r['hand_freqs'], 20))
            report.append(f"│  Offsuit: {offsuit_str}")

        report.append(f"└─")
        report.append("")

    report.append("=" * 80)
    report.append("SECTION 2: BB DEFENSE VS UTG")
    report.append("=" * 80)
    report.append("")

    bb_utg_ranges = [r for r in ranges if r['name'].startswith('BB_vs_UTG')]
    for r in bb_utg_ranges:
        report.append(f"┌─ {r['name'].upper()}")
        report.append(f"│  Path: {r['gto_path']}")
        report.append(f"│  Range Size: {r['percent']:.1f}% ({r['total_combos']:.1f} combos)")
        report.append(f"│  Unique Hands: {r['num_hands']}")
        report.append(f"│  Pure (100%): {r['pure_combos']} combos | Mixed: {r['mixed_combos']} combos")
        report.append(f"│")

        # Show top hands by frequency
        top_hands = sorted(r['hand_freqs'].items(), key=lambda x: -x[1])[:15]
        hands_str = ', '.join([f"{h}:{f:.3f}" if f < 0.999 else h for h, f in top_hands])
        report.append(f"│  Top Hands: {hands_str}")

        report.append(f"└─")
        report.append("")

    # Cross-verification: Check if fold + call frequencies make sense
    report.append("=" * 80)
    report.append("CROSS-VERIFICATION: BB vs UTG Action Frequencies")
    report.append("=" * 80)
    report.append("")

    bb_fold = next((r for r in ranges if r['name'] == 'BB_vs_UTG_fold'), None)
    bb_call = next((r for r in ranges if r['name'] == 'BB_vs_UTG_call'), None)

    if bb_fold and bb_call:
        report.append("Verifying that FOLD + CALL frequencies sum correctly:")
        report.append("")

        # Sample some hands
        sample_hands = ['22', '55', '77', 'ATo', 'QJo', 'JTs', '98s']

        report.append(f"{'Hand':<6} {'Fold %':<10} {'Call %':<10} {'3bet %':<10} {'Total':<10} {'Status'}")
        report.append("-" * 70)

        for hand in sample_hands:
            fold_freq = bb_fold['hand_freqs'].get(hand, 0.0)
            call_freq = bb_call['hand_freqs'].get(hand, 0.0)
            threebet_freq = 0.0  # Not filled yet
            total = fold_freq + call_freq + threebet_freq

            fold_pct = f"{fold_freq*100:.1f}%"
            call_pct = f"{call_freq*100:.1f}%"
            threebet_pct = f"{threebet_freq*100:.1f}%"
            total_pct = f"{total*100:.1f}%"

            # Status check (should be 100% when 3bet is added)
            if total >= 0.999:
                status = "✓ Complete"
            elif total > 0:
                status = f"⧗ Partial (need 3bet)"
            else:
                status = "✗ Missing"

            report.append(f"{hand:<6} {fold_pct:<10} {call_pct:<10} {threebet_pct:<10} {total_pct:<10} {status}")

        report.append("")
        report.append("NOTE: 3bet ranges not yet filled - totals will reach 100% after 3bet data added")
        report.append("")

    report.append("=" * 80)
    report.append("STATISTICAL SUMMARY")
    report.append("=" * 80)
    report.append("")

    for r in ranges:
        report.append(f"{r['name']:<25} {r['percent']:>6.1f}%  ({r['total_combos']:>6.1f} combos)  "
                     f"{r['num_hands']:>3} hands  Pure: {r['pure_combos']:>4}  Mixed: {r['mixed_combos']:>4}")

    report.append("")
    report.append("=" * 80)
    report.append("KEY INTERPRETATIONS")
    report.append("=" * 80)
    report.append("")
    report.append("✓ Mixed frequencies (e.g., 0.285, 0.72) represent GTO randomization")
    report.append("✓ Hands with freq < 1.0 are played that % of time for balance")
    report.append("✓ Missing hands in an action = 0% frequency for that action")
    report.append("✓ For defense ranges: Fold + Call + 3bet = 100% for each hand")
    report.append("✓ Pure combos (100%) are always played that way")
    report.append("✓ Range % = weighted combos / 1326 total possible combos")
    report.append("")

    return '\n'.join(report)


# Run the analysis
if __name__ == '__main__':
    print("Analyzing ranges from gtowizard_ranges.txt...")
    ranges = extract_ranges_from_file('/root/Documents/Ploit/solver/gtowizard_ranges.txt')

    if not ranges:
        print("No completed ranges found!")
    else:
        report = generate_report(ranges)

        # Save to file
        output_file = '/root/Documents/Ploit/solver/RANGE_VERIFICATION_REPORT.txt'
        with open(output_file, 'w') as f:
            f.write(report)

        print(f"\n✅ Analysis complete!")
        print(f"📄 Report saved to: {output_file}")
        print(f"📊 Analyzed {len(ranges)} scenarios\n")

        # Print report to console
        print(report)
