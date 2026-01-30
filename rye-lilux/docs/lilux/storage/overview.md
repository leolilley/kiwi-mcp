**Source:** Original implementation: `kiwi_mcp/storage/vector/` in kiwi-mcp

# Vector Storage Overview

## Purpose

Optional vector storage layer for retrieval-augmented generation (RAG). Stores embeddings of tools and knowledge entries for semantic search and discovery.

## Key Components

### Vector Storage Architecture

```
VectorStorage Layer
├── EmbeddingService (API embeddings)
├── VectorStore (storage backend)
├── HybridSearch (keyword + vector)
└── SearchPipeline (orchestration)
```

**Key principle:** Storage is optional—Lilux works with keyword search alone.

## Key Classes

### EmbeddingService

Call embedding APIs (OpenAI, Anthropic, etc.):

```python
class EmbeddingService:
    def __init__(self, config: VectorConfig):
        """Initialize with API config."""
    
    async def embed(self, text: str) -> List[float]:
        """Embed a single text."""
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
```

### VectorStore

Store and search embeddings:

```python
class VectorStore:
    async def add(self, id: str, embedding: List[float], metadata: dict) -> None:
        """Add embedding to store."""
    
    async def search(self, query_embedding: List[float], limit: int) -> List[SearchResult]:
        """Search by embedding similarity."""
    
    async def delete(self, id: str) -> None:
        """Delete embedding from store."""
```

### HybridSearch

Combine keyword and vector search:

```python
class HybridSearch:
    async def search(
        self,
        query: str,
        strategy: str = "hybrid",
        vector_weight: float = 0.7,
        keyword_weight: float = 0.2
    ) -> List[SearchResult]:
        """Search using hybrid strategy."""
```

### SearchPipeline

Orchestrate the full search:

```python
class SearchPipeline:
    def __init__(self, config: VectorConfig):
        """Initialize with vector config."""
    
    async def index(self, docs: List[dict]) -> None:
        """Index documents."""
    
    async def search(self, query: str) -> List[SearchResult]:
        """Search indexed documents."""
```

## File Structure

```
storage/vector/
├── base.py                      # Abstract base classes
├── api_embeddings.py            # Call embedding APIs
├── embedding_registry.py        # Load VectorConfig
├── simple_store.py              # In-memory storage
├── local.py                     # Local file storage
├── hybrid.py                    # Keyword + vector search
├── manager.py                   # Storage orchestration
├── pipeline.py                  # Full search pipeline
└── __init__.py
```

## Storage Backends

### Simple Store (In-Memory)

Minimal in-memory storage for testing:

```python
from lilux.storage.vector import SimpleVectorStore

store = SimpleVectorStore()

# Add embedding
await store.add(
    id="tool_1",
    embedding=[0.1, 0.2, 0.3, ...],
    metadata={"tool_id": "csv_reader", "version": "1.0.0"}
)

# Search
results = await store.search(
    query_embedding=[0.1, 0.2, 0.3, ...],
    limit=10
)
```

### Local Store (File-Based)

Store embeddings locally:

```python
from lilux.storage.vector import LocalVectorStore

store = LocalVectorStore(path="/home/user/.ai/vectors")

# Indexes stored in ~/.ai/vectors/
# ├── tool_embeddings.jsonl
# ├── knowledge_embeddings.jsonl
# └── metadata.json

await store.add(id="tool_1", embedding=[...], metadata={...})
```

### Cloud Backends (Qdrant, Pinecone, etc.)

Connect to external vector databases:

```python
from lilux.storage.vector import QdrantStore

store = QdrantStore(url="http://localhost:6333")

# Uses Qdrant vector database
await store.add(...)
results = await store.search(...)
```

## Embedding APIs

### OpenAI Embeddings

```python
config = {
    "embedding": {
        "url": "https://api.openai.com/v1/embeddings",
        "key": "${OPENAI_API_KEY}",
        "model": "text-embedding-3-small",
        "request_format": "openai"
    }
}

from lilux.storage.vector import EmbeddingService

service = EmbeddingService(config)

embedding = await service.embed("What is Python?")
# Returns: [0.1, 0.2, 0.3, ...]  (1536 dimensions)
```

### Local Embeddings

```python
# Use offline models (HuggingFace, etc.)
config = {
    "embedding": {
        "model": "all-MiniLM-L6-v2",
        "request_format": "local"
    }
}

service = EmbeddingService(config)

embedding = await service.embed("What is Python?")
# Returns: [0.1, 0.2, 0.3, ...]  (384 dimensions)
```

## Search Strategies

### Keyword Search Only

No embeddings needed:

```python
from lilux.config import SearchConfig
from lilux.storage.vector import HybridSearch

config = SearchConfig(strategy="keyword")
search = HybridSearch(config)

results = await search.search(
    query="Python data processing",
    strategy="keyword"
)

# Results: Tools matching keywords (title, description, etc.)
```

### Vector Search Only

Requires embeddings:

```python
config = SearchConfig(strategy="vector")
search = HybridSearch(config)

results = await search.search(
    query="Processing CSV files",
    strategy="vector"
)

# Results: Tools semantically similar to query
```

### Hybrid Search

Combine both strategies:

