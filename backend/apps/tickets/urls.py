from django.urls import path

from apps.rag.views import AIDraftGenerateView, AIDraftReviewView
from .sse import TicketEventStreamView
from .views import (
    TicketCommentListCreateView,
    TicketDetailView,
    TicketListCreateView,
)

app_name = 'tickets'

urlpatterns = [
    path('', TicketListCreateView.as_view(), name='ticket-list-create'),
    path('stream/', TicketEventStreamView.as_view(), name='ticket-sse-stream'),
    path('<uuid:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    path('<uuid:ticket_id>/comments/', TicketCommentListCreateView.as_view(), name='ticket-comment-list-create'),
    path('<uuid:ticket_id>/ai-draft/', AIDraftGenerateView.as_view(), name='ticket-ai-draft'),
    path('<uuid:ticket_id>/ai-draft/review/', AIDraftReviewView.as_view(), name='ticket-ai-draft-review'),
]

