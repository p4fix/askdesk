import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  LifeBuoy,
  FileText,
  Users,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { isAdmin } = useAuth();

  const links = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/tickets', label: 'Tickets', icon: LifeBuoy },
    { to: '/documents', label: 'Knowledge Base', icon: FileText },
  ];

  return (
    <aside className="w-64 border-r border-slate-200 bg-white flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          Helpdesk Workspace
        </div>
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{link.label}</span>
            </NavLink>
          );
        })}
      </div>

      {isAdmin && (
        <div className="p-4 space-y-1 mt-4 pt-4 border-t border-slate-100">
          <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Administration
          </div>
          <NavLink
            to="/team"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-50 text-brand-700 font-semibold'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`
            }
          >
            <Users className="w-4 h-4 shrink-0" />
            <span>Agent Directory</span>
          </NavLink>
        </div>
      )}

      <div className="mt-auto p-4 border-t border-slate-100">
        <div className="rounded-xl bg-slate-50 p-3 border border-slate-200/60 text-xs text-slate-500">
          <span className="font-semibold text-slate-700 block mb-1">
            RAG Bounded Grounding
          </span>
          Strict row-level tenancy with pgvector cosine similarity search.
        </div>
      </div>
    </aside>
  );
};
