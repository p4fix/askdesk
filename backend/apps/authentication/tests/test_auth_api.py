import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import UntypedToken
import jwt
from django.conf import settings

from apps.authentication.models import Organization, User, UserRole

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def tenant_alpha(db):
    org = Organization.objects.create(name="Alpha Corp", slug="alpha-corp")
    admin = User.objects.create_user(
        email="admin@alpha.com",
        password="SecurePassword123!",
        organization=org,
        role=UserRole.ADMIN,
        first_name="Alpha",
        last_name="Admin"
    )
    agent = User.objects.create_user(
        email="agent@alpha.com",
        password="SecurePassword123!",
        organization=org,
        role=UserRole.SUPPORT_AGENT,
        first_name="Alpha",
        last_name="Agent"
    )
    return {"org": org, "admin": admin, "agent": agent}

@pytest.fixture
def tenant_beta(db):
    org = Organization.objects.create(name="Beta LLC", slug="beta-llc")
    admin = User.objects.create_user(
        email="admin@beta.com",
        password="SecurePassword123!",
        organization=org,
        role=UserRole.ADMIN,
        first_name="Beta",
        last_name="Admin"
    )
    agent = User.objects.create_user(
        email="agent@beta.com",
        password="SecurePassword123!",
        organization=org,
        role=UserRole.SUPPORT_AGENT,
        first_name="Beta",
        last_name="Agent"
    )
    return {"org": org, "admin": admin, "agent": agent}


@pytest.mark.django_db
class TestRegistration:
    def test_successful_organization_and_admin_registration(self, api_client):
        payload = {
            "organization_name": "Acme Global",
            "email": "ceo@acme.com",
            "password": "StrongPassword2026!",
            "first_name": "Jane",
            "last_name": "Doe"
        }
        response = api_client.post("/api/v1/auth/register/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "ceo@acme.com"
        assert data["user"]["role"] == UserRole.ADMIN
        assert data["user"]["organization"]["name"] == "Acme Global"

        # Verify DB records
        created_user = User.objects.get(email="ceo@acme.com")
        assert created_user.organization.name == "Acme Global"
        assert created_user.role == UserRole.ADMIN

    def test_duplicate_email_registration_fails(self, api_client, tenant_alpha):
        payload = {
            "organization_name": "Duplicate Inc",
            "email": "admin@alpha.com",
            "password": "Password123!",
        }
        response = api_client.post("/api/v1/auth/register/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_weak_password_registration_fails(self, api_client):
        payload = {
            "organization_name": "Weak Sec Co",
            "email": "weak@example.com",
            "password": "123",
        }
        response = api_client.post("/api/v1/auth/register/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data


@pytest.mark.django_db
class TestAuthenticationAndJWT:
    def test_successful_login_returns_custom_jwt_claims(self, api_client, tenant_alpha):
        payload = {
            "email": "admin@alpha.com",
            "password": "SecurePassword123!"
        }
        response = api_client.post("/api/v1/auth/login/", payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "admin@alpha.com"

        # Decode token to verify custom tenant claims embedded in JWT
        decoded = jwt.decode(
            data["access"],
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        assert decoded["email"] == "admin@alpha.com"
        assert decoded["role"] == UserRole.ADMIN
        assert decoded["organization_id"] == str(tenant_alpha["org"].id)
        assert decoded["organization_name"] == "Alpha Corp"

    def test_login_with_invalid_credentials_fails(self, api_client, tenant_alpha):
        payload = {
            "email": "admin@alpha.com",
            "password": "WrongPassword!"
        }
        response = api_client.post("/api/v1/auth/login/", payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, tenant_alpha):
        login_res = api_client.post("/api/v1/auth/login/", {
            "email": "admin@alpha.com",
            "password": "SecurePassword123!"
        }, format="json")
        refresh_token = login_res.data["refresh"]

        refresh_res = api_client.post("/api/v1/auth/refresh/", {
            "refresh": refresh_token
        }, format="json")
        assert refresh_res.status_code == status.HTTP_200_OK
        assert "access" in refresh_res.data


@pytest.mark.django_db
class TestCurrentUserEndpoint:
    def test_authenticated_user_me_endpoint(self, api_client, tenant_alpha):
        api_client.force_authenticate(user=tenant_alpha["agent"])
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "agent@alpha.com"
        assert response.data["role"] == UserRole.SUPPORT_AGENT
        assert response.data["organization"]["slug"] == "alpha-corp"

    def test_unauthenticated_me_endpoint_returns_401(self, api_client):
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRolePermissionsAndMultiTenantIsolation:
    def test_admin_can_provision_support_agent(self, api_client, tenant_alpha):
        api_client.force_authenticate(user=tenant_alpha["admin"])
        payload = {
            "email": "newbie@alpha.com",
            "password": "Password12345!",
            "first_name": "New",
            "last_name": "Agent",
            "role": UserRole.SUPPORT_AGENT
        }
        response = api_client.post("/api/v1/auth/users/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # Ensure the new agent is automatically scoped to Alpha Corp
        new_user = User.objects.get(email="newbie@alpha.com")
        assert new_user.organization == tenant_alpha["org"]

    def test_support_agent_cannot_provision_other_users(self, api_client, tenant_alpha):
        api_client.force_authenticate(user=tenant_alpha["agent"])
        payload = {
            "email": "unauthorized@alpha.com",
            "password": "Password12345!"
        }
        response = api_client.post("/api/v1/auth/users/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_strict_multi_tenant_isolation_between_organizations(self, api_client, tenant_alpha, tenant_beta):
        """
        SDET Critical Security Test:
        Asserts that Admin Alpha cannot see or list users belonging to Tenant Beta.
        """
        api_client.force_authenticate(user=tenant_alpha["admin"])
        response = api_client.get("/api/v1/auth/users/")
        assert response.status_code == status.HTTP_200_OK

        returned_emails = [u["email"] for u in response.data["results"]]
        assert "admin@alpha.com" in returned_emails
        assert "agent@alpha.com" in returned_emails
        # Leakage check: Tenant Beta users must NEVER be returned to Tenant Alpha
        assert "admin@beta.com" not in returned_emails
        assert "agent@beta.com" not in returned_emails

