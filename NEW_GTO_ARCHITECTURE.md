# Ploit - New GTO Architecture (GTOWizard-Based)

**Status:** Architecture Design
**Date:** 2025-11-20
**Purpose:** Clean architecture built from scratch for GTOWizard data

---

## Overview

This document defines the complete new GTO architecture for Ploit, replacing the old postflop-focused GTO system with a clean design optimized for GTOWizard's data structure.

**What We're Building:**
- ✅ **Preflop GTO** (147 scenarios) - immediate implementation
- 🔄 **Postflop GTO** (aggregate reports) - future extension
- 🎯 **Leak Detection** - compare my play to GTO
- 🎯 **Exploit Finding** - identify opponent deviations

**What We're Keeping:**
- FastAPI backend + React frontend
- Claude AI integration
- Hand history parsing
- Player tracking & sessions

**What We're Scrapping:**
- Old `gto_solutions`, `gto_strategy_cache`, `gto_category_aggregates` tables
- Old `gto_service.py`
- Old GTO API endpoints

---

## 1. Database Schema

### Design Principles
1. **GTOWizard-Native:** Matches GTOWizard's data structure (scenarios, combos/hands, absolute frequencies)
2. **Extensible:** Easy to add postflop aggregate reports later
3. **Performant:** Optimized for fast queries on player actions vs GTO
4. **Clean:** No forced abstractions - simple, straightforward design

### Table: `gto_scenarios`

Metadata for each GTO scenario (preflop or postflop).

```sql
CREATE TABLE gto_scenarios (
    scenario_id SERIAL PRIMARY KEY,
    scenario_name VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'BB_vs_UTG_call', 'AsKsQs_BTN_cbet'

    -- Scenario classification
    street VARCHAR(10) NOT NULL,                 -- 'preflop', 'flop', 'turn', 'river'
    category VARCHAR(50) NOT NULL,               -- 'opening', 'defense', 'facing_3bet', 'cbet', etc.

    -- Preflop specific
    position VARCHAR(10),                        -- 'UTG', 'BB', 'BTN', etc.
    action VARCHAR(20),                          -- 'open', 'call', 'fold', '3bet', '4bet', 'allin'
    opponent_position VARCHAR(10),               -- 'UTG', NULL for opens

    -- Postflop specific (for future use)
    board VARCHAR(20),                           -- e.g., 'AsKsQs', 'PREFLOP'
    board_texture VARCHAR(50),                   -- e.g., 'monotone', 'dry', 'wet'
    position_context VARCHAR(20),                -- 'IP', 'OOP'
    action_node VARCHAR(50),                     -- 'facing_cbet', 'facing_raise'

    -- Metadata
    data_source VARCHAR(50) DEFAULT 'gtowizard', -- 'gtowizard', 'solver', 'custom'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gto_scenarios_street ON gto_scenarios(street);
CREATE INDEX idx_gto_scenarios_category ON gto_scenarios(category);
CREATE INDEX idx_gto_scenarios_position ON gto_scenarios(position);
CREATE INDEX idx_gto_scenarios_board ON gto_scenarios(board);
```

**Example Rows:**
```sql
-- Preflop examples
('BB_vs_UTG_call', 'preflop', 'defense', 'BB', 'call', 'UTG', 'PREFLOP', NULL, NULL, NULL, ...)
('UTG_open', 'preflop', 'opening', 'UTG', 'open', NULL, 'PREFLOP', NULL, NULL, NULL, ...)
('CO_vs_BTN_3bet_4bet', 'preflop', 'facing_3bet', 'CO', '4bet', 'BTN', 'PREFLOP', NULL, NULL, NULL, ...)

-- Postflop examples (future)
('AsKsQs_BTN_cbet', 'flop', 'cbet', 'BTN', 'bet', NULL, 'AsKsQs', 'monotone', 'IP', 'facing_check', ...)
```

---

### Table: `gto_frequencies`

Stores GTO frequencies for each hand in each scenario.

