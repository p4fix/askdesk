import hashlib
import json
import math
import os
import random
import urllib.request
from abc import ABC, abstractmethod
from typing import List

class BaseEmbeddingService(ABC):
    """Abstract interface for text embedding models."""
    dimensions: int = 1536

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate a 1536-dimensional embedding vector for a single string."""
        pass

    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of strings."""
        pass


class MockEmbeddingService(BaseEmbeddingService):
    """
    Deterministic pseudo-vector generator for local development and SDET test suites.
    Produces valid 1536-dimensional L2-normalized unit vectors without external network calls.
    - Identical inputs yield identical vectors.
    - Texts sharing vocabulary produce positive cosine similarity.
    """
    dimensions: int = 1536

    def _generate_vector_for_text(self, text: str) -> List[float]:
        if not text:
            # Zero vector for blank input
            return [0.0] * self.dimensions

        # Base seed from full text digest
        digest = hashlib.sha256(text.strip().lower().encode('utf-8')).hexdigest()
        seed_int = int(digest[:16], 16)
        rng = random.Random(seed_int)

        # Generate base random vector
        vec = [rng.gauss(0, 1) for _ in range(self.dimensions)]

        # Vocabulary bias: add signal based on word tokens
        words = text.lower().split()
        for word in set(words):
            word_hash = int(hashlib.md5(word.encode('utf-8')).hexdigest()[:8], 16)
            idx = word_hash % self.dimensions
            vec[idx] += 2.0

        # L2 Normalize: sqrt(sum(v_i^2)) = 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    def generate_embedding(self, text: str) -> List[float]:
        return self._generate_vector_for_text(text)

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector_for_text(t) for t in texts]


class OpenAIEmbeddingService(BaseEmbeddingService):
    """
    Production embedding service utilizing OpenAI's text-embedding-3-small (1536 dimensions).
    Uses standard library urllib for zero external SDK overhead.
    """
    dimensions: int = 1536
    API_URL = "https://api.openai.com/v1/embeddings"

    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be configured to use OpenAIEmbeddingService.")
        self.model = model

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        payload = json.dumps({
            "input": texts,
            "model": self.model
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

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings

    def generate_embedding(self, text: str) -> List[float]:
        return self.generate_embeddings_batch([text])[0]


def get_embedding_service() -> BaseEmbeddingService:
    """
    Factory resolving the active embedding provider based on environment configuration.
    Defaults to MockEmbeddingService for zero-dependency local testing.
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").lower().strip()
    api_key = os.getenv("OPENAI_API_KEY")

    if provider == "openai" and api_key:
        return OpenAIEmbeddingService(api_key=api_key)
    return MockEmbeddingService()

