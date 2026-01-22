# RAG & Vector Search Design: Scalable Semantic Discovery

**Date:** 2026-01-22  
**Status:** Approved  
**Author:** Kiwi Team  
**Phase:** 5 (Weeks 9-11)

---

## Executive Summary

This document details the implementation of vector database storage for Kiwi MCP, enabling semantic search across directives, scripts, and knowledge at scale (1M+ items). The key innovation is **validation-gated embedding**—only content that passes Kiwi's validation pipeline enters the vector store, creating a security layer that prevents malicious or malformed content from polluting search results.

---

## The Problem

### Current State: Keyword Search

```python
# Current search implementation
async def search(self, query: str, source: str = "local"):
    # Simple file scanning with keyword matching
    results = []
    for file in self._scan_files():
        if query.lower() in file.content.lower():
            results.append(file)
    return results
```

**Limitations:**
- **No semantic understanding**: "deploy app" won't match "push to production"
- **Scales linearly**: O(n) scan for every query
- **No similarity discovery**: Can't find "related" directives
- **No usage learning**: Doesn't improve from patterns

### The Scale Challenge

| Current | Near Future | Long Term |
|---------|-------------|-----------|
| ~100 directives | 10K directives | 1M+ directives |
| Project-local | User + Registry | Global ecosystem |
| Keyword works | Keyword struggles | Keyword fails |

---

## The Solution: Validation-Gated Vector Storage

### Core Insight

Kiwi already validates content before important operations (publish, run, copy). We extend this validation to act as a **security gate** for vector storage:

```
Content → Validation → IF valid → Embed & Store
                      │
                      └─ IF invalid → Reject (no embedding)
```

This ensures:
1. **Only trusted content** enters the vector DB
2. **Malformed directives** can't pollute search
3. **Signature verification** happens before embedding
4. **Audit trail** for what enters the index

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RAG Pipeline Architecture                         │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Content Sources                             │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │  │
│  │  │Directives│  │  Scripts │  │Knowledge │                     │  │
│  │  │ (.md)    │  │  (.py)   │  │  (.md)   │                     │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘                     │  │
│  └───────┼─────────────┼─────────────┼───────────────────────────┘  │
│          │             │             │                               │
│          └─────────────┼─────────────┘                               │
│                        ▼                                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                 Validation Manager (Existing)                  │  │
│  │  • XML structure validation                                   │  │
│  │  • Signature verification                                     │  │
│  │  • Permission parsing                                         │  │
│  │  • Metadata extraction                                        │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │                                       │
│                    ┌─────────▼─────────┐                            │
│                    │  Valid?           │                            │
│                    │  ┌─────┐ ┌─────┐  │                            │
│                    │  │ YES │ │ NO  │  │                            │
│                    │  └──┬──┘ └──┬──┘  │                            │
│                    └─────┼───────┼─────┘                            │
│                          │       │                                   │
│                          │       └──────► Rejected (logged)          │
│                          ▼                                           │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Embedding Pipeline                          │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                     │  │
│  │  │ Content Chunker │──│ Embedding Model │                     │  │
│  │  │ (metadata-aware)│  │(MiniLM-L6/etc) │                     │  │
│  │  └─────────────────┘  └────────┬────────┘                     │  │
│  └────────────────────────────────┼──────────────────────────────┘  │
│                                   │                                  │
│                                   ▼                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Three-Tier Vector Storage                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │  │
│  │  │   Project   │  │    User     │  │     Registry        │    │  │
│  │  │ .ai/vectors │  │~/.ai/vectors│  │ Supabase + pgvector │    │  │
│  │  │  (ChromaDB) │  │  (ChromaDB) │  │                     │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                   │                                  │
│                                   ▼                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Hybrid Search                               │  │
│  │  • Semantic similarity (vector cosine)                        │  │
│  │  • Keyword boost (BM25)                                       │  │
│  │  • Metadata filtering (item_type, category, author)           │  │
│  │  • Recency weighting (newer = higher)                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Design

### 1. VectorStore Abstraction

