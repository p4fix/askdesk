import React, { useState, useEffect } from 'react';
import { useRAG } from '../../hooks/useRAG';
import { Button } from '../common/Button';
import { ConfidenceBadge } from './ConfidenceBadge';
import { CitationCard } from './CitationCard';
import { StatusBadge } from '../common/Badge';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  Edit3,
  Bot,
  RotateCw,
  Lock,
} from 'lucide-react';

interface AIDraftPanelProps {
  ticketId: string;
  ticketStatus: string;
  onDraftAccepted?: () => void;
}

export const AIDraftPanel: React.FC<AIDraftPanelProps> = ({
  ticketId,
  onDraftAccepted,
}) => {
  const {
    draft,
    loading,
    isGenerating,
    isReviewing,
    error,
    generateDraft,
    reviewDraft,
  } = useRAG(ticketId);

  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState('');
  const [isInternalNote, setIsInternalNote] = useState(false);

  useEffect(() => {
    if (draft) {
      setEditedText(draft.final_edited_reply || draft.suggested_reply);
    }
  }, [draft]);

  const handleAccept = async () => {
    await reviewDraft({
      action: 'ACCEPT',
      edited_reply: isEditing ? editedText : undefined,
      is_internal_note: isInternalNote,
    });
    setIsEditing(false);
    if (onDraftAccepted) {
      onDraftAccepted();
    }
  };

  const handleReject = async () => {
    await reviewDraft({
      action: 'REJECT',
    });
    setIsEditing(false);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-brand-50/50 to-indigo-50/30">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm shadow-brand-500/20">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900">AI Suggested Reply</h4>
            <span className="text-[11px] text-slate-500">
              Human-in-the-Loop RAG Grounding
            </span>
          </div>
        </div>

        {draft && (
          <div className="flex items-center gap-2">
            <ConfidenceBadge score={draft.confidence_score} />
            <StatusBadge status={draft.status} />
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="p-5 flex-1 overflow-y-auto space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
            {error}
          </div>
        )}

        {!draft && !loading && (
          <div className="text-center py-8 px-4">
            <Sparkles className="w-10 h-10 text-brand-400 mx-auto mb-3" />
            <h5 className="text-sm font-semibold text-slate-800">
              No AI suggestion generated yet
            </h5>
            <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
              Synthesize a factually grounded answer referencing company documentation with citations.
            </p>
            <div className="mt-4">
              <Button
                size="sm"
                onClick={generateDraft}
                isLoading={isGenerating}
                icon={<Sparkles className="w-3.5 h-3.5" />}
              >
                Synthesize Grounded Draft
              </Button>
            </div>
          </div>
        )}

        {draft && (
          <>
            {/* Suggested Reply Card */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-700">
                  {isEditing ? 'Editing AI Response:' : 'AI Suggested Response:'}
                </span>
                {draft.status === 'DRAFT_GENERATED' && (
                  <button
                    type="button"
                    onClick={() => setIsEditing(!isEditing)}
                    className="text-xs text-brand-600 hover:text-brand-800 font-medium flex items-center gap-1"
                  >
                    <Edit3 className="w-3 h-3" />
                    <span>{isEditing ? 'Cancel Edits' : 'Edit Response'}</span>
                  </button>
                )}
              </div>

              {isEditing ? (
                <textarea
                  rows={8}
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full p-3.5 text-sm rounded-xl border border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500 text-slate-800 leading-relaxed font-sans"
                />
              ) : (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">
                  {draft.final_edited_reply || draft.suggested_reply}
                </div>
              )}
            </div>

            {/* Citations Section */}
            {draft.citations && draft.citations.length > 0 && (
              <div className="pt-2">
                <div className="text-xs font-semibold text-slate-700 mb-2 flex items-center justify-between">
                  <span>Structured Citations ({draft.citations.length}):</span>
                  <span className="text-[11px] text-slate-400 font-normal">
                    Click to view cited excerpts
                  </span>
                </div>
                <div className="space-y-2">
                  {draft.citations.map((citation, idx) => (
                    <CitationCard key={citation.id} citation={citation} index={idx} />
                  ))}
                </div>
              </div>
            )}

            {/* Review Controls (Only shown if still in DRAFT_GENERATED state) */}
            {draft.status === 'DRAFT_GENERATED' && (
              <div className="pt-4 border-t border-slate-100 space-y-3">
                <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-medium text-slate-600">
                  <input
                    type="checkbox"
                    checked={isInternalNote}
                    onChange={(e) => setIsInternalNote(e.target.checked)}
                    className="rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                  />
                  <span className="flex items-center gap-1">
                    <Lock className="w-3.5 h-3.5 text-amber-600" />
                    Dispatch as Internal Staff Note instead of customer reply
                  </span>
                </label>

                <div className="flex items-center gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    className="flex-1"
                    onClick={handleAccept}
                    isLoading={isReviewing}
                    icon={<CheckCircle2 className="w-4 h-4" />}
                  >
                    Accept & Dispatch
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReject}
                    isLoading={isReviewing}
                    icon={<XCircle className="w-4 h-4 text-rose-500" />}
                  >
                    Reject
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Regenerate Draft"
                    onClick={generateDraft}
                    isLoading={isGenerating}
                  >
                    <RotateCw className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}

            {draft.status !== 'DRAFT_GENERATED' && (
              <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 text-center">
                Draft was {draft.status.toLowerCase()} by{' '}
                <span className="font-semibold text-slate-700">{draft.reviewed_by_email}</span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
