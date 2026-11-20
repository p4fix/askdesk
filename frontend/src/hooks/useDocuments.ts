import { useState, useEffect, useCallback } from 'react';
import { documentService } from '../services/documentService';
import { Document } from '../types/documents';

export const useDocuments = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await documentService.listDocuments();
      setDocuments(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch knowledge base documents');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const uploadDocument = async (file: File, title: string) => {
    setIsUploading(true);
    setError(null);
    try {
      const newDoc = await documentService.uploadDocument(file, title);
      setDocuments((prev) => [newDoc, ...prev]);
      return newDoc;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to upload document';
      setError(msg);
      throw err;
    } finally {
      setIsUploading(false);
    }
  };

  const deleteDocument = async (id: string) => {
    try {
      await documentService.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete document';
      setError(msg);
      throw err;
    }
  };

  return {
    documents,
    loading,
    isUploading,
    error,
    refreshDocuments: fetchDocuments,
    uploadDocument,
    deleteDocument,
  };
};
