# COMPLETE Kiwi-MCP Data-Driven Architecture Analysis

**Date:** 2026-01-30
**Purpose:** Complete analysis of .ai/tools/ structure for Lilux/RYE migration

---

## All Tool Categories in .ai/

### 1. Primitives (`.ai/tools/rye/primitives/`)

**Role:** Base executors - `__executor_id__ = None`

**Schema Location:** `.ai/tools/rye/primitives/*.py` (bundled with RYE)
**Code Location:** `lilux/primitives/*.py` (Lilux package)

| File               | Description             | Type          |
| ------------------ | ----------------------- | ------------- |
| subprocess.py      | Shell command execution | Base executor |
| http_client.py     | HTTP requests           | Base executor |
| lockfile.py        | Lockfile structures     | Base executor |
| chain_validator.py | Chain validation        | Base executor |

### 2. Runtimes (`.ai/tools/rye/runtimes/`)

**Role:** Language-specific executors - `__executor_id__` points to primitives

**Schema Location:** `.ai/tools/rye/runtimes/*.py` (bundled with RYE - schemas only)
**Code Location:** No separate runtime code - runtimes use primitives via `__executor_id__`

| File                | Description            | **executor_id** | Language |
| ------------------- | ---------------------- | --------------- | -------- |
| python_runtime.py   | Python script executor | "subprocess"    | Python   |
| node_runtime.py     | Node.js executor       | "subprocess"    | Node.js  |
| mcp_http_runtime.py | HTTP-based executor    | "http_client"   | Generic  |

**Key Features:**

- Declare `ENV_CONFIG` for environment resolution
- Use template variables `${VAR}` for kernel to resolve
- Validate child tools via `VALIDATION`

### 3. Capabilities (`.ai/tools/rye/capabilities/`)

**Role:** System capability providers

| File       | Description              | Type |
| ---------- | ------------------------ | ---- |
| db.py      | Database capabilities    | ?    |
| fs.py      | File system capabilities | ?    |
| git.py     | Git capabilities         | ?    |
| mcp.py     | MCP capabilities         | ?    |
| net.py     | Network capabilities     | ?    |
| process.py | Process capabilities     | ?    |

### 4. Telemetry (`.ai/tools/rye/telemetry/`)

**Role:** Telemetry management

| File                   | Description              | Type        |
| ---------------------- | ------------------------ | ----------- |
| configure_telemetry.py | Enable/disable telemetry | Python tool |
| telemetry_status.py    | View telemetry stats     | Python tool |
| clear_telemetry.py     | Clear telemetry data     | Python tool |
| export_telemetry.py    | Export stats for publish | Python tool |

### 5. Python Tools & Libraries (Not in Base RYE Package)

**Role:** Python-specific tools and shared code (separate category - not bundled)

| Directory/File    | Description               | **executor_id**  |
| ----------------- | ------------------------- | ---------------- |
| (other tools)     | User-defined Python tools | `python_runtime` |

**Pattern:**

- Root contains Python tools (`__tool_type__ = "python"`)
- Tools can import from `lib/` directory

### 6. Utility Tools (`.ai/tools/rye/utility/`)

**Role:** General utility tools

| File               | Description             | **executor_id**  |
| ------------------ | ----------------------- | ---------------- |
| http_test.py       | Test HTTP requests      | "http_client"    |
| hello_world.py     | Demonstration tool      | "python_runtime" |
| test_proxy_pool.py | Test proxy pool library | "python_runtime" |
| (other tools)      | Various utilities       | Various          |

### 7. MCP Tools (`.ai/tools/rye/mcp/`)

**Role:** MCP (Model Context Protocol) related tools

| File                 | Description         | Type             |
| -------------------- | ------------------- | ---------------- |
| mcp_tool_template.py | MCP tool template   | "python_runtime" |
| mcp_discover.py      | MCP tool discovery  | "python_runtime" |
| mcp_call.py          | MCP tool invocation | "python_runtime" |
| context7.py          | Context management  | "python_runtime" |
| \*.yaml              | Configuration files | Config           |

**YAML Config Files:**

- mcp_stdio.yaml - MCP stdio configuration
- mcp_http.yaml - MCP HTTP configuration
- mcp_tool_template.yaml - Tool template

### 8. Extractors (`.ai/tools/rye/extractors/`)

**Role:** Data extraction utilities

