# Poker Analysis App - Complete Project Plan

## Project Overview

Build a cloud-based mobile-responsive poker analysis application that:
1. Parses poker hand history `.txt` files (PokerStars format)
2. Stores hands in a PostgreSQL cloud database
3. Calculates 12+ advanced statistical models for exploitative poker strategy
4. Integrates Claude AI with direct database access for natural language queries
5. Provides a web interface for deep research and strategic analysis

**Key Principle**: This is NOT a real-time tool. This is a research and analysis platform where users can ask Claude ANY question about their poker database and get sophisticated statistical analysis and strategic recommendations.

---

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI (REST API)
- **Database**: PostgreSQL (cloud-hosted: Supabase/Railway/AWS RDS)
- **ORM**: SQLAlchemy
- **Cloud Deployment**: Railway/Render/Heroku

### Hand History Parser
- **Custom Python parser** for PokerStars `.txt` format
- **Regex-based extraction** of players, positions, actions, amounts, pot sizes

### Frontend
- **Framework**: React 18+ with Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui or Material-UI
- **Charts**: Recharts or Chart.js
- **Hosting**: Vercel/Netlify

### AI Integration
- **Claude API**: Anthropic API (claude-sonnet-4-20250514)
- **Access**: Claude has direct PostgreSQL query access via SQL
- **System Prompt**: Comprehensive poker analyst with database access

---

## Database Schema

### Table 1: `raw_hands`
Stores complete hand history text for reference and audit trail.

```sql
CREATE TABLE raw_hands (
    hand_id BIGINT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    table_name VARCHAR(255),
    stake_level VARCHAR(50),          -- 'NL50', 'NL100', etc.
    game_type VARCHAR(50),             -- '6-max', '9-max', 'heads-up'
    raw_hand_text TEXT,                -- Complete original hand history
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_hands_timestamp ON raw_hands(timestamp);
CREATE INDEX idx_raw_hands_stake ON raw_hands(stake_level);
```

### Table 2: `hand_actions`
Every single action in every hand for granular analysis.

```sql
CREATE TABLE hand_actions (
    action_id SERIAL PRIMARY KEY,
    hand_id BIGINT REFERENCES raw_hands(hand_id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    position VARCHAR(10),              -- 'BTN', 'SB', 'BB', 'UTG', 'MP', 'CO', 'HJ'
    street VARCHAR(10),                -- 'preflop', 'flop', 'turn', 'river'
    action_type VARCHAR(20),           -- 'fold', 'call', 'raise', 'check', 'bet', 'all-in'
    amount DECIMAL(10,2),              -- Amount of bet/raise/call
    pot_size_before DECIMAL(10,2),
    pot_size_after DECIMAL(10,2),
    is_aggressive BOOLEAN,             -- TRUE if raise/bet
    facing_bet BOOLEAN,                -- TRUE if action was in response to a bet
    stack_size DECIMAL(10,2),          -- Player's stack before action
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_hand_actions_player ON hand_actions(player_name);
CREATE INDEX idx_hand_actions_hand ON hand_actions(hand_id);
CREATE INDEX idx_hand_actions_street ON hand_actions(street);
CREATE INDEX idx_hand_actions_position ON hand_actions(position);
```

### Table 3: `player_hand_summary`
Per-player per-hand boolean flags for efficient stat calculation.

```sql
CREATE TABLE player_hand_summary (
    summary_id SERIAL PRIMARY KEY,
    hand_id BIGINT REFERENCES raw_hands(hand_id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    position VARCHAR(10),
    
    -- Preflop flags
    vpip BOOLEAN DEFAULT FALSE,                    -- Voluntarily put $ in pot
    pfr BOOLEAN DEFAULT FALSE,                     -- Raised preflop
    limp BOOLEAN DEFAULT FALSE,                    -- Limped preflop
    faced_raise BOOLEAN DEFAULT FALSE,             -- Faced a preflop raise
    faced_three_bet BOOLEAN DEFAULT FALSE,
    folded_to_three_bet BOOLEAN DEFAULT FALSE,
    called_three_bet BOOLEAN DEFAULT FALSE,
    made_three_bet BOOLEAN DEFAULT FALSE,
    four_bet BOOLEAN DEFAULT FALSE,
    cold_call BOOLEAN DEFAULT FALSE,               -- Called a raise without investing yet
    squeeze BOOLEAN DEFAULT FALSE,                 -- 3-bet after call(s)
    
    -- Street visibility
    saw_flop BOOLEAN DEFAULT FALSE,
    saw_turn BOOLEAN DEFAULT FALSE,
    saw_river BOOLEAN DEFAULT FALSE,
    
    -- Continuation bet opportunities and actions (as aggressor)
    cbet_opportunity_flop BOOLEAN DEFAULT FALSE,
    cbet_made_flop BOOLEAN DEFAULT FALSE,
    cbet_opportunity_turn BOOLEAN DEFAULT FALSE,
    cbet_made_turn BOOLEAN DEFAULT FALSE,
    cbet_opportunity_river BOOLEAN DEFAULT FALSE,
    cbet_made_river BOOLEAN DEFAULT FALSE,
    
    -- Facing continuation bets
    faced_cbet_flop BOOLEAN DEFAULT FALSE,
    folded_to_cbet_flop BOOLEAN DEFAULT FALSE,
    called_cbet_flop BOOLEAN DEFAULT FALSE,
    raised_cbet_flop BOOLEAN DEFAULT FALSE,
    
    faced_cbet_turn BOOLEAN DEFAULT FALSE,
    folded_to_cbet_turn BOOLEAN DEFAULT FALSE,
    called_cbet_turn BOOLEAN DEFAULT FALSE,
    raised_cbet_turn BOOLEAN DEFAULT FALSE,
    
    faced_cbet_river BOOLEAN DEFAULT FALSE,
    folded_to_cbet_river BOOLEAN DEFAULT FALSE,
    called_cbet_river BOOLEAN DEFAULT FALSE,
    raised_cbet_river BOOLEAN DEFAULT FALSE,
    
    -- Check-raise flags
    check_raise_opportunity_flop BOOLEAN DEFAULT FALSE,
    check_raised_flop BOOLEAN DEFAULT FALSE,
    check_raise_opportunity_turn BOOLEAN DEFAULT FALSE,
    check_raised_turn BOOLEAN DEFAULT FALSE,
    check_raise_opportunity_river BOOLEAN DEFAULT FALSE,
    check_raised_river BOOLEAN DEFAULT FALSE,
    
    -- Donk bets (betting into aggressor)
    donk_bet_flop BOOLEAN DEFAULT FALSE,
    donk_bet_turn BOOLEAN DEFAULT FALSE,
    donk_bet_river BOOLEAN DEFAULT FALSE,
    
    -- Float plays (call flop, bet/raise later when checked to)
    float_flop BOOLEAN DEFAULT FALSE,              -- Called flop cbet, aggressor gave up
    
    -- Steal and blind defense
    steal_attempt BOOLEAN DEFAULT FALSE,           -- Raised first in from CO/BTN/SB
    faced_steal BOOLEAN DEFAULT FALSE,             -- In blinds facing steal
    fold_to_steal BOOLEAN DEFAULT FALSE,
    call_steal BOOLEAN DEFAULT FALSE,
    three_bet_vs_steal BOOLEAN DEFAULT FALSE,
    
    -- Showdown
    went_to_showdown BOOLEAN DEFAULT FALSE,
    won_at_showdown BOOLEAN DEFAULT FALSE,
    showed_bluff BOOLEAN DEFAULT FALSE,            -- Showed losing hand at showdown
    
    -- Hand result
    won_hand BOOLEAN DEFAULT FALSE,
    profit_loss DECIMAL(10,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hand_id, player_name)
);

CREATE INDEX idx_player_summary_player ON player_hand_summary(player_name);
CREATE INDEX idx_player_summary_hand ON player_hand_summary(hand_id);
```

### Table 4: `player_stats`
Pre-calculated traditional statistics updated after each hand upload batch.

