import React, { useState } from 'react';
import { useTickets } from '../hooks/useTickets';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { TicketCard } from '../components/tickets/TicketCard';
import { CreateTicketModal } from '../components/tickets/CreateTicketModal';
import { Button } from '../components/common/Button';
import { EmptyState } from '../components/common/EmptyState';
import {
  Plus,
  Search,
  Filter,
  LifeBuoy,
} from 'lucide-react';

export const TicketsPage: React.FC = () => {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');

  const {
    tickets,
    loading,
    filters,
    setFilters,
    createTicket,
    refreshTickets,
  } = useTickets();

  // Instant real-time queue refresh when tickets are created or updated anywhere in the tenant
  useRealtimeStream({
    onTicketCreated: () => refreshTickets(),
    onTicketUpdated: () => refreshTickets(),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters({
      ...filters,
      search: searchTerm.trim() || undefined,
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
    });
  };

  const handleFilterChange = (statusVal: string, priorityVal: string) => {
    setStatusFilter(statusVal);
    setPriorityFilter(priorityVal);
    setFilters({
      ...filters,
      search: searchTerm.trim() || undefined,
      status: statusVal || undefined,
      priority: priorityVal || undefined,
    });
  };

  const safeTickets = Array.isArray(tickets) ? tickets : [];

  return (
    <div className="space-y-6">
      {/* Header and Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Support Tickets
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage incoming inquiries, assign agents, and dispatch grounded AI draft replies.
          </p>
        </div>

        <Button
          onClick={() => setIsCreateOpen(true)}
          icon={<Plus className="w-4 h-4" />}
          className="shadow-sm"
        >
          New Ticket
        </Button>
      </div>

      {/* Filter / Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center gap-3">
        <form onSubmit={handleSearch} className="flex-1 relative w-full">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search tickets by subject or customer problem..."
            className="w-full pl-9 pr-3.5 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium shrink-0">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => handleFilterChange(e.target.value, priorityFilter)}
            className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => handleFilterChange(statusFilter, e.target.value)}
            className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All Priorities</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent</option>
          </select>
        </div>
      </div>

      {/* Ticket List / Grid */}
      {loading ? (
        <div className="text-center py-16 text-slate-400 text-sm">
          Loading ticket queue...
        </div>
      ) : safeTickets.length === 0 ? (
        <EmptyState
          icon={<LifeBuoy className="w-6 h-6" />}
          title="No support tickets found"
          description="There are currently no tickets matching your active filter criteria."
          action={
            <Button size="sm" onClick={() => setIsCreateOpen(true)}>
              Create First Ticket
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {safeTickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </div>
      )}

      {/* Create Ticket Modal */}
      <CreateTicketModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSubmit={async (data) => {
          await createTicket(data);
          refreshTickets();
        }}
      />
    </div>
  );
};
