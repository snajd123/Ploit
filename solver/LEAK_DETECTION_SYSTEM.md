# PLOIT: GTO Leak Detection & Exploitation System
## Complete Architecture & Implementation Plan

---

## 🎯 **Core Objectives**

1. **Leak Detection** - Identify where you deviate from GTO
2. **Leak Improvement** - Provide actionable recommendations to fix your leaks
3. **Exploit Finding** - Identify opponent leaks/tendencies
4. **Exploit Execution** - Show optimal exploitative adjustments in real-time

---

## 📊 **System Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐          ┌───────────────────┐           │
│  │  GTOWizard       │          │  Player Hand      │           │
│  │  Preflop Ranges  │          │  Histories        │           │
│  │  (147 scenarios) │          │  (Actual play)    │           │
│  └────────┬─────────┘          └─────────┬─────────┘           │
│           │                               │                      │
│           └───────────┬───────────────────┘                      │
│                       ▼                                          │
│              ┌─────────────────┐                                │
│              │   PostgreSQL    │                                │
│              │    Database     │                                │
│              └─────────────────┘                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ANALYSIS ENGINE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. HAND PARSER                                        │    │
│  │     • Parse hand history (PokerTracker/HM3/text)      │    │
│  │     • Extract: position, action, hole cards, board    │    │
│  │     • Identify decision points (preflop for now)      │    │
│  └────────────────────────────────────────────────────────┘    │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  2. SCENARIO MATCHER                                   │    │
│  │     • Match situation to GTO scenario                  │    │
│  │     • Example: "UTG opens, you're BB with AKo"        │    │
│  │     • Lookup scenarios: BB_vs_UTG_fold/call/3bet      │    │
│  └────────────────────────────────────────────────────────┘    │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  3. GTO COMPARATOR                                     │    │
│  │     • Get GTO frequencies for each action              │    │
│  │     • Compare actual action to GTO recommendation      │    │
│  │     • Calculate deviation / EV loss                    │    │
│  └────────────────────────────────────────────────────────┘    │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  4. LEAK AGGREGATOR                                    │    │
│  │     • Group leaks by category (defense, 3bet, etc.)   │    │
│  │     • Track frequency of each leak                     │    │
│  │     • Calculate cumulative EV loss                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 EXPLOIT CALCULATOR                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  5. TENDENCY ANALYZER                                  │    │
│  │     • Identify opponent patterns                       │    │
│  │     • "Folds BB vs UTG 85% (GTO: 73%)"               │    │
│  │     • "3bets BTN vs CO 5% (GTO: 12%)"                │    │
│  └────────────────────────────────────────────────────────┘    │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  6. COUNTER-STRATEGY GENERATOR                         │    │
│  │     • Calculate exploitative adjustments               │    │
│  │     • If opponent folds too much → increase bluffs     │    │
│  │     • If opponent calls too wide → value bet thinner   │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  My Leaks    │  │  Opponent    │  │  Exploits    │         │
│  │  Dashboard   │  │  Analysis    │  │  In Action   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 **1. LEAK DETECTION (Your Game)**

### **A. Detection Algorithm**

```python
def detect_leaks(player_hands):
    """
    Analyze player's hands and identify leaks
    """
    leaks = []

    for hand in player_hands:
        # Step 1: Identify scenario
        scenario = identify_scenario(hand)
        # Example: "BB_vs_UTG" when UTG opens and player is in BB

        # Step 2: Get all possible actions with GTO frequencies
        gto_actions = get_gto_actions(scenario, hand.hole_cards)
        # Example: {'fold': 0.425, 'call': 0.575, '3bet': 0.0}

        # Step 3: Compare actual action to GTO
        actual_action = hand.action_taken
        gto_frequency = gto_actions.get(actual_action, 0)

        # Step 4: Classify deviation
        if gto_frequency == 0:
            # MAJOR LEAK: Taking action that should NEVER be taken
            leak_type = "CRITICAL"
            ev_loss = estimate_ev_loss_critical(scenario, hand)

        elif gto_frequency < 0.1:
            # MODERATE LEAK: Taking rare action too often
            leak_type = "MODERATE"
            ev_loss = estimate_ev_loss_moderate(scenario, hand, gto_frequency)

        elif gto_frequency > 0.9:
            # Correct pure action
            leak_type = None
            ev_loss = 0

        else:
            # MIXED STRATEGY: Acceptable deviation
            # Track frequency to ensure proper mixing
            leak_type = "TRACKING"
            ev_loss = 0

        if leak_type:
            leaks.append({
                'hand_id': hand.id,
                'scenario': scenario,
                'hole_cards': hand.hole_cards,
                'actual_action': actual_action,
                'gto_frequency': gto_frequency,
                'leak_type': leak_type,
                'ev_loss': ev_loss
            })

    return leaks
```

