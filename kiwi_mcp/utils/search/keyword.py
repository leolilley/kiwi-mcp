"""
Optimal local keyword search using BM25-inspired scoring.

Features:
- Term frequency (TF) weighting
- Inverse document frequency (IDF) weighting
- Field boosting (title > description > content)
- Phrase matching bonus
- Zero external dependencies (stdlib only)
- Document indexing with tokenization
- IDF caching for performance
"""

import re
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class SearchResult:
    """Keyword search result."""

    item_id: str
    item_type: str
    score: float
    title: str
    preview: str
    path: Path
    metadata: Dict[str, Any]


class KeywordSearchEngine:
    """
    Optimal local keyword search using BM25-inspired scoring.

    Features:
    - Term frequency (TF) weighting
    - Inverse document frequency (IDF) weighting
    - Field boosting (title > description > content)
    - Phrase matching bonus
    - Zero external dependencies
    """

    # BM25 parameters
    K1 = 1.5  # Term frequency saturation
    B = 0.75  # Document length normalization

    # Default field boost weights (used when no explicit weights provided)
    DEFAULT_FIELD_WEIGHTS = {
        "title": 5.0,
        "name": 5.0,
        "description": 2.0,
        "summary": 2.0,
        "category": 1.5,
        "tags": 1.5,
        "content": 1.0,
        "body": 1.0,
    }

    def __init__(self):
        """Initialize the search engine."""
        self._doc_cache: Dict[str, Dict] = {}
        self._idf_cache: Dict[str, float] = {}
        self._avg_doc_length = 0.0
        self._total_docs = 0

    def index_document(
        self,
        item_id: str,
        item_type: str,
        fields: Dict[str, str],
        path: Path,
        metadata: Dict[str, Any],
        field_weights: Optional[Dict[str, float]] = None,
    ):
        """
        Add document to search index.

        Args:
            item_id: Unique identifier for the document
            item_type: Type of item (directive, tool, knowledge)
            fields: Dictionary of field_name -> content to index
            path: Path to the document file
            metadata: Additional metadata to store with document
            field_weights: Optional per-document field weights from extractor schema
        """
        # Tokenize each field
        tokenized = {}
        total_length = 0

        for field, content in fields.items():
            tokens = self._tokenize(content)
            tokenized[field] = Counter(tokens)
            total_length += len(tokens)

        self._doc_cache[item_id] = {
            "item_type": item_type,
            "fields": tokenized,
            "raw_fields": fields,
            "length": total_length,
            "path": path,
            "metadata": metadata,
            "field_weights": field_weights,
        }

        # Update IDF cache
        self._total_docs += 1
        self._update_idf_cache(tokenized)
        self._avg_doc_length = sum(d["length"] for d in self._doc_cache.values()) / self._total_docs

    def search(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 20,
        min_score: float = 0.1,
    ) -> List[SearchResult]:
        """
        Search indexed documents with BM25 scoring.

        Args:
            query: Search query string
            item_type: Filter by type (directive/tool/knowledge)
            limit: Maximum results to return
            min_score: Minimum relevance threshold

        Returns:
            Ranked list of SearchResults sorted by score (highest first)
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        results = []

        for item_id, doc in self._doc_cache.items():
            # Filter by type if specified
            if item_type and doc["item_type"] != item_type:
                continue

            # Calculate BM25 score across all fields
            score = self._score_document(query_tokens, doc)

            # Add phrase match bonus (1.5x for exact query match)
            if self._has_phrase_match(query.lower(), doc):
                score *= 1.5

            if score >= min_score:
                results.append(
                    SearchResult(
                        item_id=item_id,
                        item_type=doc["item_type"],
                        score=score,
                        title=doc["raw_fields"].get(
                            "title", doc["raw_fields"].get("name", item_id)
                        ),
                        preview=self._generate_preview(query_tokens, doc),
                        path=doc["path"],
                        metadata=doc["metadata"],
                    )
                )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def clear(self):
        """Clear all indexed documents and reset caches."""
        self._doc_cache.clear()
        self._idf_cache.clear()
        self._avg_doc_length = 0.0
        self._total_docs = 0

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into searchable terms.

        Args:
            text: Text to tokenize

        Returns:
            List of lowercase tokens (2+ characters)
        """
        if not text:
            return []
        # Lowercase, split on non-alphanumeric, filter short tokens
        tokens = re.findall(r"\b[a-z0-9_]{2,}\b", text.lower())
        return tokens

    def _score_document(self, query_tokens: List[str], doc: Dict) -> float:
        """
        Calculate BM25 score for document across all fields.

        Args:
            query_tokens: List of query tokens
            doc: Document from cache

        Returns:
            BM25 score for the document
        """
        total_score = 0.0
        doc_length = doc["length"]
        
        # Use per-document weights if provided, else fall back to defaults
        doc_weights = doc.get("field_weights") or self.DEFAULT_FIELD_WEIGHTS

        for field, token_counts in doc["fields"].items():
            field_weight = doc_weights.get(field, 1.0)

            for token in query_tokens:
                if token in token_counts:
                    tf = token_counts[token]
                    idf = self._idf_cache.get(token, 1.0)

                    # BM25 formula
                    numerator = tf * (self.K1 + 1)
                    denominator = tf + self.K1 * (
                        1 - self.B + self.B * (doc_length / max(self._avg_doc_length, 1))
                    )
                    term_score = idf * (numerator / denominator)

                    total_score += term_score * field_weight

        return total_score

    def _update_idf_cache(self, tokenized: Dict[str, Counter]):
        """
        Update IDF values for all terms in document.

        Args:
            tokenized: Dictionary of field -> Counter of tokens
        """
        all_terms = set()
        for token_counts in tokenized.values():
            all_terms.update(token_counts.keys())

        for term in all_terms:
            # Count documents containing this term
            doc_freq = sum(
                1
                for d in self._doc_cache.values()
                if any(term in tc for tc in d["fields"].values())
            )
            # IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
            self._idf_cache[term] = math.log(
                (self._total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1
            )

    def _has_phrase_match(self, query: str, doc: Dict) -> bool:
        """
        Check if query appears as exact phrase in document.

        Args:
            query: Query string (lowercase)
            doc: Document from cache

        Returns:
            True if exact phrase match found in any field
        """
        for content in doc["raw_fields"].values():
            if content and query in content.lower():
                return True
        return False

    def _generate_preview(self, query_tokens: List[str], doc: Dict) -> str:
        """
        Generate preview snippet with query terms highlighted.

        Args:
            query_tokens: List of query tokens
            doc: Document from cache

        Returns:
            Preview string (max 200 chars)
        """
        # Find best matching field
        content = doc["raw_fields"].get("description", "")
        if not content:
            content = doc["raw_fields"].get("content", "")[:200]

        # Truncate to reasonable length
        if len(content) > 200:
            content = content[:200] + "..."

        return content
