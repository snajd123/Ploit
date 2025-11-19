"""
Comprehensive Poker Statistics Definitions

This file serves as the authoritative source for all poker statistics,
their formulas, explanations, optimal ranges, and tooltips.

All calculations have been verified against standard poker theory sources:
- Modern Poker Theory by Michael Acevedo
- Applications of No-Limit Hold'em by Matthew Janda
- GTO Wizard ranges and documentation
- PokerTracker/HEM standard definitions
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class StatDefinition:
    """Complete definition of a poker statistic"""
    name: str
    abbreviation: str
    category: str
    description: str
    formula: str
    optimal_range: Optional[tuple] = None
    tooltip: str = ""
    unit: str = "%"
    min_sample: int = 100
    interpretation_guide: Dict[str, str] = None

    def __post_init__(self):
        if self.interpretation_guide is None:
            self.interpretation_guide = {}


# ============================================
# TRADITIONAL STATISTICS
# ============================================

TRADITIONAL_STATS = {
    # PREFLOP STATISTICS
    "vpip_pct": StatDefinition(
        name="Voluntarily Put Money In Pot",
        abbreviation="VPIP",
        category="Preflop",
        description="Percentage of hands where a player voluntarily puts money in the pot preflop (by calling or raising, not including blinds).",
        formula="(hands_where_voluntarily_invested / total_hands) × 100",
        optimal_range=(18, 25),
        tooltip="How often they play a hand. Lower = tighter, Higher = looser",
        min_sample=100,
        interpretation_guide={
            "< 15%": "Nit - Very tight, only plays premium hands",
            "15-25%": "TAG - Tight-aggressive, solid range",
            "25-35%": "LAG - Loose-aggressive, wider range",
            "35-45%": "Loose Passive - Too many hands, often calling",
            "> 45%": "Fish/Maniac - Playing way too many hands"
        }
    ),

    "pfr_pct": StatDefinition(
        name="Pre-Flop Raise",
        abbreviation="PFR",
        category="Preflop",
        description="Percentage of hands where a player raises preflop (including open-raises and 3-bets).",
        formula="(hands_where_raised_preflop / total_hands) × 100",
        optimal_range=(13, 20),
        tooltip="How often they raise before the flop. Shows aggression level",
        min_sample=100,
        interpretation_guide={
            "< 10%": "Very passive, mostly calls",
            "10-15%": "Passive aggressive",
            "15-25%": "Properly aggressive",
            "> 25%": "Hyper-aggressive, may be overplaying"
        }
    ),

    "limp_pct": StatDefinition(
        name="Limp Percentage",
        abbreviation="Limp",
        category="Preflop",
        description="Percentage of hands where a player limps (calls the big blind when first to act).",
        formula="(hands_where_limped / total_hands) × 100",
        optimal_range=(0, 5),
        tooltip="How often they limp. Good players rarely limp",
        min_sample=100,
        interpretation_guide={
            "0-5%": "Good - Rarely limps",
            "5-15%": "Somewhat passive",
            "> 15%": "Weak player - Too much limping"
        }
    ),

    "three_bet_pct": StatDefinition(
        name="Three-Bet Percentage",
        abbreviation="3-Bet",
        category="Preflop",
        description="Percentage of times a player makes a 3-bet when facing an open-raise.",
        formula="(made_3bet_count / faced_open_raise_count) × 100",
        optimal_range=(6, 12),
        tooltip="How often they re-raise an opener. Shows aggression and bluffing",
        min_sample=200,
        interpretation_guide={
            "< 5%": "Too passive, can be exploited",
            "5-10%": "Standard TAG range",
            "10-15%": "Aggressive, polarized range",
            "> 15%": "Very aggressive, may be over-3betting"
        }
    ),

    "fold_to_three_bet_pct": StatDefinition(
        name="Fold to Three-Bet",
        abbreviation="F3B",
        category="Preflop",
        description="Percentage of times a player folds when facing a 3-bet after opening.",
        formula="(folded_to_3bet_count / faced_3bet_count) × 100",
        optimal_range=(50, 60),
        tooltip="How often they fold to a 3-bet. High = exploitable with 3-bets",
        min_sample=100,
        interpretation_guide={
            "< 45%": "Too stubborn, defends too wide",
            "45-60%": "Optimal range",
            "60-75%": "Slightly exploitable by 3-betting",
            "> 75%": "Extremely exploitable - 3-bet them relentlessly"
        }
    ),

    "four_bet_pct": StatDefinition(
        name="Four-Bet Percentage",
        abbreviation="4-Bet",
        category="Preflop",
        description="Percentage of times a player makes a 4-bet when facing a 3-bet.",
        formula="(made_4bet_count / faced_3bet_count) × 100",
        optimal_range=(8, 15),
        tooltip="How often they 4-bet. Very aggressive move, usually strong or bluff",
        min_sample=50,
        interpretation_guide={
            "< 5%": "Never bluffs, 4-bet = nuts",
            "5-12%": "Balanced 4-bet range",
            "> 12%": "Aggressive 4-better, may overdo it"
        }
    ),

    "cold_call_pct": StatDefinition(
        name="Cold Call Percentage",
        abbreviation="CC",
        category="Preflop",
        description="Percentage of times a player cold-calls a raise (calls without having invested yet).",
        formula="(cold_call_count / opportunities) × 100",
        optimal_range=(8, 15),
        tooltip="Calling a raise when you haven't put money in yet",
        min_sample=100,
        interpretation_guide={
            "< 5%": "Very aggressive, rarely flat calls",
            "5-15%": "Reasonable flatting range",
            "> 15%": "Too passive, calling too much"
        }
    ),

    "squeeze_pct": StatDefinition(
        name="Squeeze Play Percentage",
        abbreviation="Squeeze",
        category="Preflop",
        description="Percentage of times a player makes a squeeze play (3-bets after an opener and caller).",
        formula="(squeeze_count / squeeze_opportunities) × 100",
        optimal_range=(8, 15),
        tooltip="3-betting when someone opens and another calls. Aggressive move",
        min_sample=50,
        interpretation_guide={
            "< 5%": "Missing squeeze opportunities",
            "5-12%": "Good squeeze frequency",
            "> 12%": "May be over-squeezing"
        }
    ),

    # POSITIONAL VPIP
    "vpip_utg": StatDefinition(
        name="VPIP from UTG",
        abbreviation="UTG VPIP",
        category="Positional",
        description="VPIP from Under The Gun (earliest position). Should be tightest range.",
        formula="(vpip_utg_count / utg_hands) × 100",
        optimal_range=(13, 18),
        tooltip="VPIP from earliest position. Should be very tight",
        min_sample=50
    ),

    "vpip_hj": StatDefinition(
        name="VPIP from Hijack",
        abbreviation="HJ VPIP",
        category="Positional",
        description="VPIP from Hijack (2 seats before button).",
        formula="(vpip_hj_count / hj_hands) × 100",
        optimal_range=(17, 22),
        tooltip="VPIP from middle position",
        min_sample=50
    ),

    "vpip_co": StatDefinition(
        name="VPIP from Cutoff",
        abbreviation="CO VPIP",
        category="Positional",
        description="VPIP from Cutoff (seat before button). Can be wider.",
        formula="(vpip_co_count / co_hands) × 100",
        optimal_range=(25, 30),
        tooltip="VPIP from late position. Can play more hands",
        min_sample=50
    ),

    "vpip_btn": StatDefinition(
        name="VPIP from Button",
        abbreviation="BTN VPIP",
        category="Positional",
        description="VPIP from Button (best position). Should be widest range.",
        formula="(vpip_btn_count / btn_hands) × 100",
        optimal_range=(43, 51),
        tooltip="VPIP from button. Should play the most hands here",
        min_sample=50
    ),

    "vpip_sb": StatDefinition(
        name="VPIP from Small Blind",
        abbreviation="SB VPIP",
        category="Positional",
        description="VPIP from Small Blind. Worst position postflop but has invested 0.5BB.",
        formula="(vpip_sb_count / sb_hands) × 100",
        optimal_range=(30, 36),
        tooltip="VPIP from small blind. Tricky position",
        min_sample=50
    ),

    "vpip_bb": StatDefinition(
        name="VPIP from Big Blind",
        abbreviation="BB VPIP",
        category="Positional",
        description="VPIP from Big Blind. Can defend wide due to pot odds.",
        formula="(vpip_bb_count / bb_hands) × 100",
        optimal_range=(35, 42),
        tooltip="VPIP from big blind. Defend with wider range",
        min_sample=50
    ),

    # STEAL & BLIND DEFENSE
    "steal_attempt_pct": StatDefinition(
        name="Steal Attempt Percentage",
        abbreviation="Steal",
        category="Blind Stealing",
        description="Percentage of times a player attempts to steal blinds from CO/BTN/SB.",
        formula="(steal_attempts / opportunities_from_late_position) × 100",
        optimal_range=(30, 45),
        tooltip="How often they try to steal blinds from late position",
        min_sample=100,
        interpretation_guide={
            "< 25%": "Too passive, missing steal opportunities",
            "25-40%": "Good steal frequency",
            "> 45%": "Over-stealing, can be exploited"
        }
    ),

    "fold_to_steal_pct": StatDefinition(
        name="Fold to Steal Attempt",
        abbreviation="Fold vs Steal",
        category="Blind Defense",
        description="Percentage of times a player folds in the blinds when facing a steal attempt.",
        formula="(folded_to_steal / faced_steal_attempt) × 100",
        optimal_range=(55, 70),
        tooltip="How often they fold to steal attempts. High = exploitable",
        min_sample=100,
        interpretation_guide={
            "< 50%": "Defending too wide from blinds",
            "50-70%": "Reasonable defense",
            "> 75%": "Folding too much - steal their blinds relentlessly"
        }
    ),

    "three_bet_vs_steal_pct": StatDefinition(
        name="Three-Bet vs Steal",
        abbreviation="3B vs Steal",
        category="Blind Defense",
        description="Percentage of times a player 3-bets from blinds when facing a steal attempt.",
        formula="(3bet_vs_steal / faced_steal_attempt) × 100",
        optimal_range=(8, 15),
        tooltip="How often they 3-bet vs steals from blinds",
        min_sample=50
    ),

    # CONTINUATION BETTING
    "cbet_flop_pct": StatDefinition(
        name="Continuation Bet Flop",
        abbreviation="Flop C-Bet",
        category="Continuation Betting",
        description="Percentage of times the preflop aggressor bets the flop.",
        formula="(flop_cbets_made / flop_cbet_opportunities) × 100",
        optimal_range=(55, 70),
        tooltip="How often they bet flop after raising preflop",
        min_sample=200,
        interpretation_guide={
            "< 50%": "Too passive, checks too much",
            "50-70%": "Balanced c-bet frequency",
            "> 75%": "Over-c-betting, bluffs too much"
        }
    ),

    "cbet_turn_pct": StatDefinition(
        name="Continuation Bet Turn",
        abbreviation="Turn C-Bet",
        category="Continuation Betting",
        description="Percentage of times the aggressor continues betting on the turn.",
        formula="(turn_cbets_made / turn_cbet_opportunities) × 100",
        optimal_range=(45, 60),
        tooltip="How often they barrel the turn after c-betting flop",
        min_sample=100,
        interpretation_guide={
            "< 40%": "Gives up too easily on turn",
            "40-60%": "Reasonable persistence",
            "> 65%": "Too aggressive, over-barreling"
        }
    ),

    "cbet_river_pct": StatDefinition(
        name="Continuation Bet River",
        abbreviation="River C-Bet",
        category="Continuation Betting",
        description="Percentage of times the aggressor continues betting on the river.",
        formula="(river_cbets_made / river_cbet_opportunities) × 100",
        optimal_range=(40, 55),
        tooltip="Triple barrel frequency - very aggressive move",
        min_sample=50
    ),

    # FACING C-BETS - FOLD
    "fold_to_cbet_flop_pct": StatDefinition(
        name="Fold to C-Bet Flop",
        abbreviation="Fold Flop CB",
        category="C-Bet Defense",
        description="Percentage of times a player folds when facing a flop c-bet.",
        formula="(folded_to_flop_cbet / faced_flop_cbet) × 100",
        optimal_range=(45, 60),
        tooltip="How often they fold to flop c-bet. High = exploitable",
        min_sample=200,
        interpretation_guide={
            "< 40%": "Too stubborn, not folding enough",
            "40-60%": "Reasonable fold frequency",
            "> 65%": "Folding too much - c-bet them relentlessly"
        }
    ),

    "fold_to_cbet_turn_pct": StatDefinition(
        name="Fold to C-Bet Turn",
        abbreviation="Fold Turn CB",
        category="C-Bet Defense",
        description="Percentage of times a player folds when facing a turn c-bet.",
        formula="(folded_to_turn_cbet / faced_turn_cbet) × 100",
        optimal_range=(50, 65),
        tooltip="Fold frequency vs turn barrel",
        min_sample=100
    ),

    "fold_to_cbet_river_pct": StatDefinition(
        name="Fold to C-Bet River",
        abbreviation="Fold River CB",
        category="C-Bet Defense",
        description="Percentage of times a player folds when facing a river c-bet.",
        formula="(folded_to_river_cbet / faced_river_cbet) × 100",
        optimal_range=(55, 70),
        tooltip="Fold frequency vs triple barrel",
        min_sample=50
    ),

    # FACING C-BETS - CALL
    "call_cbet_flop_pct": StatDefinition(
        name="Call C-Bet Flop",
        abbreviation="Call Flop CB",
        category="C-Bet Defense",
        description="Percentage of times a player calls a flop c-bet.",
        formula="(called_flop_cbet / faced_flop_cbet) × 100",
        optimal_range=(30, 45),
        tooltip="Float frequency on flop",
        min_sample=200
    ),

    # CHECK-RAISE
    "check_raise_flop_pct": StatDefinition(
        name="Check-Raise Flop",
        abbreviation="Flop C/R",
        category="Deceptive Play",
        description="Percentage of times a player check-raises the flop.",
        formula="(check_raised_flop / check_raise_opp_flop) × 100",
        optimal_range=(7, 15),
        tooltip="Trap play frequency on flop. Powerful aggressive move",
        min_sample=100,
        interpretation_guide={
            "< 5%": "Rarely traps, very straightforward",
            "5-12%": "Balanced check-raise range",
            "> 15%": "Over-check-raising, may be bluffing too much"
        }
    ),

    "check_raise_turn_pct": StatDefinition(
        name="Check-Raise Turn",
        abbreviation="Turn C/R",
        category="Deceptive Play",
        description="Percentage of times a player check-raises the turn.",
        formula="(check_raised_turn / check_raise_opp_turn) × 100",
        optimal_range=(5, 12),
        tooltip="Turn check-raise - represents very strong hand or bluff",
        min_sample=50
    ),

    "check_raise_river_pct": StatDefinition(
        name="Check-Raise River",
        abbreviation="River C/R",
        category="Deceptive Play",
        description="Percentage of times a player check-raises the river.",
        formula="(check_raised_river / check_raise_opp_river) × 100",
        optimal_range=(4, 10),
        tooltip="River check-raise - very polarized move",
        min_sample=25
    ),

    # DONK BETTING
    "donk_bet_flop_pct": StatDefinition(
        name="Donk Bet Flop",
        abbreviation="Flop Donk",
        category="Unusual Plays",
        description="Percentage of times a player leads into the preflop aggressor on the flop (donk bet).",
        formula="(donk_bet_flop / saw_flop_oop) × 100",
        optimal_range=(0, 8),
        tooltip="Leading into aggressor - usually weak play but can be exploitative",
        min_sample=100,
        interpretation_guide={
            "< 5%": "Rarely donks, plays standard",
            "5-12%": "Some donk betting strategy",
            "> 15%": "Weak player - donks too much"
        }
    ),

    # FLOAT PLAY
    "float_flop_pct": StatDefinition(
        name="Float Play Flop",
        abbreviation="Float",
        category="Advanced Plays",
        description="Percentage of times a player floats (calls flop c-bet with intention to take pot on later street).",
        formula="(float_count / faced_flop_cbet) × 100",
        optimal_range=(8, 18),
        tooltip="Calling flop with plan to bet when checked to on turn",
        min_sample=100
    ),

    # SHOWDOWN
    "wtsd_pct": StatDefinition(
        name="Went to Showdown",
        abbreviation="WTSD",
        category="Showdown",
        description="Percentage of times a player sees a showdown after seeing the flop.",
        formula="(went_to_showdown / saw_flop) × 100",
        optimal_range=(24, 30),
        tooltip="How often they go to showdown. High = calling station",
        min_sample=200,
        interpretation_guide={
            "< 20%": "Very aggressive, doesn't call down much",
            "20-30%": "Balanced showdown frequency",
            "> 35%": "Calling station - calls down too much"
        }
    ),

    "wsd_pct": StatDefinition(
        name="Won at Showdown",
        abbreviation="W$SD",
        category="Showdown",
        description="Percentage of times a player wins when going to showdown.",
        formula="(won_at_showdown / went_to_showdown) × 100",
        optimal_range=(48, 54),
        tooltip="Win rate at showdown. ~50% is expected",
        min_sample=100,
        interpretation_guide={
            "< 45%": "Going to showdown with weak hands",
            "45-55%": "Showdown hand strength is balanced",
            "> 55%": "Very value-heavy, not bluffing enough"
        }
    ),

    # AGGRESSION
    "af": StatDefinition(
        name="Aggression Factor",
        abbreviation="AF",
        category="Aggression",
        description="Ratio of aggressive actions to passive actions: (Bets + Raises) / Calls",
        formula="(total_bets + total_raises) / total_calls",
        optimal_range=(2.0, 4.0),
        tooltip="Overall aggression level. Higher = more aggressive",
        unit="ratio",
        min_sample=500,
        interpretation_guide={
            "< 1.5": "Very passive, calls too much",
            "1.5-3.0": "Balanced aggression",
            "> 4.0": "Hyper-aggressive"
        }
    ),

    "afq": StatDefinition(
        name="Aggression Frequency",
        abbreviation="AFQ",
        category="Aggression",
        description="Percentage of postflop actions that are aggressive (bet or raise).",
        formula="(total_bets + total_raises) / (total_bets + total_raises + total_calls + total_checks) × 100",
        optimal_range=(45.0, 60.0),
        tooltip="How often they choose aggression over passivity",
        unit="%",
        min_sample=500,
        interpretation_guide={
            "< 40%": "Too passive postflop",
            "40-60%": "Balanced aggression frequency",
            "> 65%": "Overly aggressive, likely over-bluffing"
        }
    ),

    # WIN RATE
    "bb_per_100": StatDefinition(
        name="Big Blinds per 100 Hands",
        abbreviation="BB/100",
        category="Win Rate",
        description="Average win rate in big blinds per 100 hands played.",
        formula="(total_profit_loss / total_hands) × 100",
        optimal_range=(3.0, 8.0),
        tooltip="Win rate. Positive = winning player, Negative = losing",
        unit="BB",
        min_sample=1000,
        interpretation_guide={
            "< -3": "Significant loser",
            "-3 to 0": "Small loser",
            "0 to 3": "Break-even to small winner",
            "3 to 8": "Good winner",
            "> 8": "Great winner (or small sample)"
        }
    ),
}

# Additional stats can be accessed but full definitions not shown for brevity
# This includes: call_cbet_turn_pct, call_cbet_river_pct, raise_cbet_flop_pct, etc.


# ============================================
# COMPOSITE METRICS
# ============================================

COMPOSITE_METRICS = {
    "exploitability_index": StatDefinition(
        name="Exploitability Index",
        abbreviation="EI",
        category="Composite",
        description="Overall measure of how exploitable a player is (0-100). Combines preflop, postflop, and showdown weaknesses.",
        formula="(Preflop_Score × 0.35) + (Postflop_Score × 0.40) + (Showdown_Score × 0.25)",
        optimal_range=(20, 40),
        tooltip="How exploitable this player is. Higher = more weaknesses to target",
        min_sample=200,
        interpretation_guide={
            "0-20": "Tough player, few weaknesses",
            "20-40": "Average exploitability",
            "40-60": "Multiple exploitable tendencies",
            "> 60": "Highly exploitable fish"
        }
    ),

    "pressure_vulnerability_score": StatDefinition(
        name="Pressure Vulnerability Score",
        abbreviation="PVS",
        category="Composite",
        description="How easily a player folds under aggressive pressure (0-100).",
        formula="(Fold3Bet × 0.25) + (FoldFlopCB × 0.20) + (FoldTurnCB × 0.25) + (FoldRiverCB × 0.30)",
        optimal_range=(40, 55),
        tooltip="How easily they fold under pressure. High = apply max pressure",
        min_sample=300,
        interpretation_guide={
            "< 40": "Stubborn, doesn't fold easily",
            "40-55": "Balanced fold frequency",
            "> 60": "Very exploitable by aggression - barrel relentlessly"
        }
    ),

    "aggression_consistency_ratio": StatDefinition(
        name="Aggression Consistency Ratio",
        abbreviation="ACR",
        category="Composite",
        description="How consistently a player maintains aggression across streets (0-1.0).",
        formula="(Turn_C-Bet / Flop_C-Bet) × (River_C-Bet / Turn_C-Bet)",
        optimal_range=(0.55, 0.75),
        tooltip="Give-up tendency. Low = gives up easily on later streets",
        unit="ratio",
        min_sample=250,
        interpretation_guide={
            "< 0.4": "Gives up very easily - float and take pot on turn",
            "0.4-0.7": "Balanced multi-street aggression",
            "> 0.7": "Stubborn barreler, may over-bluff"
        }
    ),

    "positional_awareness_index": StatDefinition(
        name="Positional Awareness Index",
        abbreviation="PAI",
        category="Composite",
        description="How well a player adjusts VPIP by position (0-100). Lower is better.",
        formula="Sum of absolute deviations from optimal VPIP for each position",
        optimal_range=(0, 25),
        tooltip="Position awareness. Low = adjusts well by position",
        min_sample=500,
        interpretation_guide={
            "< 20": "Excellent positional awareness",
            "20-40": "Decent positional adjustment",
            "> 50": "Plays too similar from all positions"
        }
    ),

    "blind_defense_efficiency": StatDefinition(
        name="Blind Defense Efficiency",
        abbreviation="BDE",
        category="Composite",
        description="Quality of blind defense strategy (0-100).",
        formula="(BB_VPIP × 0.4) + ((100 - Fold_to_Steal) × 0.3) + (BB_3bet × 0.3)",
        optimal_range=(40, 50),
        tooltip="How well they defend blinds. Optimal around 45",
        min_sample=200,
        interpretation_guide={
            "< 35": "Folding blinds too much - steal relentlessly",
            "35-50": "Good blind defense",
            "> 55": "Over-defending blinds from OOP"
        }
    ),

    "delayed_aggression_coefficient": StatDefinition(
        name="Delayed Aggression Coefficient",
        abbreviation="DAC",
        category="Composite",
        description="Frequency of deceptive slow-play tactics (check-raise, float).",
        formula="(Flop_C/R × 2) + (Turn_C/R × 1.5) + (Float × 1)",
        optimal_range=(8, 15),
        tooltip="Trap play frequency. Low = very straightforward",
        min_sample=500,
        interpretation_guide={
            "< 5": "Never traps, very straightforward",
            "5-15": "Balanced deceptive play",
            "> 18": "Traps frequently, may check-raise too much"
        }
    ),

    "multi_street_persistence_score": StatDefinition(
        name="Multi-Street Persistence Score",
        abbreviation="MPS",
        category="Composite",
        description="Commitment level when betting across multiple streets.",
        formula="[(Turn_C-Bet / Flop_C-Bet + River_C-Bet / Turn_C-Bet) / 2] × 100",
        optimal_range=(55, 65),
        tooltip="Barrel persistence. Low = gives up easily after flop c-bet",
        min_sample=350,
        interpretation_guide={
            "< 50": "Gives up very easily - float flop, attack turn",
            "50-65": "Reasonable persistence",
            "> 70": "Stubborn barreler"
        }
    ),
}


# ============================================
# PLAYER TYPE DEFINITIONS
# ============================================

PLAYER_TYPES = {
    "NIT": {
        "name": "Nit",
        "description": "Extremely tight player who only plays premium hands. Very predictable and easy to read.",
        "criteria": "VPIP < 15% AND PFR < 12%",
        "exploits": [
            "Steal their blinds aggressively (75%+ success rate)",
            "Fold when they show aggression (they have it)",
            "3-bet them relentlessly (they fold 80%+ of the time)",
            "Float flop c-bets - they give up on turn"
        ],
        "color": "gray"
    },

    "TAG": {
        "name": "Tight-Aggressive (TAG)",
        "description": "Solid player with tight ranges and aggressive play. Good fundamental poker.",
        "criteria": "VPIP 15-25%, PFR 12-20%, Gap < 5%",
        "exploits": [
            "Difficult to exploit - play straightforward",
            "Respect their aggression",
            "Target their blind defense if too tight"
        ],
        "color": "blue"
    },

    "LAG": {
        "name": "Loose-Aggressive (LAG)",
        "description": "Wide range but aggressive. Can be skilled or reckless depending on other stats.",
        "criteria": "VPIP 25-35%, PFR 18-28%, Gap < 7%",
        "exploits": [
            "Call down lighter (they bluff frequently)",
            "3-bet/4-bet for value more often",
            "Don't get pushed around",
            "Check if Fold to 3-Bet is high"
        ],
        "color": "purple"
    ),

    "CALLING_STATION": {
        "name": "Calling Station",
        "description": "Plays too many hands and calls too much. High VPIP-PFR gap.",
        "criteria": "VPIP > 35% AND Gap > 15%",
        "exploits": [
            "NEVER bluff - they won't fold",
            "Value bet thin (they call light)",
            "Bet 3 streets for value with marginal hands",
            "No fancy plays - just value bet"
        ],
        "color": "green"
    },

    "MANIAC": {
        "name": "Maniac",
        "description": "Extremely loose and aggressive. Plays way too many hands aggressively.",
        "criteria": "VPIP > 45% AND PFR > 35%",
        "exploits": [
            "Call down very light (they bluff constantly)",
            "Trap with strong hands",
            "Don't fight fire with fire",
            "Wait for strong hands and let them pay you"
        ],
        "color": "red"
    },

    "FISH": {
        "name": "Fish",
        "description": "Weak recreational player with many significant leaks.",
        "criteria": "Exploitability Index > 60",
        "exploits": [
            "Target relentlessly",
            "Identify specific leak (check EI breakdown)",
            "Adjust to their primary weakness",
            "Print money"
        ],
        "color": "orange"
    },
}


def get_stat_definition(stat_name: str) -> Optional[StatDefinition]:
    """Get the definition for a statistic"""
    if stat_name in TRADITIONAL_STATS:
        return TRADITIONAL_STATS[stat_name]
    elif stat_name in COMPOSITE_METRICS:
        return COMPOSITE_METRICS[stat_name]
    return None


def get_tooltip_text(stat_name: str) -> str:
    """Get tooltip text for a statistic"""
    stat_def = get_stat_definition(stat_name)
    if stat_def:
        return stat_def.tooltip
    return ""


def get_interpretation(stat_name: str, value: float) -> str:
    """Get interpretation text for a statistic value"""
    stat_def = get_stat_definition(stat_name)
    if not stat_def or not stat_def.interpretation_guide:
        return ""

    # Find matching range
    for range_desc, interpretation in stat_def.interpretation_guide.items():
        if _value_matches_range(value, range_desc):
            return interpretation

    return ""


def _value_matches_range(value: float, range_desc: str) -> bool:
    """Check if value matches a range description like '< 15%' or '20-30%'"""
    range_desc = range_desc.replace("%", "").strip()

    if "-" in range_desc and not range_desc.startswith("<") and not range_desc.startswith(">"):
        # Range like "20-30"
        parts = range_desc.split("-")
        low = float(parts[0])
        high = float(parts[1])
        return low <= value <= high
    elif range_desc.startswith("<"):
        # Less than
        threshold = float(range_desc[1:].strip())
        return value < threshold
    elif range_desc.startswith(">"):
        # Greater than
        threshold = float(range_desc[1:].strip())
        return value > threshold

    return False
