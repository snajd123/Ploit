# Optimized Preflop-Only Database Schema

## Overview
This schema is designed specifically for preflop GTO analysis with 188 scenarios from GTOWizard.

---

## Tables Summary

| Table | Status | Purpose |
|-------|--------|---------|
| `raw_hands` | KEEP | Store original hand history text |
| `hand_actions` | KEEP | Audit trail of all actions |
| `gto_scenarios` | KEEP | 188 preflop scenario definitions |
| `gto_frequencies` | KEEP | GTO frequencies per combo per scenario |
| `player_preflop_actions` | NEW | Individual preflop actions with GTO comparison |
| `player_scenario_stats` | NEW | Aggregated per-action stats per scenario |
| `player_stats` | SIMPLIFY | Keep only preflop aggregate stats |
| `upload_sessions` | KEEP | Upload tracking |
| `player_hand_summary` | REMOVE | Redundant for preflop-only |
| `player_actions` (old) | REMOVE | Replaced by player_preflop_actions |
| `player_gto_stats` (old) | REMOVE | Replaced by player_scenario_stats |
| `hand_types` | REMOVE | Compute in code instead |

---

## Schema Definition

### 1. gto_scenarios (KEEP - no changes)
```sql
CREATE TABLE gto_scenarios (
    scenario_id SERIAL PRIMARY KEY,
    scenario_name VARCHAR(100) UNIQUE NOT NULL,  -- 'BB_vs_BTN_call'
    street VARCHAR(10) NOT NULL DEFAULT 'preflop',
    category VARCHAR(50) NOT NULL,  -- 'opening', 'defense', 'facing_3bet', 'facing_4bet', 'squeeze'
    position VARCHAR(10),           -- Hero position: 'UTG', 'BB', etc.
    action VARCHAR(20),             -- 'open', 'fold', 'call', '3bet', '4bet', 'allin'
    opponent_position VARCHAR(10),  -- Villain position (NULL for opens)
    data_source VARCHAR(50) DEFAULT 'gtowizard',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 188 preflop scenarios
```

### 2. gto_frequencies (KEEP - no changes)
```sql
CREATE TABLE gto_frequencies (
    frequency_id SERIAL PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id) ON DELETE CASCADE,
    hand VARCHAR(4) NOT NULL,       -- 'AhKd' (combo) or 'AKo' (hand type)
    position VARCHAR(10) NOT NULL,  -- Whose strategy
    frequency DECIMAL(10, 8) NOT NULL,  -- 0.0 to 1.0
    UNIQUE(scenario_id, hand, position)
);
-- ~50,000+ frequency records (188 scenarios × ~270 combos)
```

### 3. player_preflop_actions (NEW - replaces player_actions)
```sql
CREATE TABLE player_preflop_actions (
    action_id BIGSERIAL PRIMARY KEY,

    -- Linkage
    player_name VARCHAR(100) NOT NULL,
    hand_id BIGINT NOT NULL REFERENCES raw_hands(hand_id) ON DELETE CASCADE,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id),

    -- Context
    timestamp TIMESTAMP NOT NULL,
    hero_position VARCHAR(10) NOT NULL,     -- 'BB', 'UTG', etc.
    villain_position VARCHAR(10),           -- NULL for opens
    effective_stack_bb INTEGER,             -- Stack depth matters for GTO

    -- Action details
    hole_cards VARCHAR(4),                  -- 'AKo', 'JTs' (NULL if unknown)
    action_taken VARCHAR(20) NOT NULL,      -- 'fold', 'call', 'open', '3bet', '4bet', 'allin'

    -- GTO comparison (calculated on insert)
    gto_frequency DECIMAL(10, 8),           -- What GTO says for this hand
    is_mistake BOOLEAN,                     -- Did they deviate significantly?
    ev_loss_bb DECIMAL(10, 4),              -- Estimated EV loss
    mistake_severity VARCHAR(20),           -- 'minor', 'moderate', 'major', 'critical'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indices for fast queries
    INDEX idx_player_scenario (player_name, scenario_id),
    INDEX idx_player_timestamp (player_name, timestamp DESC)
);
```

