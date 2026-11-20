import React from 'react';

type BadgeVariant =
  | 'default'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'purple';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  className = '',
}) => {
  const styles: Record<BadgeVariant, string> = {
    default: 'bg-slate-100 text-slate-700 border-slate-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    danger: 'bg-rose-50 text-rose-700 border-rose-200',
    info: 'bg-sky-50 text-sky-700 border-sky-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[variant]} ${className}`}
    >
      {children}
    </span>
  );
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  switch (status) {
    case 'OPEN':
      return <Badge variant="info">Open</Badge>;
    case 'IN_PROGRESS':
      return <Badge variant="warning">In Progress</Badge>;
    case 'RESOLVED':
      return <Badge variant="success">Resolved</Badge>;
    case 'CLOSED':
      return <Badge variant="default">Closed</Badge>;
    case 'PROCESSED':
      return <Badge variant="success">Processed</Badge>;
    case 'PENDING':
      return <Badge variant="warning">Pending</Badge>;
    case 'FAILED':
      return <Badge variant="danger">Failed</Badge>;
    case 'DRAFT_GENERATED':
      return <Badge variant="purple">AI Draft Ready</Badge>;
    case 'ACCEPTED':
      return <Badge variant="success">Accepted</Badge>;
    case 'REJECTED':
      return <Badge variant="danger">Rejected</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
};

export const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  switch (priority) {
    case 'LOW':
      return <Badge variant="default">Low</Badge>;
    case 'MEDIUM':
      return <Badge variant="info">Medium</Badge>;
    case 'HIGH':
      return <Badge variant="warning">High</Badge>;
    case 'URGENT':
      return <Badge variant="danger">Urgent</Badge>;
    default:
      return <Badge>{priority}</Badge>;
  }
};
