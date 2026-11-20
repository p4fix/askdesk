import apiClient from './api';
import {
  AddCommentRequest,
  CreateTicketRequest,
  Ticket,
  TicketComment,
  UpdateTicketRequest,
} from '../types/tickets';

export interface TicketFilterParams {
  status?: string;
  priority?: string;
  assigned_to?: string;
  search?: string;
}

export const ticketService = {
  async listTickets(params?: TicketFilterParams): Promise<Ticket[]> {
    const response = await apiClient.get<Ticket[] | { results: Ticket[] }>('/tickets/', { params });
    const data = response.data;
    if (Array.isArray(data)) {
      return data;
    }
    if (data && typeof data === 'object' && Array.isArray((data as { results: Ticket[] }).results)) {
      return (data as { results: Ticket[] }).results;
    }
    return [];
  },

  async getTicket(id: string): Promise<Ticket> {
    const response = await apiClient.get<Ticket>(`/tickets/${id}/`);
    return response.data;
  },

  async createTicket(data: CreateTicketRequest): Promise<Ticket> {
    const response = await apiClient.post<Ticket>('/tickets/', data);
    return response.data;
  },

  async updateTicket(id: string, data: UpdateTicketRequest): Promise<Ticket> {
    const response = await apiClient.patch<Ticket>(`/tickets/${id}/`, data);
    return response.data;
  },

  async listComments(ticketId: string): Promise<TicketComment[]> {
    const response = await apiClient.get<TicketComment[]>(`/tickets/${ticketId}/comments/`);
    return response.data;
  },

  async addComment(ticketId: string, data: AddCommentRequest): Promise<TicketComment> {
    const response = await apiClient.post<TicketComment>(`/tickets/${ticketId}/comments/`, data);
    return response.data;
  },
};
