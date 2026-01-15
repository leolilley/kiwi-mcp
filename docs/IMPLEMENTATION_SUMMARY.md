# TypeHandlerRegistry Implementation Summary

## Objective
Wire all handlers (directive, script, knowledge) via a central `TypeHandlerRegistry` to provide unified routing for all MCP operations.

## Solution

### 1. TypeHandlerRegistry Core (`kiwi_mcp/handlers/registry.py`)

**Core Responsibility:** Route operations by `item_type` to appropriate handler.

**Key Methods:**
```python
async def search(item_type, query, **kwargs) → Dict[str, Any]
async def load(item_type, item_id, **kwargs) → Dict[str, Any]  
async def execute(item_type, action, item_id, **kwargs) → Dict[str, Any]
```

**Routing Logic:**
- Maps `item_type` to handler: `directive`, `script`, `knowledge`
- Handles missing dependencies gracefully
- Supports project_path for local operations
- Returns structured errors for unknown types

**Interface Methods:**
- `get_supported_types()` → list of registered types
- `get_handler_info()` → handler metadata and operations

### 2. Tool Dispatch Integration

#### SearchTool (`kiwi_mcp/tools/search.py`)
```python
async def execute(self, arguments):
    # Dispatch to registry
    result = await self.registry.search(
        item_type=arguments["item_type"],
        query=arguments["query"],
        source=arguments.get("source", "local"),
        limit=arguments.get("limit", 10)
    )
    return self._format_response(result)
```

#### LoadTool (`kiwi_mcp/tools/load.py`)
```python
async def execute(self, arguments):
    # Dispatch to registry
    result = await self.registry.load(
        item_type=arguments["item_type"],
        item_id=arguments["item_id"],
        destination=arguments.get("destination", "project"),
        version=arguments.get("version")
    )
    return self._format_response(result)
```

#### ExecuteTool (`kiwi_mcp/tools/execute.py`)
```python
async def execute(self, arguments):
    # Dispatch to registry
    result = await self.registry.execute(
        item_type=arguments["item_type"],
        action=arguments["action"],
        item_id=arguments["item_id"],
        parameters=arguments.get("parameters", {}),
        project_path=arguments.get("project_path")
    )
    return self._format_response(result)
```

#### HelpTool (`kiwi_mcp/tools/help.py`)
- Updated to accept registry parameter for consistency
- Can access handler info if needed

### 3. Server Integration (`kiwi_mcp/server.py`)

```python
class KiwiMCP:
    def __init__(self, project_path=None):
        # 1. Create registry with all handlers
        self.registry = TypeHandlerRegistry(project_path=project_path)
        
        # 2. Initialize tools with registry reference
        self.tools = {
            "search": SearchTool(registry=self.registry),
            "load": LoadTool(registry=self.registry),
            "execute": ExecuteTool(registry=self.registry),
            "help": HelpTool(registry=self.registry),
        }
        
        # 3. Register MCP handlers
        self._setup_handlers()
```

