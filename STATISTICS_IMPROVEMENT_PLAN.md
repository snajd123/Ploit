# Statistics & Analytics Improvement Plan

## Overview

This plan addresses critical gaps in the statistical rigor and analytical capabilities of the poker analysis platform. The goal is to make stats **trustworthy, actionable, and calibrated** to real GTO baselines.

---

## Phase 1: Statistical Foundation (Priority: Critical)

### 1.1 Implement Confidence Intervals

**Problem:** A player with 50% VPIP over 20 hands is shown the same as 50% over 2000 hands.

**Solution:** Add Wilson score confidence intervals for all percentage stats.

**Implementation:**
```python
# backend/services/confidence_calculator.py
def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple:
    """Returns (lower_bound, upper_bound, reliability_level)"""
    if trials == 0:
        return (0, 100, "insufficient")

    z = 1.96  # 95% confidence
    p = successes / trials

    denominator = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denominator
    spread = z * sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator

    lower = max(0, (center - spread) * 100)
    upper = min(100, (center + spread) * 100)

    # Reliability based on confidence interval width
    width = upper - lower
    if width > 30:
        reliability = "low"
    elif width > 15:
        reliability = "moderate"
    elif width > 8:
        reliability = "good"
    else:
        reliability = "excellent"

    return (round(lower, 1), round(upper, 1), reliability)
```

**Frontend Display:**
- Show stat as: `VPIP: 32.5% (28-37%)` with color-coded reliability
- Green checkmark: <8% CI width (excellent)
- Yellow warning: 8-15% CI width (moderate)
- Gray/dim: >15% CI width (low confidence)

**Files to modify:**
- `backend/services/stats_calculator.py` - Add CI calculation
- `backend/models/database_models.py` - Add CI fields to PlayerStats
- `frontend/src/components/StatCard.tsx` - Display CI and reliability

**Validation:** Compare calculated CIs with known poker statistics tools (PT4, H2N).

---

### 1.2 Calibrate GTO Baselines to Real Solver Output

**Problem:** Current baselines are made up:
- `fold_to_3bet: 55%` (actual GTO: 30-50% depending on position)
- `WTSD: 27%` (actual GTO: 35-40%)
- `VPIP: 23%` (only correct for 6-max TAG)

**Solution:** Replace hardcoded values with position-specific GTO frequencies from solver output.

**New Baseline Structure:**
```python
# backend/config/gto_baselines.py
GTO_BASELINES = {
    "6max_100bb": {
        "UTG": {
            "vpip": 19.0,
            "pfr": 17.0,
            "open_raise": 17.0,
            "fold_to_3bet": 45.0,  # Position-specific
            "3bet_vs_open": 0.0,   # Can't 3bet if first to act
        },
        "HJ": {
            "vpip": 22.0,
            "pfr": 20.0,
            "open_raise": 20.0,
            "fold_to_3bet": 42.0,
        },
        "CO": {
            "vpip": 27.0,
            "pfr": 24.0,
            "open_raise": 24.0,
            "fold_to_3bet": 38.0,
        },
        "BTN": {
            "vpip": 44.0,
            "pfr": 40.0,
            "open_raise": 40.0,
            "fold_to_3bet": 35.0,
        },
        "SB": {
            "vpip": 36.0,
            "pfr": 28.0,
            "open_raise": 28.0,
            "fold_to_3bet": 40.0,
            "3bet_vs_btn": 12.0,
        },
        "BB": {
            "vpip": 40.0,  # Includes calls + 3bets
            "pfr": 12.0,
            "3bet_vs_utg": 4.0,
            "3bet_vs_btn": 10.0,
            "fold_to_steal": 50.0,
        },
        # Global stats (position-averaged)
        "global": {
            "cbet_flop": 33.0,  # Modern GTO is polarized, not 65%
            "cbet_turn": 45.0,
            "cbet_river": 50.0,
            "fold_to_cbet_flop": 40.0,
            "fold_to_cbet_turn": 42.0,
            "wtsd": 38.0,
            "wsd": 52.0,
        }
    }
}
```

**Source:** These values should be extracted from GTOWizard/Monker solutions for 100bb 6-max.

