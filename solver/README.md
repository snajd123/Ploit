# GTO Solver Configuration - MVP

This directory contains the configuration files and scripts for solving 15 critical poker scenarios using TexasSolver.

## Directory Structure

```
solver/
├── TexasSolver-v0.2.0-Linux/     # Solver binary and resources
│   ├── console_solver              # Main solver executable
│   └── resources/                  # Solver resources (ranges, comparers, etc.)
├── configs/                        # Configuration files for each scenario
│   ├── 01_SRP_Ks7c3d_cbet.txt     # K-high dry board
│   ├── 02_SRP_Ah9s3h_cbet.txt     # A-high monotone
│   ├── 03_SRP_9s8h7d_cbet.txt     # Middle connected
│   ├── 04_SRP_Qc7h2s_cbet.txt     # Q-high dry
│   ├── 05_SRP_Tc9c5h_cbet.txt     # T-high two-tone
│   ├── 06_SRP_6h5h4s_cbet.txt     # Low connected
│   ├── 07_SRP_AhKd3s_cbet.txt     # AK-high board
│   ├── 08_3BET_AhKs9d_cbet.txt    # 3-bet pot c-bet
│   ├── 09_SRP_Ts5s5h_cbet.txt     # Paired board
│   ├── 10_SRP_As5d2c_cbet.txt     # A-low dry
│   ├── 11_SRP_Kh8h3d_cbet.txt     # K-high two-tone
│   ├── 12_SRP_8d8c3s_cbet.txt     # Middle paired
│   ├── 13_SRP_Jh9c8d_cbet.txt     # High connected
│   ├── 14_SRP_Tc6d2h_cbet.txt     # Dry middle
│   └── 15_SRP_7s5s4s_cbet.txt     # Low monotone
├── outputs/                        # JSON output files from solver
├── logs/                           # Solver log files
├── MVP_SCENARIOS.md                # Detailed scenario descriptions
├── run_all_solves.sh               # Run all 15 solves sequentially
├── test_single_solve.sh            # Test a single solve
└── README.md                       # This file
```

## Scenarios Overview

All scenarios are **Single Raised Pot (SRP)** or **3-Bet Pot** flop c-bet decisions with:
- **Pot size:** 5.5bb (SRP) or 20.5bb (3-bet pot)
- **Effective stack:** 97.5bb (SRP) or 90bb (3-bet pot)
- **Position:** Button (IP) vs Big Blind (OOP)
- **Action:** BTN opens preflop, BB calls, flop decision

### Board Texture Categories

1. **Dry High Boards** (01, 04, 07): K-high, Q-high, AK-high
2. **Monotone/Two-tone** (02, 05, 11, 15): Draw-heavy boards
3. **Connected** (03, 06, 13): Straight draw potential
4. **Paired** (09, 12): TT5, 883
5. **Low Boards** (10, 14): A52, T62
6. **3-Bet Pot** (08): AhKs9d in 3-bet pot

## Configuration Format

Each config file uses TexasSolver's command-line format:

```
set_pot 5.5
set_effective_stack 97.5
set_board Ks,7c,3d
set_range_ip AA,KK:0.5,QQ,JJ,...  # Button opening range that called
set_range_oop KK:0.75,QQ,JJ,...    # BB defending range
set_bet_sizes oop,flop,bet,33,50,75
set_bet_sizes ip,flop,bet,33,50,75
build_tree
set_thread_num 4
set_accuracy 0.5
set_max_iteration 1000
start_solve
dump_result /path/to/output.json
```

### Key Parameters

- **Ranges:** Preflop ranges with frequencies (e.g., `AA,KK:0.5` = 50% of AA/KK combos)
- **Bet sizes:** 33%, 50%, 75% pot (postflop sizing)
- **Iterations:** 1000 CFR+ iterations per scenario
- **Accuracy:** 0.5% exploitability target
- **Threads:** 4 threads per solve
- **Duration:** ~10-20 minutes per scenario

## Running the Solver

### Option 1: Test Single Scenario

Test that everything works with one scenario:

```bash
cd /root/Documents/Ploit/solver
./test_single_solve.sh
```

This runs `01_SRP_Ks7c3d_cbet` and should complete in 10-20 minutes.

### Option 2: Run All 15 Scenarios