```python
# kiwi_mcp/storage/vector/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SearchResult:
    """Result from vector search."""
    item_id: str
    item_type: str  # directive | script | knowledge
    score: float    # 0.0 to 1.0 similarity
    content_preview: str
    metadata: dict
    source: str     # project | user | registry


@dataclass
class EmbeddingRecord:
    """Record stored in vector DB."""
    item_id: str
    item_type: str
    embedding: list[float]
    content: str
    metadata: dict
    validated_at: datetime
    signature: Optional[str] = None


class VectorStore(ABC):
    """Abstract base for vector storage backends."""
    
    @abstractmethod
    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None
    ) -> bool:
        """Embed content and store in vector DB.
        
        Returns True if successful, False if embedding failed.
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> list[SearchResult]:
        """Semantic search with optional filtering."""
        pass
    
    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """Remove item from vector store."""
        pass
    
    @abstractmethod
    async def update(
        self,
        item_id: str,
        content: str,
        metadata: dict
    ) -> bool:
        """Update existing embedding."""
        pass
    
    @abstractmethod
    async def exists(self, item_id: str) -> bool:
        """Check if item is in vector store."""
        pass
```

### 2. Local Vector Store (ChromaDB)

```python
# kiwi_mcp/storage/vector/local.py

import chromadb
from chromadb.config import Settings
from pathlib import Path

from .base import VectorStore, SearchResult, EmbeddingRecord
from .embeddings import EmbeddingModel


class LocalVectorStore(VectorStore):
    """ChromaDB-based vector store for project/user level."""
    
    def __init__(
        self,
        storage_path: Path,
        collection_name: str = "kiwi_items",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.storage_path = storage_path
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(storage_path),
            anonymized_telemetry=False
        ))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Cosine similarity
        )
        
        # Initialize embedding model
        self.embedder = EmbeddingModel(model_name=embedding_model)
    
    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None
    ) -> bool:
        try:
            # Generate embedding
            embedding = await self.embedder.embed(content)
            
            # Build metadata for filtering
            full_metadata = {
                "item_type": item_type,
                "validated_at": datetime.now(timezone.utc).isoformat(),
                **metadata
            }
            if signature:
                full_metadata["signature"] = signature
            
            # Upsert to ChromaDB
            self.collection.upsert(
                ids=[item_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[full_metadata]
            )
            
            # Persist to disk
            self.client.persist()
            
            return True
            
        except Exception as e:
            logging.error(f"Embedding failed for {item_id}: {e}")
            return False
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> list[SearchResult]:
        # Build where clause for filtering
        where = {}
        if item_type:
            where["item_type"] = item_type
        if filters:
            where.update(filters)
        
        # Generate query embedding
        query_embedding = await self.embedder.embed(query)
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where if where else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert to SearchResult objects
        search_results = []
        for i, item_id in enumerate(results["ids"][0]):
            # ChromaDB returns distance, convert to similarity
            distance = results["distances"][0][i]
            similarity = 1 - distance  # Cosine distance to similarity
            
            search_results.append(SearchResult(
                item_id=item_id,
                item_type=results["metadatas"][0][i].get("item_type", "unknown"),
                score=similarity,
                content_preview=results["documents"][0][i][:200] + "...",
                metadata=results["metadatas"][0][i],
                source="local"
            ))
        
        return search_results
    
    async def delete(self, item_id: str) -> bool:
        try:
            self.collection.delete(ids=[item_id])
            self.client.persist()
            return True
        except Exception:
            return False
    
    async def update(self, item_id: str, content: str, metadata: dict) -> bool:
        # ChromaDB upsert handles updates
        return await self.embed_and_store(
            item_id=item_id,
            item_type=metadata.get("item_type", "unknown"),
            content=content,
            metadata=metadata
        )
    
    async def exists(self, item_id: str) -> bool:
        result = self.collection.get(ids=[item_id])
        return len(result["ids"]) > 0
```

### 3. Registry Vector Store (pgvector)

