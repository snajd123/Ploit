# Integrating GTOWizard Preflop Ranges into Ploit

## Overview

You already have a sophisticated GTO infrastructure in Ploit. We just need to adapt the 147 GTOWizard preflop scenarios to work with your existing architecture.

---

## Current Ploit GTO Architecture

### **Existing Tables**
```sql
gto_solutions {
    solution_id,
    scenario_name,
    board,              -- e.g., "As7h2c"
    board_category_l1,  -- e.g., "Ace-high"
    board_category_l2,  -- e.g., "Ace-high-rainbow"
    board_category_l3,  -- e.g., "Ace-high-rainbow-dry"
    scenario_type,      -- e.g., "SRP_cbet", "3bet_pot"
    position_context,   -- e.g., "BTN_vs_BB"
    accuracy,
    solving_time_seconds
}

gto_strategy_cache {
    solution_id,
    hand,               -- e.g., "AKo", "JTs"
    position,
    street,             -- "preflop", "flop", "turn", "river"
    action_node,        -- e.g., "facing_raise", "in_position"
    strategy_json,      -- JSONB: {"fold": 0.425, "call": 0.575, "raise": 0}
    primary_action,
    primary_action_freq
}
```

### **Existing Services**
- `GTOService` - Queries GTO data
- `BoardCategorizer` - Categorizes flop textures
- `BaselineProvider` - Poker theory baselines
- `ClaudeService` - AI analysis with GTO knowledge

### **Existing API Endpoints**
- `/api/gto/scenarios` - List all GTO scenarios
- `/api/gto/solution/{name}` - Get specific solution
- `/api/gto/compare/{player}/{scenario}` - Compare player to GTO

---

## Adaptation Strategy

### **Option 1: Extend Existing Schema (Recommended)**

Add preflop data to existing tables with special markers:

```python
# For preflop scenarios, use:
board = "PREFLOP"
board_category_l1 = "PREFLOP"
board_category_l2 = position_context  # e.g., "BB_vs_UTG"
board_category_l3 = action           # e.g., "call", "3bet"
scenario_type = "preflop"
```

**Example Rows**:
```sql
INSERT INTO gto_solutions VALUES (
    uuid(),
    'BB_vs_UTG_call',
    'PREFLOP',
    'PREFLOP',
    'BB_vs_UTG',
    'call',
    'preflop',
    'BB_vs_UTG',
    NULL,  -- pot_size
    NULL,  -- effective_stack
    1.0,   -- accuracy (GTOWizard data)
    0      -- solving_time (pre-solved)
);

INSERT INTO gto_strategy_cache VALUES (
    uuid(),
    <solution_id>,
    'AKo',
    'BB',
    'preflop',
    'facing_open',
    '{"fold": 0.0, "call": 0.275, "3bet": 0.725}',  -- from GTOWizard
    '3bet',
    0.725
);
```

### **Option 2: Dedicated Preflop Tables (Alternative)**

Create specialized preflop tables if you want cleaner separation:

```sql
CREATE TABLE gto_preflop_scenarios (
    scenario_id UUID PRIMARY KEY,
    scenario_name VARCHAR(100) UNIQUE,  -- e.g., 'BB_vs_UTG_call'
    position VARCHAR(10),               -- e.g., 'BB'
    opponent_position VARCHAR(10),      -- e.g., 'UTG'
    action VARCHAR(20),                 -- e.g., 'call', '3bet'
    category VARCHAR(50)                -- e.g., 'defense', 'facing_3bet'
);

CREATE TABLE gto_preflop_frequencies (
    frequency_id UUID PRIMARY KEY,
    scenario_id UUID REFERENCES gto_preflop_scenarios,
    hand VARCHAR(4),                    -- e.g., 'AKo', 'JTs', '22'
    frequency DECIMAL(10, 8),           -- e.g., 0.725 (72.5%)

    UNIQUE (scenario_id, hand)
);

CREATE INDEX idx_preflop_freq_scenario ON gto_preflop_frequencies(scenario_id);
CREATE INDEX idx_preflop_freq_hand ON gto_preflop_frequencies(hand);
```

---

## Implementation Plan

