#!/usr/bin/env python3
"""
Generate position-specific GTO scenarios.
Creates scenarios for specific table positions (UTG, MP, CO, BTN, SB, BB).
"""

import os
from pathlib import Path

# Output directory
OUTPUT_DIR = Path("configs_positions")
OUTPUT_DIR.mkdir(exist_ok=True)

def create_config(scenario_num, name, pot, stack, board, range_ip, range_oop, ip_pos, oop_pos):
    """Create a TexasSolver configuration file with position info."""

    config = f"""set_pot {pot}
set_effective_stack {stack}
set_board {board}
set_range_ip {range_ip}
set_range_oop {range_oop}
set_bet_sizes oop,flop,bet,33,50,75,100
set_bet_sizes oop,flop,raise,100
set_bet_sizes oop,flop,allin
set_bet_sizes ip,flop,bet,33,50,75,100
set_bet_sizes ip,flop,raise,100
set_bet_sizes ip,flop,allin
set_allin_threshold 0.67
build_tree
set_thread_num 8
set_accuracy 0.5
set_max_iteration 1000
set_print_interval 100
set_use_isomorphism 1
start_solve
set_dump_rounds 2
dump_result /root/Documents/Ploit/solver/outputs_positions/{scenario_num:03d}_{name}.json
"""

    filename = OUTPUT_DIR / f"{scenario_num:03d}_{name}.txt"
    with open(filename, 'w') as f:
        f.write(config)

    print(f"  ✓ {scenario_num:03d}_{name} ({ip_pos} vs {oop_pos})")
    return filename

# ============================================
# POSITION-SPECIFIC RANGES
# ============================================

POSITION_RANGES = {
    # Opening ranges
    "UTG_open": "AA,KK,QQ,JJ,TT,99:0.5,88:0.25,AK,AQs,AJs,ATs,A5s:0.25,KQs,KJs:0.75,QJs,JTs",

    "MP_open": "AA,KK,QQ,JJ,TT,99,88,77:0.5,AK,AQs,AQo:0.75,AJs,AJo:0.5,ATs,A9s:0.5,A5s,A4s:0.5,KQs,KQo:0.5,KJs,KTs:0.75,QJs,QTs:0.5,JTs,T9s:0.5",

    "CO_open": "AA,KK,QQ,JJ,TT,99,88,77,66,55:0.75,AK,AQs,AQo,AJs,AJo,ATs,ATo:0.75,A9s,A8s:0.5,A7s:0.5,A5s,A4s,A3s:0.5,A2s:0.5,KQs,KQo,KJs,KJo:0.75,KTs,QJs,QTs,JTs,J9s:0.5,T9s,98s,87s:0.5,76s:0.5",

    "BTN_open": "AA,KK,QQ,JJ,TT,99,88,77,66,55,44:0.75,33:0.5,22:0.5,AK,AQs,AQo,AJs,AJo,ATs,ATo,A9s,A9o:0.5,A8s,A7s,A6s,A5s,A4s,A3s,A2s,KQs,KQo,KJs,KJo,KTs,KTo,K9s,K8s:0.5,K7s:0.5,QJs,QJo,QTs,Q9s,JTs,JTo,J9s,J8s:0.5,T9s,T8s,98s,97s:0.5,87s,86s:0.5,76s,75s:0.5,65s:0.5,54s:0.5",

    # Defense ranges vs positions
    "BB_vs_BTN": "AA,KK,QQ,JJ,TT,99,88,77,66,55,44,33,22,AK,AQs,AQo,AJs,AJo,ATs,ATo,A9s,A9o,A8s,A8o:0.75,A7s,A7o:0.5,A6s,A6o:0.5,A5s,A5o:0.75,A4s,A4o:0.75,A3s,A3o:0.5,A2s,A2o:0.5,KQs,KQo,KJs,KJo,KTs,KTo,K9s,K9o:0.75,K8s,K8o:0.5,K7s,K6s:0.75,K5s:0.5,K4s:0.5,K3s:0.5,K2s:0.5,QJs,QJo,QTs,QTo,Q9s,Q9o:0.5,Q8s,Q7s:0.5,JTs,JTo,J9s,J9o:0.75,J8s,J7s:0.5,T9s,T9o:0.75,T8s,T7s,98s,98o:0.75,97s,87s,87o:0.75,86s,76s,76o:0.5,75s,65s,65o:0.5,64s,54s,54o:0.5,53s:0.5",

    "BB_vs_CO": "AA,KK,QQ,JJ,TT,99,88,77,66,55,44:0.75,33:0.5,22:0.5,AK,AQs,AQo:0.75,AJs,AJo:0.75,ATs,ATo:0.5,A9s,A8s,A7s,A6s,A5s,A4s,A3s,A2s,KQs,KQo:0.75,KJs,KJo:0.75,KTs,KTo:0.5,K9s,K8s:0.5,K7s:0.5,QJs,QJo:0.75,QTs,Q9s,JTs,JTo:0.75,J9s,T9s,T8s,98s,87s,76s,65s,54s",

    "BB_vs_MP": "AA,KK,QQ,JJ,TT,99,88,77,66:0.75,55:0.75,44:0.5,AK,AQs,AQo:0.5,AJs,AJo:0.5,ATs,A9s,A8s,A7s,A6s,A5s,A4s,A3s,A2s,KQs,KQo:0.5,KJs,KTs,QJs,QTs,JTs,T9s,98s,87s,76s:0.5,65s:0.5",

    "BB_vs_UTG": "AA,KK,QQ,JJ,TT,99,88:0.75,77:0.5,66:0.5,55:0.5,AK,AQs,AJs,ATs,A9s:0.5,A5s,A4s:0.5,KQs,KJs,QJs,JTs,T9s:0.5",

    "SB_vs_BTN": "AA,KK,QQ,JJ,TT,99,88,77,66,55,44:0.5,33:0.5,22:0.25,AK,AQs,AQo:0.75,AJs,AJo:0.5,ATs,ATo:0.5,A9s,A8s,A7s,A6s,A5s,A4s,A3s,A2s,KQs,KQo:0.75,KJs,KJo:0.5,KTs,K9s,K8s:0.5,K7s:0.5,QJs,QJo:0.5,QTs,Q9s,JTs,JTo:0.5,J9s,T9s,T8s,98s,87s,76s,65s:0.5,54s:0.5",
}

