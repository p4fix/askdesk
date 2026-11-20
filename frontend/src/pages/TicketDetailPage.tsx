import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ticketService } from '../services/ticketService';
import { authService } from '../services/authService';
import { Ticket, TicketStatus, TicketPriority } from '../types/tickets';
import { User } from '../types/auth';
import { StatusBadge, PriorityBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { TicketTimeline } from '../components/tickets/TicketTimeline';
import { AIDraftPanel } from '../components/rag/AIDraftPanel';
import {
  ArrowLeft,
  Calendar,
  User as UserIcon,
  Shield,
  Loader2,
} from 'lucide-react';

export const TicketDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [agents, setAgents] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchTicketData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [ticketData, agentsData] = await Promise.all([
        ticketService.getTicket(id),
        authService.listAgents().catch(() => []),
      ]);
      setTicket(ticketData);
      setAgents(Array.isArray(agentsData) ? agentsData : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load ticket.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTicketData();
  }, [fetchTicketData]);

  const handleStatusChange = async (newStatus: TicketStatus) => {
    if (!ticket) return;
    setIsUpdating(true);
    try {
      const updated = await ticketService.updateTicket(ticket.id, { status: newStatus });
      setTicket((prev: Ticket | null) => (prev ? { ...prev, status: updated.status } : null));
    } finally {
      setIsUpdating(false);
    }
  };

  const handlePriorityChange = async (newPriority: TicketPriority) => {
    if (!ticket) return;
    setIsUpdating(true);
    try {
      const updated = await ticketService.updateTicket(ticket.id, { priority: newPriority });
      setTicket((prev: Ticket | null) => (prev ? { ...prev, priority: updated.priority } : null));
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAssigneeChange = async (agentId: string) => {
    if (!ticket) return;
    setIsUpdating(true);
    try {
      const updated = await ticketService.updateTicket(ticket.id, {
        assigned_to: agentId || null,
      });
      setTicket((prev: Ticket | null) => (prev ? { ...prev, assigned_to: updated.assigned_to } : null));
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddComment = async (body: string, isInternal: boolean) => {
    if (!ticket) return;
    const newComment = await ticketService.addComment(ticket.id, {
      body,
      is_internal_note: isInternal,
    });
    setTicket((prev: Ticket | null) =>
      prev
        ? {
            ...prev,
            comments: [...(prev.comments || []), newComment],
            comments_count: (prev.comments_count || 0) + 1,
            status: prev.status === 'OPEN' ? 'IN_PROGRESS' : prev.status,
          }
        : null
    );
  };

  if (loading) {
    return (
      <div className="py-20 text-center flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
        <span className="text-sm font-medium text-slate-500">
          Loading ticket and RAG engine context...
        </span>
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="py-12 text-center max-w-md mx-auto">
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm mb-4">
          {error || 'Ticket not found or inaccessible.'}
        </div>
        <Button variant="outline" onClick={() => navigate('/tickets')}>
          Return to Ticket Queue
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation & Status Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/tickets')}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back
          </Button>
          <div className="h-4 w-px bg-slate-300" />
          <h1 className="text-xl font-bold text-slate-900 tracking-tight line-clamp-1">
            {ticket.title}
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Status selector */}
          <select
            value={ticket.status}
            disabled={isUpdating}
            onChange={(e) => handleStatusChange(e.target.value as TicketStatus)}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>

          {/* Priority selector */}
          <select
            value={ticket.priority}
            disabled={isUpdating}
            onChange={(e) => handlePriorityChange(e.target.value as TicketPriority)}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="LOW">Low Priority</option>
            <option value="MEDIUM">Medium Priority</option>
            <option value="HIGH">High Priority</option>
            <option value="URGENT">Urgent Priority</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Left = Conversation Timeline; Right = RAG Suggestion & Metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Timeline & Replies */}
        <div className="lg:col-span-7 h-[780px]">
          <TicketTimeline
            ticketDescription={ticket.description}
            customerEmail={ticket.created_by.email}
            createdAt={ticket.created_at}
            comments={ticket.comments || []}
            onAddComment={handleAddComment}
          />
        </div>

        {/* Right Column: AI RAG Suggestion Panel & Assignee Controls */}
        <div className="lg:col-span-5 space-y-6">
          {/* AI Grounded Draft Panel */}
          <div className="h-[520px]">
            <AIDraftPanel
              ticketId={ticket.id}
              ticketStatus={ticket.status}
              onDraftAccepted={fetchTicketData}
            />
          </div>

          {/* Ticket Metadata Card */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4 text-xs">
            <h4 className="font-bold text-slate-900 text-sm pb-2 border-b border-slate-100 flex items-center gap-2">
              <Shield className="w-4 h-4 text-brand-600" />
              <span>Ticket Routing & Metadata</span>
            </h4>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-slate-400 block mb-1">Status</span>
                <StatusBadge status={ticket.status} />
              </div>

              <div>
                <span className="text-slate-400 block mb-1">Priority</span>
                <PriorityBadge priority={ticket.priority} />
              </div>
            </div>

            <div>
              <span className="text-slate-400 block mb-1">Assigned Support Agent</span>
              <select
                value={ticket.assigned_to?.id || ''}
                disabled={isUpdating}
                onChange={(e) => handleAssigneeChange(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">Unassigned</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.first_name} {agent.last_name} ({agent.email})
                  </option>
                ))}
              </select>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-slate-500">
              <div className="flex items-center gap-1.5">
                <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                <span>
                  Submitted by {ticket.created_by.first_name} {ticket.created_by.last_name}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