| Subdirectory/File | Description               | Type |
| ----------------- | ------------------------- | ---- |
| directive/        | Directive data extraction |      |
| knowledge/        | Knowledge data extraction |      |
| tool/             | Tool metadata extraction  |      |

**Extractors:**
| File | Description |
| ----- | ----------- |
| markdown_xml.py | Extract XML from markdown |
| markdown_frontmatter.py | Extract frontmatter from markdown |
| javascript_extractor.py | Extract data from JavaScript |
| python_extractor.py | Extract data from Python |
| yaml_extractor.py | Extract data from YAML |

### 9. Protocol (`.ai/tools/rye/protocol/`)

**Role:** Protocol implementation

| File               | Description               |
| ------------------ | ------------------------- |
| jsonrpc_handler.py | JSON-RPC protocol handler |

### 10. LLM (`.ai/tools/rye/llm/`)

**Role:** LLM-related tools and configurations

| File                    | Description                     | Type   |
| ----------------------- | ------------------------------- | ------ |
| anthropic_messages.yaml | Anthropic message format config | Config |
| openai_chat.yaml        | OpenAI chat config              | Config |
| pricing.yaml            | LLM API pricing config          | Config |

### 11. Sinks (`.ai/tools/rye/sinks/`)

**Role:** Event sinks (output destinations)

| File              | Description          | **executor_id**    |
| ----------------- | -------------------- | ------------------ |
| websocket_sink.py | WebSocket event sink | "python" (runtime) |

### 12. Threads (`.ai/tools/rye/threads/`)

**Role:** Threading and async execution

| File                    | Description                |
| ----------------------- | -------------------------- |
| anthropic_thread.yaml   | Anthropic thread config    |
| expression_evaluator.py | Expression evaluation      |
| inject_message.py       | Message injection          |
| openai_thread.yaml      | OpenAI thread config       |
| pause_thread.py         | Pause thread execution     |
| read_transcript.py      | Read thread transcript     |
| resume_thread.py        | Resume thread execution    |
| safety_harness.py       | Safety guard for execution |
| spawn_thread.py         | Spawn new threads          |
| thread_directive.yaml   | Thread directive config    |
| thread_directive.py     | Thread directive handler   |
| thread_registry.py      | Thread registration        |

### 13. Parsers (`.ai/tools/rye/parsers/`)

**Role:** Data parsing utilities

| File                    | Description             | Type   |
| ----------------------- | ----------------------- | ------ |
| markdown_xml.py         | Parse XML from markdown | Parser |
| markdown_frontmatter.py | Parse YAML frontmatter  | Parser |
| python_ast.py           | Parse Python AST        | Parser |
| yaml.py                 | Parse YAML files        | Parser |

### 14. Registry (`.ai/tools/rye/registry/`)

**Role:** Registry operations

| File        | Description                    | **executor_id** |
| ----------- | ------------------------------ | --------------- |
| registry.py | Registry operations (all-in-one) | "http_client"   |

---

## Complete Directory Structure

