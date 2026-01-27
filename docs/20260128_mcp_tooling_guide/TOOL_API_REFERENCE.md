# Tool API Reference

## Overview

The Kiwi MCP tool system has 4 main operations:

| Operation | Tool | Purpose |
|-----------|------|---------|
| **Search** | `search` | Find tools |
| **Load** | `load` | Read tool files |
| **Execute** | `execute` | Run or sign tools |
| **Help** | `help` | Get documentation |

---

## search

### Purpose
Find tools by name and description.

### Parameters

```json
{
  "item_type": "tool",
  "query": "search keywords",
  "source": "local",
  "limit": 10,
  "project_path": "/absolute/path/to/project"
}
```

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `item_type` | string | ✅ | - | Always `"tool"` |
| `query` | string | ✅ | - | Keywords to search for |
| `source` | string | ❌ | `"local"` | `"local"` or `"all"` (registry not yet supported) |
| `limit` | int | ❌ | `10` | Max results |
| `sort_by` | string | ❌ | `"score"` | `"score"`, `"date"`, or `"name"` |
| `project_path` | string | ✅ | - | Absolute path to project |

### Returns

```json
{
  "results": [
    {
      "name": "tool_name",
      "description": "What it does",
      "source": "project" or "user",
      "path": "/absolute/path/to/tool.py",
      "score": 0.95,
      "tool_type": "python"
    }
  ],
  "total": 1,
  "query": "search keywords",
  "source": "local"
}
```

### Examples

```python
# Search for tools matching "http"
{
  "item_type": "tool",
  "query": "http api request",
  "project_path": "/home/user/myproject"
}

# Get top 5 results sorted by date
{
  "item_type": "tool",
  "query": "data processing",
  "limit": 5,
  "sort_by": "date",
  "project_path": "/home/user/myproject"
}
```

### Search Algorithm

1. **Collect candidates** - All tools from `.ai/tools/` and `~/.ai/tools/`
2. **Score relevance** - Match query keywords against name + description
3. **Sort** - By relevance score, date modified, or alphabetically
4. **Return** - Top N results with scores

---

## load

### Purpose
Load a tool file into memory (read-only access).

### Parameters

```json
{
  "item_type": "tool",
  "item_id": "tool_name",
  "source": "project" or "user",
  "project_path": "/absolute/path/to/project"
}
```

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `item_type` | string | ✅ | - | Always `"tool"` |
| `item_id` | string | ✅ | - | Tool name (without .py extension) |
| `source` | string | ✅ | - | `"project"` or `"user"` |
| `destination` | string | ❌ | - | Copy to destination (if different from source) |
| `project_path` | string | ✅ | - | Absolute path to project |

### Returns (Read-Only)

```json
{
  "name": "tool_name",
  "path": "/absolute/path/to/tool.py",
  "content": "# Full file contents...",
  "source": "project",
  "metadata": {
    "name": "tool_name",
    "description": "What it does",
    "version": "1.0.0",
    "tool_type": "python",
    "executor_id": "python_runtime",
    "category": "utility"
  }
}
```

### Returns (With Copy)

```json
{
  "name": "tool_name",
  "path": "/new/path/to/tool.py",
  "content": "# Full file contents...",
  "source": "project",
  "destination": "user",
  "message": "Tool copied from project to user",
  "metadata": {...}
}
```

### Examples

```python
# Load tool for reading (no copy)
{
  "item_type": "tool",
  "item_id": "my_tool",
  "source": "project",
  "project_path": "/home/user/myproject"
}

# Load and copy to user space
{
  "item_type": "tool",
  "item_id": "my_tool",
  "source": "project",
  "destination": "user",
  "project_path": "/home/user/myproject"
}
```

---

## execute

### Purpose
Run tools or manage their signatures.

### Common Parameters

```json
{
  "item_type": "tool",
  "action": "run" or "sign",
  "item_id": "tool_name",
  "parameters": {...},
  "project_path": "/absolute/path/to/project"
}
```

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `item_type` | string | ✅ | - | Always `"tool"` |
| `action` | string | ✅ | - | `"run"` or `"sign"` |
| `item_id` | string | ✅ | - | Tool name |
| `parameters` | object | ❌ | `{}` | Tool input parameters |
| `project_path` | string | ✅ | - | Absolute path to project |

### action: run

Execute a tool with parameters.

```json
{
  "item_type": "tool",
  "action": "run",
  "item_id": "my_tool",
  "parameters": {
    "input_text": "hello",
    "option_flag": true
  },
  "project_path": "/home/user/myproject"
}
```

**Returns:**

