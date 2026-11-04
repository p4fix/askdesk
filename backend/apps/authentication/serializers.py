from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Organization, User, UserRole

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'organization',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'role', 'organization', 'is_active', 'created_at']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Enriches JWT claims with user identity, role, and organization tenant ID.
    Enables zero-lookup authorization in edge proxies and frontend routing.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Custom claims embedded directly in the JWT payload
        token['email'] = user.email
        token['role'] = user.role
        token['organization_id'] = str(user.organization.id) if user.organization else None
        token['organization_name'] = user.organization.name if user.organization else None

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Include serialized user info in login HTTP response
        data['user'] = UserSerializer(self.user).data
        return data


class RegisterOrganizationSerializer(serializers.Serializer):
    """
    Handles onboarding: atomically provisions a new Tenant Organization
    and the primary Administrator account.
    """
    organization_name = serializers.CharField(max_length=255, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value):
        normalized = value.lower().strip()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalized

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        org_name = validated_data['organization_name'].strip()
        email = validated_data['email']
        password = validated_data['password']
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()

        # Atomic transaction ensures no orphaned organization without an admin user
        with transaction.atomic():
            organization = Organization.objects.create(name=org_name)
            user = User.objects.create_user(
                email=email,
                password=password,
                organization=organization,
                role=UserRole.ADMIN,
                first_name=first_name,
                last_name=last_name,
            )

        # Generate tokens for immediate login
        refresh = RefreshToken.for_user(user)
        refresh['email'] = user.email
        refresh['role'] = user.role
        refresh['organization_id'] = str(organization.id)
        refresh['organization_name'] = organization.name

        return {
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class CreateAgentSerializer(serializers.ModelSerializer):
    """
    Admin-only serializer for provisioning new support agents within the admin's organization.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'role': {'default': UserRole.SUPPORT_AGENT}
        }

    def validate_email(self, value):
        normalized = value.lower().strip()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        org = request.user.organization
        password = validated_data.pop('password')

        user = User.objects.create_user(
            organization=org,
            password=password,
            **validated_data
        )
        return user

