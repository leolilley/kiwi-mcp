**Source:** Original implementation: `kiwi_mcp/tools/` in kiwi-mcp

# Legacy MCP Tools Details

## ⚠️ DEPRECATED - DO NOT USE

**Status:** Obsolete and removed from active codebase

**Replacement:** Use `[[lilux/primitives/overview]]` and `[[rye/mcp-server]]`

---

## What This Was

Legacy MCP tool implementations that provided:
- Search tools (keyword search)
- Help tools (documentation)
- Basic tool discovery

## Why It's Obsolete

### 1. Primitives Are Superior

Old way:
```python
# Didn't work well
tool = Tool(name="search")
results = tool.execute(query="python")
```

New way:
```python
# Much better
from lilux.storage.vector import SearchPipeline
pipeline = SearchPipeline(config)
results = await pipeline.search("python")
```

### 2. RYE Handles Everything

Old way:
```python
# Tools didn't know about RYE
# Couldn't parse directives
# Couldn't validate schemas
```

New way:
```python
# RYE is the orchestrator
# RYE parses directives
# RYE validates schemas
# RYE routes to primitives
```

### 3. Clear Separation

Old way:
```
Lilux tools
├── Search (tried to be smart)
├── Help (tried to be smart)
└── Discovery (tried to be smart)

Result: Duplicated logic between Lilux and RYE
```

New way:
```
Lilux primitives (dumb)
└── Execute what we're told

RYE orchestrator (smart)
├── Parse content
├── Validate
├── Route
└── Discover
```

## Migration Guide

### Migration from Legacy Search Tool

**Old (Deprecated):**
```python
from kiwi_mcp.tools.mcp_tools import SearchTool

search_tool = SearchTool()
results = search_tool.search(query="process data")
```

**New (Use instead):**
```python
from lilux.storage.vector import SearchPipeline
from lilux.config import VectorConfigManager

# Use vector search (better semantic understanding)
manager = VectorConfigManager(project_path="/project")
config = manager.load_config()
pipeline = SearchPipeline(config)

results = await pipeline.search("process data")
```

**Or use RYE discovery:**
```python
from rye.executor import UniversalExecutor

executor = UniversalExecutor(project_path="/project")
tools = await executor.discover_tools(query="process data")
```

### Migration from Legacy Help Tool

**Old (Deprecated):**
```python
from kiwi_mcp.tools.mcp_tools import HelpTool

help_tool = HelpTool()
docs = help_tool.get_help(tool_name="csv_reader")
```

**New (Use instead):**
```python
# RYE generates help from tool schemas
from rye.executor import UniversalExecutor

executor = UniversalExecutor(project_path="/project")
tool = executor.load_tool("csv_reader")
help_text = tool.get_help()  # Generated from schema
```

## Files No Longer Active

### `base.py`
Old tool base class:
- `ToolBase` - don't inherit from this
- `execute()` - use primitives instead

**Replace with:** Inherit from primitive classes or use directly

### `mcp_tools.py`
Legacy tool implementations:
- `SearchTool` - use SearchPipeline
- `HelpTool` - use RYE tool schema
- `DiscoveryTool` - use RYE discovery

**Replace with:** RYE orchestrator

### `help.py`, `search.py`
Old tool helpers

**Replace with:** RYE handlers

## What Happened to Features

### Search Functionality

**Then:** 
```python
SearchTool(backend="keyword").search(...)
```

**Now:**
```python
# Lilux provides search backends
SearchPipeline(config)  # Keyword, vector, or hybrid

# RYE provides ranking and filtering
UniversalExecutor().discover_tools(...)  # Smart discovery
```

### Help Generation

**Then:**
```python
HelpTool().get_help(tool_name)
```

**Now:**
```python
# From tool schema
tool = executor.load_tool(name)
print(tool.schema.description)

# From RYE documentation
from rye.docs import generate_tool_docs
docs = generate_tool_docs(tool)
```

### Tool Discovery

**Then:**
```python
DiscoveryTool().list_tools()
```

**Now:**
```python
# From RYE executor
executor = UniversalExecutor(project_path)
tools = await executor.list_tools()

# Or search
tools = await executor.discover_tools(query="process")
```

## Deprecation Timeline

| Date | Event |
|------|-------|
| 2025-Q1 | Primitives released |
| 2025-Q2 | RYE orchestrator released |
| 2025-Q3 | Legacy tools marked deprecated |
| 2026-Q1 | Legacy tools removed from codebase |

**Current Date:** 2026-01-30 (tools have been removed)

## Common Questions

### Q: Can I still use the old tools?

**A:** No, they're no longer in the codebase. Use primitives or RYE instead.

### Q: What if my code imports from here?

**A:** You'll get import errors. See migration guide above.

### Q: Why were they removed?

**A:** They duplicated logic and didn't fit the microkernel design. Primitives and RYE do it better.

### Q: Will they come back?

**A:** No. Primitives are the future.

## Next Steps

✅ **Immediate:**
- Stop using these tools
- Migrate to primitives

✅ **Short-term:**
- Use RYE for orchestration
- Leverage RYE discovery

✅ **Learn more:**
- See primitives: `[[lilux/primitives/overview]]`
- See RYE: `[[rye/universal-executor/overview]]`
- See storage: `[[lilux/storage/overview]]`

## Summary

**Bottom line:** This directory is dead code. Don't use it.

Use instead:
- **Execution:** `[[lilux/primitives/overview]]`
- **Discovery:** `[[rye/universal-executor/overview]]`
- **Search:** `[[lilux/storage/overview]]` or RYE discovery
- **Orchestration:** `[[rye/universal-executor/overview]]`
- **MCP Interface:** `[[rye/mcp-server]]`