```python
# kiwi_mcp/storage/vector/registry.py

from supabase import Client
from .base import VectorStore, SearchResult
from .embeddings import EmbeddingModel


class RegistryVectorStore(VectorStore):
    """pgvector-based vector store via Supabase for registry."""
    
    def __init__(self, supabase_client: Client, embedding_model: str = "all-MiniLM-L6-v2"):
        self.supabase = supabase_client
        self.embedder = EmbeddingModel(model_name=embedding_model)
        self.table = "item_embeddings"
    
    async def embed_and_store(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: dict,
        signature: Optional[str] = None
    ) -> bool:
        try:
            embedding = await self.embedder.embed(content)
            
            # Upsert to Supabase
            data = {
                "item_id": item_id,
                "item_type": item_type,
                "embedding": embedding,
                "content": content,
                "metadata": metadata,
                "signature": signature,
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.supabase.table(self.table).upsert(data).execute()
            return True
            
        except Exception as e:
            logging.error(f"Registry embedding failed for {item_id}: {e}")
            return False
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        item_type: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> list[SearchResult]:
        query_embedding = await self.embedder.embed(query)
        
        # Build RPC call for pgvector similarity search
        rpc_params = {
            "query_embedding": query_embedding,
            "match_count": limit
        }
        
        if item_type:
            rpc_params["filter_type"] = item_type
        
        # Call Supabase RPC function for vector search
        response = self.supabase.rpc(
            "search_embeddings",
            rpc_params
        ).execute()
        
        return [
            SearchResult(
                item_id=row["item_id"],
                item_type=row["item_type"],
                score=row["similarity"],
                content_preview=row["content"][:200] + "...",
                metadata=row["metadata"],
                source="registry"
            )
            for row in response.data
        ]
```

### 4. Embedding Model Wrapper

```python
# kiwi_mcp/storage/vector/embeddings.py

from sentence_transformers import SentenceTransformer
import asyncio
from functools import lru_cache


class EmbeddingModel:
    """Wrapper for embedding model with caching and batching."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for single text."""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self.model.encode(text, convert_to_numpy=True).tolist()
        )
        return embedding
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for batch of texts."""
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.model.encode(texts, convert_to_numpy=True).tolist()
        )
        return embeddings
    
    @property
    def embedding_dimension(self) -> int:
        """Get dimension of embeddings."""
        return self.model.get_sentence_embedding_dimension()
```

### 5. Validation-to-Vector Hook

```python
# kiwi_mcp/utils/validation.py (modifications)

class ValidationManager:
    """Extended to embed validated content."""
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store
        # ... existing init
    
    async def validate_and_embed(
        self,
        content: str,
        item_type: str,
        item_id: str
    ) -> ValidationResult:
        """Validate content and embed if valid.
        
        Security gate: Only validated content enters vector DB.
        """
        # Run existing validation
        result = await self.validate(content, item_type)
        
        if result.valid and self.vector_store:
            # Extract searchable content based on item type
            searchable = self._extract_searchable_content(content, item_type)
            
            # Build metadata for filtering
            metadata = {
                "category": result.metadata.get("category", "uncategorized"),
                "author": result.metadata.get("author"),
                "version": result.metadata.get("version"),
                "description": result.metadata.get("description", "")[:200],
            }
            
            # Embed and store
            success = await self.vector_store.embed_and_store(
                item_id=item_id,
                item_type=item_type,
                content=searchable,
                metadata=metadata,
                signature=result.signature
            )
            
            if success:
                result.embedded = True
                logging.info(f"Embedded {item_type} {item_id} to vector store")
            else:
                logging.warning(f"Failed to embed {item_type} {item_id}")
        
        return result
    
    def _extract_searchable_content(self, content: str, item_type: str) -> str:
        """Extract the most searchable parts of content.
        
        For directives: name, description, step names/descriptions
        For scripts: docstrings, function names, comments
        For knowledge: title, content, tags
        """
        if item_type == "directive":
            # Parse XML and extract key fields
            return self._extract_directive_searchable(content)
        elif item_type == "script":
            return self._extract_script_searchable(content)
        elif item_type == "knowledge":
            return self._extract_knowledge_searchable(content)
        return content
    
    def _extract_directive_searchable(self, content: str) -> str:
        """Extract searchable text from directive XML."""
        # Parse the directive
        parsed = self._parse_directive_xml(content)
        
        parts = [
            f"Directive: {parsed.get('name', '')}",
            f"Description: {parsed.get('description', '')}",
            f"Category: {parsed.get('category', '')}",
        ]
        
        # Add step descriptions
        for step in parsed.get('steps', []):
            parts.append(f"Step {step['name']}: {step.get('description', '')}")
        
        # Add input/output descriptions
        for inp in parsed.get('inputs', []):
            parts.append(f"Input {inp['name']}: {inp.get('description', '')}")
        
        return "\n".join(parts)
```