```sql
CREATE TABLE gto_frequencies (
    frequency_id SERIAL PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id) ON DELETE CASCADE,

    -- Hand identification
    hand VARCHAR(4) NOT NULL,                    -- 'AKo', 'JTs', '22', 'AhKd' (combo for postflop)

    -- Position (whose strategy is this?)
    position VARCHAR(10) NOT NULL,               -- 'BB', 'UTG', 'IP', 'OOP', 'BTN', etc.

    -- Frequency data
    frequency DECIMAL(10, 8) NOT NULL,           -- 0.0 to 1.0 (absolute frequency)

    -- Constraints
    CONSTRAINT unique_scenario_hand_position UNIQUE (scenario_id, hand, position),
    CONSTRAINT check_frequency_range CHECK (frequency >= 0 AND frequency <= 1)
);

CREATE INDEX idx_gto_frequencies_scenario ON gto_frequencies(scenario_id);
CREATE INDEX idx_gto_frequencies_hand ON gto_frequencies(hand);
CREATE INDEX idx_gto_frequencies_position ON gto_frequencies(position);
CREATE INDEX idx_gto_frequencies_freq ON gto_frequencies(frequency);
```

**Notes:**
- For preflop: `hand` = hand type like 'AKo', 'JTs', '22'
- For postflop: `hand` = specific combo like 'AhKd', 'JsTc'
- `position` = whose strategy this represents (critical for postflop where both players have strategies)
- `frequency` = absolute frequency (GTOWizard style)
  - For opening: % of all hands to open
  - For actions: % of all hands to take this action (not conditional)

**Why position field is important:**
- **Preflop:** Redundant but makes queries cleaner (position already in scenario)
- **Postflop:** Essential! Same scenario can have frequencies for BOTH IP and OOP
  - Example: "AsKsQs_cbet_spot" stores IP's betting range AND OOP's defense range

**Example Rows:**
```sql
-- Preflop: BB vs UTG call scenario
(scenario_id=1, hand='AKo', position='BB', frequency=0.595)  -- BB calls 59.5%
(scenario_id=1, hand='AKs', position='BB', frequency=0.000)  -- BB never calls (3bets or folds)
(scenario_id=1, hand='22', position='BB', frequency=0.285)   -- BB calls 28.5%

-- Preflop: UTG open scenario
(scenario_id=2, hand='AKo', position='UTG', frequency=1.000)  -- UTG always opens
(scenario_id=2, hand='22', position='UTG', frequency=0.285)   -- UTG opens 28.5%

-- Postflop: IP's cbet range on AsKsQs (future)
(scenario_id=50, hand='AhKd', position='IP', frequency=0.85)  -- IP cbets 85%

-- Postflop: OOP's call vs cbet on same board (future)
(scenario_id=50, hand='AhKd', position='OOP', frequency=0.60)  -- OOP calls 60%
```

---

### Table: `player_actions`

Stores actual player actions from hand histories for leak detection.

```sql
CREATE TABLE player_actions (
    action_id SERIAL PRIMARY KEY,

    -- Player identification
    player_name VARCHAR(100) NOT NULL,
    hand_id VARCHAR(100) NOT NULL,               -- External hand ID from tracker

    -- Action context
    timestamp TIMESTAMP NOT NULL,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id),

    -- Hole cards
    hole_cards VARCHAR(4) NOT NULL,              -- 'AKo', 'JTs', etc.

    -- Action taken
    action_taken VARCHAR(20) NOT NULL,           -- 'fold', 'call', 'raise', '3bet', etc.

    -- GTO analysis (cached)
    gto_frequency DECIMAL(10, 8),                -- What GTO says for this hand/action
    ev_loss_bb DECIMAL(10, 4),                   -- Estimated EV loss in big blinds
    is_mistake BOOLEAN,                          -- True if significant deviation
    mistake_severity VARCHAR(20),                -- 'minor', 'moderate', 'major', 'critical'

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_player_actions_player ON player_actions(player_name);
CREATE INDEX idx_player_actions_scenario ON player_actions(scenario_id);
CREATE INDEX idx_player_actions_timestamp ON player_actions(timestamp);
CREATE INDEX idx_player_actions_mistake ON player_actions(is_mistake);
CREATE INDEX idx_player_actions_hand_id ON player_actions(hand_id);
```