**Files to modify:**
- `backend/config/gto_baselines.py` (new file)
- `backend/services/gto_service.py` - Use position-specific baselines
- `backend/services/opponent_analyzer.py` - Reference new baselines
- `backend/services/stats_calculator.py` - Recalibrate EI and other metrics

---

### 1.3 Fix Player Type Classification

**Problem:** Overlapping criteria and arbitrary thresholds.

**Current Issues:**
```
LAG: VPIP >= 25% AND PFR >= 18% AND Gap < 12%
TAG: 15 <= VPIP <= 25% AND 12 <= PFR <= 20% AND Gap < 8%
# Player with VPIP=24%, PFR=19%, Gap=5% matches BOTH
```

**Solution:** Use decision tree with non-overlapping, validated thresholds:

```python
def classify_player_type(vpip: float, pfr: float, total_hands: int) -> str:
    """
    Classification based on 2+2 community standards and GTO theory.
    Requires minimum 100 hands for any classification.
    """
    if total_hands < 100:
        return "UNKNOWN"

    gap = vpip - pfr
    aggression_ratio = pfr / vpip if vpip > 0 else 0

    # Step 1: Check for extreme fish (highest priority)
    if vpip > 50 or gap > 20:
        return "FISH"

    # Step 2: Tightness classification
    is_tight = vpip < 22
    is_loose = vpip > 28

    # Step 3: Aggression classification
    is_passive = aggression_ratio < 0.6  # PFR/VPIP < 60%
    is_aggressive = aggression_ratio > 0.75  # PFR/VPIP > 75%

    # Step 4: Combine into player type
    if is_tight and is_passive:
        return "NIT"
    elif is_tight and is_aggressive:
        return "TAG"
    elif is_loose and is_passive:
        if gap > 15:
            return "CALLING_STATION"
        return "LOOSE_PASSIVE"
    elif is_loose and is_aggressive:
        if vpip > 40 and pfr > 35:
            return "MANIAC"
        return "LAG"
    elif is_aggressive:
        return "TAG"  # Default aggressive to TAG
    elif is_passive:
        return "LOOSE_PASSIVE"  # Default passive to loose-passive
    else:
        return "UNKNOWN"
```

**Validation:** Test against hand history database with known player types.

---

## Phase 2: GTO Analysis Improvements (Priority: High)

### 2.1 Expand Postflop GTO Coverage

**Current State:** Only 5 flop boards in database.

**Goal:** Cover strategically distinct board categories:

**Board Categories to Add:**
```
High dry:        A72r, K82r, Q73r
High wet:        AKQ, KQJ, QJT
Monotone:        Axx (single suit), Kxx, low
Paired:          AA2, KK3, 772
Low connected:   567, 678, 789
Low dry:         732r, 842r, 953r
Two-tone:        AK2 (two suited), KQ3, etc.
```

**Implementation:**
1. Generate GTO solutions using TexasSolver for 20+ board textures
2. Store in `gto_scenarios` table with board_texture category
3. Add board texture detection to hand parser
4. Match player's actual boards to nearest GTO texture

**Files:**
- `backend/services/board_categorizer.py` (new)
- `backend/services/gto_service.py` - Add board matching
- `solver/` - Run new solutions

---

### 2.2 Replace Fake EV Loss with Real Calculations

**Problem:** Current EV loss = `frequency * 0.3` (meaningless).

**Solution:** Use actual EV differences from game trees.

**Simplified Approach (without full solver integration):**

```python
def calculate_preflop_ev_loss(
    hero_action: str,
    gto_action: str,
    gto_frequency: float,
    pot_size_bb: float,
    position: str
) -> float:
    """
    Estimate EV loss based on action type and pot size.
    Uses empirically-derived multipliers from solver analysis.
    """
    if hero_action == gto_action:
        return 0.0

    # Base EV loss depends on action type
    base_loss = {
        ("fold", "raise"): 0.8,   # Folding a raising hand
        ("fold", "call"): 0.4,    # Folding a calling hand
        ("call", "raise"): 0.3,   # Calling instead of raising
        ("call", "fold"): 0.2,    # Calling instead of folding
        ("raise", "fold"): 0.5,   # Raising a folding hand
        ("raise", "call"): 0.2,   # Raising instead of calling
    }.get((hero_action, gto_action), 0.3)

    # Scale by GTO frequency (worse to deviate from high-freq plays)
    freq_multiplier = gto_frequency / 0.5  # Normalized to 50%

    # Scale by pot size
    pot_multiplier = pot_size_bb / 3.5  # Normalized to standard open

    return base_loss * freq_multiplier * pot_multiplier
```

