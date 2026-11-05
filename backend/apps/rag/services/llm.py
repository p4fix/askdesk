import json
import os
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseLLMService(ABC):
    """Abstract interface for LLM response generators."""
    model_name: str = "base-llm"

    @abstractmethod
    def generate_draft(
        self,
        ticket_title: str,
        ticket_description: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Synthesizes a customer-facing support reply grounded strictly in provided context chunks.
        Returns a dictionary with 'reply', 'model_name', 'confidence_score', and 'cited_chunks'.
        """
        pass


class MockLLMService(BaseLLMService):
    """
    Deterministic LLM simulator for offline development and CI/CD SDET testing.
    Produces repeatable grounded responses with structured citation tags without network calls.
    Enforces anti-hallucination fallback when no context is provided or confidence is low.
    """
    model_name: str = "mock-gpt-4o-mini"
    FALLBACK_MESSAGE: str = (
        "I do not have enough documentation to answer this question. "
        "Please reach out to our human support team for further assistance."
    )

    def generate_draft(
        self,
        ticket_title: str,
        ticket_description: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # 1. Anti-hallucination check: Empty chunks or zero relevance
        if not context_chunks or context_chunks[0]['similarity'] < 0.05:
            return {
                "reply": self.FALLBACK_MESSAGE,
                "model_name": self.model_name,
                "confidence_score": round(context_chunks[0]['similarity'], 4) if context_chunks else 0.0,
                "cited_chunks": []
            }

        # 2. Grounded response formatting with structured citations
        top_chunk = context_chunks[0]
        citations_summary = "\n".join([
            f"- [Doc: {c['document_title']}, Page: {c['page_number']}] \"{c['content'][:120].strip()}...\""
            for c in context_chunks
        ])

        reply_body = (
            f"Hello,\n\n"
            f"Thank you for contacting support regarding \"{ticket_title}\".\n\n"
            f"Based on our official documentation ({top_chunk['document_title']}):\n"
            f"{top_chunk['content'].strip()}\n\n"
            f"Sources:\n"
            f"{citations_summary}\n\n"
            f"Please let us know if you need any additional clarification."
        )

        return {
            "reply": reply_body,
            "model_name": self.model_name,
            "confidence_score": round(top_chunk['similarity'], 4),
            "cited_chunks": context_chunks
        }


class OpenAILLMService(BaseLLMService):
    """
    Production LLM client utilizing OpenAI Chat Completions API with strict context bounding.
    Uses standard library urllib for zero third-party dependency.
    """
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be configured to use OpenAILLMService.")
        self.model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _build_context_prompt(self, context_chunks: List[Dict[str, Any]]) -> str:
        if not context_chunks:
            return "No relevant documentation chunks were found in the knowledge base."

        formatted_chunks = []
        for idx, chunk in enumerate(context_chunks, 1):
            formatted_chunks.append(
                f"--- Context Chunk #{idx} ---\n"
                f"Document: {chunk['document_title']}\n"
                f"Page: {chunk['page_number']}\n"
                f"Content: {chunk['content']}\n"
            )
        return "\n".join(formatted_chunks)

    def generate_draft(
        self,
        ticket_title: str,
        ticket_description: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        system_instruction = (
            "You are an expert customer support AI assistant for an enterprise helpdesk.\n"
            "Answer the customer's support inquiry strictly and solely based on the provided Knowledge Base context chunks below.\n"
            "If the context chunks do not contain sufficient factual evidence to answer the inquiry, state clearly:\n"
            "'I do not have enough documentation to answer this question. Please reach out to our human support team for further assistance.'\n"
            "Never extrapolate, fabricate policies, or assume information outside the provided context chunks.\n"
            "For every factual statement or policy cited, reference the source using the exact format: [Doc: <Document Title>, Page: <Page Number>].\n"
            "Maintain a courteous, professional, and empathetic tone."
        )

        context_text = self._build_context_prompt(context_chunks)
        user_message = (
            f"Customer Ticket Title: {ticket_title}\n\n"
            f"Customer Problem Description:\n{ticket_description}\n\n"
            f"Knowledge Base Documentation Context:\n{context_text}"
        )

        payload = json.dumps({
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"].strip()

        confidence = round(context_chunks[0]['similarity'], 4) if context_chunks else 0.0

        return {
            "reply": reply,
            "model_name": self.model_name,
            "confidence_score": confidence,
            "cited_chunks": context_chunks if "I do not have enough documentation" not in reply else []
        }


def get_llm_service() -> BaseLLMService:
    """
    Factory resolving active LLM generator provider based on environment configuration.
    Defaults to MockLLMService for zero-dependency local development and test runs.
    """
    provider = os.getenv("LLM_PROVIDER", "mock").lower().strip()
    api_key = os.getenv("OPENAI_API_KEY")

    if provider == "openai" and api_key:
        return OpenAILLMService(api_key=api_key)
    return MockLLMService()