Run the full MVP batch (2-5 hours total):

```bash
cd /root/Documents/Ploit/solver
./run_all_solves.sh
```

Progress will be printed to console. Log files saved to `logs/` directory.

### Option 3: Run Individual Scenario

```bash
cd /root/Documents/Ploit/solver/TexasSolver-v0.2.0-Linux
./console_solver \
  --input_file /root/Documents/Ploit/solver/configs/01_SRP_Ks7c3d_cbet.txt \
  --resource_dir ./resources \
  --mode normal
```

## Output Format

Each solve produces a JSON file with:

```json
{
  "tree": {
    "node_type": "root",
    "player": 0,
    "actions": ["bet_33", "bet_50", "bet_75", "check"],
    "strategy": [0.25, 0.35, 0.15, 0.25],
    "children": [...]
  },
  "ranges": {
    "player0": {...},
    "player1": {...}
  },
  "evs": {
    "player0": 2.34,
    "player1": -2.34
  }
}
```

## Next Steps

1. ✅ **Create configs** - Done! 15 scenarios configured
2. 🔄 **Run test solve** - Verify setup works
3. ⏳ **Run all solves** - 2-5 hours batch job
4. 🔧 **Parse outputs** - Extract GTO frequencies
5. 💾 **Import to database** - Populate gto_solutions table
6. 🧪 **Test API endpoints** - Verify queries work
7. 🤖 **Integrate with Claude** - Enable GTO analysis
8. 🚀 **Deploy to production** - Release MVP

## Troubleshooting

### Solver crashes or errors
- Check log files in `logs/` directory
- Verify ranges are valid (no syntax errors)
- Ensure output directory exists
- Check disk space (each output ~5-50MB)

### Solve takes too long
- Reduce `set_max_iteration` from 1000 to 500
- Reduce bet sizing options (fewer sizes = faster)
- Increase `set_accuracy` from 0.5 to 1.0 (less precise but faster)

### Output file missing
- Check console output for errors
- Verify `dump_result` path is correct
- Check file permissions on output directory

## Technical Details

### Solver Algorithm
- **Method:** CFR+ (Counterfactual Regret Minimization Plus)
- **Convergence:** Asymptotic convergence to Nash equilibrium
- **Isomorphism:** Enabled (reduces solve time by grouping similar hands)

### Range Construction
- **IP range (Button):** Standard BTN opening range vs BB, filtered for board texture
- **OOP range (BB):** Standard BB defending range vs BTN open, filtered for board
- **Frequencies:** 0.5 = 50% of combinations, used for range mixing

### Bet Sizing Strategy
- **Small:** 33% pot (1/3 pot)
- **Medium:** 50% pot (1/2 pot)
- **Large:** 75% pot (3/4 pot)
- **All-in:** Always available
- **Threshold:** 67% stack = automatic all-in

## Performance Expectations

| Scenario Type | Complexity | Solve Time |
|---------------|-----------|------------|
| Dry boards    | Low       | 10-15 min  |
| Connected     | Medium    | 15-20 min  |
| Monotone      | High      | 20-30 min  |
| 3-bet pot     | High      | 20-30 min  |
| **Total**     | -         | **2-5 hours** |

## Database Integration

Solutions will be imported into the `gto_solutions` table:

```sql
INSERT INTO gto_solutions (
    scenario_name,
    scenario_type,
    board,
    position_oop,
    position_ip,
    pot_size,
    stack_depth,
    gto_bet_frequency,
    gto_check_frequency,
    gto_fold_frequency,
    gto_call_frequency,
    gto_raise_frequency,
    gto_betting_range,
    gto_checking_range,
    ev_oop,
    ev_ip,
    description,
    solver_version,
    solved_at
) VALUES (...);
```

This enables real-time GTO comparisons via the API:
- GET `/api/gto/solution/SRP_Ks7c3d_cbet`
- GET `/api/gto/compare/snajd/SRP_Ks7c3d_cbet`

## References

- **TexasSolver GitHub:** https://github.com/bupticybee/TexasSolver
- **CFR+ Paper:** "Solving Imperfect Information Games Using Decomposition" (Bowling et al.)
- **GTO Poker:** "The Mathematics of Poker" (Chen & Ankenman)