**Example Rows:**
```sql
-- Hero called with AKo in BB vs UTG (GTO: call 59.5%)
(player='Hero', hand_id='PS123456', scenario_id=1, hole_cards='AKo',
 action_taken='call', gto_frequency=0.595, ev_loss_bb=0.0, is_mistake=false, ...)

-- Villain folded 22 in BB vs UTG (GTO: call 28.5%)
(player='Villain1', hand_id='PS123457', scenario_id=1, hole_cards='22',
 action_taken='fold', gto_frequency=0.285, ev_loss_bb=0.15, is_mistake=true,
 mistake_severity='moderate', ...)
```

---

### Table: `player_stats`

Aggregated leak statistics per player per scenario.

```sql
CREATE TABLE player_stats (
    stat_id SERIAL PRIMARY KEY,

    -- Player and scenario
    player_name VARCHAR(100) NOT NULL,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id),

    -- Sample size
    total_hands INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Frequency comparison
    player_frequency DECIMAL(10, 8),             -- How often player takes this action
    gto_frequency DECIMAL(10, 8),                -- How often GTO says to take it
    frequency_diff DECIMAL(10, 8),               -- player - gto (positive = overfolding/overcalling)

    -- EV metrics
    total_ev_loss_bb DECIMAL(10, 4),             -- Total BB lost in this scenario
    avg_ev_loss_bb DECIMAL(10, 4),               -- Average BB lost per hand

    -- Leak classification
    leak_type VARCHAR(50),                       -- 'overfold', 'underfold', 'overcall', 'under3bet', etc.
    leak_severity VARCHAR(20),                   -- 'minor', 'moderate', 'major', 'critical'

    -- Exploit recommendation
    exploit_description TEXT,                     -- Human-readable exploit
    exploit_value_bb_100 DECIMAL(10, 4),         -- Expected value of exploit per 100 hands
    exploit_confidence DECIMAL(5, 2),            -- 0-100 confidence based on sample size

    CONSTRAINT unique_player_scenario UNIQUE (player_name, scenario_id)
);

CREATE INDEX idx_player_stats_player ON player_stats(player_name);
CREATE INDEX idx_player_stats_scenario ON player_stats(scenario_id);
CREATE INDEX idx_player_stats_leak_severity ON player_stats(leak_severity);
CREATE INDEX idx_player_stats_ev_loss ON player_stats(total_ev_loss_bb);
```

**Example Rows:**
```sql
-- Villain1 overfolding in BB vs UTG
(player='Villain1', scenario_id=1, total_hands=150,
 player_frequency=0.20, gto_frequency=0.30, frequency_diff=-0.10,
 total_ev_loss_bb=22.5, avg_ev_loss_bb=0.15,
 leak_type='undercall', leak_severity='major',
 exploit_description='Villain underdefends BB vs UTG by 10%. Open wider from UTG.',
 exploit_value_bb_100=8.5, exploit_confidence=85.0, ...)
```

---

### Table: `hand_types` (Helper)

Maps combos to hand types for preflop aggregation.

```sql
CREATE TABLE hand_types (
    combo VARCHAR(4) PRIMARY KEY,                -- 'AhKd', '2c2d', etc.
    hand VARCHAR(4) NOT NULL,                    -- 'AKo', '22', 'JTs'
    rank1 VARCHAR(1) NOT NULL,
    rank2 VARCHAR(1) NOT NULL,
    suit1 VARCHAR(1) NOT NULL,
    suit2 VARCHAR(1) NOT NULL,
    is_pair BOOLEAN NOT NULL,
    is_suited BOOLEAN NOT NULL
);

CREATE INDEX idx_hand_types_hand ON hand_types(hand);
```

---

## 2. GTO Service Layer

New `backend/services/gto_service.py` - Clean service for all GTO operations.

### Core Methods

