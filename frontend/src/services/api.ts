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

  // Get database schema (for developers)
  async getDatabaseSchema(): Promise<any> {
    const response = await this.client.get('/api/database/schema');
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

  // Clear all database data
  async clearDatabase(): Promise<{
    message: string;
    deleted: {
      raw_hands: number;
      hand_actions: number;
      player_hand_summary: number;
      player_stats: number;
      upload_sessions: number;
    };
  }> {
    const response = await this.client.delete('/api/database/clear');
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
}

// Export singleton instance
export const api = new ApiClient();
