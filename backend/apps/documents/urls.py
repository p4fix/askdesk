from django.urls import path

from .views import DocumentDetailView, DocumentListCreateView

app_name = 'documents'

urlpatterns = [
    path('', DocumentListCreateView.as_view(), name='document-list-create'),
    path('upload/', DocumentListCreateView.as_view(), name='document-upload'),
    path('<uuid:pk>/', DocumentDetailView.as_view(), name='document-detail'),
]