## Dispatch Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ MCP Client Call                                                 │
│ tool: "search"                                                  │
│ args: {item_type: "directive", query: "...", source: "local"} │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SearchTool.execute(arguments)                                   │
│ ├─ Validates item_type and query                               │
│ └─ Calls registry.search(...)                                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ TypeHandlerRegistry.search()                                    │
│ ├─ Checks item_type in handlers dict                           │
│ ├─ Returns error if unknown                                    │
│ └─ Dispatches to directive_handler.search()                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ DirectiveHandler.search()                                       │
│ ├─ Calls SearchTool from context-kiwi                          │
│ ├─ Passes all parameters                                       │
│ └─ Returns results                                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ MCP Response                                                    │
│ {                                                               │
│   "error": "...",  or                                          │
│   "directives": [...],  or                                     │
│   ...                                                           │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Handlers

### DirectiveHandler
- **Module:** `kiwi_mcp/handlers/directive/handler.py`
- **Class:** `DirectiveHandler`
- **Upstream:** context-kiwi library
- **Methods:**
  - `async search(query, source, ...)`
  - `async load(directive_name, destination, ...)`
  - `async execute(action, directive_name, parameters, ...)`

### ScriptHandler
- **Module:** `kiwi_mcp/handlers/script/handler.py`
- **Class:** `ScriptHandler`
- **Upstream:** script-kiwi library
- **Methods:**
  - `async search(query, source, ...)`
  - `async load(script_name, destination, ...)`
  - `async execute(action, script_name, parameters, ...)`

### KnowledgeHandler
- **Module:** `kiwi_mcp/handlers/knowledge/handler.py`
- **Class:** `KnowledgeHandler`
- **Upstream:** knowledge-kiwi library
- **Methods:**
  - `async search(query, source, ...)`
  - `async load(zettel_id, destination, ...)`
  - `async execute(action, zettel_id, parameters, ...)`

## Testing & Verification

### Unit Verification
```bash
# Test registry loads with all 3 handlers
python -c "from kiwi_mcp.handlers.registry import TypeHandlerRegistry; \
    r = TypeHandlerRegistry(); \
    print(f'Registry loaded: {r.get_supported_types()}')"
# Output: Registry loaded: ['directive', 'script', 'knowledge']
```

### Server Verification
```bash
# Test server has registry and tools are wired
python -c "from kiwi_mcp.server import KiwiMCP; \
    m = KiwiMCP(); \
    print(f'Server registry: {type(m.registry).__name__}'); \
    print(f'Tools wired: {all(t.registry is m.registry for t in m.tools.values())}')"
# Output: 
# Server registry: TypeHandlerRegistry
# Tools wired: True
```

### Full Verification
```bash
# Run comprehensive verification script
python verify_registry_wiring.py
# All tests pass ✓
```

## Error Handling

### Unknown Type Error
```python
await registry.search(item_type="invalid", query="test")
# Returns:
# {
#   "error": "Unknown item_type: invalid",
#   "supported_types": ["directive", "script", "knowledge"]
# }
```

### Missing Required Parameters
```python
await registry.search(item_type="directive")  # Missing query
# Returns:
# {
#   "error": "item_type and query are required"
# }
```

### Uninitialized Registry in Tool
```python
tool = SearchTool()  # Without registry
await tool.execute({"item_type": "directive", "query": "test"})
# Returns:
# {
#   "error": "Registry not initialized",
#   "message": "SearchTool requires registry instance"
# }
```

## Architecture Benefits

1. **Centralized Routing**
   - All type routing in one place
   - Easy to understand dispatch flow
   - Single point for validation

2. **Extensibility**
   - Add new type → Add handler → Register in registry
   - No tool code changes needed
   - Consistent interface for all types

3. **Separation of Concerns**
   - Registry handles routing
   - Handlers handle domain logic
   - Tools handle MCP protocol

4. **Error Handling**
   - Structured error responses
   - Graceful fallback for missing dependencies
   - Validation before dispatch

5. **Introspection**
   - Registry provides handler metadata
   - Tools can query capabilities
   - Support for dynamic help content

## Files

### New
- `kiwi_mcp/handlers/registry.py` - TypeHandlerRegistry implementation
- `verify_registry_wiring.py` - Comprehensive verification
- `REGISTRY_WIRING_REPORT.md` - Detailed report
- `IMPLEMENTATION_SUMMARY.md` - This file

### Modified
- `kiwi_mcp/server.py` - Create registry, pass to tools
- `kiwi_mcp/tools/search.py` - Dispatch via registry
- `kiwi_mcp/tools/load.py` - Dispatch via registry
- `kiwi_mcp/tools/execute.py` - Dispatch via registry
- `kiwi_mcp/tools/help.py` - Accept registry parameter

## Verification Results

✓ Registry initialization with 3 handlers
✓ Handler instances created correctly
✓ Tools wired to registry
✓ Dispatch flow functional
✓ Error handling working
✓ No import errors
✓ Project path support included

## Status

**Complete and Verified** ✓

All success criteria met:
- TypeHandlerRegistry class exists
- All 3 types registered (directive, script, knowledge)
- Server instantiates with registry
- No import errors

Ready for integration with kiwi libraries.
