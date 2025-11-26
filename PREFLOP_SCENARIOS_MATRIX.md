# Complete 6-Max Preflop Scenarios Matrix

## Overview
This document lists ALL preflop scenarios needed for comprehensive GTO analysis in 6-max 100bb poker.

---

## 1. RFI (Raise First In) - Opening Ranges
When you're first to act (no one has raised yet).

| Scenario ID | Position | Action | Description | Priority |
|-------------|----------|--------|-------------|----------|
| `UTG_open` | UTG | Open | First to act, 5 players behind | Critical |
| `HJ_open` | HJ | Open | 4 players behind | Critical |
| `CO_open` | CO | Open | 3 players behind | Critical |
| `BTN_open` | BTN | Open | 2 players behind (blinds) | Critical |
| `SB_open` | SB | Open | Only BB behind | Critical |

**Total RFI Scenarios: 5**

---

## 2. Vs Open (Defense) - Facing a Single Raise
When someone opens and you need to decide: Fold / Call / 3-Bet

### From HJ (vs UTG open only)
| Scenario ID | Hero | Villain | Actions | Priority |
|-------------|------|---------|---------|----------|
| `HJ_vs_UTG_fold` | HJ | UTG | Fold | High |
| `HJ_vs_UTG_call` | HJ | UTG | Call | High |
| `HJ_vs_UTG_3bet` | HJ | UTG | 3-Bet | High |

### From CO (vs UTG, HJ open)
| Scenario ID | Hero | Villain | Actions | Priority |
|-------------|------|---------|---------|----------|
| `CO_vs_UTG_fold` | CO | UTG | Fold | High |
| `CO_vs_UTG_call` | CO | UTG | Call | High |
| `CO_vs_UTG_3bet` | CO | UTG | 3-Bet | High |
| `CO_vs_HJ_fold` | CO | HJ | Fold | High |
| `CO_vs_HJ_call` | CO | HJ | Call | High |
| `CO_vs_HJ_3bet` | CO | HJ | 3-Bet | High |

### From BTN (vs UTG, HJ, CO open)
| Scenario ID | Hero | Villain | Actions | Priority |
|-------------|------|---------|---------|----------|
| `BTN_vs_UTG_fold` | BTN | UTG | Fold | Critical |
| `BTN_vs_UTG_call` | BTN | UTG | Call | Critical |
| `BTN_vs_UTG_3bet` | BTN | UTG | 3-Bet | Critical |
| `BTN_vs_HJ_fold` | BTN | HJ | Fold | Critical |
| `BTN_vs_HJ_call` | BTN | HJ | Call | Critical |
| `BTN_vs_HJ_3bet` | BTN | HJ | 3-Bet | Critical |
| `BTN_vs_CO_fold` | BTN | CO | Fold | Critical |
| `BTN_vs_CO_call` | BTN | CO | Call | Critical |
| `BTN_vs_CO_3bet` | BTN | CO | 3-Bet | Critical |

### From SB (vs UTG, HJ, CO, BTN open)
| Scenario ID | Hero | Villain | Actions | Priority |
|-------------|------|---------|---------|----------|
| `SB_vs_UTG_fold` | SB | UTG | Fold | High |
| `SB_vs_UTG_call` | SB | UTG | Call | High |
| `SB_vs_UTG_3bet` | SB | UTG | 3-Bet | High |
| `SB_vs_HJ_fold` | SB | HJ | Fold | High |
| `SB_vs_HJ_call` | SB | HJ | Call | High |
| `SB_vs_HJ_3bet` | SB | HJ | 3-Bet | High |
| `SB_vs_CO_fold` | SB | CO | Fold | High |
| `SB_vs_CO_call` | SB | CO | Call | High |
| `SB_vs_CO_3bet` | SB | CO | 3-Bet | High |
| `SB_vs_BTN_fold` | SB | BTN | Fold | Critical |
| `SB_vs_BTN_call` | SB | BTN | Call | Critical |
| `SB_vs_BTN_3bet` | SB | BTN | 3-Bet | Critical |

### From BB (vs UTG, HJ, CO, BTN, SB open)
| Scenario ID | Hero | Villain | Actions | Priority |
|-------------|------|---------|---------|----------|
| `BB_vs_UTG_fold` | BB | UTG | Fold | Critical |
| `BB_vs_UTG_call` | BB | UTG | Call | Critical |
| `BB_vs_UTG_3bet` | BB | UTG | 3-Bet | Critical |
| `BB_vs_HJ_fold` | BB | HJ | Fold | Critical |
| `BB_vs_HJ_call` | BB | HJ | Call | Critical |
| `BB_vs_HJ_3bet` | BB | HJ | 3-Bet | Critical |
| `BB_vs_CO_fold` | BB | CO | Fold | Critical |
| `BB_vs_CO_call` | BB | CO | Call | Critical |
| `BB_vs_CO_3bet` | BB | CO | 3-Bet | Critical |
| `BB_vs_BTN_fold` | BB | BTN | Fold | Critical |
| `BB_vs_BTN_call` | BB | BTN | Call | Critical |
| `BB_vs_BTN_3bet` | BB | BTN | 3-Bet | Critical |
| `BB_vs_SB_fold` | BB | SB | Fold | Critical |
| `BB_vs_SB_call` | BB | SB | Call | Critical |
| `BB_vs_SB_3bet` | BB | SB | 3-Bet | Critical |

