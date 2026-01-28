# Kiwi MCP Search Usage Guide

## Overview

The Kiwi MCP Search tool provides a powerful, flexible search experience across directives, tools, and knowledge entries. This guide covers how to use the search tool effectively.

## Basic Search

### Syntax

```python
from kiwi_mcp import search

results = search(
    item_type="directive",  # Required: "directive", "tool", or "knowledge"
    query="authentication setup",  # Required: Natural language query
    project_path="/path/to/project",  # Required: Absolute project path
    source="local",  # Optional: "local", "registry", or "all"
    limit=10,  # Optional: Maximum number of results
    strategy="keyword"  # Optional: "keyword", "hybrid", or "vector"
)
```

### Query Tips

1. **Use Natural Language**
   - Good: `"set up user authentication"`
   - Avoid: `"auth user setup"`

2. **Be Specific**
   - Good: `"OAuth login with Google"`
   - Avoid: `"login"`

3. **Include Context**
   - Good: `"Python web framework authentication"`
   - Avoid: `"authentication"`

## Search Strategies

### Keyword Search (Default)

- **How it works:** Uses BM25 scoring algorithm
- **Features:**
  - Term frequency weighting
  - Inverse document frequency
  - Field boosting (title > description > content)
  - Phrase matching bonus

**Example:**
```python
results = search(
    item_type="tool",
    query="web scraping",
    strategy="keyword"
)
```

### Hybrid Search (Optional)

- **How it works:** Blends keyword and vector search
- **Requires:** Vector backend (ChromaDB or Supabase)
- **Configuration:** Set via environment variables

**Example:**
```python
# Requires vector backend setup
results = search(
    item_type="knowledge",
    query="machine learning best practices",
    strategy="hybrid"
)
```

### Vector Search (Optional)

- **How it works:** Semantic similarity using embeddings
- **Requires:** Configured vector backend
- **Best for:** Semantic, context-heavy searches

**Example:**
```python
# Requires vector backend setup
results = search(
    item_type="directive",
    query="improve team collaboration workflow",
    strategy="vector"
)
```

## Environment Configuration

### RAG (Retrieval-Augmented Generation) Setup

```bash
# In .env or shell
KIWI_SEARCH_STRATEGY=hybrid
KIWI_VECTOR_BACKEND=chromadb
KIWI_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Optional: External embedding providers
OPENAI_API_KEY=sk-...  # For OpenAI embeddings
```

## Advanced Filtering

### By Item Type

```python
# Search only directives
results = search(
    item_type="directive",
    query="authentication",
    project_path="/project"
)

# Search only tools
results = search(
    item_type="tool",
    query="web scraping",
    project_path="/project"
)
```

### Source Selection

```python
# Local project search
results = search(
    query="user management",
    source="local"
)

# Registry search
results = search(
    query="authentication patterns",
    source="registry"
)

# Search everywhere
results = search(
    query="machine learning",
    source="all"
)
```

## Result Handling

```python
results = search(query="authentication", project_path="/project")

for result in results:
    print(f"Item: {result.item_id}")
    print(f"Type: {result.item_type}")
    print(f"Score: {result.score}")
    print(f"Preview: {result.preview}")
    print(f"Metadata: {result.metadata}")
```

## Troubleshooting

1. **No Results?**
   - Make query more generic
   - Check `source` parameter
   - Verify `project_path`

2. **Slow Search?**
   - Use more specific keywords
   - Reduce `limit`
   - Check vector backend performance

## Best Practices

- Always provide `project_path`
- Use natural language queries
- Be specific but not overly complex
- Experiment with different strategies

## Roadmap

- [ ] Fuzzy matching improvements
- [ ] More advanced filtering
- [ ] Enhanced metadata search
- [ ] Performance optimizations