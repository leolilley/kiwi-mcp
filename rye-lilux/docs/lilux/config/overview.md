**Source:** Original implementation: `kiwi_mcp/config/` in kiwi-mcp

# Configuration Overview

## Purpose

Lilux configuration manages search behavior and vector embedding settings. Configuration is intentionally minimal—RYE provides content understanding, Lilux just provides knobs for tool discovery and RAG.

## Key Classes

### SearchConfig

Configuration for search behavior:

```python
@dataclass
class SearchConfig:
    # Primary search strategy
    strategy: Literal["keyword", "hybrid", "vector"] = "keyword"
    
    # Keyword search settings
    min_score: float = 0.1
    default_limit: int = 20
    
    # Field boost weights
    field_weights: dict = {
        "title": 3.0,
        "name": 3.0,
        "description": 2.0,
        "category": 1.5,
        "content": 1.0,
    }
    
    # RAG settings (when available)
    vector_weight: float = 0.7
    keyword_weight: float = 0.2
    recency_weight: float = 0.1
    
    # Vector backend (optional)
    vector_backend: Optional[str] = None
    embedding_model: str = "all-MiniLM-L6-v2"
```

### VectorConfigManager

Manage vector embedding configuration:

```python
class VectorConfigManager:
    def __init__(self, project_path: str):
        """Initialize with project root."""
    
    def load_config(self) -> VectorConfig:
        """Load resolved vector config (user + project)."""
    
    def ensure_user_config(self) -> bool:
        """Create default user config if missing."""
    
    def create_project_config(
        self,
        embedding_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        storage_url: Optional[str] = None
    ) -> None:
        """Create project-specific overrides."""
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate config and test connectivity."""
```

## Configuration Hierarchy

Lilux uses **project-first** configuration resolution:

```
Project config (highest priority)
~/.ai/config/
├── search.yaml
├── vector.yaml
└── ...

User config (fallback)
.ai/config/
├── search.yaml
├── vector.yaml
└── ...
```

**Resolution:** Project config overrides user config.

## Search Configuration

### Strategy Options

**Keyword Search** (default, no setup required):
```python
config = SearchConfig(strategy="keyword")
```

Searches by field matching:
- Title (3x weight)
- Name (3x weight)
- Description (2x weight)
- Category (1.5x weight)
- Content (1x weight)

**Vector Search** (requires embeddings):
```python
config = SearchConfig(
    strategy="vector",
    vector_backend="openai",
    embedding_model="text-embedding-3-small"
)
```

Uses semantic similarity:
- Embed query and documents
- Return most similar results

**Hybrid Search** (keyword + vector):
```python
config = SearchConfig(
    strategy="hybrid",
    vector_weight=0.7,
    keyword_weight=0.2,
    recency_weight=0.1
)
```

Combines both:
- 70% vector similarity
- 20% keyword matching
- 10% recency bonus

### Field Weights

Customize field importance in keyword search:

```yaml
# search.yaml
strategy: keyword
field_weights:
  title: 3.0       # Most important
  name: 3.0
  description: 2.0
  category: 1.5
  content: 1.0     # Least important
```

Higher weights = higher relevance in results.

## Vector Configuration

### File Structure

User-level config:
```yaml
# ~/.ai/config/vector.yaml
embedding:
  url: "https://api.openai.com/v1/embeddings"
  key: "${EMBEDDING_API_KEY}"
  model: "text-embedding-3-small"
  request_format: "openai"

storage:
  type: "simple"
  url: "${VECTOR_DB_URL}"
  key: "${VECTOR_DB_KEY:}"
```

Project-level override:
```yaml
# .ai/config/vector.yaml
embedding:
  model: "text-embedding-3-large"  # Override user model

storage:
  type: "qdrant"  # Different storage for this project
  url: "http://localhost:6333"
```

### Configuration Options

**Embedding Service:**
- `url` - Embedding API endpoint
- `key` - API key (from env var)
- `model` - Embedding model name
- `request_format` - API format (openai, anthropic, etc.)

**Storage Backend:**
- `type` - Storage type (simple, qdrant, pinecone, etc.)
- `url` - Storage service URL
- `key` - Authentication key

### Environment Variables

Configuration supports variable expansion:

