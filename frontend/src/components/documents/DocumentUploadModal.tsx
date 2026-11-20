import React, { useState, useRef } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { UploadCloud, FileText, CheckCircle2 } from 'lucide-react';
import { getErrorMessage } from '../../utils/errors';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, title: string) => Promise<void>;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onUpload,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        const defaultTitle = selected.name.replace(/\.[^/.]+$/, '');
        setTitle(defaultTitle);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF or TXT file to ingest.');
      return;
    }
    if (!title.trim()) {
      setError('Please specify a document title.');
      return;
    }

    setIsUploading(true);
    setError(null);
    try {
      await onUpload(file, title.trim());
      setFile(null);
      setTitle('');
      onClose();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Upload failed.'));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Ingest Knowledge Base Document" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
            {error}
          </div>
        )}

        {/* Drag and drop / file selector */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className="cursor-pointer rounded-2xl border-2 border-dashed border-slate-300 p-6 text-center hover:border-brand-500 hover:bg-brand-50/20 transition-all"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.txt"
            className="hidden"
          />

          {file ? (
            <div className="flex flex-col items-center gap-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-500" />
              <div className="font-semibold text-slate-800 text-sm">{file.name}</div>
              <div className="text-xs text-slate-400">
                {(file.size / 1024).toFixed(1)} KB — Click to choose different file
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <UploadCloud className="w-10 h-10 text-slate-400" />
              <div className="font-semibold text-slate-700 text-sm">
                Click or drag & drop documentation file
              </div>
              <div className="text-xs text-slate-400">
                Supports Adobe PDF (.pdf) and Plain Text (.txt)
              </div>
            </div>
          )}
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Document Title *
          </label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Enterprise SLA & Incident Response Protocol"
            className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 text-xs text-slate-500 leading-relaxed">
          <span className="font-semibold text-slate-700 block mb-0.5">
            Automated Ingestion Pipeline:
          </span>
          Text extracted page-by-page, recursively split with 100-character overlap, and indexed with 1536-dimensional vector embeddings for RAG.
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
          <Button type="button" variant="outline" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isUploading} icon={<FileText className="w-4 h-4" />}>
            Ingest & Index
          </Button>
        </div>
      </form>
    </Modal>
  );
};
