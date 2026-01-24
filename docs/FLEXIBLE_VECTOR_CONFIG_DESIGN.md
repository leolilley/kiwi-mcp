# Flexible Vector Configuration Design

## 🎯 Architecture Overview

The flexible vector configuration system supports:

1. **Local embedding servers** (Ollama, local OpenAI-compatible APIs)
2. **User-level defaults** (mandatory vector DB configuration)
3. **Project-level overrides** (optional per-project customization)
4. **MCP-style environment resolution** (${VAR:default} patterns)

## 🏗️ Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    Project Level (Optional)                 │
│  .ai/config/vector.yaml - Project-specific overrides       │
│  ├─ embedding_url: "http://localhost:11434/api/embeddings" │
│  ├─ embedding_key: "custom-key"                            │
│  └─ storage_url: "http://project-vector-db:5432"           │
└─────────────────────────────────────────────────────────────┘
                              │ overrides
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    User Level (Mandatory)                   │
│  ~/.ai/config/vector.yaml - User defaults                  │
│  ├─ embedding_provider: "openai"                           │
│  ├─ embedding_url: "${OPENAI_URL:https://api.openai.com}"  │
│  ├─ embedding_key: "${OPENAI_API_KEY}"                     │
│  └─ storage_url: "${VECTOR_DB_URL}" (mandatory)            │
└─────────────────────────────────────────────────────────────┘
                              │ defaults
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Provider Registry (Built-in)               │
│  Built-in provider configurations                          │
│  ├─ openai: api.openai.com/v1/embeddings                  │
│  ├─ ollama: localhost:11434/api/embeddings                │
│  ├─ cohere: api.cohere.ai/v1/embed                        │
│  └─ local: localhost:8080/v1/embeddings                   │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration Examples

### User-Level Configuration (~/.ai/config/vector.yaml)

```yaml
# Mandatory user-level vector configuration
embedding:
  provider: openai
  url: "${OPENAI_URL:https://api.openai.com/v1/embeddings}"
  key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"

storage:
  type: simple
  url: "${VECTOR_DB_URL}"  # Mandatory - where to store vectors
  key: "${VECTOR_DB_KEY}"  # Optional - auth for vector DB

# Alternative: Local Ollama setup
# embedding:
#   provider: ollama
#   url: "${OLLAMA_URL:http://localhost:11434/api/embeddings}"
#   key: ""  # No key needed for local Ollama
#   model: "nomic-embed-text"
```

### Project-Level Override (.ai/config/vector.yaml)

```yaml
# Optional project-specific overrides
embedding:
  # Use different provider for this project
  provider: ollama
  url: "http://localhost:11434/api/embeddings"
  model: "mxbai-embed-large"

storage:
  # Use project-specific vector database
  url: "postgresql://project-vectors:5432/embeddings"
  key: "${PROJECT_VECTOR_KEY}"
```

### Environment Variables

```bash
# User-level defaults (mandatory)
export OPENAI_API_KEY="sk-..."
export VECTOR_DB_URL="postgresql://user-vectors:5432/embeddings"
export VECTOR_DB_KEY="user-vector-key"

# Project-level overrides (optional)
export PROJECT_VECTOR_KEY="project-specific-key"

# Local server alternatives
export OLLAMA_URL="http://localhost:11434/api/embeddings"
export LOCAL_EMBEDDING_URL="http://custom-server:8080/v1/embeddings"
```

## 🚀 Usage Patterns

### 1. Cloud-First Setup (OpenAI + Remote Vector DB)

```bash
# User setup (one-time)
export OPENAI_API_KEY="sk-..."
export VECTOR_DB_URL="https://my-vector-db.com/api"
export VECTOR_DB_KEY="vector-db-token"

# Works across all projects with these defaults
```

### 2. Local-First Setup (Ollama + Local Storage)

```bash
# User setup (one-time)  
export OLLAMA_URL="http://localhost:11434/api/embeddings"
export VECTOR_DB_URL="sqlite:///~/.ai/vectors/user.db"

# ~/.ai/config/vector.yaml
embedding:
  provider: ollama
  url: "${OLLAMA_URL}"
  model: "nomic-embed-text"
```

### 3. Hybrid Setup (Per-Project Flexibility)

