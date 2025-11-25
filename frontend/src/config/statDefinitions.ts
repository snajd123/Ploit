/**
 * Poker Statistics Definitions for Frontend
 *
 * This file contains all stat definitions, tooltips, formulas, and optimal ranges
 * Source: backend/config/poker_statistics_definitions.py
 */

export interface StatDefinition {
  name: string;
  abbreviation: string;
  category: string;
  description: string;
  formula: string;
  optimalRange?: [number, number];
  tooltip: string;
  unit?: string;
  minSample?: number;
  interpretationGuide?: Record<string, string>;
}

export const STAT_DEFINITIONS: Record<string, StatDefinition> = {
  // PREFLOP
  vpip_pct: {
    name: "Voluntarily Put Money In Pot",
    abbreviation: "VPIP",
    category: "Preflop",
    description: "Percentage of hands where a player voluntarily puts money in the pot preflop (by calling or raising, not including blinds).\n\nA hand counts as VPIP if the player voluntarily puts chips in the pot before the flop - either by calling a raise, making a raise, or open-limping (but not posting blinds).\n\nVariables:\n• hands_where_voluntarily_invested = Count of hands where player called, raised, or limped preflop (excludes posting blinds)\n• total_hands = Total number of hands played",
    formula: "(hands_where_voluntarily_invested / total_hands) × 100",
    optimalRange: [18, 25],
    tooltip: "How often they play a hand. Lower = tighter, Higher = looser",
    unit: "%",
    minSample: 100
  },

  pfr_pct: {
    name: "Pre-Flop Raise",
    abbreviation: "PFR",
    category: "Preflop",
    description: "Percentage of hands where a player raises preflop (including open-raises and 3-bets). This includes any hand where the player is the first raiser or raises after someone else has already raised.\n\nVariables:\n• hands_where_raised_preflop = Count of hands where player raised preflop (includes open-raising, 3-betting, 4-betting)\n• total_hands = Total number of hands played\n\nNote: PFR is always ≤ VPIP because raising is a subset of voluntarily putting money in.",
    formula: "(hands_where_raised_preflop / total_hands) × 100",
    optimalRange: [13, 20],
    tooltip: "How often they raise before the flop. Shows aggression level",
    unit: "%",
    minSample: 100
  },

  three_bet_pct: {
    name: "Three-Bet Percentage",
    abbreviation: "3-Bet",
    category: "Preflop",
    description: "Percentage of times a player makes a 3-bet when facing an open-raise. A 3-bet is a re-raise: the first raise is the open, the second raise (the 3-bet) is this statistic.\n\nVariables:\n• made_3bet_count = Number of times player re-raised an opener\n• faced_open_raise_count = Number of opportunities to 3-bet (times facing an open-raise)\n\nExample: If player faces 100 open-raises and 3-bets 8 times, 3-Bet% = 8%",
    formula: "(made_3bet_count / faced_open_raise_count) × 100",
    optimalRange: [6, 12],
    tooltip: "How often they re-raise an opener. Shows aggression and bluffing",
    unit: "%",
    minSample: 200
  },

  fold_to_three_bet_pct: {
    name: "Fold to Three-Bet",
    abbreviation: "F3B",
    category: "Preflop",
    description: "Percentage of times a player folds when facing a 3-bet after opening. This measures how often a player gives up their hand when someone re-raises their initial raise.\n\nVariables:\n• folded_to_3bet = Number of times player folded after facing a 3-bet\n• faced_3bet_count = Number of opportunities where player opened and then faced a 3-bet\n\nExample: Player opens 100 times, gets 3-bet 20 times, folds 12 times = 60% fold to 3-bet\n\nInterpretation:\n• F3B > 65% = Too weak, exploitable with light 3-bets\n• F3B 50-60% = Balanced continuation strategy\n• F3B < 45% = Too stubborn, may be 4-betting or calling too light",
    formula: "(folded_to_3bet / faced_3bet_count) × 100",
    optimalRange: [50, 60],
    tooltip: "How often they fold to a 3-bet. High = exploitable with 3-bets",
    unit: "%",
    minSample: 100
  },

  // POSITIONAL
  vpip_btn: {
    name: "VPIP from Button",
    abbreviation: "BTN VPIP",
    category: "Positional",
    description: "VPIP from Button (best position). Should be widest range. The button is the most profitable position since you act last on all postflop streets, allowing you to play more hands profitably.\n\nVariables:\n• vpip_btn_count = Number of hands voluntarily played from button position\n• btn_hands = Total number of hands dealt on the button\n\nInterpretation:\n• BTN VPIP < 35% = Too tight, not exploiting position advantage\n• BTN VPIP 43-51% = Optimal exploitation of position\n• BTN VPIP > 60% = Overplaying position, likely unprofitable",
    formula: "(vpip_btn_count / btn_hands) × 100",
    optimalRange: [43, 51],
    tooltip: "VPIP from button. Should play the most hands here",
    unit: "%",
    minSample: 50
  },

  // CONTINUATION BETTING
  cbet_flop_pct: {
    name: "Continuation Bet Flop",
    abbreviation: "Flop C-Bet",
    category: "Continuation Betting",
    description: "Percentage of times the preflop aggressor bets the flop. A continuation bet (c-bet) occurs when the player who raised preflop bets again on the flop.\n\nVariables:\n• flop_cbets_made = Number of times player bet the flop after being the preflop raiser\n• flop_cbet_opportunities = Number of times player was preflop raiser and saw the flop\n\nRequirements for c-bet opportunity:\n- Player raised preflop\n- Player saw the flop\n- Action is on the player (opponents didn't bet first)",
    formula: "(flop_cbets_made / flop_cbet_opportunities) × 100",
    optimalRange: [55, 70],
    tooltip: "How often they bet flop after raising preflop",
    unit: "%",
    minSample: 200
  },

  cbet_turn_pct: {
    name: "Continuation Bet Turn",
    abbreviation: "Turn C-Bet",
    category: "Continuation Betting",
    description: "Percentage of times the aggressor continues betting on the turn after c-betting the flop. This is often called a 'double barrel' and shows commitment to the hand.\n\nVariables:\n• turn_cbets_made = Number of times player bet turn after betting flop as preflop raiser\n• turn_cbet_opportunities = Number of times player bet flop as preflop raiser and had opportunity to bet turn\n\nRequirements:\n- Player raised preflop\n- Player c-bet the flop\n- Player has option to bet turn (opponents didn't bet first)\n\nInterpretation:\n• Turn C-Bet < 40% = Gives up too easily after flop c-bet\n• Turn C-Bet 45-60% = Balanced double-barrel frequency\n• Turn C-Bet > 70% = Over-barreling, too sticky with aggression",
    formula: "(turn_cbets_made / turn_cbet_opportunities) × 100",
    optimalRange: [45, 60],
    tooltip: "How often they barrel the turn after c-betting flop",
    unit: "%",
    minSample: 100
  },

  cbet_river_pct: {
    name: "Continuation Bet River",
    abbreviation: "River C-Bet",
    category: "Continuation Betting",
    description: "Percentage of times the aggressor continues betting on the river after betting flop and turn. This is called a 'triple barrel' and represents maximum commitment or a large bluff.\n\nVariables:\n• river_cbets_made = Number of times player bet river after betting flop and turn as preflop raiser\n• river_cbet_opportunities = Number of times player bet flop and turn as preflop raiser and had option to bet river\n\nRequirements:\n- Player raised preflop\n- Player c-bet flop and turn\n- Player has option to bet river\n\nInterpretation:\n• River C-Bet < 35% = Conservative river play, may be missing value\n• River C-Bet 40-55% = Balanced triple barrel frequency\n• River C-Bet > 65% = Over-aggressive, triple-barreling too many bluffs",
    formula: "(river_cbets_made / river_cbet_opportunities) × 100",
    optimalRange: [40, 55],
    tooltip: "Triple barrel frequency - very aggressive move",
    unit: "%",
    minSample: 50
  },

  // C-BET DEFENSE
  fold_to_cbet_flop_pct: {
    name: "Fold to C-Bet Flop",
    abbreviation: "Fold Flop CB",
    category: "C-Bet Defense",
    description: "Percentage of times a player folds when facing a flop c-bet. This measures defensive play when opponent continues their preflop aggression on the flop.\n\nVariables:\n• folded_to_flop_cbet = Number of times player folded to a flop c-bet\n• faced_flop_cbet = Number of times player faced a flop c-bet\n\nContext: Player must have voluntarily entered the pot (called or raised preflop), then faced a c-bet from the preflop raiser on the flop.\n\nInterpretation:\n• Fold > 65% = Too weak, easily c-bet off hands (highly exploitable)\n• Fold 45-60% = Balanced flop defense\n• Fold < 40% = Too sticky, calling/raising with weak ranges",
    formula: "(folded_to_flop_cbet / faced_flop_cbet) × 100",
    optimalRange: [45, 60],
    tooltip: "How often they fold to flop c-bet. High = exploitable",
    unit: "%",
    minSample: 200
  },

  fold_to_cbet_turn_pct: {
    name: "Fold to C-Bet Turn",
    abbreviation: "Fold Turn CB",
    category: "C-Bet Defense",
    description: "Percentage of times a player folds when facing a turn c-bet (double barrel). Turn bets represent stronger commitment, so fold frequencies should be slightly higher than flop.\n\nVariables:\n• folded_to_turn_cbet = Number of times player folded to a turn c-bet\n• faced_turn_cbet = Number of times player faced a turn c-bet after calling the flop\n\nContext: Player called flop c-bet, then faces another bet on turn from same aggressor.\n\nInterpretation:\n• Fold > 70% = Too weak to turn pressure, highly exploitable\n• Fold 50-65% = Balanced turn defense\n• Fold < 45% = Too stubborn, calling with too many weak hands",
    formula: "(folded_to_turn_cbet / faced_turn_cbet) × 100",
    optimalRange: [50, 65],
    tooltip: "Fold frequency vs turn barrel",
    unit: "%",
    minSample: 100
  },

  // CHECK-RAISE
  check_raise_flop_pct: {
    name: "Check-Raise Flop",
    abbreviation: "Flop C/R",
    category: "Deceptive Play",
    description: "Percentage of times a player check-raises the flop. This is a powerful deceptive move that represents either a strong hand slowplaying or a semi-bluff.\n\nVariables:\n• check_raised_flop = Number of times player checked, faced a bet, then raised on the flop\n• check_raise_opp_flop = Number of flop opportunities where player checked and faced a bet\n\nContext: Player must check first, opponent must bet, then player raises.\n\nInterpretation:\n• C/R < 5% = Too straightforward, missing bluff opportunities\n• C/R 7-15% = Balanced check-raise frequency\n• C/R > 20% = Over-aggressive, check-raising too light",
    formula: "(check_raised_flop / check_raise_opp_flop) × 100",
    optimalRange: [7, 15],
    tooltip: "Trap play frequency on flop. Powerful aggressive move",
    unit: "%",
    minSample: 100
  },

  // SHOWDOWN
  wtsd_pct: {
    name: "Went to Showdown",
    abbreviation: "WTSD",
    category: "Showdown",
    description: "Percentage of times a player sees a showdown after seeing the flop. This measures how often a player takes their hand all the way to showdown versus folding on flop, turn, or river.\n\nVariables:\n• went_to_showdown = Number of hands that reached showdown\n• saw_flop = Total number of flops seen\n\nInterpretation:\n• WTSD > 35% = Calling station, not folding enough weak hands\n• WTSD 24-30% = Balanced showdown frequency\n• WTSD < 20% = Too nitty, may be folding too many marginal hands\n\nNote: Should be analyzed together with W$SD - high WTSD with low W$SD indicates calling station tendencies.",
    formula: "(went_to_showdown / saw_flop) × 100",
    optimalRange: [24, 30],
    tooltip: "How often they go to showdown. High = calling station",
    unit: "%",
    minSample: 200
  },

  wsd_pct: {
    name: "Won at Showdown",
    abbreviation: "W$SD",
    category: "Showdown",
    description: "Percentage of times a player wins when going to showdown. This measures hand selection and ability to reach showdown with strong hands. Around 50% is expected in balanced play.\n\nVariables:\n• won_at_showdown = Number of showdowns won\n• went_to_showdown = Total number of showdowns reached\n\nInterpretation:\n• W$SD > 55% = Very strong hand selection, possibly too tight\n• W$SD 48-54% = Balanced showdown performance\n• W$SD < 45% = Poor hand selection, going to showdown with weak hands\n\nNote: Analyze with WTSD - Low WTSD + High W$SD = tight/nitty, High WTSD + Low W$SD = calling station.",
    formula: "(won_at_showdown / went_to_showdown) × 100",
    optimalRange: [48, 54],
    tooltip: "Win rate at showdown. ~50% is expected",
    unit: "%",
    minSample: 100
  },

  // AGGRESSION METRICS
  af: {
    name: "Aggression Factor",
    abbreviation: "AF",
    category: "Aggression",
    description: "Ratio of aggressive actions (bets and raises) to passive actions (calls). Measures how often a player bets or raises versus just calling. Calculated from postflop actions only.\n\nVariables:\n• bets = Total number of bets made postflop (flop, turn, river)\n• raises = Total number of raises made postflop\n• calls = Total number of calls made postflop\n\nExample: If player bets 50 times, raises 20 times, and calls 30 times:\nAF = (50 + 20) / 30 = 2.33\n\nInterpretation:\n• AF < 1 = More calling than betting/raising (passive)\n• AF = 1 = Equal aggressive and passive actions\n• AF > 2 = More aggressive than passive (typical for winning players)",
    formula: "(bets + raises) / calls",
    optimalRange: [2, 3.5],
    tooltip: "How aggressive they play. AF > 3 = very aggressive, AF < 1 = passive",
    unit: "",
    minSample: 200
  },

  afq: {
    name: "Aggression Frequency",
    abbreviation: "AFQ",
    category: "Aggression",
    description: "Percentage of postflop actions that are aggressive (bet or raise vs call or check). Unlike AF which is a ratio, AFQ is a percentage of all voluntary actions.\n\nVariables:\n• bets = Total postflop bets\n• raises = Total postflop raises\n• calls = Total postflop calls\n• checks = Total postflop checks\n\nExample: In 100 postflop actions:\n- 30 bets, 15 raises, 25 calls, 30 checks\nAFQ = (30 + 15) / (30 + 15 + 25 + 30) × 100 = 45%\n\nInterpretation:\n• AFQ < 40% = Too passive, checking/calling too much\n• AFQ 40-60% = Balanced aggression\n• AFQ > 60% = Very aggressive, may be over-betting",
    formula: "(bets + raises) / (bets + raises + calls + checks) × 100",
    optimalRange: [45, 60],
    tooltip: "How often they choose aggression over passivity",
    unit: "%",
    minSample: 200
  },

  bb_per_100: {
    name: "Big Blinds per 100 Hands",
    abbreviation: "BB/100",
    category: "Win Rate",
    description: "Win rate measured in big blinds won per 100 hands played. This is the standard metric for comparing poker win rates across different stake levels. Positive = winning player, negative = losing player.\n\nVariables:\n• total_profit_loss = Sum of all profits and losses (in dollars)\n• total_hands = Total number of hands played\n• big_blind = Size of the big blind at the stake level played\n\nExample: At $0.25/$0.50 stakes (BB = $0.50):\n- Profit: +$250 over 1,000 hands\nBB/100 = (250 / (1000 × 0.50)) × 100 = 50 BB/100\n\nBenchmarks:\n• 0 BB/100 = Break-even player\n• 3-5 BB/100 = Good winning player\n• 8+ BB/100 = Excellent player or small sample\n• Negative = Losing player",
    formula: "(total_profit_loss / (total_hands × big_blind)) × 100",
    optimalRange: [3, 10],
    tooltip: "Win rate. Positive = winning, negative = losing. 5+ bb/100 is very strong",
    unit: " BB",
    minSample: 1000
  },

  // COMPOSITE METRICS
  exploitability_index: {
    name: "Exploitability Index",
    abbreviation: "EI",
    category: "Composite",
    description: "Overall measure of how exploitable a player is (0-100). Combines preflop, postflop, and showdown weaknesses. Higher scores indicate more exploitable tendencies.\n\nComponent Calculations:\n\n• Preflop_Score: Deviation from optimal VPIP, PFR, 3-bet%, fold to 3-bet%\n  - Each stat deviation from optimal range contributes to score\n  - Larger deviations = higher score\n\n• Postflop_Score: C-bet frequencies, check-raise %, aggression metrics\n  - Measures predictability and imbalances in postflop play\n  - Over-c-betting, under-defending, or passive play increase score\n\n• Showdown_Score: WTSD%, W$SD% combination\n  - High WTSD + Low W$SD = Calling station (high score)\n  - Low WTSD + High W$SD = Nitty (moderate score)\n\nWeighting: Postflop (40%) > Preflop (35%) > Showdown (25%)",
    formula: "(Preflop_Score × 0.35) + (Postflop_Score × 0.40) + (Showdown_Score × 0.25)",
    optimalRange: [20, 40],
    tooltip: "How exploitable this player is. Higher = more weaknesses to target",
    unit: "",
    minSample: 200
  },

  pressure_vulnerability_score: {
    name: "Pressure Vulnerability Score",
    abbreviation: "PVS",
    category: "Composite",
    description: "How easily a player folds under aggressive pressure (0-100). Measures fold frequency when facing bets and raises across all streets.",
    formula: "(Fold3Bet × 0.25) + (FoldFlopCB × 0.20) + (FoldTurnCB × 0.25) + (FoldRiverCB × 0.30)\n\nWhere:\n• Fold3Bet = Fold to 3-bet percentage (weighted 25%)\n• FoldFlopCB = Fold to flop c-bet percentage (weighted 20%)\n• FoldTurnCB = Fold to turn c-bet percentage (weighted 25%)\n• FoldRiverCB = Fold to river c-bet percentage (weighted 30%)\n\nExample: Player with:\n- Fold to 3-bet: 70%\n- Fold to flop c-bet: 55%\n- Fold to turn c-bet: 65%\n- Fold to river c-bet: 70%\n\nPVS = (70×0.25) + (55×0.20) + (65×0.25) + (70×0.30) = 65.75\n\nInterpretation:\n• PVS > 60 = Very vulnerable to pressure (exploit with aggression)\n• PVS 40-60 = Balanced defense\n• PVS < 40 = Stubborn/sticky (value bet heavy, don't bluff)",
    optimalRange: [40, 55],
    tooltip: "How easily they fold under pressure. High = apply max pressure",
    unit: "",
    minSample: 300
  },

  aggression_consistency_ratio: {
    name: "Aggression Consistency Ratio",
    abbreviation: "ACR",
    category: "Composite",
    description: "How consistently a player maintains aggression across streets. Measures if a player follows through with aggression or gives up after the flop c-bet. Calculated as the geometric mean of barrel frequencies.\n\nVariables:\n• Turn_C-Bet = Turn c-bet percentage (e.g., 50%)\n• Flop_C-Bet = Flop c-bet percentage (e.g., 65%)\n• River_C-Bet = River c-bet percentage (e.g., 45%)\n\nCalculation:\n1. Turn continuation rate = Turn_C-Bet / Flop_C-Bet\n2. River continuation rate = River_C-Bet / Turn_C-Bet\n3. ACR = Product of both rates × 100\n\nExample: Flop C-Bet 65%, Turn C-Bet 50%, River C-Bet 45%\nACR = (50/65) × (45/50) × 100 = 0.77 × 0.90 × 100 = 69.3%\n\nInterpretation:\n• ACR > 70% = Very persistent, maintains aggression\n• ACR 55-75% = Balanced persistence\n• ACR < 50% = Gives up too easily, exploitable with calls",
    formula: "(Turn_C-Bet / Flop_C-Bet) × (River_C-Bet / Turn_C-Bet) × 100",
    optimalRange: [55, 75],
    tooltip: "Give-up tendency. Low = gives up easily on later streets",
    unit: "%",
    minSample: 250
  },

  positional_awareness_index: {
    name: "Positional Awareness Index",
    abbreviation: "PAI",
    category: "Composite",
    description: "How well a player adjusts VPIP by position. Measures understanding of positional advantage. Lower scores indicate better position awareness. Calculated by comparing actual VPIP to optimal VPIP for each position.\n\nPositions and Optimal VPIP:\n• Early Position (UTG, UTG+1): 14-18%\n• Middle Position (MP): 18-22%\n• Cutoff (CO): 26-32%\n• Button (BTN): 43-51%\n• Small Blind (SB): 25-32%\n• Big Blind (BB): 32-40%\n\nCalculation:\nPAI = |VPIP_EP - Optimal_EP| + |VPIP_MP - Optimal_MP| + |VPIP_CO - Optimal_CO| + |VPIP_BTN - Optimal_BTN| + |VPIP_SB - Optimal_SB| + |VPIP_BB - Optimal_BB|\n\nExample: Player has same 25% VPIP from all positions:\nPAI = |25-16| + |25-20| + |25-29| + |25-47| + |25-28| + |25-36| = 9+5+4+22+3+11 = 54\n\nInterpretation:\n• PAI < 15 = Excellent position awareness\n• PAI 15-25 = Good position adjustment\n• PAI > 30 = Poor awareness, not adjusting to position",
    formula: "Σ|Actual_VPIP_position - Optimal_VPIP_position|",
    optimalRange: [0, 25],
    tooltip: "Position awareness. Low = adjusts well by position",
    unit: "",
    minSample: 500
  },

  blind_defense_efficiency: {
    name: "Blind Defense Efficiency",
    abbreviation: "BDE",
    category: "Composite",
    description: "Quality of blind defense strategy. Combines how often and how aggressively a player defends their big blind against steals. Balances calling, 3-betting, and folding frequencies.\n\nVariables:\n• BB_VPIP = Big blind VPIP percentage (how often defending)\n• Fold_to_Steal = Fold to steal percentage (inversely weighted)\n• BB_3bet = Big blind 3-bet percentage (aggression in defense)\n\nWeighting:\n• BB_VPIP: 40% weight - Primary defense frequency\n• Defense Rate (100 - Fold_to_Steal): 30% weight - Resistance to steals\n• BB_3bet: 30% weight - Aggressive defense\n\nExample: BB_VPIP 35%, Fold to Steal 55%, BB 3-bet 12%\nBDE = (35 × 0.4) + ((100-55) × 0.3) + (12 × 0.3)\nBDE = 14 + 13.5 + 3.6 = 31.1\n\nInterpretation:\n• BDE > 50 = Over-defending blinds, losing chips\n• BDE 40-50 = Balanced blind defense\n• BDE < 35 = Under-defending, exploitable with steals",
    formula: "(BB_VPIP × 0.4) + ((100 - Fold_to_Steal) × 0.3) + (BB_3bet × 0.3)",
    optimalRange: [40, 50],
    tooltip: "How well they defend blinds. Optimal around 45",
    unit: "",
    minSample: 200
  },

  delayed_aggression_coefficient: {
    name: "Delayed Aggression Coefficient",
    abbreviation: "DAC",
    category: "Composite",
    description: "Frequency of deceptive slow-play tactics including check-raises and float plays. Measures how often a player disguises strength or uses delayed aggression rather than betting directly.\n\nVariables:\n• Flop_C/R = Flop check-raise percentage\n• Turn_C/R = Turn check-raise percentage\n• Float = Float percentage (call flop with intention to take away pot on turn)\n\nWeighting:\n• Flop C/R: 2x weight (most common and powerful)\n• Turn C/R: 1.5x weight (less common but very strong)\n• Float: 1x weight (deceptive call)\n\nExample: Flop C/R 10%, Turn C/R 8%, Float 5%\nDAC = (10 × 2) + (8 × 1.5) + (5 × 1)\nDAC = 20 + 12 + 5 = 37\n\nInterpretation:\n• DAC > 20 = Very deceptive, uses lots of traps\n• DAC 8-15 = Balanced deception frequency\n• DAC < 5 = Very straightforward, transparent play",
    formula: "(Flop_C/R × 2) + (Turn_C/R × 1.5) + (Float × 1)",
    optimalRange: [8, 15],
    tooltip: "Trap play frequency. Low = very straightforward",
    unit: "",
    minSample: 500
  },

  multi_street_persistence_score: {
    name: "Multi-Street Persistence Score",
    abbreviation: "MPS",
    category: "Composite",
    description: "Commitment level when betting across multiple streets. Measures the average continuation rate from flop to turn and turn to river. Different from ACR (which uses product), MPS uses arithmetic mean.\n\nVariables:\n• Turn_C-Bet = Turn c-bet percentage\n• Flop_C-Bet = Flop c-bet percentage\n• River_C-Bet = River c-bet percentage\n\nCalculation:\n1. Flop-to-Turn rate = Turn_C-Bet / Flop_C-Bet\n2. Turn-to-River rate = River_C-Bet / Turn_C-Bet\n3. MPS = Average of both rates × 100\n\nExample: Flop C-Bet 60%, Turn C-Bet 40%, River C-Bet 30%\nFlop-to-Turn = 40/60 = 0.667\nTurn-to-River = 30/40 = 0.75\nMPS = [(0.667 + 0.75) / 2] × 100 = 70.85%\n\nInterpretation:\n• MPS > 70% = Very persistent, rarely gives up\n• MPS 55-65% = Balanced multi-street aggression\n• MPS < 50% = Gives up easily, one-and-done c-betting",
    formula: "[(Turn_C-Bet / Flop_C-Bet + River_C-Bet / Turn_C-Bet) / 2] × 100",
    optimalRange: [55, 65],
    tooltip: "Barrel persistence. Low = gives up easily after flop c-bet",
    unit: "%",
    minSample: 350
  },
};

