from django.urls import path

from .views import (
    TicketCommentListCreateView,
    TicketDetailView,
    TicketListCreateView,
)

app_name = 'tickets'

urlpatterns = [
    path('', TicketListCreateView.as_view(), name='ticket-list-create'),
    path('<uuid:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    path('<uuid:ticket_id>/comments/', TicketCommentListCreateView.as_view(), name='ticket-comment-list-create'),
]

