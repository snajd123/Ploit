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
  // Priority leaks sorted by unified scoring algorithm
  priority_leaks?: PriorityLeak[];
}

// Priority leak from backend (used by both MyGame and PlayerProfile)
export interface PriorityLeak {
  scenario_id: string;
  category: 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';
  position: string;
  vs_position?: string | null;
  action: string;
  display_name: string;
  overall_value: number;
  overall_sample: number;
  overall_deviation: number;
  gto_value: number;
  is_leak: boolean;
  leak_severity: 'none' | 'minor' | 'moderate' | 'major';
  leak_direction: string | null;
  confidence_level: string;
  ev_weight?: number;
  priority_score?: number;
}

// GTO Positional Leak format (used by LeakAnalysisView)
export interface GTOPositionalLeak {
  category: string;
  position: string;
  vsPosition?: string;
  action: string;
  playerValue: number;
  gtoValue: number;
  deviation: number;
  severity: 'moderate' | 'major';
  sampleSize: number;
  confidence: 'low' | 'moderate' | 'high';
}

// Scenario Hands Drill-down Types
export interface ScenarioHand {
  hand_id: number;
  timestamp: string | null;
  stake_level: string | null;
  vs_position: string | null;
  player_action: string;
  // Enhanced: Hole card info
  hole_cards: string | null;
  hand_combo: string | null;
  hand_category: string | null;
  hand_tier: number | null;  // 1=Premium, 2=Strong, 3=Playable, 4=Speculative, 5=Weak
  // Enhanced: Stack info
  effective_stack_bb: number | null;
  // GTO comparison
  gto_frequencies: Record<string, number>;
  gto_recommended: string | null;
  action_gto_freq: number;
  // Enhanced: Deviation classification
  deviation_type: 'correct' | 'suboptimal' | 'mistake';
  deviation_severity: 'minor' | 'moderate' | 'major' | null;
  deviation_description: string;
  // Legacy field
  is_mistake: boolean;
}

export interface ScenarioHandsSummary {
  correct: number;
  correct_pct: number;
  suboptimal: number;
  suboptimal_pct: number;
  mistakes: number;
  mistake_pct: number;
}

export interface ScenarioHandsResponse {
  player: string;
  scenario: string;
  position: string;
  vs_position: string | null;
  gto_frequencies: Record<string, number>;
  total_hands: number;
  hands_with_hole_cards: number;
  // Enhanced summary
  summary: ScenarioHandsSummary;
  // Legacy fields
  mistakes: number;
  mistake_rate: number;
  hands: ScenarioHand[];
}

// Hand Replay Types
export interface HandReplayAction {
  player: string;
  action: string;
  amount: number;
  amount_bb: number;
  pot_before: number;
  pot_after: number;
  pot_before_bb: number;
  pot_after_bb: number;
  stack: number;
  stack_bb: number;
  is_aggressive: boolean;
  is_all_in: boolean;
  facing_bet: boolean;
}

export interface HandReplayStreet {
  actions: HandReplayAction[];
  board: string[] | null;
}

export interface HandReplayPlayer {
  name: string;
  position: string | null;
  seat: number;
  stack: number;
  stack_bb: number | null;
  hole_cards: string | null;
  is_hero: boolean;
}

export interface HandReplayResult {
  won: boolean;
  profit_loss: number;
  profit_loss_bb: number;
  showdown: boolean;
}

export interface HeroGTOAnalysis {
  scenario: string;
  vs_position: string | null;
  hero_action: string;
  action_frequency: number;
  gto_frequencies: Record<string, number>;
  recommended_action: string | null;
  deviation_type: 'correct' | 'suboptimal' | 'mistake';
  deviation_description: string;
}

export interface HandReplayResponse {
  hand_id: number;
  timestamp: string | null;
  table_name: string;
  stake_level: string;
  big_blind: number;
  game_type: string;
  button_seat: number;
  pot_size: number;
  pot_size_bb: number;
  rake: number;
  players: HandReplayPlayer[];
  hero: string | null;
  streets: Record<string, HandReplayStreet>;
  board: string[];
  results: Record<string, HandReplayResult>;
  hero_gto_analysis: HeroGTOAnalysis | null;
  raw_hand_text: string | null;
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
  fold_to_three_bet_pct?: number;
}

export interface GTOOptimalRangesResponse {
  overall: Record<string, GTOOptimalRangeItem>;
  positional: GTOPositionalRange[];
  scenarios_count: number;
  frequencies_count: number;
  last_updated?: string;
}

// AI Leak Analysis Types
export interface AIPlayerProfile {
  type: string;
  confidence: 'low' | 'moderate' | 'high';
  key_indicators: {
    vpip: number;
    pfr: number;
    gap: number;
  };
  summary: string;
}

