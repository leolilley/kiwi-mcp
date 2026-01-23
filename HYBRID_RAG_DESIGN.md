# Hybrid RAG Design: API Embeddings + Local Storage

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Content       │    │  API Embedding   │    │  Local Vector   │
│   (Directives,  │───▶│  Service         │───▶│  Store          │
│   Scripts, etc) │    │  (OpenAI, etc)   │    │  (JSON/SQLite)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Local Search   │
                                               │  (Cosine Sim)   │
                                               └─────────────────┘
```

## Benefits of Hybrid Approach

### ✅ Lightweight Dependencies
- **Before**: `sentence-transformers` (~500MB), `torch` (~1GB), `chromadb` 
- **After**: Just `httpx` for API calls, `sqlite3` (built-in Python)

### ✅ Local Data Privacy
- Embeddings generated via API, but **vectors stored locally**
- No search queries sent to external services
- Content never leaves your machine during search

### ✅ Better Embedding Quality
- OpenAI `text-embedding-3-small`: State-of-the-art, 1536 dimensions
- Cohere `embed-english-v3.0`: Optimized for search/retrieval
- Much better than local MiniLM models

### ✅ Flexible Provider Switching
- Easy to switch between OpenAI, Cohere, Voyage, Jina
- Can A/B test different embedding models
- Fallback providers if one is down

## Implementation Plan

### 1. API Embedding Service (Following MCP Pattern)

```python
# kiwi_mcp/storage/vector/api_embeddings.py
class APIEmbeddingService:
    def __init__(self, provider="openai", model="text-embedding-3-small"):
        self.provider = provider
        self.model = model
        # Environment variables like MCP: ${OPENAI_API_KEY}
        
    async def embed_text(self, text: str) -> List[float]:
        # API call with caching
        
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Batch API calls for efficiency
```

### 2. Lightweight Local Storage

```python
# kiwi_mcp/storage/vector/simple_store.py
class SimpleVectorStore:
    def __init__(self, storage_path: Path):
        # SQLite or JSON file storage
        # No ChromaDB dependency
        
    async def embed_and_store(self, item_id, content, metadata):
        # 1. Call API embedding service
        # 2. Store vector + metadata locally
        
    async def search(self, query: str, limit: int = 20):
        # 1. Call API embedding service for query
        # 2. Local cosine similarity search
        # 3. Return results (no API calls)
```

### 3. Configuration Registry (Like MCP)

```python
# kiwi_mcp/storage/vector/embedding_registry.py
EMBEDDING_PROVIDERS = {
    "openai": {
        "models": {
            "text-embedding-3-small": {"dimensions": 1536, "cost_per_1k": 0.00002},
            "text-embedding-3-large": {"dimensions": 3072, "cost_per_1k": 0.00013},
        },
        "env_var": "${OPENAI_API_KEY}",
        "endpoint": "https://api.openai.com/v1/embeddings"
    },
    "cohere": {
        "models": {
            "embed-english-v3.0": {"dimensions": 1024, "cost_per_1k": 0.0001},
        },
        "env_var": "${COHERE_API_KEY}",
        "endpoint": "https://api.cohere.ai/v1/embed"
    }
}
```

## Migration Strategy

### Phase 1: Create API Embedding Service
- New `api_embeddings.py` following MCP env var patterns
- Support OpenAI, Cohere, Voyage, Jina APIs
- Maintain same interface as current `EmbeddingModel`

### Phase 2: Create Simple Vector Store  
- SQLite-based storage (no ChromaDB)
- Local cosine similarity search
- Same interface as current `LocalVectorStore`

### Phase 3: Update Dependencies
- Remove from `pyproject.toml`: `chromadb`, `sentence-transformers`
- Keep existing `pgvector` for registry store (optional)
- Add configuration for embedding providers

### Phase 4: Graceful Fallback
- If no API key provided, fall back to keyword search
- Clear error messages about missing API keys
- Documentation on setting up API keys

## Cost Analysis

### OpenAI text-embedding-3-small
- **Cost**: $0.00002 per 1K tokens (~750 words)
- **Example**: 1000 directives × 500 words avg = $0.013 total
- **Ongoing**: Only new/updated content needs embedding

### Cohere embed-english-v3.0  
- **Cost**: $0.0001 per 1K tokens
- **Example**: Same 1000 directives = $0.067 total
- **Benefit**: Optimized for search/retrieval tasks

## User Experience

### Setup (One-time)
```bash
# Choose your provider
export OPENAI_API_KEY="sk-..."
# or
export COHERE_API_KEY="..."

# Configure in .env or shell profile
echo "OPENAI_API_KEY=sk-..." >> .env
```

### Usage (Transparent)
```python
# Same API as before - no changes needed
search_results = await vector_manager.search("deploy application")
```

### Configuration
```yaml
# .ai/config/vector.yaml
embedding:
  provider: openai
  model: text-embedding-3-small
  cache_embeddings: true
  
storage:
  type: simple  # or chromadb if available
  path: .ai/vector/
```

## Backward Compatibility

- Keep existing ChromaDB implementation as optional
- Auto-detect available dependencies
- Graceful fallback chain:
  1. API embeddings + simple storage (new default)
  2. API embeddings + ChromaDB (if installed)  
  3. Local embeddings + ChromaDB (current)
  4. Keyword search only (fallback)

## Implementation Files

```
kiwi_mcp/storage/vector/
├── api_embeddings.py      # NEW: API-based embedding service
├── simple_store.py        # NEW: Lightweight local storage  
├── embedding_registry.py  # NEW: Provider configurations
├── embeddings.py          # KEEP: Local inference (optional)
├── local.py              # KEEP: ChromaDB storage (optional)
├── hybrid.py             # UPDATE: Support both approaches
└── manager.py            # UPDATE: Auto-detect capabilities
```

This gives users the **best of both worlds**: lightweight dependencies with high-quality embeddings, while keeping data local and search fast.