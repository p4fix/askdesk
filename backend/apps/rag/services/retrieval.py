import json
import math
from typing import Any, Dict, List
from django.db import connection

from apps.documents.models import DocumentChunk, DocumentStatus
from apps.documents.services.embedding import get_embedding_service

class VectorSearchService:
    """
    Multi-tenant vector similarity retrieval engine.
    Applies strict tenant scoping (organization_id) alongside cosine similarity search.
    Provides dual-database execution:
      - PostgreSQL: High-speed HNSW index query using pgvector CosineDistance.
      - SQLite / Test fallback: In-memory vectorized cosine similarity.
    """

    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service or get_embedding_service()

    @staticmethod
    def _parse_vector(vec: Any) -> List[float]:
        """Safely parses vector storage representations into a float list."""
        if isinstance(vec, (list, tuple)):
            return [float(x) for x in vec]
        if hasattr(vec, 'tolist'):
            return [float(x) for x in vec.tolist()]
        if isinstance(vec, str):
            try:
                parsed = json.loads(vec)
                return [float(x) for x in parsed]
            except Exception:
                cleaned = vec.strip('[] \t\n\r')
                if not cleaned:
                    return []
                return [float(x.strip()) for x in cleaned.split(',') if x.strip()]
        return []

    @classmethod
    def _calculate_cosine_similarity(cls, v1: List[float], v2: Any) -> float:
        """Calculates cosine similarity between two vectors: (u . v) / (||u|| * ||v||)."""
        vec2 = cls._parse_vector(v2)
        if not v1 or not vec2 or len(v1) != len(vec2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, vec2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 <= 0.0 or norm2 <= 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    def search(
        self,
        query: str,
        organization_id: Any,
        top_k: int = 3,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic cosine similarity search scoped strictly to the specified tenant.
        Returns top_k most relevant chunks exceeding min_similarity.
        """
        if not query or not query.strip():
            return []

        # 1. Embed query using active embedding model (1536 dimensions)
        query_vector = self.embedding_service.generate_embedding(query.strip())
        if not query_vector:
            return []

        # 2. Strict tenant scoping: Only search processed documents belonging to organization
        chunks_qs = DocumentChunk.objects.filter(
            organization_id=organization_id,
            document__status=DocumentStatus.PROCESSED
        ).select_related('document')

        # 3. Database execution path
        if connection.vendor == 'postgresql':
            from pgvector.django import CosineDistance
            # CosineDistance: range [0, 2], where 0 = identical. Cosine similarity = 1 - distance
            results = chunks_qs.annotate(
                distance=CosineDistance('embedding', query_vector)
            ).order_by('distance')[:top_k]

            matches = []
            for chunk in results:
                distance = chunk.distance if chunk.distance is not None else 1.0
                similarity = round(max(0.0, 1.0 - distance), 4)
                if similarity >= min_similarity:
                    page_num = chunk.metadata.get('page', 1) if isinstance(chunk.metadata, dict) else 1
                    matches.append({
                        'chunk': chunk,
                        'similarity': similarity,
                        'document_title': chunk.document.title,
                        'page_number': page_num,
                        'content': chunk.content,
                    })
            return matches
        else:
            # SQLite / Test fallback: In-memory cosine similarity
            candidate_chunks = list(chunks_qs)
            scored = []
            for chunk in candidate_chunks:
                if not chunk.embedding:
                    continue
                similarity = round(self._calculate_cosine_similarity(query_vector, chunk.embedding), 4)
                if similarity >= min_similarity:
                    page_num = chunk.metadata.get('page', 1) if isinstance(chunk.metadata, dict) else 1
                    scored.append({
                        'chunk': chunk,
                        'similarity': similarity,
                        'document_title': chunk.document.title,
                        'page_number': page_num,
                        'content': chunk.content,
                    })
            scored.sort(key=lambda x: x['similarity'], reverse=True)
            return scored[:top_k]
