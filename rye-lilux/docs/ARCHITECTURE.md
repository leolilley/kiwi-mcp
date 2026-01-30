# Lilux/RYE Architecture: Microkernel + Operating System (Data-Driven)

**Date:** 2026-01-30
**Status:** Architecture Complete - Implementation In Progress
**Purpose:** Clear separation between Lilux (microkernel) and RYE (operating system), with data-driven tool discovery

---

## Executive Summary

**RYE is to OS. Lilux is to microkernel.**

- **Lilux** = Microkernel (Generic execution primitives - dumb)
- **RYE** = Operating System Layer (Universal executor + content bundle - smart)

They are **separate packages** but developed in a **monorepo** for simplicity.

---

## Core Architecture: Three-Layer Data-Driven System

### Diagram: Layered Data-Driven Architecture

```
                     ┌─────────────────────┐
                     │      LLM/User       │
                     └─────────┬───────────┘
                               │ calls
                               ▼
          ┌───────────────────────────────────┐
          │      RYE (OS Layer)               │  ← "Operating System"
          │                                   │
          │  5 MCP Tools (work with 3 types)  │
          │  ┌─────────────────────────────┐  │
          │  │ search, load, execute,      │  │
          │  │ sign, help                  │  │
          │  └──────────┬──────────────────┘  │
          │             │ dispatch by item_type│
          │             ▼                     │
          │  ┌─────────────────────────────┐  │
          │  │ Handlers (per item type)     │  │
          │  │ ├─ DirectiveHandler         │  │
          │  │ ├─ ToolHandler              │  │
          │  │ └─ KnowledgeHandler         │  │
          │  └──────────┬──────────────────┘  │
          │             │ tool execute only   │
          │             ▼                     │
          │  ┌─────────────────────────────┐  │
          │  │ PrimitiveExecutor            │  │
          │  │ (chain resolution + routing) │  │
          │  └──────────┬──────────────────┘  │
          │             │                     │
          │             ▼                     │
          │  ┌─────────────────────────────┐  │
          │  │   LILUX MICROKERNEL         │  │  ← "Microkernel"
          │  │                             │  │
          │  │ Primitives (hardcoded):     │  │
          │  │   - subprocess             │  │
          │  │   - http_client            │  │
          │  └─────────────────────────────┘  │
          └───────────────────────────────────┘

          .ai/ Bundle (3 Item Types)
          ┌───────────────────────────────────┐
          │  directives/                      │  ← Workflow definitions
          │    └─ *.md (XML in markdown)      │
          │                                   │
          │  tools/                           │  ← Executable tools
          │    ├─ rye/                        │  ← RYE bundled tools
          │    │   ├─ primitives/            │  ← Primitive schemas
          │    │   ├─ runtimes/              │  ← Runtime schemas
          │    │   └─ ...                    │
          │    └─ {user}/                     │  ← User tools
          │                                   │
          │  knowledge/                       │  ← Knowledge entries
          │    └─ *.md (YAML frontmatter)     │
          │                                   │
          │  parsers/                         │  ← Content parsers
          │  vector/                          │  ← Vector search data
          └───────────────────────────────────┘
```

**Key relationships:**

- **LLM → RYE:** 5 MCP tools work with 3 item types (directive, tool, knowledge)
- **Dispatch:** Each MCP tool dispatches to the appropriate Handler based on `item_type`
- **Handlers:** DirectiveHandler, ToolHandler, KnowledgeHandler implement search/load/execute/sign
- **Tool execution only:** ToolHandler.execute → PrimitiveExecutor → Lilux primitives
- **.ai/ Bundle:** Contains directives, tools, and knowledge that handlers operate on
- **Primitives:** Only subprocess and http_client are hardcoded; everything else is data-driven

---

## Three-Layer Architecture

### Layer 1: Primitives (Lilux Package + RYE Schemas)

**Role:** Base executors - `__executor_id__ = None`

These are the actual execution implementations that don't delegate to anything else.