```
.ai/
├── tools/                              # All tools and executors
│   ├── rye/                           # RYE's bundled tool category (auto-installed)
│   │   │
│   │   ├── primitives/                   # LAYER 1: Primitive schemas
│   │   │   ├── subprocess.py              # Shell schema
│   │   │   ├── http_client.py             # HTTP schema
│   │   │   ├── lockfile.py               # Lockfile schema
│   │   │   ├── auth.py                  # Auth schema
│   │   │   └── chain_validator.py       # Chain schema
│   │   │
│   │   ├── runtimes/                     # LAYER 2: Runtime schemas
│   │   │   ├── python_runtime.py          # Python (ENV_CONFIG for Python path)
│   │   │   ├── node_runtime.py            # Node.js
│   │   │   └── mcp_http_runtime.py       # HTTP-based
│   │   │
│   │   ├── capabilities/                 # System capabilities
│   │   │   ├── db.py                    # Database
│   │   │   ├── fs.py                    # File system
│   │   │   ├── git.py                   # Git
│   │   │   ├── mcp.py                   # MCP protocol
│   │   │   ├── net.py                   # Network
│   │   │   └── process.py               # Process
│   │   │
│   │   ├── telemetry/                    # Telemetry tools
│   │   │   ├── configure_telemetry.py   # Enable/disable
│   │   │   ├── telemetry_status.py      # View stats
│   │   │   ├── clear_telemetry.py       # Clear data
│   │   │   └── export_telemetry.py      # Export stats
│   │   │
│   │   ├── extractors/                   # Data extraction
│   │   │   ├── directive/              # Directive extractors
│   │   │   │   └── markdown_xml.py     # Extract XML from directive markdown
│   │   │   ├── knowledge/              # Knowledge extractors
│   │   │   │   └── markdown_frontmatter.py # Extract frontmatter from knowledge
│   │   │   └── tool/                   # Tool extractors
│   │   │       ├── javascript_extractor.py # Extract from JS tools
│   │   │       ├── python_extractor.py     # Extract from Python tools
│   │   │       └── yaml_extractor.py       # Extract from YAML tools
│   │   │
│   │   ├── protocol/                     # Protocol implementations
│   │   │   └── jsonrpc_handler.py       # JSON-RPC
│   │   │
│   │   ├── sinks/                        # Event sinks
│   │   │   ├── file_sink.py             # File output sink
│   │   │   ├── null_sink.py             # Null/discard sink
│   │   │   └── websocket_sink.py        # WebSocket sink
│   │   │
│   │   ├── threads/                      # Async execution
│   │   │   ├── anthropic_thread.yaml
│   │   │   ├── openai_thread.yaml
│   │   │   ├── expression_evaluator.py
│   │   │   ├── inject_message.py
│   │   │   ├── pause_thread.py
│   │   │   ├── read_transcript.py
│   │   │   ├── resume_thread.py
│   │   │   ├── safety_harness.py
│   │   │   ├── spawn_thread.py
│   │   │   ├── thread_directive.yaml
│   │   │   ├── thread_directive.py
│   │   │   └── thread_registry.py
│   │   │
│   │   ├── mcp/                          # MCP tools + configs
│   │   │   ├── mcp_tool_template.py   # Tool template
│   │   │   ├── mcp_discover.py        # Tool discovery
│   │   │   ├── mcp_call.py            # Tool invocation
│   │   │   ├── context7.py             # Context management
│   │   │   ├── mcp_stdio.yaml          # MCP stdio config
│   │   │   ├── mcp_http.yaml           # MCP HTTP config
│   │   │   └── ...                     # More MCP tools/configs
│   │   │
│   │   ├── llm/                          # LLM configs
│   │   │   ├── anthropic_messages.yaml
│   │   │   ├── openai_chat.yaml
│   │   │   ├── pricing.yaml
│   │   │   └── ...                     # More configs
│   │   │
│   │   ├── parsers/                      # Data parsers
│   │   │   ├── markdown_xml.py           # Parse XML from markdown
│   │   │   ├── markdown_frontmatter.py   # Parse YAML frontmatter
│   │   │   ├── python_ast.py            # Parse Python AST
│   │   │   └── yaml.py                  # Parse YAML files
│   │   │
│   │   ├── registry/                     # Registry operations
│   │   │   └── registry.py              # All registry operations (auth, push, pull, keys)
│   │   │
│   │   ├── utility/                     # General utilities
│   │   │   ├── http_test.py             # __executor_id__=http_client
│   │   │   ├── hello_world.py           # __executor_id__=python_runtime
│   │   │   └── test_proxy_pool.py       # __executor_id__=python_runtime
│   │   │
│   │   └── examples/                    # Example tools
│   │       ├── git_status/
│   │       │   └── tool.yaml           # Git status example
│   │       └── health_check/
│   │           └── tool.yaml           # Health check example
│   │
│   ├── python/                        # Python tools & libraries (separate category)
│   │   ├── lib/                      # Shared libraries
│   │   └── *.py                      # Python tools
│   │
│   └── {other-categories}/            # Other tool categories
│       ├── utility/                     # General utilities
│       └── user-defined/                # User-created categories
│
├── directives/                         # Directive definitions
│   ├── core/                          # Core directives
│   ├── implementation/                 # Implementation directives
│   ├── operations/                     # Operation directives
│   ├── workflows/                      # Workflow directives
│   └── ...                             # More categories
│
└── knowledge/                          # Knowledge entries
    ├── system/                           # System knowledge
    ├── patterns/                         # Design patterns
    └── ...                             # More categories
```

---

## Metadata Patterns by Category

### Primitives

```python
# .ai/tools/rye/primitives/subprocess.py (SCHEMA ONLY)
__tool_type__ = "primitive"
__executor_id__ = None  # ← Indicates base executor
__category__ = "primitives"
__version__ = "1.0.1"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "env": {"type": "object"},
        "cwd": {"type": "string"},
        "timeout": {"type": "integer", "default": 300},
    },
    "required": ["command"]
}
```

