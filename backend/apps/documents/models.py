import os
import uuid
from django.db import models
from django.db.backends.ddl_references import Statement
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from pgvector.django import HnswIndex, VectorField

from apps.authentication.models import Organization, User

def document_upload_path(instance, filename):
    """Stores uploaded document files under media/documents/<org_id>/<uuid>_<filename>."""
    ext = os.path.splitext(filename)[1].lower()
    safe_filename = f"{uuid.uuid4().hex[:12]}_{slugify(os.path.splitext(filename)[0])}{ext}"
    return os.path.join('documents', str(instance.organization_id), safe_filename)


class SafeHnswIndex(HnswIndex):
    """
    Subclasses pgvector's HnswIndex to guarantee dual-database compatibility.
    On PostgreSQL with pgvector, it generates the full HNSW vector cosine index DDL.
    On non-PostgreSQL engines (such as local SQLite test environments), it emits a safe no-op.
    """
    def create_sql(self, model, schema_editor, using='', **kwargs):
        if schema_editor.connection.vendor != 'postgresql':
            return Statement('-- noop non-postgres hnsw index')
        return super().create_sql(model, schema_editor, using=using, **kwargs)

    def remove_sql(self, model, schema_editor, **kwargs):
        if schema_editor.connection.vendor != 'postgresql':
            return Statement('-- noop non-postgres hnsw index')
        return super().remove_sql(model, schema_editor, **kwargs)


class DocumentStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending Processing')
    PROCESSED = 'PROCESSED', _('Processed & Indexed')
    FAILED = 'FAILED', _('Ingestion Failed')


class DocumentFileType(models.TextChoices):
    PDF = 'PDF', _('Portable Document Format (.pdf)')
    TXT = 'TXT', _('Plain Text (.txt)')


class Document(models.Model):
    """
    Uploaded company documentation source (PDF or TXT) belonging to an organization.
    Acts as the parent entity for chunked vector embeddings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='documents',
        db_index=True,
        help_text="Tenant organization that owns this document."
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_documents',
        help_text="Administrator who uploaded this document."
    )
    title = models.CharField(max_length=255, help_text="Human-readable title or document name.")
    file = models.FileField(upload_to=document_upload_path, help_text="Original uploaded document file.")
    file_type = models.CharField(max_length=10, choices=DocumentFileType.choices, db_index=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        db_index=True
    )
    error_message = models.TextField(null=True, blank=True, help_text="Error trace if ingestion failed.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']

    def delete(self, *args, **kwargs):
        # Clean up stored media file from disk upon document deletion
        if self.file and os.path.isfile(self.file.path):
            try:
                os.remove(self.file.path)
            except OSError:
                pass
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.title} [{self.file_type}] ({self.status})"


class DocumentChunk(models.Model):
    """
    Text segment extracted from a document with associated 1536-dimensional vector embedding.
    Indexed via HNSW cosine distance for sub-millisecond similarity queries.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks',
        db_index=True
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='document_chunks',
        db_index=True,
        help_text="Tenant organization scoping for multi-tenant similarity search."
    )
    chunk_index = models.PositiveIntegerField(help_text="Sequential position within the source document.")
    content = models.TextField(help_text="The extracted text chunk content.")
    token_count = models.PositiveIntegerField(default=0, help_text="Approximate token or word count.")
    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        help_text="1536-dimensional vector embedding generated from text content."
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Source metadata: page number, character offsets, section headers."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_chunks'
        ordering = ['chunk_index']
        indexes = [
            SafeHnswIndex(
                name='doc_chunk_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        return f"Chunk #{self.chunk_index} of {self.document.title} ({self.token_count} tokens)"