**Package Code Location:** `lilux/primitives/*.py`
**Schema Location:** `.ai/tools/rye/primitives/*.py` (bundled with RYE)

| File               | Description                    | Key Metadata             |
| ------------------ | ------------------------------ | ------------------------ |
| subprocess.py      | Shell command execution        | `__executor_id__ = None` |
| http_client.py     | HTTP requests with retry logic | `__executor_id__ = None` |
| lockfile.py        | Lockfile data structures       | `__executor_id__ = None` |
| chain_validator.py | Chain validation               | `__executor_id__ = None` |

**Schema Pattern:**

```python
# .ai/tools/rye/primitives/subprocess.py (SCHEMA ONLY - no code)
__version__ = "1.0.1"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "primitives"

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

**Code Implementation:** Actual execution logic lives in `lilux/primitives/subprocess.py` (package code).

### Layer 2: Runtimes (RYE Schemas + Optional Lilux Code)

**Role:** Language-specific executors - `__executor_id__` points to primitives

These add language-specific behavior on top of primitives (environment resolution, venv management, etc.).

**Schema Location:** `.ai/tools/rye/runtimes/*.py` (bundled with RYE all use subprocess or http_client primitives)

| File                | Description              | **executor_id** | ENV_CONFIG                      |
| ------------------- | ------------------------ | --------------- | ------------------------------- |
| python_runtime.py   | Python script execution  | "subprocess"    | Python interpreter resolution   |
| node_runtime.py     | Node.js script execution | "subprocess"    | Node.js interpreter resolution  |
| mcp_http_runtime.py | HTTP-based MCP runtime   | "subprocess"    | Connection pooling, retry logic |

**Schema Pattern:**

```python
# .ai/tools/rye/runtimes/python_runtime.py (SCHEMA ONLY)
__version__ = "2.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"

# Environment configuration - declares HOW to resolve interpreter
ENV_CONFIG = {
    "interpreter": {
        "type": "venv_python",
        "search": ["project", "kiwi", "user", "system"],
        "var": "RYE_PYTHON",  # ← Kernel resolves this variable
        "fallback": "python3",
    },
    "env": {
        "PYTHONUNBUFFERED": "1",
        "PROJECT_VENV_PYTHON": "${RYE_PYTHON}",  # ← Template variable
    },
}

# CONFIG uses ${RYE_PYTHON} which is resolved by kernel's EnvResolver
CONFIG = {"command": "${RYE_PYTHON}", "args": [], "timeout": 300}
```

**Key Features of Runtimes:**

1. **Environment Resolution**: Declare `ENV_CONFIG` for kernel to resolve
2. **Template Variables**: Use `${VAR_NAME}` for kernel to resolve
3. **Validation**: Validate child tools via `VALIDATION`
4. **Language-Specific**: Add Python/Node-specific logic (venv activation, path setup)

### Layer 3: Tools (`.ai/tools/{category}/`)

**Role:** User-defined tools that delegate to primitives OR runtimes via `__executor_id__`

These are the actual tools users create - data-defined, not hardcoded.

**Tool Categories:**

- `.ai/tools/rye/*` - RYE's bundled tools (auto-installed with pip)
- `.ai/tools/{other}/*` - Other tool categories

| Category      | Description                           | Example Tool        | **executor_id**  |
| ------------- | ------------------------------------- | ------------------- | ---------------- |
| utility/      | General utilities                     | http_test.py        | "http_client"    |
| mcp/          | MCP protocol tools                    | mcp_call.py         | "python_runtime" |
| extractors/   | Data extraction utilities             | markdown_xml.py     | "python_runtime" |
| protocol/     | Protocol implementations              | jsonrpc_handler.py  | "python_runtime" |
| sinks/        | Event sinks                           | websocket_sink.py   | "python_runtime" |
| threads/      | Async execution and thread management | thread_registry.py  | "python_runtime" |
| capabilities/ | System capabilities providers         | git.py              | "python_runtime" |
| telemetry/    | Telemetry management                  | telemetry_status.py | "python_runtime" |
| registry/     | Registry operations                   | registry.py         | "http_client"    |

**Tool Pattern:**

```python
# Tool example
__tool_type__ = "python"
__executor_id__ = "python_runtime"  # ← Delegates to Python runtime
__category__ = "utility"

def main(name: str = "World") -> str:
    return f"Hello, {name}!"

# Library example
# No __executor_id__ (libraries aren't executable)
```

**YAML Config Files:**

Many tools use YAML configs for declarative behavior:

- `.ai/tools/rye/mcp/mcp_stdio.yaml` - MCP stdio configuration
- `.ai/tools/rye/mcp/mcp_http.yaml` - MCP HTTP configuration
- `.ai/tools/rye/llm/openai_chat.yaml` - OpenAI chat config
- `.ai/tools/rye/llm/anthropic_messages.yaml` - Anthropic message format
- `.ai/tools/rye/threads/anthropic_thread.yaml` - Anthropic thread config
- `.ai/tools/rye/threads/openai_thread.yaml` - OpenAI thread config

---

## Universal Execution Pattern

### The Universal Executor's Role

The universal executor is a **data-driven router** that:
1. Reads tool metadata from `.ai/tools/`
2. Resolves executor chains recursively (no hardcoded lists!)
3. Routes to Lilux primitives via runtimes or direct delegation

```python
class UniversalExecutor:
    """
    Data-driven executor - resolves executor chains recursively.
    NO hardcoded executor IDs - all discovered from .ai/tools/ filesystem!
    """

    def __init__(self, ai_tools_path: Path, env_resolver: EnvResolver):
        self.ai_tools_path = ai_tools_path
        self.env_resolver = env_resolver
        # NO self.primitives or self.runtimes registries!

    def execute_tool(self, tool_path: Path, parameters: dict) -> Any:
        """
        Execute a tool by resolving its executor chain recursively.

        Chain: tool → executor_id → (runtime → executor_id) → ... → primitive
        """
        # Load tool metadata
        metadata = self._load_metadata(tool_path)
        executor_id = metadata.get("__executor_id__")

        if executor_id is None:
            # LAYER 1: This IS a primitive - execute directly
            return self._execute_primitive(tool_path, parameters)

        # DATA-DRIVEN: Resolve executor path from .ai/tools/ filesystem
        executor_path = self._resolve_executor_path(executor_id)

        # Load executor metadata (could be runtime or primitive)
        executor_metadata = self._load_metadata(executor_path)
        executor_type = executor_metadata.get("__tool_type__")

        if executor_type == "runtime":
            # LAYER 2: Resolve ENV_CONFIG at execution time
            resolved_env = self.env_resolver.resolve(
                executor_metadata.get("ENV_CONFIG"),
                context=self._get_context(tool_path)
            )
            # Merge resolved env into parameters
            parameters = {**parameters, **resolved_env}

        # RECURSIVE: Execute executor (runtime → runtime → ... → primitive)
        return self.execute_tool(executor_path, parameters)

    def _resolve_executor_path(self, executor_id: str) -> Path:
        """
        Resolve executor_id to actual path in .ai/tools/

        DATA-DRIVEN: Searches all categories, no hardcoded lists.
        """
        # Search .ai/tools/**/ for matching executor_id
        for category_dir in self.ai_tools_path.iterdir():
            if not category_dir.is_dir():
                continue

            # Check root of category
            potential_path = category_dir / f"{executor_id}.py"
            if potential_path.exists():
                return potential_path

            # Search subdirectories (primitives/, runtimes/, etc.)
            for sub_dir in category_dir.rglob("*.py"):
                if sub_dir.stem == executor_id:
                    return sub_dir

        raise ValueError(f"Executor '{executor_id}' not found in .ai/tools/")

    def _execute_primitive(self, tool_path: Path, parameters: dict) -> Any:
        """
        Execute a primitive by loading from Lilux package
        """
        primitive_name = tool_path.stem
        # Dynamic import from Lilux primitives
        primitive_module = importlib.import_module(f"lilux.primitives.{primitive_name}")
        return primitive_module.execute(parameters)