**Future:** Integrate with TexasSolver for true EV at each decision node.

---

### 2.3 Add MDF (Minimum Defense Frequency) Calculations

**What is MDF:** The minimum frequency you must defend to prevent opponent from profiting with any two cards.

**Formula:** `MDF = Pot / (Pot + Bet Size)`

**Implementation:**
```python
def calculate_mdf(pot_size: float, bet_size: float) -> float:
    """Calculate minimum defense frequency."""
    return pot_size / (pot_size + bet_size) * 100

def analyze_fold_exploitability(
    player_fold_freq: float,
    bet_size_pot_pct: float
) -> dict:
    """
    Determine if player folds too much to a given bet size.
    Returns exploit value and recommended bluff frequency.
    """
    # Common bet sizes and their MDFs
    mdf_table = {
        33: 75.0,   # 1/3 pot -> defend 75%
        50: 66.7,   # 1/2 pot -> defend 67%
        67: 60.0,   # 2/3 pot -> defend 60%
        75: 57.1,   # 3/4 pot -> defend 57%
        100: 50.0,  # Pot -> defend 50%
        150: 40.0,  # 1.5x pot -> defend 40%
    }

    mdf = calculate_mdf(100, bet_size_pot_pct)
    fold_excess = player_fold_freq - (100 - mdf)

    if fold_excess > 5:
        return {
            "exploitable": True,
            "fold_excess_pct": fold_excess,
            "recommended_bluff_freq": min(100, 50 + fold_excess),
            "exploit_ev_per_100": fold_excess * 0.03,  # Approximate
            "recommendation": f"Bluff {int(50 + fold_excess)}% of your bluffing range"
        }
    return {"exploitable": False}
```

**Files:**
- `backend/services/mdf_calculator.py` (new)
- `backend/api/gto_endpoints.py` - Add MDF endpoint
- `frontend/src/pages/PlayerProfile.tsx` - Display MDF analysis

---

## Phase 3: Composite Metrics Overhaul (Priority: Medium)

### 3.1 Recalibrate Exploitability Index

**Current Problem:** Uses wrong baselines and arbitrary weights.

**New Formula:**
```python
def calculate_exploitability_index_v2(
    stats: PlayerStats,
    baselines: dict,
    confidence_intervals: dict
) -> dict:
    """
    Calculate EI using calibrated baselines and confidence-weighted deviations.
    """
    deviations = []

    # Preflop deviations (35% weight)
    preflop_factors = [
        ("fold_to_3bet", 0.15, 10),  # Folding too much to 3-bets
        ("vpip_pfr_gap", 0.10, 8),   # Gap indicates passivity
        ("3bet", 0.10, 5),           # 3-bet frequency
    ]

    # Postflop deviations (40% weight)
    postflop_factors = [
        ("fold_to_cbet_flop", 0.15, 10),
        ("fold_to_cbet_turn", 0.15, 10),
        ("cbet_flop", 0.10, 15),     # Over or under c-betting
    ]

    # Showdown deviations (25% weight)
    showdown_factors = [
        ("wtsd", 0.15, 10),
        ("wsd", 0.10, 8),
    ]

    total_ei = 0
    for stat_name, weight, sensitivity in (preflop_factors + postflop_factors + showdown_factors):
        player_val = getattr(stats, stat_name, None)
        baseline = baselines.get(stat_name)
        ci = confidence_intervals.get(stat_name, {})

        if player_val is None or baseline is None:
            continue

        deviation = abs(player_val - baseline)

        # Weight by confidence (less confident = less contribution)
        confidence_weight = 1.0
        if ci.get("reliability") == "low":
            confidence_weight = 0.5
        elif ci.get("reliability") == "moderate":
            confidence_weight = 0.75

        contribution = (deviation / sensitivity) * weight * 100 * confidence_weight
        total_ei += contribution

    return {
        "score": min(100, total_ei),
        "confidence": "high" if all CI good else "moderate",
        "top_leaks": sorted_deviations[:3]
    }
```

