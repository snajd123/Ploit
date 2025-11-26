/**
 * TypeScript type definitions for Poker Analysis App
 */

export interface PlayerStats {
  player_name: string;
  total_hands: number;

  // Preflop statistics (percentages 0-100)
  vpip_pct?: number;
  pfr_pct?: number;
  limp_pct?: number;
  three_bet_pct?: number;
  fold_to_three_bet_pct?: number;
  four_bet_pct?: number;
  cold_call_pct?: number;
  squeeze_pct?: number;

  // Positional VPIP (for positional awareness analysis)
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

  // Win rate
  total_profit_loss?: number;
  bb_per_100?: number;

  // Composite Metrics (preflop-focused)
  exploitability_index?: number;
  positional_awareness_index?: number;
  blind_defense_efficiency?: number;
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
  confidence: 'low' | 'moderate' | 'good' | 'high';
  sample_size: number;
  vpip: number | null;
  pfr: number | null;
  aggression_ratio: number;
  exploits: string[];
}

export interface CoreMetricValue {
  value: number | null;
  interpretation: string;
  description: string;
}

export interface CoreMetrics {
  exploitability_score: CoreMetricValue;
  positional_awareness: CoreMetricValue;
  blind_defense: CoreMetricValue;
  preflop_aggression: CoreMetricValue;
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
  core_metrics: CoreMetrics;
  leaks: LeakItem[];
  leak_summary: LeakSummary;
}

// GTO Analysis Response (comprehensive player GTO comparison)
export interface GTOAnalysisResponse {
  player: string;
  adherence: {
    gto_adherence_score: number;
    avg_deviation: number;
    major_leaks_count: number;
    moderate_leaks_count: number;
    total_hands: number;
  };
  opening_ranges: Array<{
    position: string;
    total_hands: number;
    player_frequency: number;
    gto_frequency: number;
    frequency_diff: number;
    leak_severity: 'minor' | 'moderate' | 'major';
    leak_type: string | null;
  }>;
  defense_vs_open: Array<{
    position: string;
    sample_size: number;
    player_call: number;
    player_3bet: number;
    player_fold: number;
    gto_call: number;
    gto_3bet: number;
    gto_fold: number;
    call_diff: number;
    '3bet_diff': number;
    fold_diff: number;
  }>;
  facing_3bet: Array<{
    position: string;
    sample_size: number;
    player_fold: number;
    player_call: number;
    player_4bet: number;
    gto_fold: number;
    gto_call: number;
    gto_4bet: number;
    fold_diff: number;
    call_diff: number;
    '4bet_diff': number;
  }>;
  facing_3bet_matchups: Array<{
    position: string;
    vs_position: string;
    sample_size: number;
    player_fold: number | null;
    player_call: number | null;
    player_4bet: number | null;
    gto_fold: number;
    gto_call: number;
    gto_4bet: number;
    fold_diff: number | null;
    call_diff: number | null;
    '4bet_diff': number | null;
  }>;
  blind_defense: Array<{
    position: string;
    sample_size: number;
    player_fold: number;
    player_call: number;
    player_3bet: number;
    gto_fold: number;
    gto_call: number;
    gto_3bet: number;
    fold_diff: number;
    call_diff: number;
    '3bet_diff': number;
  }>;
  steal_attempts: Array<{
    position: string;
    sample_size: number;
    player_frequency: number;
    gto_frequency: number;
    frequency_diff: number;
    leak_type: string | null;
  }>;
  position_matchups: Array<{
    position: string;
    vs_position: string;
    sample_size: number;
    player_fold: number | null;
    player_call: number | null;
    player_3bet: number | null;
    gto_fold: number;
    gto_call: number;
    gto_3bet: number;
    fold_diff: number | null;
    call_diff: number | null;
    '3bet_diff': number | null;
  }>;
  facing_4bet_reference: Array<{
    position: string;
    vs_position: string;
    sample_size: number;
    player_fold: number | null;
    player_call: number | null;
    player_5bet: number | null;
    gto_fold: number;
    gto_call: number;
    gto_5bet: number;
    fold_diff: number | null;
    call_diff: number | null;
    '5bet_diff': number | null;
  }>;
}

