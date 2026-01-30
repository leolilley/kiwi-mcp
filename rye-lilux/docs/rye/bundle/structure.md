**Source:** Original implementation: `.ai/` directory structure in kiwi-mcp

# Content Bundle Structure

## Overview

The content bundle (`.ai/` directory) contains all tool definitions, directives, and knowledge entries. It's bundled with RYE and deployed as data, not code.

## Bundle Organization

```
.ai/
├── tools/                           # All tool definitions
│   ├── rye/                         # RYE bundled tools (auto-installed)
│   │   ├── primitives/              # Layer 1: Execution primitives (2 files)
│   │   ├── runtimes/                # Layer 2: Language runtimes (3 files)
│   │   ├── capabilities/            # System capabilities (6 files)
│   │   ├── telemetry/               # Telemetry tools (7 files)
│   │   ├── extractors/              # Data extractors (3 subdirs)
│   │   │   ├── directive/
│   │   │   ├── knowledge/
│   │   │   └── tool/
│   │   ├── parsers/                 # Data parsers (4 files)
│   │   ├── protocol/                # Protocol implementations (1 file)
│   │   ├── sinks/                   # Event sinks (3 files)
│   │   ├── threads/                 # Async execution (12 files + yaml)
│   │   ├── mcp/                     # MCP tools (py + yaml)
│   │   ├── llm/                     # LLM configs (yaml)
│   │   ├── registry/                # Registry operations (1 file)
│   │   ├── utility/                 # Utilities (3 files)
│   │   ├── examples/                # Examples (2 files)
│   │   └── python/                  # Python shared libraries
│   │       └── lib/                 # Library modules
│   │
│   └── {other}/                     # User/custom tool categories
│       └── {category}/              # Any category (python, user, etc.)
│           └── *.py, *.yaml
│
├── directives/                      # Workflow definitions
│   ├── *.xml                        # Directive definitions
│   └── ...
│
└── knowledge/                       # Knowledge entries
    ├── *.md                         # Knowledge articles
    └── ...
```

## Category Definitions

### RYE Tool Categories (Under `.ai/tools/rye/`)

#### 1. Primitives (`rye/primitives/`)

**2 execution primitive schemas** - hardcoded execution with `__executor_id__ = None`

| File | Purpose |
|------|---------|
| `subprocess.py` | Shell command execution |
| `http_client.py` | HTTP requests with retry |

**Note:** Only subprocess and http_client are execution primitives. Other files in primitives/ (lockfile, chain_validator, integrity_verifier) are helper modules.

**Key:** All have `__executor_id__ = None` (no delegation)

#### 2. Runtimes (`rye/runtimes/`)

**3 language-specific executors** - add environment configuration on top of primitives

| File | Delegates To | Purpose |
|------|--------------|---------|
| `python_runtime.py` | subprocess | Python script execution |
| `node_runtime.py` | subprocess | Node.js script execution |
| `mcp_http_runtime.py` | http_client | HTTP-based MCP |

**Key:** All have `__executor_id__` pointing to primitives, declare `ENV_CONFIG`

#### 3. Capabilities (`rye/capabilities/`)

**6 system capability providers** - expose system features

| File | Executor | Purpose |
|------|----------|---------|
| `git.py` | python_runtime | Git operations |
| `fs.py` | python_runtime | Filesystem operations |
| `db.py` | python_runtime | Database operations |
| `net.py` | python_runtime | Network operations |
| `process.py` | python_runtime | Process management |
| `mcp.py` | python_runtime | MCP operations |

#### 4. Telemetry (`rye/telemetry/`)

**7 telemetry tools** - system monitoring and diagnostics

| File | Purpose |
|------|---------|
| `telemetry_configure.py` | Configure telemetry |
| `telemetry_status.py` | Get telemetry status |
| `telemetry_clear.py` | Clear telemetry data |
| `telemetry_export.py` | Export telemetry |
| `rag_configure.py` | Configure RAG |
| `lib_configure.py` | Configure libraries |
| `health_check.py` | System health check |

#### 5. Extractors (`rye/extractors/`)

**Data extraction utilities** - organized by type

```
extractors/
├── directive/                      # Extract from directives
│   ├── extract_directive_metadata.py
│   └── ...
├── knowledge/                      # Extract from knowledge
│   ├── extract_knowledge_metadata.py
│   └── ...
└── tool/                           # Extract from tools
    ├── extract_tool_metadata.py
    └── ...
```

#### 6. Parsers (`rye/parsers/`)

**4 data format parsers** - handle different content formats

| File | Purpose |
|------|---------|
| `markdown_xml.py` | Parse Markdown with XML |
| `frontmatter.py` | Parse frontmatter (YAML + Markdown) |
| `python_ast.py` | Parse Python AST |
| `yaml.py` | Parse YAML |

#### 7. Protocol (`rye/protocol/`)

**Protocol implementations** - communication protocols

| File | Purpose |
|------|---------|
| `jsonrpc_handler.py` | JSON-RPC protocol handler |

#### 8. Sinks (`rye/sinks/`)

**3 event sinks** - where events flow to

| File | Purpose |
|------|---------|
| `file_sink.py` | Write to files |
| `null_sink.py` | Discard events |
| `websocket_sink.py` | Send to WebSocket |

#### 9. Threads (`rye/threads/`)

**12 thread management tools** - async execution and threading

| File | Purpose |
|------|---------|
| `thread_create.py` | Create thread |
| `thread_read.py` | Read thread |
| `thread_update.py` | Update thread |
| `thread_delete.py` | Delete thread |
| `message_add.py` | Add message to thread |
| `message_read.py` | Read thread messages |
| `message_update.py` | Update message |
| `message_delete.py` | Delete message |
| `run_create.py` | Create run |
| `run_read.py` | Read run |
| `run_update.py` | Update run |
| `run_step_read.py` | Read run steps |