export interface AIRootCause {
  cause: string;
  severity: 'critical' | 'major' | 'minor';
  evidence: string;
  impact: string;
}

export interface AIPriorityImprovement {
  priority: number;
  area: string;
  issue: string;
  heuristic: string;
  target_metric: string;
  specific_actions: string[];
}

export interface AILeakAnalysisResponse {
  success: boolean;
  player_name: string;
  total_hands: number;
  confidence: 'low' | 'moderate' | 'high';
  player_profile: AIPlayerProfile;
  root_causes: AIRootCause[];
  priority_improvements: AIPriorityImprovement[];
  quick_heuristics: string[];
  analysis_text: string;
  error?: string;
}

// Session Leak Comparison Types
export type ImprovementStatus = 'improved' | 'same' | 'worse' | 'overcorrected';
export type LeakSeverity = 'none' | 'minor' | 'moderate' | 'major';
export type ConfidenceLevel = 'insufficient' | 'low' | 'moderate' | 'high';
export type LeakDirection = 'too_tight' | 'too_loose' | 'too_high' | 'too_low' | null;

export interface ScenarioComparison {
  // Scenario identification (the "link")
  scenario_id: string;
  category: 'opening' | 'defense' | 'facing_3bet';
  position: string;
  vs_position: string | null;
  action: string;
  display_name: string;

  // Overall player stats (lifetime)
  overall_value: number;
  overall_sample: number;
  overall_deviation: number;
  is_leak: boolean;
  leak_direction: LeakDirection;
  leak_severity: LeakSeverity;
  ev_weight?: number;

  // GTO baseline
  gto_value: number;

  // Session stats
  session_value: number | null;
  session_sample: number;
  session_deviation: number | null;

  // Improvement analysis
  improvement_score: number | null;
  improvement_status: ImprovementStatus | null;
  within_gto_zone: boolean | null;
  overcorrected: boolean;
  confidence_level: ConfidenceLevel;
  priority_score?: number;
}

export interface SessionLeakComparisonSummary {
  total_scenarios: number;
  scenarios_with_leaks: number;
  scenarios_improved: number;
  scenarios_same: number;
  scenarios_worse: number;
  scenarios_overcorrected: number;
  overall_improvement_score: number;
  session_grade: 'A' | 'B' | 'C' | 'D' | 'F';
}

export interface SessionLeakComparisonResponse {
  session_id: number;
  player_name: string;
  session_hands: number;
  confidence: 'low' | 'moderate' | 'high';
  scenarios: ScenarioComparison[];
  priority_leaks: ScenarioComparison[];
  summary: SessionLeakComparisonSummary;
}

// Session Group Analysis Types (for multi-session trend analysis)
export interface SessionTrendStats {
  hands: number;
  vpip_pct: number;
  pfr_pct: number;
  three_bet_pct: number;
  fold_to_three_bet_pct: number;
  wtsd_pct: number;
  won_at_sd_pct: number;
}

export interface SessionTrendScenario {
  value: number;
  sample: number;
}

export interface SessionTrendData {
  session_id: number;
  date: string | null;
  hands: number;
  profit_bb: number;
  stats: SessionTrendStats;
  scenarios: Record<string, SessionTrendScenario>;
}

export interface SessionGroupAnalysisResponse {
  session_ids: number[];
  player_name: string;
  total_hands: number;
  total_profit_bb: number;
  session_count: number;
  date_range: {
    start: string | null;
    end: string | null;
  };
  confidence: 'low' | 'moderate' | 'high';

  aggregated: {
    scenarios: ScenarioComparison[];
    priority_leaks: ScenarioComparison[];
    summary: SessionLeakComparisonSummary;
  };

  session_trends: SessionTrendData[];
}

// Positional P/L Breakdown Types (Phase 1 Feature)
export interface PositionalPL {
  position: string;
  hands: number;
  profit_bb: number;
  profit_dollars: number;
  bb_100: number;
  expected_bb_100: number;
  vs_expected: number;
  performance: 'above' | 'below' | 'expected';
  win_rate: number;
  hands_won: number;
}

export interface PositionalPLSummary {
  profitable_positions: number;
  losing_positions: number;
  above_expected: number;
  below_expected: number;
}

export interface PositionalPLResponse {
  session_id: number;
  player_name: string;
  total_hands: number;
  total_profit_bb: number;
  big_blind: number;
  positions: PositionalPL[];
  best_position: string | null;
  worst_position: string | null;
  summary: PositionalPLSummary;
}

// Preflop Mistakes Types (Phase 1 Feature)
export interface PreflopMistake {
  hand_id: number;
  timestamp: string | null;
  position: string;
  scenario: string;
  hole_cards: string;
  action_taken: string;
  gto_action: string;
  gto_frequency: number;
  ev_loss_bb: number;
  severity: 'minor' | 'moderate' | 'major';
  in_gto_range: boolean;
  description: string;
}