**Total Vs Open Scenarios: 45** (15 matchups × 3 actions)

---

## 3. Facing 3-Bet (Original Raiser's Response)
When you opened and someone 3-bets you: Fold / Call / 4-Bet

### UTG faces 3-bet from:
| Scenario ID | Hero | 3-Bettor | Actions | Priority |
|-------------|------|----------|---------|----------|
| `UTG_vs_HJ_3bet_fold` | UTG | HJ | Fold to 3-bet | High |
| `UTG_vs_HJ_3bet_call` | UTG | HJ | Call 3-bet | High |
| `UTG_vs_HJ_3bet_4bet` | UTG | HJ | 4-bet | High |
| `UTG_vs_CO_3bet_fold` | UTG | CO | Fold to 3-bet | High |
| `UTG_vs_CO_3bet_call` | UTG | CO | Call 3-bet | High |
| `UTG_vs_CO_3bet_4bet` | UTG | CO | 4-bet | High |
| `UTG_vs_BTN_3bet_fold` | UTG | BTN | Fold to 3-bet | Critical |
| `UTG_vs_BTN_3bet_call` | UTG | BTN | Call 3-bet | Critical |
| `UTG_vs_BTN_3bet_4bet` | UTG | BTN | 4-bet | Critical |
| `UTG_vs_SB_3bet_fold` | UTG | SB | Fold to 3-bet | High |
| `UTG_vs_SB_3bet_call` | UTG | SB | Call 3-bet | High |
| `UTG_vs_SB_3bet_4bet` | UTG | SB | 4-bet | High |
| `UTG_vs_BB_3bet_fold` | UTG | BB | Fold to 3-bet | High |
| `UTG_vs_BB_3bet_call` | UTG | BB | Call 3-bet | High |
| `UTG_vs_BB_3bet_4bet` | UTG | BB | 4-bet | High |

### HJ faces 3-bet from:
| Scenario ID | Hero | 3-Bettor | Actions | Priority |
|-------------|------|----------|---------|----------|
| `HJ_vs_CO_3bet_fold` | HJ | CO | Fold to 3-bet | High |
| `HJ_vs_CO_3bet_call` | HJ | CO | Call 3-bet | High |
| `HJ_vs_CO_3bet_4bet` | HJ | CO | 4-bet | High |
| `HJ_vs_BTN_3bet_fold` | HJ | BTN | Fold to 3-bet | Critical |
| `HJ_vs_BTN_3bet_call` | HJ | BTN | Call 3-bet | Critical |
| `HJ_vs_BTN_3bet_4bet` | HJ | BTN | 4-bet | Critical |
| `HJ_vs_SB_3bet_fold` | HJ | SB | Fold to 3-bet | High |
| `HJ_vs_SB_3bet_call` | HJ | SB | Call 3-bet | High |
| `HJ_vs_SB_3bet_4bet` | HJ | SB | 4-bet | High |
| `HJ_vs_BB_3bet_fold` | HJ | BB | Fold to 3-bet | High |
| `HJ_vs_BB_3bet_call` | HJ | BB | Call 3-bet | High |
| `HJ_vs_BB_3bet_4bet` | HJ | BB | 4-bet | High |

### CO faces 3-bet from:
| Scenario ID | Hero | 3-Bettor | Actions | Priority |
|-------------|------|----------|---------|----------|
| `CO_vs_BTN_3bet_fold` | CO | BTN | Fold to 3-bet | Critical |
| `CO_vs_BTN_3bet_call` | CO | BTN | Call 3-bet | Critical |
| `CO_vs_BTN_3bet_4bet` | CO | BTN | 4-bet | Critical |
| `CO_vs_SB_3bet_fold` | CO | SB | Fold to 3-bet | High |
| `CO_vs_SB_3bet_call` | CO | SB | Call 3-bet | High |
| `CO_vs_SB_3bet_4bet` | CO | SB | 4-bet | High |
| `CO_vs_BB_3bet_fold` | CO | BB | Fold to 3-bet | Critical |
| `CO_vs_BB_3bet_call` | CO | BB | Call 3-bet | Critical |
| `CO_vs_BB_3bet_4bet` | CO | BB | 4-bet | Critical |

