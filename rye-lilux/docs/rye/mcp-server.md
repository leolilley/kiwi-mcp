**Source:** Original implementation: `kiwi_mcp/server.py` adapted for RYE

# MCP Server Architecture

## Overview

RYE's MCP server exposes a **universal tool interface** to LLMs via the Model Context Protocol.

## Lilux vs RYE MCP Relationship

| Aspect             | Lilux (Microkernel)   | RYE (OS)                            |
| ------------------ | --------------------- | ----------------------------------- |
| **Entry Point**    | Not used (dependency) | `python -m rye.server`              |
| **LLM Calls**      | `mcp__lilux__*`       | `mcp__rye__*`                       |
| **User Install**   | `pip install lilux`   | `pip install rye-lilux` (gets both) |
| **Tool Discovery** | Fixed tool list       | Auto-scan .ai/ (dynamic)            |
| **Primary Use**    | Dependency only       | Main interface for LLMs             |

## MCP Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "rye": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "rye.server"],
      "environment": {
        "USER_SPACE": "/home/user/.ai"
      },
      "enabled": true
    }
  }
}
```

### Cursor IDE

```json
{
  "mcpServers": {
    "rye": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "rye.server"],
      "environment": {
        "USER_SPACE": "/home/user/.ai"
      },
      "alwaysAllow": [
        "mcp__rye__search",
        "mcp__rye__load",
        "mcp__rye__execute",
        "mcp__rye__sign",
        "mcp__rye__help"
      ]
    }
  }
}
```

## The 5 Universal MCP Tools

RYE exposes exactly **5 MCP tools** that work with **3 item types**:

| Item Type | Description | Location |
|-----------|-------------|----------|
| `directive` | Workflow definitions | `.ai/directives/` |
| `tool` | Executable tools | `.ai/tools/` |
| `knowledge` | Knowledge entries | `.ai/knowledge/` |

### 1. Search (`mcp__rye__search`)

**Purpose:** Search for items across directives, tools, or knowledge

```
Request:
{
  "item_type": "directive" | "tool" | "knowledge",
  "query": "lead generation",
  "source": "project" | "user",
  "limit": 10,
  "project_path": "/path/to/project"
}

Response:
{
  "results": [...],
  "total": 5,
  "query": "lead generation",
  "search_type": "keyword" | "vector_hybrid"
}
```

### 2. Load (`mcp__rye__load`)

**Purpose:** Load item content or copy between locations

```
Request:
{
  "item_type": "directive" | "tool" | "knowledge",
  "item_id": "create_tool",
  "source": "project" | "user",
  "destination": "project" | "user",  # Optional - omit for read-only
  "project_path": "/path/to/project"
}

Response:
{
  "content": "...",
  "metadata": {...},
  "path": "..."
}
```

### 3. Execute (`mcp__rye__execute`)

**Purpose:** Execute an item

```
Request:
{
  "item_type": "directive" | "tool" | "knowledge",
  "item_id": "scraper",
  "parameters": {"url": "https://..."},
  "project_path": "/path/to/project"
}

Response:
{
  "status": "success",
  "data": {...},
  "metadata": {"duration_ms": 123}
}
```

**Execution behavior by item type:**
- `directive`: Returns parsed XML for agent to follow
- `tool`: Executes tool via executor chain → primitives
- `knowledge`: Returns knowledge content

### 4. Sign (`mcp__rye__sign`)

**Purpose:** Validate and sign an item file

```
Request:
{
  "item_type": "directive" | "tool" | "knowledge",
  "item_id": "my_directive",
  "project_path": "/path/to/project",
  "parameters": {"location": "project"}
}

