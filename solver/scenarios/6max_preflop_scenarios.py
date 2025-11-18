"""
6-Max Preflop GTO Scenario Matrix
Generates comprehensive preflop scenarios for 100BB 6-max cash games.
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class PreflopScenario:
    """Represents a single preflop scenario"""
    scenario_id: int
    name: str
    description: str
    positions: List[str]  # Players involved
    action_sequence: str  # e.g., "RFI", "Open_3bet", "Open_Call_Squeeze"
    stack_bb: int = 100


# 6-max positions (seat order from dealer button clockwise)
POSITIONS_6MAX = ["BTN", "SB", "BB", "UTG", "MP", "CO"]

# Opening positions (everyone except SB/BB can open)
OPENING_POSITIONS = ["UTG", "MP", "CO", "BTN"]
BLIND_POSITIONS = ["SB", "BB"]


def generate_rfi_scenarios() -> List[PreflopScenario]:
    """
    Generate Raise First In (RFI) scenarios.
    Each position's opening range when action folds to them.
    """
    scenarios = []
    scenario_id = 1

    # RFI from each position
    for pos in OPENING_POSITIONS:
        scenarios.append(PreflopScenario(
            scenario_id=scenario_id,
            name=f"RFI_{pos}",
            description=f"{pos} raise first in, folds to {pos}",
            positions=[pos],
            action_sequence="RFI"
        ))
        scenario_id += 1

    # SB scenarios (special cases)
    scenarios.append(PreflopScenario(
        scenario_id=scenario_id,
        name="SB_RFI",
        description="SB raise first in (open raise) vs BB",
        positions=["SB", "BB"],
        action_sequence="SB_RFI"
    ))
    scenario_id += 1

    scenarios.append(PreflopScenario(
        scenario_id=scenario_id,
        name="SB_complete",
        description="SB completes (limps) vs BB",
        positions=["SB", "BB"],
        action_sequence="SB_COMPLETE"
    ))
    scenario_id += 1

    # BB RFI vs SB limp
    scenarios.append(PreflopScenario(
        scenario_id=scenario_id,
        name="BB_vs_SB_limp",
        description="SB limps, BB can check or raise",
        positions=["SB", "BB"],
        action_sequence="SB_LIMP_BB_DECISION"
    ))
    scenario_id += 1

    return scenarios


def generate_3bet_scenarios() -> List[PreflopScenario]:
    """
    Generate 3bet scenarios.
    For each position that opens, positions behind can 3bet.
    """
    scenarios = []
    scenario_id = 100  # Start at 100 to separate from RFI

    for opener in OPENING_POSITIONS:
        # Get positions that act after opener
        opener_idx = POSITIONS_6MAX.index(opener)

        # Positions that can 3bet (anyone acting after opener)
        for i in range(len(POSITIONS_6MAX)):
            threebettor_idx = (opener_idx + 1 + i) % len(POSITIONS_6MAX)
            threebettor = POSITIONS_6MAX[threebettor_idx]

            # Skip if we've circled back to opener
            if threebettor == opener:
                continue

            # Skip if threebettor would have acted before opener
            # (They would have folded already in a RFI scenario)
            if threebettor in OPENING_POSITIONS:
                if OPENING_POSITIONS.index(threebettor) < OPENING_POSITIONS.index(opener):
                    continue

            scenarios.append(PreflopScenario(
                scenario_id=scenario_id,
                name=f"{opener}_open_{threebettor}_3bet",
                description=f"{opener} opens, {threebettor} 3bets",
                positions=[opener, threebettor],
                action_sequence="OPEN_3BET"
            ))
            scenario_id += 1

    return scenarios


def generate_4bet_scenarios() -> List[PreflopScenario]:
    """
    Generate 4bet scenarios.
    After a 3bet, original raiser can 4bet.
    """
    scenarios = []
    scenario_id = 200  # Start at 200

    # Build from 3bet scenarios
    threbet_scenarios = generate_3bet_scenarios()

    for s in threbet_scenarios:
        opener = s.positions[0]
        threebettor = s.positions[1]

        scenarios.append(PreflopScenario(
            scenario_id=scenario_id,
            name=f"{opener}_open_{threebettor}_3bet_{opener}_4bet",
            description=f"{opener} opens, {threebettor} 3bets, {opener} 4bets",
            positions=[opener, threebettor],
            action_sequence="OPEN_3BET_4BET"
        ))
        scenario_id += 1

    return scenarios


def generate_cold_call_scenarios() -> List[PreflopScenario]:
    """
    Generate cold call scenarios.
    After an open, someone cold calls (not 3bets).
    """
    scenarios = []
    scenario_id = 300  # Start at 300

    for opener in OPENING_POSITIONS:
        opener_idx = POSITIONS_6MAX.index(opener)

        # Positions that can cold call
        for i in range(len(POSITIONS_6MAX)):
            caller_idx = (opener_idx + 1 + i) % len(POSITIONS_6MAX)
            caller = POSITIONS_6MAX[caller_idx]

            if caller == opener:
                continue

            # Skip if caller would have acted before opener
            if caller in OPENING_POSITIONS:
                if OPENING_POSITIONS.index(caller) < OPENING_POSITIONS.index(opener):
                    continue

            scenarios.append(PreflopScenario(
                scenario_id=scenario_id,
                name=f"{opener}_open_{caller}_call",
                description=f"{opener} opens, {caller} cold calls",
                positions=[opener, caller],
                action_sequence="OPEN_CALL"
            ))
            scenario_id += 1

    return scenarios


def generate_squeeze_scenarios() -> List[PreflopScenario]:
    """
    Generate squeeze scenarios.
    Open -> Cold call -> 3bet (squeeze) from third player.
    """
    scenarios = []
    scenario_id = 400  # Start at 400

    # Simplified: Most common squeeze spots
    common_squeezes = [
        ("UTG", "MP", "CO"),
        ("UTG", "MP", "BTN"),
        ("UTG", "CO", "BTN"),
        ("MP", "CO", "BTN"),
        ("CO", "BTN", "SB"),
        ("CO", "BTN", "BB"),
        ("BTN", "SB", "BB"),
    ]

    for opener, caller, squeezer in common_squeezes:
        scenarios.append(PreflopScenario(
            scenario_id=scenario_id,
            name=f"{opener}_open_{caller}_call_{squeezer}_squeeze",
            description=f"{opener} opens, {caller} calls, {squeezer} squeezes",
            positions=[opener, caller, squeezer],
            action_sequence="OPEN_CALL_SQUEEZE"
        ))
        scenario_id += 1

    return scenarios


def generate_blind_defense_scenarios() -> List[PreflopScenario]:
    """
    Generate blind defense scenarios.
    Specifically SB and BB defending vs opens.
    """
    scenarios = []
    scenario_id = 500  # Start at 500

    for opener in OPENING_POSITIONS:
        # BB vs open
        scenarios.append(PreflopScenario(
            scenario_id=scenario_id,
            name=f"{opener}_open_BB_defend",
            description=f"{opener} opens, BB defends (call/3bet range)",
            positions=[opener, "BB"],
            action_sequence="OPEN_BB_DEFEND"
        ))
        scenario_id += 1

        # SB vs open (when BB folds)
        scenarios.append(PreflopScenario(
            scenario_id=scenario_id,
            name=f"{opener}_open_SB_defend",
            description=f"{opener} opens, SB defends (call/3bet range)",
            positions=[opener, "SB"],
            action_sequence="OPEN_SB_DEFEND"
        ))
        scenario_id += 1

    return scenarios


def generate_all_scenarios() -> List[PreflopScenario]:
    """Generate all preflop scenarios"""
    all_scenarios = []

    all_scenarios.extend(generate_rfi_scenarios())
    all_scenarios.extend(generate_3bet_scenarios())
    all_scenarios.extend(generate_4bet_scenarios())
    all_scenarios.extend(generate_cold_call_scenarios())
    all_scenarios.extend(generate_squeeze_scenarios())
    all_scenarios.extend(generate_blind_defense_scenarios())

    return all_scenarios


def print_scenario_summary():
    """Print summary of all scenarios"""
    rfi = generate_rfi_scenarios()
    threbet = generate_3bet_scenarios()
    fourbet = generate_4bet_scenarios()
    cold_call = generate_cold_call_scenarios()
    squeeze = generate_squeeze_scenarios()
    blind_def = generate_blind_defense_scenarios()

    print("=" * 60)
    print("6-Max Preflop GTO Scenario Matrix (100BB)")
    print("=" * 60)
    print(f"RFI scenarios:           {len(rfi):4d}")
    print(f"3bet scenarios:          {len(threbet):4d}")
    print(f"4bet scenarios:          {len(fourbet):4d}")
    print(f"Cold call scenarios:     {len(cold_call):4d}")
    print(f"Squeeze scenarios:       {len(squeeze):4d}")
    print(f"Blind defense scenarios: {len(blind_def):4d}")
    print("-" * 60)
    print(f"TOTAL SCENARIOS:         {sum([len(rfi), len(threbet), len(fourbet), len(cold_call), len(squeeze), len(blind_def)]):4d}")
    print("=" * 60)


if __name__ == "__main__":
    print_scenario_summary()

    print("\n\nSample scenarios:")
    all_sc = generate_all_scenarios()
    for s in all_sc[:10]:
        print(f"{s.scenario_id:3d}. {s.name:40s} - {s.description}")
