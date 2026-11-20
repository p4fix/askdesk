import React, { useState } from 'react';
import { TicketComment } from '../../types/tickets';
import { Button } from '../common/Button';
import { MessageSquare, ShieldAlert, Send, Lock } from 'lucide-react';

interface TicketTimelineProps {
  ticketDescription: string;
  customerEmail: string;
  createdAt: string;
  comments: TicketComment[];
  onAddComment: (body: string, isInternal: boolean) => Promise<void>;
}

export const TicketTimeline: React.FC<TicketTimelineProps> = ({
  ticketDescription,
  customerEmail,
  createdAt,
  comments,
  onAddComment,
}) => {
  const [commentBody, setCommentBody] = useState('');
  const [isInternalNote, setIsInternalNote] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentBody.trim()) return;

    setIsSubmitting(true);
    try {
      await onAddComment(commentBody.trim(), isInternalNote);
      setCommentBody('');
      setIsInternalNote(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-brand-600" />
          <span>Conversation History & Activity</span>
        </h4>
        <span className="text-xs text-slate-500">
          {comments.length + 1} message{comments.length !== 0 ? 's' : ''}
        </span>
      </div>

      <div className="flex-1 p-6 overflow-y-auto space-y-6">
        {/* Original Inquiry */}
        <div className="flex gap-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-800 text-white text-xs font-bold shadow-sm">
            C
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold text-slate-900">
                Customer ({customerEmail})
              </span>
              <span className="text-[11px] text-slate-400">
                {new Date(createdAt).toLocaleString()}
              </span>
            </div>
            <div className="rounded-2xl rounded-tl-none bg-slate-50 p-4 border border-slate-200/80 text-sm text-slate-800 whitespace-pre-wrap leading-relaxed shadow-sm">
              {ticketDescription}
            </div>
          </div>
        </div>

        {/* Threaded Comments */}
        {comments.map((comment) => (
          <div key={comment.id} className="flex gap-4">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold shadow-sm ${
                comment.is_internal_note
                  ? 'bg-amber-600 text-white ring-4 ring-amber-50'
                  : 'bg-brand-600 text-white ring-4 ring-brand-50'
              }`}
            >
              {comment.author.first_name[0] || 'A'}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-slate-900">
                  {comment.author.first_name} {comment.author.last_name}
                </span>
                {comment.is_internal_note && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">
                    <Lock className="w-3 h-3" />
                    Internal Staff Note
                  </span>
                )}
                <span className="text-[11px] text-slate-400">
                  {new Date(comment.created_at).toLocaleString()}
                </span>
              </div>
              <div
                className={`rounded-2xl rounded-tl-none p-4 text-sm whitespace-pre-wrap leading-relaxed shadow-sm border ${
                  comment.is_internal_note
                    ? 'bg-amber-50/70 text-amber-950 border-amber-200'
                    : 'bg-white text-slate-800 border-slate-200'
                }`}
              >
                {comment.body}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Reply Box */}
      <div className="p-4 border-t border-slate-200 bg-slate-50/50">
        <form onSubmit={handleSubmit} className="space-y-3">
          <textarea
            rows={3}
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
            placeholder={
              isInternalNote
                ? 'Write a private internal note (visible only to agents & admins)...'
                : 'Write a public customer reply...'
            }
            className={`w-full px-3.5 py-2.5 text-sm rounded-xl border focus:outline-none focus:ring-2 transition-all resize-y ${
              isInternalNote
                ? 'bg-amber-50/50 border-amber-300 focus:ring-amber-500 text-amber-950'
                : 'bg-white border-slate-300 focus:ring-brand-500 text-slate-900'
            }`}
          />

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-medium text-slate-600">
              <input
                type="checkbox"
                checked={isInternalNote}
                onChange={(e) => setIsInternalNote(e.target.checked)}
                className="rounded border-slate-300 text-amber-600 focus:ring-amber-500"
              />
              <span className="flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                Post as Internal Staff Note
              </span>
            </label>

            <Button
              type="submit"
              variant={isInternalNote ? 'secondary' : 'primary'}
              size="sm"
              isLoading={isSubmitting}
              icon={<Send className="w-3.5 h-3.5" />}
            >
              {isInternalNote ? 'Post Internal Note' : 'Send Public Reply'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