```

### Runtime Execution Pattern

Runtimes use ENV_CONFIG to declare environment needs:

```python
class PythonRuntime:
    """Python runtime executor."""

    # Environment configuration
    ENV_CONFIG = {
        "interpreter": {
            "type": "venv_python",
        "search": ["project", "rye", "user", "system"],
            "var": "RYE_PYTHON",
            "fallback": "python3",
        },
    }

    def execute(self, tool_path: Path, parameters: dict):
        # Kernel resolves ${RYE_PYTHON} based on ENV_CONFIG
        config = self._resolve_env_vars(tool_path, "subprocess")

        # Create subprocess with resolved Python path
        return subprocess.run(
            [config["command"], *config["args"]],
            env=config["env"],
        )
```

---

## Tool Discovery

### How Tools Are Found

The universal executor searches `.ai/tools/` and builds dynamic tool registry:

```python
def discover_tools(base_path: Path):
    """Discover all tools in system."""
    tools = {}

    # Scan all categorys in .ai/tools/
    for category_dir in base_path.iterdir():
        if not category_dir.is_dir():
            continue

        # Scan all categories in category
        for py_file in category_dir.rglob("**/*.py"):
            # Load module
            module = load_module(py_file)

            # Check if it's a tool
            if hasattr(module, "__tool_type__"):
                tool_id = f"{category_dir.name}/{py_file.stem}"
                tools[tool_id] = {
                    "path": py_file,
                    "category": category_dir.name,
                    "tool_type": getattr(module, "__tool_type__"),
                    "executor_id": getattr(module, "__executor_id__"),
                    "category": getattr(module, "__category__"),
                    "CONFIG_SCHEMA": getattr(module, "CONFIG_SCHEMA", None),
                    "ENV_CONFIG": getattr(module, "ENV_CONFIG", None),
                    "CONFIG": getattr(module, "CONFIG", None),
                }

    return tools