// Scenario Hands Drill-down Types
export interface ScenarioHand {
  hand_id: number;
  timestamp: string | null;
  stake_level: string | null;
  vs_position: string | null;
  player_action: string;
  gto_frequencies: Record<string, number>;
  gto_recommended: string | null;
  is_mistake: boolean;
  action_gto_freq: number;
}

export interface ScenarioHandsResponse {
  player: string;
  scenario: string;
  position: string;
  vs_position: string | null;
  gto_frequencies: Record<string, number>;
  total_hands: number;
  mistakes: number;
  mistake_rate: number;
  hands: ScenarioHand[];
}

// GTO Scenario Types (Preflop-only)
export type GTOCategory = 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';

export interface GTOScenario {
  scenario_id: number;
  scenario_name: string;
  street: string;  // Always 'preflop' for now
  category: GTOCategory;
  position?: string;  // UTG, MP, CO, BTN, SB, BB
  action?: string;  // open, fold, call, 3bet, 4bet, allin
  opponent_position?: string;
  gto_aggregate_freq?: number;  // For villain analysis (without hole cards)
  description?: string;
}

export interface GTOFrequency {
  frequency_id: number;
  scenario_id: number;
  hand: string;  // e.g., "AhKd"
  position: string;
  frequency: number;  // 0.0 to 1.0
}

// Hero vs Villain Analysis Types
export interface HeroAnalysis {
  scenario: string;
  hole_cards: string;
  action_taken: string;
  gto_frequency: number;  // Combo-level frequency
  is_deviation: boolean;
  deviation_severity?: number;
}

export interface VillainAnalysis {
  scenario: string;
  action_taken: boolean;
  gto_aggregate_freq: number;  // Average frequency across all combos
  note: string;
}

// Player Preflop Action (for hero analysis with hole cards)
export interface PlayerPreflopAction {
  action_id: number;
  hand_id: number;
  player_name: string;
  position: string;
  scenario_id?: number;
  hole_cards?: string;
  action_taken: string;
  gto_frequency?: number;
  is_gto_deviation: boolean;
  deviation_severity?: number;
  is_hero: boolean;
}

// Player Scenario Stats (for both hero and villain aggregated analysis)
export interface PlayerScenarioStats {
  stat_id: number;
  player_name: string;
  scenario_id: number;
  total_occurrences: number;
  action_taken_count: number;
  player_frequency?: number;
  gto_frequency?: number;
  deviation?: number;
  abs_deviation?: number;
  is_hero: boolean;  // TRUE=hero (combo GTO), FALSE=villain (aggregate GTO)
}

// Upload Session Types
export interface UploadSessionItem {
  session_id: number;
  filename: string | null;
  upload_timestamp: string | null;
  hands_parsed: number;
  hands_failed: number;
  players_updated: number;
  stake_level: string | null;
  status: string;
  error_message: string | null;
  processing_time_seconds: number | null;
}

export interface UploadHistoryResponse {
  uploads: UploadSessionItem[];
  total: number;
  limit: number;
  offset: number;
}

// Database Reset Types
export interface ResetPreviewResponse {
  to_delete: {
    raw_hands: number;
    hand_actions: number;
    player_preflop_actions: number;
    player_scenario_stats: number;
    player_stats: number;
    upload_sessions: number;
  };
  to_preserve: {
    gto_scenarios: number;
    gto_frequencies: number;
  };
}

export interface ClearDatabaseResponse {
  message: string;
  deleted: {
    raw_hands: number;
    hand_actions: number;
    player_preflop_actions: number;
    player_scenario_stats: number;
    player_stats: number;
    upload_sessions: number;
  };
  preserved: {
    gto_scenarios: number;
    gto_frequencies: number;
  };
}

// GTO Optimal Ranges Types
export interface GTOOptimalRangeItem {
  stat_key: string;
  optimal_low: number;
  optimal_high: number;
  gto_value?: number;
  source: string;
  description?: string;
}

export interface GTOPositionalRange {
  position: string;
  vpip_pct: number;
  three_bet_pct?: number;
  fold_to_3bet_pct?: number;
}

export interface GTOOptimalRangesResponse {
  overall: Record<string, GTOOptimalRangeItem>;
  positional: GTOPositionalRange[];
  scenarios_count: number;
  frequencies_count: number;
  last_updated?: string;
}
