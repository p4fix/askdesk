import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import Organization, User, UserRole
from apps.tickets.models import Ticket, TicketComment, TicketPriority, TicketStatus

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
    agent_1 = User.objects.create_user(
        email="agent1@alpha.com",
        password="SecurePassword123!",
        organization=org,
        role=UserRole.SUPPORT_AGENT,
        first_name="Alpha",
        last_name="One"
    )
    agent_2 = User.objects.create_user(
        email="agent2@alpha.com",
        password="SecurePassword123!",
        organization=org,
        role=UserRole.SUPPORT_AGENT,
        first_name="Alpha",
        last_name="Two"
    )
    return {"org": org, "admin": admin, "agent_1": agent_1, "agent_2": agent_2}

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
class TestTicketCreation:
    def test_agent_can_create_ticket_with_defaults(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        api_client.force_authenticate(user=agent)

        payload = {
            "title": "Cannot login to VPN portal",
            "description": "User gets error 504 Gateway Timeout when connecting.",
        }
        response = api_client.post("/api/v1/tickets/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["status"] == TicketStatus.OPEN
        assert data["priority"] == TicketPriority.MEDIUM
        assert data["assigned_to"] is None
        assert data["created_by"]["id"] == str(agent.id)
        assert data["comments_count"] == 0

    def test_create_ticket_with_explicit_priority_and_assignee(self, api_client, tenant_alpha):
        agent_1 = tenant_alpha["agent_1"]
        agent_2 = tenant_alpha["agent_2"]
        api_client.force_authenticate(user=agent_1)

        payload = {
            "title": "Production database latency spike",
            "description": "Query latency spiked past 3500ms.",
            "priority": TicketPriority.URGENT,
            "assigned_to": str(agent_2.id),
        }
        response = api_client.post("/api/v1/tickets/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["priority"] == TicketPriority.URGENT
        assert response.data["assigned_to"]["id"] == str(agent_2.id)

    def test_cannot_assign_ticket_to_agent_from_different_tenant(self, api_client, tenant_alpha, tenant_beta):
        alpha_agent = tenant_alpha["agent_1"]
        beta_agent = tenant_beta["agent"]
        api_client.force_authenticate(user=alpha_agent)

        payload = {
            "title": "Cross tenant injection attempt",
            "description": "Attempting to assign ticket to competitor's agent.",
            "assigned_to": str(beta_agent.id),
        }
        response = api_client.post("/api/v1/tickets/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "assigned_to" in response.data

    def test_create_ticket_validation_blank_fields(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        api_client.force_authenticate(user=agent)

        response = api_client.post("/api/v1/tickets/", {"title": "", "description": ""}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in response.data
        assert "description" in response.data

    def test_unauthenticated_ticket_creation_returns_401(self, api_client):
        response = api_client.post("/api/v1/tickets/", {"title": "Test", "description": "Desc"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTicketListingAndFiltering:
    def test_strict_multi_tenant_isolation_in_ticket_list(self, api_client, tenant_alpha, tenant_beta):
        alpha_agent = tenant_alpha["agent_1"]
        beta_agent = tenant_beta["agent"]

        # Create 2 tickets for Alpha
        t1 = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=alpha_agent,
            title="Alpha Ticket 1",
            description="Alpha issue 1"
        )
        t2 = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=alpha_agent,
            title="Alpha Ticket 2",
            description="Alpha issue 2"
        )
        # Create 1 ticket for Beta
        t_beta = Ticket.objects.create(
            organization=tenant_beta["org"],
            created_by=beta_agent,
            title="Beta Confidential Issue",
            description="Beta confidential description"
        )

        api_client.force_authenticate(user=alpha_agent)
        response = api_client.get("/api/v1/tickets/")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data
        ticket_ids = [item["id"] for item in results]
        assert str(t1.id) in ticket_ids
        assert str(t2.id) in ticket_ids
        assert str(t_beta.id) not in ticket_ids

    def test_filter_by_status(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]

        Ticket.objects.create(organization=org, created_by=agent, title="Open Ticket", description="Desc", status=TicketStatus.OPEN)
        Ticket.objects.create(organization=org, created_by=agent, title="Resolved Ticket", description="Desc", status=TicketStatus.RESOLVED)

        api_client.force_authenticate(user=agent)
        response = api_client.get("/api/v1/tickets/?status=OPEN")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data
        assert len(results) == 1
        assert results[0]["status"] == TicketStatus.OPEN

    def test_filter_by_priority(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]

        Ticket.objects.create(organization=org, created_by=agent, title="Low Priority", description="Desc", priority=TicketPriority.LOW)
        Ticket.objects.create(organization=org, created_by=agent, title="Urgent Priority", description="Desc", priority=TicketPriority.URGENT)

        api_client.force_authenticate(user=agent)
        response = api_client.get("/api/v1/tickets/?priority=URGENT")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data
        assert len(results) == 1
        assert results[0]["priority"] == TicketPriority.URGENT

    def test_filter_by_assigned_to_me_and_unassigned(self, api_client, tenant_alpha):
        agent_1 = tenant_alpha["agent_1"]
        agent_2 = tenant_alpha["agent_2"]
        org = tenant_alpha["org"]

        t_mine = Ticket.objects.create(organization=org, created_by=agent_1, assigned_to=agent_1, title="Mine", description="Desc")
        t_other = Ticket.objects.create(organization=org, created_by=agent_1, assigned_to=agent_2, title="Other", description="Desc")
        t_unassigned = Ticket.objects.create(organization=org, created_by=agent_1, assigned_to=None, title="Unassigned", description="Desc")

        api_client.force_authenticate(user=agent_1)

        # Filter: assigned_to=me
        res_me = api_client.get("/api/v1/tickets/?assigned_to=me")
        data_me = res_me.data["results"] if "results" in res_me.data else res_me.data
        assert len(data_me) == 1
        assert data_me[0]["id"] == str(t_mine.id)

        # Filter: assigned_to=unassigned
        res_un = api_client.get("/api/v1/tickets/?assigned_to=unassigned")
        data_un = res_un.data["results"] if "results" in res_un.data else res_un.data
        assert len(data_un) == 1
        assert data_un[0]["id"] == str(t_unassigned.id)

    def test_search_filter_by_text(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]

        Ticket.objects.create(organization=org, created_by=agent, title="Refund request for invoice 9091", description="Customer wants money back")
        Ticket.objects.create(organization=org, created_by=agent, title="Password reset failed", description="Auth token expired")

        api_client.force_authenticate(user=agent)
        response = api_client.get("/api/v1/tickets/?search=refund")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data
        assert len(results) == 1
        assert "Refund" in results[0]["title"]


@pytest.mark.django_db
class TestTicketDetailAndUpdates:
    def test_retrieve_ticket_detail_with_comments_count(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]
        ticket = Ticket.objects.create(organization=org, created_by=agent, title="Detail Check", description="Full details")

        # Add a comment
        TicketComment.objects.create(ticket=ticket, author=agent, body="First investigation step")

        api_client.force_authenticate(user=agent)
        response = api_client.get(f"/api/v1/tickets/{ticket.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(ticket.id)
        assert response.data["description"] == "Full details"
        assert response.data["comments_count"] == 1
        assert len(response.data["comments"]) == 1
        assert response.data["comments"][0]["body"] == "First investigation step"

    def test_patch_ticket_status_and_priority(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]
        ticket = Ticket.objects.create(organization=org, created_by=agent, title="Status Patch", description="Desc")

        api_client.force_authenticate(user=agent)
        patch_payload = {
            "status": TicketStatus.IN_PROGRESS,
            "priority": TicketPriority.HIGH,
        }
        response = api_client.patch(f"/api/v1/tickets/{ticket.id}/", patch_payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TicketStatus.IN_PROGRESS
        assert response.data["priority"] == TicketPriority.HIGH

        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.priority == TicketPriority.HIGH

    def test_patch_ticket_assignee(self, api_client, tenant_alpha):
        agent_1 = tenant_alpha["agent_1"]
        agent_2 = tenant_alpha["agent_2"]
        org = tenant_alpha["org"]
        ticket = Ticket.objects.create(organization=org, created_by=agent_1, title="Assignee Test", description="Desc")

        api_client.force_authenticate(user=agent_1)
        response = api_client.patch(f"/api/v1/tickets/{ticket.id}/", {"assigned_to": str(agent_2.id)}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["assigned_to"]["id"] == str(agent_2.id)

    def test_patch_ticket_with_invalid_assignee_fails(self, api_client, tenant_alpha, tenant_beta):
        agent_1 = tenant_alpha["agent_1"]
        beta_agent = tenant_beta["agent"]
        org = tenant_alpha["org"]
        ticket = Ticket.objects.create(organization=org, created_by=agent_1, title="Cross Assign", description="Desc")

        api_client.force_authenticate(user=agent_1)
        response = api_client.patch(f"/api/v1/tickets/{ticket.id}/", {"assigned_to": str(beta_agent.id)}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "assigned_to" in response.data

    def test_cross_tenant_ticket_detail_returns_404(self, api_client, tenant_alpha, tenant_beta):
        alpha_agent = tenant_alpha["agent_1"]
        beta_agent = tenant_beta["agent"]
        beta_ticket = Ticket.objects.create(
            organization=tenant_beta["org"],
            created_by=beta_agent,
            title="Beta Private Ticket",
            description="Beta confidential content"
        )

        api_client.force_authenticate(user=alpha_agent)
        # Attempt to access Beta's ticket from Alpha
        response = api_client.get(f"/api/v1/tickets/{beta_ticket.id}/")
        # Must return 404 to avoid information disclosure
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTicketComments:
    def test_add_public_comment_to_ticket(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]
        ticket = Ticket.objects.create(organization=org, created_by=agent, title="Comment Test", description="Desc")

        api_client.force_authenticate(user=agent)
        payload = {
            "body": "Customer replied with screenshot of the stack trace.",
            "is_internal_note": False,
        }
        response = api_client.post(f"/api/v1/tickets/{ticket.id}/comments/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["body"] == payload["body"]
        assert response.data["is_internal_note"] is False
        assert response.data["author"]["id"] == str(agent.id)

    def test_add_internal_note_to_ticket(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]
        ticket = Ticket.objects.create(organization=org, created_by=agent, title="Internal Note Test", description="Desc")

        api_client.force_authenticate(user=agent)
        payload = {
            "body": "Internal notes: Issue appears related to upstream AWS outage in us-east-1.",
            "is_internal_note": True,
        }
        response = api_client.post(f"/api/v1/tickets/{ticket.id}/comments/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_internal_note"] is True

    def test_blank_comment_body_fails_validation(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent_1"]
        org = tenant_alpha["org"]
        ticket = Ticket.objects.create(organization=org, created_by=agent, title="Blank Note", description="Desc")

        api_client.force_authenticate(user=agent)
        response = api_client.post(f"/api/v1/tickets/{ticket.id}/comments/", {"body": "   "}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "body" in response.data

    def test_cannot_post_comment_to_foreign_tenant_ticket(self, api_client, tenant_alpha, tenant_beta):
        alpha_agent = tenant_alpha["agent_1"]
        beta_agent = tenant_beta["agent"]
        beta_ticket = Ticket.objects.create(
            organization=tenant_beta["org"],
            created_by=beta_agent,
            title="Beta Private Ticket",
            description="Secret"
        )

        api_client.force_authenticate(user=alpha_agent)
        response = api_client.post(
            f"/api/v1/tickets/{beta_ticket.id}/comments/",
            {"body": "Intruder comment"},
            format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

