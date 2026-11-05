from typing import Optional
from django.db import transaction

from apps.rag.models import AIDraftCitation, AIDraftResponse, AIDraftStatus
from apps.rag.services.llm import BaseLLMService, get_llm_service
from apps.rag.services.retrieval import VectorSearchService
from apps.tickets.models import Ticket

class RAGOrchestrator:
    """
    Coordinates the end-to-end RAG pipeline for customer tickets:
      1. Synthesizes search query from ticket title & description.
      2. Executes multi-tenant vector similarity search over processed DocumentChunks.
      3. Passes bounded context to LLM service with anti-hallucination guardrails.
      4. Persists AIDraftResponse and AIDraftCitation entities within an atomic transaction.
    """

    def __init__(
        self,
        vector_search: Optional[VectorSearchService] = None,
        llm_service: Optional[BaseLLMService] = None
    ):
        self.vector_search = vector_search or VectorSearchService()
        self.llm_service = llm_service or get_llm_service()

    def generate_draft_for_ticket(
        self,
        ticket: Ticket,
        top_k: int = 3,
        min_similarity: float = 0.05
    ) -> AIDraftResponse:
        """
        Executes vector search and grounded LLM generation for a support ticket.
        Returns the saved AIDraftResponse instance.
        """
        # 1. Synthesize query text
        query = f"{ticket.title}\n{ticket.description}".strip()

        # 2. Retrieve top-k semantic chunks scoped strictly to the ticket's tenant
        matched_chunks = self.vector_search.search(
            query=query,
            organization_id=ticket.organization_id,
            top_k=top_k,
            min_similarity=min_similarity
        )

        # 3. Generate grounded response via LLM service
        result = self.llm_service.generate_draft(
            ticket_title=ticket.title,
            ticket_description=ticket.description,
            context_chunks=matched_chunks
        )

        # 4. Atomically persist draft response and citations
        with transaction.atomic():
            draft = AIDraftResponse.objects.create(
                ticket=ticket,
                organization=ticket.organization,
                suggested_reply=result['reply'],
                model_name=result['model_name'],
                confidence_score=result['confidence_score'],
                status=AIDraftStatus.DRAFT_GENERATED
            )

            cited_chunks = result.get('cited_chunks', [])
            citations = [
                AIDraftCitation(
                    draft_response=draft,
                    chunk=chunk_meta['chunk'],
                    relevance_score=chunk_meta['similarity'],
                    cited_excerpt=chunk_meta['content'][:500],
                    source_title=chunk_meta['document_title'],
                    page_number=chunk_meta['page_number']
                )
                for chunk_meta in cited_chunks
            ]
            if citations:
                AIDraftCitation.objects.bulk_create(citations)

        return draft