**Code Implementation:** Actual execution logic lives in `lilux/primitives/subprocess.py`.

### Runtimes

```python
# .ai/tools/rye/runtimes/python_runtime.py (SCHEMA ONLY)
__tool_type__ = "runtime"
__executor_id__ = "subprocess" | "http_client" | ...  # ← Delegates to primitive
__category__ = "runtimes"
__version__ = "2.0.0"

ENV_CONFIG = {
    "interpreter": {
        "type": "venv_python",
        "search": ["project", "user", "system"],
        "var": "RYE_PYTHON",  # ← Kernel resolves this
        "fallback": "python3",
    },
}

CONFIG = {
    "command": "${RYE_PYTHON}",  # ← Template variable
    "args": [],
    "timeout": 300,
}
```

### Python Tools

```python
# Tool
__tool_type__ = "python"
__executor_id__ = "python_runtime"  # ← Delegates to Python runtime

# Library
# No __executor_id__ (libraries aren't executable)
```

### Utility Tools

```python
__tool_type__ = "python"
__executor_id__ = "http_client"  # Direct to primitive
```

### MCP Tools

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "mcp"

# Use YAML config files for MCP protocol
# anthropic_thread.yaml, openai_thread.yaml, etc.
```

---

## Critical Insights for RYE Migration

### 1. Everything is a Tool

**ALL categories must be organized under `.ai/tools/{category}/`:**

- `primitives/` - Primitive schemas
- `runtimes/` - Runtime schemas
- `capabilities/` - System capabilities
- `telemetry/` - Telemetry tools
- `extractors/` - Data extraction utilities
- `protocol/` - Protocol implementations
- `sinks/` - Event sinks
- `threads/` - Async execution
- `mcp/` - MCP protocol tools
- `llm/` - LLM configs
- `registry/` - Registry operations
- `utility/` - General utilities
- `python/` - Python tools and `lib/` shared libraries

### 2. Category Organization

**Tools are organized by category:**

- `.ai/tools/rye/*` - RYE bundled tools (auto-installed with `pip install rye-lilux`)
- `~/.ai/tools/{user}/*` - User tools (manually created or pulled from registry)

**Everything follows same structure - no special "core" distinction.**

### 3. YAML Config Files Are Critical

Many tools use YAML configs:

- `.ai/tools/rye/mcp/mcp_stdio.yaml`
- `.ai/tools/rye/mcp/mcp_http.yaml`
- `.ai/tools/rye/mcp/mcp_tool_template.yaml`
- `.ai/tools/rye/llm/openai_chat.yaml`
- `.ai/tools/rye/llm/anthropic_messages.yaml`
- `.ai/tools/rye/threads/anthropic_thread.yaml`
- `.ai/tools/rye/threads/openai_thread.yaml`

**These configs MUST be bundled and loaded dynamically.**

### 4. Library Pattern (python/lib/)

Shared libraries follow this pattern:

```python
# No __executor_id__ (libraries aren't executable)
```

**RYE must support importing from `python/lib/` directory within any category.**

### 5. Runtime Independence

Tools can use any runtime:

- Python tools → `__executor_id__ = "python_runtime"` (uses ENV_CONFIG)
- Node.js tools → `__executor_id__ = "node_runtime"` (if implemented)
- Bash tools → `__executor_id__ = "subprocess"` (direct to primitive)
- HTTP tools → `__executor_id__ = "http_client"` (direct to primitive)

### 6. Universal Discovery Pattern

The kernel must scan `.ai/tools/` recursively:

- Scan ALL categorys (rye, user, etc.)
- Parse metadata from Python files
- Parse metadata from YAML configs
- Build tool registry
- No hardcoded tool list

---

## Implementation Status Summary

### ✅ EXISTING CODE - Ready to Use

| Component | Status | Location | Action |
|-----------|--------|----------|--------|
| **Primitives** | ✅ Complete | `lilux/primitives/` | Copy/reference - no implementation needed |
| **Runtime Services** | ✅ Complete | `lilux/runtime/` | Use in UniversalExecutor |
| **Lockfile, Auth, Chain Validator** | ✅ Complete | `lilux/primitives/` | Ready to use |
| **EnvResolver** | ✅ Complete | `lilux/runtime/env_resolver.py` | Called at execution time |
| **AuthStore** | ✅ Complete | `lilux/runtime/auth.py` | Keychain integration ready |

### ⏳ INTENDED ARCHITECTURE - Needs Implementation

| Component | Status | Location | Action |
|-----------|--------|----------|--------|
| **Universal Executor** | ⏳ Design complete | `rye/executor/universal_executor.py` | Implement routing engine |
| **Tool Categories** | ⏳ Structure defined | `rye/.ai/tools/rye/` | Copy from kiwi-mcp, organize |
| **Tool Discovery** | ⏳ Pattern defined | `rye/executor/` | Scan `.ai/tools/` recursively |
| **Category Support** | ⏳ Pattern defined | RYE loader | Support rye/ + user/ categorys |

### ✅ PACKAGING - Already Set Up

| Component | Status | Configuration |
|-----------|--------|---|
| **.ai/ Bundle** | ✅ Ready | `package-data = { "rye" = [".ai/**/*"] }` |
| **Installation** | ✅ Ready | `pip install rye-lilux` → gets both + bundle |
| **ENV_CONFIG Resolution** | ✅ Timing confirmed | **At execution time** (not init) |

