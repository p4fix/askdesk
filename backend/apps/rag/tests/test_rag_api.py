import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import Organization, User, UserRole
from apps.documents.models import Document, DocumentChunk, DocumentFileType, DocumentStatus
from apps.documents.services.embedding import MockEmbeddingService
from apps.rag.models import AIDraftCitation, AIDraftResponse, AIDraftStatus
from apps.rag.services.retrieval import VectorSearchService
from apps.tickets.models import Ticket, TicketComment, TicketPriority, TicketStatus

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant_alpha(db):
    org = Organization.objects.create(name="Alpha Logistics", slug="alpha-logistics")
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
    org = Organization.objects.create(name="Beta Health", slug="beta-health")
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


@pytest.fixture
def alpha_knowledge_base(tenant_alpha):
    """Provisions a sample processed document with indexed vector chunks for Tenant Alpha."""
    embedding_service = MockEmbeddingService()
    org = tenant_alpha["org"]
    admin = tenant_alpha["admin"]

    doc = Document.objects.create(
        organization=org,
        uploaded_by=admin,
        title="Alpha Refund & Cancellation Guidelines",
        file="documents/sample_refund.txt",
        file_type=DocumentFileType.TXT,
        file_size_bytes=1024,
        status=DocumentStatus.PROCESSED
    )

    chunk_1_text = (
        "Refund Policy Overview: Customers can request a full refund within 30 days of purchase "
        "if the software license has not been activated. To initiate a refund, submit a ticket "
        "with the invoice number and reason for cancellation."
    )
    chunk_2_text = (
        "Server Maintenance Window: Scheduled downtime occurs every Sunday from 02:00 UTC to 04:00 UTC. "
        "Critical emergency patches may be applied with a 30-minute advance notice banner."
    )

    vec_1 = embedding_service.generate_embedding(chunk_1_text)
    vec_2 = embedding_service.generate_embedding(chunk_2_text)

    chunk_1 = DocumentChunk.objects.create(
        document=doc,
        organization=org,
        chunk_index=0,
        content=chunk_1_text,
        token_count=len(chunk_1_text.split()),
        embedding=vec_1,
        metadata={"page": 1, "section": "Refunds"}
    )
    chunk_2 = DocumentChunk.objects.create(
        document=doc,
        organization=org,
        chunk_index=1,
        content=chunk_2_text,
        token_count=len(chunk_2_text.split()),
        embedding=vec_2,
        metadata={"page": 2, "section": "Maintenance"}
    )

    return {"document": doc, "chunk_1": chunk_1, "chunk_2": chunk_2}


@pytest.fixture
def beta_knowledge_base(tenant_beta):
    """Provisions confidential documents in Tenant Beta to verify cross-tenant vector isolation."""
    embedding_service = MockEmbeddingService()
    org = tenant_beta["org"]
    admin = tenant_beta["admin"]

    doc = Document.objects.create(
        organization=org,
        uploaded_by=admin,
        title="Beta Confidential Executive Compensation",
        file="documents/beta_payroll.txt",
        file_type=DocumentFileType.TXT,
        file_size_bytes=512,
        status=DocumentStatus.PROCESSED
    )

    secret_text = "Executive bonus structure: Vice presidents receive 40% equity bonuses upon quarterly targets."
    vec = embedding_service.generate_embedding(secret_text)

    chunk = DocumentChunk.objects.create(
        document=doc,
        organization=org,
        chunk_index=0,
        content=secret_text,
        token_count=len(secret_text.split()),
        embedding=vec,
        metadata={"page": 1}
    )
    return {"document": doc, "chunk": chunk}


@pytest.fixture
def alpha_ticket(tenant_alpha):
    """Provisions an open ticket in Tenant Alpha requesting a refund."""
    return Ticket.objects.create(
        organization=tenant_alpha["org"],
        created_by=tenant_alpha["agent"],
        title="Customer requesting license refund within 14 days",
        description="The customer bought License #9948 two weeks ago and wants a full refund because their team chose a different tool.",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH
    )