```sql
CREATE TABLE player_stats (
    player_name VARCHAR(100) PRIMARY KEY,
    total_hands INT DEFAULT 0,
    
    -- Preflop statistics (percentages 0-100)
    vpip_pct DECIMAL(5,2),                        -- % of hands played voluntarily
    pfr_pct DECIMAL(5,2),                         -- % of hands raised preflop
    limp_pct DECIMAL(5,2),                        -- % of hands limped
    three_bet_pct DECIMAL(5,2),                   -- % of times 3-bet when opportunity
    fold_to_three_bet_pct DECIMAL(5,2),           -- % folded when facing 3-bet
    four_bet_pct DECIMAL(5,2),                    -- % of times 4-bet when facing 3-bet
    cold_call_pct DECIMAL(5,2),                   -- % cold called vs raise
    squeeze_pct DECIMAL(5,2),                     -- % squeezed vs raise + call
    
    -- Positional VPIP (for positional awareness analysis)
    vpip_utg DECIMAL(5,2),
    vpip_hj DECIMAL(5,2),
    vpip_mp DECIMAL(5,2),
    vpip_co DECIMAL(5,2),
    vpip_btn DECIMAL(5,2),
    vpip_sb DECIMAL(5,2),
    vpip_bb DECIMAL(5,2),
    
    -- Steal and blind defense
    steal_attempt_pct DECIMAL(5,2),               -- % attempted steal from late position
    fold_to_steal_pct DECIMAL(5,2),               -- % folded in blinds to steal
    three_bet_vs_steal_pct DECIMAL(5,2),          -- % 3-bet vs steal from blinds
    
    -- Postflop aggression (continuation betting)
    cbet_flop_pct DECIMAL(5,2),                   -- % cbet on flop when opportunity
    cbet_turn_pct DECIMAL(5,2),                   -- % cbet (or barrel) on turn
    cbet_river_pct DECIMAL(5,2),                  -- % cbet (or barrel) on river
    
    -- Postflop defense (facing cbets)
    fold_to_cbet_flop_pct DECIMAL(5,2),           -- % folded to flop cbet
    fold_to_cbet_turn_pct DECIMAL(5,2),           -- % folded to turn cbet
    fold_to_cbet_river_pct DECIMAL(5,2),          -- % folded to river cbet
    
    call_cbet_flop_pct DECIMAL(5,2),              -- % called flop cbet
    call_cbet_turn_pct DECIMAL(5,2),              -- % called turn cbet
    call_cbet_river_pct DECIMAL(5,2),             -- % called river cbet
    
    raise_cbet_flop_pct DECIMAL(5,2),             -- % raised flop cbet
    raise_cbet_turn_pct DECIMAL(5,2),             -- % raised turn cbet
    raise_cbet_river_pct DECIMAL(5,2),            -- % raised river cbet
    
    -- Check-raise frequency
    check_raise_flop_pct DECIMAL(5,2),            -- % check-raised on flop
    check_raise_turn_pct DECIMAL(5,2),            -- % check-raised on turn
    check_raise_river_pct DECIMAL(5,2),           -- % check-raised on river
    
    -- Donk betting
    donk_bet_flop_pct DECIMAL(5,2),
    donk_bet_turn_pct DECIMAL(5,2),
    donk_bet_river_pct DECIMAL(5,2),
    
    -- Float frequency
    float_flop_pct DECIMAL(5,2),                  -- % floated flop and bet later
    
    -- Aggression metrics
    af DECIMAL(5,2),                              -- Aggression Factor: (bet+raise) / call
    afq DECIMAL(5,2),                             -- Aggression Frequency: (bet+raise) / (bet+raise+call+fold)
    
    -- Showdown metrics
    wtsd_pct DECIMAL(5,2),                        -- % Went To ShowDown (of hands that saw flop)
    wsd_pct DECIMAL(5,2),                         -- % Won $ at ShowDown (of showdowns)
    
    -- Win rate
    total_profit_loss DECIMAL(12,2),              -- Total profit/loss in BB
    bb_per_100 DECIMAL(8,2),                      -- Big blinds won per 100 hands
    
    -- Composite Metrics (calculated and stored for query performance)
    exploitability_index DECIMAL(5,2),            -- 0-100 overall exploitability
    pressure_vulnerability_score DECIMAL(5,2),    -- 0-100 fold frequency under pressure
    aggression_consistency_ratio DECIMAL(5,2),    -- 0-2 give-up tendency
    positional_awareness_index DECIMAL(5,2),      -- 0-150 position-specific play quality
    blind_defense_efficiency DECIMAL(5,2),        -- 0-100 blind defense quality
    value_bluff_imbalance_ratio DECIMAL(5,2),     -- -3 to +3 showdown value vs bluff balance
    range_polarization_factor DECIMAL(5,2),       -- 0-3 bet sizing and range construction
    street_fold_gradient DECIMAL(5,2),            -- -20 to +30 folding pattern changes
    delayed_aggression_coefficient DECIMAL(5,2),  -- 0-50 check-raise and trap frequency
    multi_street_persistence_score DECIMAL(5,2),  -- 0-100 commitment across streets
    optimal_stake_skill_rating DECIMAL(5,2),      -- 0-100 skill vs stake match
    player_type VARCHAR(20),                      -- QEM: 'NIT', 'TAG', 'LAG', 'CALLING_STATION', 'MANIAC', 'FISH'
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_hand_date TIMESTAMP,
    last_hand_date TIMESTAMP
);

CREATE INDEX idx_player_stats_hands ON player_stats(total_hands);
CREATE INDEX idx_player_stats_vpip ON player_stats(vpip_pct);
CREATE INDEX idx_player_stats_pfr ON player_stats(pfr_pct);
CREATE INDEX idx_player_stats_ei ON player_stats(exploitability_index);
CREATE INDEX idx_player_stats_pvs ON player_stats(pressure_vulnerability_score);
CREATE INDEX idx_player_stats_type ON player_stats(player_type);
```

### Table 5: `upload_sessions`
Track hand history file uploads for audit and debugging.

```sql
CREATE TABLE upload_sessions (
    session_id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hands_parsed INT DEFAULT 0,
    hands_failed INT DEFAULT 0,
    players_updated INT DEFAULT 0,
    stake_level VARCHAR(50),
    status VARCHAR(50) DEFAULT 'processing',      -- 'processing', 'completed', 'failed'
    error_message TEXT,
    processing_time_seconds INT
);

CREATE INDEX idx_upload_sessions_timestamp ON upload_sessions(upload_timestamp);
```

---

## 12 Composite Statistical Models

These models are **calculated and stored in the `player_stats` table** for query performance and flexibility. They are updated whenever player statistics are recalculated (after uploading new hand histories).

**Why store them in the database?**
1. **Performance**: No need to recalculate on every query - instant lookups
2. **Query flexibility**: Claude can filter/sort by any metric (e.g., `WHERE exploitability_index > 70`)
3. **Indexing**: Fast queries with indexes on composite metrics
4. **Consistency**: All queries see the same values
5. **Simplicity**: Single source of truth for all statistics

**Update workflow**: Parse hands → Calculate traditional stats → Calculate composite metrics → Store all in player_stats table

### 1. Exploitability Index (EI)
**Purpose**: Overall measure of how exploitable a player is (0-100 scale)

**Formula**:
```
EI = (Preflop_Score × 0.35) + (Postflop_Score × 0.40) + (Showdown_Score × 0.25)

Where:
Preflop_Score = |VPIP/PFR Gap - 3| × 2 + |Fold to 3bet - 55| × 0.5 + |3bet% - 7| × 1.5

Postflop_Score = |Flop Cbet - Turn Cbet| × 1.5 + |Fold to Cbet Flop - 55| × 0.8 + |Check-raise Flop - 5| × 2

Showdown_Score = |WTSD - 27| × 1.2 + |W$SD - 51| × 0.8
```

**Interpretation**:
- 0-20: Solid regular, minimal exploits
- 20-40: Competent with specific leaks
- 40-60: Moderately exploitable
- 60-80: Highly exploitable (prime target)
- 80-100: Extreme fish (max value extraction)

**Minimum Sample**: 200 hands preliminary, 500 hands confident

