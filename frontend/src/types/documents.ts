import { User } from './auth';

export type DocumentStatus = 'PENDING' | 'PROCESSED' | 'FAILED';
export type DocumentFileType = 'PDF' | 'TXT';

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  metadata: {
    page?: number;
    section?: string;
    [key: string]: unknown;
  };
  created_at: string;
}

export interface Document {
  id: string;
  title: string;
  file: string;
  file_type: DocumentFileType;
  file_size_bytes: number;
  status: DocumentStatus;
  error_message?: string | null;
  chunks_count: number;
  uploaded_by: User;
  chunks?: DocumentChunk[];
  created_at: string;
  updated_at: string;
}