---

### 3.2 Simplify to Fewer, More Meaningful Metrics

**Current:** 12 composite metrics (too many, confusing).

**Proposed:** 5 core metrics with clear meaning:

| Metric | What It Measures | Action |
|--------|-----------------|--------|
| **Exploitability Score** | Overall how exploitable (0-100) | Higher = more profit potential |
| **Aggression Profile** | Passive/Balanced/Aggressive | Adjust your bet sizing |
| **Positional Awareness** | Poor/Average/Good | Identify positional leaks |
| **Showdown Tendencies** | Station/Balanced/Nitty | Adjust value/bluff ratio |
| **Pressure Response** | Folds/Calls/Fights | Adjust bluffing frequency |

**Remove:** ACR, RPF, SFG, DAC, MPS, OSSR, VBIR (too granular, overlapping).

---

## Phase 4: Frontend Display Improvements (Priority: Medium)

### 4.1 Add Confidence Indicators to All Stats

**Before:**
```
VPIP: 32.5%
PFR: 24.1%
3-Bet: 8.2%
```

**After:**
```
VPIP: 32.5% ± 4.2   ✓ (847 hands)
PFR: 24.1% ± 3.8    ✓ (847 hands)
3-Bet: 8.2% ± 6.1   ⚠ (89 opportunities)
```

### 4.2 Show "Exploit This" Recommendations

For each exploitable tendency, show:
- **What they do wrong:** "Folds 68% to c-bets (GTO: 40%)"
- **How to exploit:** "C-bet 85% of range on flop, including all air"
- **Expected value:** "+3.2 BB/100 from exploiting this leak"

### 4.3 Add Stat Reliability Dashboard

Show users which stats they can trust:
```
✓ Reliable Stats (>500 samples):
  VPIP, PFR, WTSD, W$SD

⚠ Preliminary Stats (100-500 samples):
  3-Bet, Fold to 3-Bet, C-Bet Flop

✗ Insufficient Data (<100 samples):
  C-Bet Turn, C-Bet River, Check-Raise
```

---

## Implementation Priority

### Week 1-2: Foundation
- [ ] Implement Wilson score confidence intervals
- [ ] Add CI display to frontend stat cards
- [ ] Create calibrated GTO baselines file

### Week 3-4: Player Classification
- [ ] Fix overlapping player type logic
- [ ] Recalibrate Exploitability Index formula
- [ ] Add confidence-weighted calculations

### Week 5-6: GTO Improvements
- [ ] Add MDF calculator
- [ ] Expand postflop board coverage (5 → 20)
- [ ] Improve EV loss estimation

### Week 7-8: Cleanup
- [ ] Remove redundant composite metrics
- [ ] Add exploit recommendations to player profiles
- [ ] Create stat reliability dashboard

---

## Validation Plan

### 1. Confidence Interval Validation
- Compare with PokerTracker 4 and Hold'em Manager stats
- Verify CI width matches expected statistical properties

### 2. GTO Baseline Validation
- Cross-reference with GTOWizard published ranges
- Validate against Monker Solver solutions
- Check community consensus (2+2, RIO)

### 3. Player Classification Validation
- Test on known player pool (regs vs fish)
- Compare with PT4/HEM player type assignments
- Manual review of edge cases

### 4. Exploit Value Validation
- Backtest recommendations against actual results
- Compare EV estimates with solver calculations
- User feedback on recommendation quality

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Stats showing confidence level | 0% | 100% |
| GTO baselines with source | 0% | 100% |
| Player classification accuracy | ~60% | >85% |
| Postflop board coverage | 5 | 20+ |
| Composite metrics with validation | 0/12 | 5/5 |

---

## Files to Create/Modify

### New Files:
- `backend/services/confidence_calculator.py`
- `backend/config/gto_baselines.py`
- `backend/services/mdf_calculator.py`
- `backend/services/board_categorizer.py`

### Modified Files:
- `backend/services/stats_calculator.py`
- `backend/services/gto_service.py`
- `backend/services/opponent_analyzer.py`
- `backend/models/database_models.py`
- `frontend/src/components/StatCard.tsx`
- `frontend/src/pages/PlayerProfile.tsx`
- `frontend/src/pages/GTOAnalysis.tsx`