---

### 2. Pressure Vulnerability Score (PVS)
**Purpose**: Measures susceptibility to aggressive pressure across all streets

**Formula**:
```
PVS = (Fold to 3bet × 0.25) + 
      (Fold to Flop Cbet × 0.20) + 
      (Fold to Turn Cbet × 0.25) + 
      (Fold to River Bet × 0.30)
```

**Weighted by street** because later streets = more chips committed = higher fold value

**Interpretation**:
- PVS > 65: Hyper-bluffable (attack relentlessly)
- PVS 55-65: Above-average fold frequency (increase bluffing)
- PVS 45-55: Balanced (standard approach)
- PVS 35-45: Calling tendencies (reduce bluffs, thin value bet)
- PVS < 35: Calling station (never bluff)

**Minimum Sample**: 300 hands

---

### 3. Aggression Consistency Ratio (ACR)
**Purpose**: Identifies players who start aggressive but surrender on later streets

**Formula**:
```
ACR = (Turn Cbet % / Flop Cbet %) × (River Cbet % / Turn Cbet %)

Perfect consistency = 1.0
```

**Interpretation**:
- ACR 0.80-1.20: Consistent aggression (balanced)
- ACR 0.50-0.79: Moderate give-up tendency (float flop, attack turn)
- ACR 0.30-0.49: High give-up frequency (call flop liberally, bet turn)
- ACR < 0.30: Extreme fit-or-fold (float with air, fire turn/river)

**Example**:
Player cbets 70% flop, 35% turn, 25% river
```
ACR = (35/70) × (25/35) = 0.50 × 0.71 = 0.355
```
**Exploit**: Float flop with any equity, bet when they check turn

**Minimum Sample**: 250 hands

---

### 4. Positional Awareness Index (PAI)
**Purpose**: Measures how well a player adjusts their play by position

**Formula**:
```
PAI_Score = Σ |Position_VPIP - Optimal_VPIP| for all positions

Optimal VPIP ranges:
- UTG: 13-18%
- HJ: 17-22%
- MP: 17-22%
- CO: 25-30%
- BTN: 43-51%
- SB: 30-36%
- BB: 35-42%
```

**Lower score = better positional awareness**

**Interpretation**:
- PAI < 15: Excellent positional awareness
- PAI 15-30: Good awareness
- PAI 30-50: Poor awareness (exploitable)
- PAI > 50: No positional awareness (major leak)

**Exploit**: Against high PAI players, attack their positional weaknesses (e.g., steal vs tight UTG)

**Minimum Sample**: 500 hands (need position-specific stats)

---

### 5. Blind Defense Efficiency (BDE)
**Purpose**: Measures quality of blind defense vs steals

**Formula**:
```
BDE = (BB VPIP × 0.4) + ((100 - Fold to Steal) × 0.3) + (BB 3bet % × 0.3)

Optimal BDE: 40-50
```

**Interpretation**:
- BDE < 30: Over-folding blinds (increase steal frequency)
- BDE 40-50: Balanced blind defense
- BDE > 60: Over-defending blinds (decrease steal attempts, value bet thinner)

**Minimum Sample**: 200 hands from blinds

---

### 6. Value-Bluff Imbalance Ratio (VBIR)
**Purpose**: Identifies showdown value vs bluffing balance

**Formula**:
```
VBIR = (W$SD - 50) / (WTSD - 27)

Optimal: -0.5 to +0.5
```

