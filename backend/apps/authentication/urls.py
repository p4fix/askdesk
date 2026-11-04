from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CurrentUserView,
    CustomTokenObtainPairView,
    RegisterView,
    UserManagementView,
)

app_name = 'authentication'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('me/', CurrentUserView.as_view(), name='me'),
    path('users/', UserManagementView.as_view(), name='user-list-create'),
]

