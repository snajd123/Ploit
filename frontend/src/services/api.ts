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

  // Get player GTO analysis
  async getPlayerGTOAnalysis(playerName: string): Promise<GTOAnalysisResponse> {
    const response = await this.client.get<GTOAnalysisResponse>(`/api/players/${encodeURIComponent(playerName)}/gto-analysis`);
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

  // Get GTO optimal ranges from database
  async getGTOOptimalRanges(): Promise<GTOOptimalRangesResponse> {
    const response = await this.client.get<GTOOptimalRangesResponse>('/api/gto/optimal-ranges');
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiClient();
