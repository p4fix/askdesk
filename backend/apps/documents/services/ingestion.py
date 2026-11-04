import os
from typing import Any, Dict, List
from django.db import transaction
from pypdf import PdfReader

from apps.documents.models import Document, DocumentChunk, DocumentFileType, DocumentStatus
from .chunking import RecursiveCharacterTextSplitter
from .embedding import BaseEmbeddingService, get_embedding_service

class DocumentIngestionService:
    """
    Orchestrates end-to-end document text extraction, recursive chunking,
    vector embedding generation, and atomic persistence into pgvector.
    """

    def __init__(
        self,
        embedding_service: BaseEmbeddingService = None,
        splitter: RecursiveCharacterTextSplitter = None
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.splitter = splitter or RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

    def extract_text_pages(self, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """Extracts text structured with page numbers from PDF or TXT files."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Source file not found at path: {file_path}")

        pages: List[Dict[str, Any]] = []

        if file_type == DocumentFileType.TXT:
            with open(file_path, 'rb') as f:
                raw_bytes = f.read()

            # Robust multi-encoding decode attempt
            text = ""
            for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
                try:
                    text = raw_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            cleaned_text = text.strip()
            if cleaned_text:
                pages.append({'page': 1, 'text': cleaned_text})

        elif file_type == DocumentFileType.PDF:
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                cleaned = page_text.strip()
                if cleaned:
                    pages.append({'page': idx + 1, 'text': cleaned})

        return pages

    def ingest(self, document: Document) -> List[DocumentChunk]:
        """
        Executes the ingestion pipeline on a Document instance.
        Updates document status to PROCESSED upon success, or FAILED on error.
        """
        file_path = document.file.path

        try:
            # 1. Update file size if not recorded
            if not document.file_size_bytes and os.path.isfile(file_path):
                document.file_size_bytes = os.path.getsize(file_path)

            # 2. Extract text per page
            pages = self.extract_text_pages(file_path, document.file_type)
            if not pages:
                raise ValueError("No readable text could be extracted from the uploaded file.")

            # 3. Recursively split into semantic chunks with sliding overlap
            chunk_dicts = self.splitter.split_document_pages(pages)
            if not chunk_dicts:
                raise ValueError("Extracted text did not produce any valid chunks.")

            # 4. Generate 1536-dimensional vector embeddings
            texts_to_embed = [item['content'] for item in chunk_dicts]
            vectors = self.embedding_service.generate_embeddings_batch(texts_to_embed)

            # 5. Persist chunks atomically
            with transaction.atomic():
                # Clean up previous chunks if re-processing
                document.chunks.all().delete()

                chunk_objects = [
                    DocumentChunk(
                        document=document,
                        organization=document.organization,
                        chunk_index=chunk_meta['chunk_index'],
                        content=chunk_meta['content'],
                        token_count=chunk_meta['token_count'],
                        embedding=vector,
                        metadata=chunk_meta['metadata'],
                    )
                    for chunk_meta, vector in zip(chunk_dicts, vectors)
                ]
                created_chunks = DocumentChunk.objects.bulk_create(chunk_objects)

                document.status = DocumentStatus.PROCESSED
                document.error_message = None
                document.save(update_fields=['status', 'error_message', 'file_size_bytes', 'updated_at'])

            return created_chunks

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.save(update_fields=['status', 'error_message', 'updated_at'])
            raise

