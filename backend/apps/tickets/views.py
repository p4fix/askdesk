from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response

from apps.authentication.permissions import IsOrgMember
from apps.tickets.models import Ticket, TicketComment, TicketPriority, TicketStatus
from apps.tickets.serializers import (
    TicketCommentSerializer,
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
    TicketUpdateSerializer,
)

class TicketListCreateView(generics.ListCreateAPIView):
    """
    List tickets with status/priority/assignee filtering and full-text search,
    or submit a new customer support ticket.
    Strict tenant boundary: Scoped strictly to the requesting user's organization.
    """
    permission_classes = [IsOrgMember]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Ticket.objects.filter(organization=user.organization)
            .select_related('created_by', 'assigned_to')
            .annotate(comments_count=Count('comments'))
        )

        # Query parameter filters
        ticket_status = self.request.query_params.get('status')
        if ticket_status:
            queryset = queryset.filter(status=ticket_status.upper())

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority.upper())

        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            if assigned_to.lower() == 'me':
                queryset = queryset.filter(assigned_to=user)
            elif assigned_to.lower() == 'unassigned':
                queryset = queryset.filter(assigned_to__isnull=True)
            else:
                queryset = queryset.filter(assigned_to_id=assigned_to)

        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketCreateSerializer
        return TicketListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        # Return full detail representation on creation
        detail_serializer = TicketDetailSerializer(ticket, context=self.get_serializer_context())
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve full ticket details with threaded conversation history,
    update ticket state/assignment, or close/delete a ticket.
    Multi-tenant isolation: Returns 404 for any ticket belonging to another tenant.
    """
    permission_classes = [IsOrgMember]

    def get_queryset(self):
        return (
            Ticket.objects.filter(organization=self.request.user.organization)
            .select_related('created_by', 'assigned_to')
            .prefetch_related('comments__author')
            .annotate(comments_count=Count('comments'))
        )

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return TicketUpdateSerializer
        return TicketDetailSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_ticket = serializer.save()

        # Re-fetch with annotations & prefetch for response representation
        refreshed = (
            Ticket.objects.filter(id=updated_ticket.id)
            .select_related('created_by', 'assigned_to')
            .prefetch_related('comments__author')
            .annotate(comments_count=Count('comments'))
            .first()
        )
        return Response(TicketDetailSerializer(refreshed).data, status=status.HTTP_200_OK)


class TicketCommentListCreateView(generics.ListCreateAPIView):
    """
    List threaded comments and internal notes for a ticket,
    or append a new public reply or internal staff note.
    """
    permission_classes = [IsOrgMember]
    serializer_class = TicketCommentSerializer

    def get_ticket(self):
        return get_object_or_404(
            Ticket,
            id=self.kwargs['ticket_id'],
            organization=self.request.user.organization
        )

    def get_queryset(self):
        ticket = self.get_ticket()
        return ticket.comments.select_related('author').order_by('created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ticket'] = self.get_ticket()
        return context

    def perform_create(self, serializer):
        serializer.save()

