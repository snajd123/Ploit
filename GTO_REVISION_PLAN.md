# GTO Stats Revision Plan

## Objective
Replace all hardcoded GTO baselines with data from our internal GTO database. All player stats, leak detection, and exploit recommendations must be derived from our own solver data - no external website data.

---

## Current State

### What We Have
1. **GTO Database Tables** (exist but partially empty):
   - `gto_scenarios` - Scenario metadata (preflop/postflop)
   - `gto_frequencies` - Hand frequencies per scenario (EMPTY)
   - `gto_solutions` - Postflop solver output (56 solutions imported)
   - `player_gto_stats` - Player leak aggregations

2. **Solver Data**:
   - 56 postflop solutions from TexasSolver in `/solver/outputs_comprehensive/`
   - Each solution has 279 hand combos with action frequencies
   - Board categorization system (3-level hierarchy)

3. **Hardcoded Baselines** (to be replaced):
   - `/backend/services/gto_baselines.py` - Currently used for all comparisons
   - Contains preflop ranges, postflop c-bet frequencies, showdown stats

### What's Missing
- Preflop frequency data not populated in database
- Postflop hand strategies stored as JSON blobs, not queryable
- No aggregation tables for category-based matching
- Service layer queries hardcoded values, not database

---

## Implementation Plan

### Phase 1: Preflop GTO Data Population
**Goal**: Populate preflop frequencies from our own solver/range data

#### 1.1 Generate Preflop Scenarios
Create scenarios for all 6-max preflop situations:
- Opening ranges: UTG, HJ, CO, BTN, SB (5 scenarios)
- Defense vs open: BB vs each position (5 scenarios)
- 3-bet scenarios: Each position vs openers (20+ scenarios)
- Facing 3-bet: Fold/call/4-bet frequencies (20+ scenarios)

**Files to create/modify**:
- `backend/scripts/populate_preflop_scenarios.py`

#### 1.2 Import Preflop Frequencies
Parse existing range files and populate `gto_frequencies`:
- Parse `/solver/gtowizard_ranges.txt` (if using our own data)
- OR run TexasSolver for preflop scenarios
- Convert combo frequencies to hand type frequencies

**Data structure**:
```
gto_frequencies:
- scenario_id: FK to gto_scenarios
- hand: 'AKo', 'QJs', '77' (169 hands)
- position: whose strategy (hero)
- frequency: 0.0 to 1.0
```

#### 1.3 Create Preflop Query Functions
Replace hardcoded lookups with database queries:
```python
def get_preflop_gto_frequency(position: str, action: str, hand: str) -> float:
    # Query gto_frequencies table
    # Return aggregated frequency for hand type
```

---

### Phase 2: Postflop GTO Data Normalization
**Goal**: Make postflop solver data queryable

#### 2.1 Create Normalized Frequency Table
New table `postflop_hand_frequencies`:
```sql
CREATE TABLE postflop_hand_frequencies (
    id SERIAL PRIMARY KEY,
    solution_id INTEGER REFERENCES gto_solutions(solution_id),
    combo VARCHAR(4),           -- 'AhKd', '7s7c'
    hand_type VARCHAR(4),       -- 'AKo', '77'
    action_index INTEGER,       -- 0=check, 1=bet_small, etc.
    action_name VARCHAR(50),    -- 'CHECK', 'BET 2.000000'
    frequency DECIMAL(10,8),    -- 0.0 to 1.0
    UNIQUE(solution_id, combo, action_index)
);
```

#### 2.2 Parse and Populate Postflop Frequencies
Script to extract from JSONB `hand_strategies`:
- Parse 279 combos per solution
- Extract frequency for each action
- Insert into normalized table
- ~94,000 records for 56 solutions

**Files to create**:
- `backend/scripts/normalize_postflop_frequencies.py`

#### 2.3 Create Aggregation Tables
For board category matching:
```sql
CREATE TABLE gto_category_aggregates (
    id SERIAL PRIMARY KEY,
    board_category_l1 VARCHAR(50),
    board_category_l2 VARCHAR(100),
    position_context VARCHAR(10),  -- 'IP' or 'OOP'
    action_name VARCHAR(50),
    avg_frequency DECIMAL(10,8),
    std_frequency DECIMAL(10,8),
    sample_count INTEGER
);
```

---

### Phase 3: Replace Hardcoded Baselines
**Goal**: Remove `gto_baselines.py` dependencies

#### 3.1 Create GTO Data Service
New service layer that queries database:
```python
class GTODataService:
    def get_preflop_baseline(self, stat: str, position: str = None) -> float:
        """Get preflop baseline from gto_frequencies table"""

    def get_postflop_baseline(self, board: str, position: str, action: str) -> float:
        """Get postflop baseline from gto_solutions or category aggregates"""

    def get_baseline_for_stat(self, stat_name: str) -> Dict:
        """Universal baseline getter - replaces gto_baselines.py"""
```

#### 3.2 Update Stats Calculator
Modify `stats_calculator.py` to use GTODataService:
- Replace `from backend.services.gto_baselines import ...`
- Inject GTODataService
- Query database for all baseline comparisons

#### 3.3 Update Leak Analysis
Modify leak detection to use database frequencies:
- Compare player actions to database GTO
- Calculate deviations from actual solver data
- Generate exploits based on specific scenario data

