"""
Parse TexasSolver output JSON files and prepare data for database import.

This script processes the JSON output from TexasSolver and extracts:
- GTO action frequencies (bet/check/fold/call/raise percentages)
- Bet sizing distributions
- Expected values for each position
- Hand ranges for each action

Output is formatted for insertion into the gto_solutions table.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from decimal import Decimal


class GTOSolutionParser:
    """Parser for TexasSolver JSON output files"""

    def __init__(self, json_file_path: str):
        self.json_file = json_file_path
        self.data = None
        self.scenario_name = Path(json_file_path).stem

    def load(self) -> bool:
        """Load JSON file"""
        try:
            with open(self.json_file, 'r') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading {self.json_file}: {e}")
            return False

    def extract_frequencies(self) -> Dict:
        """
        Extract action frequencies from the game tree.

        TexasSolver JSON structure:
        {
            "actions": ["CHECK", "BET 3.000000", "BET 6.000000", "BET 97.000000"],
            "strategy": {
                "actions": [...],
                "strategy": {
                    "2d2c": [0.999769, 0.000219, 0.000010, 0.0],
                    "2h2c": [0.999774, 0.000215, 0.000010, 0.0],
                    ... 279 hand combos
                }
            }
        }

        Returns dict with:
        - gto_bet_frequency: % of range that bets
        - gto_check_frequency: % of range that checks
        - gto_fold_frequency: % of range that folds (for IP facing bet)
        - gto_call_frequency: % of range that calls (for IP facing bet)
        - gto_raise_frequency: % of range that raises
        """
        if not self.data:
            return {}

        # Get actions list from root
        actions = self.data.get('actions', [])

        # Get hand-by-hand strategies from root
        strategy_data = self.data.get('strategy', {})
        hand_strategies = strategy_data.get('strategy', {})

        if not actions or not hand_strategies:
            print(f"  Warning: No actions or strategies found in JSON")
            return {}

        # Calculate average frequency for each action across all hands
        num_hands = len(hand_strategies)
        action_freqs = {}

        for action_idx, action in enumerate(actions):
            # Sum frequencies for this action across all hand combos
            total_freq = sum(
                hand_freqs[action_idx]
                for hand_freqs in hand_strategies.values()
            )
            # Average and convert to percentage
            avg_freq = (total_freq / num_hands) * 100

            # Classify action type
            action_type = self._classify_action(action)
            action_freqs[action_type] = action_freqs.get(action_type, 0.0) + avg_freq

        return {
            'gto_bet_frequency': round(action_freqs.get('bet', 0.0), 2),
            'gto_check_frequency': round(action_freqs.get('check', 0.0), 2),
            'gto_fold_frequency': round(action_freqs.get('fold', 0.0), 2),
            'gto_call_frequency': round(action_freqs.get('call', 0.0), 2),
            'gto_raise_frequency': round(action_freqs.get('raise', 0.0), 2),
        }

    def _classify_action(self, action: str) -> str:
        """Classify action string into action type"""
        action_lower = action.lower()

        if 'fold' in action_lower:
            return 'fold'
        elif 'check' in action_lower:
            return 'check'
        elif 'call' in action_lower:
            return 'call'
        elif 'raise' in action_lower or 'reraise' in action_lower:
            return 'raise'
        elif 'bet' in action_lower or 'allin' in action_lower:
            return 'bet'
        else:
            return 'unknown'

    def extract_bet_sizes(self) -> Dict:
        """
        Extract bet sizing distribution.

        TexasSolver bet actions format: "BET 3.000000" means bet of 3 BB
        Need to convert to % of pot based on scenario pot size.

        Returns:
        - gto_bet_size_small: Small bet sizing (% of pot)
        - gto_bet_size_medium: Medium bet sizing
        - gto_bet_size_large: Large bet sizing
        """
        if not self.data:
            return {}

        actions = self.data.get('actions', [])

        # Extract bet sizes from action strings
        bet_sizes_bb = []
        for action in actions:
            if action.startswith('BET '):
                try:
                    # Parse "BET 3.000000" -> 3.0 BB
                    size_bb = float(action.split()[1])
                    bet_sizes_bb.append(size_bb)
                except (ValueError, IndexError):
                    pass

        # Convert BB to % of pot
        # Assume pot size from scenario (5.5 BB for SRP, 20.5 BB for 3bet)
        pot_size = 5.5  # Default SRP pot
        if '3bet' in self.scenario_name.lower():
            pot_size = 20.5

        bet_sizes_pct = sorted([round((size / pot_size) * 100) for size in bet_sizes_bb])

        # Classify into small/medium/large
        result = {}
        if len(bet_sizes_pct) >= 1:
            result['gto_bet_size_small'] = bet_sizes_pct[0]
        if len(bet_sizes_pct) >= 2:
            result['gto_bet_size_medium'] = bet_sizes_pct[1]
        if len(bet_sizes_pct) >= 3:
            result['gto_bet_size_large'] = bet_sizes_pct[2]

        return {
            'gto_bet_size_small': result.get('gto_bet_size_small'),
            'gto_bet_size_medium': result.get('gto_bet_size_medium'),
            'gto_bet_size_large': result.get('gto_bet_size_large'),
        }

    def extract_evs(self) -> Dict:
        """
        Extract expected values for each player.

        Note: EV calculation from TexasSolver's full game tree is complex.
        For MVP, we'll leave EVs as NULL and can add them later if needed.
        The critical data is the action frequencies, not the EVs.

        Returns:
        - ev_oop: EV for out-of-position player (in BB) - NULL for now
        - ev_ip: EV for in-position player (in BB) - NULL for now
        """
        # Return NULL - can calculate from game tree later if needed
        return {
            'ev_oop': None,
            'ev_ip': None,
        }

    def extract_ranges(self) -> Dict:
        """
        Extract hand ranges for each action.

        Note: Full hand-by-hand range extraction would require parsing the
        strategy for each action and categorizing hands. For MVP, we'll store
        the frequencies (which are already averaged across all hands) and can
        add detailed ranges later if needed.

        Returns JSONB-formatted ranges for:
        - gto_betting_range - NULL for now
        - gto_checking_range - NULL for now
        - gto_raising_range - NULL for now
        - gto_calling_range - NULL for now
        - gto_folding_range - NULL for now
        """
        # Return NULL - can extract detailed hand ranges later if needed
        return {
            'gto_betting_range': None,
            'gto_checking_range': None,
            'gto_raising_range': None,
            'gto_calling_range': None,
            'gto_folding_range': None,
        }

    def parse_scenario_name(self) -> Dict:
        """
        Parse scenario name to extract metadata.

        Example: "01_SRP_Ks7c3d_cbet" ->
        - scenario_name: "SRP_Ks7c3d_cbet"
        - scenario_type: "srp_flop"
        - board: "Ks7c3d"
        - position_oop: "BB"
        - position_ip: "BTN"
        """
        parts = self.scenario_name.split('_')

        # Remove numeric prefix if present
        if parts[0].isdigit():
            parts = parts[1:]

        scenario_type = parts[0].lower()  # SRP or 3BET
        board = parts[1] if len(parts) > 1 else None
        action = parts[2] if len(parts) > 2 else 'cbet'

        # Classify scenario type
        if scenario_type == '3bet':
            scenario_type = '3bet_pot'
        elif scenario_type == 'srp':
            scenario_type = 'srp_flop'
        else:
            scenario_type = 'unknown'

        return {
            'scenario_name': '_'.join(parts),
            'scenario_type': scenario_type,
            'board': board,
            'position_oop': 'BB',  # All our scenarios are BB (OOP)
            'position_ip': 'BTN',  # All our scenarios are BTN (IP)
        }

    def extract_all(self) -> Dict:
        """Extract all data from solution"""
        if not self.load():
            return None

        result = {}

        # Scenario metadata
        result.update(self.parse_scenario_name())

        # Pot size and stack (hardcoded based on scenario type)
        if result['scenario_type'] == '3bet_pot':
            result['pot_size'] = 20.5
            result['stack_depth'] = 90.0
        else:
            result['pot_size'] = 5.5
            result['stack_depth'] = 97.5

        # GTO frequencies
        result.update(self.extract_frequencies())

        # Bet sizes
        result.update(self.extract_bet_sizes())

        # EVs
        result.update(self.extract_evs())

        # Ranges (JSONB)
        result.update(self.extract_ranges())

        # Description
        result['description'] = self._generate_description(result)

        # Solver metadata
        result['solver_version'] = 'TexasSolver-0.2.0'

        return result

    def _generate_description(self, data: Dict) -> str:
        """Generate human-readable description"""
        board = data.get('board', 'unknown')
        scenario_type = data.get('scenario_type', 'unknown')
        bet_freq = data.get('gto_bet_frequency', 0)

        if scenario_type == '3bet_pot':
            return f"3-bet pot c-bet decision on {board} board. GTO bets {bet_freq:.1f}% of range."
        else:
            return f"Single raised pot c-bet decision on {board} board. GTO bets {bet_freq:.1f}% of range."


def parse_all_solutions(output_dir: str) -> List[Dict]:
    """Parse all JSON solution files in a directory"""
    output_path = Path(output_dir)

    if not output_path.exists():
        print(f"Output directory not found: {output_dir}")
        return []

    solutions = []
    json_files = list(output_path.glob('*.json'))

    print(f"Found {len(json_files)} solution files")

    for json_file in sorted(json_files):
        print(f"\nParsing: {json_file.name}")

        parser = GTOSolutionParser(str(json_file))
        solution = parser.extract_all()

        if solution:
            solutions.append(solution)
            print(f"  ✓ Extracted: {solution['scenario_name']}")
            print(f"    Bet freq: {solution.get('gto_bet_frequency', 0):.1f}%")

            # Handle None values for EVs
            ev_oop = solution.get('ev_oop')
            ev_ip = solution.get('ev_ip')
            if ev_oop is not None and ev_ip is not None:
                print(f"    EV (OOP): {ev_oop:.2f} BB")
                print(f"    EV (IP):  {ev_ip:.2f} BB")
            else:
                print(f"    EVs: Not extracted (can add later if needed)")
        else:
            print(f"  ✗ Failed to parse {json_file.name}")

    return solutions


def generate_sql_insert(solution: Dict) -> str:
    """Generate SQL INSERT statement for a solution"""
    # Helper function to format values for SQL
    def fmt_val(val):
        if val is None:
            return 'NULL'
        return str(val)

    sql = f"""
