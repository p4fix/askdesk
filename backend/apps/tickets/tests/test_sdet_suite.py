import json
import queue
import threading
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import Organization, User, UserRole
from apps.tickets.events import TenantEventBroadcaster, event_broadcaster
from apps.tickets.models import Ticket, TicketComment, TicketPriority, TicketStatus
from apps.rag.models import AIDraftCitation, AIDraftResponse, AIDraftStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant_alpha(db):
    org = Organization.objects.create(name="Alpha Corp", slug="alpha-corp")
    admin = User.objects.create_user(
        email="admin@alpha.com",
        password="Password123!",
        organization=org,
        role=UserRole.ADMIN,
        first_name="Alpha",
        last_name="Admin",
    )
    agent = User.objects.create_user(
        email="agent@alpha.com",
        password="Password123!",
        organization=org,
        role=UserRole.SUPPORT_AGENT,
        first_name="Alpha",
        last_name="Agent",
    )
    return {"org": org, "admin": admin, "agent": agent}


@pytest.fixture
def tenant_beta(db):
    org = Organization.objects.create(name="Beta Industries", slug="beta-ind")
    admin = User.objects.create_user(
        email="admin@beta.com",
        password="Password123!",
        organization=org,
        role=UserRole.ADMIN,
        first_name="Beta",
        last_name="Admin",
    )
    agent = User.objects.create_user(
        email="agent@beta.com",
        password="Password123!",
        organization=org,
        role=UserRole.SUPPORT_AGENT,
        first_name="Beta",
        last_name="Agent",
    )
    return {"org": org, "admin": admin, "agent": agent}


def get_token_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['email'] = user.email
    refresh['role'] = user.role
    refresh['organization_id'] = str(user.organization.id)
    return str(refresh.access_token)


@pytest.mark.django_db
class TestBroadcasterUnit:
    """Rigorous unit tests for TenantEventBroadcaster pub/sub mechanics."""

    def test_broadcaster_subscribe_and_unsubscribe(self):
        broadcaster = TenantEventBroadcaster()
        org_id = "test-org-123"

        assert broadcaster.active_subscribers_count(org_id) == 0
        q1 = broadcaster.subscribe(org_id)
        q2 = broadcaster.subscribe(org_id)
        assert broadcaster.active_subscribers_count(org_id) == 2

        broadcaster.unsubscribe(org_id, q1)
        assert broadcaster.active_subscribers_count(org_id) == 1

        broadcaster.unsubscribe(org_id, q2)
        assert broadcaster.active_subscribers_count(org_id) == 0

    def test_broadcaster_multi_tenant_isolation(self):
        """Dispatched events to Org A must NEVER leak to Org B subscriber queues."""
        broadcaster = TenantEventBroadcaster()
        org_alpha = "org-alpha-uuid"
        org_beta = "org-beta-uuid"

        q_alpha = broadcaster.subscribe(org_alpha)
        q_beta = broadcaster.subscribe(org_beta)

        count = broadcaster.broadcast(org_alpha, "ticket.created", {"id": "ticket-1", "title": "Alpha ticket"})
        assert count == 1

        # Alpha subscriber must receive the event
        assert not q_alpha.empty()
        event = q_alpha.get_nowait()
        assert event["type"] == "ticket.created"
        assert event["data"]["title"] == "Alpha ticket"

        # Beta subscriber must have received NOTHING
        assert q_beta.empty()

        broadcaster.unsubscribe(org_alpha, q_alpha)
        broadcaster.unsubscribe(org_beta, q_beta)

    def test_broadcaster_concurrency_stress(self):
        """Validates thread-safety under heavy concurrent multi-threaded dispatching."""
        broadcaster = TenantEventBroadcaster()
        org_ids = [f"org-{i}" for i in range(5)]
        queues = {org_id: broadcaster.subscribe(org_id) for org_id in org_ids}

        def worker(org_id):
            for i in range(20):
                broadcaster.broadcast(org_id, "ping", {"index": i})

        threads = []
        for org_id in org_ids:
            for _ in range(4):
                t = threading.Thread(target=worker, args=(org_id,))
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

        # Each org received 4 threads * 20 iterations = 80 events
        for org_id, q in queues.items():
            assert q.qsize() == 80
            broadcaster.unsubscribe(org_id, q)


