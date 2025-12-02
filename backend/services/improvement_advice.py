"""
Improvement Advice Service

Provides tiered improvement advice for poker leaks:
- Tier 1: Quick Fix (2-3 specific hands to add/remove, simple heuristic)
- Tier 2: Detailed Explanation (range construction, hand categories, EV implications)
- Tier 3: Study Resources (AI-generated personalized recommendations)

Based on GTO theory and poker professor guidance.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class LeakCategory(Enum):
    """Categories of preflop leaks."""
    OPENING = "opening"
    DEFENSE = "defense"
    FACING_3BET = "facing_3bet"
    FACING_4BET = "facing_4bet"


class LeakDirection(Enum):
    """Direction of leak deviation from GTO."""
    TOO_LOOSE = "too_loose"      # Player does action too much
    TOO_TIGHT = "too_tight"      # Player does action too little


@dataclass
class HandCategory:
    """A category of hands to adjust."""
    name: str
    description: str
    hands: List[str]
    priority: int  # 1 = highest priority to add/remove


@dataclass
class QuickFix:
    """Tier 1: Quick fix advice."""
    heuristic: str
    hands_to_add: List[str]
    hands_to_remove: List[str]
    adjustment_pct: str  # e.g., "Open 5% wider"


@dataclass
class DetailedExplanation:
    """Tier 2: Detailed explanation."""
    principle: str
    hand_categories: List[HandCategory]
    ev_implication: str
    common_mistakes: List[str]
    position_specific_notes: Optional[str] = None


@dataclass
class StudyResource:
    """Tier 3: Study resources."""
    concepts_to_learn: List[str]
    solver_scenarios: List[str]
    practice_exercises: List[str]


@dataclass
class ImprovementAdvice:
    """Complete improvement advice for a leak."""
    leak_type: str
    leak_category: str
    position: str
    vs_position: Optional[str]
    player_value: float
    gto_value: float
    deviation: float
    quick_fix: QuickFix
    detailed: DetailedExplanation
    study: StudyResource
    caveats: List[str]
    sample_size_warning: Optional[str] = None


# =============================================================================
# STATIC ADVICE TEMPLATES
# =============================================================================

OPENING_ADVICE = {
    "too_tight": {
        "UTG": {
            "quick_fix": QuickFix(
                heuristic="Open ~16-18% from UTG. Add suited connectors and suited aces.",
                hands_to_add=["A2s", "A3s", "A4s", "A5s", "76s", "87s", "98s", "T9s", "KTs"],
                hands_to_remove=[],
                adjustment_pct="Open 3-5% wider"
            ),
            "detailed": DetailedExplanation(
                principle="UTG range needs suited connectors for board coverage. Without them, your range is face-up on low connected boards.",
                hand_categories=[
                    HandCategory("Suited Aces", "Blockers to AA/AK + wheel potential", ["A2s", "A3s", "A4s", "A5s"], 1),
                    HandCategory("Suited Connectors", "Equity realization + deception", ["76s", "87s", "98s", "T9s"], 2),
                    HandCategory("Suited Broadways", "Strong high card + flush potential", ["KTs", "QTs", "JTs"], 3),
                ],
                ev_implication="Missing these hands costs ~0.5-1 BB/100 in stolen blinds and postflop equity.",
                common_mistakes=[
                    "Folding all suited connectors from EP",
                    "Only opening premium pairs and AK/AQ",
                    "Not adjusting for table dynamics (tighter vs 3-bet happy table)"
                ],
                position_specific_notes="UTG is your tightest position, but GTO still opens ~16-18% of hands."
            ),
            "study": StudyResource(
                concepts_to_learn=["RFI (Raise First In) ranges", "Board coverage", "Range vs range equity"],
                solver_scenarios=["UTG open 2.5bb vs various 3-bet sizes", "UTG vs BB defense"],
                practice_exercises=["Memorize UTG opening range", "Practice identifying dominated vs playable hands"]
            ),
            "caveats": [
                "Tighten up vs aggressive 3-bettors behind you",
                "Widen slightly in passive games",
                "Consider stack depths - play tighter if short stacked"
            ]
        },
        "MP": {
            "quick_fix": QuickFix(
                heuristic="Open ~20-22% from MP. Add more suited connectors and offsuit broadways.",
                hands_to_add=["A2s", "A3s", "A4s", "A5s", "65s", "76s", "87s", "KJo", "QJo"],
                hands_to_remove=[],
                adjustment_pct="Open 4-6% wider"
            ),
            "detailed": DetailedExplanation(
                principle="MP has one less player behind than UTG, allowing a wider opening range. Suited connectors gain value with fewer players to act.",
                hand_categories=[
                    HandCategory("Suited Aces", "Block premiums + nuts potential", ["A2s", "A3s", "A4s", "A5s"], 1),
                    HandCategory("Suited Connectors", "Board coverage on low boards", ["65s", "76s", "87s", "98s"], 2),
                    HandCategory("Offsuit Broadways", "Strong high card equity", ["KJo", "QJo", "KTo"], 3),
                ],
                ev_implication="Under-opening from MP loses ~0.8 BB/100 in unclaimed pots.",
                common_mistakes=[
                    "Playing same range as UTG",
                    "Folding all suited one-gappers",
                    "Not value betting thin enough with marginal hands"
                ]
            ),
            "study": StudyResource(
                concepts_to_learn=["Position value", "Range widening by position"],
                solver_scenarios=["MP open vs CO/BTN 3-bet"],
                practice_exercises=["Compare UTG vs MP ranges", "Identify +EV opens"]
            ),
            "caveats": [
                "In 9-max games, MP plays more like UTG+1",
                "Adjust based on players yet to act"
            ]
        },
        "CO": {
            "quick_fix": QuickFix(
                heuristic="Open ~27-30% from CO. Add suited gappers and more offsuit hands.",
                hands_to_add=["A2s-A9s", "K9s", "Q9s", "J8s", "T8s", "97s", "86s", "75s", "KTo", "QTo", "JTo"],
                hands_to_remove=[],
                adjustment_pct="Open 5-8% wider"
            ),
            "detailed": DetailedExplanation(
                principle="CO is a stealing position. Only BTN and blinds remain, so you can profitably open much wider.",
                hand_categories=[
                    HandCategory("All Suited Aces", "Always open from CO", ["A2s", "A3s", "A4s", "A5s", "A6s", "A7s", "A8s", "A9s"], 1),
                    HandCategory("Suited Kings/Queens", "Strong stealing hands", ["K9s", "K8s", "Q9s", "Q8s"], 2),
                    HandCategory("Suited Connectors/Gappers", "Playability postflop", ["97s", "86s", "75s", "T8s", "J8s"], 3),
                    HandCategory("Offsuit Broadways", "High card strength", ["KTo", "QTo", "JTo", "K9o"], 4),
                ],
                ev_implication="CO under-opening is one of the biggest leaks - costs 1-2 BB/100 in lost stealing equity.",
                common_mistakes=[
                    "Playing CO like EP",
                    "Folding suited connectors",
                    "Not defending opens wide enough"
                ],
                position_specific_notes="CO should open nearly 3x as many hands as UTG."
            ),
            "study": StudyResource(
                concepts_to_learn=["Stealing equity", "Fold equity calculation", "BTN dynamics"],
                solver_scenarios=["CO open vs BTN 3-bet vs blind squeeze"],
                practice_exercises=["Practice CO steal situations", "Calculate fold equity needed"]
            ),
            "caveats": [
                "Tighten slightly with aggressive BTN behind",
                "Can open even wider vs tight blinds"
            ]
        },
        "BTN": {
            "quick_fix": QuickFix(
                heuristic="Open ~43-48% from BTN. This is your widest opening position.",
                hands_to_add=["Any suited hand", "K2o+", "Q5o+", "J7o+", "T7o+", "97o+", "87o", "76o"],
                hands_to_remove=[],
                adjustment_pct="Open 8-12% wider"
            ),
            "detailed": DetailedExplanation(
                principle="BTN has guaranteed position postflop. You can profitably open almost any hand with reasonable equity.",
                hand_categories=[
                    HandCategory("All Suited Hands", "Open any two suited cards", ["32s+"], 1),
                    HandCategory("Offsuit Kings", "High card + stealing value", ["K2o", "K3o", "K4o", "K5o+"], 2),
                    HandCategory("Offsuit Connectors", "Playability when called", ["76o", "87o", "98o", "T9o"], 3),
                    HandCategory("Marginal Offsuit", "Pure stealing hands", ["Q5o+", "J7o+", "T7o+"], 4),
                ],
                ev_implication="BTN under-opening is leaving significant money on the table - 2-3 BB/100 in unclaimed pots.",
                common_mistakes=[
                    "Treating BTN like a middle position",
                    "Folding suited hands",
                    "Not adjusting to blind tendencies"
                ],
                position_specific_notes="BTN should be your most profitable position by far."
            ),
            "study": StudyResource(
                concepts_to_learn=["Position value calculation", "Blind stealing theory", "Postflop position advantage"],
                solver_scenarios=["BTN vs BB heads-up", "BTN vs SB/BB multiway defense"],
                practice_exercises=["Play BTN-only sessions", "Track steal success rate"]
            ),
            "caveats": [
                "Against very aggressive blinds, tighten to ~35-40%",
                "Against passive blinds, can open 50%+"
            ]
        },
        "SB": {
            "quick_fix": QuickFix(
                heuristic="Open ~40-45% from SB vs BB only. Mix raises with some limps.",
                hands_to_add=["Suited hands 54s+", "Offsuit broadways", "All pocket pairs"],
                hands_to_remove=[],
                adjustment_pct="Open 6-10% wider"
            ),
            "detailed": DetailedExplanation(
                principle="SB vs BB is a unique heads-up battle. You have a wide range advantage but positional disadvantage.",
                hand_categories=[
                    HandCategory("Linear Value", "Strong hands to raise", ["22+", "A2s+", "K2s+", "Q4s+", "J6s+"], 1),
                    HandCategory("Limp Candidates", "Hands that play well multiway", ["54s", "65s", "small pairs"], 2),
                    HandCategory("Offsuit Broadways", "Raising for value", ["K9o+", "Q9o+", "J9o+", "T9o"], 3),
                ],
                ev_implication="SB is naturally -EV but under-opening makes it worse by ~1 BB/100.",
                common_mistakes=[
                    "Raising same range as BTN (too wide)",
                    "Never limping (missing +EV spots)",
                    "Over-folding to BB 3-bets"
                ],
                position_specific_notes="GTO includes some limping from SB - don't be afraid to implement it."
            ),
            "study": StudyResource(
                concepts_to_learn=["SB vs BB theory", "Limping ranges", "Mixed strategies"],
                solver_scenarios=["SB open vs BB 3-bet responses"],
                practice_exercises=["Practice SB vs BB battles"]
            ),
            "caveats": [
                "Against aggressive BB, tighten and size up",
                "Against passive BB, can open wider with smaller sizing"
            ]
        }
    },
    "too_loose": {
        "UTG": {
            "quick_fix": QuickFix(
                heuristic="Open only ~16-18% from UTG. Remove marginal hands that face too much 3-bet pressure.",
                hands_to_add=[],
                hands_to_remove=["KJo", "QJo", "JTo", "A9o", "A8o", "K9s", "Q9s", "98o", "87o"],
                adjustment_pct="Open 4-6% tighter"
            ),
            "detailed": DetailedExplanation(
                principle="UTG opens face 5 players behind. Marginal hands don't realize enough equity when 3-bet.",
                hand_categories=[
                    HandCategory("Dominated Offsuit", "Remove these first", ["KJo", "QJo", "JTo", "KTo"], 1),
                    HandCategory("Weak Aces", "Dominated too often", ["A9o", "A8o", "A7o"], 2),
                    HandCategory("Marginal Suited", "Only keep if table is passive", ["K9s", "Q9s", "J9s"], 3),
                ],
                ev_implication="Over-opening from UTG loses ~1-2 BB/100 from getting 3-bet and folding.",
                common_mistakes=[
                    "Opening any Ax offsuit",
                    "Opening KJo/QJo in EP",
                    "Not tightening vs aggressive tables"
                ],
                position_specific_notes="Your UTG range should be your tightest and strongest."
            ),
            "study": StudyResource(
                concepts_to_learn=["Dominated hands", "3-bet defense ranges"],
                solver_scenarios=["UTG open, face 3-bet, fold equity analysis"],
                practice_exercises=["Compare EVs of marginal opens"]
            ),
            "caveats": [
                "Can keep some hands vs passive tables",
                "Tighten more in tough games"
            ]
        },
        "BTN": {
            "quick_fix": QuickFix(
                heuristic="Open ~43-48% from BTN, not 55%+. Even BTN has limits.",
                hands_to_add=[],
                hands_to_remove=["72o", "83o", "93o", "T2o", "J2o", "Q2o-Q4o", "K2o", "52o", "62o"],
                adjustment_pct="Open 5-8% tighter"
            ),
            "detailed": DetailedExplanation(
                principle="While BTN is wide, hands with zero playability are still -EV opens even with position.",
                hand_categories=[
                    HandCategory("Unplayable Offsuit", "Zero equity realization", ["72o", "83o", "93o", "T2o-T4o"], 1),
                    HandCategory("Weak Queens/Kings", "Dominated by BB defense", ["Q2o", "Q3o", "K2o"], 2),
                ],
                ev_implication="Opening trash loses the open sizing when called + postflop mistakes.",
                common_mistakes=[
                    "Opening any two cards",
                    "Not folding worst hands",
                    "Ignoring blind player types"
                ]
            ),
            "study": StudyResource(
                concepts_to_learn=["Equity realization", "Playability concepts"],
                solver_scenarios=["BTN open worst hands vs BB defend"],
                practice_exercises=["Find the cutoff for +EV BTN opens"]
            ),
            "caveats": [
                "Against very weak blinds, can be wider",
                "Against strong blinds, tighten more"
            ]
        }
    }
}

DEFENSE_ADVICE = {
    "too_tight": {  # Over-folding in blinds
        "BB": {
            "quick_fix": QuickFix(
                heuristic="Defend ~45-55% of hands vs BTN open (varies by sizing). You're getting great pot odds.",
                hands_to_add=["Any suited hand", "K2o+", "Q6o+", "J7o+", "T7o+", "97o+", "87o", "76o"],
                hands_to_remove=[],
                adjustment_pct="Defend 10-15% wider"
            ),
            "detailed": DetailedExplanation(
                principle="BB gets the best pot odds in poker. With 1bb invested vs a 2.5bb open, you only need ~28% equity to call.",
                hand_categories=[
                    HandCategory("All Suited Hands", "Must defend - equity + playability", ["32s+", "42s+", "52s+"], 1),
                    HandCategory("Offsuit Kings", "High card + pot odds", ["K2o+", "K3o+"], 2),
                    HandCategory("Offsuit Connectors", "Playability + implied odds", ["76o", "87o", "98o"], 3),
                    HandCategory("3-Bet Candidates", "Mix of value + bluffs", ["A5s", "A4s", "K5s", "76s"], 4),
                ],
                ev_implication="Over-folding BB vs BTN costs 2-4 BB/100 - one of the biggest leaks possible.",
                common_mistakes=[
                    "Folding suited hands",
                    "Folding to small raise sizes",
                    "Not 3-betting enough as defense"
                ],
                position_specific_notes="BB defense is the #1 spot where tight players lose money."
            ),
            "study": StudyResource(
                concepts_to_learn=["Pot odds", "MDF (Minimum Defense Frequency)", "3-bet/call/fold ratios"],
                solver_scenarios=["BB vs BTN 2.5bb open", "BB vs CO 2.5bb open"],
                practice_exercises=["Calculate pot odds for calls", "Practice 3-bet ranges"]
            ),
            "caveats": [
                "Tighten vs larger open sizes (3bb+)",
                "Tighten vs EP opens",
                "Consider rake in smaller pots"
            ]
        },
        "SB": {
            "quick_fix": QuickFix(
                heuristic="Defend ~30-35% vs BTN, but mostly by 3-betting (not calling). SB has worst position postflop.",
                hands_to_add=["A5s", "A4s", "A3s", "A2s", "K5s", "76s", "65s", "54s"],
                hands_to_remove=[],
                adjustment_pct="3-bet 5-8% more"
            ),
            "detailed": DetailedExplanation(
                principle="SB should rarely flat call - you'll be OOP postflop with BB still to act. 3-bet or fold is usually correct.",
                hand_categories=[
                    HandCategory("Value 3-Bets", "Strong hands to 3-bet for value", ["TT+", "AQs+", "AK"], 1),
                    HandCategory("Bluff 3-Bets", "Suited aces with blockers", ["A5s", "A4s", "A3s", "A2s"], 2),
                    HandCategory("Semi-Bluff 3-Bets", "Suited connectors", ["76s", "65s", "87s", "98s"], 3),
                ],
                ev_implication="SB over-folding or over-calling (instead of 3-betting) costs ~1-2 BB/100.",
                common_mistakes=[
                    "Calling too much from SB (should mostly 3-bet or fold)",
                    "Not 3-betting suited connectors",
                    "Folding A5s/A4s"
                ],
                position_specific_notes="SB should 3-bet about 10-14% vs late position opens."
            ),
            "study": StudyResource(
                concepts_to_learn=["SB 3-bet strategy", "Polarized vs linear ranges", "Squeeze play"],
                solver_scenarios=["SB vs BTN open", "SB squeeze vs open + call"],
                practice_exercises=["Practice SB 3-bet ranges"]
            ),
            "caveats": [
                "Can call more vs very tight openers",
                "Adjust squeeze frequency based on caller tendencies"
            ]
        }
    },
    "too_loose": {  # Over-defending/over-calling
        "BB": {
            "quick_fix": QuickFix(
                heuristic="Don't defend trash offsuit hands even with pot odds. Some hands have zero playability.",
                hands_to_add=[],
                hands_to_remove=["72o", "83o", "84o", "93o", "94o", "T2o", "T3o", "J2o", "J3o", "Q2o"],
                adjustment_pct="Fold 8-12% more"
            ),
            "detailed": DetailedExplanation(
                principle="While pot odds favor wide defense, hands with zero playability still lose money due to postflop mistakes.",
                hand_categories=[
                    HandCategory("Unplayable Trash", "Always fold", ["72o", "83o", "84o", "93o", "94o"], 1),
                    HandCategory("Dominated Hands", "Fold vs tight opens", ["T2o", "T3o", "J2o", "J3o", "Q2o"], 2),
                ],
                ev_implication="Defending trash creates postflop mistakes that outweigh pot odds benefit.",
                common_mistakes=[
                    "Defending any two cards with pot odds",
                    "Not adjusting to raiser position",
                    "Calling without plan for postflop"
                ]
            ),
            "study": StudyResource(
                concepts_to_learn=["Equity realization", "Postflop playability"],
                solver_scenarios=["BB defense with marginal hands"],
                practice_exercises=["Identify hands with good vs poor playability"]
            ),
            "caveats": [
                "Can defend wider vs very small opens",
                "Tighten significantly vs EP opens"
            ]
        }
    }
}

FACING_3BET_ADVICE = {
    "too_tight": {  # Over-folding to 3-bets
        "default": {
            "quick_fix": QuickFix(
                heuristic="Defend ~40-50% of your opening range vs 3-bets. You're folding too much.",
                hands_to_add=["AJo", "KQo", "KQs", "QJs", "JTs", "TT", "99", "A5s", "A4s"],
                hands_to_remove=[],
                adjustment_pct="Continue 8-12% more"
            ),
            "detailed": DetailedExplanation(
                principle="If you fold too much to 3-bets, opponents can profitably 3-bet you with any two cards. You must defend enough to make their bluffs unprofitable.",
                hand_categories=[
                    HandCategory("Must-Defend Value", "Never fold these to a single 3-bet", ["QQ+", "AKs", "AKo"], 1),
                    HandCategory("Standard Continues", "Call or 4-bet", ["JJ", "TT", "AQs", "AQo", "KQs"], 2),
                    HandCategory("Calling Range", "Suited hands that play well", ["AJs", "KQs", "QJs", "JTs", "T9s", "99", "88"], 3),
                    HandCategory("4-Bet Bluffs", "Blockers with fold equity", ["A5s", "A4s", "A3s", "K5s"], 4),
                ],
                ev_implication="Over-folding to 3-bets costs 2-3 BB/100 - opponents exploit you relentlessly.",
                common_mistakes=[
                    "Folding AQo/KQs to 3-bets",
                    "Folding TT/99 to all 3-bets",
                    "Never 4-bet bluffing",
                    "Treating all 3-bets the same regardless of position"
                ],
                position_specific_notes="Defend wider when you opened from late position (wider range = more defense)."
            ),
            "study": StudyResource(
                concepts_to_learn=["MDF (Minimum Defense Frequency)", "4-bet range construction", "Blocker theory"],
                solver_scenarios=["BTN open, face BB 3-bet", "CO open, face BTN 3-bet"],
                practice_exercises=["Calculate MDF for your open sizing", "Build 4-bet bluff ranges"]
            ),
            "caveats": [
                "Tighten vs tight 3-bettors (value-heavy)",
                "Widen vs aggressive 3-bettors (bluff-heavy)",
                "Stack depth matters: tighter <50bb, wider >150bb"
            ]
        }
    },
    "too_loose": {  # Under-folding to 3-bets (calling too much)
        "default": {
            "quick_fix": QuickFix(
                heuristic="Don't call 3-bets with dominated hands. Either 4-bet or fold marginal holdings.",
                hands_to_add=[],
                hands_to_remove=["KJo", "QJo", "JTo", "A9o", "A8o", "KTo", "QTo"],
                adjustment_pct="Fold 8-12% more of marginal hands"
            ),
            "detailed": DetailedExplanation(
                principle="Calling 3-bets with dominated hands creates difficult postflop situations. These hands don't realize enough equity OOP.",
                hand_categories=[
                    HandCategory("Dominated Offsuit", "Fold or 4-bet, never call", ["KJo", "QJo", "JTo", "KTo"], 1),
                    HandCategory("Weak Aces", "Usually fold vs 3-bet", ["A9o", "A8o", "A7o"], 2),
                    HandCategory("Convert to Bluffs", "4-bet sometimes, fold sometimes", ["A5s", "A4s"], 3),
                ],
                ev_implication="Calling with dominated hands bleeds money postflop.",
                common_mistakes=[
                    "Calling with any Ax offsuit",
                    "Calling KJo/QJo vs tight 3-bettors",
                    "Not 4-bet bluffing with better hands (A5s)"
                ]
            ),
            "study": StudyResource(
                concepts_to_learn=["Dominated hand theory", "4-bet bluff selection"],
                solver_scenarios=["What to do with KJo vs 3-bet"],
                practice_exercises=["Identify dominated hands in 3-bet pots"]
            ),
            "caveats": [
                "Can call wider IP vs smaller 3-bets",
                "Adjust based on 3-bettor's range"
            ]
        }
    }
}


def get_improvement_advice(
    leak_category: str,
    leak_direction: str,
    position: str,
    vs_position: Optional[str],
    player_value: float,
    gto_value: float,
    sample_size: int
) -> ImprovementAdvice:
    """
    Get static improvement advice for a leak.

    Args:
        leak_category: opening, defense, facing_3bet, facing_4bet
        leak_direction: too_loose or too_tight
        position: Player position (UTG, MP, CO, BTN, SB, BB)
        vs_position: Opponent position (for defense/facing scenarios)
        player_value: Player's frequency for this action
        gto_value: GTO frequency for this action
        sample_size: Number of hands in sample

    Returns:
        ImprovementAdvice object with all tiers
    """
    deviation = player_value - gto_value

    # Select the right advice template
    advice_map = {
        "opening": OPENING_ADVICE,
        "defense": DEFENSE_ADVICE,
        "facing_3bet": FACING_3BET_ADVICE,
    }

    category_advice = advice_map.get(leak_category, {})
    direction_advice = category_advice.get(leak_direction, {})

    # Get position-specific or default advice
    position_advice = direction_advice.get(position, direction_advice.get("default", {}))

    if not position_advice:
        # Fallback to generic advice
        return _get_generic_advice(leak_category, leak_direction, position, vs_position,
                                   player_value, gto_value, deviation, sample_size)

    # Build the advice object
    quick_fix = position_advice.get("quick_fix", QuickFix("Adjust frequency closer to GTO", [], [], ""))
    detailed = position_advice.get("detailed", DetailedExplanation("", [], "", []))
    study = position_advice.get("study", StudyResource([], [], []))
    caveats = position_advice.get("caveats", [])

    # Add sample size warning if needed
    sample_warning = None
    if sample_size < 100:
        sample_warning = f"Low confidence ({sample_size} hands). Need 100+ hands for reliable data."
    elif sample_size < 300:
        sample_warning = f"Moderate confidence ({sample_size} hands). Patterns may be variance."

    return ImprovementAdvice(
        leak_type=f"{leak_direction}_{leak_category}",
        leak_category=leak_category,
        position=position,
        vs_position=vs_position,
        player_value=player_value,
        gto_value=gto_value,
        deviation=deviation,
        quick_fix=quick_fix,
        detailed=detailed,
        study=study,
        caveats=caveats,
        sample_size_warning=sample_warning
    )


def _get_generic_advice(
    leak_category: str,
    leak_direction: str,
    position: str,
    vs_position: Optional[str],
    player_value: float,
    gto_value: float,
    deviation: float,
    sample_size: int
) -> ImprovementAdvice:
    """Generate generic advice when no specific template exists."""

    if leak_direction == "too_tight":
        quick_fix = QuickFix(
            heuristic=f"Increase your {leak_category} frequency by ~{abs(deviation):.0f}%",
            hands_to_add=["Suited connectors", "Suited aces", "Broadways"],
            hands_to_remove=[],
            adjustment_pct=f"Add ~{abs(deviation):.0f}% more hands"
        )
        detailed = DetailedExplanation(
            principle="You're playing too tight in this spot. GTO plays wider to remain unexploitable.",
            hand_categories=[
                HandCategory("Add First", "Strongest hands you're folding", ["Suited broadways", "Medium pairs"], 1),
                HandCategory("Add Second", "Playable suited hands", ["Suited connectors", "Suited aces"], 2),
            ],
            ev_implication=f"Playing {abs(deviation):.0f}% tighter than GTO costs significant EV in unclaimed pots.",
            common_mistakes=["Playing too few hands", "Being too risk-averse", "Not adjusting to opponent tendencies"]
        )
    else:
        quick_fix = QuickFix(
            heuristic=f"Decrease your {leak_category} frequency by ~{abs(deviation):.0f}%",
            hands_to_add=[],
            hands_to_remove=["Marginal offsuit hands", "Dominated hands"],
            adjustment_pct=f"Remove ~{abs(deviation):.0f}% of marginal hands"
        )
        detailed = DetailedExplanation(
            principle="You're playing too loose in this spot. GTO plays tighter to avoid dominated situations.",
            hand_categories=[
                HandCategory("Remove First", "Weakest hands you're playing", ["Trash offsuit", "Weak aces"], 1),
                HandCategory("Remove Second", "Dominated hands", ["KJo/QJo type hands", "Weak kings"], 2),
            ],
            ev_implication=f"Playing {abs(deviation):.0f}% looser than GTO creates postflop difficulties.",
            common_mistakes=["Playing too many hands", "Not respecting position", "Ignoring opponent ranges"]
        )

    study = StudyResource(
        concepts_to_learn=[f"{leak_category.replace('_', ' ').title()} theory", "Range construction", "GTO frequencies"],
        solver_scenarios=[f"Run {position} {leak_category} simulations"],
        practice_exercises=["Review your hand histories for this spot"]
    )

    sample_warning = None
    if sample_size < 100:
        sample_warning = f"Low confidence ({sample_size} hands). Need 100+ hands."

    return ImprovementAdvice(
        leak_type=f"{leak_direction}_{leak_category}",
        leak_category=leak_category,
        position=position,
        vs_position=vs_position,
        player_value=player_value,
        gto_value=gto_value,
        deviation=deviation,
        quick_fix=quick_fix,
        detailed=detailed,
        study=study,
        caveats=["Adjust based on opponent tendencies", "Consider stack depths"],
        sample_size_warning=sample_warning
    )


def advice_to_dict(advice: ImprovementAdvice) -> Dict[str, Any]:
    """Convert ImprovementAdvice to dictionary for JSON serialization."""
    return {
        "leak_type": advice.leak_type,
        "leak_category": advice.leak_category,
        "position": advice.position,
        "vs_position": advice.vs_position,
        "player_value": advice.player_value,
        "gto_value": advice.gto_value,
        "deviation": advice.deviation,
        "sample_size_warning": advice.sample_size_warning,
        "tier1_quick_fix": {
            "heuristic": advice.quick_fix.heuristic,
            "hands_to_add": advice.quick_fix.hands_to_add,
            "hands_to_remove": advice.quick_fix.hands_to_remove,
            "adjustment": advice.quick_fix.adjustment_pct
        },
        "tier2_detailed": {
            "principle": advice.detailed.principle,
            "hand_categories": [
                {
                    "name": cat.name,
                    "description": cat.description,
                    "hands": cat.hands,
                    "priority": cat.priority
                }
                for cat in advice.detailed.hand_categories
            ],
            "ev_implication": advice.detailed.ev_implication,
            "common_mistakes": advice.detailed.common_mistakes,
            "position_notes": advice.detailed.position_specific_notes
        },
        "tier3_study": {
            "concepts": advice.study.concepts_to_learn,
            "solver_scenarios": advice.study.solver_scenarios,
            "exercises": advice.study.practice_exercises
        },
        "caveats": advice.caveats
    }
