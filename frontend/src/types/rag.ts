export type AIDraftStatus = 'DRAFT_GENERATED' | 'REVIEWED' | 'ACCEPTED' | 'REJECTED';

export interface AIDraftCitation {
  id: string;
  chunk_id: string | null;
  source_title: string;
  page_number: number;
  relevance_score: number;
  cited_excerpt: string;
}

export interface AIDraftResponse {
  id: string;
  ticket_id: string;
  organization_id: string;
  suggested_reply: string;
  model_name: string;
  confidence_score: number | null;
  status: AIDraftStatus;
  final_edited_reply: string | null;
  reviewed_by_email: string | null;
  citations: AIDraftCitation[];
  created_at: string;
  reviewed_at: string | null;
}

export interface ReviewDraftRequest {
  action: 'ACCEPT' | 'REJECT';
  edited_reply?: string;
  is_internal_note?: boolean;
}

export interface SemanticSearchResult {
  chunk_id: string;
  document_title: string;
  page_number: number;
  similarity: number;
  content: string;
}