```yaml
embedding:
  key: "${EMBEDDING_API_KEY}"      # Required from env
  url: "${EMBEDDING_URL:https://...}"  # Optional with default
```

Lilux expands `${VAR}` and `${VAR:-default}` syntax at load time.

## Usage Examples

### Default Configuration

```python
from lilux.config import SearchConfig

# Use defaults (keyword search, no vectors)
config = SearchConfig()

print(config.strategy)  # "keyword"
print(config.embedding_model)  # "all-MiniLM-L6-v2"
```

### Load from Environment

```python
config = SearchConfig.from_env()

# Reads:
# KIWI_SEARCH_STRATEGY="hybrid"
# KIWI_VECTOR_BACKEND="openai"
# KIWI_EMBEDDING_MODEL="text-embedding-3-small"
```

### Vector Configuration Setup

```python
from lilux.config import VectorConfigManager

manager = VectorConfigManager(project_path="/home/user/project")

# Ensure user config exists
manager.ensure_user_config()

# Create project override
manager.create_project_config(
    embedding_url="https://api.openai.com/v1/embeddings",
    embedding_model="text-embedding-3-large",
    storage_url="http://localhost:6333"
)

# Load resolved config
config = manager.load_config()
```

### Validate Configuration

```python
manager = VectorConfigManager(project_path="/home/user/project")

# Test connectivity
result = manager.validate_config()

if result["embedding"]["ok"]:
    print("✓ Embedding service available")
else:
    print("✗ Embedding service failed")

if result["storage"]["ok"]:
    print("✓ Storage service available")
else:
    print("✗ Storage service failed")
```

## Architecture Role

Configuration is part of the **optional RAG layer**:

1. **Search strategy** - How to find tools/knowledge
2. **Vector settings** - Embedding and storage
3. **Field weighting** - Customize keyword search
4. **Hierarchical resolution** - Project overrides user

## RYE Relationship

RYE uses configuration for:
- Tool discovery by keyword or semantic search
- Knowledge base search (RAG)
- Search result ranking

**Pattern:**
```python
# RYE's tool discovery
from lilux.config import SearchConfig, VectorConfigManager

manager = VectorConfigManager(project_path=project_root)
search_config = SearchConfig.from_env()

# Discover tools
tools = search_by_query(
    query="data processing",
    config=search_config
)
```

See `[[rye/universal-executor/overview]]` for discovery integration.

## Best Practices

### 1. Start with Keyword Search

```python
# Simplest, no dependencies
config = SearchConfig(strategy="keyword")
```

Works well for:
- Known tool names
- Clear descriptions
- Category-based search

### 2. Add Vector Search for Better UX

```python
# When user experience matters
config = SearchConfig(
    strategy="hybrid",
    vector_weight=0.7,
    keyword_weight=0.2
)
```

Better at:
- Fuzzy matching
- Semantic understanding
- Natural language queries

### 3. Customize Field Weights

```yaml
# Emphasize titles and descriptions
field_weights:
  title: 5.0       # Very important
  name: 4.0
  description: 3.0
  category: 1.0
  content: 0.5     # Less important
```

### 4. Use Project Overrides Carefully

```yaml
# .ai/config/vector.yaml
# Only override what's needed
embedding:
  model: "custom-model"  # Project-specific model
```

Don't duplicate user config—only override.

## Testing

```python
import pytest
from lilux.config import SearchConfig

def test_default_search_config():
    config = SearchConfig()
    
    assert config.strategy == "keyword"
    assert config.default_limit == 20
    assert config.field_weights["title"] == 3.0

def test_search_config_from_env(monkeypatch):
    monkeypatch.setenv("KIWI_SEARCH_STRATEGY", "hybrid")
    
    config = SearchConfig.from_env()
    
    assert config.strategy == "hybrid"
```

## Limitations and Design

### By Design (Not a Bug)

1. **Lilux has minimal config**
   - No content understanding config
   - No parsing rules
   - RYE handles content config

2. **Search config is optional**
   - Defaults work for simple cases
   - Override only as needed

3. **Vector storage is optional**
   - Works without embeddings
   - Keyword search is sufficient for many cases

## Next Steps

- See storage: `[[lilux/storage/overview]]`
- See utilities: `[[lilux/utils/overview]]`
- See RYE: `[[rye/universal-executor/overview]]`
