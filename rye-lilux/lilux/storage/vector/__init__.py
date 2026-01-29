"""Vector storage and search implementation.

Architecture:
- SimpleVectorStore: SQLite-based local storage with cosine similarity
- LocalVectorStore: Wrapper around SimpleVectorStore
- EmbeddingService: API-based embedding generation (OpenAI, Cohere, etc.)
"""

from .base import VectorStore, SearchResult, EmbeddingRecord
from .simple_store import SimpleVectorStore
from .local import LocalVectorStore
from .pipeline import ValidationGatedEmbedding
from .manager import ThreeTierVectorManager
from .hybrid import HybridSearch
from .api_embeddings import EmbeddingService
from .embedding_registry import VectorConfig, load_vector_config

__all__ = [
    # Base
    "VectorStore",
    "SearchResult",
    "EmbeddingRecord",
    # Stores
    "SimpleVectorStore",
    "LocalVectorStore",
    # Embeddings
    "EmbeddingService",
    "VectorConfig",
    "load_vector_config",
    # Pipeline
    "ValidationGatedEmbedding",
    "ThreeTierVectorManager",
    "HybridSearch",
]
