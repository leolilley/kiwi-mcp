# Search Tool (`mcp__rye__search`)

## Purpose

Search for items across directives, tools, or knowledge entries using keyword or vector-based semantic search.

## Request Schema

```json
{
  "item_type": "directive" | "tool" | "knowledge",  // Required
  "query": "string",                                 // Required: Search query
  "source": "project" | "user",                      // Default: "project"
  "limit": 10,                                       // Default: 10
  "project_path": "/path/to/project"                 // Required
}
```

## Response Schema

```json
{
  "results": [
    {
      "id": "string",
      "type": "directive" | "tool" | "knowledge",
      "score": 0.95,
      "preview": "string",
      "metadata": {...},
      "source": "project" | "user"
    }
  ],
  "total": 5,
  "query": "string",
  "search_type": "keyword" | "vector_hybrid",
  "source": "project"
}
```

## Examples

### Search for Directives

**Request:**
```json
{
  "item_type": "directive",
  "query": "lead generation",
  "source": "project",
  "project_path": "/home/user/myproject"
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "lead_scraper",
      "type": "directive",
      "score": 0.92,
      "preview": "Scrape leads from Google Maps...",
      "metadata": {"version": "1.0.0", "category": "automation"},
      "source": "project"
    }
  ],
  "total": 1,
  "query": "lead generation",
  "search_type": "keyword",
  "source": "project"
}
```

### Search for Tools

**Request:**
```json
{
  "item_type": "tool",
  "query": "http scraper",
  "source": "project",
  "project_path": "/home/user/myproject"
}
```

### Search for Knowledge

**Request:**
```json
{
  "item_type": "knowledge",
  "query": "API patterns",
  "source": "user",
  "limit": 5,
  "project_path": "/home/user/myproject"
}
```

## Search Types

| Type | Description | When Used |
|------|-------------|-----------|
| `vector_hybrid` | Semantic + keyword search | When `.ai/vector/` is configured |
| `keyword` | BM25-inspired keyword matching | Fallback when vector unavailable |

## Source Locations

| Source | Path | Description |
|--------|------|-------------|
| `project` | `{project_path}/.ai/` | Project-local items |
| `user` | `~/.ai/` | User-global items |

## Handler Dispatch

Search dispatches to the appropriate handler based on `item_type`:

```
mcp__rye__search(item_type="directive", query="...", project_path="...")
    │
    └─→ DirectiveHandler.search(query, source, limit)
        │
        ├─→ Vector search (if configured)
        └─→ Keyword search (fallback)
```

## Related Documentation

- [[../mcp-server]] - MCP server architecture
- [[load]] - Load item content
- [[execute]] - Execute items