---

## Migration Implementation Plan

### Phase 6.1: Primitives (Already in Lilux)

- ✅ `lilux/primitives/subprocess.py` (code implementation)
- ✅ `lilux/primitives/http_client.py` (code implementation)
- Need: `.ai/tools/rye/primitives/subprocess.py` (schema)
- Need: `.ai/tools/rye/primitives/http_client.py` (schema)

### Phase 6.2: Runtimes (Create in .ai/tools/rye/)

- Need: `.ai/tools/rye/runtimes/python_runtime.py` (schema)
- Need: `.ai/tools/rye/runtimes/node_runtime.py` (schema)
- Need: `.ai/tools/rye/runtimes/mcp_http_runtime.py` (schema)

### Phase 6.3: Create Universal Executor (In RYE)

- `rye/executor/universal_executor.py`
- Parse metadata from all tool types
- Route to primitives/runtimes
- Support `__tool_type__` categories
- Handle multiple categorys (rye, user, etc.)

### Phase 6.4: Bundle All Tool Categories

Copy from kiwi-mcp to `rye/.ai/tools/rye/`:

- `primitives/`
- `runtimes/`
- `capabilities/`
- `telemetry/`
- `extractors/`
- `protocol/`
- `sinks/`
- `threads/`
- `mcp/`
- `llm/`
- `registry/`
- `utility/`
- `python/lib/`

### Phase 6.5: Handle YAML Configs

- Bundle YAML config files
- Implement dynamic config loading
- Support template variables

### Phase 6.6: Implement Tool Discovery

- Scan `.ai/tools/` recursively (all categorys)
- Parse metadata from Python files
- Parse metadata from YAML configs
- Build tool registry

---

## Architecture Comparison

| Layer          | kiwi-mcp Implementation               | Lilux/RYE Target                                                                  |
| -------------- | ------------------------------------- | --------------------------------------------------------------------------------- |
| **Primitives** | `.ai/tools/primitives/*.py` (schemas) | Schemas: `.ai/tools/rye/primitives/*.py`<br>Code: `lilux/primitives/*.py`         |
| **Runtimes**   | `.ai/tools/runtimes/*.py` (schemas)   | Schemas: `.ai/tools/rye/runtimes/*.py`<br>Code: No separate code - use primitives |
| **Tools**      | `.ai/tools/{category}/`               | `.ai/tools/{category}/` (organized by category)                                   |
| **Categories** | None (flat)                           | Organized by category (rye/, python/, etc.)                                       |
| **Discovery**  | Manual import                         | Auto-scan `.ai/tools/` (all categories)                                           |
| **Configs**    | `.ai/tools/{category}/*.yaml`         | `.ai/tools/{category}/*.yaml` (organized by category)                             |

---

## Next Steps

1. **Copy primitive schemas** from kiwi-mcp to `.ai/tools/rye/primitives/`
2. **Copy runtime schemas** from kiwi-mcp to `.ai/tools/rye/runtimes/`
3. **Implement universal executor** in RYE with category support
4. **Bundle all tool categories** to `.ai/tools/rye/`
5. **Implement tool discovery** with category scanning
6. **Test category organization** (rye vs python vs other categories)

This is **complete data-driven architecture** with category organization that provides maximum flexibility!

---

**Document Status:** Complete Analysis
**Based On:** kiwi-mcp implementation and Lilux/RYE architecture
**Last Updated:** 2026-01-30