**Interpretation**:
- VBIR > +1.0: Too value-heavy, rarely bluffs (don't pay them off)
- VBIR +0.5 to +1.0: Slightly value-heavy (lean toward folding)
- VBIR -0.5 to +0.5: Balanced
- VBIR -1.0 to -0.5: Slightly bluff-heavy (call down lighter)
- VBIR < -1.0: Maniac (hero call exploitably)

**Minimum Sample**: 1000 hands

---

### 7. Range Polarization Factor (RPF)
**Purpose**: Measures bet sizing and range construction

**Formula**:
```
RPF = (Average Bet Size / Pot Size) × (River Bet Frequency / Flop Bet Frequency)
```

**Requires**: Bet sizing data from hand_actions table

**Interpretation**:
- RPF > 1.5: Highly polarized (big bets, merged range vulnerable)
- RPF 0.8-1.5: Balanced
- RPF < 0.8: Merged range (unclear value/bluff distinction)

**Minimum Sample**: 500 hands

---

### 8. Street-by-Street Fold Gradient (SFG)
**Purpose**: Measures how folding frequency changes across streets

**Formula**:
```
SFG = [(Fold to Flop Cbet - Fold to Turn Cbet) + 
       (Fold to Turn Cbet - Fold to River Cbet)] / 2
```

**Interpretation**:
- SFG > 15: Large fold gradient (multi-barrel profitable)
- SFG 5-15: Moderate gradient (selective barreling)
- SFG < 5: Flat gradient (single street bluffs only)
- SFG < 0: Negative gradient (trap player, careful with bluffs)

**Minimum Sample**: 500 hands

---

### 9. Delayed Aggression Coefficient (DAC)
**Purpose**: Measures check-raise and trap play frequency

**Formula**:
```
DAC = (Check-raise Flop % × 2) + (Check-raise Turn % × 1.5) + (Float % × 1)

Optimal: 8-15
```

**Interpretation**:
- DAC < 5: Rarely traps (cbet profitably)
- DAC 8-15: Balanced
- DAC > 20: Over-trapping (bet smaller, check back more)

**Minimum Sample**: 500 hands

---

### 10. Quick Exploit Matrix (QEM)
**Purpose**: Rapid player type classification for immediate exploitation

**Classification Rules**:
```
Based on VPIP/PFR and gap:

NIT: VPIP < 15%, PFR < 12%
  → Exploit: Steal relentlessly, fold to their aggression

TAG (Tight-Aggressive): VPIP 15-25%, PFR 12-20%, Gap < 5
  → Exploit: Play straightforward, avoid marginal spots

LAG (Loose-Aggressive): VPIP 25-35%, PFR 18-28%, Gap < 7
  → Exploit: Call down lighter, trap with strong hands

CALLING STATION: VPIP > 35%, Gap > 15
  → Exploit: Value bet thin, never bluff

MANIAC: VPIP > 45%, PFR > 35%
  → Exploit: Hero call, trap with monsters

FISH: Any player with EI > 60
  → Exploit: Maximally exploit primary leak
```

**Minimum Sample**: 20-50 hands (preliminary only)

---

### 11. Multi-Street Persistence Score (MPS)
**Purpose**: Measures commitment level across betting streets

**Formula**:
```
MPS = [(% of flop cbets that reach turn bet) + 
       (% of turn bets that reach river bet) + 
       (% of check-calls that reach showdown)] / 3

Optimal: 55-65%
```

**Interpretation**:
- MPS > 75%: High persistence (don't bluff, they won't fold)
- MPS 65-75%: Above-average commitment (thin value bet)
- MPS 55-65%: Balanced
- MPS 40-55%: Quick surrender (float and attack)
- MPS < 40%: Extreme give-up (aggressive turn/river play)

**Minimum Sample**: 350 hands

---

### 12. Optimal Stake Threshold Model
**Purpose**: Determines when a player's skill level matches their stake

**Formula**:
```
Skill_Rating = (100 - EI) + (PAI Score × -5) + (BDE - 30) + (|W$SD - 51| × -2)

Recommended Stakes:
- Skill < 30: NL2
- Skill 30-45: NL10
- Skill 45-60: NL25
- Skill 60-70: NL50
- Skill > 70: NL100+
```

**Application**: Identify players playing above their statistical skill level (highly exploitable through pressure)

**Minimum Sample**: 1000 hands

---

## Sample Size Requirements Summary

| Hands | Metrics Available | Reliability |
|-------|------------------|-------------|
| 20-50 | QEM only | Preliminary |
| 100-300 | EI, PVS, BDE, ACR | Moderate |
| 500+ | PAI, RPF, DAC, MPS, SFG | High |
| 1000+ | VBIR, Optimal Stake | Very High |

---

## Core Components to Build

### Component 1: Hand History Parser

**File**: `backend/parser/pokerstars_parser.py`

**Requirements**:
- Parse PokerStars `.txt` hand history format
- Extract: hand ID, timestamp, table name, stakes, player names, positions, stacks, actions, amounts, pot sizes
- Handle multi-street actions (preflop/flop/turn/river)
- Identify action types: fold, call, raise, bet, check, all-in
- Calculate boolean flags for `player_hand_summary` table
- Handle edge cases: all-ins, side pots, uncalled bets, partial showdowns

**Key Functions**:
```python
def parse_hand_history_file(file_path: str) -> List[Hand]:
    """
    Parse entire .txt file containing multiple hands.
    Returns list of Hand objects.
    """
    
def extract_hand_metadata(hand_text: str) -> dict:
    """
    Extract hand ID, timestamp, table name, stake level, game type.
    Returns: {hand_id, timestamp, table_name, stake_level, game_type}
    """
    
def extract_players_and_positions(hand_text: str) -> dict:
    """
    Map player names to positions and starting stacks.
    Returns: {player_name: {position, stack}}
    """
    
def parse_preflop_actions(hand_text: str) -> List[Action]:
    """
    Extract all preflop actions with amounts and pot sizes.
    """
    
def parse_postflop_actions(hand_text: str, street: str) -> List[Action]:
    """
    Extract actions for flop/turn/river.
    """
    
def identify_preflop_aggressor(actions: List[Action]) -> str:
    """
    Identify who was the last aggressor preflop (for cbet opportunities).
    """
    
def calculate_player_flags(hand: Hand) -> dict:
    """
    Calculate all boolean flags for player_hand_summary.
    Returns: {player_name: {vpip, pfr, cbet_opportunity_flop, ...}}
    """
    
def calculate_profit_loss(hand: Hand) -> dict:
    """
    Calculate profit/loss for each player.
    Returns: {player_name: profit_loss_amount}
    """
```

**Example PokerStars Format**:
```
PokerStars Hand #123456789012: Hold'em No Limit ($0.25/$0.50 USD) - 2025/11/17 10:30:15 ET
Table 'Andromeda V' 6-max Seat #1 is the button
Seat 1: Player1 ($50.00 in chips)
Seat 2: Player2 ($75.50 in chips)
Seat 3: Player3 ($100.00 in chips)
Seat 4: Player4 ($62.25 in chips)
Seat 5: Player5 ($88.75 in chips)
Seat 6: Player6 ($55.00 in chips)
Player2: posts small blind $0.25
Player3: posts big blind $0.50
*** HOLE CARDS ***
Player4: folds
Player5: folds
Player6: raises $1.50 to $2.00
Player1: folds
Player2: folds
Player3: calls $1.50
*** FLOP *** [Ah 7c 3d]
Player3: checks
Player6: bets $3.00
Player3: calls $3.00
*** TURN *** [Ah 7c 3d] [Ks]
Player3: checks
Player6: bets $7.50
Player3: folds
Uncalled bet ($7.50) returned to Player6
Player6 collected $9.75 from pot
Player6: doesn't show hand
*** SUMMARY ***
Total pot $10.25 | Rake $0.50
Board [Ah 7c 3d Ks]
Seat 1: Player1 (button) folded before Flop (didn't bet)
Seat 2: Player2 (small blind) folded before Flop
Seat 3: Player3 (big blind) folded on the Turn
Seat 4: Player4 folded before Flop (didn't bet)
Seat 5: Player5 folded before Flop (didn't bet)
Seat 6: Player6 collected ($9.75)
```

**Edge Cases to Handle**:
- Multiple players all-in
- Side pots
- Uncalled bets
- Players sitting out
- Rabbit hunting (running it multiple times)
- Partial showdowns (not all cards shown)

---

### Component 2: Database Service

**File**: `backend/services/database_service.py`

**Requirements**:
- SQLAlchemy models for all 5 tables
- CRUD operations for inserting hands and querying stats
- Batch insert optimization for large hand history files
- Transaction management to ensure data consistency
- Aggregation queries to calculate percentages from boolean flags

**Key Functions**:
```python
async def insert_hand_batch(hands: List[Hand]) -> dict:
    """
    Insert multiple hands atomically.
    Returns: {hands_inserted, hands_failed, error_details}
    """
    
async def update_player_stats(player_name: str):
    """
    Recalculate aggregated stats for a single player from player_hand_summary.
    
    Process:
    1. Calculate all traditional statistics (VPIP%, PFR%, etc.) from player_hand_summary
    2. Calculate all 12 composite metrics using stats_calculator
    3. Update player_stats table with both traditional stats AND composite metrics
    
    This ensures metrics are always stored and queryable.
    """
    
async def update_all_player_stats():
    """
    Recalculate stats for all players (run after batch upload).
    """
    
async def get_player_stats(player_name: str) -> dict:
    """
    Retrieve all traditional stats for a player.
    Returns dict with all fields from player_stats table.
    """
    
async def get_all_players(
    min_hands: int = 100, 
    stake_level: str = None,
    order_by: str = 'total_hands'
) -> List[dict]:
    """
    Get all players matching criteria.
    """
    
async def execute_custom_query(sql: str) -> List[dict]:
    """
    Execute arbitrary SQL query (for Claude's use).
    Returns query results as list of dicts.
    """
    
async def get_database_stats() -> dict:
    """
    Get overview stats: total hands, total players, stake breakdown, date range.
    """
```

**Aggregation Example**:
```python
# Calculate VPIP% for a player
vpip_pct = (
    SELECT 
        (COUNT(*) FILTER (WHERE vpip = TRUE)::float / COUNT(*)) * 100 
    FROM player_hand_summary 
    WHERE player_name = 'Player_X'
)
```

---

### Component 3: Statistical Calculator

**File**: `backend/services/stats_calculator.py`

**Requirements**:
- Implement all 12 composite metric formulas exactly as specified
- Input: player_stats dictionary (traditional stats)
- Output: calculated metrics that are stored back in the database
- Handle edge cases (division by zero, insufficient data)
- Return confidence/reliability based on sample size
- **These metrics are STORED in player_stats table, not calculated on-the-fly**

**Key Functions**:
```python
def calculate_exploitability_index(stats: dict) -> dict:
    """
    Calculate EI from player stats.
    Returns: {
        'ei': float (0-100),
        'preflop_score': float,
        'postflop_score': float,
        'showdown_score': float,
        'interpretation': str,
        'reliability': str
    }
    """
    
def calculate_pressure_vulnerability_score(stats: dict) -> dict:
    """
    Calculate PVS from fold frequencies.
    Returns: {
        'pvs': float (0-100),
        'interpretation': str,
        'exploit_recommendation': str
    }
    """
    
def calculate_aggression_consistency_ratio(stats: dict) -> dict:
    """
    Calculate ACR from cbet frequencies.
    Returns: {
        'acr': float,
        'interpretation': str,
        'exploit_recommendation': str
    }
    """
    
def calculate_positional_awareness_index(stats: dict) -> dict:
    """
    Calculate PAI from position-specific VPIP.
    Returns: {
        'pai': float,
        'position_deviations': dict,
        'interpretation': str
    }
    """

def calculate_all_metrics(stats: dict) -> dict:
    """
    Calculate all 12 composite metrics at once.
    Returns dict with all metrics ready to be stored in database.
    {
        'exploitability_index': float,
        'pressure_vulnerability_score': float,
        'aggression_consistency_ratio': float,
        'positional_awareness_index': float,
        'blind_defense_efficiency': float,
        'value_bluff_imbalance_ratio': float,
        'range_polarization_factor': float,
        'street_fold_gradient': float,
        'delayed_aggression_coefficient': float,
        'multi_street_persistence_score': float,
        'optimal_stake_skill_rating': float,
        'player_type': str
    }
    """
    
def classify_player_type(stats: dict) -> str:
    """
    Use QEM to classify player type.
    Returns: 'NIT', 'TAG', 'LAG', 'CALLING_STATION', 'MANIAC', or 'FISH'
    """

def get_sample_size_reliability(total_hands: int, metric: str) -> str:
    """
    Return reliability level based on sample size requirements.
    Returns: 'insufficient', 'preliminary', 'moderate', 'high', 'very_high'
    """
```

**Implementation Notes**:
- All percentage inputs should be 0-100 format (not 0-1)
- Handle None/null values gracefully (return None for that metric)
- Return None for metrics with insufficient data
- These calculated values are immediately stored in `player_stats` table
- No need to recalculate on every query - just read from database

---

### Component 4: FastAPI Backend

**File**: `backend/main.py`

**Endpoints**:

```python
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Poker Analysis API")

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_hand_history(file: UploadFile):
    """
    Accept .txt file upload containing poker hand histories.
    
    Process:
    1. Save uploaded file temporarily
    2. Parse all hands using pokerstars_parser
    3. Insert hands into database (raw_hands, hand_actions, player_hand_summary)
    4. Update aggregated player_stats
    5. Create upload_session record
    
    Returns: {
        'session_id': int,
        'hands_parsed': int,
        'hands_failed': int,
        'players_updated': int,
        'stake_level': str,
        'processing_time': float
    }
    """

@app.get("/api/players")
async def get_all_players(
    min_hands: int = 100,
    stake_level: str = None,
    sort_by: str = 'total_hands',
    limit: int = 100
):
    """
    Get all players with optional filtering.
    
    Returns: [{
        'player_name': str,
        'total_hands': int,
        'vpip_pct': float,
        'pfr_pct': float,
        'three_bet_pct': float,
        'af': float,
        'wtsd_pct': float,
        'wsd_pct': float,
        'bb_per_100': float,
        ...
    }]
    """

@app.get("/api/players/{player_name}")
async def get_player_profile(player_name: str):
    """
    Get complete player profile with all stats and composite metrics.
    
    Process:
    1. Query player_stats for player (includes traditional stats AND composite metrics)
    2. All metrics are pre-calculated and stored, so this is a fast lookup
    3. Return complete profile with interpretations
    
    Returns: {
        'player_name': str,
        'total_hands': int,
        'sample_reliability': str,
        'traditional_stats': {
            'vpip_pct': float,
            'pfr_pct': float,
            ...
        },
        'composite_metrics': {
            'exploitability_index': float,
            'pressure_vulnerability_score': float,
            'aggression_consistency_ratio': float,
            ... all 12 metrics
        },
        'player_classification': {
            'type': str,  # from player_type column
            'description': str,
            'primary_exploits': [...]  # generated from metrics
        }
    }
    """

@app.post("/api/query/claude")
async def query_with_claude(request: dict):
    """
    Send natural language query to Claude for database analysis.
    
    Request body: {
        'query': str (user's natural language question)
    }
    
    Process:
    1. Send query to Claude API with system prompt and database schema
    2. Claude may execute SQL queries via database_service
    3. Claude analyzes results and generates response
    
    Returns: {
        'response': str (Claude's analysis in markdown),
        'sql_queries': List[str] (queries executed, for transparency),
        'data': dict (relevant data Claude used)
    }
    """

@app.get("/api/database/schema")
async def get_database_schema():
    """
    Return complete database schema for Claude.
    Used by Claude to understand available tables and columns.
    
    Returns: {
        'tables': {
            'table_name': {
                'columns': [...],
                'description': str,
                'row_count': int
            }
        }
    }
    """

@app.get("/api/database/stats")
async def get_database_stats():
    """
    Get overview statistics about the database.
    
    Returns: {
        'total_hands': int,
        'total_players': int,
        'stake_levels': {
            'NL50': {'hands': int, 'players': int},
            'NL100': {...},
            ...
        },
        'date_range': {
            'first_hand': datetime,
            'last_hand': datetime
        },
        'recent_uploads': [{...}]
    }
    """

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    Returns: {'status': 'healthy', 'database': 'connected', 'timestamp': datetime}
    """
```

---

### Component 5: Claude Integration

**File**: `backend/services/claude_service.py`

**System Prompt**:
```python
CLAUDE_SYSTEM_PROMPT = """
You are an elite poker analyst with PhD-level statistical expertise. You have 
direct SQL access to a comprehensive poker hand history PostgreSQL database.

You can answer ANY question about this database - from simple lookups to complex 
multi-table research queries. There are no restrictions on what you can query or 
analyze.

DATABASE CONNECTION:
{database_connection_details}

DATABASE SCHEMA:

Table: raw_hands
- hand_id (BIGINT, PRIMARY KEY): Unique hand identifier
- timestamp (TIMESTAMP): When hand was played
- table_name (VARCHAR): Table name
- stake_level (VARCHAR): e.g., 'NL50', 'NL100'
- game_type (VARCHAR): e.g., '6-max', '9-max'
- raw_hand_text (TEXT): Complete original hand history
- created_at (TIMESTAMP): When inserted into database

Table: hand_actions
- action_id (SERIAL, PRIMARY KEY)
- hand_id (BIGINT, FOREIGN KEY): References raw_hands
- player_name (VARCHAR)
- position (VARCHAR): 'BTN', 'SB', 'BB', 'UTG', 'MP', 'CO', 'HJ'
- street (VARCHAR): 'preflop', 'flop', 'turn', 'river'
- action_type (VARCHAR): 'fold', 'call', 'raise', 'check', 'bet', 'all-in'
- amount (DECIMAL): Bet/raise/call amount
- pot_size_before (DECIMAL)
- pot_size_after (DECIMAL)
- is_aggressive (BOOLEAN): TRUE if raise/bet
- facing_bet (BOOLEAN): TRUE if facing a bet
- stack_size (DECIMAL): Stack before action

Table: player_hand_summary
- summary_id (SERIAL, PRIMARY KEY)
- hand_id (BIGINT, FOREIGN KEY)
- player_name (VARCHAR)
- position (VARCHAR)
- [50+ boolean flags for vpip, pfr, cbet opportunities, folds, etc.]
- profit_loss (DECIMAL): Result for this hand

Table: player_stats
- player_name (VARCHAR, PRIMARY KEY)
- total_hands (INT)
- [100+ percentage statistics covering preflop, postflop, aggression, showdown]
- [12 composite metrics - STORED in database]:
  - exploitability_index (DECIMAL): 0-100 overall exploitability
  - pressure_vulnerability_score (DECIMAL): 0-100 fold frequency under pressure
  - aggression_consistency_ratio (DECIMAL): 0-2 give-up tendency
  - positional_awareness_index (DECIMAL): 0-150 position-specific play quality
  - blind_defense_efficiency (DECIMAL): 0-100 blind defense quality
  - value_bluff_imbalance_ratio (DECIMAL): -3 to +3 showdown balance
  - range_polarization_factor (DECIMAL): 0-3 bet sizing patterns
  - street_fold_gradient (DECIMAL): -20 to +30 folding changes
  - delayed_aggression_coefficient (DECIMAL): 0-50 trap frequency
  - multi_street_persistence_score (DECIMAL): 0-100 commitment level
  - optimal_stake_skill_rating (DECIMAL): 0-100 skill rating
  - player_type (VARCHAR): 'NIT', 'TAG', 'LAG', 'CALLING_STATION', 'MANIAC', 'FISH'
- last_updated (TIMESTAMP)

Table: upload_sessions
- session_id (SERIAL, PRIMARY KEY)
- filename (VARCHAR)
- upload_timestamp (TIMESTAMP)
- hands_parsed (INT)
- status (VARCHAR)

AVAILABLE TOOLS:
- You can execute any SQL query via the database_service
- Full read access to all tables
- Perform joins, aggregations, window functions, CTEs, subqueries, etc.
- No write access (read-only for safety)

STATISTICAL MODELS (REFERENCE):

All composite metrics are **pre-calculated and stored in the player_stats table**. 
You can query them directly without recalculation:

```sql
SELECT player_name, exploitability_index, player_type 
FROM player_stats 
WHERE exploitability_index > 70 
ORDER BY exploitability_index DESC;
```

Here are the formulas and interpretations for reference:

1. **Exploitability Index (EI)**: Overall exploitability (0-100)
   Formula: (Preflop_Score × 0.35) + (Postflop_Score × 0.40) + (Showdown_Score × 0.25)
   Where:
   - Preflop_Score = |VPIP/PFR Gap - 3| × 2 + |Fold to 3bet - 55| × 0.5 + |3bet% - 7| × 1.5
   - Postflop_Score = |Flop Cbet - Turn Cbet| × 1.5 + |Fold to Cbet Flop - 55| × 0.8 + |Check-raise Flop - 5| × 2
   - Showdown_Score = |WTSD - 27| × 1.2 + |W$SD - 51| × 0.8
   Interpretation: 0-20 solid reg, 20-40 competent, 40-60 exploitable, 60-80 highly exploitable, 80-100 extreme fish

2. **Pressure Vulnerability Score (PVS)**: Fold frequency under pressure
   Formula: (Fold 3bet × 0.25) + (Fold Flop Cbet × 0.20) + (Fold Turn × 0.25) + (Fold River × 0.30)
   Interpretation: >65 hyper-bluffable, 55-65 above avg folds, 45-55 balanced, 35-45 calling tendency, <35 calling station

3. **Aggression Consistency Ratio (ACR)**: Give-up tendency
   Formula: (Turn Cbet / Flop Cbet) × (River Cbet / Turn Cbet)
   Interpretation: 0.8-1.2 consistent, 0.5-0.79 moderate give-up (float and attack), <0.5 high give-up

4. **Positional Awareness Index (PAI)**: Position-specific play quality
   Formula: Σ |Position_VPIP - Optimal_VPIP|
   Optimal: UTG 13-18%, HJ/MP 17-22%, CO 25-30%, BTN 43-51%, SB 30-36%, BB 35-42%
   Interpretation: <15 excellent, 15-30 good, 30-50 poor, >50 no awareness

5. **Blind Defense Efficiency (BDE)**: Quality of blind defense
   Formula: (BB VPIP × 0.4) + ((100 - Fold to Steal) × 0.3) + (BB 3bet × 0.3)
   Interpretation: <30 over-folding (increase steals), 40-50 optimal, >60 over-defending (value bet thin)

6. **Value-Bluff Imbalance Ratio (VBIR)**: Showdown value vs bluff balance
   Formula: (W$SD - 50) / (WTSD - 27)
   Interpretation: >+1 too value-heavy, -0.5 to +0.5 balanced, <-1 maniac (hero call)

7. **Range Polarization Factor (RPF)**: Bet sizing and range construction
   Formula: (Avg Bet Size / Pot) × (River Bet Freq / Flop Bet Freq)
   Interpretation: >1.5 highly polarized, 0.8-1.5 balanced, <0.8 merged

8. **Street-by-Street Fold Gradient (SFG)**: Folding pattern changes
   Formula: [(Fold Flop - Fold Turn) + (Fold Turn - Fold River)] / 2
   Interpretation: >15 multi-barrel profitable, 5-15 selective barrel, <5 single street only, <0 trap player

9. **Delayed Aggression Coefficient (DAC)**: Check-raise and trap frequency
   Formula: (CR Flop × 2) + (CR Turn × 1.5) + (Float × 1)
   Interpretation: <5 rarely traps (cbet profitable), 8-15 balanced, >20 over-trapping

10. **Quick Exploit Matrix (QEM)**: Player type classification
    NIT: VPIP<15%, PFR<12% | TAG: VPIP 15-25%, PFR 12-20%, Gap<5
    LAG: VPIP 25-35%, PFR 18-28%, Gap<7 | CALLING STATION: VPIP>35%, Gap>15
    MANIAC: VPIP>45%, PFR>35% | FISH: EI>60

11. **Multi-Street Persistence Score (MPS)**: Commitment across streets
    Formula: [(% flop→turn) + (% turn→river) + (% check-call→showdown)] / 3
    Interpretation: >75% high persistence (don't bluff), 55-65% balanced, <40% extreme give-up

12. **Optimal Stake Threshold**: Skill vs stake mismatch
    Formula: Skill = (100-EI) + (PAI×-5) + (BDE-30) + (|W$SD-51|×-2)
    Stakes: <30=NL2, 30-45=NL10, 45-60=NL25, 60-70=NL50, >70=NL100+

SAMPLE SIZE REQUIREMENTS:
- 20-50 hands: QEM classification only (preliminary)
- 100-300 hands: EI, PVS, BDE, ACR (moderate confidence)
- 500+ hands: PAI, RPF, DAC, MPS, SFG (high confidence)
- 1000+ hands: VBIR, Optimal Stake (very high confidence)

YOUR APPROACH:
1. Understand what the user is asking
2. Write and execute SQL queries to gather necessary data
3. Calculate relevant composite metrics if needed for the analysis
4. Analyze the results with statistical rigor
5. Answer the question clearly and directly
6. Provide specific, actionable insights when asked for strategy
7. Always consider sample size reliability
8. If data is insufficient, state this clearly
9. Show your SQL queries for transparency

RESPONSE STYLE:
- Adapt to the query complexity (simple question = concise answer, research = detailed)
- Use tables/lists when presenting multiple players or comparisons
- Calculate metrics only when relevant to the question
- Explain reasoning and statistical significance
- Provide concrete exploit recommendations when asked for strategy
- Format responses in clear markdown

EXAMPLE QUERIES YOU CAN HANDLE:

Simple Lookups:
- "What's Player_X's VPIP?" → SELECT vpip_pct FROM player_stats WHERE player_name = 'Player_X'
- "What's Player_X's Exploitability Index?" → SELECT exploitability_index FROM player_stats WHERE player_name = 'Player_X'
- "How many hands are in the database?" → SELECT SUM(total_hands) FROM player_stats
- "Show me all players from NL50" → SELECT * FROM player_stats WHERE stake_level = 'NL50'

Research & Analysis:
- "Find the 10 most exploitable players" → ORDER BY exploitability_index DESC LIMIT 10
- "Which players fold to 3-bets >70% from blinds?" → WHERE fold_to_three_bet_pct > 70
- "Show all calling stations with 500+ hands" → WHERE player_type = 'CALLING_STATION' AND total_hands >= 500
- "What's the average EI at NL50 vs NL100?" → GROUP BY stake_level, AVG(exploitability_index)
- "Find players with PVS > 65 and ACR < 0.5" → WHERE pressure_vulnerability_score > 65 AND aggression_consistency_ratio < 0.5

Comparative Analysis:
- "Compare population stats across stake levels"
- "How does my database compare to general population tendencies?"
- "What's the biggest leak at each stake?"

Strategic Questions:
- "Who should I target tonight at NL50?"
- "What's the most profitable exploit in my database?"
- "Find 3-betting opportunities against weak players"

Pattern Discovery:
- "What interesting trends can you find?"
- "Which position shows the biggest leaks?"
- "Find unusual statistical patterns"

Time-Based:
- "Show hands from last week"
- "How have stats changed over time?"
- "Compare recent uploads to older data"

Custom Queries:
- "Show all river bluffs that worked"
- "Find spots where I should have 3-bet"
- "Which players float the flop most?"

You have complete freedom to query and analyze however you see fit. Be creative, 
thorough, and always statistically rigorous.
"""
```

**Key Functions**:
```python
import anthropic
import os

async def query_claude(
    user_query: str, 
    database_schema: dict,
    execute_sql_callback: callable
) -> dict:
    """
    Send query to Claude API, handle SQL execution, return response.
    
    Args:
        user_query: Natural language question from user
        database_schema: Current database schema and stats
        execute_sql_callback: Function Claude can call to execute SQL
        
    Returns: {
        'response': str (markdown formatted),
        'sql_queries': List[str],
        'error': str (if any)
    }
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    system_prompt = CLAUDE_SYSTEM_PROMPT.format(
        database_connection_details="PostgreSQL database with full read access",
    )
    
    # Initial message to Claude
    messages = [
        {
            "role": "user",
            "content": f"Database Schema:\n{database_schema}\n\nUser Query: {user_query}"
        }
    ]
    
    # Allow Claude to make multiple tool calls (SQL queries)
    sql_queries_executed = []
    
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=system_prompt,
            messages=messages,
            tools=[
                {
                    "name": "execute_sql_query",
                    "description": "Execute a SQL query against the poker database. Returns query results as JSON.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The SQL query to execute (SELECT only)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        )
        
        # Check if Claude wants to execute SQL
        if response.stop_reason == "tool_use":
            tool_use = next(block for block in response.content if block.type == "tool_use")
            sql_query = tool_use.input["query"]
            sql_queries_executed.append(sql_query)
            
            # Execute the SQL query
            try:
                results = await execute_sql_callback(sql_query)
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(results)
                }
            except Exception as e:
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": f"Error executing query: {str(e)}"
                }
            
            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": [tool_result]})
        else:
            # Claude has finished, extract response
            response_text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                ""
            )
            
            return {
                "response": response_text,
                "sql_queries": sql_queries_executed,
                "error": None
            }
```

**Alternative Implementation**: If direct tool use is complex, you can have Claude write SQL in markdown code blocks and parse them:

```python
async def query_claude_simple(user_query: str) -> dict:
    """
    Simpler approach: Claude writes SQL in code blocks, backend executes them.
    """
    # Send query to Claude
    # Parse response for ```sql code blocks
    # Execute each SQL query found
    # Send results back to Claude
    # Claude generates final response
```

---

### Component 6: Frontend (React)

**File Structure**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── UploadHandHistory.jsx     # File upload with progress
│   │   ├── PlayerList.jsx            # Searchable table of players
│   │   ├── PlayerProfile.jsx         # Full player stats + metrics
│   │   ├── ClaudeQueryInterface.jsx  # Natural language query UI
│   │   ├── DatabaseStats.jsx         # Overview dashboard
│   │   ├── MetricCard.jsx            # Reusable stat display card
│   │   ├── StatChart.jsx             # Recharts visualization
│   │   └── Layout.jsx                # App layout with navigation
│   ├── pages/
│   │   ├── HomePage.jsx              # Dashboard overview
│   │   ├── UploadPage.jsx            # Upload interface
│   │   ├── PlayersPage.jsx           # Player database
│   │   ├── PlayerDetailPage.jsx      # Individual player profile
│   │   └── QueryPage.jsx             # Claude query interface
│   ├── services/
│   │   └── api.js                    # API client (axios)
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
├── vite.config.js
└── tailwind.config.js
```

**Key Pages/Features**:

#### 1. Upload Page (`UploadPage.jsx`)
```jsx
// Features:
// - Drag-and-drop .txt file upload
// - Progress bar during parsing
// - Summary after completion (hands parsed, players updated)
// - Error handling for invalid files

<UploadHandHistory 
  onUploadComplete={(result) => {
    // Show: 
    // - Hands parsed: 234
    // - Players updated: 18
    // - Processing time: 3.2s
  }}
/>
```

#### 2. Player Database Page (`PlayersPage.jsx`)
```jsx
// Features:
// - Searchable/filterable table
// - Columns: Name, Hands, VPIP, PFR, 3bet%, AF, WTSD, W$SD, BB/100
// - Sort by any column
// - Filter by stake level, minimum hands
// - Click player row → navigate to PlayerDetailPage
// - Export to CSV

<PlayerList 
  players={allPlayers}
  onPlayerClick={(playerName) => navigate(`/players/${playerName}`)}
/>
```

#### 3. Player Profile Page (`PlayerDetailPage.jsx`)
```jsx
// Features:
// - Complete traditional stats in organized sections
// - All 12 composite metrics with explanations
// - Player classification badge (NIT/TAG/LAG/etc.)
// - Radar chart comparing player to optimal ranges
// - Sample size reliability indicator
// - "Ask Claude about this player" quick button
// - Hand history link (view all hands for this player)

<PlayerProfile 
  playerName={playerName}
  stats={playerStats}
  metrics={compositeMetrics}
  classification={playerType}
/>
```

#### 4. Claude Query Interface (`QueryPage.jsx`)
```jsx
// Features:
// - Large text input for natural language queries
// - Query history (recent queries saved)
// - Response displayed in formatted markdown
// - Optional: show SQL queries Claude executed (toggle)
// - Example queries as quick buttons:
//   - "Find most exploitable players"
//   - "Show calling stations at NL50"
//   - "What's the biggest population leak?"
// - Loading state while Claude processes

<ClaudeQueryInterface 
  onSubmitQuery={(query) => {
    // Call API, show loading, display response
  }}
/>
```

#### 5. Dashboard Page (`HomePage.jsx`)
```jsx
// Features:
// - Total hands in database
// - Total players tracked
// - Breakdown by stake level (pie chart)
// - Recent uploads list
// - Top 10 most exploitable players (by EI)
// - Quick actions: Upload, Query Claude, View Players

<DatabaseStats stats={overviewStats} />
<TopExploitablePlayers players={top10} />
<RecentUploads uploads={recentUploads} />
```

**API Client (`services/api.js`)**:
```javascript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  // Upload hand history
  uploadHandHistory: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${API_BASE_URL}/api/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  
  // Get all players
  getAllPlayers: async (params = {}) => {
    return axios.get(`${API_BASE_URL}/api/players`, { params });
  },
  
  // Get player profile
  getPlayerProfile: async (playerName) => {
    return axios.get(`${API_BASE_URL}/api/players/${encodeURIComponent(playerName)}`);
  },
  
  // Query Claude
  queryClaude: async (query) => {
    return axios.post(`${API_BASE_URL}/api/query/claude`, { query });
  },
  
  // Get database stats
  getDatabaseStats: async () => {
    return axios.get(`${API_BASE_URL}/api/database/stats`);
  }
};
```

---

## Development Phases

### Phase 1: Database Setup (Day 1-2)
- [ ] Set up PostgreSQL database (Supabase/Railway)
- [ ] Create all 5 tables with proper indexes
- [ ] Test connections and basic CRUD
- [ ] Create sample data for testing

### Phase 2: Hand History Parser (Day 3-5)
- [ ] Implement PokerStars .txt parser
- [ ] Handle all action types and edge cases
- [ ] Calculate boolean flags for player_hand_summary
- [ ] Test with real hand history files
- [ ] Handle parsing errors gracefully

### Phase 3: Database Service (Day 6-7)
- [ ] Build SQLAlchemy models
- [ ] Implement batch insert functions
- [ ] Create aggregation queries for player_stats
- [ ] Test stat calculations for accuracy
- [ ] Optimize query performance

### Phase 4: Statistical Calculator (Day 8-10)
- [ ] Implement all 12 composite metric formulas
- [ ] Verify calculations with test cases
- [ ] Add player classification (QEM)
- [ ] Handle edge cases and insufficient data
- [ ] Document each metric clearly

### Phase 5: FastAPI Backend (Day 11-13)
- [ ] Build all API endpoints
- [ ] Integrate parser + database + stats calculator
- [ ] Add error handling and validation
- [ ] Test with Postman/curl
- [ ] Add request logging

### Phase 6: Claude Integration (Day 14-16)
- [ ] Implement Claude API service
- [ ] Create comprehensive system prompt
- [ ] Build SQL execution callback
- [ ] Test Claude's query capabilities
- [ ] Handle tool use / multi-turn conversations
- [ ] Verify strategic analysis quality

### Phase 7: Frontend Development (Day 17-22)
- [ ] Set up React + Vite + Tailwind
- [ ] Build all pages and components
- [ ] Implement file upload with progress
- [ ] Create player list and profile views
- [ ] Build Claude query interface
- [ ] Add data visualizations (charts)
- [ ] Responsive design for mobile

### Phase 8: Integration & Testing (Day 23-25)
- [ ] Connect frontend to backend
- [ ] End-to-end testing of full workflow
- [ ] Fix bugs and edge cases
- [ ] Performance optimization
- [ ] Security review (SQL injection prevention, etc.)

### Phase 9: Deployment (Day 26-28)
- [ ] Deploy backend to Railway/Render
- [ ] Deploy frontend to Vercel
- [ ] Configure production database
- [ ] Set up environment variables
- [ ] SSL/HTTPS configuration
- [ ] Monitor logs and errors

### Phase 10: Documentation (Day 29-30)
- [ ] Write comprehensive README
- [ ] API documentation
- [ ] Parser specification
- [ ] Metrics guide with formulas
- [ ] User guide with screenshots
- [ ] Developer setup instructions

---

## Testing Requirements

### Unit Tests

**Parser Tests** (`tests/test_parser.py`):
```python
def test_parse_simple_hand():
    """Test parsing a basic hand with standard actions"""
    
def test_parse_all_in_hand():
    """Test handling all-in situations"""
    
def test_parse_multiway_pot():
    """Test 3+ players seeing flop"""
    
def test_calculate_vpip_pfr_flags():
    """Verify VPIP and PFR are calculated correctly"""
    
def test_cbet_opportunity_detection():
    """Verify cbet opportunities identified correctly"""
```

**Stats Calculator Tests** (`tests/test_stats_calculator.py`):
```python
def test_exploitability_index():
    """Verify EI formula with known inputs"""
    
def test_pressure_vulnerability_score():
    """Test PVS calculation"""
    
def test_player_classification():
    """Test QEM player type classification"""
    
def test_insufficient_sample_handling():
    """Verify proper handling of low sample sizes"""
```

**Database Tests** (`tests/test_database.py`):
```python
def test_insert_hand():
    """Test inserting a single hand"""
    
def test_update_player_stats():
    """Test aggregation query correctness"""
    
def test_query_players():
    """Test filtering and sorting players"""
```

### Integration Tests

**End-to-End Test**:
1. Upload hand history file
2. Verify hands parsed correctly
3. Check player_stats updated
4. Query player profile
5. Verify composite metrics calculated
6. Test Claude query functionality

**Sample Test Data**:
- Include 100+ sample hands in `tests/data/sample_hands.txt`
- Include expected outputs for each metric
- Test with various player types (nit, TAG, LAG, calling station, maniac)

---

## Configuration Files

### Backend

**`.env`**:
```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/poker_analysis_db

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Backend
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# Environment
ENVIRONMENT=development  # or production
```

**`requirements.txt`**:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
python-multipart==0.0.6
anthropic==0.18.0
pydantic==2.6.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
```

**`pyproject.toml`** (optional, for Poetry):
```toml
[tool.poetry]
name = "poker-analysis-backend"
version = "1.0.0"
description = "Poker analysis backend with Claude AI integration"
authors = ["Your Name"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = "^2.0.25"
psycopg2-binary = "^2.9.9"
anthropic = "^0.18.0"
```

### Frontend

**`package.json`**:
```json
{
  "name": "poker-analysis-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "axios": "^1.6.5",
    "recharts": "^2.10.0",
    "react-markdown": "^9.0.0",
    "lucide-react": "^0.307.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "vite": "^5.0.11"
  }
}
```

**`vite.config.js`**:
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

**`tailwind.config.js`**:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**`.env`** (frontend):
```env
VITE_API_URL=http://localhost:8000
```

---

## Deployment Guide

### Backend Deployment (Railway)

1. **Create Railway project**:
   - Connect GitHub repository
   - Add PostgreSQL service
   - Set environment variables

2. **Environment Variables**:
   - `DATABASE_URL`: Auto-provided by Railway PostgreSQL
   - `ANTHROPIC_API_KEY`: Your Claude API key
   - `FRONTEND_URL`: Your deployed frontend URL
   - `ENVIRONMENT`: `production`

3. **Build Command**: `pip install -r requirements.txt`

4. **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### Frontend Deployment (Vercel)

1. **Connect GitHub repository**

2. **Build Settings**:
   - Framework: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`

3. **Environment Variables**:
   - `VITE_API_URL`: Your Railway backend URL

4. **Deploy**: Automatic on push to main branch

---

## Success Criteria

The application is complete when:

1. ✅ User can upload `.txt` hand history files via web interface
2. ✅ Parser correctly extracts all actions and calculates flags
3. ✅ Database stores hands and updates player statistics
4. ✅ All 12 composite metrics calculate correctly
5. ✅ Player profiles display complete stats with interpretations
6. ✅ Claude can answer any natural language query about the database
7. ✅ Claude generates accurate exploitative strategy recommendations
8. ✅ Frontend is mobile-responsive and works on all devices
9. ✅ Application is deployed to production with cloud database
10. ✅ All documentation is complete and comprehensive

---

## Future Enhancements (Post-MVP)

- **Real-time hand tracking**: Input hands during live play
- **Session analysis**: Upload multiple files, track profit by player type
- **Execution tracking**: Did user follow Claude's recommendations?
- **Range visualization**: Display opponent ranges graphically
- **GTO comparison**: Compare exploitative strategy vs GTO
- **Multi-user support**: User authentication and private databases
- **Hand replayer**: Replay hands with Claude's analysis overlay
- **Export reports**: Generate PDF reports on opponents
- **Mobile app**: Native iOS/Android app
- **HUD integration**: Sync with real poker HUD software
- **Tournament mode**: ICM calculations and tournament-specific stats
- **AI opponent modeling**: Predict opponent actions
- **Bankroll tracking**: Integrate with profit/loss tracking

---

## File Structure Summary

```
poker-analysis-app/
├── backend/
│   ├── main.py                           # FastAPI application
│   ├── parser/
│   │   ├── __init__.py
│   │   └── pokerstars_parser.py          # Hand history parser
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database_service.py           # Database operations
│   │   ├── stats_calculator.py           # 12 composite metrics
│   │   └── claude_service.py             # Claude API integration
│   ├── models/
│   │   ├── __init__.py
│   │   └── database_models.py            # SQLAlchemy models
│   ├── tests/
│   │   ├── test_parser.py
│   │   ├── test_stats_calculator.py
│   │   ├── test_database.py
│   │   └── data/
│   │       └── sample_hands.txt
│   ├── requirements.txt
│   ├── .env
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadHandHistory.jsx
│   │   │   ├── PlayerList.jsx
│   │   │   ├── PlayerProfile.jsx
│   │   │   ├── ClaudeQueryInterface.jsx
│   │   │   ├── DatabaseStats.jsx
│   │   │   ├── MetricCard.jsx
│   │   │   ├── StatChart.jsx
│   │   │   └── Layout.jsx
│   │   ├── pages/
│   │   │   ├── HomePage.jsx
│   │   │   ├── UploadPage.jsx
│   │   │   ├── PlayersPage.jsx
│   │   │   ├── PlayerDetailPage.jsx
│   │   │   └── QueryPage.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── .env
│   └── README.md
│
├── docs/
│   ├── README.md                         # Main project documentation
│   ├── API_DOCS.md                       # API endpoint documentation
│   ├── PARSER_SPEC.md                    # Hand history parser specification
│   ├── METRICS_GUIDE.md                  # All 12 metrics explained
│   └── DEPLOYMENT.md                     # Deployment instructions
│
├── .gitignore
└── README.md
```

---

## Getting Started (For Claude Code)

**Read this file completely, then:**

1. Set up the PostgreSQL database with all 5 tables
2. Build the hand history parser for PokerStars format
3. Implement the 12 statistical models in stats_calculator.py
4. Create the FastAPI backend with all endpoints
5. Integrate Claude API with database access
6. Build the React frontend with all pages
7. Test the complete workflow end-to-end
8. Deploy to production

**Key priorities:**
- Accurate parser (critical for all downstream analysis)
- Correct metric calculations (verify with test cases)
- Robust Claude integration (must handle any query)
- Clean, intuitive UI (mobile-friendly)

**This is a comprehensive deep-analysis tool, not a real-time assistant. Focus on flexibility and analytical power.**

---

## Questions or Clarifications Needed

If you need clarification on any aspect of this plan:
- PokerStars hand history format edge cases
- Specific SQL query examples for aggregation
- Claude API tool use implementation details
- Frontend component design decisions
- Deployment configuration specifics

**Ask before starting implementation to ensure everything is clear.**

---

**END OF PROJECT PLAN**