### **B. Leak Categories**

1. **Opening Leaks**
   - Too tight (missing EV by not opening)
   - Too loose (losing chips with weak opens)

2. **Defense Leaks**
   - Overfolding (exploitable by aggressive opponents)
   - Underfolding (calling too wide, losing to value)

3. **3bet Leaks**
   - Under-3betting (missing value/fold equity)
   - Over-3betting (too polarized/too linear)

4. **Facing 3bet Leaks**
   - Folding too much (exploitable by light 3bets)
   - 4betting too light (losing to calling stations)

5. **Multiway Leaks**
   - Overcalling (entering multiway pots too wide)
   - Missing squeezes (not capitalizing on dead money)

### **C. EV Loss Calculation**

```python
def estimate_ev_loss(scenario, hand, gto_frequency):
    """
    Estimate EV loss from deviation
    Uses simplified model based on action type
    """

    # Base EV costs (in big blinds)
    base_costs = {
        'fold_when_should_call': 0.5,      # Missing pot equity
        'fold_when_should_3bet': 1.0,      # Missing fold equity + value
        'call_when_should_fold': 1.5,      # Calling into better range
        '3bet_when_should_fold': 3.0,      # Risking chips with weak hand
        '4bet_when_should_fold': 5.0,      # Huge mistake
    }

    # Adjust based on how far off GTO we are
    mistake_key = f"{hand.action_taken}_when_should_{get_gto_action(scenario, hand)}"
    base_cost = base_costs.get(mistake_key, 0)

    # Scale by how pure the GTO action is
    ev_loss = base_cost * (1 - gto_frequency)

    return ev_loss
```

---

## 📈 **2. LEAK IMPROVEMENT (Fixing Your Game)**

### **A. Improvement Recommendations**

```python
def generate_improvement_plan(player_leaks):
    """
    Generate actionable recommendations to fix leaks
    Prioritized by EV impact
    """

    # Group leaks by category
    grouped_leaks = group_by_category(player_leaks)

    recommendations = []

    for category, leaks in grouped_leaks.items():
        total_ev_loss = sum(leak['ev_loss'] for leak in leaks)
        frequency = len(leaks)

        # Generate specific recommendation
        if category == 'defense':
            if most_common_leak(leaks) == 'fold':
                rec = {
                    'category': 'BB Defense',
                    'issue': f"Folding BB {frequency} times (-{total_ev_loss:.2f} BB)",
                    'fix': "Expand calling/3betting ranges vs aggressive opens",
                    'priority': calculate_priority(total_ev_loss, frequency),
                    'specific_hands': get_specific_hands_to_defend(leaks),
                    'ev_gain': total_ev_loss  # Potential gain if fixed
                }

        elif category == 'facing_3bet':
            if most_common_leak(leaks) == 'fold':
                rec = {
                    'category': 'Facing 3bets',
                    'issue': f"Folding to 3bets {frequency} times (-{total_ev_loss:.2f} BB)",
                    'fix': "4bet or call more hands that have good equity",
                    'priority': calculate_priority(total_ev_loss, frequency),
                    'specific_hands': get_hands_to_continue_vs_3bet(leaks),
                    'ev_gain': total_ev_loss
                }

        recommendations.append(rec)

    # Sort by priority (highest EV gain first)
    return sorted(recommendations, key=lambda x: x['priority'], reverse=True)
```

### **B. Training Mode**