/**
 * Get stat definition by key
 */
export function getStatDefinition(statKey: string): StatDefinition | undefined {
  return STAT_DEFINITIONS[statKey];
}

/**
 * GTO optimal range from API
 */
export interface GTOOptimalRange {
  stat_key: string;
  optimal_low: number;
  optimal_high: number;
  gto_value?: number;
  source: string;
}

/**
 * Get stat definition with GTO optimal range override
 * If gtoRanges is provided and has data for this stat, use those values
 */
export function getStatDefinitionWithGTO(
  statKey: string,
  gtoRanges?: Record<string, GTOOptimalRange>
): StatDefinition | undefined {
  const baseDef = STAT_DEFINITIONS[statKey];
  if (!baseDef) return undefined;

  // If we have GTO data for this stat, override the optimal range
  if (gtoRanges && gtoRanges[statKey]) {
    const gtoRange = gtoRanges[statKey];
    return {
      ...baseDef,
      optimalRange: [gtoRange.optimal_low, gtoRange.optimal_high],
      tooltip: gtoRange.gto_value
        ? `${baseDef.tooltip} (GTO: ${gtoRange.gto_value.toFixed(1)}%)`
        : baseDef.tooltip,
    };
  }

  return baseDef;
}

/**
 * Get all stat definitions with GTO overrides applied
 */
