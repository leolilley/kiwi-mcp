from typing import Optional
import logging
from pathlib import Path

from .manager import ThreeTierVectorManager
from .base import SearchResult
from lilux.config.search_config import SearchConfig
from lilux.utils.search.keyword import KeywordSearchEngine
from lilux.utils.search.keyword import SearchResult as KeywordSearchResult

logger = logging.getLogger(__name__)


class HybridSearch:
    """Blend semantic + keyword + recency for optimal results.

    Supports hybrid search combining:
    - Vector similarity (semantic search)
    - Keyword BM25 scoring
    - Recency/source weighting

    Falls back gracefully when vector search is unavailable.
    """

    def __init__(
        self,
        vector_manager: ThreeTierVectorManager,
        keyword_engine: Optional[KeywordSearchEngine] = None,
        config: Optional[SearchConfig] = None,
    ):
        """Initialize hybrid search.

        Args:
            vector_manager: ThreeTierVectorManager for semantic search
            keyword_engine: Optional KeywordSearchEngine for BM25 scoring
            config: Optional SearchConfig with weights and settings
        """
        self.manager = vector_manager
        self.keyword_engine = keyword_engine
        self.config = config or SearchConfig()

        # Use weights from config
        self.semantic_weight = self.config.vector_weight
        self.keyword_weight = self.config.keyword_weight
        self.recency_weight = self.config.recency_weight

    async def search(
        self, query: str, source: str = "project", item_type: Optional[str] = None, limit: int = 20
    ) -> list[SearchResult]:
        """Search with hybrid scoring blending vector and keyword results.

        Args:
            query: Search query string
            source: Search source ("project", "user", "all")
            item_type: Optional filter by item type
            limit: Maximum results to return

        Returns:
            List of SearchResult sorted by blended score
        """
        # Get vector results if available (fetch more to allow for re-ranking)
        vector_results = {}
        try:
            results = await self.manager.search(query, source, item_type, limit * 2)
            vector_results = {r.item_id: r for r in results}
            logger.debug(f"Vector search returned {len(vector_results)} results")
        except Exception as e:
            logger.warning(f"Vector search failed, falling back to keyword only: {e}")
            vector_results = {}

        # Get keyword results if engine available
        keyword_results = {}
        if self.keyword_engine:
            try:
                kw_results = self.keyword_engine.search(
                    query,
                    item_type=item_type,
                    limit=limit * 2,
                    min_score=self.config.min_score,
                )
                keyword_results = {r.item_id: r for r in kw_results}
                logger.debug(f"Keyword search returned {len(keyword_results)} results")
            except Exception as e:
                logger.warning(f"Keyword search failed: {e}")
                keyword_results = {}

        # Blend results
        blended = self._blend_results(vector_results, keyword_results)

        # Sort by final blended score and return top N
        return sorted(blended, key=lambda x: x.score, reverse=True)[:limit]

    def _blend_results(self, vector_results: dict, keyword_results: dict) -> list[SearchResult]:
        """Blend vector and keyword search results.

        Args:
            vector_results: Dict of item_id -> SearchResult from vector search
            keyword_results: Dict of item_id -> SearchResult from keyword search

        Returns:
            List of blended SearchResult objects
        """
        # Collect all unique items
        all_items = set(vector_results.keys()) | set(keyword_results.keys())

        if not all_items:
            return []

        blended = []

        for item_id in all_items:
            vector_result = vector_results.get(item_id)
            keyword_result = keyword_results.get(item_id)

            # Get base result (prefer vector, fall back to keyword)
            base_result = vector_result or keyword_result

            # Convert keyword result to vector SearchResult if needed
            if not vector_result and keyword_result:
                base_result = self._convert_keyword_result(keyword_result)

            # Calculate normalized scores
            vector_score = vector_result.score if vector_result else 0.0
            keyword_score = keyword_result.score if keyword_result else 0.0

            # Normalize scores to 0-1 range if needed
            # Vector scores are typically 0-1, keyword scores may be higher
            if keyword_score > 1.0:
                keyword_score = min(keyword_score / 10.0, 1.0)  # Rough normalization

            # Calculate recency score (default to project if source not available)
            source = getattr(base_result, "source", "project")
            recency_score = 0.1 if source == "project" else 0.05

            # Blend scores using configured weights
            blended_score = (
                self.semantic_weight * vector_score
                + self.keyword_weight * keyword_score
                + self.recency_weight * recency_score
            )

            # Update result with blended score
            base_result.score = blended_score
            blended.append(base_result)

        return blended

    def _convert_keyword_result(self, kw_result: KeywordSearchResult) -> SearchResult:
        """Convert KeywordSearchEngine result to vector SearchResult.

        Args:
            kw_result: SearchResult from KeywordSearchEngine

        Returns:
            SearchResult compatible with vector search
        """
        # Extract source from metadata if available, otherwise infer from path
        metadata_source = kw_result.metadata.get("source", None)
        if metadata_source is None:
            # Infer from path - if it contains .ai/ it's user, else project
            path_str = str(kw_result.path)
            if ".ai" in path_str and (
                ".ai/user" in path_str or path_str.startswith(str(Path.home()) + "/.ai")
            ):
                source = "user"
            else:
                source = "project"
        else:
            source = metadata_source

        return SearchResult(
            item_id=kw_result.item_id,
            item_type=kw_result.item_type,
            score=kw_result.score,
            content_preview=kw_result.preview,
            metadata=kw_result.metadata,
            source=source,
        )

    def update_weights(
        self,
        semantic_weight: float,
        keyword_weight: float,
        recency_weight: float,
    ):
        """Update scoring weights and normalize to sum to 1.0.

        Args:
            semantic_weight: Weight for vector similarity scores
            keyword_weight: Weight for keyword BM25 scores
            recency_weight: Weight for recency/source scores
        """
        # Normalize weights to sum to 1.0
        total = semantic_weight + keyword_weight + recency_weight
        if total > 0:
            self.semantic_weight = semantic_weight / total
            self.keyword_weight = keyword_weight / total
            self.recency_weight = recency_weight / total

            # Update config if available
            if self.config:
                self.config.vector_weight = self.semantic_weight
                self.config.keyword_weight = self.keyword_weight
                self.config.recency_weight = self.recency_weight

            logger.debug(
                f"Updated weights: semantic={self.semantic_weight:.2f}, "
                f"keyword={self.keyword_weight:.2f}, recency={self.recency_weight:.2f}"
            )

    def set_keyword_engine(self, engine: Optional[KeywordSearchEngine]):
        """Set or update the keyword search engine.

        Args:
            engine: KeywordSearchEngine instance or None to disable keyword search
        """
        self.keyword_engine = engine
        logger.debug(f"Keyword engine {'enabled' if engine else 'disabled'}")