```
┌─────────────────────────────────────────────────────────────┐
│  LEAK IMPROVEMENT TRAINING                                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Your Biggest Leak: Folding BB vs UTG too often             │
│  EV Loss: -3.2 BB/100 hands                                 │
│  Frequency: 85% fold (GTO: 73%)                             │
│                                                               │
│  ┌─────────────────────────────────────────────────┐        │
│  │  HANDS TO DEFEND MORE:                          │        │
│  │                                                  │        │
│  │  ATo  - You fold 100% | GTO: Call 82.5%        │        │
│  │  K7s  - You fold 90%  | GTO: Call 43%          │        │
│  │  QJo  - You fold 80%  | GTO: Call 57.5%        │        │
│  │  T9s  - You fold 100% | GTO: 3bet 81%          │        │
│  └─────────────────────────────────────────────────┘        │
│                                                               │
│  💡 TIP: These hands have good equity vs UTG's range.       │
│          Start by calling 50% of the time, then increase.   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 **3. EXPLOIT FINDING (Opponent Analysis)**

### **A. Opponent Profiling**

```python
def profile_opponent(opponent_hands):
    """
    Build detailed profile of opponent's tendencies
    """

    profile = {
        'player_name': opponent_hands[0].player_name,
        'total_hands': len(opponent_hands),
        'tendencies': {},
        'exploits': []
    }

    # Analyze each scenario
    for scenario in get_unique_scenarios(opponent_hands):
        hands_in_scenario = filter_by_scenario(opponent_hands, scenario)

        # Calculate frequencies
        action_counts = count_actions(hands_in_scenario)
        total = len(hands_in_scenario)

        for action, count in action_counts.items():
            player_freq = count / total
            gto_freq = get_avg_gto_frequency(scenario, action)

            deviation = player_freq - gto_freq

            # Significant deviation = exploitable tendency
            if abs(deviation) > 0.15:  # 15% threshold
                tendency = {
                    'scenario': scenario,
                    'action': action,
                    'player_frequency': player_freq,
                    'gto_frequency': gto_freq,
                    'deviation': deviation,
                    'sample_size': count,
                    'exploitable': True
                }

                profile['tendencies'][f"{scenario}_{action}"] = tendency

    return profile
```

### **B. Exploitable Patterns**

| **Opponent Tendency** | **Leak** | **Exploit** |
|----------------------|----------|-------------|
| Folds BB 85% vs UTG (GTO: 73%) | Overfolding | Open wider from UTG, increase bluff frequency |
| 3bets BTN vs CO 5% (GTO: 12%) | Under-3betting | Raise more from CO, steal blinds aggressively |
| Folds to 3bet 80% (GTO: 60%) | Weak vs aggression | 3bet light, high fold equity |
| Calls 3bets 35% (GTO: 20%) | Overcalling 3bets | 3bet for value wider, reduce bluffs |
| 4bets 2% (GTO: 8%) | Never 4bets | 3bet more hands, they won't fight back |
| Folds to 4bet 90% (GTO: 70%) | Scared of 4bets | 4bet bluff frequently |

### **C. Live Exploit Recommendations**

```
┌─────────────────────────────────────────────────────────────┐
│  OPPONENT: Villain1                                          │
│  Sample: 450 hands                                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🎯 BIGGEST EXPLOIT: Folds BB vs BTN 68% (GTO: 56.7%)      │
│      → Open 100% of BTN vs this player (GTO: 42%)          │
│      → Expected profit: +2.8 BB/100                         │
│                                                               │
│  🎯 EXPLOIT #2: Never 4bets (0% in 23 opportunities)        │
│      → 3bet lighter vs this opponent                        │
│      → They will fold or call, never fight back             │
│      → Expected profit: +1.5 BB/100                         │
│                                                               │
│  🎯 EXPLOIT #3: Calls 3bets too wide (32% vs GTO 20%)      │
│      → 3bet for value wider, reduce bluff frequency         │
│      → Hands like AJo, KQo are pure value vs this range    │
│      → Expected profit: +0.8 BB/100                         │
│                                                               │
│  📊 Total Exploitative Edge: +5.1 BB/100                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ **4. EXPLOIT EXECUTION (Real-Time Guidance)**

### **A. HUD Integration (Future)**

