**Source:** Original implementation: `kiwi_mcp/tools/` in kiwi-mcp

# Legacy MCP Tools (Deprecated)

## ⚠️ WARNING: DEPRECATED

This directory contains legacy MCP tool implementations that are **no longer used**.

**DO NOT USE for new implementations.**

See `[[lilux/tools/mcp-tools]]` for deprecation details.

## What Was Here

The legacy tools module provided:
- Old MCP tool base class
- Legacy tool adapters
- Deprecated search and help tools

## Migration Path

### If you have old code using these tools:

1. **For tool execution**: Use `[[lilux/primitives/overview]]` instead
2. **For tool discovery**: Use `[[rye/categories/primitives]]`
3. **For MCP interface**: Use `[[rye/mcp-server]]`

### Example Migration

**Old (Don't use):**
```python
from kiwi_mcp.tools import LegacyToolAdapter

adapter = LegacyToolAdapter("my_tool")
result = await adapter.execute(params)
```

**New (Use instead):**
```python
from lilux.primitives import SubprocessPrimitive

primitive = SubprocessPrimitive()
result = await primitive.execute(config, params)
```

## Why It's Deprecated

1. **Primitives are better**
   - `SubprocessPrimitive` replaces tool execution
   - `HttpClientPrimitive` replaces HTTP tools
   - More explicit, more testable

2. **RYE is the orchestrator**
   - RYE handles tool discovery
   - RYE handles MCP interface
   - RYE handles content understanding

3. **Clear separation**
   - Lilux = dumb primitives
   - RYE = smart orchestration
   - No middle layer needed

## Files in This Directory

### `base.py`
Old tool base class—**don't use**

### `mcp_tools.py`
Legacy MCP tool implementations—**deprecated**

See `[[lilux/tools/mcp-tools]]` for details.

## What to Use Instead

| Old Tool | Use Instead | Link |
|----------|------------|------|
| Tool execution | SubprocessPrimitive | `[[lilux/primitives/subprocess]]` |
| HTTP calls | HttpClientPrimitive | `[[lilux/primitives/http-client]]` |
| Tool discovery | RYE | `[[rye/universal-executor/overview]]` |
| MCP interface | RYE MCP server | `[[rye/mcp-server]]` |
| Search | RYE search | `[[rye/universal-executor/overview]]` |

## Next Steps

- ✅ Migrate to primitives: `[[lilux/primitives/overview]]`
- ✅ Use RYE for orchestration: `[[rye/universal-executor/overview]]`
- ✅ See runtime services: `[[lilux/runtime-services/overview]]`
