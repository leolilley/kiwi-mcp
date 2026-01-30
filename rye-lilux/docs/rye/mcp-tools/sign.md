# Sign Tool (`mcp__rye__sign`)

## Purpose

Validate and sign a directive, tool, or knowledge file. Adds cryptographic signature for integrity verification.

## Request Schema

```json
{
  "item_type": "directive" | "tool" | "knowledge",  // Required
  "item_id": "string",                               // Required (or glob pattern)
  "project_path": "/path/to/project",                // Required
  "parameters": {                                    // Optional
    "location": "project" | "user",
    "category": "string"
  }
}
```

## Response Schema

```json
{
  "status": "signed",
  "path": "string",
  "signature": "string",
  "timestamp": "2026-01-30T12:00:00Z"
}
```

## Validation by Item Type

| Item Type | Validation |
|-----------|------------|
| `directive` | XML syntax and structure |
| `tool` | Python code and metadata |
| `knowledge` | YAML frontmatter |

## Examples

### Sign a Directive

**Request:**
```json
{
  "item_type": "directive",
  "item_id": "create_tool",
  "project_path": "/home/user/myproject"
}
```

**Response:**
```json
{
  "status": "signed",
  "path": "/home/user/myproject/.ai/directives/create_tool.md",
  "signature": "kiwi-mcp:validated:2026-01-30T12:00:00Z:abc123...",
  "timestamp": "2026-01-30T12:00:00Z"
}
```

### Sign a Tool

**Request:**
```json
{
  "item_type": "tool",
  "item_id": "scraper",
  "project_path": "/home/user/myproject",
  "parameters": {"location": "project"}
}
```

### Batch Sign with Glob Pattern

Sign all directives in a subdirectory:

**Request:**
```json
{
  "item_type": "directive",
  "item_id": "demos/meta/*",
  "project_path": "/home/user/myproject"
}
```

**Response:**
```json
{
  "signed": ["demo1", "demo2", "demo3"],
  "failed": [],
  "total": 3,
  "summary": "Signed 3/3 items"
}
```

## Re-signing

Always allowed. Run sign again after modifying a file to update the signature.

## Validation Failure

```json
{
  "status": "error",
  "error": "Tool validation failed",
  "details": [
    "Missing required version metadata",
    "Invalid CONFIG_SCHEMA structure"
  ],
  "path": "/path/to/tool.py",
  "solution": "Fix validation issues and retry"
}
```

## Signature Format

Signatures are embedded as comments in the file:

**Python tools:**
```python
# kiwi-mcp:validated:2026-01-30T12:00:00Z:abc123def456...
```

**Markdown directives/knowledge:**
```markdown
<!-- kiwi-mcp:validated:2026-01-30T12:00:00Z:abc123def456... -->
```

## Handler Dispatch

```
mcp__rye__sign(item_type="tool", item_id="scraper", project_path="...")
    │
    └─→ ToolHandler.sign(item_id, parameters)
        │
        ├─→ Load file content
        ├─→ Extract and validate metadata
        ├─→ Generate content hash
        └─→ Write signature to file
```

## Related Documentation

- [[../mcp-server]] - MCP server architecture
- [[execute]] - Signature verification during execution
- [[search]] - Search for items