```bash
# User defaults: OpenAI + shared vector DB
export OPENAI_API_KEY="sk-..."
export VECTOR_DB_URL="https://shared-vectors.com/api"

# Project A: Use local Ollama for privacy
# .ai/config/vector.yaml in Project A
embedding:
  provider: ollama
  url: "http://localhost:11434/api/embeddings"

# Project B: Use project-specific vector DB
# .ai/config/vector.yaml in Project B  
storage:
  url: "postgresql://project-b-vectors:5432/embeddings"
```

## 🔌 Handler Integration

### Updated Handler Initialization

```python
# Current pattern
handler = DirectiveHandler(project_path="/path/to/project")

# Enhanced pattern
handler = DirectiveHandler(
    project_path="/path/to/project",
    vector_config=VectorConfig.resolve(
        user_config_path="~/.ai/config/vector.yaml",
        project_config_path="/path/to/project/.ai/config/vector.yaml"
    )
)
```

### MCP-Style Resolution

```python
def resolve_vector_config(user_path: str, project_path: str) -> VectorConfig:
    """Resolve vector config with project overrides, following MCP patterns."""
    
    # Load user config (mandatory)
    user_config = load_yaml(user_path)
    if not user_config.get('storage', {}).get('url'):
        raise ValueError("User-level VECTOR_DB_URL is mandatory")
    
    # Load project config (optional)
    project_config = load_yaml(project_path) if exists(project_path) else {}
    
    # Resolve with environment variables
    resolved = merge_configs(user_config, project_config)
    resolved = resolve_env_vars(resolved)  # ${VAR:default} resolution
    
    return VectorConfig(**resolved)
```

## 🎛️ Provider Support Matrix

| Provider | Local Support | URL Override | Key Required | Models |
|----------|---------------|--------------|--------------|---------|
| **OpenAI** | ✅ (Compatible APIs) | ✅ | ✅ | 3-small, 3-large, ada-002 |
| **Ollama** | ✅ (Local only) | ✅ | ❌ | nomic-embed, mxbai-embed |
| **Cohere** | ❌ (API only) | ✅ | ✅ | embed-english-v3.0 |
| **Voyage** | ❌ (API only) | ✅ | ✅ | voyage-large-2, voyage-code-2 |
| **Jina** | ❌ (API only) | ✅ | ✅ | jina-embeddings-v2 |
| **Local** | ✅ (Generic) | ✅ | ❓ | Custom models |

## 🔒 Security Considerations

### 1. API Key Management
- Keys stored in environment variables (not config files)
- Support for key rotation via environment updates
- Optional keys for local servers

### 2. URL Validation
- Validate URLs before making requests
- Support allowlist for trusted domains
- Local server detection and warnings

### 3. Project Isolation
- Project configs can't access user-level secrets
- Vector databases can be project-specific
- Clear separation of concerns

## 📊 Migration Path

### Phase 1: Enhance Registry
- Add URL template support (`${PROVIDER_URL:default}`)
- Add local provider configs (Ollama, generic local)
- Maintain backward compatibility

### Phase 2: Add Config Resolution
- Implement user/project config loading
- Add MCP-style environment resolution
- Create config validation

### Phase 3: Update Handlers
- Modify handler initialization to accept vector config
- Update vector manager to use resolved config
- Add config validation at startup

### Phase 4: Documentation & Testing
- Update walkthrough tests with config examples
- Create setup guides for different patterns
- Add troubleshooting for common config issues

## 🎯 Benefits

### For Users
- **Flexible deployment**: Cloud, local, or hybrid setups
- **Cost control**: Choose between free local and paid API embeddings
- **Privacy options**: Keep sensitive projects on local infrastructure
- **Easy switching**: Change providers without code changes

### For Projects
- **Per-project customization**: Different embedding strategies per project
- **Team coordination**: Shared vector databases for collaboration
- **Environment parity**: Same config patterns across dev/staging/prod
- **Vendor flexibility**: Easy to switch embedding providers

### For Developers
- **Consistent patterns**: Same config resolution as MCP system
- **Testability**: Easy to mock different configurations
- **Extensibility**: Simple to add new providers
- **Maintainability**: Clear separation of config and implementation

This design provides maximum flexibility while maintaining the simplicity and consistency of the existing MCP patterns.