---

### Phase 4: Comprehensive Stats Recalculation
**Goal**: Recalculate all player stats using database GTO

#### 4.1 Define Core GTO Stats
From our solver data, calculate:

**Preflop Stats** (vs GTO opening/defense):
- VPIP deviation by position
- PFR deviation by position
- 3-bet frequency vs GTO by position pair
- Fold to 3-bet vs GTO
- Open raise sizing (if available)

**Postflop Stats** (vs GTO solver output):
- C-bet frequency vs GTO by board texture
- Fold to c-bet vs GTO by board texture
- Check-raise frequency vs GTO
- River bet/fold frequencies

#### 4.2 Create Position-Specific Baselines
From database, derive:
```python
POSITION_BASELINES = {
    'UTG': {'vpip': query_avg('UTG', 'open'), 'pfr': ...},
    'HJ': {...},
    'CO': {...},
    'BTN': {...},
    'SB': {...},
    'BB': {...}
}
```

#### 4.3 Create Board-Texture Baselines
From solver output, derive:
```python
BOARD_TEXTURE_BASELINES = {
    'dry_rainbow': {'cbet': avg_from_category('dry-rainbow')},
    'wet_monotone': {'cbet': avg_from_category('wet-monotone')},
    ...
}
```

---

### Phase 5: Frontend Integration
**Goal**: Display GTO-based stats with source attribution

#### 5.1 Update API Responses
Add GTO source information:
```json
{
  "stat": "vpip",
  "player_value": 35.2,
  "gto_baseline": 24.0,
  "gto_source": "internal_solver",
  "scenarios_used": 5,
  "confidence": "high"
}
```

#### 5.2 Update Frontend Components
- Show "Based on X solver scenarios"
- Indicate data source (internal GTO database)
- Display confidence based on scenario coverage

---

## Data Requirements

### Minimum Preflop Coverage
| Scenario Type | Count | Priority |
|--------------|-------|----------|
| Opening ranges | 5 | Critical |
| Defense vs open | 5 | Critical |
| 3-bet ranges | 20 | High |
| Facing 3-bet | 20 | High |
| Squeeze | 10 | Medium |
| **Total** | **60** | |

### Minimum Postflop Coverage
| Board Category | Solutions | Priority |
|---------------|-----------|----------|
| Dry rainbow | 10+ | Critical |
| Wet connected | 10+ | Critical |
| Paired boards | 10+ | High |
| Monotone | 5+ | High |
| **Total** | **56 (current)** | |

---

## Implementation Order

### Week 1: Foundation
1. [ ] Create `populate_preflop_scenarios.py` script
2. [ ] Populate gto_scenarios with preflop scenarios
3. [ ] Create frequency import from existing range data
4. [ ] Populate gto_frequencies table

### Week 2: Normalization
5. [ ] Create `postflop_hand_frequencies` table
6. [ ] Create `normalize_postflop_frequencies.py` script
7. [ ] Parse and populate from gto_solutions.hand_strategies
8. [ ] Create `gto_category_aggregates` table and populate

### Week 3: Service Layer
9. [ ] Create `GTODataService` class
10. [ ] Add database query methods for all baseline types
11. [ ] Update `stats_calculator.py` to use GTODataService
12. [ ] Update leak analysis to use database queries

### Week 4: Integration & Testing
13. [ ] Remove hardcoded gto_baselines.py dependencies
14. [ ] Recalculate all player stats
15. [ ] Update frontend to show GTO source
16. [ ] Full testing and validation

---

## Success Criteria

1. **No External Data**: All GTO comparisons use internal database only
2. **Full Coverage**: Preflop + postflop scenarios populated
3. **Queryable**: All baselines come from SQL queries, not hardcoded
4. **Traceable**: Each stat shows which scenarios were used
5. **Accurate**: Deviations match actual solver output

---

## Files to Create/Modify

### New Files
- `backend/scripts/populate_preflop_scenarios.py`
- `backend/scripts/normalize_postflop_frequencies.py`
- `backend/services/gto_data_service.py`
- `backend/models/postflop_frequency_models.py`

### Modified Files
- `backend/services/stats_calculator.py` - Use GTODataService
- `backend/services/gto_service.py` - Use database queries
- `backend/main.py` - Add new endpoints if needed
- `frontend/src/types.ts` - Add GTO source fields
- `frontend/src/pages/PlayerProfile.tsx` - Show GTO source

### Deprecated Files
- `backend/services/gto_baselines.py` - To be removed after migration

---

## Risk Mitigation

1. **Insufficient Data**: If solver data is incomplete
   - Fallback: Keep gto_baselines.py as last resort with clear warning
   - Solution: Run more solver scenarios

2. **Performance**: 110k+ frequency records
   - Solution: Add proper indexes, consider caching

3. **Accuracy**: Solver settings may vary
   - Solution: Standardize solver config (iterations, accuracy)
   - Document which solver settings were used

---

## Questions to Resolve

1. Do we have preflop solver data, or only ranges from GTOWizard?
2. Should we run TexasSolver for preflop scenarios?
3. What's the minimum sample of postflop boards per category?
4. Do we need different baselines for different stack depths?
