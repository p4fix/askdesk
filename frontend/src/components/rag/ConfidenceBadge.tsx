import React from 'react';
import { Sparkles } from 'lucide-react';

interface ConfidenceBadgeProps {
  score: number | null;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score }) => {
  if (score === null || score === undefined) return null;

  const percentage = Math.round(score * 100);

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-200';
  let label = 'Low Grounding';

  if (score >= 0.25) {
    colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    label = 'Strong Grounding';
  } else if (score >= 0.12) {
    colorClasses = 'bg-amber-50 text-amber-700 border-amber-200';
    label = 'Moderate Grounding';
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClasses}`}
    >
      <Sparkles className="w-3 h-3" />
      <span>{label} ({percentage}%)</span>
    </span>
  );
};
