"""Test local vector store functionality (SQLite-based)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from kiwi_mcp.storage.vector.local import LocalVectorStore
from kiwi_mcp.storage.vector.simple_store import SimpleVectorStore
from kiwi_mcp.storage.vector.base import SearchResult


class TestLocalVectorStore:
    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        service = MagicMock()
        service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
        return service

    def test_init(self, tmp_path, mock_embedding_service):
        """Test initialization."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            collection_name="test_collection",
            embedding_service=mock_embedding_service,
        )

        assert store.storage_path == storage_path
        assert store.collection_name == "test_collection"
        assert store.embedder == mock_embedding_service
        assert storage_path.exists()
        # Check that internal store is initialized
        assert store._store is not None
        assert isinstance(store._store, SimpleVectorStore)

    def test_init_default_params(self, tmp_path):
        """Test initialization with default parameters (no embedder)."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(storage_path)

        # Without embedding service, embedder should be None
        assert store.collection_name == "kiwi_items"
        assert store.embedder is None  # No default embedder anymore

    @pytest.mark.asyncio
    async def test_embed_and_store(self, tmp_path, mock_embedding_service):
        """Test embedding and storing items."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        result = await store.embed_and_store(
            item_id="test_id",
            item_type="directive",
            content="test content",
            metadata={"key": "value"},
            signature="test_sig",
        )

        assert result is True
        mock_embedding_service.embed.assert_called_once_with("test content")

    @pytest.mark.asyncio
    async def test_search(self, tmp_path, mock_embedding_service):
        """Test searching items."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        # Store some items first
        await store.embed_and_store(
            item_id="item1",
            item_type="directive",
            content="content about testing",
            metadata={"name": "test1"},
        )
        await store.embed_and_store(
            item_id="item2",
            item_type="tool",
            content="content about tools",
            metadata={"name": "test2"},
        )

        # Search
        results = await store.search("test query", limit=10)

        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].source == "local"

    @pytest.mark.asyncio
    async def test_search_with_item_type_filter(self, tmp_path, mock_embedding_service):
        """Test search with item_type filter."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        await store.embed_and_store(
            item_id="item1",
            item_type="directive",
            content="content1",
            metadata={},
        )
        await store.embed_and_store(
            item_id="item2",
            item_type="tool",
            content="content2",
            metadata={},
        )

        results = await store.search("query", item_type="directive")

        assert len(results) == 1
        assert results[0].item_type == "directive"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, tmp_path, mock_embedding_service):
        """Test search with empty results."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        results = await store.search("test query")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete(self, tmp_path, mock_embedding_service):
        """Test deleting items."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        await store.embed_and_store(
            item_id="test_id",
            item_type="directive",
            content="test content",
            metadata={},
        )

        assert await store.exists("test_id") is True

        result = await store.delete("test_id")

        assert result is True
        assert await store.exists("test_id") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, tmp_path, mock_embedding_service):
        """Test deleting nonexistent item."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        result = await store.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, tmp_path, mock_embedding_service):
        """Test exists check returns True."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        await store.embed_and_store(
            item_id="test_id",
            item_type="directive",
            content="test content",
            metadata={},
        )

        result = await store.exists("test_id")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, tmp_path, mock_embedding_service):
        """Test exists check returns False."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        result = await store.exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_update(self, tmp_path, mock_embedding_service):
        """Test updating items."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        await store.embed_and_store(
            item_id="test_id",
            item_type="directive",
            content="original content",
            metadata={"version": "1"},
        )

        result = await store.update(
            item_id="test_id",
            content="updated content",
            metadata={"version": "2"},
        )

        assert result is True

    def test_get_stats(self, tmp_path, mock_embedding_service):
        """Test getting store statistics."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            embedding_service=mock_embedding_service
        )

        stats = store.get_stats()

        assert "total" in stats
        assert "by_type" in stats
        assert "db_path" in stats
        assert stats["total"] == 0


class TestSimpleVectorStore:
    """Test the underlying SimpleVectorStore directly."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        service = MagicMock()
        service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
        return service

    def test_init_creates_db(self, tmp_path, mock_embedding_service):
        """Test that initialization creates the database."""
        storage_path = tmp_path / "vector_store"

        store = SimpleVectorStore(
            storage_path=storage_path,
            collection_name="test",
            embedding_service=mock_embedding_service,
        )

        db_path = storage_path / "test.db"
        assert db_path.exists()

    @pytest.mark.asyncio
    async def test_embed_and_store_no_embedder(self, tmp_path):
        """Test that embed_and_store fails without embedder."""
        storage_path = tmp_path / "vector_store"

        store = SimpleVectorStore(
            storage_path=storage_path,
            collection_name="test",
            embedding_service=None,
        )

        with pytest.raises(RuntimeError, match="Embedding service not configured"):
            await store.embed_and_store(
                item_id="test",
                item_type="directive",
                content="test",
                metadata={},
            )

    @pytest.mark.asyncio
    async def test_search_no_embedder(self, tmp_path):
        """Test that search fails without embedder."""
        storage_path = tmp_path / "vector_store"

        store = SimpleVectorStore(
            storage_path=storage_path,
            collection_name="test",
            embedding_service=None,
        )

        with pytest.raises(RuntimeError, match="Embedding service not configured"):
            await store.search("query")