### 4. player_scenario_stats (NEW - replaces player_gto_stats)
```sql
CREATE TABLE player_scenario_stats (
    stat_id SERIAL PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id),

    -- Sample size
    total_opportunities INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Action counts (how many times they took each action)
    fold_count INTEGER DEFAULT 0,
    call_count INTEGER DEFAULT 0,
    open_count INTEGER DEFAULT 0,      -- For opening scenarios
    three_bet_count INTEGER DEFAULT 0,
    four_bet_count INTEGER DEFAULT 0,
    allin_count INTEGER DEFAULT 0,

    -- Player frequencies (calculated from counts)
    fold_freq DECIMAL(10, 8),
    call_freq DECIMAL(10, 8),
    open_freq DECIMAL(10, 8),
    three_bet_freq DECIMAL(10, 8),
    four_bet_freq DECIMAL(10, 8),
    allin_freq DECIMAL(10, 8),

    -- GTO frequencies (from gto_frequencies, averaged)
    gto_fold_freq DECIMAL(10, 8),
    gto_call_freq DECIMAL(10, 8),
    gto_open_freq DECIMAL(10, 8),
    gto_three_bet_freq DECIMAL(10, 8),
    gto_four_bet_freq DECIMAL(10, 8),
    gto_allin_freq DECIMAL(10, 8),

    -- Deviations (player - GTO)
    fold_deviation DECIMAL(10, 8),
    call_deviation DECIMAL(10, 8),
    open_deviation DECIMAL(10, 8),
    three_bet_deviation DECIMAL(10, 8),
    four_bet_deviation DECIMAL(10, 8),

    -- Primary leak detection
    primary_leak VARCHAR(50),           -- 'overfold', 'undercall', 'over3bet', etc.
    primary_leak_severity VARCHAR(20),  -- 'minor', 'moderate', 'major', 'critical'
    total_ev_loss_bb DECIMAL(10, 4),

    -- Exploit recommendation
    exploit_description TEXT,
    exploit_value_bb_100 DECIMAL(10, 4),
    exploit_confidence DECIMAL(5, 2),   -- Based on sample size

    UNIQUE(player_name, scenario_id),
    INDEX idx_player_leak (player_name, primary_leak_severity DESC)
);
```

