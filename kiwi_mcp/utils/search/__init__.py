"""Search utilities for Kiwi MCP.

This module provides keyword search functionality for searching
directives, tools, and knowledge entries.

Architecture:
- KeywordSearchEngine: BM25-based search with schema-driven field weights
- SearchResult: Standard result type with score and metadata
- scoring.py: Standalone utilities (kept for potential reuse, not used by engine)
"""

from .keyword import KeywordSearchEngine, SearchResult

__all__ = [
    "KeywordSearchEngine",
    "SearchResult",
]
