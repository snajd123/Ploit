/**
 * API Client Service
 *
 * Handles all communication with the FastAPI backend.
 */

import axios, { AxiosInstance } from 'axios';
import type {
  PlayerStats,
  PlayerListItem,
  DatabaseStats,
  UploadResponse,
  ClaudeQueryRequest,
  ClaudeQueryResponse,
  HealthResponse,
  PlayerExploitAnalysisResponse,
  ConversationListItem,
  ConversationDetail,
  LeakAnalysisResponse,
  ResetPreviewResponse,
  ClearDatabaseResponse,
  UploadHistoryResponse,
  GTOOptimalRangesResponse,
  GTOAnalysisResponse,
  ScenarioHandsResponse,
  HandReplayResponse,
  AILeakAnalysisResponse,
  SessionLeakComparisonResponse,
  SessionGroupAnalysisResponse,
  PositionalPLResponse,
  PreflopMistakesResponse,
  GTOScoreResponse,
  HeroNickname,
  HeroNicknameCreate,
  HeroNicknameCheck,
  HeroNicknameList,
  MyGameOverview,
  HeroSessionResponse,
  PoolSummary,
  PoolDetail,
} from '../types';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Health check
  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/api/health');
    return response.data;
  }

  // Upload hand history file
  async uploadHandHistory(file: File, onProgress?: (progress: number) => void): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<UploadResponse>('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  }

  // Upload multiple hand history files
  async uploadHandHistoryBatch(files: File[], onProgress?: (progress: number) => void): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await this.client.post<UploadResponse>('/api/upload/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  }

  // Get all players
  async getPlayers(params?: {
    min_hands?: number;
    stake_level?: string;
    sort_by?: string;
    limit?: number;
  }): Promise<PlayerListItem[]> {
    const response = await this.client.get<PlayerListItem[]>('/api/players', { params });
    return response.data;
  }

  // Get player profile
  async getPlayerProfile(playerName: string): Promise<PlayerStats> {
    const response = await this.client.get<PlayerStats>(`/api/players/${encodeURIComponent(playerName)}`);
    return response.data;
  }

  // Get player leak analysis
  async getPlayerLeaks(playerName: string): Promise<LeakAnalysisResponse> {
    const response = await this.client.get<LeakAnalysisResponse>(`/api/players/${encodeURIComponent(playerName)}/leaks`);
    return response.data;
  }

  // Get AI-powered preflop leak analysis
  async getAILeakAnalysis(playerName: string): Promise<AILeakAnalysisResponse> {
    const response = await this.client.post<AILeakAnalysisResponse>(
      `/api/players/${encodeURIComponent(playerName)}/ai-leak-analysis`
    );
    return response.data;
  }

  // Get player GTO analysis
  async getPlayerGTOAnalysis(playerName: string): Promise<GTOAnalysisResponse> {
    const response = await this.client.get<GTOAnalysisResponse>(`/api/players/${encodeURIComponent(playerName)}/gto-analysis`);
    return response.data;
  }

  // Get scenario hands for drill-down
  async getScenarioHands(
    playerName: string,
    scenario: string,
    position: string,
    vsPosition?: string,
    limit: number = 1000
  ): Promise<ScenarioHandsResponse> {
    const params = new URLSearchParams({
      scenario,
      position,
      limit: limit.toString()
    });
    if (vsPosition) {
      params.append('vs_position', vsPosition);
    }
    const response = await this.client.get<ScenarioHandsResponse>(
      `/api/players/${encodeURIComponent(playerName)}/scenario-hands?${params}`
    );
    return response.data;
  }

  // Get full hand history for replay
  async getHandReplay(handId: number): Promise<HandReplayResponse> {
    const response = await this.client.get<HandReplayResponse>(
      `/api/hands/${handId}/replay`
    );
    return response.data;
  }

  // Get GTO range matrix for a scenario (for RangeGrid display)
  async getGTORangeMatrix(
    category: string,
    position: string,
    opponentPosition?: string
  ): Promise<Record<string, Record<string, number>>> {
    const params = new URLSearchParams({
      category,
      position
    });
    if (opponentPosition) {
      params.append('opponent_position', opponentPosition);
    }
    const response = await this.client.get<Record<string, Record<string, number>>>(
      `/api/gto/range-matrix?${params}`
    );
    return response.data;
  }

  // Get database statistics
  async getDatabaseStats(): Promise<DatabaseStats> {
    const response = await this.client.get<DatabaseStats>('/api/database/stats');
    return response.data;
  }

  // Query Claude AI
  async queryClaude(request: ClaudeQueryRequest): Promise<ClaudeQueryResponse> {
    const response = await this.client.post<ClaudeQueryResponse>('/api/query/claude', request);
    return response.data;
  }

  // Recalculate all player statistics
  async recalculateStats(): Promise<{
    message: string;
    players_processed: number;
    players_updated: number;
    players_failed: number;
  }> {
    const response = await this.client.post('/api/database/recalculate-stats');
    return response.data;
  }

  // Get preview of what would be deleted in a reset
  async getResetPreview(): Promise<ResetPreviewResponse> {
    const response = await this.client.get<ResetPreviewResponse>('/api/database/reset-preview');
    return response.data;
  }

  // Clear all player data (preserves GTO reference data)
  async clearDatabase(): Promise<ClearDatabaseResponse> {
    const response = await this.client.delete<ClearDatabaseResponse>('/api/database/clear');
    return response.data;
  }

  // Get upload history
  async getUploadHistory(limit: number = 50, offset: number = 0): Promise<UploadHistoryResponse> {
    const response = await this.client.get<UploadHistoryResponse>('/api/uploads', {
      params: { limit, offset }
    });
    return response.data;
  }

  // Analyze player against poker theory baselines and GTO scenarios
  async analyzePlayerExploits(playerName: string, scenarios?: string[]): Promise<PlayerExploitAnalysisResponse> {
    const response = await this.client.post<PlayerExploitAnalysisResponse>(
      `/api/gto/analyze/${encodeURIComponent(playerName)}`,
      { scenarios }
    );
    return response.data;
  }

  // Generate pre-game strategy
  async generatePreGameStrategy(request: {
    opponent_names: string[];
    hero_name?: string;
    stakes?: string;
    game_type?: string;
  }): Promise<any> {
    const response = await this.client.post('/api/strategy/pre-game', request);
    return response.data;
  }

  // Quick opponent lookup
  async quickLookup(playerName: string): Promise<any> {
    const response = await this.client.get(`/api/strategy/quick-lookup/${encodeURIComponent(playerName)}`);
    return response.data;
  }

  // Get all conversations
  async getConversations(limit: number = 50): Promise<ConversationListItem[]> {
    const response = await this.client.get<ConversationListItem[]>('/api/conversations/', {
      params: { limit }
    });
    return response.data;
  }

  // Get specific conversation
  async getConversation(conversationId: number): Promise<ConversationDetail> {
    const response = await this.client.get<ConversationDetail>(`/api/conversations/${conversationId}`);
    return response.data;
  }

  // Delete conversation
  async deleteConversation(conversationId: number): Promise<void> {
    await this.client.delete(`/api/conversations/${conversationId}`);
  }

  // Detect all sessions from uploaded hands
  async detectAllSessions(sessionGapMinutes: number = 30): Promise<{
    players_processed: number;
    total_sessions_created: number;
    sessions_by_player: Record<string, any[]>;
  }> {
    const response = await this.client.post('/api/sessions/detect-all', null, {
      params: { session_gap_minutes: sessionGapMinutes }
    });
    return response.data;
  }

  // Get session leak comparison (session vs overall vs GTO)
  async getSessionLeakComparison(sessionId: number): Promise<SessionLeakComparisonResponse> {
    const response = await this.client.get<SessionLeakComparisonResponse>(
      `/api/sessions/${sessionId}/leak-comparison`
    );
    return response.data;
  }

  // Get group analysis for multiple sessions with trend data
  async getSessionGroupAnalysis(sessionIds: number[]): Promise<SessionGroupAnalysisResponse> {
    const response = await this.client.post<SessionGroupAnalysisResponse>(
      '/api/sessions/group-analysis',
      { session_ids: sessionIds }
    );
    return response.data;
  }

  // Get GTO optimal ranges from database
  async getGTOOptimalRanges(): Promise<GTOOptimalRangesResponse> {
    const response = await this.client.get<GTOOptimalRangesResponse>('/api/gto/optimal-ranges');
    return response.data;
  }

  // Get positional P/L breakdown for a session
  async getSessionPositionalPL(sessionId: number): Promise<PositionalPLResponse> {
    const response = await this.client.get<PositionalPLResponse>(
      `/api/sessions/${sessionId}/positional-pl`
    );
    return response.data;
  }

  // Get biggest preflop mistakes for a session
  async getSessionPreflopMistakes(sessionId: number, limit: number = 10): Promise<PreflopMistakesResponse> {
    const response = await this.client.get<PreflopMistakesResponse>(
      `/api/sessions/${sessionId}/preflop-mistakes`,
      { params: { limit } }
    );
    return response.data;
  }

  // Get GTO deviation score for a session
  async getSessionGTOScore(sessionId: number): Promise<GTOScoreResponse> {
    const response = await this.client.get<GTOScoreResponse>(
      `/api/sessions/${sessionId}/gto-score`
    );
    return response.data;
  }

  // Aggregate endpoints for multiple sessions
  async getAggregatePositionalPL(sessionIds: number[]): Promise<PositionalPLResponse> {
    const response = await this.client.post<PositionalPLResponse>(
      '/api/sessions/aggregate/positional-pl',
      { session_ids: sessionIds }
    );
    return response.data;
  }

  async getAggregatePreflopMistakes(sessionIds: number[], limit: number = 10): Promise<PreflopMistakesResponse> {
    const response = await this.client.post<PreflopMistakesResponse>(
      '/api/sessions/aggregate/preflop-mistakes',
      { session_ids: sessionIds },
      { params: { limit } }
    );
    return response.data;
  }

  async getAggregateGTOScore(sessionIds: number[]): Promise<GTOScoreResponse> {
    const response = await this.client.post<GTOScoreResponse>(
      '/api/sessions/aggregate/gto-score',
      { session_ids: sessionIds }
    );
    return response.data;
  }

  // ========================================
  // Hero Nicknames / Settings API
  // ========================================

  // Get all hero nicknames
  async getHeroNicknames(): Promise<HeroNickname[]> {
    const response = await this.client.get<HeroNickname[]>('/api/settings/hero-nicknames');
    return response.data;
  }

  // Add a hero nickname
  async addHeroNickname(data: HeroNicknameCreate): Promise<HeroNickname> {
    const response = await this.client.post<HeroNickname>('/api/settings/hero-nicknames', data);
    return response.data;
  }

  // Delete a hero nickname
  async deleteHeroNickname(nicknameId: number): Promise<void> {
    await this.client.delete(`/api/settings/hero-nicknames/${nicknameId}`);
  }

  // Update a hero nickname
  async updateHeroNickname(nicknameId: number, data: Partial<HeroNicknameCreate>): Promise<HeroNickname> {
    const response = await this.client.put<HeroNickname>(
      `/api/settings/hero-nicknames/${nicknameId}`,
      data
    );
    return response.data;
  }

  // Check if a player name is a hero
  async checkIfHero(playerName: string): Promise<HeroNicknameCheck> {
    const response = await this.client.get<HeroNicknameCheck>(
      `/api/settings/hero-nicknames/check/${encodeURIComponent(playerName)}`
    );
    return response.data;
  }

  // Get simple list of all hero nicknames (for quick matching)
  async getHeroNicknameList(): Promise<HeroNicknameList> {
    const response = await this.client.get<HeroNicknameList>('/api/settings/hero-nicknames/list-names');
    return response.data;
  }

  // ========================================
  // My Game API (Hero with hole cards)
  // ========================================

  // Get overview of hero's performance
  async getMyGameOverview(): Promise<MyGameOverview> {
    const response = await this.client.get<MyGameOverview>('/api/my-game/overview');
    return response.data;
  }

  // Get hero's sessions
  async getMyGameSessions(limit: number = 50, offset: number = 0): Promise<HeroSessionResponse[]> {
    const response = await this.client.get<HeroSessionResponse[]>('/api/my-game/sessions', {
      params: { limit, offset }
    });
    return response.data;
  }

  // Check if a player is a hero
  async checkIfMyPlayer(playerName: string): Promise<{ is_hero: boolean; player_name: string }> {
    const response = await this.client.get<{ is_hero: boolean; player_name: string }>(
      `/api/my-game/check/${encodeURIComponent(playerName)}`
    );
    return response.data;
  }

  // Get aggregated GTO analysis for all hero nicknames
  async getMyGameGTOAnalysis(): Promise<GTOAnalysisResponse> {
    const response = await this.client.get<GTOAnalysisResponse>('/api/my-game/gto-analysis');
    return response.data;
  }

  // ========================================
  // Pools API (Opponents by site + stake)
  // ========================================

  // Get all pools
  async getPools(): Promise<PoolSummary[]> {
    const response = await this.client.get<PoolSummary[]>('/api/pools/');
    return response.data;
  }

  // Get pool detail
  async getPoolDetail(stakeLevel: string, limit: number = 50, sortBy: string = 'total_hands'): Promise<PoolDetail> {
    const response = await this.client.get<PoolDetail>(
      `/api/pools/${encodeURIComponent(stakeLevel)}`,
      { params: { limit, sort_by: sortBy } }
    );
    return response.data;
  }

  // Get player detail in a pool
  async getPoolPlayerDetail(stakeLevel: string, playerName: string): Promise<any> {
    const response = await this.client.get(
      `/api/pools/${encodeURIComponent(stakeLevel)}/players/${encodeURIComponent(playerName)}`
    );
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiClient();
