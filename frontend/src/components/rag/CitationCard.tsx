import React, { useState } from 'react';
import { AIDraftCitation } from '../../types/rag';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

interface CitationCardProps {
  citation: AIDraftCitation;
  index: number;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden text-xs">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2 font-medium text-slate-800 line-clamp-1">
          <BookOpen className="w-3.5 h-3.5 text-brand-600 shrink-0" />
          <span>
            [{index + 1}] {citation.source_title}
          </span>
          <span className="text-slate-400 font-normal">
            (Page {citation.page_number})
          </span>
        </div>

        <div className="flex items-center gap-2 text-slate-400 shrink-0">
          <span className="text-[11px] font-semibold text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded border border-brand-200">
            {Math.round(citation.relevance_score * 100)}% Match
          </span>
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 py-2.5 bg-slate-50 border-t border-slate-100 text-slate-600 text-xs italic leading-relaxed">
          &ldquo;{citation.cited_excerpt}&rdquo;
        </div>
      )}
    </div>
  );
};
