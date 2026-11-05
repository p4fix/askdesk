from django.urls import path
from apps.rag.views import AIDraftGenerateView, AIDraftReviewView, SemanticSearchView

app_name = 'rag'

urlpatterns = [
    path('search/', SemanticSearchView.as_view(), name='search'),
    path('tickets/<uuid:ticket_id>/draft/', AIDraftGenerateView.as_view(), name='ticket-draft'),
    path('tickets/<uuid:ticket_id>/review/', AIDraftReviewView.as_view(), name='ticket-review'),
]