```python
class GTOService:
    """Service for GTO frequency queries and comparisons."""

    def __init__(self, db: Session):
        self.db = db

    # === PREFLOP GTO QUERIES ===

    def get_gto_frequency(
        self,
        scenario_name: str,
        hand: str
    ) -> Optional[float]:
        """
        Get GTO frequency for a specific hand in a scenario.

        Args:
            scenario_name: e.g., 'BB_vs_UTG_call'
            hand: e.g., 'AKo', 'JTs', '22'

        Returns:
            float: Frequency (0.0 to 1.0) or None if not found
        """

    def get_action_breakdown(
        self,
        position: str,
        opponent: str,
        hand: str
    ) -> Dict[str, float]:
        """
        Get all action frequencies for a hand in a situation.

        Args:
            position: e.g., 'BB'
            opponent: e.g., 'UTG'
            hand: e.g., 'AKo'

        Returns:
            {'fold': 0.0, 'call': 0.595, '3bet': 0.405, ...}
        """

    def get_opening_range(self, position: str) -> Dict[str, float]:
        """Get full opening range for a position."""

    # === LEAK DETECTION ===

    def record_player_action(
        self,
        player_name: str,
        hand_id: str,
        scenario_name: str,
        hole_cards: str,
        action_taken: str
    ) -> PlayerAction:
        """
        Record a player action and analyze against GTO.

        Automatically:
        - Looks up GTO frequency
        - Calculates EV loss
        - Flags mistakes
        - Updates player_stats
        """

    def get_player_leaks(
        self,
        player_name: str,
        min_hands: int = 20,
        sort_by: str = 'ev_loss'
    ) -> List[PlayerStat]:
        """
        Get all leaks for a player, sorted by severity.

        Args:
            player_name: Player to analyze
            min_hands: Minimum sample size
            sort_by: 'ev_loss', 'frequency_diff', 'severity'

        Returns:
            List of PlayerStat objects with leak information
        """

    def get_biggest_leak(self, player_name: str) -> Optional[PlayerStat]:
        """Get player's single biggest leak by EV loss."""

    # === EXPLOIT FINDING ===

    def calculate_exploits(
        self,
        player_name: str,
        min_confidence: float = 70.0
    ) -> List[Dict]:
        """
        Calculate exploitable patterns in player's game.

        Returns:
            [
                {
                    'scenario': 'BB_vs_UTG_call',
                    'leak_type': 'undercall',
                    'frequency_diff': -0.10,
                    'exploit': 'Open wider from UTG',
                    'value_bb_100': 8.5,
                    'confidence': 85.0
                },
                ...
            ]
        """

    def get_counter_strategy(
        self,
        player_name: str,
        position: str
    ) -> Dict[str, Any]:
        """
        Generate counter-strategy for a player in a position.

        Example: If villain overfolding BB vs UTG, returns:
        {
            'position': 'UTG',
            'vs_player': 'Villain1',
            'adjustments': [
                {'hand': 'KQo', 'gto': 0.5, 'exploitative': 1.0, 'reason': 'Villain overfolding'}
            ],
            'expected_value_bb_100': 12.3
        }
        """

    # === STATISTICS ===

    def get_player_gto_adherence(
        self,
        player_name: str,
        street: str = 'preflop'
    ) -> Dict[str, Any]:
        """
        Calculate how closely player follows GTO.

        Returns:
            {
                'total_hands': 500,
                'avg_frequency_diff': 0.05,
                'total_ev_loss_bb': 75.0,
                'avg_ev_loss_per_hand': 0.15,
                'gto_adherence_score': 78.5,  # 0-100
                'major_leaks_count': 3
            }
        """
```

---

## 3. API Endpoints

New `backend/api/gto_endpoints.py` - RESTful API for GTO data.

### Endpoint Structure

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

router = APIRouter(prefix="/api/gto", tags=["gto"])

# === GTO QUERIES ===

