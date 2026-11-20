import apiClient from './api';
import { Document } from '../types/documents';

export const documentService = {
  async listDocuments(): Promise<Document[]> {
    const response = await apiClient.get<Document[]>('/documents/');
    return response.data;
  },

  async getDocument(id: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/documents/${id}/`);
    return response.data;
  },

  async uploadDocument(file: File, title: string): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);

    const response = await apiClient.post<Document>('/documents/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async deleteDocument(id: string): Promise<void> {
    await apiClient.delete(`/documents/${id}/`);
  },
};