```

---

## Configuration Resolution

### Kernel's Environment Resolver

The kernel resolves environment variables for tools:

```python
class EnvResolver:
    """Resolve environment variables for tool execution."""

    def resolve(self, config_or_env_config) -> Dict[str, str]:
        """
        Resolve environment variables.

        If it's an ENV_CONFIG (runtime):
            - Search for interpreter (Python, Node, etc.)
            - Set VAR_NAME variable
            - Return resolved environment

        If it's a CONFIG (primitive):
            - Return resolved ${VAR} values
            - Add any env vars specified in env key
        """
        if "ENV_CONFIG" in config_or_env_config:
            # Runtime: resolve interpreter
            return self._resolve_runtime_env(config_or_env_config)
        else:
            # Primitive: template variables
            return self._resolve_template_vars(config_or_env_config)

    def _resolve_runtime_env(self, env_config: Dict) -> Dict[str, str]:
        """Resolve runtime environment configuration."""
        interpreter_config = env_config.get("interpreter", {})

        if interpreter_config.get("type") == "venv_python":
            var_name = interpreter_config.get("var", "PYTHON_PATH")
            fallback = interpreter_config.get("fallback", "python3")
            python_path = self._find_python(var_name, fallback, interpreter_config["search"])

            # Set environment variable
            os.environ[var_name] = python_path

            return {"PYTHON_PATH": python_path}