@router.get("/frequency")
async def get_gto_frequency(
    scenario: str,
    hand: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    GET /api/gto/frequency?scenario=BB_vs_UTG_call&hand=AKo

    Returns: {"frequency": 0.595, "percentage": 59.5}
    """

@router.get("/breakdown")
async def get_action_breakdown(
    position: str,
    opponent: str,
    hand: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    GET /api/gto/breakdown?position=BB&opponent=UTG&hand=AKo

    Returns: {
        "fold": 0.0,
        "call": 0.595,
        "3bet": 0.405
    }
    """

@router.get("/range/{position}")
async def get_opening_range(
    position: str,
    min_frequency: float = 0.0,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    GET /api/gto/range/UTG?min_frequency=0.5

    Returns: {
        "position": "UTG",
        "range": {
            "AA": 1.0,
            "KK": 1.0,
            "AKs": 1.0,
            ...
        },
        "total_combos": 450,
        "vpip": 15.2
    }
    """

# === LEAK DETECTION ===

@router.post("/action")
async def record_action(
    action_data: PlayerActionCreate,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    POST /api/gto/action
    Body: {
        "player_name": "Villain1",
        "hand_id": "PS123456",
        "scenario": "BB_vs_UTG_call",
        "hole_cards": "AKo",
        "action_taken": "fold"
    }

    Returns: {
        "action_id": 123,
        "gto_frequency": 0.595,
        "ev_loss_bb": 0.75,
        "is_mistake": true,
        "severity": "major"
    }
    """

@router.get("/leaks/{player}")
async def get_player_leaks(
    player: str,
    min_hands: int = 20,
    sort_by: str = "ev_loss",
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    GET /api/gto/leaks/Villain1?min_hands=20&sort_by=ev_loss

    Returns: [
        {
            "scenario": "BB_vs_UTG_call",
            "total_hands": 150,
            "player_frequency": 0.20,
            "gto_frequency": 0.30,
            "frequency_diff": -0.10,
            "leak_type": "undercall",
            "leak_severity": "major",
            "total_ev_loss_bb": 22.5,
            "exploit": "Open wider from UTG"
        },
        ...
    ]
    """

@router.get("/adherence/{player}")
async def get_gto_adherence(
    player: str,
    street: str = "preflop",
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    GET /api/gto/adherence/Hero?street=preflop

    Returns: {
        "player": "Hero",
        "street": "preflop",
        "total_hands": 500,
        "gto_adherence_score": 78.5,
        "avg_ev_loss_per_hand": 0.15,
        "total_ev_loss_bb": 75.0,
        "major_leaks_count": 3
    }
    """

# === EXPLOIT FINDING ===

@router.get("/exploits/{player}")
async def get_exploits(
    player: str,
    min_confidence: float = 70.0,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    GET /api/gto/exploits/Villain1?min_confidence=70

    Returns: [
        {
            "scenario": "BB_vs_UTG_call",
            "leak_type": "undercall",
            "frequency_diff": -0.10,
            "exploit": "Open wider from UTG. Increase opening range by 10%.",
            "value_bb_100": 8.5,
            "confidence": 85.0,
            "sample_size": 150
        },
        ...
    ]
    """

@router.get("/counter/{player}/{position}")
async def get_counter_strategy(
    player: str,
    position: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    GET /api/gto/counter/Villain1/UTG

    Returns: {
        "position": "UTG",
        "vs_player": "Villain1",
        "adjustments": [
            {
                "hand": "KQo",
                "gto_frequency": 0.5,
                "exploitative_frequency": 1.0,
                "reason": "Villain underdefends BB by 10%",
                "value_increase_bb": 0.15
            }
        ],
        "expected_value_bb_100": 12.3
    }
    """
```

---

## 4. Import Script

`backend/scripts/import_gtowizard.py` - Import 147 preflop scenarios.

```python
#!/usr/bin/env python3
"""
Import GTOWizard preflop ranges to new GTO database.
"""
import re
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.gto_models import GTOScenario, GTOFrequency, HandType

def parse_gtowizard_file(filepath: str) -> Dict[str, Dict[str, float]]:
    """Parse gtowizard_ranges.txt file."""
    with open(filepath, 'r') as f:
        content = f.read()

    pattern = r'\[DONE\]\s+(\w+)\s*\n#\s*GTOWizard:\s*(.*?)\n(.*?)\n\n'
    ranges = {}

    for match in re.finditer(pattern, content, re.DOTALL):
        scenario_name = match.group(1)
        range_data = match.group(3).strip()
        combos = parse_combo_range(range_data)

        if combos:
            ranges[scenario_name] = combos

    return ranges

def categorize_scenario(scenario_name: str) -> Tuple[str, str, str, str]:
    """Extract metadata from scenario name."""
    parts = scenario_name.split('_')

    # Opening ranges
    if scenario_name.endswith('_open'):
        return 'opening', parts[0], 'open', None

    # Defense and facing bets
    if 'vs' in scenario_name:
        position = parts[0]
        opponent = parts[2]
        action = parts[-1]

        if '3bet' in scenario_name:
            category = 'facing_3bet'
        elif '4bet' in scenario_name:
            category = 'facing_4bet'
        elif action in ['fold', 'call', '3bet']:
            category = 'defense'
        else:
            category = 'multiway'

        return category, position, action, opponent

    return 'unknown', 'unknown', 'unknown', None

def import_preflop_ranges():
    """Import all 147 preflop scenarios."""
    db = SessionLocal()

    try:
        print("Loading GTOWizard ranges...")
        ranges = parse_gtowizard_file('/root/Documents/Ploit/solver/gtowizard_ranges.txt')
        print(f"Found {len(ranges)} scenarios\n")

        # Step 1: Create scenarios
        print("Step 1: Creating scenarios...")
        scenario_map = {}

        for scenario_name in ranges.keys():
            category, position, action, opponent = categorize_scenario(scenario_name)

            scenario = GTOScenario(
                scenario_name=scenario_name,
                street='preflop',
                category=category,
                position=position,
                action=action,
                opponent_position=opponent,
                board='PREFLOP',
                data_source='gtowizard'
            )
            db.add(scenario)
            db.flush()

            scenario_map[scenario_name] = scenario.scenario_id

        db.commit()
        print(f"  ✅ Created {len(scenario_map)} scenarios\n")

        # Step 2: Aggregate combos to hands and insert frequencies
        print("Step 2: Inserting GTO frequencies...")

        total_frequencies = 0
        for scenario_name, combos in ranges.items():
            scenario_id = scenario_map[scenario_name]

            # Get position from scenario metadata
            category, position, action, opponent = categorize_scenario(scenario_name)

            # Aggregate combos to hands
            hand_frequencies = {}
            for combo, freq in combos.items():
                hand = combo_to_hand(combo)
                if hand:
                    if hand not in hand_frequencies:
                        hand_frequencies[hand] = []
                    hand_frequencies[hand].append(freq)

            # Calculate average frequency per hand
            for hand, freqs in hand_frequencies.items():
                avg_freq = sum(freqs) / len(freqs)

                frequency = GTOFrequency(
                    scenario_id=scenario_id,
                    hand=hand,
                    position=position,  # Add position field
                    frequency=avg_freq
                )
                db.add(frequency)

            total_frequencies += len(hand_frequencies)
            print(f"  ✅ {scenario_name}: {len(hand_frequencies)} hands")

        db.commit()
        print(f"\n  Total frequencies inserted: {total_frequencies}\n")

        # Verification
        print("=" * 80)
        print("IMPORT COMPLETE!")
        print("=" * 80)
        print(f"✅ Scenarios: {len(scenario_map)}")
        print(f"✅ Frequencies: {total_frequencies}")

    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == '__main__':
    import_preflop_ranges()
```

---

## 5. Claude AI Integration

Update Claude's system prompt to include GTO knowledge.

### System Prompt Addition

```python
GTO_KNOWLEDGE = """
## GTO Poker Analysis

You have access to 147 preflop GTO scenarios from GTOWizard covering:
- Opening ranges (UTG, MP, CO, BTN, SB)
- BB/SB defense vs all positions
- Facing 3bets and 4bets
- Multiway scenarios

### Available GTO Queries

1. **Get GTO Frequency:**
   SELECT gf.frequency, gf.position FROM gto_frequencies gf
   JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
   WHERE gs.scenario_name = 'BB_vs_UTG_call' AND gf.hand = 'AKo' AND gf.position = 'BB';

2. **Get Action Breakdown:**
   SELECT gs.action, gf.frequency
   FROM gto_frequencies gf
   JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
   WHERE gs.position = 'BB' AND gs.opponent_position = 'UTG'
     AND gf.hand = 'AKo' AND gf.position = 'BB';

3. **Find Player Leaks:**
   SELECT * FROM player_stats
   WHERE player_name = 'Villain1'
   ORDER BY total_ev_loss_bb DESC
   LIMIT 5;

4. **Get Exploits:**
   SELECT scenario_id, leak_type, exploit_description, exploit_value_bb_100
   FROM player_stats
   WHERE player_name = 'Villain1' AND exploit_confidence > 70
   ORDER BY exploit_value_bb_100 DESC;

### Interpreting Results

- **Frequency = 0.0:** Never take this action
- **Frequency = 1.0:** Always take this action
- **Frequency 0.0-1.0:** Mixed strategy

- **EV Loss:** Big blinds lost due to deviation from GTO
- **Leak Severity:** minor (<0.05 BB), moderate (0.05-0.15), major (0.15-0.30), critical (>0.30)

### Example Conversation

User: "How often should I call in BB vs UTG with AKo?"

Claude: *Queries database*
According to GTO, you should call with AKo in BB vs UTG 59.5% of the time, and 3bet the remaining 40.5%. This mixed strategy makes you unexploitable.

User: "What are Villain1's biggest leaks?"

Claude: *Queries player_stats*
Villain1's biggest leak is underdefending BB vs UTG (calling only 20% when GTO calls 30%). This has cost them 22.5 BB over 150 hands. **Exploit:** Open wider from UTG against this player. Expected value: +8.5 BB/100.
"""
```

---

## 6. Data Flow

### Leak Detection Flow

```
1. Hand History File
   ↓
2. Hand History Parser (existing Ploit component)
   ↓
3. Extract preflop actions
   ↓
4. For each action:
   - Identify scenario (e.g., BB_vs_UTG_call)
   - Look up GTO frequency
   - Calculate EV loss
   - Insert into player_actions
   ↓
5. Update player_stats (aggregated leaks)
   ↓
6. Claude AI analyzes and explains leaks
```

### Exploit Finding Flow

```
1. Query player_stats for opponent
   ↓
2. Identify significant deviations (frequency_diff > threshold)
   ↓
3. For each leak:
   - Calculate exploit value
   - Generate counter-strategy
   - Estimate confidence based on sample size
   ↓
4. Return exploits sorted by EV
   ↓
5. Claude AI explains exploits in natural language
```

---

## 7. Implementation Checklist

### Phase 1: Database & Import (Week 1)
- [ ] Create new database schema (4 tables)
- [ ] Create SQLAlchemy models
- [ ] Write import script
- [ ] Import 147 preflop scenarios
- [ ] Verify data integrity

### Phase 2: GTO Service (Week 1-2)
- [ ] Implement GTOService class
- [ ] GTO query methods
- [ ] Leak detection methods
- [ ] Exploit finding methods
- [ ] Unit tests

### Phase 3: API Endpoints (Week 2)
- [ ] GTO query endpoints
- [ ] Leak detection endpoints
- [ ] Exploit finding endpoints
- [ ] API tests

### Phase 4: Claude Integration (Week 2-3)
- [ ] Update Claude system prompt
- [ ] Test GTO queries via Claude
- [ ] Test leak analysis via Claude
- [ ] Test exploit recommendations via Claude

### Phase 5: Hand History Integration (Week 3)
- [ ] Connect hand parser to player_actions
- [ ] Auto-analyze hands on import
- [ ] Real-time leak detection
- [ ] Player dashboards

### Phase 6: Frontend (Week 3-4)
- [ ] GTO range viewer
- [ ] Leak detection dashboard
- [ ] Exploit finder UI
- [ ] Player stats page

---

## 8. Future Extensions

### Postflop GTOWizard Integration

When adding postflop aggregate reports:

1. **New scenarios:** Add flop/turn/river scenarios to `gto_scenarios`
   - `board`: 'AsKsQs', 'AsKsQs2h', etc.
   - `board_texture`: 'monotone', 'paired', 'dry', 'wet'
   - `action_node`: 'facing_cbet', 'facing_raise'

2. **Postflop frequencies:** Same `gto_frequencies` table
   - `hand`: Specific combo like 'AhKd', 'JsTs'
   - `frequency`: Action frequency from aggregate report

3. **No schema changes needed:** Current design is already extensible!

---

## Summary

This architecture provides:

✅ **Clean design** optimized for GTOWizard data structure
✅ **Extensible** for postflop aggregate reports
✅ **Performant** with indexed queries
✅ **Comprehensive** leak detection & exploit finding
✅ **Claude-integrated** for natural language insights
✅ **Backward compatible** with existing Ploit infrastructure

Ready to implement!
