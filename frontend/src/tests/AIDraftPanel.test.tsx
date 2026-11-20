import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { ConfidenceBadge } from '../components/rag/ConfidenceBadge';
import { CitationCard } from '../components/rag/CitationCard';
import { AIDraftCitation } from '../types/rag';

describe('RAG Frontend Components', () => {
  it('renders ConfidenceBadge with strong grounding correctly', () => {
    render(<ConfidenceBadge score={0.35} />);
    expect(screen.getByText(/Strong Grounding/i)).toBeInTheDocument();
    expect(screen.getByText(/35%/i)).toBeInTheDocument();
  });

  it('renders ConfidenceBadge with moderate grounding', () => {
    render(<ConfidenceBadge score={0.18} />);
    expect(screen.getByText(/Moderate Grounding/i)).toBeInTheDocument();
  });

  it('renders CitationCard with source title and page number', () => {
    const mockCitation: AIDraftCitation = {
      id: 'cit-1',
      chunk_id: 'chunk-1',
      source_title: 'Refund Policy & Terms',
      page_number: 2,
      relevance_score: 0.88,
      cited_excerpt: 'Customers may request a full refund within 30 days of purchase.',
    };

    render(<CitationCard citation={mockCitation} index={0} />);
    expect(screen.getByText(/Refund Policy & Terms/i)).toBeInTheDocument();
    expect(screen.getByText(/Page 2/i)).toBeInTheDocument();
    expect(screen.getByText(/88% Match/i)).toBeInTheDocument();
  });
});
