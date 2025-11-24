# GTO Scenarios Database

Total scenarios: 127

## Opening (5 scenarios)
- UTG_open
- MP_open
- CO_open
- BTN_open
- SB_open

## Defense (16 scenarios)
Defending against a single open raise (fold/call/3bet)

### BB Defense
- BB_vs_UTG_fold, BB_vs_UTG_call
- BB_vs_MP_fold, BB_vs_MP_call
- BB_vs_CO_fold, BB_vs_CO_call
- BB_vs_SB_fold, BB_vs_SB_call

### SB Defense
- SB_vs_UTG_fold, SB_vs_UTG_call
- SB_vs_MP_fold, SB_vs_MP_call
- SB_vs_CO_fold, SB_vs_CO_call
- SB_vs_BTN_fold, SB_vs_BTN_call (wait, this might be multiway?)

### CO Defense
- CO_vs_UTG_fold
- CO_vs_MP_fold

## Facing 3-Bet (69 scenarios)
Hero is 3-betting or facing a 3-bet

### BB 3-betting
- BB_vs_UTG_3bet, BB_vs_MP_3bet, BB_vs_CO_3bet, BB_vs_BTN_3bet, BB_vs_SB_3bet
- BB_vs_UTG_BTN_3bet (multiway)
- BB_vs_MP_BTN_3bet (multiway)
- BB_vs_CO_BTN_3bet (multiway)

### SB 3-betting
- SB_vs_UTG_3bet, SB_vs_MP_3bet, SB_vs_CO_3bet, SB_vs_BTN_3bet
- SB_vs_UTG_BTN_3bet (multiway)
- SB_vs_MP_BTN_3bet (multiway)
- SB_vs_CO_BTN_3bet (multiway)

### CO 3-betting
- CO_vs_UTG_3bet, CO_vs_MP_3bet

### BTN 3-betting
- BTN_vs_UTG_3bet, BTN_vs_MP_3bet, BTN_vs_CO_3bet

### UTG Facing 3-bet (from CO/BTN/SB/BB)
- UTG_vs_CO_3bet_fold, UTG_vs_CO_3bet_call, UTG_vs_CO_3bet_4bet, UTG_vs_CO_3bet_allin
- UTG_vs_BTN_3bet_fold, UTG_vs_BTN_3bet_call, UTG_vs_BTN_3bet_4bet, UTG_vs_BTN_3bet_allin
- UTG_vs_SB_3bet_fold, UTG_vs_SB_3bet_call, UTG_vs_SB_3bet_4bet, UTG_vs_SB_3bet_allin
- UTG_vs_BB_3bet_fold, UTG_vs_BB_3bet_call, UTG_vs_BB_3bet_4bet, UTG_vs_BB_3bet_allin

### MP Facing 3-bet (from BTN/SB/BB)
- MP_vs_BTN_3bet_fold, MP_vs_BTN_3bet_call, MP_vs_BTN_3bet_4bet, MP_vs_BTN_3bet_allin
- MP_vs_SB_3bet_fold, MP_vs_SB_3bet_call, MP_vs_SB_3bet_4bet, MP_vs_SB_3bet_allin
- MP_vs_BB_3bet_fold, MP_vs_BB_3bet_call, MP_vs_BB_3bet_4bet, MP_vs_BB_3bet_allin

### CO Facing 3-bet (from BTN/SB/BB)
- CO_vs_BTN_3bet_fold, CO_vs_BTN_3bet_call, CO_vs_BTN_3bet_4bet, CO_vs_BTN_3bet_allin
- CO_vs_SB_3bet_fold, CO_vs_SB_3bet_call, CO_vs_SB_3bet_4bet, CO_vs_SB_3bet_allin
- CO_vs_BB_3bet_fold, CO_vs_BB_3bet_call, CO_vs_BB_3bet_4bet, CO_vs_BB_3bet_allin