# ============================================================================
# 1. Vector Retrieval and Multi-Tenant Isolation Tests
# ============================================================================
@pytest.mark.django_db
class TestVectorRetrievalAndSemanticSearch:

    def test_vector_search_returns_relevant_chunks_within_tenant(self, tenant_alpha, alpha_knowledge_base):
        service = VectorSearchService(embedding_service=MockEmbeddingService())
        results = service.search(
            query="How do I get a full refund for an unactivated license?",
            organization_id=tenant_alpha["org"].id,
            top_k=2
        )

        assert len(results) > 0
        top_result = results[0]
        assert "Refund Policy Overview" in top_result["content"]
        assert top_result["document_title"] == "Alpha Refund & Cancellation Guidelines"
        assert top_result["page_number"] == 1
        assert top_result["similarity"] > 0.15

    def test_strict_multi_tenant_isolation_in_vector_retrieval(
        self, tenant_alpha, tenant_beta, alpha_knowledge_base, beta_knowledge_base
    ):
        """Alpha agent querying for Beta confidential keywords must NEVER retrieve Beta chunks."""
        service = VectorSearchService(embedding_service=MockEmbeddingService())

        # Tenant Alpha search for Beta confidential data
        alpha_results = service.search(
            query="Executive bonus structure and quarterly equity targets",
            organization_id=tenant_alpha["org"].id,
            top_k=5
        )

        for match in alpha_results:
            assert "Executive bonus" not in match["content"]
            assert match["document_title"] != "Beta Confidential Executive Compensation"

        # Tenant Beta searching the exact same query receives the document
        beta_results = service.search(
            query="Executive bonus structure and quarterly equity targets",
            organization_id=tenant_beta["org"].id,
            top_k=5
        )
        assert len(beta_results) == 1
        assert "Executive bonus structure" in beta_results[0]["content"]

    def test_semantic_search_api_endpoint(self, api_client, tenant_alpha, alpha_knowledge_base):
        api_client.force_authenticate(user=tenant_alpha["agent"])
        response = api_client.get(
            "/api/v1/rag/search/",
            {"query": "scheduled downtime server maintenance", "top_k": 3}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert len(data) >= 1
        assert "Server Maintenance Window" in data[0]["content"]
        assert data[0]["page_number"] == 2

    def test_empty_query_returns_empty_results(self, tenant_alpha, alpha_knowledge_base):
        service = VectorSearchService(embedding_service=MockEmbeddingService())
        assert service.search(query="", organization_id=tenant_alpha["org"].id) == []
        assert service.search(query="   ", organization_id=tenant_alpha["org"].id) == []


# ============================================================================
# 2. RAG Generation Pipeline Tests
# ============================================================================
@pytest.mark.django_db
class TestRAGDraftGeneration:

    def test_generate_ai_draft_with_grounded_citations(
        self, api_client, tenant_alpha, alpha_ticket, alpha_knowledge_base
    ):
        api_client.force_authenticate(user=tenant_alpha["agent"])

        response = api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data

        assert data["ticket_id"] == str(alpha_ticket.id)
        assert data["organization_id"] == str(tenant_alpha["org"].id)
        assert data["status"] == AIDraftStatus.DRAFT_GENERATED
        assert data["model_name"] == "mock-gpt-4o-mini"
        assert data["confidence_score"] > 0.15
        assert "Refund Policy Overview" in data["suggested_reply"]

        # Verify structured citations
        citations = data["citations"]
        assert len(citations) >= 1
        top_citation = citations[0]
        assert top_citation["source_title"] == "Alpha Refund & Cancellation Guidelines"
        assert top_citation["page_number"] == 1
        assert top_citation["relevance_score"] > 0.15
        assert "Customers can request a full refund within 30 days" in top_citation["cited_excerpt"]

        # Verify DB persistence
        draft_in_db = AIDraftResponse.objects.get(id=data["id"])
        assert draft_in_db.citations.count() == len(citations)

    def test_anti_hallucination_fallback_when_knowledge_base_lacks_context(
        self, api_client, tenant_alpha, alpha_knowledge_base
    ):
        api_client.force_authenticate(user=tenant_alpha["agent"])

        # Ticket regarding a topic with no documentation in knowledge base
        exotic_ticket = Ticket.objects.create(
            organization=tenant_alpha["org"],
            created_by=tenant_alpha["agent"],
            title="Quantum gravity warp engine calibration protocol",
            description="Our sub-space hyperspace relay is fluctuating at 99.4 gigahertz. Need guidance.",
            status=TicketStatus.OPEN,
            priority=TicketPriority.LOW
        )

        response = api_client.post(f"/api/v1/tickets/{exotic_ticket.id}/ai-draft/")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data

        fallback_msg = (
            "I do not have enough documentation to answer this question. "
            "Please reach out to our human support team for further assistance."
        )
        assert fallback_msg in data["suggested_reply"]
        assert data["citations"] == []

    def test_get_latest_ai_draft_for_ticket(
        self, api_client, tenant_alpha, alpha_ticket, alpha_knowledge_base
    ):
        api_client.force_authenticate(user=tenant_alpha["agent"])

        # Prior to generation, returns 404
        get_before = api_client.get(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")
        assert get_before.status_code == status.HTTP_404_NOT_FOUND

        # Generate draft
        post_resp = api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")
        assert post_resp.status_code == status.HTTP_201_CREATED

        # Fetch draft
        get_after = api_client.get(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")
        assert get_after.status_code == status.HTTP_200_OK
        assert get_after.data["id"] == post_resp.data["id"]
        assert len(get_after.data["citations"]) > 0

    def test_cross_tenant_draft_generation_blocked_with_404(
        self, api_client, tenant_beta, alpha_ticket
    ):
        """Beta agent cannot discover or trigger AI generation for Alpha's ticket."""
        api_client.force_authenticate(user=tenant_beta["agent"])
        response = api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_draft_generation_returns_401(self, api_client, alpha_ticket):
        response = api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# 3. Human-in-the-Loop Review Workflow Tests
# ============================================================================
@pytest.mark.django_db
class TestHumanInTheLoopReviewWorkflow:

    def test_agent_accepts_ai_draft_verbatim_creates_public_ticket_comment(
        self, api_client, tenant_alpha, alpha_ticket, alpha_knowledge_base
    ):
        agent = tenant_alpha["agent"]
        api_client.force_authenticate(user=agent)

        # 1. Generate AI Draft
        gen_resp = api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")
        assert gen_resp.status_code == status.HTTP_201_CREATED
        suggested_reply = gen_resp.data["suggested_reply"]

        # 2. Accept Draft Verbatim
        review_resp = api_client.post(
            f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/review/",
            {"action": "ACCEPT"}
        )
        assert review_resp.status_code == status.HTTP_200_OK
        data = review_resp.data

        assert data["status"] == AIDraftStatus.ACCEPTED
        assert data["final_edited_reply"] == suggested_reply
        assert data["reviewed_by_email"] == agent.email
        assert data["reviewed_at"] is not None

        # 3. Assert TicketComment was dispatched automatically
        comments = TicketComment.objects.filter(ticket=alpha_ticket)
        assert comments.count() == 1
        comment = comments.first()
        assert comment.author == agent
        assert comment.body == suggested_reply
        assert comment.is_internal_note is False

        # 4. Assert ticket state transitioned from OPEN to IN_PROGRESS
        alpha_ticket.refresh_from_db()
        assert alpha_ticket.status == TicketStatus.IN_PROGRESS

    def test_agent_accepts_ai_draft_with_edits_and_internal_note(
        self, api_client, tenant_alpha, alpha_ticket, alpha_knowledge_base
    ):
        agent = tenant_alpha["agent"]
        api_client.force_authenticate(user=agent)

        api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")

        custom_text = (
            "Hi John, I verified your license was unactivated. "
            "I have approved your full refund of $199. It will appear on your card in 3-5 days."
        )

        review_resp = api_client.post(
            f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/review/",
            {
                "action": "ACCEPT",
                "edited_reply": custom_text,
                "is_internal_note": True
            }
        )
        assert review_resp.status_code == status.HTTP_200_OK
        assert review_resp.data["final_edited_reply"] == custom_text

        # Verify comment in database is marked as internal note
        comment = TicketComment.objects.filter(ticket=alpha_ticket).last()
        assert comment.body == custom_text
        assert comment.is_internal_note is True

    def test_agent_rejects_ai_draft_does_not_create_comment(
        self, api_client, tenant_alpha, alpha_ticket, alpha_knowledge_base
    ):
        agent = tenant_alpha["agent"]
        api_client.force_authenticate(user=agent)

        api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")

        review_resp = api_client.post(
            f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/review/",
            {"action": "REJECT"}
        )
        assert review_resp.status_code == status.HTTP_200_OK
        assert review_resp.data["status"] == AIDraftStatus.REJECTED
        assert review_resp.data["reviewed_by_email"] == agent.email

        # Assert NO comment was posted
        assert TicketComment.objects.filter(ticket=alpha_ticket).count() == 0

    def test_review_non_existent_draft_returns_404(self, api_client, tenant_alpha, alpha_ticket):
        api_client.force_authenticate(user=tenant_alpha["agent"])
        response = api_client.post(
            f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/review/",
            {"action": "ACCEPT"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No AI draft found" in response.data["detail"]

    def test_review_with_invalid_action_returns_400(
        self, api_client, tenant_alpha, alpha_ticket, alpha_knowledge_base
    ):
        api_client.force_authenticate(user=tenant_alpha["agent"])
        api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")

        response = api_client.post(
            f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/review/",
            {"action": "INVALID_ACTION"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "action" in response.data

    def test_cross_tenant_review_blocked_with_404(
        self, api_client, tenant_alpha, tenant_beta, alpha_ticket, alpha_knowledge_base
    ):
        # Generate draft in Alpha
        api_client.force_authenticate(user=tenant_alpha["agent"])
        api_client.post(f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/")

        # Attempt review from Beta agent
        api_client.force_authenticate(user=tenant_beta["agent"])
        response = api_client.post(
            f"/api/v1/tickets/{alpha_ticket.id}/ai-draft/review/",
            {"action": "ACCEPT"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