```

---

## Complete Directory Structure

### RYE .ai/ Bundle (Data-Driven)

```
.ai/ (Data-Driven Content Bundle)
├── tools/                              # All tools and executors
│   ├── rye/                           # RYE's bundled tool category (auto-installed)
│   │   │
│   │   ├── primitives/                   # Primitive schemas
│   │   │   ├── subprocess.py              # Shell schema
│   │   │   ├── http_client.py             # HTTP schema
│   │   │   ├── lockfile.py               # Lockfile schema
│   │   │   ├── auth.py                  # Auth schema
│   │   │   └── chain_validator.py       # Chain schema
│   │   │
│   │   ├── runtimes/                     # Runtime schemas
│   │   │   ├── python_runtime.py          # Python (ENV_CONFIG for Python path)
│   │   │   ├── node_runtime.py            # Node.js
│   │   │   └── mcp_http_runtime.py       # HTTP-based
│   │   │
│   │   ├── capabilities/                 # System capabilities
│   │   │   ├── git.py                   # Git operations
│   │   │   ├── fs.py                    # File system
│   │   │   ├── db.py                    # Database
│   │   │   ├── net.py                   # Network
│   │   │   ├── process.py               # Process management
│   │   │   └── mcp.py                   # MCP protocol
│   │   │
│   │   ├── telemetry/                    # Telemetry tools
│   │   │   ├── configure_telemetry.py   # Enable/disable
│   │   │   ├── telemetry_status.py      # View stats
│   │   │   └── clear_telemetry.py       # Clear data
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
│   │   │   └── jsonrpc_handler.py       # JSON-RPC handler
│   │   │
│   │   ├── sinks/                        # Event sinks
│   │   │   ├── file_sink.py             # File output sink
│   │   │   ├── null_sink.py             # Null/discard sink
│   │   │   └── websocket_sink.py        # WebSocket sink
│   │   │
│   │   ├── threads/                      # Async execution
│   │   │   ├── thread_registry.py       # Thread management
│   │   │   ├── spawn_thread.py         # Create threads
│   │   │   ├── pause_thread.py         # Pause threads
│   │   │   └── resume_thread.py        # Resume threads
│   │   │
│   │   ├── mcp/                          # MCP tools + configs
│   │   │   ├── mcp_tool_template.py   # Tool template
│   │   │   ├── mcp_discover.py        # Tool discovery
│   │   │   ├── mcp_call.py            # Tool invocation
│   │   │   ├── context7.py             # Context management
│   │   │   ├── mcp_stdio.yaml          # MCP stdio config
│   │   │   └── mcp_http.yaml           # MCP HTTP config
│   │   │
│   │   ├── llm/                          # LLM configs
│   │   │   ├── anthropic_messages.yaml
│   │   │   ├── openai_chat.yaml
│   │   │   └── pricing.yaml
│   │   │
│   │   ├── registry/                     # Registry operations
│   │   │   ├── publish_tool.py          # Publish to registry
│   │   │   ├── pull_tool.py             # Pull from registry
│   │   │   └── search_registry.py      # Search registry
│   │   │

│   │
│   └── {user}/                        # User tool categorys
│       ├── my-tools/                     # User's personal tools
│       └── another-category/             # Another user tool package
│
├── directives/                         # Directive definitions (markdown)
│   ├── core/                          # Core directives
│   ├── implementation/                 # Implementation directives
│   ├── operations/                     # Operation directives
│   └── workflows/                      # Workflow directives
│
└── knowledge/                          # Knowledge entries (markdown)
    ├── system/                           # System knowledge
    ├── patterns/                         # Design patterns
    └── ...                             # More categories
