#!/usr/bin/env python3
"""
Generate comprehensive GTO scenario configurations.
Creates ~85 additional scenarios to complement the 15 MVP scenarios.
Total: ~100 scenarios covering all important board textures and game states.
"""

import os
from pathlib import Path

# Output directory
OUTPUT_DIR = Path("configs_comprehensive")
OUTPUT_DIR.mkdir(exist_ok=True)

# Base configuration template
def create_config(scenario_num, name, pot, stack, board, range_ip, range_oop, game_type="SRP"):
    """Create a TexasSolver configuration file."""

    # Adjust bet sizes based on game type
    if game_type == "3BET":
        bet_sizes_small = "33,50"
        bet_sizes_large = "75,100"
    elif game_type == "4BET":
        bet_sizes_small = "33"
        bet_sizes_large = "75,100"
    else:  # SRP
        bet_sizes_small = "33,50"
        bet_sizes_large = "75,100"

    config = f"""set_pot {pot}
set_effective_stack {stack}
set_board {board}
set_range_ip {range_ip}
set_range_oop {range_oop}
set_bet_sizes oop,flop,bet,{bet_sizes_small},{bet_sizes_large}
set_bet_sizes oop,flop,raise,100
set_bet_sizes oop,flop,allin
set_bet_sizes ip,flop,bet,{bet_sizes_small},{bet_sizes_large}
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
dump_result /root/Documents/Ploit/solver/outputs_comprehensive/{scenario_num:03d}_{name}.json
"""

    filename = OUTPUT_DIR / f"{scenario_num:03d}_{name}.txt"
    with open(filename, 'w') as f:
        f.write(config)

    return filename

# Starting from scenario 16 (after the 15 MVP scenarios)
scenario_num = 16

# Define ranges for different scenarios
RANGES = {
    "srp_ip_wide": "AA,KK:0.5,QQ,JJ,TT,99,88,77,66,55,AK,AQs,AQo:0.75,AJs,AJo:0.75,ATs,A9s:0.5,A8s:0.5,A7s:0.5,A6s:0.5,A5s:0.75,A4s:0.75,A3s:0.5,A2s:0.5,KQs,KQo:0.75,KJs,KJo:0.5,KTs,K9s:0.5,QJs,QTs,Q9s:0.5,JTs,J9s:0.5,T9s,98s,87s,76s:0.5,65s:0.5",
    "srp_oop_wide": "KK:0.75,QQ,JJ,TT,99,88,77:0.75,66,55,44,33:0.5,22:0.5,AK:0.25,AQs,AQo:0.5,AJs,AJo:0.5,ATs,ATo:0.75,A9s,A8s,A7s,A6s,A5s,A4s,A3s,A2s,KQ:0.75,KJs,KJo:0.75,KTs,KTo:0.75,K9s,K8s,K7s:0.75,K6s:0.5,K5s:0.5,K4s:0.5,K3s:0.5,K2s:0.5,QJs,QTs,Q9s,Q8s,JTs,J9s,J8s,T9s,T8s,98s,97s,87s,86s,76s,75s,65s,64s,54s",
    "3bet_ip": "AA,KK,QQ:0.75,JJ:0.5,TT:0.25,AK,AQs,AQ:0.5,AJs,AJ:0.25,ATs:0.5,KQs,KQ:0.25,KJs:0.5,QJs:0.25,JTs:0.25,A5s:0.25,A4s:0.25",
    "3bet_oop": "AA,KK,QQ,JJ,TT,99:0.5,88:0.25,AK,AQs,AQ:0.75,AJs,AJ:0.5,ATs,AT:0.25,A5s:0.5,A4s:0.5,KQs,KQ:0.5,KJs:0.25,QJs:0.25",
    "4bet_ip": "AA,KK,QQ:0.5,JJ:0.25,AK,AQs:0.25,A5s:0.25,A4s:0.25",
    "4bet_oop": "AA,KK,QQ,JJ:0.5,AK,AQs:0.5"
}

scenarios = []

print("Generating comprehensive GTO scenario configurations...")
print("=" * 60)

# ============================================
# 1. DRY ACE-HIGH BOARDS (10 scenarios)
# ============================================
print("\n[1/10] Dry Ace-high boards...")

boards_ace = [
    ("Ah,7c,2d", "A72r"),
    ("As,8h,3c", "A83r"),
    ("Ad,9s,4h", "A94r"),
    ("Ac,6h,2s", "A62r"),
    ("Ah,Tc,3d", "AT3r"),
]

