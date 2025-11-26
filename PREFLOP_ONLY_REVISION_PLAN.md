# Preflop-Only GTO Stats Revision Plan

## Objective
Remove all postflop and showdown stats from the system. Player analysis, leak detection, and exploit recommendations will be based **exclusively on preflop GTO data** from our GTOWizard database (188 scenarios).

---

## Current State Summary

### Stats Currently Tracked
| Category | Stats | Action |
|----------|-------|--------|
| **Preflop** | VPIP, PFR, 3-bet, fold to 3-bet, 4-bet, cold call, limp, squeeze, steal, positional VPIP | **KEEP** |
| **Postflop** | C-bet (flop/turn/river), fold to c-bet, call c-bet, raise c-bet, check-raise, donk bet, float | **REMOVE** |
| **Showdown** | WTSD, W$SD, WWSF | **REMOVE** |
| **Aggression** | AF, AFQ | **REMOVE** (uses postflop data) |

### Composite Metrics
| Metric | Uses | Action |
|--------|------|--------|
| Exploitability Index (EI) | 35% preflop + 40% postflop + 25% showdown | **REVISE** → 100% preflop |
| Pressure Vulnerability Score | Fold to c-bet across streets | **REMOVE** |
| Aggression Consistency Ratio | Turn/Flop c-bet ratios | **REMOVE** |
| Positional Awareness Index | VPIP by position | **KEEP** |
| Blind Defense Efficiency | BB VPIP + fold to steal | **KEEP** |
| Value-Bluff Imbalance | WTSD/W$SD | **REMOVE** |
| Range Polarization Factor | River/Flop bet freq | **REMOVE** |
| Street Fold Gradient | Cross-street folds | **REMOVE** |
| Delayed Aggression Coefficient | Check-raise/float | **REMOVE** |
| Multi-Street Persistence | Street persistence | **REMOVE** |
| Player Type | VPIP/PFR based | **KEEP** (revise slightly) |

---

## Implementation Plan

### Phase 1: Backend - Remove Postflop Stats

#### 1.1 Update `gto_baselines.py`
- Remove `POSTFLOP_BASELINES` dictionary
- Remove `SHOWDOWN_BASELINES` dictionary
- Keep only `PREFLOP_GLOBAL` and `PREFLOP_BASELINES_6MAX`

#### 1.2 Update `stats_calculator.py`
- Remove calculation of postflop composite metrics:
  - `pressure_vulnerability_score`
  - `aggression_consistency_ratio`
  - `value_bluff_imbalance_ratio`
  - `range_polarization_factor`
  - `street_fold_gradient`
  - `delayed_aggression_coefficient`
  - `multi_street_persistence_score`
- Revise `exploitability_index` to use 100% preflop weighting
- Keep: `positional_awareness_index`, `blind_defense_efficiency`, `player_type`

#### 1.3 Update Leak Analysis (`get_leak_analysis()`)
- Remove postflop leaks: c-bet, fold to c-bet
- Remove showdown leaks: WTSD, W$SD
- Keep only preflop leaks:
  - VPIP (high/low)
  - PFR (high/low)
  - 3-bet (high/low)
  - Fold to 3-bet (high/low)
  - 4-bet
  - Cold call
  - Limp
  - Positional deviations

#### 1.4 Update GTO Service (`gto_service.py`)
- Modify `compare_player_to_gto()` to only return preflop deviations
- Remove postflop exploit recommendations
- Update exploit text to be more specific using our 188 scenario data

---

### Phase 2: Database - Import GTOWizard Data

#### 2.1 Run Import Script
- Execute `import_gtowizard_preflop.py`
- Populates `gto_scenarios` with 188 scenarios
- Populates `gto_frequencies` with combo-level frequencies
- Handle 6 zero-frequency scenarios

#### 2.2 Update Player GTO Stats
- Run `populate_gto_fixed.py` to recalculate player stats against new GTO data
- This compares actual player actions to our GTO frequencies

---

### Phase 3: Frontend - Simplify UI

#### 3.1 Update `PlayerProfile.tsx`
- Remove "Postflop Statistics" section
- Remove "Showdown Statistics" section
- Remove charts: C-Bet Streets Chart, Showdown Chart
- Keep: Preflop stats, Positional VPIP chart, Preflop Aggression chart

#### 3.2 Update Leak Display
- Only show preflop-related leaks
- Update Core Metrics to exclude showdown tendency
- Remove aggression metrics (AF, AFQ)

#### 3.3 Update Types (`types.ts`)
- Mark postflop fields as optional/deprecated
- Add comments indicating preflop-only mode

---

### Phase 4: New Preflop-Only Features

#### 4.1 Position-Specific GTO Comparison
Using our 188 scenarios, show detailed breakdowns:
- Opening range deviations by position
- Defense frequency vs each opener
- 3-bet/4-bet frequencies vs optimal
- Squeeze play analysis

#### 4.2 Scenario-Based Leak Detection
Instead of aggregate stats, detect leaks per scenario:
```
"BB vs BTN: Player folds 65% (GTO: 42%) → Over-folding leak"
"CO open: Player opens 35% (GTO: 28%) → Over-opening leak"
```

