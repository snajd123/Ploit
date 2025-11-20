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
sys.path.insert(0, str(Path(__file__).parent.parent))

from board_categorizer import BoardCategorizer

# Database imports
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
    DB_AVAILABLE = True
except ImportError:
    print("Warning: psycopg2 not available. Running in dry-run mode only.")
    DB_AVAILABLE = False


class GTOSolutionImporter:
    """Imports GTO solutions from solver directory into database."""

    def __init__(self, solver_dir: str, config_dir: str, output_dir: str, db_url: Optional[str] = None):
        """
        Initialize importer.

        Args:
            solver_dir: Path to solver directory
            config_dir: Path to config files directory
            output_dir: Path to output files directory
            db_url: Database connection URL (optional)
        """
        self.solver_dir = Path(solver_dir)
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.categorizer = BoardCategorizer()
        self.db_url = db_url
        self.db_conn = None

        # Statistics
        self.stats = {
            'total_configs': 0,
            'total_solutions': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'db_inserted': 0
        }

        # Category tracking for aggregates
        self.category_solutions = {
            'l1': defaultdict(list),
            'l2': defaultdict(list),
            'l3': defaultdict(list)
        }

    def connect_db(self):
        """Connect to database."""
        if not DB_AVAILABLE:
            print("Database not available (psycopg2 not installed)")
            return False

        if not self.db_url:
            print("No database URL provided")
            return False

        try:
            self.db_conn = psycopg2.connect(self.db_url)
            print(f"✓ Connected to database")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            return False

    def close_db(self):
        """Close database connection."""
        if self.db_conn:
            self.db_conn.close()
            print("Database connection closed")

    def insert_solution(self, solution: Dict) -> bool:
        """
        Insert a solution into the database.

        Args:
            solution: Solution dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            return False

        try:
            cursor = self.db_conn.cursor()

            # Build INSERT query
            insert_query = """
                INSERT INTO gto_solutions (
                    scenario_name, config_file, output_file, board,
                    flop_card_1, flop_card_2, flop_card_3,
                    board_category_l1, board_category_l2, board_category_l3,
                    is_paired, is_rainbow, is_two_tone, is_monotone,
                    is_connected, is_highly_connected, has_broadway, is_dry, is_wet,
                    high_card_rank, middle_card_rank, low_card_rank,
                    scenario_type, position_context, action_sequence,
                    pot_size, effective_stack, ip_range, oop_range,
                    accuracy, iterations, file_size_bytes, solved_at, imported_at,
                    gto_check_frequency, gto_bet_frequency, gto_raise_frequency,
                    gto_fold_frequency, gto_call_frequency
                )
                VALUES (
                    %(scenario_name)s, %(config_file)s, %(output_file)s, %(board)s,
                    %(flop_card_1)s, %(flop_card_2)s, %(flop_card_3)s,
                    %(board_category_l1)s, %(board_category_l2)s, %(board_category_l3)s,
                    %(is_paired)s, %(is_rainbow)s, %(is_two_tone)s, %(is_monotone)s,
                    %(is_connected)s, %(is_highly_connected)s, %(has_broadway)s, %(is_dry)s, %(is_wet)s,
                    %(high_card_rank)s, %(middle_card_rank)s, %(low_card_rank)s,
                    %(scenario_type)s, %(position_context)s, %(action_sequence)s,
                    %(pot_size)s, %(effective_stack)s, %(ip_range)s, %(oop_range)s,
                    %(accuracy)s, %(iterations)s, %(file_size_bytes)s, %(solved_at)s, %(imported_at)s,
                    %(gto_check_frequency)s, %(gto_bet_frequency)s, %(gto_raise_frequency)s,
                    %(gto_fold_frequency)s, %(gto_call_frequency)s
                )
                ON CONFLICT (scenario_name) DO UPDATE SET
                    board_category_l1 = EXCLUDED.board_category_l1,
                    board_category_l2 = EXCLUDED.board_category_l2,
                    board_category_l3 = EXCLUDED.board_category_l3,
                    is_paired = EXCLUDED.is_paired,
                    is_rainbow = EXCLUDED.is_rainbow,
                    is_two_tone = EXCLUDED.is_two_tone,
                    is_monotone = EXCLUDED.is_monotone,
                    is_connected = EXCLUDED.is_connected,
                    is_highly_connected = EXCLUDED.is_highly_connected,
                    has_broadway = EXCLUDED.has_broadway,
                    is_dry = EXCLUDED.is_dry,
                    is_wet = EXCLUDED.is_wet,
                    high_card_rank = EXCLUDED.high_card_rank,
                    middle_card_rank = EXCLUDED.middle_card_rank,
                    low_card_rank = EXCLUDED.low_card_rank,
                    gto_check_frequency = EXCLUDED.gto_check_frequency,
                    gto_bet_frequency = EXCLUDED.gto_bet_frequency,
                    gto_raise_frequency = EXCLUDED.gto_raise_frequency,
                    gto_fold_frequency = EXCLUDED.gto_fold_frequency,
                    gto_call_frequency = EXCLUDED.gto_call_frequency
                RETURNING solution_id;
            """

            cursor.execute(insert_query, solution)
            solution_id = cursor.fetchone()[0]
            self.db_conn.commit()
            cursor.close()

            self.stats['db_inserted'] += 1
            return True

        except Exception as e:
            print(f"    ✗ Database error: {e}")
            self.db_conn.rollback()
            return False

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

    def extract_gto_frequencies(self, output_path: Path) -> Dict[str, float]:
        """
        Extract and aggregate GTO frequencies from solver output JSON.

        Args:
            output_path: Path to JSON solver output file

        Returns:
            Dictionary with aggregated frequencies (check_freq, bet_freq, raise_freq, fold_freq)
        """
        try:
            with open(output_path, 'r') as f:
                data = json.load(f)

            actions = data.get('actions', [])

            # The actual hand strategies are nested under data['strategy']['strategy']
            strategy_node = data.get('strategy', {})
            strategy = strategy_node.get('strategy', {}) if isinstance(strategy_node, dict) else {}

            if not actions or not strategy:
                return {}

            # Initialize frequency accumulators
            freq_totals = {
                'check': 0.0,
                'bet': 0.0,
                'raise': 0.0,
                'fold': 0.0,
                'call': 0.0
            }

            # For each hand combo, aggregate frequencies by action type
            num_hands = 0
            for hand_combo, frequencies in strategy.items():
                # Skip non-list entries
                if not isinstance(frequencies, list):
                    continue

                if len(frequencies) != len(actions):
                    continue

                # Count valid hand combos
                num_hands += 1

                for i, action in enumerate(actions):
                    freq = frequencies[i]

                    # Ensure freq is numeric
                    if not isinstance(freq, (int, float)):
                        continue

                    action_upper = action.upper()

                    if 'CHECK' in action_upper:
                        freq_totals['check'] += freq
                    elif 'BET' in action_upper:
                        freq_totals['bet'] += freq
                    elif 'RAISE' in action_upper:
                        freq_totals['raise'] += freq
                    elif 'FOLD' in action_upper:
                        freq_totals['fold'] += freq
                    elif 'CALL' in action_upper:
                        freq_totals['call'] += freq

            # Calculate averages (convert to percentage 0-100)
            if num_hands > 0:
                return {
                    'gto_check_frequency': round((freq_totals['check'] / num_hands) * 100, 2),
                    'gto_bet_frequency': round((freq_totals['bet'] / num_hands) * 100, 2),
                    'gto_raise_frequency': round((freq_totals['raise'] / num_hands) * 100, 2),
                    'gto_fold_frequency': round((freq_totals['fold'] / num_hands) * 100, 2),
                    'gto_call_frequency': round((freq_totals['call'] / num_hands) * 100, 2)
                }

            return {}

        except Exception as e:
            print(f"    Warning: Failed to extract frequencies from {output_path.name}: {e}")
            return {}

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

            # Extract GTO frequencies from solver output
            frequencies = self.extract_gto_frequencies(output_path)

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
                'imported_at': datetime.now(),
                # Add GTO frequencies
                **frequencies
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

                # Insert into database if connected
                if self.db_conn and not dry_run:
                    if self.insert_solution(solution):
                        print(f"    ✓ Saved to database")
                    else:
                        print(f"    ✗ Failed to save to database")
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
    import argparse

    # Parse arguments
    parser = argparse.ArgumentParser(description='Import GTO solutions to database')
    parser.add_argument('--dry-run', action='store_true', help='Process but do not write to database')
    parser.add_argument('--db-url', type=str, help='Database URL (or use DATABASE_URL env var)')
    args = parser.parse_args()

    # Get database URL
    db_url = args.db_url or os.environ.get('DATABASE_URL')

    # Paths
    solver_dir = Path("/root/Documents/Ploit/solver")
    config_dir = solver_dir / "configs_comprehensive"
    output_dir = solver_dir / "outputs_comprehensive"

    # Create importer
    importer = GTOSolutionImporter(
        solver_dir=str(solver_dir),
        config_dir=str(config_dir),
        output_dir=str(output_dir),
        db_url=db_url
    )

    # Connect to database if not dry run
    if not args.dry_run and db_url:
        if not importer.connect_db():
            print("Failed to connect to database. Exiting.")
            return

    # Run import
    results = importer.run_import(dry_run=args.dry_run)

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

    # Close database connection
    importer.close_db()


if __name__ == "__main__":
    main()