```json
{
  "tool_id": "my_tool",
  "action": "run",
  "status": "success",
  "result": {...},
  "execution_time_ms": 123,
  "output_path": ".ai/outputs/tools/my_tool/output_20260128_120000.json"
}
```

**Or on error:**

```json
{
  "error": "Error description",
  "tool_id": "my_tool",
  "action": "run"
}
```

### action: sign

Validate and sign a tool (update its signature).

```json
{
  "item_type": "tool",
  "action": "sign",
  "item_id": "my_tool",
  "parameters": {
    "location": "project",
    "category": "my_category"
  },
  "project_path": "/home/user/myproject"
}
```

**Returns:**

```json
{
  "tool_id": "my_tool",
  "action": "sign",
  "status": "signed",
  "message": "Tool signed successfully",
  "signature": "kiwi-mcp:validated:2026-01-28T12:00:00Z:abc123...",
  "hash": "abc123..."
}
```

### Parameter Passing

Parameters are passed to the tool's `main()` function:

```python
# Tool definition
def main(input_text: str, count: int = 1) -> dict:
    return {"result": input_text * count}

# MCP call
{
  "item_type": "tool",
  "action": "run",
  "item_id": "my_tool",
  "parameters": {
    "input_text": "hello",
    "count": 3
  },
  "project_path": "/home/user/myproject"
}

# Result: {"result": "hellohellohello"}
```

### Examples

```python
# Run tool with no parameters
{
  "item_type": "tool",
  "action": "run",
  "item_id": "greeting",
  "parameters": {},
  "project_path": "/home/user/myproject"
}

# Run tool with parameters
{
  "item_type": "tool",
  "action": "run",
  "item_id": "text_processor",
  "parameters": {
    "text": "hello world",
    "transform": "uppercase"
  },
  "project_path": "/home/user/myproject"
}

# Sign a tool
{
  "item_type": "tool",
  "action": "sign",
  "item_id": "my_tool",
  "parameters": {
    "location": "project"
  },
  "project_path": "/home/user/myproject"
}
```

---

## help

### Purpose
Get documentation about the tool system.

### Parameters

```json
{
  "topic": "optional_topic"
}
```

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `topic` | string | ❌ | Optional: `"tool"`, `"search"`, `"load"`, `"execute"`, etc. |

### Returns

```json
{
  "help": "Long help text...",
  "topic": "tools" or specific topic,
  "examples": [...]
}
```

### Examples

```python
# General help
{ }

# Help for a specific topic
{ "topic": "tool" }

# Help for execute action
{ "topic": "execute" }
```

---

## Error Responses

All tools return consistent error responses:

```json
{
  "error": "Error description",
  "item_type": "tool",
  "message": "Human-readable explanation",
  "suggestion": "How to fix it"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Tool not found` | File doesn't exist | Check path: `.ai/tools/category/name.py` |
| `Content hash mismatch` | File modified after signing | Re-sign with `action: sign` |
| `Invalid metadata` | Missing `__version__`, etc. | Add required fields to top of file |
| `Execution failed` | Tool error | Check tool parameters and logic |
| `project_path is required` | Missing parameter | Add `project_path: "/absolute/path"` |

---

## Tool File Format

### Required Signature

First line MUST be:
```python
# kiwi-mcp:validated:{TIMESTAMP}Z:{HASH}
```

### Required Metadata

```python
__version__ = "1.0.0"           # Required: semantic version
__tool_type__ = "python"         # Required: python, api, mcp_tool, or primitive
__executor_id__ = "python_runtime"  # Required: executor tool name or None
__category__ = "utility"         # Required: category for organization
```

### Required Function

```python
def main(**kwargs) -> dict:
    """Docstring describing the tool."""
    # Implementation
    return {...}
```

---

## Executor Chain Example

How `run` action resolves and executes tools:

```
1. resolve("my_tool")
   → Load: .ai/tools/my_category/my_tool.py
   → Extract: tool_type="python", executor_id="python_runtime"

2. resolve("python_runtime")
   → Load: .ai/tools/python_runtime.py (or ~/.ai/tools/python_runtime.py)
   → Extract: tool_type="runtime", executor_id="subprocess"

3. resolve("subprocess")
   → Load: .ai/tools/primitives/subprocess.py
   → Extract: executor_id=None → PRIMITIVE
   → Execute directly

4. Execute chain
   → [my_tool.py] → [python_runtime.py] → [subprocess.py (hard-coded)]
   → Spawn Python interpreter with my_tool's main() function
```

---

## See Also

- `README.md` - Full documentation
- `QUICK_START.md` - Getting started guide
- `.ai/tools/` - Example tools in project
- `kiwi_mcp/handlers/tool/handler.py` - Implementation
- `kiwi_mcp/schemas.py` - Metadata extraction logic
