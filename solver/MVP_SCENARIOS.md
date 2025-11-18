# GTO Solver MVP - 15 Critical Scenarios

This document defines the 15 highest-value poker scenarios to solve for the MVP implementation.

## Selection Criteria
- High frequency in online poker
- Clear exploitable patterns
- Directly comparable to player stats in database
- Reasonable solve time (10-20 minutes each)

---

## PREFLOP SCENARIOS (5)

### 1. BTN_steal_vs_BB
**Description:** Button open-raises facing big blind defense
**Game State:**
- Position: BTN vs BB
- Action: BTN opens 2.5bb, BB to act
- Stack depth: 100bb
- Pot: 3.5bb

**Strategy Focus:** BB's defense frequency (fold/call/3bet)
**Stats Mapped:** `fold_to_steal_pct`, `three_bet_pct`, `call_vs_steal_pct`

---

### 2. BB_vs_BTN_steal_defend
**Description:** Big blind defending vs button steal
**Game State:**
- Position: BB facing BTN open
- Action: BTN opens 2.5bb, BB decides
- Stack depth: 100bb
- Pot: 3.5bb

**Strategy Focus:** BB's calling/3-betting range
**Stats Mapped:** `bb_fold_to_steal_pct`, `bb_3bet_vs_steal_pct`

---

### 3. CO_open_vs_BTN_3bet
**Description:** Cutoff open facing button 3-bet
**Game State:**
- Position: CO vs BTN
- Action: CO opens 2.5bb, BTN 3bets to 9bb, CO to act
- Stack depth: 100bb
- Pot: 10.5bb

**Strategy Focus:** Facing 3-bet (fold/call/4bet)
**Stats Mapped:** `fold_to_three_bet_pct`, `call_three_bet_pct`, `four_bet_pct`

---

### 4. BTN_3bet_vs_CO_open
**Description:** Button 3-betting vs cutoff open
**Game State:**
- Position: BTN vs CO open
- Action: CO opens 2.5bb, BTN decides
- Stack depth: 100bb
- Pot: 4bb

**Strategy Focus:** 3-bet frequency and range
**Stats Mapped:** `three_bet_pct`, `three_bet_vs_open_pct`

---

### 5. SB_squeeze_vs_CO_BTN
**Description:** Small blind squeeze play vs CO open + BTN call
**Game State:**
- Position: SB vs CO + BTN
- Action: CO opens 2.5bb, BTN calls, SB decides
- Stack depth: 100bb
- Pot: 6bb

**Strategy Focus:** Squeeze 3-bet frequency
**Stats Mapped:** `squeeze_pct`, `three_bet_pct`

---

## SINGLE RAISED POT FLOPS (7)

### 6. SRP_Ks7c3d_cbet
**Description:** K-high dry board c-bet decision
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Board: Ks 7c 3d (rainbow, dry)
- Pot: 5.5bb
- Stack: 97.5bb

**Strategy Focus:** C-bet frequency and sizing
**Stats Mapped:** `cbet_flop_pct`, `fold_to_cbet_flop_pct`

---

### 7. SRP_Ah9s3h_cbet
**Description:** A-high monotone board c-bet
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Board: Ah 9s 3h (monotone hearts)
- Pot: 5.5bb
- Stack: 97.5bb

**Strategy Focus:** C-bet on draw-heavy board
**Stats Mapped:** `cbet_flop_pct`, `fold_to_cbet_flop_pct`

---

### 8. SRP_9s8h7d_cbet
**Description:** Middle connected board c-bet
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Board: 9s 8h 7d (connected, rainbow)
- Pot: 5.5bb
- Stack: 97.5bb

**Strategy Focus:** C-bet on coordinated board
**Stats Mapped:** `cbet_flop_pct`, `fold_to_cbet_flop_pct`

---

### 9. SRP_Qc7h2s_cbet
**Description:** Q-high dry board c-bet
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Board: Qc 7h 2s (rainbow, dry)
- Pot: 5.5bb
- Stack: 97.5bb

**Strategy Focus:** C-bet frequency on Q-high
**Stats Mapped:** `cbet_flop_pct`, `fold_to_cbet_flop_pct`

---

### 10. SRP_Tc9c5h_cbet
**Description:** T-high two-tone board c-bet
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Board: Tc 9c 5h (flush draw + straight draw)
- Pot: 5.5bb
- Stack: 97.5bb

