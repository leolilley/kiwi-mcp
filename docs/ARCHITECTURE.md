# Kiwi MCP Architecture

**Date:** 2026-01-15  
**Version:** 0.1.0

---

## System Overview

Kiwi MCP is a unified MCP server that provides a single interface with 4 tools and a type-aware registry pattern for managing directives, tools, and knowledge.

```
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Server (stdio)                            │
│                    KiwiMCP class                                 │
└──────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
          ┌─────▼──────┐ ┌────▼─────┐ ┌───▼──────┐
          │   search   │ │   load   │ │ execute  │
          │   tool     │ │   tool   │ │  tool    │
          └─────┬──────┘ └────┬─────┘ └───┬──────┘
                │             │             │
                └─────────────┼─────────────┘
                              │
                 ┌────────────▼────────────┐
                 │ TypeHandlerRegistry    │
                 │ (routing + dispatch)   │
                 └───┬────────────┬───┬────┘
                     │            │   │
            ┌────────▼──┐  ┌──────▼┐ │
            │ Directive │  │ Tool  │ │  Knowledge
            │ Handler   │  │Handler│ │  Handler
            └────┬──────┘  └──┬────┘ │
                 │            │      └─────┬─────┐
        ┌────────▼──────────┬─▼──────┐     │     │
        │   Local Storage   │        │     │     │
        │ .ai/directives/   │Registry│     │     │
        │ .ai/tools/         │(Supa..)│     │     │
        │ .ai/knowledge/    │        │     │     │
        └───────────────────┴────────┘     │     │
                                  Local    │     Registry
                                  Storage  │
```

---

## Core Components

### 1. MCP Server (kiwi_mcp/server.py)

**Class:** `KiwiMCP`

Entry point for the MCP server. Initializes all tools and handlers.

```python
class KiwiMCP:
    def __init__(self, project_path=None):
        self.server = Server("kiwi-mcp")
        self.registry = TypeHandlerRegistry(project_path=project_path)
        
        self.tools = {
            "search": SearchTool(registry=self.registry),
            "load": LoadTool(registry=self.registry),
            "execute": ExecuteTool(registry=self.registry),
            "help": HelpTool(registry=self.registry),
        }
```

**Responsibilities:**
- Register tools with MCP protocol
- Handle tool dispatch
- Manage server lifecycle
- Error handling and logging

### 2. Tools Layer (kiwi_mcp/tools/)

Four unified tools implementing consistent interface.

#### BaseTool (Abstract)
```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def schema(self) -> Tool:
        """MCP tool schema with name, description, inputSchema"""
        pass
    
    @abstractmethod
    async def execute(self, arguments: dict) -> str:
        """Execute tool, return JSON string"""
        pass
```

#### SearchTool
- **Purpose:** Find items across local + registry
- **Input:** `item_type`, `query`, `source`, `limit`
- **Output:** `{ "results": [...] }` or `{ "error": "..." }`
- **Dispatch:** Calls `registry.search(item_type, query, ...)`

#### LoadTool
- **Purpose:** Download from registry to local
- **Input:** `item_type`, `item_id`, `destination`, `project_path`, `version`
- **Output:** `{ "status": "loaded", "path": "..." }`
- **Dispatch:** Calls `registry.load(item_type, item_id, ...)`

#### ExecuteTool
- **Purpose:** Run operations (run, publish, delete, create, update, link)
- **Input:** `item_type`, `action`, `item_id`, `parameters`, ...
- **Output:** `{ "status": "...", ... }` or `{ "error": "..." }`
- **Dispatch:** Calls `registry.execute(item_type, action, item_id, ...)`

#### HelpTool
- **Purpose:** Provide usage guidance
- **Input:** `topic` (optional)
- **Output:** `{ "help": "..." }`
- **Dispatch:** Returns hardcoded help text

### 3. TypeHandlerRegistry (kiwi_mcp/handlers/registry.py)

Central routing component that dispatches operations to type-specific handlers.