### **Step 1: Adapt GTOWizard Data Format**

Create script to convert your 147 scenarios to Ploit format:

```python
#!/usr/bin/env python3
"""
Convert GTOWizard ranges to Ploit GTO format
"""

import re
import uuid
from datetime import datetime
from database import SessionLocal
from models.gto_models import GTOSolution, GTOStrategyCache

def parse_gtowizard_file():
    """Parse gtowizard_ranges.txt"""
    with open('solver/gtowizard_ranges.txt', 'r') as f:
        content = f.read()

    pattern = r'\[DONE\]\s+(\w+)\s*\n#\s*GTOWizard:\s*(.*?)\n(.*?)\n\n'
    scenarios = {}

    for match in re.finditer(pattern, content, re.DOTALL):
        scenario_name = match.group(1)
        combos = parse_combo_range(match.group(3).strip())
        scenarios[scenario_name] = combos

    return scenarios

def aggregate_to_hands(combos):
    """Group combos by hand type"""
    hands = {}
    for combo, freq in combos.items():
        hand = combo_to_hand(combo)
        if hand not in hands:
            hands[hand] = []
        hands[hand].append(freq)

    # Average frequencies for each hand
    return {hand: sum(freqs)/len(freqs) for hand, freqs in hands.items()}

def import_preflop_to_ploit():
    """Import all preflop scenarios to Ploit GTO tables"""
    scenarios = parse_gtowizard_file()
    db = SessionLocal()

    for scenario_name, combos in scenarios.items():
        # Parse scenario name
        position, opponent, action = parse_scenario_name(scenario_name)

        # Create GTOSolution entry
        solution = GTOSolution(
            solution_id=str(uuid.uuid4()),
            scenario_name=scenario_name,
            board="PREFLOP",
            board_category_l1="PREFLOP",
            board_category_l2=f"{position}_vs_{opponent}",
            board_category_l3=action,
            scenario_type="preflop",
            position_context=f"{position}_vs_{opponent}",
            accuracy=1.0,  # GTOWizard data
            solving_time_seconds=0
        )
        db.add(solution)
        db.flush()

        # Aggregate combos to hands
        hands = aggregate_to_hands(combos)

        # Create GTOStrategyCache entries
        for hand, frequency in hands.items():
            if frequency > 0:  # Only store hands in range
                cache_entry = GTOStrategyCache(
                    cache_id=str(uuid.uuid4()),
                    solution_id=solution.solution_id,
                    hand=hand,
                    position=position,
                    street="preflop",
                    action_node=determine_action_node(scenario_name),
                    strategy_json={action: frequency},
                    primary_action=action,
                    primary_action_freq=frequency
                )
                db.add(cache_entry)

    db.commit()
    print(f"Imported {len(scenarios)} preflop scenarios")

def determine_action_node(scenario_name):
    """Map scenario to action node"""
    if '_open' in scenario_name:
        return 'open'
    elif '_3bet_' in scenario_name and not scenario_name.endswith('_3bet'):
        return 'facing_3bet'
    elif '_4bet_' in scenario_name:
        return 'facing_4bet'
    elif 'vs_' in scenario_name:
        return 'facing_open'
    return 'unknown'

if __name__ == '__main__':
    import_preflop_to_ploit()
```

### **Step 2: Update GTOService**

Extend your existing `GTOService` to handle preflop queries:

