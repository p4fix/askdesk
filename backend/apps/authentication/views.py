from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsOrgAdmin
from .serializers import (
    CreateAgentSerializer,
    CustomTokenObtainPairSerializer,
    RegisterOrganizationSerializer,
    UserSerializer,
)

class RegisterView(APIView):
    """
    Public onboarding endpoint. Registers an Organization and its primary Admin user.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Authenticates user with email & password, returning JWT tokens with tenant claims.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class CurrentUserView(APIView):
    """
    Returns the authenticated user's profile and organization metadata.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserManagementView(generics.ListCreateAPIView):
    """
    Admin-only endpoint to list support agents or provision new agents for the organization.
    Multi-tenant isolation: Scoped strictly to the requesting Admin's organization.
    """
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        # Strict tenant boundary: Admins can only see users from their own organization
        return User.objects.filter(organization=self.request.user.organization).order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateAgentSerializer
        return UserSerializer

    def perform_create(self, serializer):
        serializer.save()

