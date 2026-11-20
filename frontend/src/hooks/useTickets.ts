import { useState, useEffect, useCallback } from 'react';
import { ticketService, TicketFilterParams } from '../services/ticketService';
import { CreateTicketRequest, Ticket, UpdateTicketRequest } from '../types/tickets';

export const useTickets = (initialFilters?: TicketFilterParams) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TicketFilterParams>(initialFilters || {});

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ticketService.listTickets(filters);
      setTickets(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tickets');
      setTickets([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const createTicket = async (data: CreateTicketRequest) => {
    const newTicket = await ticketService.createTicket(data);
    setTickets((prev) => [newTicket, ...prev]);
    return newTicket;
  };

  const updateTicket = async (id: string, data: UpdateTicketRequest) => {
    const updated = await ticketService.updateTicket(id, data);
    setTickets((prev) => prev.map((t) => (t.id === id ? { ...t, ...updated } : t)));
    return updated;
  };

  return {
    tickets,
    loading,
    error,
    filters,
    setFilters,
    refreshTickets: fetchTickets,
    createTicket,
    updateTicket,
  };
};