@pytest.mark.django_db
class TestSSEStreamEndpoint:
    """Integration tests for GET /api/v1/tickets/stream/ Server-Sent Events endpoint."""

    def test_sse_stream_missing_auth_returns_401(self, api_client):
        res = api_client.get("/api/v1/tickets/stream/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sse_stream_invalid_token_returns_401(self, api_client):
        res = api_client.get("/api/v1/tickets/stream/?token=malformed_fake_jwt_string")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sse_stream_header_auth_connection_ready(self, api_client, tenant_alpha):
        token = get_token_for_user(tenant_alpha["admin"])
        res = api_client.get(
            "/api/v1/tickets/stream/?limit=1",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert res.status_code == status.HTTP_200_OK
        assert "text/event-stream" in res["Content-Type"]

        # Parse the initial connection.ready event
        content = b"".join(res.streaming_content).decode("utf-8")
        assert "event: connection.ready" in content
        assert tenant_alpha["admin"].email in content

    def test_sse_stream_query_param_auth(self, api_client, tenant_alpha):
        """Browser native EventSource connects via '?token=<jwt>'."""
        token = get_token_for_user(tenant_alpha["agent"])
        res = api_client.get(f"/api/v1/tickets/stream/?token={token}&limit=1")
        assert res.status_code == status.HTTP_200_OK
        content = b"".join(res.streaming_content).decode("utf-8")
        assert "event: connection.ready" in content
        assert str(tenant_alpha["org"].id) in content

    def test_sse_receives_ticket_created_event(self, api_client, tenant_alpha):
        org_id = str(tenant_alpha["org"].id)
        token = get_token_for_user(tenant_alpha["agent"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Subscribe queue to capture broadcast
        sub_queue = event_broadcaster.subscribe(org_id)

        try:
            res = api_client.post(
                "/api/v1/tickets/",
                {
                    "title": "SSE Ticket Test",
                    "description": "Verifying real-time broadcast to connected agents.",
                    "priority": "HIGH",
                },
                format="json",
            )
            assert res.status_code == status.HTTP_201_CREATED
            ticket_id = res.data["id"]

            assert not sub_queue.empty()
            event = sub_queue.get_nowait()
            assert event["type"] == "ticket.created"
            assert event["data"]["id"] == ticket_id
            assert event["data"]["title"] == "SSE Ticket Test"
            assert event["data"]["priority"] == "HIGH"
        finally:
            event_broadcaster.unsubscribe(org_id, sub_queue)

    def test_sse_receives_comment_added_event(self, api_client, tenant_alpha):
        org_id = str(tenant_alpha["org"].id)
        token = get_token_for_user(tenant_alpha["agent"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        ticket = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=tenant_alpha["admin"],
            title="Comment Broadcast Test",
            description="Testing live comment stream.",
        )

        sub_queue = event_broadcaster.subscribe(org_id)
        try:
            res = api_client.post(
                f"/api/v1/tickets/{ticket.id}/comments/",
                {"body": "Hello customer, we are working on this.", "is_internal_note": False},
                format="json",
            )
            assert res.status_code == status.HTTP_201_CREATED

            assert not sub_queue.empty()
            event = sub_queue.get_nowait()
            assert event["type"] == "comment.added"
            assert event["data"]["ticket_id"] == str(ticket.id)
            assert "Hello customer" in event["data"]["body"]
            assert event["data"]["is_internal_note"] is False
        finally:
            event_broadcaster.unsubscribe(org_id, sub_queue)

    def test_sse_receives_ticket_updated_event(self, api_client, tenant_alpha):
        org_id = str(tenant_alpha["org"].id)
        token = get_token_for_user(tenant_alpha["admin"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        ticket = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=tenant_alpha["admin"],
            title="State Transition Broadcast",
            description="Testing status update broadcast.",
            status=TicketStatus.OPEN,
        )

        sub_queue = event_broadcaster.subscribe(org_id)
        try:
            res = api_client.patch(
                f"/api/v1/tickets/{ticket.id}/",
                {"status": "IN_PROGRESS", "priority": "URGENT"},
                format="json",
            )
            assert res.status_code == status.HTTP_200_OK

            assert not sub_queue.empty()
            event = sub_queue.get_nowait()
            assert event["type"] == "ticket.updated"
            assert event["data"]["id"] == str(ticket.id)
            assert event["data"]["status"] == "IN_PROGRESS"
            assert event["data"]["priority"] == "URGENT"
        finally:
            event_broadcaster.unsubscribe(org_id, sub_queue)


@pytest.mark.django_db
class TestSDETMultiTenantSecurity:
    """
    Rigorously tests multi-tenant security boundaries:
    Ensures zero cross-tenant event leakage, mutation, or eavesdropping.
    """

    def test_cross_tenant_sse_eavesdropping_prevention(self, api_client, tenant_alpha, tenant_beta):
        """Tenant Beta agent must NEVER receive Tenant Alpha ticket/comment events."""
        token_alpha = get_token_for_user(tenant_alpha["admin"])
        org_alpha = str(tenant_alpha["org"].id)
        org_beta = str(tenant_beta["org"].id)

        queue_alpha = event_broadcaster.subscribe(org_alpha)
        queue_beta = event_broadcaster.subscribe(org_beta)

        try:
            api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_alpha}")
            # Alpha creates a confidential ticket
            res = api_client.post(
                "/api/v1/tickets/",
                {
                    "title": "Alpha Confidential Security Ticket",
                    "description": "Proprietary internal vulnerability.",
                    "priority": "URGENT",
                },
                format="json",
            )
            assert res.status_code == status.HTTP_201_CREATED

            # Alpha queue must have received the event
            assert not queue_alpha.empty()
            alpha_event = queue_alpha.get_nowait()
            assert alpha_event["data"]["title"] == "Alpha Confidential Security Ticket"

            # Beta queue must have received NOTHING
            assert queue_beta.empty()
        finally:
            event_broadcaster.unsubscribe(org_alpha, queue_alpha)
            event_broadcaster.unsubscribe(org_beta, queue_beta)

    def test_cross_tenant_ticket_assignment_prevented(self, api_client, tenant_alpha, tenant_beta):
        """Alpha Admin cannot assign an Alpha ticket to a Beta Agent."""
        token_alpha = get_token_for_user(tenant_alpha["admin"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_alpha}")

        ticket = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=tenant_alpha["admin"],
            title="Alpha Ticket for Assignee Test",
            description="Testing assignee tenant boundaries.",
        )

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/",
            {"assigned_to": str(tenant_beta["agent"].id)},
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_cross_tenant_ticket_detail_isolation(self, api_client, tenant_alpha, tenant_beta):
        """Beta Agent querying Alpha ticket receives 404 Not Found."""
        token_beta = get_token_for_user(tenant_beta["agent"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_beta}")

        ticket_alpha = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=tenant_alpha["admin"],
            title="Alpha Only Ticket",
            description="Strictly confidential to Alpha.",
        )

        res = api_client.get(f"/api/v1/tickets/{ticket_alpha.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_tenant_comment_injection_prevented(self, api_client, tenant_alpha, tenant_beta):
        """Beta Agent cannot post comments to Alpha ticket."""
        token_beta = get_token_for_user(tenant_beta["agent"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_beta}")

        ticket_alpha = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=tenant_alpha["admin"],
            title="Alpha Secret",
            description="Tenant isolation test.",
        )

        res = api_client.post(
            f"/api/v1/tickets/{ticket_alpha.id}/comments/",
            {"body": "Injected malicious reply from foreign tenant.", "is_internal_note": False},
            format="json",
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_rag_review_event_broadcasting(self, api_client, tenant_alpha):
        """Reviewing an AI draft broadcasts rag.draft_reviewed and comment.added."""
        token_alpha = get_token_for_user(tenant_alpha["admin"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_alpha}")
        org_id = str(tenant_alpha["org"].id)

        ticket = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=tenant_alpha["admin"],
            title="RAG Draft Review Ticket",
            description="Customer asking about return policy.",
            status=TicketStatus.OPEN,
        )

        draft = AIDraftResponse.objects.create(
            ticket=ticket,
            organization=tenant_alpha["org"],
            suggested_reply="Returns are accepted within 30 days of purchase.",
            confidence_score=0.95,
            status=AIDraftStatus.DRAFT_GENERATED,
        )

        sub_queue = event_broadcaster.subscribe(org_id)
        try:
            res = api_client.post(
                f"/api/v1/tickets/{ticket.id}/ai-draft/review/",
                {"action": "ACCEPT", "is_internal_note": False},
                format="json",
            )
            assert res.status_code == status.HTTP_200_OK

            # Must have received comment.added, ticket.updated (from OPEN to IN_PROGRESS), and rag.draft_reviewed
            events = []
            while not sub_queue.empty():
                events.append(sub_queue.get_nowait())

            event_types = [e["type"] for e in events]
            assert "comment.added" in event_types
            assert "ticket.updated" in event_types
            assert "rag.draft_reviewed" in event_types
        finally:
            event_broadcaster.unsubscribe(org_id, sub_queue)
