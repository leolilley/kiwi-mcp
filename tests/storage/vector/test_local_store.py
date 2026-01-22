"""Test local vector store functionality."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from kiwi_mcp.storage.vector.local import LocalVectorStore
from kiwi_mcp.storage.vector.base import SearchResult


class TestLocalVectorStore:
    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock embedding model."""
        model = MagicMock()
        model.embed.return_value = [0.1, 0.2, 0.3, 0.4]
        return model

    def test_init(self, tmp_path, mock_embedding_model):
        """Test initialization."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(
            storage_path=storage_path,
            collection_name="test_collection",
            embedding_model=mock_embedding_model,
        )

        assert store.storage_path == storage_path
        assert store.collection_name == "test_collection"
        assert store.embedder == mock_embedding_model
        assert store._client is None
        assert store._collection is None
        assert storage_path.exists()

    def test_init_default_params(self, tmp_path):
        """Test initialization with default parameters."""
        storage_path = tmp_path / "vector_store"

        store = LocalVectorStore(storage_path)

        assert store.collection_name == "kiwi_items"
        assert store.embedder is not None
        assert store.embedder.model_name == "all-MiniLM-L6-v2"

    @patch("kiwi_mcp.storage.vector.local.chromadb")
    def test_get_client_success(self, mock_chromadb, tmp_path):
        """Test successful client creation."""
        storage_path = tmp_path / "vector_store"
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client

        store = LocalVectorStore(storage_path)
        client = store._get_client()

        assert client == mock_client
        assert store._client == mock_client
        mock_chromadb.Client.assert_called_once()

        # Second call should return cached client
        client2 = store._get_client()
        assert client2 == mock_client
        # Still only called once
        assert mock_chromadb.Client.call_count == 1

    def test_get_client_missing_dependency(self, tmp_path):
        """Test handling of missing chromadb dependency."""
        storage_path = tmp_path / "vector_store"
        store = LocalVectorStore(storage_path)

        with patch("kiwi_mcp.storage.vector.local.chromadb", side_effect=ImportError):
            with pytest.raises(ImportError) as exc_info:
                store._get_client()

            assert "chromadb is required" in str(exc_info.value)

    @patch("kiwi_mcp.storage.vector.local.chromadb")
    def test_get_collection(self, mock_chromadb, tmp_path, mock_embedding_model):
        """Test collection creation."""
        storage_path = tmp_path / "vector_store"
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        store = LocalVectorStore(
            storage_path=storage_path,
            collection_name="test_collection",
            embedding_model=mock_embedding_model,
        )

        collection = store._get_collection()

        assert collection == mock_collection
        assert store._collection == mock_collection
        mock_client.get_or_create_collection.assert_called_once_with(
            name="test_collection", metadata={"hnsw:space": "cosine"}
        )

    @pytest.mark.asyncio
    async def test_embed_and_store(self, tmp_path, mock_embedding_model):
        """Test embedding and storing items."""
        storage_path = tmp_path / "vector_store"

        with patch("kiwi_mcp.storage.vector.local.chromadb"):
            store = LocalVectorStore(storage_path, embedding_model=mock_embedding_model)

            # Mock collection
            mock_collection = MagicMock()
            store._collection = mock_collection

            result = await store.embed_and_store(
                item_id="test_id",
                item_type="directive",
                content="test content",
                metadata={"key": "value"},
                signature="test_sig",
            )

            assert result is True
            mock_embedding_model.embed.assert_called_once_with("test content")
            mock_collection.upsert.assert_called_once_with(
                ids=["test_id"],
                embeddings=[[0.1, 0.2, 0.3, 0.4]],
                documents=["test content"],
                metadatas=[{"item_type": "directive", "signature": "test_sig", "key": "value"}],
            )

    @pytest.mark.asyncio
    async def test_search(self, tmp_path, mock_embedding_model):
        """Test searching items."""
        storage_path = tmp_path / "vector_store"

        with patch("kiwi_mcp.storage.vector.local.chromadb"):
            store = LocalVectorStore(storage_path, embedding_model=mock_embedding_model)

            # Mock collection and search results
            mock_collection = MagicMock()
            store._collection = mock_collection

            mock_collection.query.return_value = {
                "ids": [["item1", "item2"]],
                "distances": [[0.1, 0.3]],
                "documents": [["content1", "content2"]],
                "metadatas": [
                    [
                        {"item_type": "directive", "key": "value1"},
                        {"item_type": "script", "key": "value2"},
                    ]
                ],
            }

            results = await store.search("test query", limit=10, item_type="directive")

            assert len(results) == 2
            assert isinstance(results[0], SearchResult)
            assert results[0].item_id == "item1"
            assert results[0].item_type == "directive"
            assert results[0].score == 0.9  # 1 - 0.1
            assert results[0].content_preview == "content1"
            assert results[0].source == "local"

            mock_embedding_model.embed.assert_called_once_with("test query")
            mock_collection.query.assert_called_once_with(
                query_embeddings=[[0.1, 0.2, 0.3, 0.4]],
                n_results=10,
                where={"item_type": "directive"},
            )

    @pytest.mark.asyncio
    async def test_search_empty_results(self, tmp_path, mock_embedding_model):
        """Test search with empty results."""
        storage_path = tmp_path / "vector_store"

        with patch("kiwi_mcp.storage.vector.local.chromadb"):
            store = LocalVectorStore(storage_path, embedding_model=mock_embedding_model)

            # Mock collection with empty results
            mock_collection = MagicMock()
            store._collection = mock_collection
            mock_collection.query.return_value = {
                "ids": [[]],
                "distances": [[]],
                "documents": [[]],
                "metadatas": [[]],
            }

            results = await store.search("test query")

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete(self, tmp_path, mock_embedding_model):
        """Test deleting items."""
        storage_path = tmp_path / "vector_store"

        with patch("kiwi_mcp.storage.vector.local.chromadb"):
            store = LocalVectorStore(storage_path, embedding_model=mock_embedding_model)

            mock_collection = MagicMock()
            store._collection = mock_collection

            result = await store.delete("test_id")

            assert result is True
            mock_collection.delete.assert_called_once_with(ids=["test_id"])

    @pytest.mark.asyncio
    async def test_delete_error(self, tmp_path, mock_embedding_model):
        """Test delete error handling."""
        storage_path = tmp_path / "vector_store"

        with patch("kiwi_mcp.storage.vector.local.chromadb"):
            store = LocalVectorStore(storage_path, embedding_model=mock_embedding_model)

            mock_collection = MagicMock()
            mock_collection.delete.side_effect = Exception("Delete failed")
            store._collection = mock_collection

            result = await store.delete("test_id")

            assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, tmp_path, mock_embedding_model):
        """Test exists check returns True."""
        storage_path = tmp_path / "vector_store"

        with patch("kiwi_mcp.storage.vector.local.chromadb"):
            store = LocalVectorStore(storage_path, embedding_model=mock_embedding_model)

            mock_collection = MagicMock()
            mock_collection.get.return_value = {"ids": ["test_id"]}
            store._collection = mock_collection

            result = await store.exists("test_id")

            assert result is True
            mock_collection.get.assert_called_once_with(ids=["test_id"])

    @pytest.mark.asyncio
    async def test_exists_false(self, tmp_path, mock_embedding_model):
        """Test exists check returns False."""
        storage_path = tmp_path / "vector_store"

        with patch("kiwi_mcp.storage.vector.local.chromadb"):
            store = LocalVectorStore(storage_path, embedding_model=mock_embedding_model)

            mock_collection = MagicMock()
            mock_collection.get.return_value = {"ids": []}
            store._collection = mock_collection

            result = await store.exists("test_id")

            assert result is False
