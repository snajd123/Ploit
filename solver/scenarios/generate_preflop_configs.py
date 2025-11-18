"""
Generate TexasSolver configuration files for 6-max preflop scenarios.
Creates .txt config files that TexasSolver can execute.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

# Import the scenario generator module
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("scenarios", "6max_preflop_scenarios.py")
scenarios_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scenarios_module)

generate_all_scenarios = scenarios_module.generate_all_scenarios
PreflopScenario = scenarios_module.PreflopScenario


# Standard preflop ranges (simplified for initial solving)
# These are starting ranges - GTO solver will adjust them

PREFLOP_RANGES = {
    "UTG": "88+,A9s+,KTs+,QTs+,JTs,ATo+,KQo",
    "MP": "77+,A7s+,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo",
    "CO": "66+,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,65s,A9o+,KTo+,QTo+,JTo",
    "BTN": "22+,A2s+,K2s+,Q6s+,J7s+,T7s+,97s+,86s+,75s+,64s+,54s,A2o+,K9o+,Q9o+,J9o+,T9o",
    "SB": "22+,A2s+,K2s+,Q2s+,J6s+,T6s+,96s+,85s+,75s+,64s+,54s,A2o+,K8o+,Q9o+,J9o+,T9o",
    "BB": "22+,A2s+,K2s+,Q2s+,J2s+,T2s+,92s+,82s+,72s+,62s+,52s+,42s+,32s,A2o+,K2o+,Q2o+,J7o+,T7o+,97o+,87o,76o"
}

# Defending ranges (tighter than opening)
DEFEND_RANGES = {
    "vs_UTG": "99+,ATs+,KQs,AJo+,KQo",
    "vs_MP": "88+,A9s+,KTs+,QJs,ATo+,KJo+",
    "vs_CO": "77+,A7s+,K9s+,Q9s+,J9s+,T9s,A9o+,KTo+,QJo",
    "vs_BTN": "66+,A5s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A8o+,K9o+,Q9o+,JTo",
    "vs_SB": "55+,A3s+,K7s+,Q8s+,J8s+,T8s+,97s+,87s,76s,A7o+,K9o+,Q9o+,JTo",
}

# 3bet ranges
THREBET_RANGES = {
    "vs_UTG": "QQ+,AKs,AKo",
    "vs_MP": "JJ+,AQs+,AKo",
    "vs_CO": "99+,A9s+,KQs,AJo+,KQo",
    "vs_BTN": "77+,A7s+,K9s+,Q9s+,J9s+,T9s,A9o+,KTo+,QJo",
    "vs_SB": "66+,A5s+,K8s+,Q9s+,J8s+,T8s+,97s+,A8o+,K9o+,Q9o+",
}


def get_pot_size(scenario: PreflopScenario) -> float:
    """Calculate pot size based on action sequence"""
    if scenario.action_sequence == "RFI":
        return 1.5  # SB + BB
    elif scenario.action_sequence in ["SB_RFI", "SB_COMPLETE", "SB_LIMP_BB_DECISION"]:
        return 1.5  # SB + BB
    elif scenario.action_sequence == "OPEN_CALL":
        return 6.0  # Open 2.5BB + caller 2.5BB + blinds 1.5BB
    elif scenario.action_sequence == "OPEN_3BET":
        return 12.0  # Open 2.5BB + 3bet 9BB + blinds
    elif scenario.action_sequence == "OPEN_3BET_4BET":
        return 30.0  # After 4bet
    elif scenario.action_sequence == "OPEN_CALL_SQUEEZE":
        return 15.0  # Open + call + squeeze
    elif scenario.action_sequence.endswith("_DEFEND"):
        return 4.0  # Open + blind
    else:
        return 1.5  # Default


def get_ranges_for_scenario(scenario: PreflopScenario) -> Dict[str, str]:
    """Get appropriate ranges for each position in scenario"""
    ranges = {}

    if scenario.action_sequence == "RFI":
        # Opening range vs unopened pot
        pos = scenario.positions[0]
        ranges[pos] = PREFLOP_RANGES.get(pos, PREFLOP_RANGES["BTN"])

    elif scenario.action_sequence == "SB_RFI":
        ranges["SB"] = PREFLOP_RANGES["SB"]
        ranges["BB"] = DEFEND_RANGES["vs_SB"]

    elif scenario.action_sequence == "OPEN_3BET":
        opener, threebettor = scenario.positions
        ranges[opener] = PREFLOP_RANGES.get(opener, PREFLOP_RANGES["BTN"])
        ranges[threebettor] = THREBET_RANGES.get(f"vs_{opener}", THREBET_RANGES["vs_BTN"])

    elif scenario.action_sequence == "OPEN_CALL":
        opener, caller = scenario.positions
        ranges[opener] = PREFLOP_RANGES.get(opener, PREFLOP_RANGES["BTN"])
        ranges[caller] = DEFEND_RANGES.get(f"vs_{opener}", DEFEND_RANGES["vs_BTN"])

    else:
        # Default: use position's standard range
        for pos in scenario.positions:
            ranges[pos] = PREFLOP_RANGES.get(pos, PREFLOP_RANGES["BTN"])

    return ranges


def generate_config_file(scenario: PreflopScenario, output_dir: str):
    """Generate a single TexasSolver config file for a scenario"""

    pot_size = get_pot_size(scenario)
    stack_size = 100  # 100BB in big blinds
    effective_stack = stack_size - (pot_size / 2)  # Remaining stack

    ranges = get_ranges_for_scenario(scenario)

    # Create config content
    config_lines = []

    # Game setup
    config_lines.append(f"set_pot {pot_size}")
    config_lines.append(f"set_effective_stack {effective_stack}")

    # Set ranges
    # For simplicity, using 2-player ranges (OOP and IP)
    if len(ranges) == 1:
        # Single player (RFI scenario) - need to define vs field
        pos = list(ranges.keys())[0]
        config_lines.append(f"set_range_ip {ranges[pos]}")
        config_lines.append(f"set_range_oop {DEFEND_RANGES['vs_BTN']}")  # Generic defense
    elif len(ranges) == 2:
        # Two player scenario
        pos1, pos2 = ranges.keys()
        config_lines.append(f"set_range_ip {ranges[pos1]}")
        config_lines.append(f"set_range_oop {ranges[pos2]}")
    else:
        # Multi-way - simplify to 2 players for now
        pos1 = list(ranges.keys())[0]
        config_lines.append(f"set_range_ip {ranges[pos1]}")
        config_lines.append(f"set_range_oop {DEFEND_RANGES['vs_BTN']}")
    config_lines.append("set_bet_sizes oop,flop,bet,50,100")
    config_lines.append("set_bet_sizes oop,flop,raise,100")
    config_lines.append("set_bet_sizes oop,flop,allin")
    config_lines.append("set_bet_sizes ip,flop,bet,50,100")
    config_lines.append("set_bet_sizes ip,flop,raise,100")
    config_lines.append("set_bet_sizes ip,flop,allin")
    config_lines.append("set_allin_threshold 0.67")
    config_lines.append("build_tree")
    config_lines.append("set_thread_num 8")
    config_lines.append("set_accuracy 1.0")
    config_lines.append("set_max_iteration 300")
    config_lines.append("set_print_interval 50")
    config_lines.append("set_use_isomorphism 1")
    config_lines.append("start_solve")
    output_path = f"{output_dir}/preflop_outputs/{scenario.name}.json"
    config_lines.append("set_dump_rounds 2")
    config_lines.append(f"dump_result {output_path}")

    # Write config file
    config_filename = f"{output_dir}/preflop_configs/{scenario.scenario_id:03d}_{scenario.name}.txt"
    with open(config_filename, 'w') as f:
        f.write('\n'.join(config_lines))

    return config_filename


def generate_all_configs():
    """Generate all config files"""

    # Setup directories
    base_dir = "/root/Documents/Ploit/solver"
    config_dir = f"{base_dir}/preflop_configs"
    output_dir = f"{base_dir}/preflop_outputs"

    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Generate scenarios
    scenarios = generate_all_scenarios()

    print("=" * 60)
    print(f"Generating TexasSolver configs for {len(scenarios)} scenarios")
    print("=" * 60)

    generated = []
    for scenario in scenarios:
        config_file = generate_config_file(scenario, base_dir)
        generated.append(config_file)
        print(f"✓ {scenario.scenario_id:3d}. {scenario.name:40s}")

    print("=" * 60)
    print(f"Generated {len(generated)} config files")
    print(f"Config dir: {config_dir}")
    print(f"Output dir: {output_dir}")
    print("=" * 60)

    # Generate batch solve script
    generate_batch_script(scenarios, base_dir)


def generate_batch_script(scenarios: List[PreflopScenario], base_dir: str):
    """Generate bash script to solve all scenarios"""

    script_path = f"{base_dir}/solve_all_preflop.sh"

    script_lines = [
        "#!/bin/bash",
        "# Batch solve all 6-max preflop scenarios",
        "",
        "SOLVER_DIR=\"/root/Documents/Ploit/solver/TexasSolver-v0.2.0-Linux\"",
        "CONFIG_DIR=\"/root/Documents/Ploit/solver/preflop_configs\"",
        "LOG_DIR=\"/root/Documents/Ploit/solver/preflop_logs\"",
        "",
        "mkdir -p \"$LOG_DIR\"",
        "",
        "cd \"$SOLVER_DIR\"",
        "",
        f"total={len(scenarios)}",
        "completed=0",
        "failed=0",
        "",
        "echo \"=====================================\"",
        "echo \"6-Max Preflop GTO Batch Solve\"",
        "echo \"Starting at: $(date)\"",
        "echo \"=====================================\"",
        "",
    ]

    for i, scenario in enumerate(scenarios, 1):
        config_file = f"{scenario.scenario_id:03d}_{scenario.name}.txt"
        log_file = f"{scenario.name}.log"

        script_lines.extend([
            f"echo \"\"",
            f"echo \"[{i}/{len(scenarios)}] Solving: {scenario.name}\"",
            f"echo \"Started at: $(date)\"",
            "",
            f"./console_solver --input_file \"$CONFIG_DIR/{config_file}\" --resource_dir ./resources --mode holdem \\",
            f"    > \"$LOG_DIR/{log_file}\" 2>&1",
            "",
            "exit_code=$?",
            "if [ $exit_code -eq 0 ]; then",
            f"    echo \"✓ Completed: {scenario.name}\"",
            "    ((completed++))",
            "else",
            f"    echo \"✗ Failed: {scenario.name} (exit code: $exit_code)\"",
            "    ((failed++))",
            "fi",
            f"echo \"Finished at: $(date)\"",
            "echo \"---\"",
            "",
        ])

    script_lines.extend([
        "echo \"\"",
        "echo \"=====================================\"",
        "echo \"Batch Solve Complete\"",
        "echo \"Completed: $completed/$total\"",
        "echo \"Failed: $failed/$total\"",
        "echo \"Finished at: $(date)\"",
        "echo \"=====================================\"",
    ])

    with open(script_path, 'w') as f:
        f.write('\n'.join(script_lines))

    os.chmod(script_path, 0o755)  # Make executable

    print(f"\n✓ Generated batch solve script: {script_path}")
    print(f"  Run with: {script_path}")


if __name__ == "__main__":
    generate_all_configs()
