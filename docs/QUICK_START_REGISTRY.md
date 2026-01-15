# Quick Start: TypeHandlerRegistry

## What Was Built

A unified registry system that routes all MCP operations (search, load, execute) to the appropriate handler (directive, script, knowledge) based on `item_type`.

## Key Files

| File | Purpose |
|------|---------|
| `kiwi_mcp/handlers/registry.py` | Core registry class (NEW) |
| `kiwi_mcp/server.py` | Server initialization (MODIFIED) |
| `kiwi_mcp/tools/search.py` | Search tool dispatch (MODIFIED) |
| `kiwi_mcp/tools/load.py` | Load tool dispatch (MODIFIED) |
| `kiwi_mcp/tools/execute.py` | Execute tool dispatch (MODIFIED) |
| `verify_registry_wiring.py` | Full verification suite |

## Basic Usage

```python
from kiwi_mcp.server import KiwiMCP
import asyncio

async def main():
    # Create server (registry is auto-initialized)
    mcp = KiwiMCP(project_path="/path/to/project")
    
    # Access registry directly
    registry = mcp.registry
    
    # Search for directives
    result = await registry.search(
        item_type="directive",
        query="lead generation",
        source="registry"
    )
    
    # Load a script
    result = await registry.load(
        item_type="script",
        item_id="google_maps_scraper",
        destination="project"
    )
    
    # Run knowledge entry
    result = await registry.execute(
        item_type="knowledge",
        action="create",
        item_id="new_entry",
        parameters={"title": "...", "content": "..."}
    )

asyncio.run(main())
```

## How It Works

1. **User calls tool** → `search(item_type="directive", query="test")`
2. **Tool validates** → Checks required parameters
3. **Tool dispatches** → Calls `registry.search(item_type="directive", query="test")`
4. **Registry routes** → Looks up handler for "directive" type
5. **Handler executes** → DirectiveHandler.search(query="test")
6. **Returns result** → JSON response to MCP client

## API Reference

### TypeHandlerRegistry

```python
class TypeHandlerRegistry:
    # Constructor
    __init__(project_path: Optional[str] = None)
    
    # Core methods (async)
    async search(item_type, query, source="local", limit=10, **kwargs)
    async load(item_type, item_id, destination="project", version=None, **kwargs)
    async execute(item_type, action, item_id, parameters=None, **kwargs)
    
    # Introspection methods
    get_supported_types() → list[str]  # ["directive", "script", "knowledge"]
    get_handler_info() → dict  # Full handler metadata
```

### Supported Types

```
directive  → DirectiveHandler  → context-kiwi
script     → ScriptHandler     → script-kiwi
knowledge  → KnowledgeHandler  → knowledge-kiwi
```

### Supported Actions

**Directive:**
- search, load, run, publish, delete

**Script:**
- search, load, run

**Knowledge:**
- search, load, create, update, delete, link, publish

## Error Responses

**Invalid type:**
```python
{
    "error": "Unknown item_type: invalid",
    "supported_types": ["directive", "script", "knowledge"]
}
```

**Missing parameters:**
```python
{
    "error": "item_type and query are required"
}
```

**Handler error:**
```python
{
    "error": "Failed to search directives",
    "message": "Connection timeout"
}
```

## Testing

```bash
# Verify all wiring
python verify_registry_wiring.py

# Quick check registry loads
python -c "from kiwi_mcp.handlers.registry import TypeHandlerRegistry; \
    print(TypeHandlerRegistry().get_supported_types())"

# Check server initialization
python -c "from kiwi_mcp.server import KiwiMCP; \
    m = KiwiMCP(); \
    print(f'Registry: {type(m.registry).__name__}')"
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│           MCP Client / Tool Call                │
└──────────────────┬────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  SearchTool         │
        │  LoadTool           │
        │  ExecuteTool        │
        │  HelpTool           │
        └──────────┬──────────┘
                   │
        ┌──────────▼────────────────────┐
        │  TypeHandlerRegistry          │
        │  Routes by item_type          │
        └──┬─────────┬──────────┬───────┘
           │         │          │
    ┌──────▼──┐ ┌───▼──┐ ┌──────▼──┐
    │Directive│ │Script│ │Knowledge│
    │Handler  │ │Handler│ │Handler  │
    └──────┬──┘ └───┬──┘ └──────┬──┘
           │        │          │
    ┌──────▼──┐ ┌───▼──┐ ┌──────▼──┐
    │context- │ │script│ │knowledge│
    │kiwi     │ │kiwi  │ │kiwi     │
    └─────────┘ └──────┘ └─────────┘
```

## Next Steps

1. **Integration**: When context-kiwi, script-kiwi, knowledge-kiwi are available
2. **Testing**: Run full end-to-end tests with actual libraries
3. **Monitoring**: Add logging/metrics to registry dispatch
4. **Extensions**: Add more handler types as needed

## Key Benefits

✓ **Unified Interface** - Same dispatch pattern for all types
✓ **Extensible** - Add new types without modifying tools
✓ **Maintainable** - Centralized routing logic
✓ **Resilient** - Graceful error handling
✓ **Observable** - Built-in introspection

---

For detailed documentation, see:
- `REGISTRY_WIRING_REPORT.md` - Full technical report
- `IMPLEMENTATION_SUMMARY.md` - Architecture deep dive
- `verify_registry_wiring.py` - Test suite with examples
