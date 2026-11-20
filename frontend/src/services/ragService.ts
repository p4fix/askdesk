import apiClient from './api';
import {
  AIDraftResponse,
  ReviewDraftRequest,
  SemanticSearchResult,
} from '../types/rag';

export const ragService = {
  async generateDraft(ticketId: string): Promise<AIDraftResponse> {
    const response = await apiClient.post<AIDraftResponse>(`/tickets/${ticketId}/ai-draft/`);
    return response.data;
  },

  async getLatestDraft(ticketId: string): Promise<AIDraftResponse> {
    const response = await apiClient.get<AIDraftResponse>(`/tickets/${ticketId}/ai-draft/`);
    return response.data;
  },

  async reviewDraft(ticketId: string, data: ReviewDraftRequest): Promise<AIDraftResponse> {
    const response = await apiClient.post<AIDraftResponse>(
      `/tickets/${ticketId}/ai-draft/review/`,
      data
    );
    return response.data;
  },

  async semanticSearch(
    query: string,
    topK: number = 3,
    minSimilarity: number = 0.0
  ): Promise<SemanticSearchResult[]> {
    const response = await apiClient.get<SemanticSearchResult[]>('/rag/search/', {
      params: {
        query,
        top_k: topK,
        min_similarity: minSimilarity,
      },
    });
    return response.data;
  },
};