#### 4.3 Hand-Specific Exploits
Using combo-level frequencies:
```
"When you have AKo on BTN vs UTG open:
 - GTO: Call 35%, 3-bet 65%
 - Player: Always 3-bets
 - Exploit: Trap with AKo occasionally"
```

---

## File Changes Summary

### Backend Files to Modify
| File | Changes |
|------|---------|
| `backend/services/gto_baselines.py` | Remove postflop/showdown baselines |
| `backend/services/stats_calculator.py` | Remove 7 composite metrics, revise EI |
| `backend/services/gto_service.py` | Filter to preflop-only exploits |
| `backend/main.py` | Update API responses to exclude postflop |

### Frontend Files to Modify
| File | Changes |
|------|---------|
| `frontend/src/pages/PlayerProfile.tsx` | Remove postflop sections |
| `frontend/src/types.ts` | Mark postflop fields optional |
| `frontend/src/components/*.tsx` | Remove postflop charts |

### Database Changes
1. **Remove postflop columns from `player_stats` table**:
   - `cbet_flop_pct`, `cbet_turn_pct`, `cbet_river_pct`
   - `fold_to_cbet_flop_pct`, `fold_to_cbet_turn_pct`, `fold_to_cbet_river_pct`
   - `call_cbet_flop_pct`, `call_cbet_turn_pct`, `call_cbet_river_pct`
   - `raise_cbet_flop_pct`, `raise_cbet_turn_pct`, `raise_cbet_river_pct`
   - `check_raise_flop_pct`, `check_raise_turn_pct`, `check_raise_river_pct`
   - `donk_bet_flop_pct`, `donk_bet_turn_pct`, `donk_bet_river_pct`
   - `float_flop_pct`
   - `wtsd_pct`, `wsd_pct`
   - `af`, `afq`
   - Postflop composite metrics columns

2. **Remove postflop columns from `player_hand_summary` table**:
   - All `cbet_*`, `folded_to_cbet_*`, `called_cbet_*`, `raised_cbet_*`
   - All `check_raised_*`, `donk_bet_*`
   - `floated_flop`
   - `went_to_showdown`, `won_at_showdown`

3. **Clear postflop GTO data**:
   - Delete from `gto_solutions` (postflop solver data)
   - Delete postflop scenarios from `gto_scenarios`
   - Keep only preflop scenarios

### Database Scripts to Run
1. `backend/scripts/cleanup_postflop_data.py` - Remove postflop columns and data
2. `backend/scripts/import_gtowizard_preflop.py` - Import 188 scenarios
3. `backend/scripts/populate_gto_fixed.py` - Recalculate player stats

---

## New Preflop Stats to Display

### Key Preflop Metrics
| Stat | Description | GTO Baseline |
|------|-------------|--------------|
| VPIP | Overall voluntarily put in pot | 24% |
| PFR | Pre-flop raise frequency | 20% |
| 3-Bet | 3-bet frequency | 7% |
| Fold to 3-Bet | Folding when facing 3-bet | 48% |
| 4-Bet | 4-bet frequency | 2.5% |
| Cold Call | Cold calling opens | 5% |
| Steal Attempt | Late position steals | - |
| Fold to Steal | Folding to steals in blinds | - |

### Position-Specific Metrics
| Position | GTO VPIP | GTO PFR | GTO 3-Bet Range |
|----------|----------|---------|-----------------|
| UTG | 17% | 17% | vs HJ/CO/BTN/SB/BB |
| MP | 21% | 21% | vs CO/BTN/SB/BB |
| CO | 28% | 26% | vs BTN/SB/BB |
| BTN | 48% | 42% | vs SB/BB |
| SB | 42% | 38% | vs BB |
| BB | 38% | 11% | Defense vs all |

### Scenario Coverage (188 total)
- Opening ranges: 5 positions
- Defense vs open: 45 scenarios (fold/call/3bet × 15 matchups)
- Facing 3-bet: 42 scenarios (fold/call/4bet × 14 matchups)
- Facing 4-bet: 78 scenarios
- Squeeze: 18 scenarios

---

## Success Criteria

1. **No postflop data shown** anywhere in the app
2. **All comparisons use GTOWizard data** from our database
3. **Leak detection is preflop-only** and scenario-specific
4. **Exploits are actionable** with position/hand context
5. **Frontend is clean** without placeholder/empty sections

---

## Execution Order

1. [ ] **Database cleanup** - Remove postflop columns and data
2. [ ] **Import GTOWizard data** - Load 188 preflop scenarios
3. [ ] **Update `gto_baselines.py`** - Remove postflop baselines
4. [ ] **Update `stats_calculator.py`** - Remove postflop metrics
5. [ ] **Update `gto_service.py`** - Preflop-only exploits
6. [ ] **Update database models** - Remove postflop columns from ORM
7. [ ] **Update `main.py`** - Filter API responses
8. [ ] **Update frontend types** - Remove postflop fields
9. [ ] **Update PlayerProfile.tsx** - Remove postflop UI sections
10. [ ] **Recalculate all player stats** - Using new preflop-only metrics
11. [ ] **Test end-to-end**
12. [ ] **Deploy to production**
