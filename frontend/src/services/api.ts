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
}

// Export singleton instance
export const api = new ApiClient();
