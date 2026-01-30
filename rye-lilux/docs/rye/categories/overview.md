**Source:** Original implementation: `.ai/tools/rye/` and tool organization in kiwi-mcp

# Tool Categories Overview

## Purpose

This overview describes all tool categories in RYE and how they relate to each other.

## Category Hierarchy

```
.ai/tools/
├── rye/                           # Bundled RYE categories
│   ├── primitives/                # Layer 1: Base executors
│   ├── runtimes/                  # Layer 2: Language runtimes
│   ├── capabilities/              # System features (git, fs, db, net, process, mcp)
│   ├── telemetry/                 # Monitoring and diagnostics
│   ├── extractors/                # Data extraction (directive/, knowledge/, tool/)
│   ├── parsers/                   # Data format parsing
│   ├── protocol/                  # Communication protocols (jsonrpc)
│   ├── sinks/                     # Event destinations
│   ├── threads/                   # Async execution
│   ├── mcp/                       # MCP protocol tools
│   ├── llm/                       # LLM provider configs
│   ├── registry/                  # Tool distribution
│   ├── utility/                   # General helpers
│   ├── examples/                  # Reference implementations
│   └── python/lib/                # Shared Python libraries
│
└── {other}/                       # User/custom categories
    └── {tools...}
```

## Categories (Complete List)

### 1. **Primitives** (2 execution primitives)
**Location:** `lilux/primitives/` (code) + `.ai/tools/rye/primitives/` (schemas)

Hardcoded execution engines - the terminal nodes of all tool execution.

**Key:** `__executor_id__ = None` (no delegation)

- subprocess - Shell command execution
- http_client - HTTP requests

**Note:** Only these 2 contain actual execution code. Everything else routes to them.

**See:** [[primitives]]

### 2. **Runtimes** (3 tools)
**Location:** `.ai/tools/rye/runtimes/`

Language-specific executors - Layer 2 of three-layer architecture.

**Key:** `__executor_id__` points to primitives, declares `ENV_CONFIG`

- python_runtime - Python script execution
- node_runtime - Node.js execution
- mcp_http_runtime - MCP HTTP client

**See:** [[runtimes]]

### 3. **Capabilities** (6 tools)
**Location:** `.ai/tools/rye/capabilities/`

System feature providers - Layer 3 user tools.

**Key:** All use `python_runtime`

- git - Version control
- fs - Filesystem operations
- db - Database operations
- net - Network operations
- process - Process management
- mcp - MCP operations

**See:** [[capabilities]]

### 4. **Telemetry** (7 tools)
**Location:** `.ai/tools/rye/telemetry/`

System monitoring and diagnostics.

**Key:** All use `python_runtime`

- telemetry_configure - Configure collection
- telemetry_status - Get status
- telemetry_clear - Clear data
- telemetry_export - Export data
- rag_configure - Configure RAG
- lib_configure - Configure libraries
- health_check - System health

**See:** [[telemetry]]

### 5. **Extractors** (3 subdirectories)
**Location:** `.ai/tools/rye/extractors/`

Data extraction from content files.

**Key:** All use `python_runtime`

**Subdirectories:**
- directive/ - Extract from XML directives
- knowledge/ - Extract from Markdown knowledge
- tool/ - Extract from Python/YAML tools

**See:** [[extractors]]

### 6. **Parsers** (4 tools)
**Location:** `.ai/tools/rye/parsers/`

Data format parsing.

**Key:** All use `python_runtime`

- markdown_xml - Parse Markdown + XML
- frontmatter - Parse YAML frontmatter + Markdown
- python_ast - Parse Python code
- yaml - Parse YAML configs

**See:** [[parsers]]

### 7. **Protocol** (1 tool)
**Location:** `.ai/tools/rye/protocol/`

Communication protocol implementations.

**Key:** Uses `python_runtime`

- jsonrpc_handler - JSON-RPC protocol

**See:** [[protocol]]

### 8. **Sinks** (3 tools)
**Location:** `.ai/tools/rye/sinks/`

Event destination handlers.

**Key:** All use `python_runtime`

- file_sink - Write to files
- null_sink - Discard events
- websocket_sink - Send to WebSocket

**See:** [[sinks]]

### 9. **Threads** (12 tools + YAML)
**Location:** `.ai/tools/rye/threads/`

Async execution and thread management.

**Key:** All use `python_runtime`

**Tools:**
- thread_create, thread_read, thread_update, thread_delete
- message_add, message_read, message_update, message_delete
- run_create, run_read, run_update, run_step_read

**Configs:**
- anthropic_thread.yaml
- openai_thread.yaml

**See:** [[threads]]

### 10. **MCP** (3 tools + YAML)
**Location:** `.ai/tools/rye/mcp/`

Model Context Protocol support.

