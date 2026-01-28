# Search Architecture Alignment: Lilux Kernel + RYE Content

**Date:** 2026-01-28  
**Status:** Design Alignment  
**Context:** Reconciling search implementation with Lilux/RYE split architecture

---

## Current State Summary

| Component         | Status                 | Issues                                          |
| ----------------- | ---------------------- | ----------------------------------------------- |
| Keyword Search    | Implemented            | Naive substring matching, no directives support |
| Vector/RAG Search | Implemented (optional) | Requires `.ai/vector/` setup + embeddings       |
| Search Tool       | Works                  | Falls back silently, unclear to users           |

**Core Problem:** The keyword fallback is unreliable (2/10 rating per analysis), but vector search requires external dependencies.

---

## Alignment with Lilux/RYE Split

### Lilux (Kernel) Responsibilities

The kernel owns the **search infrastructure**:

```
lilux/
├── tools/
│   └── search.py              # SearchTool MCP interface
├── storage/
│   └── vector/                # Vector storage backends (optional RAG)
│       ├── base.py            # VectorStore abstraction
│       ├── local.py           # LocalVectorStore (ChromaDB)
│       ├── hybrid.py          # HybridSearch
│       └── manager.py         # ThreeTierVectorManager
└── utils/
    └── search/                # NEW: Core search utilities
        ├── keyword.py         # Optimal keyword search engine
        ├── scoring.py         # Relevance scoring algorithms
        └── index.py           # Optional local indexing
```

**Lilux provides:**

1. **MCP SearchTool** - The unified search interface
2. **Handler dispatch** - Routes to type-specific handlers
3. **Vector storage abstractions** - Plugin architecture for RAG
4. **Core search algorithms** - BM25, TF-IDF, keyword matching

### RYE (Content) Responsibilities

RYE content is **searchable**, not search infrastructure:

```
rye/
├── .ai/
│   ├── directives/            # Searchable content
│   ├── tools/                 # Searchable content
│   └── knowledge/             # Searchable content
└── (no search code here)
```

**RYE provides:**

1. **Searchable content** - Directives, tools, knowledge
2. **Metadata** - Categories, tags, descriptions (for filtering)
3. **No search logic** - Uses Lilux search infrastructure

---

## Ideal Search Architecture

### Design Principles

1. **Keyword-first, RAG-optional** - Local keyword search must be excellent by default
2. **Zero external deps for basic search** - Works out of the box
3. **RAG as plugin** - Vector search adds value, never required
4. **Consistent interface** - Same SearchTool regardless of backend

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SearchTool (MCP Interface)                    │
│                    lilux/tools/search.py                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Search Strategy Router                        │
│  Decides: Keyword-only OR Hybrid (Keyword + Vector)              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Keyword     │    │   Vector      │    │   Hybrid      │
│   Search      │    │   Search      │    │   Search      │
│  (Default)    │    │  (Optional)   │    │  (When RAG)   │
└───────┬───────┘    └───────┬───────┘    └───────────────┘
        │                    │
        ▼                    ▼
┌───────────────┐    ┌───────────────┐
│ BM25 + TF-IDF │    │ Vector Store  │
│ Local Index   │    │ (ChromaDB/    │
│ (No ext deps) │    │  Supabase)    │
└───────────────┘    └───────────────┘
```

---

## Optimal Keyword Search Implementation

### Replace Current Naive Matching

**Current (file_search.py):**

```python
def score_relevance(content: str, query_terms: List[str]) -> float:
    content_lower = content.lower()
    matches = sum(1 for term in query_terms if term.lower() in content_lower)
    # Binary: either matches or doesn't
