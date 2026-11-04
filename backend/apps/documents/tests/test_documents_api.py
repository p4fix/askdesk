import io
import math
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import Organization, User, UserRole
from apps.documents.models import Document, DocumentChunk, DocumentFileType, DocumentStatus
from apps.documents.services.chunking import RecursiveCharacterTextSplitter
from apps.documents.services.embedding import MockEmbeddingService

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

def make_sample_pdf_bytes(text="Hello from AskDesk Knowledge Base"):
    """Generates a minimal valid single-page PDF with text stream for test extraction."""
    stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET".encode('ascii')
    stream_len = len(stream_content)
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {stream_len} >> stream
BT
/F1 12 Tf
72 712 Td
({text}) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000350 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
426
%%EOF"""
    return pdf.encode('latin-1')


@pytest.mark.django_db
class TestDocumentUploadAndIngestion:
    def test_admin_can_upload_txt_document_and_triggers_chunking(self, api_client, tenant_alpha):
        admin = tenant_alpha["admin"]
        api_client.force_authenticate(user=admin)

        sample_text = (
            "AskDesk Company Policy - Refund Terms\n\n"
            "Customers may request a full refund within 30 days of initial purchase. "
            "To qualify, the account must be in good standing and usage under 100 API units.\n\n"
            "Exceptions apply to enterprise annual contracts, which require 60 days written notice."
        )
        uploaded_file = SimpleUploadedFile("refund_policy.txt", sample_text.encode("utf-8"), content_type="text/plain")

        response = api_client.post(
            "/api/v1/documents/upload/",
            {"file": uploaded_file, "title": "Refund Policy 2026"},
            format="multipart"
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert data["title"] == "Refund Policy 2026"
        assert data["file_type"] == DocumentFileType.TXT
        assert data["status"] == DocumentStatus.PROCESSED
        assert data["chunks_count"] > 0
        assert len(data["chunks"]) > 0

        # Verify DocumentChunk in DB
        first_chunk = DocumentChunk.objects.filter(document_id=data["id"]).first()
        assert first_chunk is not None
        assert "Refund Terms" in first_chunk.content
        assert first_chunk.token_count > 0
        assert first_chunk.embedding is not None
        assert len(first_chunk.embedding) == 1536
        assert first_chunk.metadata.get("page") == 1

    def test_admin_can_upload_pdf_document_and_extracts_pages(self, api_client, tenant_alpha):
        admin = tenant_alpha["admin"]
        api_client.force_authenticate(user=admin)

        pdf_bytes = make_sample_pdf_bytes("Standard Operating Procedure for Server Outages")
        uploaded_file = SimpleUploadedFile("sop_servers.pdf", pdf_bytes, content_type="application/pdf")

        response = api_client.post(
            "/api/v1/documents/upload/",
            {"file": uploaded_file, "title": "SOP Server Outages"},
            format="multipart"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == DocumentStatus.PROCESSED
        assert response.data["file_type"] == DocumentFileType.PDF
        assert response.data["chunks_count"] >= 1

        chunk = DocumentChunk.objects.filter(document_id=response.data["id"]).first()
        assert chunk is not None
        assert "Operating Procedure" in chunk.content
        assert chunk.metadata.get("page") == 1

    def test_support_agent_cannot_upload_document(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent"]
        api_client.force_authenticate(user=agent)

        uploaded_file = SimpleUploadedFile("unauthorized.txt", b"Agent text", content_type="text/plain")
        response = api_client.post(
            "/api/v1/documents/upload/",
            {"file": uploaded_file, "title": "Agent Upload"},
            format="multipart"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_unsupported_file_extension_fails(self, api_client, tenant_alpha):
        admin = tenant_alpha["admin"]
        api_client.force_authenticate(user=admin)

        uploaded_file = SimpleUploadedFile("script.sh", b"echo hello", content_type="application/x-sh")
        response = api_client.post(
            "/api/v1/documents/upload/",
            {"file": uploaded_file, "title": "Shell script"},
            format="multipart"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data

    def test_empty_document_marks_status_failed(self, api_client, tenant_alpha):
        admin = tenant_alpha["admin"]
        api_client.force_authenticate(user=admin)

        uploaded_file = SimpleUploadedFile("empty.txt", b"   ", content_type="text/plain")
        response = api_client.post(
            "/api/v1/documents/upload/",
            {"file": uploaded_file, "title": "Empty File"},
            format="multipart"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == DocumentStatus.FAILED
        assert response.data["error_message"] is not None


@pytest.mark.django_db
class TestDocumentListingAndFiltering:
    def test_strict_multi_tenant_isolation_in_documents(self, api_client, tenant_alpha, tenant_beta):
        alpha_admin = tenant_alpha["admin"]
        beta_admin = tenant_beta["admin"]

        doc_alpha = Document.objects.create(
            organization=tenant_alpha["org"],
            uploaded_by=alpha_admin,
            title="Alpha Confidential Internal Handbook",
            file_type=DocumentFileType.TXT,
            status=DocumentStatus.PROCESSED
        )
        doc_beta = Document.objects.create(
            organization=tenant_beta["org"],
            uploaded_by=beta_admin,
            title="Beta Secret Roadmap",
            file_type=DocumentFileType.TXT,
            status=DocumentStatus.PROCESSED
        )

        api_client.force_authenticate(user=alpha_admin)
        response = api_client.get("/api/v1/documents/")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data
        doc_ids = [d["id"] for d in results]
        assert str(doc_alpha.id) in doc_ids
        assert str(doc_beta.id) not in doc_ids

    def test_support_agent_can_list_and_view_documents_in_own_org(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent"]
        admin = tenant_alpha["admin"]

        doc = Document.objects.create(
            organization=tenant_alpha["org"],
            uploaded_by=admin,
            title="Agent Viewable Handbook",
            file_type=DocumentFileType.TXT,
            status=DocumentStatus.PROCESSED
        )

        api_client.force_authenticate(user=agent)
        response = api_client.get("/api/v1/documents/")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data
        assert any(d["id"] == str(doc.id) for d in results)

    def test_filter_by_status_and_search(self, api_client, tenant_alpha):
        admin = tenant_alpha["admin"]
        org = tenant_alpha["org"]

        Document.objects.create(organization=org, uploaded_by=admin, title="Billing Guidelines", file_type=DocumentFileType.TXT, status=DocumentStatus.PROCESSED)
        Document.objects.create(organization=org, uploaded_by=admin, title="Failed Upload", file_type=DocumentFileType.TXT, status=DocumentStatus.FAILED)

        api_client.force_authenticate(user=admin)

        # Filter by status
        res_status = api_client.get("/api/v1/documents/?status=PROCESSED")
        data_status = res_status.data["results"] if "results" in res_status.data else res_status.data
        assert len(data_status) == 1
        assert data_status[0]["status"] == DocumentStatus.PROCESSED

        # Search by keyword
        res_search = api_client.get("/api/v1/documents/?search=Billing")
        data_search = res_search.data["results"] if "results" in res_search.data else res_search.data
        assert len(data_search) == 1
        assert "Billing" in data_search[0]["title"]


@pytest.mark.django_db
class TestDocumentDetailAndDeletion:
    def test_retrieve_document_detail_with_chunks(self, api_client, tenant_alpha):
        admin = tenant_alpha["admin"]
        org = tenant_alpha["org"]
        doc = Document.objects.create(
            organization=org,
            uploaded_by=admin,
            title="API Specification",
            file_type=DocumentFileType.TXT,
            status=DocumentStatus.PROCESSED
        )
        DocumentChunk.objects.create(
            document=doc,
            organization=org,
            chunk_index=0,
            content="Endpoint /v1/auth documentation",
            token_count=4,
            embedding=[0.0] * 1536
        )

        api_client.force_authenticate(user=admin)
        response = api_client.get(f"/api/v1/documents/{doc.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(doc.id)
        assert response.data["chunks_count"] == 1
        assert len(response.data["chunks"]) == 1
        assert response.data["chunks"][0]["content"] == "Endpoint /v1/auth documentation"

    def test_cross_tenant_document_detail_returns_404(self, api_client, tenant_alpha, tenant_beta):
        alpha_admin = tenant_alpha["admin"]
        beta_admin = tenant_beta["admin"]

        beta_doc = Document.objects.create(
            organization=tenant_beta["org"],
            uploaded_by=beta_admin,
            title="Beta Private Doc",
            file_type=DocumentFileType.TXT
        )

        api_client.force_authenticate(user=alpha_admin)
        response = api_client.get(f"/api/v1/documents/{beta_doc.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_delete_document_and_cascades_chunks(self, api_client, tenant_alpha):
        admin = tenant_alpha["admin"]
        org = tenant_alpha["org"]

        doc = Document.objects.create(
            organization=org,
            uploaded_by=admin,
            title="Document to Delete",
            file_type=DocumentFileType.TXT
        )
        chunk1 = DocumentChunk.objects.create(
            document=doc,
            organization=org,
            chunk_index=0,
            content="Chunk 1",
            token_count=2,
            embedding=[0.0] * 1536
        )
        chunk2 = DocumentChunk.objects.create(
            document=doc,
            organization=org,
            chunk_index=1,
            content="Chunk 2",
            token_count=2,
            embedding=[0.0] * 1536
        )

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f"/api/v1/documents/{doc.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Document.objects.filter(id=doc.id).exists()
        # Verify chunks cascaded
        assert not DocumentChunk.objects.filter(id=chunk1.id).exists()
        assert not DocumentChunk.objects.filter(id=chunk2.id).exists()

    def test_support_agent_cannot_delete_document(self, api_client, tenant_alpha):
        agent = tenant_alpha["agent"]
        admin = tenant_alpha["admin"]

        doc = Document.objects.create(
            organization=tenant_alpha["org"],
            uploaded_by=admin,
            title="Protected Document",
            file_type=DocumentFileType.TXT
        )

        api_client.force_authenticate(user=agent)
        response = api_client.delete(f"/api/v1/documents/{doc.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestChunkingAndEmbeddingServices:
    def test_recursive_character_splitter_splits_text(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        long_text = (
            "Paragraph one provides essential context regarding company account setup. "
            "Paragraph two delves into billing thresholds, invoicing schedules, and payment terms. "
            "Paragraph three covers support escalations and resolution timelines."
        )
        chunks = splitter.split_text(long_text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 120

    def test_mock_embedding_service_unit_vectors(self):
        svc = MockEmbeddingService()
        vec = svc.generate_embedding("Customer refund policy")
        assert len(vec) == 1536
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 0.01

        # Deterministic assertion
        vec2 = svc.generate_embedding("Customer refund policy")
        assert vec == vec2

