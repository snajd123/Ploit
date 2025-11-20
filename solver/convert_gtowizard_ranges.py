#!/usr/bin/env python3
"""
Convert GTOWizard combo-by-combo ranges to TexasSolver format.

GTOWizard format: 2d2c: 1, 2h2c: 1, 2h2d: 1, ...
TexasSolver format: 22, AKs, AKo:0.5, ...
"""

import re
from collections import defaultdict
from typing import Dict, List, Tuple

# Card rank mapping
RANKS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
         'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
RANK_NAMES = {v: k for k, v in RANKS.items()}

def parse_combo(combo: str) -> Tuple[str, str, str, str]:
    """Parse a combo like 'AhKd' into (rank1, suit1, rank2, suit2)."""
    combo = combo.strip()
    rank1, suit1 = combo[0], combo[1]
    rank2, suit2 = combo[2], combo[3]
    return rank1, suit1, rank2, suit2

def normalize_hand(rank1: str, rank2: str) -> Tuple[str, str]:
    """Normalize hand so higher rank comes first."""
    if RANKS[rank1] < RANKS[rank2]:
        return rank2, rank1
    return rank1, rank2

def parse_gtowizard_range(range_text: str) -> Dict[str, float]:
    """
    Parse GTOWizard range text.

    Args:
        range_text: String like "2d2c: 1,2h2c: 1,3c2c: 1,..."

    Returns:
        Dict mapping combo (e.g., "AhKd") to frequency (0-1)
    """
    combos = {}

    # Split by comma and parse each combo
    for item in range_text.split(','):
        item = item.strip()
        if ':' not in item:
            continue

        combo, freq = item.split(':')
        combo = combo.strip()
        freq = float(freq.strip())

        combos[combo] = freq

    return combos

def combos_to_texasolver(combos: Dict[str, float]) -> str:
    """
    Convert GTOWizard combo dict to TexasSolver range string.

    Args:
        combos: Dict mapping combo (e.g., "AhKd") to frequency

    Returns:
        TexasSolver format string like "AA,KK,AKs,AKo:0.5,..."
    """
    # Group combos by hand type
    hands = defaultdict(list)  # hand -> [(combo, freq), ...]

    for combo, freq in combos.items():
        rank1, suit1, rank2, suit2 = parse_combo(combo)
        rank1, rank2 = normalize_hand(rank1, rank2)

        # Determine hand type
        if rank1 == rank2:
            # Pair
            hand = f"{rank1}{rank2}"
        elif suit1 == suit2:
            # Suited
            hand = f"{rank1}{rank2}s"
        else:
            # Offsuit
            hand = f"{rank1}{rank2}o"

        hands[hand].append((combo, freq))

    # Convert to TexasSolver format
    result = []

    # Sort hands by rank (high to low)
    def hand_sort_key(hand: str) -> Tuple[int, int, int]:
        """Sort key: pairs first, then by high card, then by low card."""
        if hand.endswith('s') or hand.endswith('o'):
            rank1 = RANKS[hand[0]]
            rank2 = RANKS[hand[1]]
            suited = 1 if hand.endswith('s') else 0
            return (0, rank1, rank2, suited)  # Non-pairs
        else:
            # Pair
            rank = RANKS[hand[0]]
            return (1, rank, rank, 0)  # Pairs come first

    for hand in sorted(hands.keys(), key=hand_sort_key, reverse=True):
        combo_list = hands[hand]

        # Check if all combos have same frequency
        freqs = [freq for _, freq in combo_list]

        if len(set(freqs)) == 1:
            # All same frequency
            freq = freqs[0]
            if freq == 1.0:
                result.append(hand)
            else:
                result.append(f"{hand}:{freq}")
        else:
            # Mixed frequencies - use average
            avg_freq = sum(freqs) / len(freqs)
            if avg_freq >= 0.99:
                result.append(hand)
            else:
                result.append(f"{hand}:{avg_freq:.2f}")

    return ','.join(result)

def convert_ranges_file(input_file: str, output_file: str):
    """
    Convert gtowizard_ranges.txt to solver-ready format.

    Args:
        input_file: Path to gtowizard_ranges.txt
        output_file: Path to output converted ranges
    """
    with open(input_file, 'r') as f:
        content = f.read()

    # Find all range sections
    sections = re.findall(r'\[(TODO|DONE)\] (\w+)\n.*?\n---\n(.*?)(?=\n\n\[|$)',
                         content, re.DOTALL)

    converted = {}

    for status, name, range_text in sections:
        if status == 'TODO' or not range_text.strip():
            continue

        try:
            # Parse and convert
            combos = parse_gtowizard_range(range_text)
            texasolver_range = combos_to_texasolver(combos)
            converted[name] = texasolver_range
            print(f"✓ Converted {name}: {len(combos)} combos → {len(texasolver_range)} chars")
        except Exception as e:
            print(f"✗ Failed to convert {name}: {e}")

    # Write output
    with open(output_file, 'w') as f:
        f.write("# Converted GTOWizard Ranges\n")
        f.write("# Format: TexasSolver compatible\n\n")

        for name, range_str in sorted(converted.items()):
            f.write(f"[{name}]\n")
            f.write(f"{range_str}\n\n")

    print(f"\n✓ Converted {len(converted)} ranges")
    print(f"✓ Saved to: {output_file}")

if __name__ == '__main__':
    import sys

    input_file = 'gtowizard_ranges.txt'
    output_file = 'texasolver_ranges.txt'

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    print("GTOWizard → TexasSolver Range Converter")
    print("=" * 60)

    try:
        convert_ranges_file(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