export interface PreflopMistakesResponse {
  session_id: number;
  player_name: string;
  total_mistakes: number;
  total_ev_loss_bb: number;
  mistakes_by_severity: Record<string, number>;
  mistakes: PreflopMistake[];
}

// GTO Score Types (Phase 1 Feature)
export interface GTOScoreComponent {
  score: number;
  weight: number;
  description: string;
}

export interface GTOMistakesSummary {
  total: number;
  major: number;
  moderate: number;
  minor: number;
  ev_loss_bb: number;
}

export interface GTOScoreResponse {
  session_id: number;
  player_name: string;
  total_hands: number;
  gto_score: number;
  grade: string;
  rating: string;
  components: {
    frequency_accuracy: GTOScoreComponent;
    mistake_avoidance: GTOScoreComponent;
    ev_preservation: GTOScoreComponent;
  };
  mistakes_summary: GTOMistakesSummary;
  weakest_area: 'frequency_accuracy' | 'mistake_avoidance' | 'ev_preservation';
  improvement_suggestion: string;
  confidence: 'low' | 'moderate' | 'high';
}

// Hero Nickname Types (for My Game vs Pools distinction)
export interface HeroNickname {
  nickname_id: number;
  nickname: string;
  site: string | null;
  created_at: string;
}

export interface HeroNicknameCreate {
  nickname: string;
  site?: string | null;
}

export interface HeroNicknameCheck {
  is_hero: boolean;
  nickname_id: number | null;
  site: string | null;
}

export interface HeroNicknameList {
  nicknames: string[];
}

// My Game Types (hero analysis with hole cards)
export interface HeroSessionResponse {
  session_id: number;
  player_name: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  total_hands: number;
  profit_loss_bb: number;
  bb_100: number;
  table_stakes: string;
  table_name: string | null;
}

export interface HeroStatsResponse {
  player_name: string;
  total_hands: number;
  sessions_count: number;
  total_profit_bb: number;
  avg_bb_100: number;
  vpip_pct: number;
  pfr_pct: number;
  three_bet_pct: number;
  fold_to_three_bet_pct: number | null;
  player_type: string | null;
  first_session: string | null;
  last_session: string | null;
}

export interface MyGameOverview {
  hero_nicknames: string[];
  total_sessions: number;
  total_hands: number;
  total_profit_bb: number;
  avg_bb_100: number;
  stats_by_nickname: HeroStatsResponse[];
}

// Pools Types (opponent analysis by site + stake)
export interface PoolSummary {
  pool_id: string;
  display_name: string;
  site: string;
  stake_level: string;
  player_count: number;
  total_hands: number;
  avg_vpip: number;
  avg_pfr: number;
  avg_3bet: number;
}

export interface PoolPlayer {
  player_name: string;
  total_hands: number;
  vpip_pct: number;
  pfr_pct: number;
  three_bet_pct: number;
  fold_to_three_bet_pct: number | null;
  player_type: string | null;
}

export interface PoolDetail {
  pool_id: string;
  display_name: string;
  site: string;
  stake_level: string;
  player_count: number;
  total_hands: number;
  avg_stats: Record<string, number>;
  players: PoolPlayer[];
}

// Strategy Types
export interface OpponentSummary {
  player_name: string;
  player_type: string | null;
  total_hands: number;
  exploitability_index: number | null;
  top_exploits: string[];
  key_stats: Record<string, string>;
}

export interface PreGameStrategyResponse {
  session_summary: string;
  table_dynamics: string;
  overall_strategy: string;
  opponent_summaries: OpponentSummary[];
  focus_areas: string[];
  quick_tips: string[];
}

export interface QuickLookupExploit {
  stat: string;
  exploit: string;
  deviation: string;
  severity: 'critical' | 'major' | 'moderate' | 'minor';
  ev_loss: string | null;
  is_gto_based: boolean;
}

export interface QuickLookupResponse {
  player_name: string;
  player_type: string | null;
  total_hands: number;
  exploitability_index: number | null;
  strategy_summary: string;
  key_stats: Record<string, string>;
  top_exploits: QuickLookupExploit[];
  gto_exploit_count: number;
  traditional_exploit_count: number;
  total_ev: number;
}

// Session Detection Response
export interface DetectedSession {
  session_id: number;
  start_time: string;
  end_time: string;
  total_hands: number;
  profit_loss_bb: number;
}

export interface DetectAllSessionsResponse {
  players_processed: number;
  total_sessions_created: number;
  sessions_by_player: Record<string, DetectedSession[]>;
}