### 5. player_stats (SIMPLIFIED - preflop only)
```sql
CREATE TABLE player_stats (
    player_name VARCHAR(100) PRIMARY KEY,
    total_hands INTEGER DEFAULT 0,

    -- Core preflop stats
    vpip_pct DECIMAL(5, 2),
    pfr_pct DECIMAL(5, 2),
    three_bet_pct DECIMAL(5, 2),
    fold_to_three_bet_pct DECIMAL(5, 2),
    four_bet_pct DECIMAL(5, 2),
    cold_call_pct DECIMAL(5, 2),
    limp_pct DECIMAL(5, 2),
    squeeze_pct DECIMAL(5, 2),

    -- Positional VPIP
    vpip_utg DECIMAL(5, 2),
    vpip_mp DECIMAL(5, 2),
    vpip_co DECIMAL(5, 2),
    vpip_btn DECIMAL(5, 2),
    vpip_sb DECIMAL(5, 2),
    vpip_bb DECIMAL(5, 2),

    -- Steal/defense
    steal_attempt_pct DECIMAL(5, 2),
    fold_to_steal_pct DECIMAL(5, 2),
    three_bet_vs_steal_pct DECIMAL(5, 2),

    -- Win rate (keep for reference)
    total_profit_loss DECIMAL(12, 2),
    bb_per_100 DECIMAL(8, 2),

    -- Composite metrics (preflop-only)
    exploitability_index DECIMAL(5, 2),        -- Recalculated for preflop
    positional_awareness_index DECIMAL(5, 2),  -- Based on positional VPIP
    blind_defense_efficiency DECIMAL(5, 2),    -- BB/SB defense quality
    player_type VARCHAR(20),                   -- 'TAG', 'LAG', 'NIT', 'FISH', etc.

    -- Metadata
    first_hand_date TIMESTAMP,
    last_hand_date TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Tables to DROP

```sql
-- Remove postflop/legacy tables
DROP TABLE IF EXISTS player_hand_summary CASCADE;
DROP TABLE IF EXISTS player_actions CASCADE;      -- Old GTO table
DROP TABLE IF EXISTS player_gto_stats CASCADE;    -- Old GTO stats
DROP TABLE IF EXISTS hand_types CASCADE;          -- Compute in code
DROP TABLE IF EXISTS gto_solutions CASCADE;       -- Postflop solver data
DROP TABLE IF EXISTS postflop_hand_frequencies CASCADE;  -- If exists
DROP TABLE IF EXISTS gto_category_aggregates CASCADE;    -- If exists
```

---

## Data Flow (Optimized)

```
Hand History Upload
        ↓
    raw_hands (store text)
        ↓
    hand_actions (parse all actions)
        ↓
    [Preflop Extraction]
        ↓
    player_preflop_actions
    (link to scenario, calculate GTO deviation)
        ↓
    player_scenario_stats
    (aggregate per-action frequencies)
        ↓
    player_stats
    (overall preflop stats + composite metrics)
        ↓
    Frontend: Leak Analysis + Exploits
```

---

## Key Improvements

### 1. Proper FK Linkage
```sql
-- player_preflop_actions links to both:
hand_id → raw_hands.hand_id     -- Trace back to original hand
scenario_id → gto_scenarios     -- Map to GTO
```

### 2. Stack Depth Tracking
```sql
effective_stack_bb INTEGER  -- 50bb vs 100bb changes GTO significantly
```

### 3. Per-Action Breakdown
```sql
-- Instead of one aggregate number:
fold_count, call_count, three_bet_count...
fold_freq, call_freq, three_bet_freq...
fold_deviation, call_deviation, three_bet_deviation...
```

### 4. Reduced Column Count
- **Old player_stats**: 50+ columns (most postflop)
- **New player_stats**: 25 columns (preflop only)
- **Removed player_hand_summary**: 90+ columns → 0

---

## Migration Steps

1. Create new tables (`player_preflop_actions`, `player_scenario_stats`)
2. Migrate data from old tables where applicable
3. Drop old postflop columns from `player_stats`
4. Drop deprecated tables
5. Update ORM models
6. Update services to use new schema
7. Recalculate all player stats

---

## Index Strategy

```sql
-- Fast player lookups
CREATE INDEX idx_preflop_player ON player_preflop_actions(player_name);
CREATE INDEX idx_preflop_scenario ON player_preflop_actions(scenario_id);
CREATE INDEX idx_preflop_player_scenario ON player_preflop_actions(player_name, scenario_id);

-- Fast leak queries
CREATE INDEX idx_scenario_stats_player ON player_scenario_stats(player_name);
CREATE INDEX idx_scenario_stats_leak ON player_scenario_stats(player_name, primary_leak_severity DESC);

-- Fast scenario lookups
CREATE INDEX idx_gto_freq_scenario ON gto_frequencies(scenario_id);
```

---

## Estimated Storage

| Table | Rows (est.) | Size |
|-------|-------------|------|
| raw_hands | 100k | 50MB |
| hand_actions | 500k | 100MB |
| gto_scenarios | 188 | <1MB |
| gto_frequencies | 50k | 5MB |
| player_preflop_actions | 200k | 50MB |
| player_scenario_stats | 10k | 5MB |
| player_stats | 500 | <1MB |
| **Total** | | **~210MB** |

This is significantly smaller than current schema with postflop data.