```python
# In backend/services/gto_service.py

class GTOService:

    def get_preflop_gto_action(
        self,
        position: str,
        opponent_position: str,
        hand: str,
        action: str
    ) -> Optional[float]:
        """
        Get GTO frequency for preflop action

        Args:
            position: Player position (e.g., 'BB')
            opponent_position: Opponent position (e.g., 'UTG')
            hand: Hand type (e.g., 'AKo')
            action: Action to check (e.g., 'call', '3bet')

        Returns:
            Frequency (0.0 to 1.0) or None if not found
        """
        scenario_name = f"{position}_vs_{opponent_position}_{action}"

        result = self.db.query(GTOStrategyCache).join(
            GTOSolution
        ).filter(
            GTOSolution.scenario_name == scenario_name,
            GTOStrategyCache.hand == hand,
            GTOStrategyCache.street == 'preflop'
        ).first()

        if result:
            return result.primary_action_freq
        return 0.0  # Not in range

    def get_preflop_action_breakdown(
        self,
        position: str,
        opponent_position: str,
        hand: str
    ) -> Dict[str, float]:
        """
        Get all action frequencies for a preflop situation

        Returns:
            {"fold": 0.425, "call": 0.575, "3bet": 0.0}
        """
        # Query all actions for this position vs opponent
        actions = ['fold', 'call', '3bet', '4bet', 'allin']
        frequencies = {}

        for action in actions:
            freq = self.get_preflop_gto_action(
                position, opponent_position, hand, action
            )
            if freq > 0:
                frequencies[action] = freq

        return frequencies

    def compare_player_preflop(
        self,
        player_name: str,
        position: str,
        opponent_position: str
    ) -> Dict:
        """
        Compare player's preflop play to GTO

        Returns detailed leak analysis for this position matchup
        """
        # Get player's actual actions in this spot
        player_actions = self.db.query(PlayerHandSummary).filter(
            PlayerHandSummary.player_name == player_name,
            PlayerHandSummary.position == position,
            # Filter for hands where opponent opened from opponent_position
            # (requires join to hand_actions table)
        ).all()

        # Compare each hand to GTO
        leaks = []
        for hand_summary in player_actions:
            hand = hand_summary.hole_cards
            actual_action = hand_summary.action_taken

            # Get GTO frequencies
            gto_freqs = self.get_preflop_action_breakdown(
                position, opponent_position, hand
            )

            # Calculate deviation
            gto_freq = gto_freqs.get(actual_action, 0)

            if gto_freq == 0:
                leak_type = "CRITICAL"  # Taking action GTO never takes
            elif gto_freq < 0.1:
                leak_type = "MODERATE"  # Rare action
            else:
                leak_type = None  # Acceptable

            if leak_type:
                leaks.append({
                    'hand': hand,
                    'actual_action': actual_action,
                    'gto_frequency': gto_freq,
                    'leak_type': leak_type
                })

        return {
            'total_hands': len(player_actions),
            'leaks': leaks,
            'leak_count': len(leaks),
            'gto_adherence': 1 - (len(leaks) / len(player_actions))
        }
```

### **Step 3: Create Preflop API Endpoints**

Add to `backend/api/gto_endpoints.py`:

```python
@router.get("/preflop/action")
async def get_preflop_gto_action(
    position: str,
    opponent: str,
    hand: str,
    action: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get GTO frequency for specific preflop action

    Example: /api/gto/preflop/action?position=BB&opponent=UTG&hand=AKo&action=3bet
    Returns: {"frequency": 0.725}
    """
    frequency = gto_service.get_preflop_gto_action(
        position, opponent, hand, action
    )
    return {"frequency": frequency}

@router.get("/preflop/breakdown")
async def get_preflop_breakdown(
    position: str,
    opponent: str,
    hand: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Get all action frequencies for a hand

    Example: /api/gto/preflop/breakdown?position=BB&opponent=UTG&hand=JTs
    Returns: {"fold": 0.0, "call": 0.595, "3bet": 0.405}
    """
    frequencies = gto_service.get_preflop_action_breakdown(
        position, opponent, hand
    )
    return frequencies

@router.get("/preflop/compare/{player_name}")
async def compare_player_preflop(
    player_name: str,
    position: str,
    opponent: str,
    gto_service: GTOService = Depends(get_gto_service)
):
    """
    Compare player's preflop strategy to GTO

    Example: /api/gto/preflop/compare/Villain1?position=BB&opponent=UTG
    """
    comparison = gto_service.compare_player_preflop(
        player_name, position, opponent
    )
    return comparison
```

### **Step 4: Enhance Claude's Preflop Knowledge**

Update Claude system prompt in `backend/services/claude_service.py`:

