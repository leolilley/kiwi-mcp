"""Test embedding model functionality."""

import pytest
from unittest.mock import MagicMock, patch
from kiwi_mcp.storage.vector.embeddings import EmbeddingModel


class TestEmbeddingModel:
    def test_init_default_model(self):
        """Test initialization with default model."""
        model = EmbeddingModel()
        assert model.model_name == "all-MiniLM-L6-v2"
        assert model.dimension == 384
        assert model._model is None
        assert isinstance(model._cache, dict)

    def test_init_custom_model(self):
        """Test initialization with custom model name."""
        model = EmbeddingModel("custom-model")
        assert model.model_name == "custom-model"
        assert model.dimension == 384

    @patch("kiwi_mcp.storage.vector.embeddings.SentenceTransformer")
    def test_get_model_lazy_loading(self, mock_transformer):
        """Test lazy loading of sentence transformer model."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 512
        mock_transformer.return_value = mock_model

        model = EmbeddingModel()
        assert model._model is None

        # First call should load the model
        result_model = model._get_model()
        assert result_model == mock_model
        assert model._model == mock_model
        assert model.dimension == 512

        # Second call should reuse cached model
        result_model2 = model._get_model()
        assert result_model2 == mock_model
        mock_transformer.assert_called_once_with("all-MiniLM-L6-v2")

    def test_get_model_missing_dependency(self):
        """Test handling of missing sentence-transformers dependency."""
        model = EmbeddingModel()

        with patch(
            "kiwi_mcp.storage.vector.embeddings.SentenceTransformer", side_effect=ImportError
        ):
            with pytest.raises(ImportError) as exc_info:
                model._get_model()

            assert "sentence-transformers is required" in str(exc_info.value)

    @patch("kiwi_mcp.storage.vector.embeddings.SentenceTransformer")
    def test_embed_text(self, mock_transformer):
        """Test embedding single text with caching."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        mock_transformer.return_value = mock_model

        model = EmbeddingModel()

        # First call
        result1 = model.embed("test text")
        assert result1 == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once_with("test text")

        # Second call should use cache
        mock_model.encode.reset_mock()
        result2 = model.embed("test text")
        assert result2 == [0.1, 0.2, 0.3]
        mock_model.encode.assert_not_called()

        # Different text should call encode again
        mock_model.encode.return_value.tolist.return_value = [0.4, 0.5, 0.6]
        result3 = model.embed("different text")
        assert result3 == [0.4, 0.5, 0.6]
        mock_model.encode.assert_called_once_with("different text")

    @patch("kiwi_mcp.storage.vector.embeddings.SentenceTransformer")
    def test_embed_batch(self, mock_transformer):
        """Test batch embedding."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_transformer.return_value = mock_model

        model = EmbeddingModel()
        texts = ["text1", "text2"]

        result = model.embed_batch(texts)
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_model.encode.assert_called_once_with(texts)
