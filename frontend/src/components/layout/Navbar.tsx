import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Building2, LogOut, User as UserIcon } from 'lucide-react';
import { Badge } from '../common/Badge';

export const Navbar: React.FC = () => {
  const { user, organization, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-slate-200 bg-white/80 px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white font-bold shadow-md shadow-brand-500/20">
          AD
        </div>
        <div>
          <span className="font-bold text-slate-900 tracking-tight text-lg">
            AskDesk
          </span>
          <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded bg-brand-50 text-brand-700 border border-brand-200">
            AI-RAG
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {organization && (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold text-slate-900">{organization.name}</span>
          </div>
        )}

        {user && (
          <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 border border-slate-200 text-slate-600">
                <UserIcon className="w-4 h-4" />
              </div>
              <div className="hidden md:block text-left">
                <div className="text-xs font-medium text-slate-900">
                  {user.first_name} {user.last_name}
                </div>
                <div className="text-[11px] text-slate-500">{user.email}</div>
              </div>
            </div>

            <Badge variant={user.role === 'ADMIN' ? 'purple' : 'info'}>
              {user.role === 'ADMIN' ? 'Admin' : 'Agent'}
            </Badge>

            <button
              onClick={logout}
              title="Sign Out"
              className="text-slate-400 hover:text-rose-600 rounded-lg p-1.5 hover:bg-slate-100 transition-colors ml-1"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