**Key:** Mixed executors

**Tools:**
- mcp_call - Execute MCP calls
- mcp_server - Run MCP server
- mcp_client - Create MCP client

**Configs:**
- mcp_stdio.yaml
- mcp_http.yaml
- mcp_ws.yaml

**See:** [[mcp]]

### 11. **LLM** (5 configs)
**Location:** `.ai/tools/rye/llm/`

LLM provider configurations.

**Key:** YAML configs (not executable)

**Configs:**
- openai_chat.yaml - OpenAI Chat API
- openai_completion.yaml - OpenAI Completion API
- anthropic_messages.yaml - Anthropic Messages API
- anthropic_completion.yaml - Anthropic Completion API
- pricing.yaml - Token pricing

**See:** [[llm]]

### 12. **Registry** (1 tool)
**Location:** `.ai/tools/rye/registry/`

Tool distribution and package management.

**Key:** Uses `http_client`

- registry.py - Publish, pull, search tools

**Operations:** publish, pull, search, auth, key

**See:** [[registry]]

### 13. **Utility** (3 tools)
**Location:** `.ai/tools/rye/utility/`

General-purpose helpers.

**Key:** Mixed executors

- http_test - Test HTTP endpoints
- hello_world - Demo/test tool
- test_proxy_pool - Test proxy functionality

**See:** [[utility]]

### 14. **Examples** (2 tools)
**Location:** `.ai/tools/rye/examples/`

Reference implementations.

**Key:** Use `python_runtime`

- git_status - Git operations example
- health_check - System diagnostics example

**See:** [[examples]]

### 15. **Python Library** (Shared modules)
**Location:** `.ai/tools/rye/python/lib/`

Shared Python libraries for tools.

**Key:** `__tool_type__ = "python_lib"` (not executable)

- proxy_pool.py - Shared proxy pool
- (other shared modules)

**See:** [[python]]

### Category Summary Table

| Category | Count | Type | Executor | Purpose |
|----------|-------|------|----------|---------|
| Primitives | 2 | Schema | None | Execution engines |
| Runtimes | 3 | Schema | subprocess, http | Language runtimes |
| Capabilities | 6 | Python | python_runtime | System features |
| Telemetry | 7 | Python | python_runtime | Monitoring |
| Extractors | 3 dirs | Python | python_runtime | Data extraction |
| Parsers | 4 | Python | python_runtime | Format parsing |
| Protocol | 1 | Python | python_runtime | Protocols |
| Sinks | 3 | Python | python_runtime | Event destinations |
| Threads | 12 + YAML | Python | python_runtime | Async execution |
| MCP | 3 + YAML | Mixed | Mixed | MCP protocol |
| LLM | 5 | YAML | N/A | LLM configs |
| Registry | 1 | Python | http_client | Tool distribution |
| Utility | 3 | Python | Mixed | Helpers |
| Examples | 2 | Python | python_runtime | Reference impls |
| Python/Lib | N | Python | N/A | Shared libraries |

**Total:** ~80+ tools + configs in bundled RYE

## Category Dependencies

```
Primitives (Layer 1)
    │
    ├─→ Runtimes (Layer 2)
    │   ├─ Declare ENV_CONFIG
    │   └─ Delegate to Primitives
    │
    └─→ Tools (Layer 3)
        ├─ Capabilities
        ├─ Telemetry
        ├─ Extractors
        ├─ Parsers
        ├─ Protocol
        ├─ Sinks
        ├─ Threads
        ├─ MCP
        ├─ Registry
        ├─ Utility
        └─ Examples
            │
            └─ Use Runtimes & Primitives
```

## Auto-Discovery

All categories are auto-discovered:

```
RYE Startup
    │
    ├─→ Scan .ai/tools/rye/*/*.py
    ├─→ Scan .ai/tools/rye/*/*.yaml
    ├─→ Scan .ai/tools/{other}/*/*.py
    │
    └─→ Build dynamic tool registry
        └─ MCP server exposes all tools
```

## Category Organization

- **RYE Category** (`.ai/tools/rye/`): Bundled tools (auto-installed)
- **Other Categorys** (`.ai/tools/{user}/`): Custom tools (user-created)

## Best Practices

1. **Extend via categories** - Create custom categories for organization
2. **Use appropriate executor** - Match tool to executor
3. **Follow metadata pattern** - Consistent `__version__`, `__tool_type__`, etc.
4. **Document CONFIG_SCHEMA** - Clear parameter documentation
5. **Handle errors gracefully** - Return error status in response

## Related Documentation

- [[../bundle/structure]] - Bundle directory organization
- [[../universal-executor/routing]] - How tools are routed
- [[../universal-executor/overview]] - Executor architecture
- [[../package/structure]] - Package organization