Response:
{
  "status": "signed",
  "path": "...",
  "signature": "..."
}
```

**Batch signing:** Use glob patterns like `demos/meta/*`

### 5. Help (`mcp__rye__help`)

**Purpose:** Get help and usage guidance

```
Request:
{
  "topic": "overview" | "search" | "load" | "execute" | "sign" | "directives" | "tools" | "knowledge"
}

Response:
{
  "status": "help",
  "topic": "search",
  "content": "..."
}
```

## Server Startup

```bash
python -m rye.server
```

**Process:**
1. Initialize RYE server
2. Scan .ai/tools/ directory
3. Build tool registry
4. Register 5 MCP tools
5. Start listening for LLM requests

## Tool Discovery Flow

```
Server Startup
    │
    ├─→ discovery.py scans .ai/tools/
    │
    ├─→ Find all .py and .yaml files
    │
    ├─→ Extract metadata from each
    │   ├─ __version__, __tool_type__
    │   ├─ __executor_id__, __category__
    │   ├─ CONFIG_SCHEMA
    │   └─ ENV_CONFIG (if runtime)
    │
    ├─→ Build tool registry
    │   └─ All tools indexed
    │
    └─→ MCP server ready
        └─ LLM can call 5 universal tools
```

## Request/Response Flow

```
LLM
    │
    └─→ JSON-RPC Request (MCP)
        │
        ├─→ mcp__rye__search
        │   └─→ RYE tool registry lookup
        │
        ├─→ mcp__rye__load
        │   └─→ Load tool metadata
        │
        ├─→ mcp__rye__execute
        │   ├─→ Universal executor routes
        │   ├─→ ENV_CONFIG resolution
        │   ├─→ Lilux primitive execution
        │   └─→ Result returned
        │
        ├─→ mcp__rye__sign
        │   └─→ Sign with credentials
        │
        └─→ mcp__rye__help
            └─→ Return help text
                │
                └─→ JSON-RPC Response (MCP)
                    │
                    └─→ Back to LLM
```

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `USER_SPACE` | User tool directory | `~/.ai` |
| `RYE_DEBUG` | Enable debug logging | `false` |
| `RYE_PORT` | Server port | `8000` |

### Server Settings

```python
# rye/server.py (pseudocode)

class RYEServer:
    def __init__(self):
        self.tool_registry = {}
        self.user_space = os.getenv("USER_SPACE", "~/.ai")
        self.debug = os.getenv("RYE_DEBUG", "false").lower() == "true"
    
    def start(self):
        # Discover all tools
        self._discover_tools()
        
        # Register MCP tools
        self._register_mcp_tools()
        
        # Start listening
        self._start_server()
    
    def _discover_tools(self):
        """Scan .ai/tools/ and build registry."""
        for tool_file in glob.glob("**/*.py", recursive=True):
            metadata = self._extract_metadata(tool_file)
            self.tool_registry[metadata["name"]] = metadata
    
    def _register_mcp_tools(self):
        """Register 5 universal MCP tools."""
        self.register_tool("mcp__rye__search", self.search)
        self.register_tool("mcp__rye__load", self.load)
        self.register_tool("mcp__rye__execute", self.execute)
        self.register_tool("mcp__rye__sign", self.sign)
        self.register_tool("mcp__rye__help", self.help)
```

## Tool Names from LLM Perspective

- `mcp__rye__search` - Universal search (auto-discovered from .ai/)
- `mcp__rye__load` - Universal load (auto-discovered from .ai/)
- `mcp__rye__execute` - Universal execute (auto-discovered from .ai/)
- `mcp__rye__sign` - Universal sign (auto-discovered from .ai/)
- `mcp__rye__help` - Universal help (auto-discovered from .ai/)

## LLM Workflow

### Example: Execute Git Command

```
LLM: "Check git status"
    │
    ├─→ Call mcp__rye__search("git")
    │   └─→ Returns: [{name: "git", category: "capabilities", ...}]
    │
    ├─→ Call mcp__rye__load("git")
    │   └─→ Returns: {schema: {...}, description: "..."}
    │
    └─→ Call mcp__rye__execute({
            name: "git",
            parameters: {command: "status"}
        })
        └─→ Returns: {status: "success", result: {...}}
            │
            └─→ LLM presents result to user
```

## Key Points

- **RYE is the main MCP entry point** - not Lilux
- **LLM talks to RYE** → RYE universal executor routes to Lilux
- **User installs RYE** → gets OS + microkernel
- **RYE scans .ai/tools/** → builds dynamic tool registry
- **5 universal tools** → search, load, execute, sign, help
- **Auto-discovery** → new tools immediately available
- **Dynamic registry** → no hardcoded tool list

## Related Documentation

- [[universal-executor/routing]] - How tools are executed
- [[universal-executor/overview]] - Universal executor architecture
- [[categories/mcp]] - MCP tools in RYE
- [[bundle/structure]] - Bundle organization

