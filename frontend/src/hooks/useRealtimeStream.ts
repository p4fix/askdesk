import { useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

export interface SSEEventData<T = unknown> {
  type: string;
  data: T;
}

export interface TicketCreatedEvent {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  created_by: string;
  created_at: string;
}

export interface TicketUpdatedEvent {
  id: string;
  title?: string;
  status?: string;
  priority?: string;
  assigned_to?: string | null;
  updated_at: string;
}

export interface CommentAddedEvent {
  id: string;
  ticket_id: string;
  author: string;
  author_name: string;
  body: string;
  is_internal_note: boolean;
  created_at: string;
}

export interface DraftReviewedEvent {
  draft_id: string;
  ticket_id: string;
  action: 'ACCEPT' | 'REJECT';
  reviewed_by: string;
}

interface UseRealtimeStreamOptions {
  onTicketCreated?: (data: TicketCreatedEvent) => void;
  onTicketUpdated?: (data: TicketUpdatedEvent) => void;
  onCommentAdded?: (data: CommentAddedEvent) => void;
  onDraftReviewed?: (data: DraftReviewedEvent) => void;
  enabled?: boolean;
}

export const useRealtimeStream = ({
  onTicketCreated,
  onTicketUpdated,
  onCommentAdded,
  onDraftReviewed,
  enabled = true,
}: UseRealtimeStreamOptions = {}) => {
  const { isAuthenticated } = useAuth();
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !isAuthenticated) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    const token = localStorage.getItem('askdesk_access_token');
    if (!token) return;

    const streamUrl = `/api/v1/tickets/stream/?token=${encodeURIComponent(token)}`;
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('ticket.created', (event: MessageEvent) => {
      try {
        const payload: TicketCreatedEvent = JSON.parse(event.data);
        onTicketCreated?.(payload);
      } catch (err) {
        console.error('Failed to parse ticket.created SSE message', err);
      }
    });

    eventSource.addEventListener('ticket.updated', (event: MessageEvent) => {
      try {
        const payload: TicketUpdatedEvent = JSON.parse(event.data);
        onTicketUpdated?.(payload);
      } catch (err) {
        console.error('Failed to parse ticket.updated SSE message', err);
      }
    });

    eventSource.addEventListener('comment.added', (event: MessageEvent) => {
      try {
        const payload: CommentAddedEvent = JSON.parse(event.data);
        onCommentAdded?.(payload);
      } catch (err) {
        console.error('Failed to parse comment.added SSE message', err);
      }
    });

    eventSource.addEventListener('rag.draft_reviewed', (event: MessageEvent) => {
      try {
        const payload: DraftReviewedEvent = JSON.parse(event.data);
        onDraftReviewed?.(payload);
      } catch (err) {
        console.error('Failed to parse rag.draft_reviewed SSE message', err);
      }
    });

    eventSource.onerror = (err) => {
      // EventSource automatically retries connection upon disconnection
      console.debug('AskDesk SSE stream disconnected or retrying...', err);
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [enabled, isAuthenticated, onTicketCreated, onTicketUpdated, onCommentAdded, onDraftReviewed]);

  return {
    isConnected: !!eventSourceRef.current,
  };
};
