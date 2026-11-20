import React, { useState, useEffect } from 'react';
import { authService } from '../services/authService';
import { User } from '../types/auth';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { Badge } from '../components/common/Badge';
import { Users, UserPlus, Mail, Lock, User as UserIcon, Shield } from 'lucide-react';

export const TeamPage: React.FC = () => {
  const [agents, setAgents] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const data = await authService.listAgents();
      setAgents(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await authService.createAgent({
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        password,
      });
      setEmail('');
      setFirstName('');
      setLastName('');
      setPassword('');
      setIsModalOpen(false);
      fetchAgents();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to provision agent.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Support Agent Directory
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Provision and manage support agents within your organization tenant boundary.
          </p>
        </div>

        <Button
          onClick={() => setIsModalOpen(true)}
          icon={<UserPlus className="w-4 h-4" />}
        >
          Provision Agent
        </Button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-brand-600" />
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Tenant Members ({agents.length})
            </span>
          </div>
          <span className="text-xs text-slate-400">
            Row-level multi-tenancy guarantees agents only see this organization's data.
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-slate-400">Loading agents...</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {agents.map((agent) => (
              <div key={agent.id} className="p-4 flex items-center justify-between text-sm">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 border border-slate-200 text-slate-600 font-semibold text-xs">
                    {agent.first_name[0] || 'U'}
                  </div>
                  <div>
                    <div className="font-semibold text-slate-900">
                      {agent.first_name} {agent.last_name}
                    </div>
                    <div className="text-xs text-slate-400">{agent.email}</div>
                  </div>
                </div>

                <Badge variant={agent.role === 'ADMIN' ? 'purple' : 'info'}>
                  {agent.role === 'ADMIN' ? 'Administrator' : 'Support Agent'}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Provision Agent Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Provision New Support Agent">
        <form onSubmit={handleCreateAgent} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">First Name *</label>
              <input
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Alex"
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Last Name *</label>
              <input
                type="text"
                required
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Smith"
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Agent Email *</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex@company.com"
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Initial Password *</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Temporary secure password"
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Provision Agent
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