### 6. Hybrid Search Handler

```python
# kiwi_mcp/handlers/search.py

from typing import Optional
from .base import BaseHandler
from ..storage.vector import VectorStore, SearchResult


class HybridSearchHandler:
    """Combines semantic and keyword search for best results."""
    
    def __init__(
        self,
        project_store: VectorStore,
        user_store: Optional[VectorStore] = None,
        registry_store: Optional[VectorStore] = None
    ):
        self.project_store = project_store
        self.user_store = user_store
        self.registry_store = registry_store
    
    async def search(
        self,
        query: str,
        source: str = "local",  # local | user | registry | all
        item_type: Optional[str] = None,
        limit: int = 20,
        keyword_weight: float = 0.3  # Blend ratio
    ) -> list[SearchResult]:
        """Perform hybrid semantic + keyword search."""
        
        results = []
        
        # Determine which stores to search
        stores_to_search = []
        if source in ("local", "all"):
            stores_to_search.append(("project", self.project_store))
        if source in ("user", "all") and self.user_store:
            stores_to_search.append(("user", self.user_store))
        if source in ("registry", "all") and self.registry_store:
            stores_to_search.append(("registry", self.registry_store))
        
        # Search each store in parallel
        import asyncio
        search_tasks = [
            self._search_store(store, query, item_type, limit)
            for name, store in stores_to_search
        ]
        
        store_results = await asyncio.gather(*search_tasks)
        
        # Flatten and merge results
        for store_result in store_results:
            results.extend(store_result)
        
        # Apply keyword boosting
        results = self._apply_keyword_boost(results, query, keyword_weight)
        
        # Sort by final score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
    
    def _apply_keyword_boost(
        self,
        results: list[SearchResult],
        query: str,
        weight: float
    ) -> list[SearchResult]:
        """Boost results that contain query keywords."""
        query_terms = set(query.lower().split())
        
        for result in results:
            content_lower = result.content_preview.lower()
            
            # Count matching terms
            matches = sum(1 for term in query_terms if term in content_lower)
            keyword_score = matches / len(query_terms) if query_terms else 0
            
            # Blend semantic and keyword scores
            result.score = (1 - weight) * result.score + weight * keyword_score
        
        return results
    
    async def _search_store(
        self,
        store: VectorStore,
        query: str,
        item_type: Optional[str],
        limit: int
    ) -> list[SearchResult]:
        """Search a single vector store."""
        try:
            return await store.search(query, limit=limit, item_type=item_type)
        except Exception as e:
            logging.error(f"Search failed in store: {e}")
            return []
```

---

## Three-Tier Storage Architecture

### Storage Locations

| Tier | Path | Scope | Persistence |
|------|------|-------|-------------|
| **Project** | `.ai/vectors/` | Single project | Git-ignored, rebuilds from content |
| **User** | `~/.ai/vectors/` | All user projects | Persists across projects |
| **Registry** | Supabase + pgvector | Global | Cloud-hosted, shared |

### Synchronization Flow

```
Create/Edit Directive
        │
        ▼
┌───────────────────┐
│ Validate Content  │
└─────────┬─────────┘
          │
    ┌─────▼─────┐
    │   Valid?  │
    └─────┬─────┘
          │ YES
          ▼
┌───────────────────┐
│ Embed to Project  │◄── Automatic on create/edit
│ Vector Store      │
└─────────┬─────────┘
          │
          ▼ (on sync_to_user)
┌───────────────────┐
│ Embed to User     │◄── Manual: sync_directives to user
│ Vector Store      │
└─────────┬─────────┘
          │
          ▼ (on publish)
┌───────────────────┐
│ Embed to Registry │◄── Automatic on publish
│ Vector Store      │
└─────────────────────┘
```