```python
class TypeHandlerRegistry:
    def __init__(self, project_path=None):
        self.directive_handler = DirectiveHandler(project_path)
        self.tool_handler = ToolHandler(project_path)
        self.knowledge_handler = KnowledgeHandler(project_path)
        
        self.handlers = {
            "directive": self.directive_handler,
            "tool": self.tool_handler,
            "knowledge": self.knowledge_handler,
        }
    
    async def search(self, item_type, query, **kwargs):
        handler = self._get_handler(item_type)
        return await handler.search(query, **kwargs)
    
    async def load(self, item_type, item_id, **kwargs):
        handler = self._get_handler(item_type)
        # Map item_id to type-specific param name
        if item_type == "directive":
            return await handler.load(directive_name=item_id, **kwargs)
        elif item_type == "tool":
            return await handler.load(tool_id=item_id, **kwargs)
        elif item_type == "knowledge":
            return await handler.load(zettel_id=item_id, **kwargs)
    
    async def execute(self, item_type, action, item_id, parameters=None, **kwargs):
        handler = self._get_handler(item_type)
        # Similar mapping as load()
        return await handler.execute(action=action, ...)
```

**Key Features:**
- **Routing:** Maps `item_type` to appropriate handler
- **Parameter Mapping:** Normalizes `item_id` to handler-specific names
  - `directive` → `directive_name`
  - `tool` → `tool_id`
  - `knowledge` → `zettel_id`
- **Error Handling:** Catches exceptions, returns error dicts
- **Logging:** Info and error logs for debugging

### 4. Type-Specific Handlers

#### DirectiveHandler (kiwi_mcp/handlers/directive/handler.py)
Handles directive operations (search, load, run, publish, delete, create, update).

```python
class DirectiveHandler:
    async def search(self, query, source="local", **kwargs):
        # Search local .ai/directives/ or registry
    
    async def load(self, directive_name, destination, **kwargs):
        # Download from registry to destination
    
    async def execute(self, action, directive_name, parameters, **kwargs):
        # Route to _run_directive, _publish, _delete, etc.
```

**Storage:**
- Project: `.ai/directives/`
- User: `~/.ai/directives/`
- Format: Markdown with YAML frontmatter

#### ToolHandler (kiwi_mcp/handlers/tool/handler.py)
Handles tool operations (search, load, run, publish, delete).

```python
class ToolHandler:
    async def search(self, query, source="local", **kwargs):
        # Search local .ai/tools/ or registry
    
    async def load(self, tool_id, destination, **kwargs):
        # Download from registry
    
    async def execute(self, action, tool_id, parameters, **kwargs):
        # Route to _run_tool, _publish, _delete, etc.
```

**Storage:**
- Project: `.ai/tools/`
- User: `~/.ai/tools/`
- Format: YAML manifest + source files

#### KnowledgeHandler (kiwi_mcp/handlers/knowledge/handler.py)
Handles knowledge operations (search, load, create, update, delete, link, publish).

```python
class KnowledgeHandler:
    async def search(self, query, source="local", **kwargs):
        # Search local .ai/knowledge/ or registry
    
    async def load(self, zettel_id, destination, **kwargs):
        # Download from registry
    
    async def execute(self, action, zettel_id, parameters, **kwargs):
        # Route to _create, _update, _delete, _link, _publish, etc.
```

**Storage:**
- Project: `.ai/knowledge/`
- User: `~/.knowledge-kiwi/`
- Format: Markdown with metadata

### 5. API Layer (kiwi_mcp/api/)

Supabase-based registry clients.

#### BaseRegistry (kiwi_mcp/api/base.py)
```python
class BaseRegistry:
    def __init__(self, table_name):
        self.client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SECRET_KEY")
        )
        self.table_name = table_name
    
    async def search(self, query, **kwargs):
        # Query via HTTP/RPC
    
    async def get(self, item_id, **kwargs):
        # Fetch single item
    
    async def publish(self, **kwargs):
        # Insert/update in registry
```

#### DirectiveRegistry, ToolRegistry, KnowledgeRegistry
Extend `BaseRegistry` with table-specific methods.

### 6. Utilities (kiwi_mcp/utils/)

