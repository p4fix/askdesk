from django.db.models import Count
from rest_framework import filters, generics, parsers, status
from rest_framework.response import Response

from apps.authentication.permissions import IsOrgAdmin, IsOrgMember
from apps.documents.models import Document
from apps.documents.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentUploadSerializer,
)

class DocumentListCreateView(generics.ListCreateAPIView):
    """
    List company knowledge base documents or upload a new documentation file (PDF / TXT).
    - GET: Accessible to all authenticated organization agents and admins.
    - POST: Admin-only endpoint. Triggers automated text extraction, chunking, and embedding.
    """
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title']
    ordering_fields = ['created_at', 'title', 'file_size_bytes', 'status']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsOrgAdmin()]
        return [IsOrgMember()]

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Document.objects.filter(organization=user.organization)
            .select_related('uploaded_by')
            .annotate(chunks_count=Count('chunks'))
        )

        doc_status = self.request.query_params.get('status')
        if doc_status:
            queryset = queryset.filter(status=doc_status.upper())

        file_type = self.request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type.upper())

        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DocumentUploadSerializer
        return DocumentListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        # Re-query with annotated chunk counts and prefetched chunks for rich response
        refreshed = (
            Document.objects.filter(id=document.id)
            .select_related('uploaded_by')
            .prefetch_related('chunks')
            .annotate(chunks_count=Count('chunks'))
            .first()
        )
        return Response(DocumentDetailSerializer(refreshed).data, status=status.HTTP_201_CREATED)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    """
    Retrieve document details with chunk snippet statistics,
    or delete a document and cascade removal of all its pgvector vector embeddings.
    - GET: Accessible to all organization members.
    - DELETE: Admin-only action.
    """
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsOrgAdmin()]
        return [IsOrgMember()]

    def get_queryset(self):
        return (
            Document.objects.filter(organization=self.request.user.organization)
            .select_related('uploaded_by')
            .prefetch_related('chunks')
            .annotate(chunks_count=Count('chunks'))
        )

    def get_serializer_class(self):
        return DocumentDetailSerializer

