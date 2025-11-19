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
    description: "Percentage of hands where a player voluntarily puts money in the pot preflop (by calling or raising, not including blinds). A hand counts as VPIP if the player voluntarily puts chips in the pot before the flop - either by calling a raise, making a raise, or open-limping (but not posting blinds).",
    formula: "(hands_where_voluntarily_invested / total_hands) × 100\n\nWhere:\n• hands_where_voluntarily_invested = Count of hands where player called, raised, or limped preflop (excludes posting blinds)\n• total_hands = Total number of hands played",
    optimalRange: [18, 25],
    tooltip: "How often they play a hand. Lower = tighter, Higher = looser",
    unit: "%",
    minSample: 100
  },

  pfr_pct: {
    name: "Pre-Flop Raise",
    abbreviation: "PFR",
    category: "Preflop",
    description: "Percentage of hands where a player raises preflop (including open-raises and 3-bets). This includes any hand where the player is the first raiser or raises after someone else has already raised.",
    formula: "(hands_where_raised_preflop / total_hands) × 100\n\nWhere:\n• hands_where_raised_preflop = Count of hands where player raised preflop (includes open-raising, 3-betting, 4-betting)\n• total_hands = Total number of hands played\n\nNote: PFR is always ≤ VPIP because raising is a subset of voluntarily putting money in",
    optimalRange: [13, 20],
    tooltip: "How often they raise before the flop. Shows aggression level",
    unit: "%",
    minSample: 100
  },

  three_bet_pct: {
    name: "Three-Bet Percentage",
    abbreviation: "3-Bet",
    category: "Preflop",
    description: "Percentage of times a player makes a 3-bet when facing an open-raise. A 3-bet is a re-raise: the first raise is the open, the second raise (the 3-bet) is this statistic.",
    formula: "(made_3bet_count / faced_open_raise_count) × 100\n\nWhere:\n• made_3bet_count = Number of times player re-raised an opener\n• faced_open_raise_count = Number of opportunities to 3-bet (times facing an open-raise)\n\nExample: If player faces 100 open-raises and 3-bets 8 times, 3-Bet% = 8%",
    optimalRange: [6, 12],
    tooltip: "How often they re-raise an opener. Shows aggression and bluffing",
    unit: "%",
    minSample: 200
  },

  fold_to_three_bet_pct: {
    name: "Fold to Three-Bet",
    abbreviation: "F3B",
    category: "Preflop",
    description: "Percentage of times a player folds when facing a 3-bet after opening.",
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
    description: "VPIP from Button (best position). Should be widest range.",
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
    description: "Percentage of times the preflop aggressor bets the flop. A continuation bet (c-bet) occurs when the player who raised preflop bets again on the flop.",
    formula: "(flop_cbets_made / flop_cbet_opportunities) × 100\n\nWhere:\n• flop_cbets_made = Number of times player bet the flop after being the preflop raiser\n• flop_cbet_opportunities = Number of times player was preflop raiser and saw the flop\n\nRequirements for c-bet opportunity:\n- Player raised preflop\n- Player saw the flop\n- Action is on the player (opponents didn't bet first)",
    optimalRange: [55, 70],
    tooltip: "How often they bet flop after raising preflop",
    unit: "%",
    minSample: 200
  },

  cbet_turn_pct: {
    name: "Continuation Bet Turn",
    abbreviation: "Turn C-Bet",
    category: "Continuation Betting",
    description: "Percentage of times the aggressor continues betting on the turn.",
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
    description: "Percentage of times the aggressor continues betting on the river.",
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
    description: "Percentage of times a player folds when facing a flop c-bet.",
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
    description: "Percentage of times a player folds when facing a turn c-bet.",
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
    description: "Percentage of times a player check-raises the flop.",
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
    description: "Percentage of times a player sees a showdown after seeing the flop.",
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
    description: "Percentage of times a player wins when going to showdown.",
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
    description: "Ratio of aggressive actions (bets and raises) to passive actions (calls). Measures how often a player bets or raises versus just calling. Calculated from postflop actions only.",
    formula: "(bets + raises) / calls\n\nWhere:\n• bets = Total number of bets made postflop (flop, turn, river)\n• raises = Total number of raises made postflop\n• calls = Total number of calls made postflop\n\nExample: If player bets 50 times, raises 20 times, and calls 30 times:\nAF = (50 + 20) / 30 = 2.33\n\nInterpretation:\n• AF < 1 = More calling than betting/raising (passive)\n• AF = 1 = Equal aggressive and passive actions\n• AF > 2 = More aggressive than passive (typical for winning players)",
    optimalRange: [2, 3.5],
    tooltip: "How aggressive they play. AF > 3 = very aggressive, AF < 1 = passive",
    unit: "",
    minSample: 200
  },

  afq: {
    name: "Aggression Frequency",
    abbreviation: "AFQ",
    category: "Aggression",
    description: "Percentage of postflop actions that are aggressive (bet or raise vs call or check). Unlike AF which is a ratio, AFQ is a percentage of all voluntary actions.",
    formula: "(bets + raises) / (bets + raises + calls + checks) × 100\n\nWhere:\n• bets = Total postflop bets\n• raises = Total postflop raises\n• calls = Total postflop calls\n• checks = Total postflop checks\n\nExample: In 100 postflop actions:\n- 30 bets, 15 raises, 25 calls, 30 checks\nAFQ = (30 + 15) / (30 + 15 + 25 + 30) × 100 = 45%\n\nInterpretation:\n• AFQ < 40% = Too passive, checking/calling too much\n• AFQ 40-60% = Balanced aggression\n• AFQ > 60% = Very aggressive, may be over-betting",
    optimalRange: [45, 60],
    tooltip: "How often they choose aggression over passivity",
    unit: "%",
    minSample: 200
  },

  bb_per_100: {
    name: "Big Blinds per 100 Hands",
    abbreviation: "BB/100",
    category: "Win Rate",
    description: "Win rate measured in big blinds won per 100 hands played. This is the standard metric for comparing poker win rates across different stake levels. Positive = winning player, negative = losing player.",
    formula: "(total_profit_loss / (total_hands × big_blind)) × 100\n\nWhere:\n• total_profit_loss = Sum of all profits and losses (in dollars)\n• total_hands = Total number of hands played\n• big_blind = Size of the big blind at the stake level played\n\nExample: At $0.25/$0.50 stakes (BB = $0.50):\n- Profit: +$250 over 1,000 hands\nBB/100 = (250 / (1000 × 0.50)) × 100 = 50 BB/100\n\nBenchmarks:\n• 0 BB/100 = Break-even player\n• 3-5 BB/100 = Good winning player\n• 8+ BB/100 = Excellent player or small sample\n• Negative = Losing player",
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
    description: "Overall measure of how exploitable a player is (0-100). Combines preflop, postflop, and showdown weaknesses. Higher scores indicate more exploitable tendencies.",
    formula: "(Preflop_Score × 0.35) + (Postflop_Score × 0.40) + (Showdown_Score × 0.25)\n\nComponent Calculations:\n\n• Preflop_Score: Deviation from optimal VPIP, PFR, 3-bet%, fold to 3-bet%\n  - Each stat deviation from optimal range contributes to score\n  - Larger deviations = higher score\n\n• Postflop_Score: C-bet frequencies, check-raise %, aggression metrics\n  - Measures predictability and imbalances in postflop play\n  - Over-c-betting, under-defending, or passive play increase score\n\n• Showdown_Score: WTSD%, W$SD% combination\n  - High WTSD + Low W$SD = Calling station (high score)\n  - Low WTSD + High W$SD = Nitty (moderate score)\n\nWeighting: Postflop (40%) > Preflop (35%) > Showdown (25%)",
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
    description: "How consistently a player maintains aggression across streets (0-1.0).",
    formula: "(Turn_C-Bet / Flop_C-Bet) × (River_C-Bet / Turn_C-Bet)",
    optimalRange: [55, 75],
    tooltip: "Give-up tendency. Low = gives up easily on later streets",
    unit: "%",
    minSample: 250
  },

  positional_awareness_index: {
    name: "Positional Awareness Index",
    abbreviation: "PAI",
    category: "Composite",
    description: "How well a player adjusts VPIP by position (0-100). Lower is better.",
    formula: "Sum of absolute deviations from optimal VPIP for each position",
    optimalRange: [0, 25],
    tooltip: "Position awareness. Low = adjusts well by position",
    unit: "",
    minSample: 500
  },

  blind_defense_efficiency: {
    name: "Blind Defense Efficiency",
    abbreviation: "BDE",
    category: "Composite",
    description: "Quality of blind defense strategy (0-100).",
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
    description: "Frequency of deceptive slow-play tactics (check-raise, float).",
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
    description: "Commitment level when betting across multiple streets.",
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