### BTN faces 3-bet from:
| Scenario ID | Hero | 3-Bettor | Actions | Priority |
|-------------|------|----------|---------|----------|
| `BTN_vs_SB_3bet_fold` | BTN | SB | Fold to 3-bet | Critical |
| `BTN_vs_SB_3bet_call` | BTN | SB | Call 3-bet | Critical |
| `BTN_vs_SB_3bet_4bet` | BTN | SB | 4-bet | Critical |
| `BTN_vs_BB_3bet_fold` | BTN | BB | Fold to 3-bet | Critical |
| `BTN_vs_BB_3bet_call` | BTN | BB | Call 3-bet | Critical |
| `BTN_vs_BB_3bet_4bet` | BTN | BB | 4-bet | Critical |

### SB faces 3-bet from BB:
| Scenario ID | Hero | 3-Bettor | Actions | Priority |
|-------------|------|----------|---------|----------|
| `SB_vs_BB_3bet_fold` | SB | BB | Fold to 3-bet | Critical |
| `SB_vs_BB_3bet_call` | SB | BB | Call 3-bet | Critical |
| `SB_vs_BB_3bet_4bet` | SB | BB | 4-bet | Critical |

**Total Facing 3-Bet Scenarios: 42** (14 matchups × 3 actions)

---

## 4. Facing 4-Bet (3-Bettor's Response)
When you 3-bet and villain 4-bets: Fold / Call / 5-Bet(All-in)

| Scenario ID | Hero (3-bettor) | Villain (4-bettor) | Priority |
|-------------|-----------------|-------------------|----------|
| `BB_vs_UTG_4bet_fold` | BB | UTG | High |
| `BB_vs_UTG_4bet_call` | BB | UTG | High |
| `BB_vs_UTG_4bet_allin` | BB | UTG | High |
| `BB_vs_BTN_4bet_fold` | BB | BTN | Critical |
| `BB_vs_BTN_4bet_call` | BB | BTN | Critical |
| `BB_vs_BTN_4bet_allin` | BB | BTN | Critical |
| `SB_vs_BTN_4bet_fold` | SB | BTN | Critical |
| `SB_vs_BTN_4bet_call` | SB | BTN | Critical |
| `SB_vs_BTN_4bet_allin` | SB | BTN | Critical |
| `BTN_vs_BB_4bet_fold` | BTN | BB | High |
| `BTN_vs_BB_4bet_call` | BTN | BB | High |
| `BTN_vs_BB_4bet_allin` | BTN | BB | High |
| `CO_vs_BB_4bet_fold` | CO | BB | High |
| `CO_vs_BB_4bet_call` | CO | BB | High |
| `CO_vs_BB_4bet_allin` | CO | BB | High |

**Total Facing 4-Bet Scenarios: 15-24** (most common matchups)

---

## 5. Special Scenarios (Lower Priority)

### Squeeze Plays
When there's an open and a call, and you squeeze from later position.

| Scenario ID | Hero | Open | Caller | Priority |
|-------------|------|------|--------|----------|
| `BTN_squeeze_vs_UTG_HJ` | BTN | UTG | HJ | Medium |
| `SB_squeeze_vs_CO_BTN` | SB | CO | BTN | Medium |
| `BB_squeeze_vs_CO_BTN` | BB | CO | BTN | Medium |
| `BB_squeeze_vs_BTN_SB` | BB | BTN | SB | Medium |

### Limp Pots (if tracking limps)
| Scenario ID | Hero | Action | Priority |
|-------------|------|--------|----------|
| `SB_complete` | SB | Complete vs BB | Low |
| `BB_vs_SB_limp_raise` | BB | Raise vs SB limp | Low |
| `BB_vs_SB_limp_check` | BB | Check vs SB limp | Low |

---

## Summary: Total Scenarios Needed

| Category | Scenarios | Priority |
|----------|-----------|----------|
| RFI (Opening) | 5 | Critical |
| Vs Open (Defense) | 45 | Critical |
| Facing 3-Bet | 42 | High |
| Facing 4-Bet | 15-24 | Medium |
| Squeeze | 4-8 | Medium |
| Limp Pots | 3-6 | Low |
| **TOTAL** | **~115-130** | |

---

## Data Required Per Scenario

For each scenario, we need:
1. **169 hand frequencies** (AA, AKs, AKo, ... 22)
2. Each hand has frequency 0.0 to 1.0 for that action

Example for `BB_vs_BTN_call`:
```
Hand    Frequency
AA      0.00      (never just call, always 3-bet)
AKs     0.35      (call 35%, 3-bet 65%)
AKo     0.55      (call 55%, 3-bet 45%)
QJs     0.80      (call 80%, fold 15%, 3-bet 5%)
72o     0.00      (always fold)
...
```

**Total frequency records needed: ~115 scenarios × 169 hands = ~19,435 records**

---

## GTOWizard Data Format Expected

When you provide GTOWizard data, please format as:
```
SCENARIO: BB_vs_BTN_call
AA:0.00
AKs:0.35
AKo:0.55
AQs:0.45
AQo:0.60
...
```

Or as a CSV:
```
scenario,hand,frequency
BB_vs_BTN_call,AA,0.00
BB_vs_BTN_call,AKs,0.35
BB_vs_BTN_call,AKo,0.55
...
```