```

### Lilux Package (Code Implementation)

```
lilux/ (Microkernel Package)
├── primitives/             # LAYER 1: Base executors (ACTUAL CODE)
│   ├── subprocess.py      # Shell execution implementation
│   ├── http_client.py     # HTTP client implementation
│   ├── lockfile.py        # Lockfile manager implementation
│   ├── auth.py           # Keychain implementation
│   └── chain_validator.py # Chain validation implementation
│
├── runtime/                # Runtime services
│   ├── auth.py            # AuthStore (keychain)
│   ├── env_resolver.py     # EnvResolver (variable resolution)
│   └── lockfile_store.py  # Lockfile persistence
│
├── utils/                  # Minimal kernel helpers
│   ├── resolvers.py       # PathResolver (routing)
│   ├── logger.py
│   ├── paths.py
│   └── extensions.py     # Extension discovery
│
├── config/                 # Configuration
│   ├── search_config.py
│   └── vector_config.py
│
├── storage/                # Vector storage (RAG)
│   └── vector/
│
├── schemas/                # Schema definitions
│   └── tool_schema.py
│
├── handlers/               # Dumb routers (no content intelligence)
│   ├── directive/
│   ├── tool/
│   └── knowledge/
│
└── server.py               # MCP server (legacy - RYE is main entry)
```

---

---

## Implementation Status & Code Availability

### ✅ EXISTING: Primitives (Ready to Use)

All primitive implementations are **complete and identical** in both kiwi-mcp and lilux:

```
lilux/primitives/
├── subprocess.py ✅ (Complete implementation)
├── http_client.py ✅ (Complete implementation)
├── chain_validator.py ✅ (Complete implementation)
├── lockfile.py ✅ (Complete implementation)
├── errors.py ✅
├── executor.py ✅
├── integrity.py ✅
└── integrity_verifier.py ✅
```

**Action:** Copy or reference these files - no implementation needed.

### ✅ EXISTING: Runtime Services (Ready to Use)

All runtime service implementations exist in lilux:

```
lilux/runtime/
├── auth.py ✅ (AuthStore - keychain integration)
├── env_resolver.py ✅ (EnvResolver - template variable resolution)
└── lockfile_store.py ✅ (LockfileStore - concurrency management)
```

**Action:** Use these services in UniversalExecutor implementation.

### ⏳ INTENDED: Universal Executor (Needs Implementation)

The `rye/executor/universal_executor.py` is the **architectural pattern** - needs building:

- Load tool metadata from `.ai/tools/`
- Parse `__executor_id__` to route to primitives/runtimes
- Call `env_resolver.resolve()` at **execution time** (not init)
- Support multiple categorys (rye/, user/, etc.)

**Action:** Implement following the pattern shown below.

### ⏳ INTENDED: Tool Categories Organization (Needs Migration)

Tool categories need **copying from kiwi-mcp** to `rye/.ai/tools/rye/`:

```
rye/.ai/tools/rye/
├── primitives/ (schemas + code references)
├── runtimes/ (schemas only)
├── capabilities/
├── telemetry/
├── extractors/
├── protocol/
├── sinks/
├── threads/
├── mcp/
├── llm/
├── registry/
├── utility/
└── python/lib/ (shared libraries)
```

**Action:** Copy from kiwi-mcp structure, organize by category.

### ✅ EXISTING: .ai/ Bundle Structure

The `.ai/` directory is bundled with RYE package via:

```toml
# rye/pyproject.toml
[tool.setuptools]
package-data = { "rye" = [".ai/**/*"] }
```

**Installation Flow:**

```bash
pip install rye-lilux  # Gets lilux + rye + .ai/ bundle
```

---

## ENV_CONFIG Resolution Flow (Execution Time)

**CRITICAL:** ENV_CONFIG is resolved **at execution time**, not at init time.

### Resolution Flow

```
1. Tool Invocation (LLM → RYE)
   ↓
2. RYE loads tool metadata
   - If __executor_id__ = "python_runtime"
   - RYE loads .ai/tools/rye/runtimes/python_runtime.py
   ↓
3. RYE's universal executor calls EnvResolver
   - env_resolver.resolve(ENV_CONFIG, current_context)
   - Returns resolved environment variables
   ↓
4. Resolved environment passed to Lilux primitive
   - subprocess.execute(command, env=resolved_env)
   ↓
5. Lilux primitive executes with resolved environment
```

### Example: Python Runtime Resolution

```python
# .ai/tools/rye/runtimes/python_runtime.py declares:
ENV_CONFIG = {
    "interpreter": {
        "type": "venv_python",
        "search": ["project", "user", "system"],
        "var": "RYE_PYTHON",  # ← Variable name
        "fallback": "python3",
    },
    "env": {
        "PYTHONUNBUFFERED": "1",
        "PROJECT_VENV_PYTHON": "${RYE_PYTHON}",  # ← Template variable
    },
}