# ============================================
# GENERATE SCENARIOS
# ============================================

scenario_num = 1
scenarios = []

print("Generating position-specific GTO scenarios...")
print("=" * 80)

# Common board runouts
BOARDS = {
    "Ace_high_dry": [
        ("As,8h,3c", "A83r"),
        ("Ad,9s,4h", "A94r"),
        ("Ac,6h,2s", "A62r"),
    ],
    "King_high_dry": [
        ("Kh,9c,4d", "K94r"),
        ("Ks,Tc,3h", "KT3r"),
        ("Kd,6s,2h", "K62r"),
    ],
    "Connected": [
        ("Ts,9h,8d", "T98r"),
        ("9c,7h,6s", "976r"),
        ("8h,7s,6d", "876r"),
    ],
}

# ============================================
# 1. BTN vs BB (Most important)
# ============================================
print("\n[1/6] BTN vs BB scenarios...")
for board_type, boards in BOARDS.items():
    for board, name in boards[:1]:  # One per category
        create_config(
            scenario_num,
            f"BTN_vs_BB_{name}_cbet",
            5.5, 97.5, board,
            POSITION_RANGES["BTN_open"],
            POSITION_RANGES["BB_vs_BTN"],
            "BTN", "BB"
        )
        scenario_num += 1

# ============================================
# 2. CO vs BB
# ============================================
print("\n[2/6] CO vs BB scenarios...")
for board_type, boards in BOARDS.items():
    for board, name in boards[:1]:
        create_config(
            scenario_num,
            f"CO_vs_BB_{name}_cbet",
            5.5, 97.5, board,
            POSITION_RANGES["CO_open"],
            POSITION_RANGES["BB_vs_CO"],
            "CO", "BB"
        )
        scenario_num += 1

# ============================================
# 3. CO vs BTN (cold call)
# ============================================
print("\n[3/6] CO vs BTN scenarios...")
for board_type, boards in BOARDS.items():
    for board, name in boards[:1]:
        create_config(
            scenario_num,
            f"CO_vs_BTN_{name}_cbet",
            5.5, 97.5, board,
            POSITION_RANGES["CO_open"],
            POSITION_RANGES["BTN_open"],  # BTN cold called CO open
            "CO", "BTN"
        )
        scenario_num += 1

# ============================================
# 4. MP vs BB
# ============================================
print("\n[4/6] MP vs BB scenarios...")
for board, name in BOARDS["Ace_high_dry"][:1]:
    create_config(
        scenario_num,
        f"MP_vs_BB_{name}_cbet",
        5.5, 97.5, board,
        POSITION_RANGES["MP_open"],
        POSITION_RANGES["BB_vs_MP"],
        "MP", "BB"
    )
    scenario_num += 1

# ============================================
# 5. UTG vs BB
# ============================================
print("\n[5/6] UTG vs BB scenarios...")
for board, name in BOARDS["Ace_high_dry"][:1]:
    create_config(
        scenario_num,
        f"UTG_vs_BB_{name}_cbet",
        5.5, 97.5, board,
        POSITION_RANGES["UTG_open"],
        POSITION_RANGES["BB_vs_UTG"],
        "UTG", "BB"
    )
    scenario_num += 1

# ============================================
# 6. BTN vs SB
# ============================================
print("\n[6/6] BTN vs SB scenarios...")
for board, name in BOARDS["Ace_high_dry"][:1]:
    create_config(
        scenario_num,
        f"BTN_vs_SB_{name}_cbet",
        5.5, 97.5, board,
        POSITION_RANGES["BTN_open"],
        POSITION_RANGES["SB_vs_BTN"],
        "BTN", "SB"
    )
    scenario_num += 1

print("\n" + "=" * 80)
print(f"✓ Generated {scenario_num - 1} position-specific scenarios")
print(f"✓ Config files saved to: {OUTPUT_DIR}")
print(f"\nNext steps:")
print(f"  1. Create outputs directory: mkdir -p outputs_positions")
print(f"  2. Run solver: ./TexasSolver-v0.2.0-Linux/console_solver configs_positions/001_BTN_vs_BB_A83r_cbet.txt")
print(f"  3. Or run all in parallel with a script")