```
During live play, display:

┌─────────────────────────────────┐
│  VILLAIN1 (BB)                  │
│  Tendencies:                    │
│  • Folds BB 68% ⬆️ (GTO: 57%)   │
│  • Never 4bets ⚠️               │
│                                  │
│  Recommended Adjustments:       │
│  • Open 100% from BTN           │
│  • 3bet light vs their opens    │
│                                  │
│  EV Gain: +5.1 BB/100          │
└─────────────────────────────────┘

YOUR HAND: A♠ 7♠
POSITION: BTN
VILLAIN1 OPENS MP

┌─────────────────────────────────┐
│  GTO: 3bet 0% | Fold 35%        │
│                                  │
│  ⚡ EXPLOIT:                     │
│  3bet here! Villain folds to    │
│  3bets 80% (GTO: 60%)          │
│                                  │
│  Expected outcome:              │
│  Fold: 80% (+3.5 BB)           │
│  Call: 20% (-0.5 BB)           │
│                                  │
│  EV: +2.7 BB                    │
└─────────────────────────────────┘
```

### **B. Session Review**

```
After session, show:

┌──────────────────────────────────────────────────────────────┐
│  SESSION SUMMARY                                              │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  Hands Played: 250                                            │
│  GTO Decisions: 178 (71%)                                     │
│  Exploitative Plays: 42 (17%)                                │
│  Leaks: 30 (12%)                                             │
│                                                                │
│  ╔══════════════════════════════════════════════════════╗    │
│  ║  YOUR PERFORMANCE                                    ║    │
│  ╚══════════════════════════════════════════════════════╝    │
│                                                                │
│  ✅ Improved: BB Defense                                      │
│      Folding 75% (down from 85%, target: 73%)                │
│      Progress: 👍 Getting closer!                            │
│                                                                │
│  ⚠️  Still Leaking: Facing 3bets                             │
│      Folding 78% (GTO: 65%)                                  │
│      Cost: -1.2 BB this session                              │
│                                                                │
│  ╔══════════════════════════════════════════════════════╗    │
│  ║  EXPLOITS EXECUTED                                   ║    │
│  ╚══════════════════════════════════════════════════════╝    │
│                                                                │
│  🎯 vs Villain1: Opened 95% from BTN (GTO: 42%)              │
│      Result: Won 12 BB from increased fold equity            │
│                                                                │
│  🎯 vs Villain2: 3bet light 8 times (they fold to 3bet 85%)  │
│      Result: Won 18 BB                                        │
│                                                                │
│  💰 Total Exploitative Profit: +30 BB                         │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠️ **Implementation Phases**

### **Phase 1: Database & Import (Current)**
- ✅ Design database schema
- ✅ Create import script
- ⏳ Import 147 preflop scenarios
- ⏳ Verify data integrity

### **Phase 2: Hand History Parser**
- Parse PokerTracker/HM3 hand histories
- Extract relevant decision points
- Map to GTO scenarios
- Store in `player_hands` table

### **Phase 3: Leak Detection Engine**
- Implement comparison algorithm
- Calculate EV loss estimates
- Generate leak reports
- Build improvement recommendations

### **Phase 4: Opponent Analysis**
- Profile opponent tendencies
- Identify exploitable patterns
- Calculate exploitative adjustments
- Generate real-time recommendations

### **Phase 5: User Interface**
- Build dashboard for leak reports
- Create opponent analysis view
- Display real-time exploit suggestions
- Session review system

### **Phase 6: Postflop Integration**
- Import GTOWizard postflop aggregate reports
- Extend analysis to flop/turn/river decisions
- Complete end-to-end leak detection

---

## 📝 **Key Formulas**

### **EV Loss Calculation**
```
EV_loss = Σ (GTO_action_EV - Actual_action_EV) × Frequency

Simplified:
EV_loss ≈ Base_cost × (1 - GTO_frequency) × Sample_size
```

### **Exploit Value**
```
Exploit_value = (Opponent_frequency - GTO_frequency) × Pot_size × Fold_equity

Example:
Opponent folds BB 85% vs UTG (GTO: 73%)
Deviation = 12%
Average pot = 2.5 BB
Fold equity gain = 12% × 2.5 = 0.3 BB per hand
Over 100 hands = +30 BB/100
```

### **Priority Score**
```
Priority = EV_impact × √(Sample_size) / 100

Higher priority = fix first
```

---

## 🎓 **Next Steps**

1. **Review this architecture** - Any changes needed?
2. **Set up PostgreSQL database** - Run schema.sql
3. **Import preflop data** - Run import script
4. **Build hand parser** - Start with simple text format
5. **Implement leak detector** - Core comparison algorithm

Ready to start building? 🚀
