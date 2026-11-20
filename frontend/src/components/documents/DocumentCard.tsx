import React, { useState } from 'react';
import { Document } from '../../types/documents';
import { StatusBadge } from '../common/Badge';
import { FileText, Trash2, Layers, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { Button } from '../common/Button';

interface DocumentCardProps {
  document: Document;
  onDelete: (id: string) => Promise<void>;
  isAdmin: boolean;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({
  document,
  onDelete,
  isAdmin,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [showChunks, setShowChunks] = useState(false);

  const formattedSize = (document.file_size_bytes / 1024).toFixed(1) + ' KB';
  const formattedDate = new Date(document.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  const handleDelete = async () => {
    if (confirm(`Are you sure you want to delete "${document.title}"? All chunk embeddings will be purged.`)) {
      setIsDeleting(true);
      try {
        await onDelete(document.id);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:border-slate-300 transition-all">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 border border-brand-200">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-slate-900 text-sm line-clamp-1">
                {document.title}
              </h4>
              <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                <span className="font-medium text-slate-700">{document.file_type}</span>
                <span>•</span>
                <span>{formattedSize}</span>
                <span>•</span>
                <span>Uploaded {formattedDate}</span>
              </div>
            </div>
          </div>

          <StatusBadge status={document.status} />
        </div>

        {document.error_message && (
          <div className="mt-3 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="line-clamp-2">{document.error_message}</span>
          </div>
        )}

        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-1.5 font-medium text-slate-700">
            <Layers className="w-4 h-4 text-brand-500" />
            <span>{document.chunks_count} Vector Chunks (HNSW Cosine)</span>
          </div>

          <div className="flex items-center gap-2">
            {document.chunks && document.chunks.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowChunks(!showChunks)}
                icon={showChunks ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              >
                {showChunks ? 'Hide Chunks' : 'View Chunks'}
              </Button>
            )}

            {isAdmin && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleDelete}
                isLoading={isDeleting}
                className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                icon={<Trash2 className="w-3.5 h-3.5" />}
              >
                Delete
              </Button>
            )}
          </div>
        </div>
      </div>

      {showChunks && document.chunks && (
        <div className="p-4 bg-slate-50 border-t border-slate-200 max-h-60 overflow-y-auto space-y-2 text-xs">
          <div className="font-semibold text-slate-700 mb-2">Extracted Vector Chunks:</div>
          {document.chunks.map((chunk) => (
            <div key={chunk.id} className="p-3 bg-white rounded-lg border border-slate-200 text-slate-700">
              <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span className="font-semibold text-slate-800">Chunk #{chunk.chunk_index}</span>
                <span>Page {chunk.metadata.page || 1} • {chunk.token_count} tokens</span>
              </div>
              <p className="line-clamp-3 italic">&ldquo;{chunk.content}&rdquo;</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