export function getStatDefinitionsWithGTO(
  gtoRanges?: Record<string, GTOOptimalRange>
): Record<string, StatDefinition> {
  if (!gtoRanges) return STAT_DEFINITIONS;

  const merged: Record<string, StatDefinition> = {};
  for (const [key, def] of Object.entries(STAT_DEFINITIONS)) {
    const gtoRange = gtoRanges[key];
    if (gtoRange) {
      merged[key] = {
        ...def,
        optimalRange: [gtoRange.optimal_low, gtoRange.optimal_high],
        tooltip: gtoRange.gto_value
          ? `${def.tooltip} (GTO: ${gtoRange.gto_value.toFixed(1)}%)`
          : def.tooltip,
      };
    } else {
      merged[key] = def;
    }
  }
  return merged;
}

/**
 * Get tooltip text for a stat
 */
export function getStatTooltip(statKey: string): string {
  const def = STAT_DEFINITIONS[statKey];
  return def?.tooltip || "";
}

/**
 * Get interpretation for a stat value
 */
export function getStatInterpretation(statKey: string, value: number): string {
  const def = STAT_DEFINITIONS[statKey];
  if (!def || !def.interpretationGuide) return "";

  // Find matching range
  for (const [range, interpretation] of Object.entries(def.interpretationGuide)) {
    if (valueMatchesRange(value, range)) {
      return interpretation;
    }
  }

  return "";
}

function valueMatchesRange(value: number, rangeDesc: string): boolean {
  const cleanRange = rangeDesc.replace("%", "").trim();

  if (cleanRange.includes("-") && !cleanRange.startsWith("<") && !cleanRange.startsWith(">")) {
    const [low, high] = cleanRange.split("-").map(Number);
    return value >= low && value <= high;
  } else if (cleanRange.startsWith("<")) {
    const threshold = Number(cleanRange.substring(1).trim());
    return value < threshold;
  } else if (cleanRange.startsWith(">")) {
    const threshold = Number(cleanRange.substring(1).trim());
    return value > threshold;
  }

  return false;
}