**Strategy Focus:** C-bet on draw-heavy board
**Stats Mapped:** `cbet_flop_pct`, `fold_to_cbet_flop_pct`

---

### 11. SRP_6h5h4s_cbet
**Description:** Low connected board c-bet
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Board: 6h 5h 4s (low, connected, flush draw)
- Pot: 5.5bb
- Stack: 97.5bb

**Strategy Focus:** C-bet on low coordinated board
**Stats Mapped:** `cbet_flop_pct`, `fold_to_cbet_flop_pct`

---

### 12. SRP_AhKd3s_cbet
**Description:** AK-high board c-bet
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Board: Ah Kd 3s (two broadway, rainbow)
- Pot: 5.5bb
- Stack: 97.5bb

**Strategy Focus:** C-bet on high-card board
**Stats Mapped:** `cbet_flop_pct`, `fold_to_cbet_flop_pct`

---

## CRITICAL DECISION POINTS (3)

### 13. TURN_Ks7c3d_Th_barrel
**Description:** Turn barrel decision after flop c-bet
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Flop: Ks 7c 3d, BTN bets 3bb, BB calls
- Turn: Th
- Pot: 11.5bb
- Stack: 94.5bb

**Strategy Focus:** Turn barrel frequency
**Stats Mapped:** `cbet_turn_pct`, `fold_to_cbet_turn_pct`

---

### 14. RIVER_Ks7c3d_Th_Ac_bluff
**Description:** River bluff decision after turn barrel
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BTN open 2.5bb, BB call
- Flop: Ks 7c 3d, BTN bets 3bb, BB calls
- Turn: Th, BTN bets 8bb, BB calls
- River: Ac
- Pot: 27.5bb
- Stack: 86.5bb

**Strategy Focus:** River bluff frequency
**Stats Mapped:** `cbet_river_pct`, `fold_to_cbet_river_pct`

---

### 15. 3BET_AhKs9d_cbet
**Description:** 3-bet pot c-bet decision
**Game State:**
- Position: BTN (IP) vs BB (OOP)
- Preflop: BB opens 3bb, BTN 3bets 10bb, BB calls
- Board: Ah Ks 9d (two broadway, rainbow)
- Pot: 20.5bb
- Stack: 90bb

**Strategy Focus:** 3-bet pot c-bet frequency
**Stats Mapped:** `cbet_3bet_pot_pct`, `fold_to_3bet_cbet_pct`

---

## Implementation Priority

### Phase 1 (Highest Value - Solve First)
1. BTN_steal_vs_BB
2. SRP_Ks7c3d_cbet
3. SRP_Ah9s3h_cbet
4. CO_open_vs_BTN_3bet
5. 3BET_AhKs9d_cbet

### Phase 2 (High Value)
6. SRP_9s8h7d_cbet
7. SRP_Qc7h2s_cbet
8. TURN_Ks7c3d_Th_barrel
9. BB_vs_BTN_steal_defend
10. BTN_3bet_vs_CO_open

### Phase 3 (Supplementary)
11. SRP_Tc9c5h_cbet
12. SRP_6h5h4s_cbet
13. SRP_AhKd3s_cbet
14. RIVER_Ks7c3d_Th_Ac_bluff
15. SB_squeeze_vs_CO_BTN

---

## Expected Results

Each solved scenario will produce:
- **GTO frequencies:** Bet/check/fold/call/raise percentages
- **Bet sizing distribution:** Small/medium/large bet frequencies
- **EV calculations:** Expected value for each position
- **Range breakdowns:** Which hands take which actions
- **Exploitability measure:** How far from Nash equilibrium

## Database Storage

All solutions will be inserted into `gto_solutions` table:
```sql
INSERT INTO gto_solutions (
    scenario_name, scenario_type, board,
    position_oop, position_ip,
    pot_size, stack_depth,
    gto_bet_frequency, gto_fold_frequency, gto_raise_frequency,
    gto_betting_range, gto_folding_range, gto_calling_range,
    description, solved_at
) VALUES (...);
```

## Next Steps

1. Create TexasSolver config files for each scenario
2. Run batch solve (estimated 2-5 hours)
3. Parse output and import to database
4. Test API endpoints with real data
5. Integrate with Claude AI for exploit analysis
