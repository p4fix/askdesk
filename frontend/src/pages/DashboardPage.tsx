import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useTickets } from '../hooks/useTickets';
import { useDocuments } from '../hooks/useDocuments';
import { TicketCard } from '../components/tickets/TicketCard';
import {
  LifeBuoy,
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const { user, organization } = useAuth();
  const { tickets, loading: ticketsLoading } = useTickets();
  const { documents, loading: docsLoading } = useDocuments();

  const openTickets = tickets.filter((t) => t.status === 'OPEN');
  const inProgressTickets = tickets.filter((t) => t.status === 'IN_PROGRESS');
  const urgentTickets = tickets.filter(
    (t) => (t.priority === 'URGENT' || t.priority === 'HIGH') && t.status !== 'CLOSED' && t.status !== 'RESOLVED'
  );
  const resolvedCount = tickets.filter((t) => t.status === 'RESOLVED' || t.status === 'CLOSED').length;

  return (
    <div className="space-y-8">
      {/* Welcome banner */}
      <div className="rounded-2xl bg-gradient-to-r from-brand-700 via-brand-600 to-indigo-700 p-8 text-white shadow-xl shadow-brand-900/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-white/20 text-white backdrop-blur-sm uppercase tracking-wider">
            {organization?.name || 'Enterprise'} Tenant
          </span>
          <h1 className="text-2xl md:text-3xl font-bold mt-2 tracking-tight">
            Welcome back, {user?.first_name}!
          </h1>
          <p className="text-brand-100 text-sm mt-1 max-w-xl">
            AskDesk RAG Helpdesk is actively monitoring incoming support queues with factual vector grounding.
          </p>
        </div>

        <Link
          to="/tickets"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white text-brand-700 font-semibold text-sm hover:bg-brand-50 transition-colors shadow-md"
        >
          <span>View Ticket Queue</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sky-50 text-sky-600 border border-sky-200">
            <LifeBuoy className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{openTickets.length}</div>
            <div className="text-xs font-medium text-slate-500">Open Tickets</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-50 text-amber-600 border border-amber-200">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{inProgressTickets.length}</div>
            <div className="text-xs font-medium text-slate-500">In Progress</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-rose-50 text-rose-600 border border-rose-200">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{urgentTickets.length}</div>
            <div className="text-xs font-medium text-slate-500">High / Urgent Priority</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200">
            <CheckCircle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{resolvedCount}</div>
            <div className="text-xs font-medium text-slate-500">Resolved / Closed</div>
          </div>
        </div>
      </div>

      {/* Two-column layout: Recent Tickets and Knowledge Base Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">Recent Customer Inquiries</h2>
            <Link
              to="/tickets"
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 hover:underline"
            >
              See all ({tickets.length})
            </Link>
          </div>

          {ticketsLoading ? (
            <div className="text-center py-10 text-slate-400 text-sm">
              Loading recent tickets...
            </div>
          ) : tickets.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 text-slate-500 text-sm">
              No tickets submitted yet. Create your first support ticket to test the workflow.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {tickets.slice(0, 4).map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} />
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">Knowledge Base</h2>
            <Link
              to="/documents"
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 hover:underline"
            >
              Manage docs
            </Link>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <div className="text-sm font-bold text-slate-900">
                  {docsLoading ? '...' : documents.length} Indexed Document{documents.length !== 1 ? 's' : ''}
                </div>
                <div className="text-xs text-slate-500">
                  Total Chunks:{' '}
                  {documents.reduce((acc, d) => acc + (d.chunks_count || 0), 0)}
                </div>
              </div>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              When support tickets are opened, the RAG retrieval engine performs cosine similarity searches over your active document chunks and drafts factually grounded responses.
            </p>

            <Link
              to="/documents"
              className="w-full inline-flex items-center justify-center px-4 py-2 text-xs font-semibold text-brand-700 bg-brand-50 rounded-xl hover:bg-brand-100 transition-colors"
            >
              Upload New Knowledge Base File
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