for board, name in boards_ace:
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # SRP IP checkback
    create_config(scenario_num, f"SRP_{name}_check", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

# ============================================
# 2. DRY KING-HIGH BOARDS (8 scenarios)
# ============================================
print("[2/10] Dry King-high boards...")

boards_king = [
    ("Kh,9c,4d", "K94r"),
    ("Ks,Tc,3h", "KT3r"),
    ("Kd,6s,2h", "K62r"),
    ("Kc,Jh,5s", "KJ5r"),
]

for board, name in boards_king:
    # SRP OOP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet_oop", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # 3-bet pot IP c-bet
    create_config(scenario_num, f"3BET_{name}_cbet", 18.5, 90.5, board,
                  RANGES["3bet_ip"], RANGES["3bet_oop"], "3BET")
    scenario_num += 1

# ============================================
# 3. BROADWAY BOARDS (8 scenarios)
# ============================================
print("[3/10] Broadway boards...")

boards_broadway = [
    ("Ah,Kd,3s", "AK3r"),  # Already have this
    ("Kh,Qs,7d", "KQ7r"),
    ("Qd,Js,5h", "QJ5r"),
    ("Jc,Th,4s", "JT4r"),
]

for board, name in boards_broadway[1:]:  # Skip AK3r (already have it)
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # 3-bet pot OOP c-bet
    create_config(scenario_num, f"3BET_{name}_cbet_oop", 18.5, 90.5, board,
                  RANGES["3bet_ip"], RANGES["3bet_oop"], "3BET")
    scenario_num += 1

# ============================================
# 4. MIDDLE CONNECTED BOARDS (10 scenarios)
# ============================================
print("[4/10] Middle connected boards...")

boards_middle = [
    ("Ts,9h,8d", "T98r"),
    ("9c,7h,6s", "976r"),
    ("8h,7s,6d", "876r"),
    ("7d,6c,5h", "765r"),
    ("Jh,Ts,9d", "JT9r"),
]

for board, name in boards_middle:
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # SRP OOP check-call
    create_config(scenario_num, f"SRP_{name}_check_oop", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

# ============================================
# 5. LOW BOARDS (8 scenarios)
# ============================================
print("[5/10] Low boards...")

boards_low = [
    ("5h,4d,3c", "543r"),
    ("6s,5h,3d", "653r"),
    ("7c,4h,2s", "742r"),
    ("8d,5c,2h", "852r"),
]

for board, name in boards_low:
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # 3-bet pot IP c-bet
    create_config(scenario_num, f"3BET_{name}_cbet", 18.5, 90.5, board,
                  RANGES["3bet_ip"], RANGES["3bet_oop"], "3BET")
    scenario_num += 1

# ============================================
# 6. PAIRED HIGH BOARDS (10 scenarios)
# ============================================
print("[6/10] Paired high boards...")

boards_paired_high = [
    ("Kh,Kc,7d", "KK7r"),
    ("Qd,Qs,9h", "QQ9r"),
    ("Jc,Jh,6s", "JJ6r"),
    ("Th,Ts,4d", "TT4r"),
    ("9h,9c,5s", "995r"),
]

for board, name in boards_paired_high:
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # 3-bet pot IP c-bet
    create_config(scenario_num, f"3BET_{name}_cbet", 18.5, 90.5, board,
                  RANGES["3bet_ip"], RANGES["3bet_oop"], "3BET")
    scenario_num += 1

# ============================================
# 7. PAIRED LOW BOARDS (6 scenarios)
# ============================================
print("[7/10] Paired low boards...")

boards_paired_low = [
    ("7h,7d,3c", "773r"),
    ("6s,6c,2h", "662r"),
    ("5d,5h,Ah", "55Ar"),
]

for board, name in boards_paired_low:
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # SRP OOP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet_oop", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

# ============================================
# 8. MONOTONE BOARDS (8 scenarios)
# ============================================
print("[8/10] Monotone boards...")

boards_monotone = [
    ("Ah,Kh,3h", "AK3hhh"),
    ("Qs,Ts,5s", "QT5sss"),
    ("9d,7d,6d", "976ddd"),
    ("8c,5c,2c", "852ccc"),
]

for board, name in boards_monotone:
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # 3-bet pot OOP c-bet
    create_config(scenario_num, f"3BET_{name}_cbet_oop", 18.5, 90.5, board,
                  RANGES["3bet_ip"], RANGES["3bet_oop"], "3BET")
    scenario_num += 1

# ============================================
# 9. TWO-TONE WET BOARDS (8 scenarios)
# ============================================
print("[9/10] Two-tone wet boards...")

boards_twotone = [
    ("Ah,Th,9s", "AT9hh"),
    ("Kd,Jd,8c", "KJ8dd"),
    ("Qh,9h,7s", "Q97hh"),
    ("Ts,8s,6c", "T86ss"),
]

for board, name in boards_twotone:
    # SRP IP c-bet
    create_config(scenario_num, f"SRP_{name}_cbet", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

    # SRP IP checkback
    create_config(scenario_num, f"SRP_{name}_check", 5.5, 97.5, board,
                  RANGES["srp_ip_wide"], RANGES["srp_oop_wide"])
    scenario_num += 1

# ============================================
# 10. 4-BET POTS (5 scenarios)
# ============================================
print("[10/10] 4-bet pot scenarios...")

boards_4bet = [
    ("Ah,Ks,7d", "AK7r"),
    ("Qh,Jd,3s", "QJ3r"),
    ("Ts,9h,4c", "T94r"),
    ("8d,7h,2s", "872r"),
    ("Kh,6s,6d", "K66r"),
]

for board, name in boards_4bet:
    create_config(scenario_num, f"4BET_{name}_cbet", 42.5, 72.5, board,
                  RANGES["4bet_ip"], RANGES["4bet_oop"], "4BET")
    scenario_num += 1

print("\n" + "=" * 60)
print(f"✅ Generated {scenario_num - 16} new scenario configurations!")
print(f"📁 Total scenarios: 15 (MVP) + {scenario_num - 16} (new) = {scenario_num - 1} total")
print(f"💾 Config files saved to: {OUTPUT_DIR}/")
print("\nReady to solve!")