**YAML Configs:**
- `anthropic_thread.yaml` - Anthropic thread config
- `openai_thread.yaml` - OpenAI thread config

#### 10. MCP (`rye/mcp/`)

**MCP tools and configurations**

| File | Purpose |
|------|---------|
| `mcp_call.py` | Execute MCP calls |
| `mcp_server.py` | Run MCP server |
| `mcp_client.py` | MCP client |

**YAML Configs:**
- `mcp_stdio.yaml` - MCP stdio configuration
- `mcp_http.yaml` - MCP HTTP configuration
- `mcp_ws.yaml` - MCP WebSocket configuration

#### 11. LLM (`rye/llm/`)

**LLM provider configurations** - YAML config files only

| File | Purpose |
|------|---------|
| `openai_chat.yaml` | OpenAI Chat API config |
| `openai_completion.yaml` | OpenAI Completion API config |
| `anthropic_messages.yaml` | Anthropic Messages API config |
| `anthropic_completion.yaml` | Anthropic Completion API config |
| `pricing.yaml` | Token pricing config |

#### 12. Registry (`rye/registry/`)

**Registry operations** - publish/pull from registry

| File | Executor | Purpose |
|------|----------|---------|
| `registry.py` | http_client | Registry publish/pull/search |

**Operations:**
- `publish` - Publish to registry
- `pull` - Pull from registry
- `search` - Search registry
- `auth` - Registry authentication
- `key` - Manage registry keys

#### 13. Parsers (`rye/parsers/`)

Already listed above - 4 data format parsers

#### 14. Utility (`rye/utility/`)

**General utilities**

| File | Executor | Purpose |
|------|----------|---------|
| `http_test.py` | http_client | HTTP request testing |
| `hello_world.py` | python_runtime | Hello world example |
| `test_proxy_pool.py` | python_runtime | Proxy pool testing |

#### 15. Examples (`rye/examples/`)

**Example tools** - reference implementations

| File | Purpose |
|------|---------|
| `git_status.py` | Git status example |
| `health_check.py` | Health check example |

#### 16. Python Libraries (`rye/python/lib/`)

**Shared Python libraries** - imported by tools

| Module | Purpose |
|--------|---------|
| `proxy_pool.py` | Shared proxy pool implementation |
| (other shared libs) | Reusable Python modules |

**Key:** Libraries have `__tool_type__ = "python_lib"` (not executable)

## Tool Category Summary

| Category | Count | Type | Executor |
|----------|-------|------|----------|
| Primitives | 2 | Schemas | None |
| Runtimes | 3 | Schemas | subprocess, http_client |
| Capabilities | 6 | Python | python_runtime |
| Telemetry | 7 | Python | python_runtime |
| Extractors | 3 dirs | Python | python_runtime |
| Parsers | 4 | Python | python_runtime |
| Protocol | 1 | Python | python_runtime |
| Sinks | 3 | Python | python_runtime |
| Threads | 12 | Python + YAML | python_runtime |
| MCP | 3 py + YAML | Python + configs | python_runtime |
| LLM | 5 | YAML configs only | N/A |
| Registry | 1 | Python | http_client |
| Utility | 3 | Python | varies |
| Examples | 2 | Python | varies |
| Python Libs | N | Python | N/A (not executable) |

**Total:** ~80+ tools/configs in bundled RYE package

## Auto-Discovery Process

### Startup

```
RYE Server Startup
    │
    └─→ discovery.py scans .ai/tools/
        │
        ├─→ Find all Python files: **/*.py
        ├─→ Find all YAML files: **/*.yaml
        │
        └─→ For each file:
            ├─ Parse metadata
            ├─ Extract __tool_type__, __executor_id__, __category__
            ├─ Extract CONFIG_SCHEMA
            ├─ Extract ENV_CONFIG (if runtime)
            └─ Register in tool registry
```

### Tool Lookup

```
LLM requests tool: git(command="status")
    │
    └─→ Tool Registry lookup: "git"
        │
        └─→ Found: .ai/tools/rye/capabilities/git.py
            │
            ├─ __tool_type__ = "python"
            ├─ __executor_id__ = "python_runtime"
            ├─ __category__ = "capabilities"
            │
            └─→ Return tool definition to LLM
```

## Category Organization

### RYE Category (`.ai/tools/rye/`)

**Bundled with RYE package** - auto-installed via `pip install rye-lilux`

- All tool categories
- All 80+ tools
- All YAML configs
- Shared Python libraries

### User/Custom Categorys (`.ai/tools/{other}/`)

**User-defined tools** - can create any category

```
.ai/tools/
├── rye/                        # Bundled with RYE
├── python/                     # Example: Python tools
├── user/                       # Example: User tools
└── myproject/                  # Example: Project-specific tools
```

## Directory Metadata

### File-Level Metadata

```python
# .ai/tools/rye/capabilities/git.py

__version__ = "1.0.0"          # Tool version
__tool_type__ = "python"       # Type: primitive, runtime, python, python_lib
__executor_id__ = "python_runtime"  # Execution delegate
__category__ = "capabilities"  # Category category
```

### Directory-Level Organization

- **Category**: High-level grouping (capabilities, telemetry, etc.)
- **Category**: Top-level (rye, python, user, etc.)
- **Name**: Individual tool file

## Related Documentation

- [[../universal-executor/overview]] - Tool discovery and routing
- [[../categories/overview]] - All categories detailed
- [[../categories/extractors]] - Schema-driven extraction
- [[../categories/parsers]] - Content preprocessors