INSERT INTO gto_solutions (
    scenario_name, scenario_type, board,
    position_oop, position_ip,
    pot_size, stack_depth,
    gto_bet_frequency, gto_check_frequency,
    gto_fold_frequency, gto_call_frequency, gto_raise_frequency,
    gto_bet_size_small, gto_bet_size_medium, gto_bet_size_large,
    ev_oop, ev_ip,
    description, solver_version
) VALUES (
    '{solution['scenario_name']}',
    '{solution['scenario_type']}',
    '{solution.get('board', '')}',
    '{solution['position_oop']}',
    '{solution['position_ip']}',
    {solution['pot_size']},
    {solution['stack_depth']},
    {fmt_val(solution.get('gto_bet_frequency'))},
    {fmt_val(solution.get('gto_check_frequency'))},
    {fmt_val(solution.get('gto_fold_frequency'))},
    {fmt_val(solution.get('gto_call_frequency'))},
    {fmt_val(solution.get('gto_raise_frequency'))},
    {fmt_val(solution.get('gto_bet_size_small'))},
    {fmt_val(solution.get('gto_bet_size_medium'))},
    {fmt_val(solution.get('gto_bet_size_large'))},
    {fmt_val(solution.get('ev_oop'))},
    {fmt_val(solution.get('ev_ip'))},
    '{solution.get('description', '')}',
    '{solution.get('solver_version', 'TexasSolver-0.2.0')}'
)
ON CONFLICT (scenario_name) DO UPDATE SET
    gto_bet_frequency = EXCLUDED.gto_bet_frequency,
    gto_check_frequency = EXCLUDED.gto_check_frequency,
    ev_oop = EXCLUDED.ev_oop,
    ev_ip = EXCLUDED.ev_ip;
"""
    return sql


if __name__ == "__main__":
    # Parse all solutions in the outputs directory
    output_dir = "/root/Documents/Ploit/solver/outputs"

    solutions = parse_all_solutions(output_dir)

    print(f"\n{'='*60}")
    print(f"Successfully parsed {len(solutions)}/15 solutions")
    print(f"{'='*60}")

    if solutions:
        # Generate SQL file
        sql_file = "/root/Documents/Ploit/backend/scripts/import_gto_solutions.sql"

        with open(sql_file, 'w') as f:
            f.write("-- Auto-generated SQL to import GTO solutions\n")
            f.write(f"-- Generated from {len(solutions)} TexasSolver output files\n\n")

            for solution in solutions:
                f.write(generate_sql_insert(solution))
                f.write("\n")

        print(f"\nGenerated SQL import file: {sql_file}")
        print(f"Run with: psql ploit_db < {sql_file}")
