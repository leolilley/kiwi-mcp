from dataclasses import dataclass, field
from typing import Optional, Literal
import os


@dataclass
class SearchConfig:
    """Configuration for Lilux search behavior."""

    # Primary search strategy
    strategy: Literal["keyword", "hybrid", "vector"] = "keyword"

    # Keyword search settings
    min_score: float = 0.1
    default_limit: int = 20

    # Field boost weights
    field_weights: dict = field(
        default_factory=lambda: {
            "title": 3.0,
            "name": 3.0,
            "description": 2.0,
            "category": 1.5,
            "content": 1.0,
        }
    )

    # RAG settings (when available)
    vector_weight: float = 0.7
    keyword_weight: float = 0.2
    recency_weight: float = 0.1

    # Vector backend (optional)
    vector_backend: Optional[str] = None
    embedding_model: str = "all-MiniLM-L6-v2"

    @classmethod
    def from_env(cls) -> "SearchConfig":
        """Load config from environment variables."""
        return cls(
            strategy=os.getenv("KIWI_SEARCH_STRATEGY", "keyword"),
            vector_backend=os.getenv("KIWI_VECTOR_BACKEND"),
            embedding_model=os.getenv("KIWI_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        )