```

**Proposed (BM25-inspired):**

```python
# lilux/utils/search/keyword.py

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
    - Fuzzy matching for typos (optional)
    - Zero external dependencies
    """

    # BM25 parameters
    K1 = 1.5  # Term frequency saturation
    B = 0.75  # Document length normalization

    # Field boost weights
    FIELD_WEIGHTS = {
        "title": 3.0,
        "name": 3.0,
        "description": 2.0,
        "category": 1.5,
        "tags": 1.5,
        "content": 1.0,
    }

    def __init__(self):
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
        metadata: Dict[str, Any]
    ):
        """Add document to search index."""
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
        }

        # Update IDF cache
        self._total_docs += 1
        self._update_idf_cache(tokenized)
        self._avg_doc_length = sum(
            d["length"] for d in self._doc_cache.values()
        ) / self._total_docs

    def search(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 20,
        min_score: float = 0.1
    ) -> List[SearchResult]:
        """
        Search indexed documents with BM25 scoring.

        Args:
            query: Search query string
            item_type: Filter by type (directive/tool/knowledge)
            limit: Maximum results
            min_score: Minimum relevance threshold

        Returns:
            Ranked list of SearchResults
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

            # Add phrase match bonus
            if self._has_phrase_match(query.lower(), doc):
                score *= 1.5

            if score >= min_score:
                results.append(SearchResult(
                    item_id=item_id,
                    item_type=doc["item_type"],
                    score=score,
                    title=doc["raw_fields"].get("title", doc["raw_fields"].get("name", item_id)),
                    preview=self._generate_preview(query_tokens, doc),
                    path=doc["path"],
                    metadata=doc["metadata"],
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into searchable terms."""
        if not text:
            return []
        # Lowercase, split on non-alphanumeric, filter short tokens
        tokens = re.findall(r'\b[a-z0-9_]{2,}\b', text.lower())
        return tokens

    def _score_document(self, query_tokens: List[str], doc: Dict) -> float:
        """Calculate BM25 score for document across all fields."""
        total_score = 0.0
        doc_length = doc["length"]

        for field, token_counts in doc["fields"].items():
            field_weight = self.FIELD_WEIGHTS.get(field, 1.0)

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
        """Update IDF values for all terms in document."""
        all_terms = set()
        for token_counts in tokenized.values():
            all_terms.update(token_counts.keys())

        for term in all_terms:
            # Count documents containing this term
            doc_freq = sum(
                1 for d in self._doc_cache.values()
                if any(term in tc for tc in d["fields"].values())
            )
            # IDF formula
            self._idf_cache[term] = math.log(
                (self._total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1
            )

    def _has_phrase_match(self, query: str, doc: Dict) -> bool:
        """Check if query appears as exact phrase in document."""
        for content in doc["raw_fields"].values():
            if content and query in content.lower():
                return True
        return False

    def _generate_preview(self, query_tokens: List[str], doc: Dict) -> str:
        """Generate preview snippet with query terms highlighted."""
        # Find best matching field
        content = doc["raw_fields"].get("description", "")
        if not content:
            content = doc["raw_fields"].get("content", "")[:200]

        # Truncate to reasonable length
        if len(content) > 200:
            content = content[:200] + "..."

        return content

    def clear(self):
        """Clear all indexed documents."""
        self._doc_cache.clear()
        self._idf_cache.clear()
        self._avg_doc_length = 0.0
        self._total_docs = 0
```

---

## RAG as Optional Plugin

### Plugin Architecture

```python
# lilux/storage/vector/__init__.py

from typing import Protocol, Optional, List
from dataclasses import dataclass


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    item_id: str
    item_type: str
    score: float  # Cosine similarity 0-1
    content_preview: str
    metadata: dict
    source: str


class VectorBackend(Protocol):
    """Protocol for vector search backends (RAG plugins)."""

    async def search(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 20
    ) -> List[VectorSearchResult]:
        """Semantic similarity search."""
        ...

    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict
    ) -> bool:
        """Embed content and store in vector DB."""
        ...

    def is_available(self) -> bool:
        """Check if backend is configured and ready."""
        ...
```

### Bundled RAG Implementations (Lilux)

```
lilux/storage/vector/
├── base.py              # VectorBackend protocol
├── local.py             # ChromaDB implementation (optional dep)
├── supabase.py          # Supabase pgvector (optional dep)
├── api_embeddings.py    # OpenAI/Anthropic embeddings
└── hybrid.py            # Keyword + Vector blending
```

### RYE Integration

RYE content is automatically indexed when:

1. **Project initialization** - `rye init` triggers indexing
2. **Content changes** - File watchers (optional) reindex
3. **Explicit sync** - `sync_directives`, `sync_tools`, `sync_knowledge`

---

## Search Flow with Alignment

```
User Query: "authentication directives"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ SearchTool.execute()                                         │
│ - Validate: item_type=directive, query="authentication"     │
│ - project_path="/home/user/project"                         │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Strategy Selection                                           │
│ - Check: is_vector_available(project_path)?                 │
│ - NO → Use KeywordSearchEngine                              │
│ - YES → Use HybridSearch (keyword + vector)                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │                                         │
         ▼ (Default)                               ▼ (With RAG)
┌─────────────────────┐               ┌─────────────────────┐
│ KeywordSearchEngine │               │ HybridSearch        │
│ - BM25 scoring      │               │ - 0.7 semantic      │
│ - Field boosting    │               │ - 0.2 keyword       │
│ - Phrase matching   │               │ - 0.1 recency       │
└─────────┬───────────┘               └─────────┬───────────┘
          │                                     │
          └─────────────────┬───────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Results                                                      │
│ - search_type: "keyword" or "hybrid"                        │
│ - quality: "good" (keyword BM25) or "excellent" (hybrid)    │
│ - items: [{ id, type, score, preview, metadata }]           │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Fix Keyword Search (Lilux Kernel) ✅

**Files Created/Modified:**

1. ✅ **NEW:** `lilux/utils/search/keyword.py` - BM25 search engine
2. ✅ **NEW:** `lilux/utils/search/scoring.py` - Scoring algorithms
3. ✅ **UPDATE:** `lilux/tools/search.py` - Use new KeywordSearchEngine
4. ✅ **UPDATE:** `lilux/handlers/directive/handler.py` - Add `search()` method
5. ✅ **UPDATE:** `lilux/utils/file_search.py` - Deprecate naive scoring

**Status:** COMPLETED ✅
- Keyword search now uses BM25 scoring
- Field boosting implemented
- Phrase matching added
- Zero external dependencies

### Phase 2: RAG Plugin Architecture (Lilux Kernel) 🟡

**Files Created/Modified:**

1. 🟡 **UPDATE:** `lilux/storage/vector/base.py` - VectorBackend protocol
2. 🟡 **UPDATE:** `lilux/storage/vector/hybrid.py` - Blend keyword + vector
3. 🟡 **NEW:** `lilux/config/search_config.py` - Search configuration

**Status:** IN PROGRESS 🟡
- Vector backend protocol defined
- Hybrid search strategy outlined
- Configuration structure created

### Phase 3: Content Indexing (Integration) 🟡

**Integration Points:**

1. 🟡 **RYE content** - Partial auto-indexing support
2. 🟡 **Project content** - Basic indexing implemented
3. 🟡 **User content** - Indexing in `~/.ai/` scope started

**Status:** IN PROGRESS 🟡
- Basic content discovery implemented
- File watcher prototype in development
- Metadata extraction needs refinement

---

## Configuration

### Lilux Search Config

```python
# lilux/config/search_config.py

from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass
class SearchConfig:
    """Configuration for Lilux search behavior."""

    # Primary search strategy
    strategy: Literal["keyword", "hybrid", "vector"] = "keyword"

    # Keyword search settings
    min_score: float = 0.1
    default_limit: int = 20

    # Field boost weights
    field_weights: dict = field(default_factory=lambda: {
        "title": 3.0,
        "name": 3.0,
        "description": 2.0,
        "category": 1.5,
        "content": 1.0,
    })

    # RAG settings (when available)
    vector_weight: float = 0.7
    keyword_weight: float = 0.2
    recency_weight: float = 0.1

    # Vector backend (optional)
    vector_backend: Optional[str] = None  # "chromadb", "supabase", etc.
    embedding_model: str = "all-MiniLM-L6-v2"
```

### Environment Variables

```bash
# Optional: Enable RAG features
KIWI_SEARCH_STRATEGY=hybrid           # keyword | hybrid | vector
KIWI_VECTOR_BACKEND=chromadb          # chromadb | supabase
KIWI_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Optional: Embedding API (for external models)
OPENAI_API_KEY=sk-...                 # For text-embedding-3-small
```

---

## Success Criteria

### Keyword Search (Default)

- [ ] Directive search works (currently broken)
- [ ] BM25 scoring provides meaningful relevance ranking
- [ ] Synonyms work via fuzzy matching (optional enhancement)
- [ ] Search latency < 100ms for 1000 items
- [ ] Zero external dependencies

### RAG Plugin (Optional)

- [ ] ChromaDB backend works when installed
- [ ] Supabase pgvector works when configured
- [ ] Hybrid blending improves relevance by 30%+
- [ ] Graceful fallback when RAG unavailable
- [ ] Clear indication of search strategy in results

---

## Summary

| Aspect           | Current                  | Ideal                    |
| ---------------- | ------------------------ | ------------------------ |
| Default Search   | Naive substring          | BM25 + TF-IDF            |
| Directive Search | Broken                   | Works                    |
| RAG              | Required for good search | Optional enhancement     |
| Dependencies     | ChromaDB for good search | Zero for good search     |
| User Feedback    | Silent fallback          | Clear strategy indicator |

**Key Alignment:**

- **Lilux** owns search infrastructure (algorithms, backends, MCP tool)
- **RYE** provides searchable content (directives, tools, knowledge)
- **Keyword search** is first-class, not a fallback
- **RAG** is a plugin that enhances, never required
