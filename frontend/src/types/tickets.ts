import { User } from './auth';

export type TicketStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
export type TicketPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export interface TicketComment {
  id: string;
  ticket: string;
  author: User;
  body: string;
  is_internal_note: boolean;
  created_at: string;
}

export interface Ticket {
  id: string;
  organization: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  created_by: User;
  assigned_to: User | null;
  comments_count?: number;
  comments?: TicketComment[];
  created_at: string;
  updated_at: string;
}

export interface CreateTicketRequest {
  title: string;
  description: string;
  priority?: TicketPriority;
  assigned_to?: string | null;
}

export interface UpdateTicketRequest {
  status?: TicketStatus;
  priority?: TicketPriority;
  assigned_to?: string | null;
}

export interface AddCommentRequest {
  body: string;
  is_internal_note?: boolean;
}
