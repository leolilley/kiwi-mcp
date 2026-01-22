"""Test hybrid search functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from kiwi_mcp.storage.vector.hybrid import HybridSearch
from kiwi_mcp.storage.vector.base import SearchResult


class TestHybridSearch:
    @pytest.fixture
    def mock_vector_manager(self):
        """Create a mock vector manager."""
        manager = MagicMock()
        manager.search = AsyncMock()
        return manager

    @pytest.fixture
    def sample_results(self):
        """Create sample search results."""
        return [
            SearchResult(
                item_id="item1",
                item_type="directive",
                score=0.8,
                content_preview="test content with keyword match",
                metadata={"key": "value"},
                source="local",
            ),
            SearchResult(
                item_id="item2",
                item_type="script",
                score=0.6,
                content_preview="different content here",
                metadata={"key": "value2"},
                source="registry",
            ),
        ]

    def test_init(self, mock_vector_manager):
        """Test initialization."""
        hybrid = HybridSearch(mock_vector_manager)

        assert hybrid.manager == mock_vector_manager
        assert hybrid.semantic_weight == 0.7
        assert hybrid.keyword_weight == 0.2
        assert hybrid.recency_weight == 0.1

    def test_init_custom_weights(self, mock_vector_manager):
        """Test initialization with custom weights."""
        hybrid = HybridSearch(
            mock_vector_manager, semantic_weight=0.5, keyword_weight=0.3, recency_weight=0.2
        )

        assert hybrid.semantic_weight == 0.5
        assert hybrid.keyword_weight == 0.3
        assert hybrid.recency_weight == 0.2

    @pytest.mark.asyncio
    async def test_search(self, mock_vector_manager, sample_results):
        """Test hybrid search with score blending."""
        mock_vector_manager.search.return_value = sample_results

        hybrid = HybridSearch(mock_vector_manager)

        results = await hybrid.search(
            query="test keyword", source="all", item_type="directive", limit=10
        )

        assert len(results) == 2
        mock_vector_manager.search.assert_called_once_with(
            "test keyword",
            "all",
            "directive",
            20,  # limit * 2
        )

        # Check that scores were modified (keyword boost + recency)
        # First result should have higher score due to keyword match + local source
        assert results[0].score > 0.8  # Original + keyword + recency boost
        assert results[1].score < results[0].score

    @pytest.mark.asyncio
    async def test_search_keyword_boosting(self, mock_vector_manager):
        """Test keyword matching boost."""
        results = [
            SearchResult(
                item_id="item1",
                item_type="directive",
                score=0.5,
                content_preview="python script automation",
                metadata={},
                source="local",
            )
        ]
        mock_vector_manager.search.return_value = results

        hybrid = HybridSearch(mock_vector_manager)

        # Query with keywords that match content
        final_results = await hybrid.search("python automation")

        # Score should be boosted due to keyword matches
        assert final_results[0].score > 0.5
        # Should get boost for both "python" and "automation" matches

    def test_update_weights(self, mock_vector_manager):
        """Test updating weights."""
        hybrid = HybridSearch(mock_vector_manager)

        hybrid.update_weights(0.6, 0.3, 0.1)

        # Weights should be normalized
        assert hybrid.semantic_weight == 0.6
        assert hybrid.keyword_weight == 0.3
        assert hybrid.recency_weight == 0.1

    def test_update_weights_normalization(self, mock_vector_manager):
        """Test weight normalization."""
        hybrid = HybridSearch(mock_vector_manager)

        # Weights that don't sum to 1
        hybrid.update_weights(1.0, 1.0, 1.0)

        # Should be normalized to sum to 1
        assert abs(hybrid.semantic_weight - 1 / 3) < 0.001
        assert abs(hybrid.keyword_weight - 1 / 3) < 0.001
        assert abs(hybrid.recency_weight - 1 / 3) < 0.001

    def test_update_weights_zero_total(self, mock_vector_manager):
        """Test handling of zero total weights."""
        hybrid = HybridSearch(mock_vector_manager)
        original_weights = (hybrid.semantic_weight, hybrid.keyword_weight, hybrid.recency_weight)

        hybrid.update_weights(0.0, 0.0, 0.0)

        # Weights should remain unchanged when total is 0
        assert hybrid.semantic_weight == original_weights[0]
        assert hybrid.keyword_weight == original_weights[1]
        assert hybrid.recency_weight == original_weights[2]