```python
config = SearchConfig(
    strategy="hybrid",
    vector_weight=0.7,
    keyword_weight=0.2,
    recency_weight=0.1
)

results = await search.search(
    query="Data processing",
    strategy="hybrid"
)

# Results: Ranked by 70% vector + 20% keyword + 10% recency
```

## Complete Example: Index and Search

### 1. Create Pipeline

```python
from lilux.storage.vector import SearchPipeline
from lilux.config import VectorConfigManager

manager = VectorConfigManager(project_path="/home/user/project")
config = manager.load_config()

pipeline = SearchPipeline(config)
```

### 2. Index Documents

```python
docs = [
    {
        "id": "tool_csv_reader",
        "title": "CSV Reader",
        "description": "Read CSV files and return JSON",
        "content": "Supports various CSV formats...",
        "category": "data",
        "tool_id": "csv_reader",
        "version": "1.0.0"
    },
    {
        "id": "tool_json_processor",
        "title": "JSON Processor",
        "description": "Process and validate JSON data",
        "content": "Supports JSON Schema validation...",
        "category": "data",
        "tool_id": "json_processor",
        "version": "2.0.0"
    }
]

await pipeline.index(docs)

# Indexed: embeddings stored + metadata saved
```

### 3. Search

```python
# Keyword search
results = await pipeline.search("read CSV files")

# Results: [csv_reader, json_processor]
# Ranked by relevance
```

## RAG Integration

### Knowledge Base Search

```python
# Index knowledge entries
knowledge_docs = [
    {
        "id": "knowledge_1",
        "title": "REST API Patterns",
        "content": "REST APIs should use HTTP verbs...",
        "category": "api",
        "entry_type": "pattern"
    },
    {
        "id": "knowledge_2",
        "title": "Python Best Practices",
        "content": "Use virtual environments...",
        "category": "python",
        "entry_type": "practice"
    }
]

await pipeline.index(knowledge_docs)

# Search with context expansion
results = await pipeline.search("How do I structure API endpoints?")

# Results: Most relevant knowledge entries
# Can be passed as context to LLM
```

## Architecture Role

Vector storage is part of the **optional search and discovery layer**:

1. **Embedding storage** - Store computed embeddings
2. **Semantic search** - Find tools by meaning
3. **Knowledge retrieval** - RAG support
4. **Hybrid search** - Keyword + semantic

## RYE Relationship

RYE uses vector storage for:
- Tool discovery by semantic search
- Knowledge base queries
- Context expansion for LLM

**Pattern:**
```python
# RYE's tool discovery
pipeline = SearchPipeline(config)

# Search for relevant tools
tools = await pipeline.search("process data files")

# Results can be:
# - Used directly if confident
# - Passed as context to LLM for ranking
```

See `[[rye/universal-executor/overview]]` for discovery integration.

## Configuration

### User-Level Config

```yaml
# ~/.ai/config/vector.yaml
embedding:
  url: "https://api.openai.com/v1/embeddings"
  key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"
  request_format: "openai"

storage:
  type: "local"
  path: "~/.ai/vectors"
```

### Project-Level Override

```yaml
# .ai/config/vector.yaml
embedding:
  model: "text-embedding-3-large"  # Use larger model

storage:
  type: "qdrant"
  url: "http://localhost:6333"  # Use Qdrant for this project
```

## Testing

```python
import pytest
from lilux.storage.vector import SimpleVectorStore

@pytest.mark.asyncio
async def test_store_and_search():
    store = SimpleVectorStore()
    
    # Add embedding
    await store.add(
        id="test_1",
        embedding=[0.1, 0.2, 0.3, 0.4],
        metadata={"name": "Test"}
    )
    
    # Search
    results = await store.search(
        query_embedding=[0.1, 0.2, 0.3, 0.4],
        limit=10
    )
    
    assert len(results) > 0
    assert results[0].id == "test_1"
```

## Best Practices

### 1. Start Without Vectors

```python
# Keyword search is often sufficient
config = SearchConfig(strategy="keyword")
```

### 2. Add Vectors When Needed

```python
# When users expect semantic search
config = SearchConfig(strategy="hybrid")
```

### 3. Index Regularly

```python
# Keep embeddings up-to-date
pipeline = SearchPipeline(config)

# Re-index when tools/knowledge change
await pipeline.index(updated_docs)
```

### 4. Monitor Search Quality

Track:
- Search latency
- Result relevance
- User feedback
- Embedding costs (if using API)

## Limitations and Design

### By Design (Not a Bug)

1. **Optional layer**
   - Lilux works without vectors
   - Add only if needed

2. **Storage agnostic**
   - Swap backends without changing code
   - Local, cloud, or hybrid

3. **Simple default**
   - `SimpleVectorStore` for testing
   - Production uses local or cloud

4. **No real-time sync**
   - Index updated manually
   - Scheduled indexing recommended

## Storage Comparison

| Backend | Use Case | Setup |
|---------|----------|-------|
| SimpleVectorStore | Testing, demos | None (in-memory) |
| LocalVectorStore | Small projects | File system |
| Qdrant | Production | Docker or cloud |
| Pinecone | Managed vector DB | Cloud service |

## Next Steps

- See config: `[[lilux/config/overview]]`
- See schemas: `[[lilux/schemas/overview]]`
- See utils: `[[lilux/utils/overview]]`
