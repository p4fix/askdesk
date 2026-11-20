import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Ticket } from '../../types/tickets';
import { PriorityBadge, StatusBadge } from '../common/Badge';
import { MessageSquare, Clock, User as UserIcon } from 'lucide-react';

interface TicketCardProps {
  ticket: Ticket;
}

export const TicketCard: React.FC<TicketCardProps> = ({ ticket }) => {
  const navigate = useNavigate();

  const formattedDate = new Date(ticket.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      onClick={() => navigate(`/tickets/${ticket.id}`)}
      className="group bg-white p-5 rounded-xl border border-slate-200 hover:border-brand-300 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
    >
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Clock className="w-3.5 h-3.5" />
            <span>{formattedDate}</span>
          </div>
        </div>

        <h3 className="font-semibold text-slate-900 group-hover:text-brand-600 transition-colors line-clamp-1 text-base">
          {ticket.title}
        </h3>
        <p className="mt-1.5 text-xs text-slate-500 line-clamp-2 leading-relaxed">
          {ticket.description}
        </p>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-500">
            <UserIcon className="w-3 h-3" />
          </div>
          <span>
            {ticket.assigned_to
              ? `${ticket.assigned_to.first_name} ${ticket.assigned_to.last_name}`
              : 'Unassigned'}
          </span>
        </div>

        <div className="flex items-center gap-1 text-slate-400 font-medium">
          <MessageSquare className="w-3.5 h-3.5" />
          <span>{ticket.comments_count ?? 0}</span>
        </div>
      </div>
    </div>
  );
};