#### paths.py
- `resolve_item_path()` - Find file by item_id and type
- `get_user_home()` - User space directory
- `get_project_path()` - Project space directory

#### search.py
- Multi-term search utilities
- Relevance scoring
- Filter and sort

#### logger.py
- Structured logging
- Log levels

---

## Request Flow Example

### Search Request

```
User Request:
{
  "tool": "search",
  "arguments": {
    "item_type": "directive",
    "query": "authentication",
    "source": "registry"
  }
}

Flow:
1. MCP Server receives call_tool("search", arguments)
2. Dispatches to SearchTool.execute(arguments)
3. SearchTool calls registry.search("directive", "authentication", source="registry")
4. TypeHandlerRegistry._get_handler("directive") returns DirectiveHandler
5. DirectiveHandler.search("authentication", source="registry")
   - Query Supabase registry
   - Return results
6. SearchTool._format_response() converts to JSON string
7. MCP Server returns TextContent with JSON string
```

### Execute Request

```
User Request:
{
  "tool": "execute",
  "arguments": {
    "item_type": "directive",
    "action": "run",
    "item_id": "oauth_setup",
    "parameters": {"provider": "google"}
  }
}

Flow:
1. MCP Server receives call_tool("execute", arguments)
2. Dispatches to ExecuteTool.execute(arguments)
3. ExecuteTool calls registry.execute(
     "directive", "run", "oauth_setup", 
     parameters={"provider": "google"}
   )
4. TypeHandlerRegistry maps item_id→directive_name
5. Calls DirectiveHandler.execute(
     action="run",
     directive_name="oauth_setup",
     parameters={"provider": "google"}
   )
6. DirectiveHandler routes to _run_directive()
   - Load from local (.ai/directives/) or registry
   - Return parsed content with instructions
7. ExecuteTool._format_response() converts to JSON string
8. MCP Server returns TextContent
```

---

## Storage Strategy

### Local Storage

```
~/.ai/                                  # User space (env var: AI_USER_SPACE)
├── directives/
│   ├── setup/
│   │   └── bootstrap.md
│   └── auth/
│       └── oauth_setup.md
├── tools/
│   ├── scraping/
│   │   └── google_maps_leads/
│   │       ├── manifest.yaml
│   │       └── main.py
│   └── enrichment/
│       └── email_validator/
│           ├── manifest.yaml
│           └── main.py
└── knowledge/
    ├── email-infrastructure/
    │   └── 001-deliverability.md
    └── authentication/
        └── 002-jwt-auth.md

.ai/                                    # Project space
├── directives/                         # Same structure as ~/.ai/
├── tools/
└── knowledge/
```

### Registry Storage (Supabase)

**Table: directives**
```sql
- id (pk)
- name (unique)
- version
- category
- subcategory
- description
- content (markdown)
- frontmatter (json)
- created_at
- updated_at
```

**Table: tools**
```sql
- id (pk)
- tool_id (unique)
- tool_type (script, mcp_server, runtime, etc.)
- executor_id (references another tool)
- version
- category
- subcategory
- description
- manifest (json)
- created_at
- updated_at
```

**Table: tool_version_files**
```sql
- id (pk)
- tool_version_id (fk)
- file_path
- content
- content_hash
- created_at
```

**Table: knowledge**
```sql
- id (pk)
- zettel_id (unique)
- title
- entry_type (api_fact, pattern, concept, learning, etc.)
- category
- content (markdown)
- tags (array)
- created_at
- updated_at
```

---

## Configuration

### Environment Variables

```bash
# Supabase registry
SUPABASE_URL=https://project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key

# User space (defaults to ~/.ai)
AI_USER_SPACE=~/.ai

# Logging
LOG_LEVEL=INFO

# Optional
PROJECT_PATH=/path/to/project  # For tool initialization
```

### Settings (kiwi_mcp/config/settings.py)

```python
class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SECRET_KEY", "")
    user_space: Path = Path(os.getenv("AI_USER_SPACE", "~/.ai")).expanduser()
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
```

---

## Error Handling

