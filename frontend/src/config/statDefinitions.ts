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
    description: "Percentage of hands where a player voluntarily puts money in the pot preflop (by calling or raising, not including blinds).",
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
    description: "Percentage of hands where a player raises preflop (including open-raises and 3-bets).",
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
    description: "Percentage of times a player makes a 3-bet when facing an open-raise.",
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
    description: "Percentage of times the preflop aggressor bets the flop.",
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
    description: "Ratio of aggressive actions (bets and raises) to passive actions (calls). Higher = more aggressive.",
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
    description: "Percentage of postflop actions that are aggressive (bet or raise vs call or check).",
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
    description: "Win rate measured in big blinds won per 100 hands played. Positive = winning player.",
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
    description: "Overall measure of how exploitable a player is (0-100). Combines preflop, postflop, and showdown weaknesses.",
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
    description: "How easily a player folds under aggressive pressure (0-100).",
    formula: "(Fold3Bet × 0.25) + (FoldFlopCB × 0.20) + (FoldTurnCB × 0.25) + (FoldRiverCB × 0.30)",
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