---

## Implementation Plan

### Database Migrations (Supabase)

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table
CREATE TABLE item_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id TEXT UNIQUE NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('directive', 'script', 'knowledge')),
    embedding vector(384),  -- MiniLM-L6 dimension
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    signature TEXT,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX ON item_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create RPC function for similarity search
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(384),
    match_count INT DEFAULT 20,
    filter_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    item_id TEXT,
    item_type TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ie.item_id,
        ie.item_type,
        ie.content,
        ie.metadata,
        1 - (ie.embedding <=> query_embedding) AS similarity
    FROM item_embeddings ie
    WHERE (filter_type IS NULL OR ie.item_type = filter_type)
    ORDER BY ie.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Dependencies

```toml
# pyproject.toml additions
[project.optional-dependencies]
rag = [
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
    "pgvector>=0.2.0",  # For Supabase connection
]
```

---

## Performance Considerations

### Embedding Model Selection

| Model | Dimension | Speed | Quality | Recommendation |
|-------|-----------|-------|---------|----------------|
| all-MiniLM-L6-v2 | 384 | Fast | Good | **Default** |
| all-mpnet-base-v2 | 768 | Medium | Better | Large registries |
| text-embedding-3-small | 1536 | API call | Best | Production registry |

### Caching Strategy

```python
# Cache embeddings for identical content
@lru_cache(maxsize=1000)
def _cached_embed(content_hash: str, model: str) -> list[float]:
    # Cache key is content hash + model name
    pass

# Batch embedding for bulk operations
async def embed_batch(texts: list[str]) -> list[list[float]]:
    # Process in batches of 32 for optimal GPU utilization
    pass
```

### Index Rebuilding

Vector stores can be rebuilt from source content if needed:

```python
async def rebuild_vector_store(store: VectorStore, source_path: Path):
    """Rebuild entire vector store from source files."""
    for item_path in source_path.rglob("*.md"):
        content = item_path.read_text()
        result = await validation_manager.validate_and_embed(
            content=content,
            item_type=detect_item_type(item_path),
            item_id=generate_item_id(item_path)
        )
```

---

## Security Considerations

### Validation Gate

The key security property: **untrusted content never enters the vector store**.

```python
# WRONG: Direct embedding
async def unsafe_embed(content: str):
    await vector_store.embed(content)  # Malicious content could be embedded!

# RIGHT: Validation-gated embedding
async def safe_embed(content: str):
    result = await validator.validate(content)
    if result.valid:
        await vector_store.embed(content)  # Only validated content
```

### Signature Verification

Before embedding registry content:
1. Verify signature matches content
2. Check signer is authorized
3. Validate timestamp is reasonable

### Search Result Filtering

```python
# User can only see their own unpublished items
async def search_with_acl(query: str, user_id: str):
    results = await store.search(query)
    return [r for r in results if r.is_public or r.author == user_id]
```

---

## Integration with MCP 2.0

Phase 5 (RAG) is a prerequisite for Phase 12 (MCP 2.0 Intent Calling). The vector store enables:

1. **Schema Discovery**: FunctionGemma queries vector DB for relevant tool schemas
2. **Context Enrichment**: Pre-fetch related directives/knowledge for intent resolution
3. **Learning**: Store successful resolutions for improved future matching

See [MCP_2_INTENT_DESIGN.md](./MCP_2_INTENT_DESIGN.md) for how RAG powers intent resolution.

---

## Success Metrics

- [ ] Semantic search returns relevant results for 90%+ queries
- [ ] Search latency < 100ms for project-local (< 10K items)
- [ ] Search latency < 500ms for registry (< 1M items)
- [ ] Validation-gate blocks 100% of invalid content
- [ ] Three-tier storage works correctly (project → user → registry)
- [ ] Hybrid search outperforms keyword-only by 30%+ on relevance

---

## Related Documents

- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Phase 5 in roadmap
- [MCP_2_INTENT_DESIGN.md](./MCP_2_INTENT_DESIGN.md) - Uses RAG for intent resolution
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
