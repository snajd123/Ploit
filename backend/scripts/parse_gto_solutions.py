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

        Returns dict with:
        - gto_bet_frequency: % of range that bets
        - gto_check_frequency: % of range that checks
        - gto_fold_frequency: % of range that folds
        - gto_call_frequency: % of range that calls
        - gto_raise_frequency: % of range that raises
        """
        if not self.data:
            return {}

        # Navigate to root node
        root = self.data.get('tree', {})

        # Get action distribution from root
        actions = root.get('actions', [])
        strategy = root.get('strategy', [])

        if not actions or not strategy:
            return {}

        # Map actions to frequencies
        freq_map = {}
        for action, freq in zip(actions, strategy):
            action_type = self._classify_action(action)
            freq_map[action_type] = freq_map.get(action_type, 0.0) + freq

        # Convert to percentages
        return {
            'gto_bet_frequency': round(freq_map.get('bet', 0.0) * 100, 2),
            'gto_check_frequency': round(freq_map.get('check', 0.0) * 100, 2),
            'gto_fold_frequency': round(freq_map.get('fold', 0.0) * 100, 2),
            'gto_call_frequency': round(freq_map.get('call', 0.0) * 100, 2),
            'gto_raise_frequency': round(freq_map.get('raise', 0.0) * 100, 2),
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

        Returns:
        - gto_bet_size_small: Small bet sizing (% of pot)
        - gto_bet_size_medium: Medium bet sizing
        - gto_bet_size_large: Large bet sizing
        """
        if not self.data:
            return {}

        root = self.data.get('tree', {})
        actions = root.get('actions', [])
        strategy = root.get('strategy', [])

        # Extract bet sizes
        bet_sizes = {}
        for action, freq in zip(actions, strategy):
            if 'bet' in action.lower() and freq > 0.05:  # Only significant actions
                # Try to extract size from action name (e.g., "bet_50" = 50% pot)
                parts = action.split('_')
                if len(parts) > 1:
                    try:
                        size = int(parts[1])
                        if size < 40:
                            bet_sizes['small'] = size
                        elif size < 65:
                            bet_sizes['medium'] = size
                        else:
                            bet_sizes['large'] = size
                    except:
                        pass

        return {
            'gto_bet_size_small': bet_sizes.get('small'),
            'gto_bet_size_medium': bet_sizes.get('medium'),
            'gto_bet_size_large': bet_sizes.get('large'),
        }

    def extract_evs(self) -> Dict:
        """
        Extract expected values for each player.

        Returns:
        - ev_oop: EV for out-of-position player (in BB)
        - ev_ip: EV for in-position player (in BB)
        """
        if not self.data:
            return {}

        evs = self.data.get('evs', {})

        return {
            'ev_oop': round(evs.get('player0', 0.0), 2),
            'ev_ip': round(evs.get('player1', 0.0), 2),
        }

    def extract_ranges(self) -> Dict:
        """
        Extract hand ranges for each action.

        Returns JSONB-formatted ranges for:
        - gto_betting_range
        - gto_checking_range
        - gto_raising_range
        - gto_calling_range
        - gto_folding_range
        """
        if not self.data:
            return {}

        # TexasSolver stores ranges in the 'ranges' section
        ranges = self.data.get('ranges', {})

        # For now, return simplified structure
        # Full implementation would parse hand-by-hand strategies
        return {
            'gto_betting_range': json.dumps(ranges.get('player0_betting', {})),
            'gto_checking_range': json.dumps(ranges.get('player0_checking', {})),
            'gto_raising_range': json.dumps(ranges.get('player0_raising', {})),
            'gto_calling_range': json.dumps(ranges.get('player0_calling', {})),
            'gto_folding_range': json.dumps(ranges.get('player0_folding', {})),
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
            print(f"    EV (OOP): {solution.get('ev_oop', 0):.2f} BB")
            print(f"    EV (IP):  {solution.get('ev_ip', 0):.2f} BB")
        else:
            print(f"  ✗ Failed to parse {json_file.name}")

    return solutions


def generate_sql_insert(solution: Dict) -> str:
    """Generate SQL INSERT statement for a solution"""
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
    {solution.get('gto_bet_frequency', 'NULL')},
    {solution.get('gto_check_frequency', 'NULL')},
    {solution.get('gto_fold_frequency', 'NULL')},
    {solution.get('gto_call_frequency', 'NULL')},
    {solution.get('gto_raise_frequency', 'NULL')},
    {solution.get('gto_bet_size_small') or 'NULL'},
    {solution.get('gto_bet_size_medium') or 'NULL'},
    {solution.get('gto_bet_size_large') or 'NULL'},
    {solution.get('ev_oop', 'NULL')},
    {solution.get('ev_ip', 'NULL')},
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
