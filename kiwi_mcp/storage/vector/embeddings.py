from functools import lru_cache
import hashlib


class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384  # Default dimension for MiniLM-L6-v2
        self._cache: dict[str, list[float]] = {}
        self._model = None

    def _get_model(self):
        """Lazy load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                self.dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text with caching."""
        cache_key = hashlib.md5(text.encode()).hexdigest()

        if cache_key in self._cache:
            return self._cache[cache_key]

        model = self._get_model()
        embedding = model.encode(text).tolist()
        self._cache[cache_key] = embedding
        return embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding for efficiency."""
        model = self._get_model()
        return model.encode(texts).tolist()