### BTN Facing 3-bet (from SB/BB)
- BTN_vs_SB_3bet_fold, BTN_vs_SB_3bet_call, BTN_vs_SB_3bet_4bet, BTN_vs_SB_3bet_allin
- BTN_vs_BB_3bet_fold, BTN_vs_BB_3bet_call, BTN_vs_BB_3bet_4bet, BTN_vs_BB_3bet_allin

### SB Facing 3-bet (from BB)
- SB_vs_BB_3bet_fold, SB_vs_BB_3bet_call, SB_vs_BB_3bet_4bet, SB_vs_BB_3bet_allin

## Facing 4-Bet (8 scenarios)
Hero facing a 4-bet after 3-betting

### BB Facing 4-bet
- BB_vs_BTN_4bet_fold, BB_vs_BTN_4bet_call, BB_vs_BTN_4bet_5bet, BB_vs_BTN_4bet_allin
- BB_vs_CO_4bet_fold, BB_vs_CO_4bet_call, BB_vs_CO_4bet_5bet, BB_vs_CO_4bet_allin

### SB Facing 4-bet
- SB_vs_BTN_4bet_fold, SB_vs_BTN_4bet_call, SB_vs_BTN_4bet_5bet, SB_vs_BTN_4bet_allin

## Multiway (29 scenarios)
Multiple players involved (opener + caller(s) + hero)

### BB in Multiway
- BB_vs_UTG_BTN_fold, BB_vs_UTG_BTN_call
- BB_vs_MP_BTN_fold, BB_vs_MP_BTN_call
- BB_vs_CO_BTN_fold, BB_vs_CO_BTN_call
- BB_vs_BTN_fold, BB_vs_BTN_call (unclear opener - possibly SB opens, BTN calls)

### SB in Multiway
- SB_vs_UTG_BTN_fold, SB_vs_UTG_BTN_call
- SB_vs_MP_BTN_fold, SB_vs_MP_BTN_call
- SB_vs_CO_BTN_fold, SB_vs_CO_BTN_call
- SB_vs_BTN_fold, SB_vs_BTN_call (unclear opener)

### BTN in Multiway
- BTN_vs_UTG_fold, BTN_vs_UTG_call
- BTN_vs_MP_fold, BTN_vs_MP_call
- BTN_vs_CO_fold, BTN_vs_CO_call

## How to Browse Scenarios

### Example 1: Opening Scenario
1. Click "Raise" at UTG
2. Click "View GTO Solution for UTG"
3. See UTG_open range

### Example 2: Defense Scenario
1. UTG clicks "Raise"
2. MP-CO-BTN-SB all click "Fold"
3. BB clicks "Call"
4. Click "View GTO Solution for BB"
5. See BB_vs_UTG_call range

### Example 3: 3-Bet Scenario
1. UTG clicks "Raise"
2. MP-CO-BTN-SB click "Fold"
3. BB clicks "3-Bet"
4. Click "View GTO Solution for BB"
5. See BB_vs_UTG_3bet range

### Example 4: Facing 3-Bet Scenario
1. UTG clicks "Raise"
2. MP-CO click "Fold"
3. BTN clicks "3-Bet"
4. SB clicks "Fold"
5. BB clicks "Fold"
6. Action back to UTG
7. UTG clicks "4-Bet"
8. Click "View GTO Solution for UTG"
9. See UTG_vs_BTN_3bet_4bet range

### Example 5: Multiway Scenario
1. UTG clicks "Raise"
2. MP-CO click "Fold"
3. BTN clicks "Call"
4. SB clicks "Fold"
5. BB clicks "Call"
6. Click "View GTO Solution for BB"
7. See BB_vs_UTG_BTN_call range

### Example 6: Facing 4-Bet Scenario
1. CO clicks "Raise"
2. BTN clicks "3-Bet"
3. SB-BB click "Fold"
4. CO clicks "4-Bet"
5. Action back to BTN
6. BTN clicks "5-Bet"
7. Click "View GTO Solution for BTN"
8. See BTN_vs_CO_4bet_5bet range (if exists)