# At execution time:
# 1. env_resolver finds Python interpreter (searches "project", "user", "system")
# 2. Resolves ${RYE_PYTHON} → /path/to/project/.venv/bin/python3
# 3. Sets PYTHONUNBUFFERED=1 and PROJECT_VENV_PYTHON=/path/to/project/.venv/bin/python3
# 4. Passes resolved env to subprocess.execute()
```

**Source:** Original implementation: `kiwi_mcp/runtime/env_resolver.py` in kiwi-mcp

---

## Key Benefits of This Architecture

### 1. Three-Layer Separation

| Layer      | Role                       | **executor_id**               | Schema Location           | Code Location              |
| ---------- | -------------------------- | ----------------------------- | ------------------------- | -------------------------- |
| Primitives | Base executors             | None                          | .ai/tools/rye/primitives/ | lilux/primitives/          |
| Runtimes   | Language executors         | "subprocess", etc.            | .ai/tools/rye/runtimes/   | lilux/runtimes/ (optional) |
| Tools      | User-defined functionality | "subprocess", "runtime", etc. | .ai/tools/{category}/     | .ai/tools/{category}/      |

### 2. Runtime Independence

**Tools can use any runtime:**

- Python tools → `__executor_id__ = "python_runtime"` (uses ENV_CONFIG)
- Node.js tools → `__executor_id__ = "node_runtime"` (uses ENV_CONFIG)
- Bash tools → `__executor_id__ = "subprocess"` (direct to primitive)
- HTTP tools → `__executor_id__ = "http_client"` (direct to primitive)

### 3. Environment Configuration

**Runtimes declare environment needs via ENV_CONFIG:**

- How to find interpreter
- What environment variables to set
- Search order for interpreters

**Universal executor resolves these declaratively.**

### 4. Shared Libraries

### 5. Configuration-Driven Behavior

**Tools define behavior via metadata:**

- `CONFIG_SCHEMA` - JSON Schema for parameters
- `CONFIG` - Static configuration
- Template variables `${VAR}` for environment resolution

### 6. Extensibility

**Adding new capabilities:**

1. Add primitive schema to `.ai/tools/rye/primitives/` + code to `lilux/primitives/`
2. Add runtime schema to `.ai/tools/rye/runtimes/` + optional code

3. All tools automatically discoverable

### 7. Universal Discovery

**The system auto-discovers all tools:**

- Scans `.ai/tools/` recursively (all categories)
- Parses metadata from Python files
- Parses metadata from YAML configs
- Builds dynamic tool registry
- No hardcoded tool list

### 8. Category Organization

**Tools are organized by category:**

- `.ai/tools/rye/*` - RYE bundled tools (auto-installed)

- `.ai/tools/{other}/*` - Other tool categories

**Everything follows same structure - tools are tools.**

---

## Architecture Comparison

| Aspect              | Old Plan (Hardcoded)     | Correct Data-Driven                           |
| ------------------- | ------------------------ | --------------------------------------------- |
| Tool Definition     | Hardcoded 5 Python tools | Data files with metadata                      |
| Tool Discovery      | Manual imports           | Auto-scan .ai/tools/                          |
| Tool Language       | Python only              | Any language (if runtime exists)              |
| Tool Behavior       | Code-based               | Configuration-based (ENV_CONFIG)              |
| Tool Extensibility  | Code changes required    | Add primitives → all tools benefit            |
| Tool Organization   | No clear category        | Organized by category (rye/, user/, etc.)     |
| Runtime Support     | Embedded in tools        | Declarative via .ai/tools/runtimes/           |
| Primitives Location | Mixed (code + schemas)   | Separated: schemas in .ai/, code in lilux/    |
| Libraries           | Handled manually         | Dedicated python/lib/ directories by category |
| Config Files        | Embedded in code         | YAML files (declarative)                      |
| Execution Model     | 5 hardcoded tools        | Universal executor routing                    |
| Flexibility         | Low (fixed 5 tools)      | High (metadata-driven)                        |

---

## Package Configuration

### Lilux Microkernel (`lilux/pyproject.toml`)

```toml
[project]
name = "lilux"
version = "0.1.0"
description = "Lilux Microkernel - Generic execution primitives for AI agents"

dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "keyring>=23.0.0",
]
```

### RYE OS (`rye/pyproject.toml`)

```toml
[project]
name = "rye-lilux"
version = "0.1.0"
description = "RYE - AI operating system with universal tool executor running on Lilux microkernel"

dependencies = [
    "lilux>=0.1.0",  # ← Depends on microkernel
]

[project.scripts]
rye = "rye.server:main"  # ← RYE is main package!

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["rye"]
package-data = { "rye" = [".ai/**/*"] }  # Bundle .ai/ content
```

---

## MCP Configuration

### Example: Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "rye": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "rye.server"],  # ← RYE's entry point!
      "environment": {
        "USER_SPACE": "/home/leo/.ai",
      },
      "enabled": true
    }
  }
}
```

