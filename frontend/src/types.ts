/**
 * TypeScript type definitions for Poker Analysis App
 */

export interface PlayerStats {
  player_name: string;
  total_hands: number;

  // Traditional stats
  vpip_pct?: number;
  pfr_pct?: number;
  three_bet_pct?: number;
  fold_to_three_bet_pct?: number;
  cbet_flop_pct?: number;
  fold_to_cbet_flop_pct?: number;
  wtsd_pct?: number;
  wsd_pct?: number;

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

export type PlayerType = 'NIT' | 'TAG' | 'LAG' | 'CALLING_STATION' | 'MANIAC' | 'FISH' | null;

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
}

export interface HealthResponse {
  status: string;
  database: string;
  timestamp: string;
}
