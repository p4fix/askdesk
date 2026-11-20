import React, { useState } from 'react';
import { useDocuments } from '../hooks/useDocuments';
import { useAuth } from '../context/AuthContext';
import { DocumentCard } from '../components/documents/DocumentCard';
import { DocumentUploadModal } from '../components/documents/DocumentUploadModal';
import { Button } from '../components/common/Button';
import { EmptyState } from '../components/common/EmptyState';
import {
  Upload,
  BookOpen,
  Database,
  Search,
} from 'lucide-react';
import { ragService } from '../services/ragService';
import { SemanticSearchResult } from '../types/rag';

export const DocumentsPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const {
    documents,
    loading,
    uploadDocument,
    deleteDocument,
    refreshDocuments,
  } = useDocuments();

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SemanticSearchResult[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    setIsSearching(true);
    try {
      const results = await ragService.semanticSearch(searchQuery.trim(), 3);
      setSearchResults(results);
    } finally {
      setIsSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  const totalChunks = documents.reduce((acc, d) => acc + (d.chunks_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Knowledge Base & Documentation
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Company SOPs, refund guidelines, and manuals indexed for high-speed pgvector cosine similarity search.
          </p>
        </div>

        {isAdmin && (
          <Button
            onClick={() => setIsUploadOpen(true)}
            icon={<Upload className="w-4 h-4" />}
            className="shadow-sm"
          >
            Upload Document
          </Button>
        )}
      </div>

      {/* Vector Retrieval Audit Test Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-brand-600" />
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Semantic Vector Search Inspector
            </span>
          </div>
          <span className="text-xs text-slate-400">
            {totalChunks} indexed 1536-dim vector chunks across {documents.length} docs
          </span>
        </div>

        <form onSubmit={handleSemanticSearch} className="flex gap-3">
          <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Test similarity search query (e.g. 'How do customer refunds work for unactivated licenses?')..."
              className="w-full pl-10 pr-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <Button type="submit" size="sm" isLoading={isSearching}>
            Search Vectors
          </Button>

          {searchResults && (
            <Button type="button" variant="ghost" size="sm" onClick={clearSearch}>
              Clear
            </Button>
          )}
        </form>

        {/* Semantic Search Matches Preview */}
        {searchResults && (
          <div className="pt-3 border-t border-slate-100 space-y-2">
            <div className="text-xs font-semibold text-slate-700">
              Retrieved Chunks ({searchResults.length}):
            </div>
            {searchResults.length === 0 ? (
              <div className="text-xs text-slate-500 italic">
                No matching chunks found above similarity threshold for this query.
              </div>
            ) : (
              searchResults.map((match) => (
                <div
                  key={match.chunk_id}
                  className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between font-semibold text-slate-800">
                    <span>
                      {match.document_title} (Page {match.page_number})
                    </span>
                    <span className="text-brand-600 font-bold">
                      {Math.round(match.similarity * 100)}% Cosine Match
                    </span>
                  </div>
                  <p className="text-slate-600 italic leading-relaxed">
                    &ldquo;{match.content}&rdquo;
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Documents Grid */}
      {loading ? (
        <div className="text-center py-16 text-slate-400 text-sm">
          Loading knowledge base documents...
        </div>
      ) : documents.length === 0 ? (
        <EmptyState
          icon={<BookOpen className="w-6 h-6" />}
          title="Knowledge base is empty"
          description="Upload PDF or TXT policies and user manuals to empower your agents with AI-drafted replies."
          action={
            isAdmin ? (
              <Button size="sm" onClick={() => setIsUploadOpen(true)}>
                Upload First Document
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onDelete={deleteDocument}
              isAdmin={isAdmin}
            />
          ))}
        </div>
      )}

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUpload={async (file, title) => {
          await uploadDocument(file, title);
          refreshDocuments();
        }}
      />
    </div>
  );
};