```python
PREFLOP_GTO_KNOWLEDGE = """
## Preflop GTO Data

You now have access to 147 preflop GTO scenarios from GTOWizard, including:

- **Opening ranges** (5 positions: UTG, MP, CO, BTN, SB)
- **BB defense** vs all opens (fold/call/3bet frequencies)
- **SB defense** vs all opens
- **IP cold calls** (CO, BTN facing opens)
- **Facing 3bets** (fold/call/4bet/allin)
- **Facing 4bets** (fold/call/5bet/allin)
- **Multiway scenarios** (squeezes, overcalls)

### Querying Preflop GTO

```sql
-- Get all hands BB should call vs UTG open
SELECT hand, primary_action_freq
FROM gto_strategy_cache gsc
JOIN gto_solutions gs ON gsc.solution_id = gs.solution_id
WHERE gs.scenario_name = 'BB_vs_UTG_call'
  AND gsc.street = 'preflop'
  AND gsc.primary_action_freq > 0
ORDER BY gsc.primary_action_freq DESC;

-- Compare player to GTO
SELECT
    phs.hole_cards as hand,
    phs.action_taken,
    gsc.primary_action_freq as gto_frequency,
    CASE
        WHEN gsc.primary_action_freq = 0 THEN 'CRITICAL LEAK'
        WHEN gsc.primary_action_freq < 0.1 THEN 'MODERATE LEAK'
        ELSE 'ACCEPTABLE'
    END as assessment
FROM player_hand_summary phs
LEFT JOIN gto_strategy_cache gsc ON gsc.hand = phs.hole_cards
WHERE phs.player_name = 'Villain1'
  AND phs.position = 'BB'
  AND gsc.street = 'preflop';
```

### Interpreting Preflop GTO

- **Frequency 1.0 (100%)**: Pure action (always do this)
- **Frequency 0.5-0.9**: Strong preference, do most of the time
- **Frequency 0.1-0.5**: Mixed strategy, balance required
- **Frequency < 0.1**: Rare action, mostly for balance
- **Frequency 0.0**: Never take this action

### Example Analysis

"BB vs UTG open with JTs:
- GTO: Call 59.5%, 3bet 40.5%, Fold 0%
- If player folds JTs here → CRITICAL LEAK (missing EV)"
"""

# Add to system prompt
self.system_prompt += "\n\n" + PREFLOP_GTO_KNOWLEDGE
```

### **Step 5: Frontend Components**

Create React component to visualize preflop GTO:

```typescript
// frontend/src/components/PreflopGTOMatrix.tsx

interface PreflopGTOMatrixProps {
  position: string;
  opponent: string;
}

export function PreflopGTOMatrix({ position, opponent }: PreflopGTOMatrixProps) {
  const [gtoData, setGtoData] = useState<Record<string, ActionFrequencies>>();

  useEffect(() => {
    // Fetch GTO data for all hands
    apiClient.get(`/gto/preflop/all?position=${position}&opponent=${opponent}`)
      .then(data => setGtoData(data));
  }, [position, opponent]);

  return (
    <div className="grid grid-cols-13">
      {POKER_HANDS.map(hand => (
        <HandCell
          key={hand}
          hand={hand}
          frequencies={gtoData[hand]}
        />
      ))}
    </div>
  );
}

function HandCell({ hand, frequencies }) {
  const primaryAction = Object.keys(frequencies).reduce((a, b) =>
    frequencies[a] > frequencies[b] ? a : b
  );

  const color = {
    'fold': 'bg-red-200',
    'call': 'bg-blue-200',
    '3bet': 'bg-green-200',
    '4bet': 'bg-yellow-200'
  }[primaryAction];

  return (
    <div className={`${color} p-2 text-center`}>
      <div className="font-bold">{hand}</div>
      <div className="text-xs">
        {(frequencies[primaryAction] * 100).toFixed(0)}%
      </div>
    </div>
  );
}
```

---

## Claude Integration Examples

### **Example 1: Ask Claude About Preflop Strategy**

