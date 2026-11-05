from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsOrgMember
from apps.rag.models import AIDraftResponse, AIDraftStatus
from apps.rag.serializers import (
    AIDraftResponseSerializer,
    AIDraftReviewSerializer,
    SemanticSearchQuerySerializer,
    SemanticSearchResultSerializer,
)
from apps.rag.services.orchestrator import RAGOrchestrator
from apps.rag.services.retrieval import VectorSearchService
from apps.tickets.models import Ticket, TicketComment, TicketStatus

class AIDraftGenerateView(APIView):
    """
    Generate or inspect the latest AI-suggested draft for a specific ticket.
    Strict tenant boundary: User can only access tickets within their own organization.
    """
    permission_classes = [IsOrgMember]

    def get_ticket(self, ticket_id):
        return get_object_or_404(
            Ticket.objects.select_related('organization'),
            id=ticket_id,
            organization=self.request.user.organization
        )

    def post(self, request, ticket_id):
        """Triggers the RAG pipeline to generate a grounded draft with structured citations."""
        ticket = self.get_ticket(ticket_id)
        orchestrator = RAGOrchestrator()
        draft = orchestrator.generate_draft_for_ticket(ticket)
        serializer = AIDraftResponseSerializer(draft)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, ticket_id):
        """Retrieves the most recent AI draft generated for this ticket."""
        ticket = self.get_ticket(ticket_id)
        draft = ticket.ai_drafts.prefetch_related('citations', 'reviewed_by').first()
        if not draft:
            return Response(
                {"detail": "No AI draft has been generated for this ticket yet."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = AIDraftResponseSerializer(draft)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AIDraftReviewView(APIView):
    """
    Human-in-the-loop review endpoint.
    Allows support agents to accept (with optional edits) or reject an AI-generated draft.
    When accepted, automatically posts the response as a formal ticket comment.
    """
    permission_classes = [IsOrgMember]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket,
            id=ticket_id,
            organization=request.user.organization
        )

        draft = ticket.ai_drafts.prefetch_related('citations').first()
        if not draft:
            return Response(
                {"detail": "No AI draft found to review for this ticket."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AIDraftReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        edited_reply = serializer.validated_data.get('edited_reply', '').strip()
        is_internal_note = serializer.validated_data.get('is_internal_note', False)

        if action == 'ACCEPT':
            final_text = edited_reply if edited_reply else draft.suggested_reply
            draft.status = AIDraftStatus.ACCEPTED
            draft.final_edited_reply = final_text
            draft.reviewed_by = request.user
            draft.reviewed_at = timezone.now()
            draft.save(update_fields=['status', 'final_edited_reply', 'reviewed_by', 'reviewed_at'])

            # Automatically dispatch as a formal ticket comment
            TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                body=final_text,
                is_internal_note=is_internal_note
            )

            # Transition ticket from OPEN to IN_PROGRESS upon initial response
            if ticket.status == TicketStatus.OPEN:
                ticket.status = TicketStatus.IN_PROGRESS
                ticket.save(update_fields=['status', 'updated_at'])

        elif action == 'REJECT':
            draft.status = AIDraftStatus.REJECTED
            draft.reviewed_by = request.user
            draft.reviewed_at = timezone.now()
            draft.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

        response_serializer = AIDraftResponseSerializer(draft)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class SemanticSearchView(APIView):
    """
    Direct semantic retrieval endpoint for testing and auditing vector search recall.
    Scopes search strictly to the requesting user's organization knowledge base.
    """
    permission_classes = [IsOrgMember]

    def get(self, request):
        serializer = SemanticSearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['query']
        top_k = serializer.validated_data.get('top_k', 3)
        min_similarity = serializer.validated_data.get('min_similarity', 0.0)

        retrieval_service = VectorSearchService()
        matches = retrieval_service.search(
            query=query,
            organization_id=request.user.organization_id,
            top_k=top_k,
            min_similarity=min_similarity
        )

        result_serializer = SemanticSearchResultSerializer(matches, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)
