#!/usr/bin/env python3
"""
GTO Solutions Import Script

Imports all GTO solver solutions from the solver directory into the database
with multi-level board categorization and pre-computed aggregates.

Usage:
    python3 import_gto_solutions.py

This script:
1. Scans solver output directory for solution files
2. Parses config files to extract board and scenario information
3. Categorizes each board using BoardCategorizer
4. Imports solutions into gto_solutions table
5. Calculates aggregates for all categories
6. Updates gto_category_aggregates table
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "services"))

from board_categorizer import BoardCategorizer


class GTOSolutionImporter:
    """Imports GTO solutions from solver directory into database."""

    def __init__(self, solver_dir: str, config_dir: str, output_dir: str):
        """
        Initialize importer.

        Args:
            solver_dir: Path to solver directory
            config_dir: Path to config files directory
            output_dir: Path to output files directory
        """
        self.solver_dir = Path(solver_dir)
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.categorizer = BoardCategorizer()

        # Statistics
        self.stats = {
            'total_configs': 0,
            'total_solutions': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0
        }

        # Category tracking for aggregates
        self.category_solutions = {
            'l1': defaultdict(list),
            'l2': defaultdict(list),
            'l3': defaultdict(list)
        }

    def parse_config_file(self, config_path: Path) -> Optional[Dict]:
        """
        Parse a solver config file to extract scenario information.

        Args:
            config_path: Path to config file

        Returns:
            Dictionary with scenario data, or None if parse fails
        """
        try:
            with open(config_path, 'r') as f:
                content = f.read()

            # Extract key fields
            scenario = {}

            # Board
            board_match = re.search(r'set_board\s+([\w,]+)', content)
            if board_match:
                board_str = board_match.group(1).replace(',', '')
                scenario['board'] = board_str
            else:
                return None

            # Pot size
            pot_match = re.search(r'set_pot\s+([\d.]+)', content)
            if pot_match:
                scenario['pot_size'] = float(pot_match.group(1))

            # Effective stack
            stack_match = re.search(r'set_effective_stack\s+([\d.]+)', content)
            if stack_match:
                scenario['effective_stack'] = float(stack_match.group(1))

            # Ranges
            ip_range_match = re.search(r'set_range_ip\s+([\w,:.]+)', content)
            if ip_range_match:
                scenario['ip_range'] = ip_range_match.group(1)

            oop_range_match = re.search(r'set_range_oop\s+([\w,:.]+)', content)
            if oop_range_match:
                scenario['oop_range'] = oop_range_match.group(1)

            # Accuracy
            accuracy_match = re.search(r'set_accuracy\s+([\d.]+)', content)
            if accuracy_match:
                scenario['accuracy'] = float(accuracy_match.group(1))

            # Max iterations
            iter_match = re.search(r'set_max_iteration\s+(\d+)', content)
            if iter_match:
                scenario['iterations'] = int(iter_match.group(1))

            return scenario

        except Exception as e:
            print(f"Error parsing {config_path}: {e}")
            return None

    def extract_scenario_from_filename(self, filename: str) -> Dict:
        """
        Extract scenario information from filename.

        Filename format: "019_SRP_A83r_check.txt"
        Components: [number]_[scenario_type]_[board]_[action].txt

        Args:
            filename: Config/solution filename

        Returns:
            Dictionary with extracted info
        """
        info = {}

        # Remove extension
        name = filename.replace('.txt', '').replace('.json', '')

        # Split by underscore
        parts = name.split('_')

        if len(parts) >= 3:
            # Scenario type (SRP, 3BP, etc.)
            info['scenario_type'] = parts[1] if len(parts) > 1 else 'SRP'

            # Action sequence (cbet, check, etc.)
            if len(parts) >= 4:
                info['action_sequence'] = parts[3]
            else:
                info['action_sequence'] = 'unknown'

            # Determine position context from action
            if 'oop' in name.lower():
                info['position_context'] = 'OOP'
            elif any(x in name.lower() for x in ['cbet', 'bet', 'raise']):
                info['position_context'] = 'IP'
            else:
                info['position_context'] = 'Unknown'

        return info

    def process_solution(self, config_filename: str) -> Optional[Dict]:
        """
        Process a single GTO solution.

        Args:
            config_filename: Name of config file (e.g., "019_SRP_A83r_check.txt")

        Returns:
            Dictionary with complete solution data, or None if processing fails
        """
        try:
            # Paths
            config_path = self.config_dir / config_filename
            output_filename = config_filename.replace('.txt', '.json')
            output_path = self.output_dir / output_filename

            # Check if files exist
            if not config_path.exists():
                print(f"Config not found: {config_path}")
                return None

            if not output_path.exists():
                print(f"Solution not found: {output_path}")
                return None

            # Parse config
            scenario = self.parse_config_file(config_path)
            if not scenario or 'board' not in scenario:
                print(f"Failed to parse config: {config_filename}")
                return None

            # Extract scenario info from filename
            filename_info = self.extract_scenario_from_filename(config_filename)
            scenario.update(filename_info)

            # Categorize board
            board = scenario['board']
            try:
                analysis = self.categorizer.analyze(board)
            except Exception as e:
                print(f"Failed to categorize board {board}: {e}")
                return None

            # Get file metadata
            file_size = output_path.stat().st_size
            solved_at = datetime.fromtimestamp(output_path.stat().st_mtime)

            # Build complete solution data
            solution = {
                'scenario_name': config_filename.replace('.txt', ''),
                'config_file': str(config_path),
                'output_file': str(output_path),
                'board': board,
                'flop_card_1': analysis.cards[0] if len(analysis.cards) > 0 else None,
                'flop_card_2': analysis.cards[1] if len(analysis.cards) > 1 else None,
                'flop_card_3': analysis.cards[2] if len(analysis.cards) > 2 else None,
                'board_category_l1': analysis.category_l1,
                'board_category_l2': analysis.category_l2,
                'board_category_l3': analysis.category_l3,
                'is_paired': analysis.is_paired,
                'is_rainbow': analysis.is_rainbow,
                'is_two_tone': analysis.is_two_tone,
                'is_monotone': analysis.is_monotone,
                'is_connected': analysis.is_connected,
                'is_highly_connected': analysis.is_highly_connected,
                'has_broadway': analysis.has_broadway,
                'is_dry': analysis.is_dry,
                'is_wet': analysis.is_wet,
                'high_card_rank': analysis.high_card_rank,
                'middle_card_rank': analysis.middle_card_rank,
                'low_card_rank': analysis.low_card_rank,
                'scenario_type': scenario.get('scenario_type'),
                'position_context': scenario.get('position_context'),
                'action_sequence': scenario.get('action_sequence'),
                'pot_size': scenario.get('pot_size'),
                'effective_stack': scenario.get('effective_stack'),
                'ip_range': scenario.get('ip_range'),
                'oop_range': scenario.get('oop_range'),
                'accuracy': scenario.get('accuracy'),
                'iterations': scenario.get('iterations'),
                'file_size_bytes': file_size,
                'solved_at': solved_at,
                'imported_at': datetime.now()
            }

            # Track for aggregate calculation
            self.category_solutions['l1'][analysis.category_l1].append(solution)
            self.category_solutions['l2'][analysis.category_l2].append(solution)
            self.category_solutions['l3'][analysis.category_l3].append(solution)

            return solution

        except Exception as e:
            print(f"Error processing {config_filename}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_aggregates(self) -> List[Dict]:
        """
        Calculate aggregates for all categories.

        Returns:
            List of aggregate dictionaries for gto_category_aggregates table
        """
        aggregates = []

        # Process each level
        for level_name, level_data in self.category_solutions.items():
            level_num = int(level_name[1])  # "l1" -> 1

            for category_name, solutions in level_data.items():
                if not solutions:
                    continue

                # Calculate statistics
                solution_count = len(solutions)

                # Average pot and stack sizes
                avg_pot = sum(s['pot_size'] for s in solutions if s.get('pot_size')) / solution_count
                avg_stack = sum(s['effective_stack'] for s in solutions if s.get('effective_stack')) / solution_count

                # Pick representative board (first one for now, could be improved)
                representative = solutions[0]

                aggregate = {
                    'category_level': level_num,
                    'category_name': category_name,
                    'solution_count': solution_count,
                    'total_scenarios': None,  # Could estimate based on category
                    'coverage_pct': None,
                    'representative_board': representative['board'],
                    'representative_solution_id': None,  # Will be set after DB insertion
                    'avg_pot_size': avg_pot,
                    'avg_stack_size': avg_stack,
                    'common_actions': None,  # Could extract from solution files
                    'avg_cbet_freq': None,  # Would need solution parsing
                    'avg_check_freq': None,
                    'avg_fold_to_cbet_freq': None,
                    'last_updated': datetime.now()
                }

                aggregates.append(aggregate)

        return aggregates

    def run_import(self, dry_run: bool = False) -> Dict:
        """
        Run the full import process.

        Args:
            dry_run: If True, process but don't write to database

        Returns:
            Dictionary with import statistics
        """
        print("=" * 80)
        print("GTO SOLUTIONS IMPORT")
        print("=" * 80)
        print(f"Solver directory: {self.solver_dir}")
        print(f"Config directory: {self.config_dir}")
        print(f"Output directory: {self.output_dir}")
        print()

        # Find all config files
        config_files = sorted(self.config_dir.glob("*.txt"))
        self.stats['total_configs'] = len(config_files)

        print(f"Found {len(config_files)} config files\n")

        # Process each solution
        solutions = []
        for i, config_path in enumerate(config_files, 1):
            config_filename = config_path.name
            print(f"[{i}/{len(config_files)}] Processing {config_filename}...")

            solution = self.process_solution(config_filename)

            if solution:
                solutions.append(solution)
                self.stats['imported'] += 1
                print(f"  ✓ Imported: {solution['board']} -> L3: {solution['board_category_l3']}")
            else:
                self.stats['skipped'] += 1
                print(f"  ✗ Skipped")

        print()

        # Calculate aggregates
        print("Calculating category aggregates...")
        aggregates = self.calculate_aggregates()

        print(f"  Generated {len(aggregates)} category aggregates")
        print()

        # Summary
        print("=" * 80)
        print("IMPORT SUMMARY")
        print("=" * 80)
        print(f"Total config files: {self.stats['total_configs']}")
        print(f"Successfully imported: {self.stats['imported']}")
        print(f"Skipped: {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        print()

        # Category breakdown
        print("Category Breakdown:")
        for level in ['l1', 'l2', 'l3']:
            level_num = int(level[1])
            categories = self.category_solutions[level]
            print(f"  Level {level_num}: {len(categories)} categories")
            for cat_name, cat_solutions in sorted(categories.items(), key=lambda x: -len(x[1]))[:5]:
                print(f"    - {cat_name}: {len(cat_solutions)} solutions")

        print()

        if dry_run:
            print("DRY RUN - No data written to database")
        else:
            print("TODO: Database insertion not yet implemented")
            print("Next step: Connect to database and insert solutions + aggregates")

        return {
            'stats': self.stats,
            'solutions': solutions,
            'aggregates': aggregates
        }


def main():
    """Main entry point."""
    # Paths
    solver_dir = Path("/root/Documents/Ploit/solver")
    config_dir = solver_dir / "configs_comprehensive"
    output_dir = solver_dir / "outputs_comprehensive"

    # Create importer
    importer = GTOSolutionImporter(
        solver_dir=str(solver_dir),
        config_dir=str(config_dir),
        output_dir=str(output_dir)
    )

    # Run import (dry run for now)
    results = importer.run_import(dry_run=True)

    # Export results to JSON for inspection
    output_file = solver_dir / "import_results.json"
    print(f"\nExporting results to {output_file}...")

    # Convert datetime objects to strings for JSON serialization
    def serialize_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    with open(output_file, 'w') as f:
        json.dump({
            'stats': results['stats'],
            'solution_count': len(results['solutions']),
            'aggregate_count': len(results['aggregates']),
            'sample_solutions': results['solutions'][:5],  # First 5
            'all_aggregates': results['aggregates']
        }, f, indent=2, default=serialize_datetime)

    print(f"Results exported successfully!")


if __name__ == "__main__":
    main()
