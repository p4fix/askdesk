import { useState, useCallback, useEffect } from 'react';
import { ragService } from '../services/ragService';
import { AIDraftResponse, ReviewDraftRequest } from '../types/rag';

export const useRAG = (ticketId: string) => {
  const [draft, setDraft] = useState<AIDraftResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isReviewing, setIsReviewing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLatestDraft = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ragService.getLatestDraft(ticketId);
      setDraft(data);
    } catch {
      // 404 is normal if no draft has been generated yet
      setDraft(null);
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    if (ticketId) {
      fetchLatestDraft();
    }
  }, [ticketId, fetchLatestDraft]);

  const generateDraft = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const newDraft = await ragService.generateDraft(ticketId);
      setDraft(newDraft);
      return newDraft;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate AI suggestion';
      setError(msg);
      throw err;
    } finally {
      setIsGenerating(false);
    }
  };

  const reviewDraft = async (data: ReviewDraftRequest) => {
    setIsReviewing(true);
    setError(null);
    try {
      const updated = await ragService.reviewDraft(ticketId, data);
      setDraft(updated);
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit draft review';
      setError(msg);
      throw err;
    } finally {
      setIsReviewing(false);
    }
  };

  return {
    draft,
    loading,
    isGenerating,
    isReviewing,
    error,
    generateDraft,
    reviewDraft,
    refreshDraft: fetchLatestDraft,
  };
};