### Consistent Error Format

All endpoints return error responses in same format:

```json
{
  "error": "Description of error",
  "item_type": "directive|script|knowledge",
  "action": "operation attempted",
  "item_id": "identifier",
  "message": "User-friendly message"
}
```

### Handler Error Recovery

1. **Unknown Handler** → Return 404 error with supported types
2. **Handler Exception** → Catch, log, return error dict
3. **Invalid Parameters** → Return validation error
4. **File Not Found** → Return not found error with search suggestion
5. **Registry Unavailable** → Fall back to local (if available) or error

---

## Design Patterns

### 1. Type Handler Pattern
Route operations through `item_type` to specific handler implementations. Enables:
- Adding new types (e.g., `plugin`) without changing tools
- Consistent interface for diverse implementations
- Decoupled handlers and tools

### 2. Parameter Normalization
Tools use `item_id` universally, registry maps to type-specific names:
- Directive: `directive_name`
- Tool: `tool_id`
- Knowledge: `zettel_id`

Enables uniform tool interface across different types.

### 3. Async/Await Throughout
All I/O (file, network) is async for responsiveness:
- File operations via `aiofiles`
- Registry queries via async HTTP/Supabase client
- Tools are async-native

### 4. Registry + Local Dual Storage
Support both local development and centralized registry:
- `source="local"` → search/use local files only
- `source="registry"` → search registry (Supabase) only
- `source="all"` → prefer local, fall back to registry
- `load` → download registry to local

### 5. Markdown + Metadata
Store items with content + structured metadata:
- Directives/Knowledge: Markdown content + YAML frontmatter
- Tools: YAML manifest + source files
- Enables human-readable storage + structured queries

---

## Extension Points

### Adding a New Type

1. Create handler: `kiwi_mcp/handlers/newtype/handler.py`
2. Extend `BaseRegistry`: `kiwi_mcp/api/newtype_registry.py`
3. Register in `TypeHandlerRegistry.__init__()`:
   ```python
   self.newtype_handler = NewTypeHandler(project_path)
   self.handlers["newtype"] = self.newtype_handler
   ```
4. Update tool schemas to include `"newtype"` in enums
5. Add tests

### Custom Handler Methods

Handlers can implement any methods needed for their type:
- Standard: `search`, `load`, `execute`
- Custom: Type-specific operations

### Middleware/Plugins

Future: Add middleware layer for:
- Authentication/authorization
- Rate limiting
- Caching
- Custom handlers

---

## Testing Strategy

### Unit Tests
- **test_tools.py:** Tool schemas, validation, error handling (20+ tests)
- **test_handlers.py:** Handler routing, parameter mapping (20+ tests)
- **test_api.py:** Registry client mocking (future)

### Integration Tests
- **test_flows.py:** Full request flows with fixtures
- Mocked registry and filesystem
- End-to-end scenarios

### Coverage Target
- >85% for all modules
- Focus on error paths and edge cases
- Mock external dependencies (Supabase)

---

## Performance Considerations

1. **Caching**
   - Cache searches locally (future)
   - Cache registry metadata

2. **Pagination**
   - Registry queries paginated
   - `limit` parameter prevents large result sets

3. **Async I/O**
   - Non-blocking file and network operations
   - Concurrent handler initialization

4. **Lazy Loading**
   - Handlers init only when needed
   - Registry connections on demand

---

## Security

1. **No Credentials in Code**
   - Use environment variables
   - `.env.example` for setup

2. **Input Validation**
   - Pydantic schemas for all parameters
   - Reject invalid item types

3. **Path Traversal Prevention**
   - Constrain to designated directories
   - Resolve paths safely

4. **Registry Authentication**
   - Supabase requires `SUPABASE_SECRET_KEY`
   - Publish operations secured

---

## Roadmap

- [ ] **Phase 7:** RAG/Vector Search
- [ ] **Phase 8:** Authentication/Authorization
- [ ] **Phase 9:** Webhooks + Real-time
- [ ] **Phase 10:** Web UI
- [ ] **Phase 11:** Plugin System
