from typing import Optional

from .manager import ThreeTierVectorManager
from .base import SearchResult


class HybridSearch:
    """Blend semantic + keyword + recency for optimal results."""

    def __init__(
        self,
        vector_manager: ThreeTierVectorManager,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.2,
        recency_weight: float = 0.1,
    ):
        self.manager = vector_manager
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.recency_weight = recency_weight

    async def search(
        self, query: str, source: str = "all", item_type: Optional[str] = None, limit: int = 20
    ) -> list[SearchResult]:
        """Search with hybrid scoring."""
        # Get semantic results (fetch more to allow for re-ranking)
        results = await self.manager.search(query, source, item_type, limit * 2)

        # Apply keyword boost
        query_terms = set(query.lower().split())

        for r in results:
            # Calculate keyword match score
            content_lower = r.content_preview.lower()
            keyword_matches = sum(1 for t in query_terms if t in content_lower)
            keyword_score = keyword_matches / len(query_terms) if query_terms else 0

            # Simple recency boost (could be enhanced with actual timestamps)
            recency_score = 0.1 if r.source == "local" else 0.05

            # Blend scores
            r.score = (
                self.semantic_weight * r.score
                + self.keyword_weight * keyword_score
                + self.recency_weight * recency_score
            )

        # Sort by final blended score and return top N
        return sorted(results, key=lambda x: x.score, reverse=True)[:limit]

    def update_weights(self, semantic_weight: float, keyword_weight: float, recency_weight: float):
        """Update scoring weights."""
        # Normalize weights to sum to 1.0
        total = semantic_weight + keyword_weight + recency_weight
        if total > 0:
            self.semantic_weight = semantic_weight / total
            self.keyword_weight = keyword_weight / total
            self.recency_weight = recency_weight / total
