import os
from rest_framework import serializers

from apps.authentication.models import User
from apps.documents.models import Document, DocumentChunk, DocumentFileType, DocumentStatus
from apps.documents.services.ingestion import DocumentIngestionService

class DocumentUserSummarySerializer(serializers.ModelSerializer):
    """Minimal representation of the uploading user."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role']
        read_only_fields = fields


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serialized document chunk snippet (omits large raw float vectors from HTTP responses)."""

    class Meta:
        model = DocumentChunk
        fields = [
            'id',
            'chunk_index',
            'content',
            'token_count',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight document representation for knowledge base tables and search listings."""
    uploaded_by = DocumentUserSummarySerializer(read_only=True)
    chunks_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'file_type',
            'file_size_bytes',
            'status',
            'chunks_count',
            'uploaded_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Full document representation including chunk counts and extracted snippet previews."""
    uploaded_by = DocumentUserSummarySerializer(read_only=True)
    chunks_count = serializers.SerializerMethodField()
    chunks = DocumentChunkSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'file_type',
            'file_size_bytes',
            'status',
            'error_message',
            'chunks_count',
            'uploaded_by',
            'chunks',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_chunks_count(self, obj):
        if hasattr(obj, 'chunks_count'):
            return obj.chunks_count
        return obj.chunks.count()


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Handles multipart file uploads for company documentation (PDF or TXT).
    Validates file formats and triggers the chunking and embedding ingestion pipeline.
    """
    file = serializers.FileField(required=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)

    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB upload ceiling

    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'status', 'file_type', 'created_at']
        read_only_fields = ['id', 'status', 'file_type', 'created_at']

    def validate_file(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ('.pdf', '.txt'):
            raise serializers.ValidationError(
                f"Unsupported file format '{ext}'. Only .pdf and .txt files are supported."
            )

        if value.size > self.MAX_FILE_SIZE_BYTES:
            max_mb = self.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise serializers.ValidationError(f"File size exceeds the {max_mb}MB limit.")

        return value

    def create(self, validated_data):
        request = self.context['request']
        uploaded_file = validated_data['file']

        # Default title to file basename if omitted
        title = validated_data.get('title')
        if not title or not title.strip():
            title = os.path.splitext(uploaded_file.name)[0].replace('_', ' ').replace('-', ' ').title()

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        file_type = DocumentFileType.PDF if ext == '.pdf' else DocumentFileType.TXT

        document = Document.objects.create(
            organization=request.user.organization,
            uploaded_by=request.user,
            title=title.strip(),
            file=uploaded_file,
            file_type=file_type,
            file_size_bytes=uploaded_file.size,
            status=DocumentStatus.PENDING,
        )

        # Trigger chunking & pgvector embedding pipeline
        try:
            ingestion_service = DocumentIngestionService()
            ingestion_service.ingest(document)
        except Exception as e:
            # Document status is marked FAILED within ingestion service
            pass

        return document