```
User: "How should I defend BB vs UTG open with ATo?"

Claude: Let me check the GTO frequencies for that spot.

[Claude queries database]

SELECT hand, primary_action_freq, primary_action
FROM gto_strategy_cache gsc
JOIN gto_solutions gs ON gsc.solution_id = gs.solution_id
WHERE gs.scenario_name IN ('BB_vs_UTG_fold', 'BB_vs_UTG_call', 'BB_vs_UTG_3bet')
  AND gsc.hand = 'ATo'
  AND gsc.street = 'preflop';

Results:
- BB_vs_UTG_fold: 17.5%
- BB_vs_UTG_call: 82.5%
- BB_vs_UTG_3bet: 0%

Claude: BB should defend ATo vs UTG open by calling 82.5% of the time and folding 17.5%.
Never 3bet with ATo in this spot - it's a pure call or fold situation, heavily weighted
toward calling. This hand has good equity but not enough to 3bet against UTG's tight range.
```

### **Example 2: Leak Detection**

```
User: "Am I defending BB correctly vs UTG opens?"

Claude: Let me analyze your BB defense vs UTG.

[Queries player_hand_summary + gto_strategy_cache]

Found 45 hands where you faced UTG open from BB.

Your defense frequency: 27% (12/45 hands defended)
GTO defense frequency: ~27% overall - you're in the right ballpark!

But looking at specific hands:
- ATo: You folded 100% (5/5 times) | GTO: Call 82.5%
  → LEAK: Folding a profitable call

- QJo: You folded 80% (4/5 times) | GTO: Call 57.5%
  → LEAK: Slightly overfolding

- KQo: You 3bet 100% (3/3 times) | GTO: Call 78%, 3bet 22%
  → Minor imbalance, but acceptable

Overall: You're defending the correct frequency, but with the wrong hands.
You're calling too tight and missing profitable defends.

Recommendation: Add ATo, KTo, QJo to your calling range vs UTG.
```

### **Example 3: Opponent Exploitation**

```
User: "How can I exploit Villain1's preflop play?"

Claude: Let me analyze Villain1's preflop tendencies vs GTO.

[Queries player_hand_summary for Villain1]

Analyzing Villain1's BB defense vs your UTG opens (23 hands):

Villain1 folds BB: 82.6% (19/23 hands)
GTO folds BB vs UTG: 73.5%
Deviation: +9.1% (overfolding)

Hands where Villain1 folded that GTO defends:
- ATo (GTO calls 82.5%) - Villain1 folded 100% (3/3)
- QJo (GTO calls 57.5%) - Villain1 folded 100% (2/2)
- K7s (GTO calls 43%) - Villain1 folded 100% (1/1)

EXPLOIT: Open wider from UTG vs this player!
- GTO UTG opening range: 17.7%
- Exploitative range vs Villain1: ~23-25%

Add hands like: K9s, QTs, JTo, A8o
Expected profit: +0.8 BB per hand (from increased fold equity)
```

---

## Migration Checklist

- [ ] **Step 1**: Create import script (`import_gtowizard_to_ploit.py`)
- [ ] **Step 2**: Run import (147 scenarios → gto_solutions + gto_strategy_cache)
- [ ] **Step 3**: Update `GTOService` with preflop methods
- [ ] **Step 4**: Add `/api/gto/preflop/*` endpoints
- [ ] **Step 5**: Update Claude system prompt with preflop knowledge
- [ ] **Step 6**: Test queries:
  - `SELECT * FROM gto_solutions WHERE scenario_type = 'preflop'`
  - `SELECT * FROM gto_strategy_cache WHERE street = 'preflop' AND hand = 'AKo'`
- [ ] **Step 7**: Test API endpoints
- [ ] **Step 8**: Create frontend components (optional)
- [ ] **Step 9**: Ask Claude preflop questions
- [ ] **Step 10**: Run full leak detection on sample player

---

## Benefits of This Integration

1. **Leverage Existing Infrastructure** - No new tables, services, or patterns
2. **Claude Gets Smarter** - Can now answer ANY preflop question with GTO data
3. **Unified Analysis** - Preflop + postflop in same system
4. **Automatic Leak Detection** - Existing comparison logic works for preflop
5. **Exploit Generation** - Same deviation analysis applies
6. **Future Proof** - Can add more preflop scenarios (4bet ranges, squeezes, etc.)

---

## Next Steps

1. Adapt the GTOWizard import script to Ploit's schema
2. Run import and verify data
3. Test Claude queries
4. Build frontend visualization (optional)
5. Start analyzing actual player data with full preflop GTO coverage!
