/**
 * TypeScript type definitions for Poker Analysis App
 */

export interface PlayerStats {
  player_name: string;
  total_hands: number;

  // Traditional stats - Preflop
  vpip_pct?: number;
  pfr_pct?: number;
  limp_pct?: number;
  three_bet_pct?: number;
  fold_to_three_bet_pct?: number;
  four_bet_pct?: number;
  cold_call_pct?: number;
  squeeze_pct?: number;

  // Positional VPIP
  vpip_utg?: number;
  vpip_hj?: number;
  vpip_mp?: number;
  vpip_co?: number;
  vpip_btn?: number;
  vpip_sb?: number;
  vpip_bb?: number;

  // Steal and blind defense
  steal_attempt_pct?: number;
  fold_to_steal_pct?: number;
  three_bet_vs_steal_pct?: number;

  // Continuation betting
  cbet_flop_pct?: number;
  cbet_turn_pct?: number;
  cbet_river_pct?: number;

  // Facing cbets
  fold_to_cbet_flop_pct?: number;
  fold_to_cbet_turn_pct?: number;
  fold_to_cbet_river_pct?: number;
  call_cbet_flop_pct?: number;
  call_cbet_turn_pct?: number;
  call_cbet_river_pct?: number;
  raise_cbet_flop_pct?: number;
  raise_cbet_turn_pct?: number;
  raise_cbet_river_pct?: number;

  // Check-raise
  check_raise_flop_pct?: number;
  check_raise_turn_pct?: number;
  check_raise_river_pct?: number;

  // Donk betting
  donk_bet_flop_pct?: number;
  donk_bet_turn_pct?: number;
  donk_bet_river_pct?: number;

  // Float
  float_flop_pct?: number;

  // Aggression
  af?: number;
  afq?: number;

  // Showdown
  wtsd_pct?: number;
  wsd_pct?: number;

  // Win rate
  total_profit_loss?: number;
  bb_per_100?: number;

  // Composite metrics
  exploitability_index?: number;
  pressure_vulnerability_score?: number;
  aggression_consistency_ratio?: number;
  positional_awareness_index?: number;
  blind_defense_efficiency?: number;
  value_bluff_imbalance_ratio?: number;
  range_polarization_factor?: number;
  street_fold_gradient?: number;
  delayed_aggression_coefficient?: number;
  multi_street_persistence_score?: number;
  optimal_stake_skill_rating?: number;
  player_type?: PlayerType;

  // Dates
  first_hand_date?: string;
  last_hand_date?: string;
  last_updated?: string;
}

export type PlayerType = 'NIT' | 'TAG' | 'LAG' | 'CALLING_STATION' | 'MANIAC' | 'FISH' | 'LOOSE_PASSIVE' | 'TIGHT' | 'TIGHT_PASSIVE' | 'UNKNOWN' | null;

export interface PlayerListItem {
  player_name: string;
  total_hands: number;
  vpip_pct?: number;
  pfr_pct?: number;
  player_type?: PlayerType;
  exploitability_index?: number;
}

export interface DatabaseStats {
  total_hands: number;
  total_players: number;
  first_hand_date?: string;
  last_hand_date?: string;
}

export interface UploadResponse {
  session_id: number;
  hands_parsed: number;
  hands_failed: number;
  players_updated: number;
  stake_level?: string;
  processing_time: number;
  message: string;
}

export interface ClaudeQueryRequest {
  query: string;
  conversation_history?: Array<{
    role: string;
    content: string;
  }>;
  conversation_id?: number;
}

export interface ClaudeToolCall {
  tool: string;
  input: Record<string, any>;
  result: Record<string, any>;
}

export interface ClaudeQueryResponse {
  success: boolean;
  response: string;
  tool_calls?: ClaudeToolCall[];
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
  error?: string;
  conversation_id?: number;
}

export interface ConversationMessage {
  message_id: number;
  role: 'user' | 'assistant';
  content: string;
  tool_calls?: Record<string, any> | null;
  usage?: Record<string, any> | null;
  created_at: string;
}

export interface ConversationListItem {
  conversation_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  conversation_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface HealthResponse {
  status: string;
  database: string;
  timestamp: string;
}

// Baseline Comparison Types
export interface Deviation {
  stat: string;
  player: number;
  baseline?: number;
  gto?: number;
  deviation: number;
  abs_deviation: number;
  severity: 'negligible' | 'minor' | 'moderate' | 'severe' | 'extreme';
  exploitable: boolean;
  direction: 'over' | 'under';
  exploit_direction?: string;
  exploit?: string;  // Detailed exploitation strategy
  estimated_ev?: number;
}

export interface BaselineComparisonResponse {
  comparison_type?: 'baseline' | 'gto';
  scenario: string;
  baseline_type?: string;
  baseline_source?: string;
  position?: string;
  gto_baseline?: {
    scenario_type?: string;
    board?: string;
    description?: string;
    gto_bet_freq?: number;
    gto_fold_freq?: number;
    gto_raise_freq?: number;
  };
  deviations: Deviation[];
  exploitable_count: number;
  total_estimated_ev: number;
  summary: string;
}

export interface PlayerExploitAnalysisResponse {
  player_name: string;
  scenarios_analyzed: number;
  total_estimated_ev: number;
  analyses: BaselineComparisonResponse[];
  summary: string;
}

// Leak Analysis Types
export interface LeakItem {
  stat: string;
  player_value: number;
  gto_baseline: number;
  deviation: number;
  direction: 'high' | 'low';
  severity: 'minor' | 'moderate' | 'major' | 'critical';
  tendency: string;
  exploit: string;
  ev_impact_bb_100: number;
}

export interface PlayerTypeInfo {
  type: string;
  description: string;
  key_traits: string[];
  primary_exploit: string;
  secondary_exploits: string[];
}

export interface CoreMetric {
  name: string;
  value: number;
  gto_baseline: number;
  deviation: number;
  reliability: 'excellent' | 'good' | 'moderate' | 'low' | 'insufficient';
  ci_lower: number;
  ci_upper: number;
  sample_size: number;
}

export interface LeakSummary {
  total_leaks: number;
  critical_leaks: number;
  major_leaks: number;
  total_ev_opportunity: number;
  reliability: 'high' | 'moderate' | 'low';
}

export interface LeakAnalysisResponse {
  player_name: string;
  total_hands: number;
  player_type: PlayerTypeInfo;
  core_metrics: CoreMetric[];
  leaks: LeakItem[];
  leak_summary: LeakSummary;
}