**Tool names from LLM perspective:**

- `mcp__rye__search` - Universal search (auto-discovered from .ai/)
- `mcp__rye__load` - Universal load (auto-discovered from .ai/)
- `mcp__rye__execute` - Universal execute (auto-discovered from .ai/)
- `mcp__rye__sign` - Universal sign (auto-discovered from .ai/)
- `mcp__rye__help` - Universal help (auto-discovered from .ai/)

---

## Summary: Microkernel + OS Architecture

| Aspect              | Lilux (Microkernel)          | RYE (OS)                                       |
| ------------------- | ---------------------------- | ---------------------------------------------- |
| **What**            | Generic execution primitives | Universal executor + data-driven tools         |
| **Analogy**         | Hardware microkernel         | Operating system                               |
| **Intelligence**    | Dumb - just executes         | Smart - understands content shapes             |
| **Extensibility**   | Add new primitives           | Add new tools/categories to .ai/               |
| **Package**         | `lilux`                      | `rye-lilux`                                    |
| **Entry Point**     | Not used (dependency)        | `python -m rye.server`                         |
| **LLM Calls**       | `mcp__lilux__*`              | `mcp__rye__*`                                  |
| **User Install**    | `pip install lilux`          | `pip install rye-lilux` (gets both)            |
| **Tool Discovery**  | Fixed tool list              | Auto-scan .ai/ (dynamic)                       |
| **Tool Categories** | 5 hardcoded tools            | All tools in .ai/tools/\* (by category)        |
| **Primitives**      | Code + schemas mixed         | Separated: code in lilux/, schemas in .ai/     |
| **Runtimes**        | Embedded in tools            | Declarative schemas in .ai/tools/rye/runtimes/ |
| **Libraries**       | Handled manually             | Not included in base RYE package               |
| **Config Files**    | Embedded in code             | YAML files in .ai/tools/rye/\*/                |
| **Categorys**       | None                         | .ai/tools/rye/_ + .ai/tools/{user}/_           |

**Relationship:** RYE (OS) imports Lilux (microkernel) primitives to execute intelligence. The universal executor routes data-driven tools to appropriate primitives based on metadata.

**Bottom line:**

- User installs RYE → gets OS + microkernel
- LLM talks to RYE → RYE universal executor routes to Lilux
- RYE scans .ai/tools/ → builds dynamic tool registry
- RYE routes each tool to appropriate Lilux primitive or runtime
- Lilux provides dumb execution primitives only
- All intelligence is data-defined in .ai/ (not hardcoded)
- Primitives: schemas in `.ai/tools/rye/primitives/`, code in `lilux/primitives/`
- Clear separation: Kernel = dumb primitives, RYE = intelligent executor + data bundle
- All tools organized by category (rye, python, etc.) - everything is a tool!

---

**Document Status: Final & Production-Ready**
**Last Updated:** 2026-01-30
**Author:** Kiwi MCP Team
