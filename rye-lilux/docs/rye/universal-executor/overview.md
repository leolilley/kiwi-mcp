**Source:** Original implementation: `kiwi_mcp/primitives/executor.py` in kiwi-mcp

# Universal Executor Overview

## Purpose

The universal executor is RYE's core routing mechanism. It reads tool metadata and intelligently routes execution to the appropriate Lilux primitive or runtime based on:

- `__tool_type__` - What kind of tool (primitive, runtime, python, etc.)
- `__executor_id__` - Which executor to delegate to (None, "subprocess", "http_client", "python_runtime", etc.)

## Architecture

```
┌─────────────────────────────────┐
│   Tool Invocation (LLM/User)    │
└──────────────┬──────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  RYE Universal Executor              │
│  (DATA-DRIVEN - No hardcoded IDs!)│
│                                      │
│  1. Load tool metadata               │
│  2. Check __executor_id__            │
│  3. Resolve executor from filesystem  │ ← NEW!
│  4. Route recursively to primitive    │ ← NEW!
└──────────┬───────────────────────────┘
           │
     ┌──────┴──────┬──────────────┬────────────┐
     │             │              │            │
     ▼             ▼              ▼            ▼
┌────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐
│Primitive│  │ Runtime  │  │ Subprocess │  │HTTP Client│
│(No Del) │  │Delegated │  │ Primitive  │  │Primitive │
│Schema   │  │w/ ENV    │  │(exec cmds) │  │(http req)│
└────────┘  └──────────┘  └────────────┘  └──────────┘
     ▲            ▲              ▲              ▲
     │            │              │              │
     └────────────┴──────────────┴──────────────┘
            LILUX MICROKERNEL
```

**KEY:** Universal executor discovers executors from `.ai/tools/` filesystem, not from hardcoded registries.

## Three-Layer Routing

### Layer 1: Primitives (`__executor_id__ = None`)

**Direct execution - no delegation**

```python
# .ai/tools/rye/primitives/subprocess.py
__tool_type__ = "primitive"
__executor_id__ = None  # ← No delegation
__category__ = "primitives"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "timeout": {"type": "integer", "default": 300},
    },
    "required": ["command"]
}
```

**Execution:** Universal executor calls Lilux primitive directly

```python
# In rye/executor.py (pseudocode)
if executor_id is None:
    # Primitive - execute directly
    return lilux.primitives.subprocess.execute(config)
```

### Layer 2: Runtimes (`__executor_id__ = "subprocess"`)

**Environment-configured delegation**

```python
# .ai/tools/rye/runtimes/python_runtime.py
__tool_type__ = "runtime"
__executor_id__ = "subprocess"  # ← Delegates to subprocess primitive
__category__ = "runtimes"

ENV_CONFIG = {
    "interpreter": {
        "type": "venv_python",
        "search": ["project", "user", "system"],
        "var": "RYE_PYTHON",
        "fallback": "python3",
    },
    "env": {
        "PYTHONUNBUFFERED": "1",
        "PROJECT_VENV_PYTHON": "${RYE_PYTHON}",
    },
}

CONFIG = {
    "command": "${RYE_PYTHON}",
    "args": [],
    "timeout": 300,
}
```

**Execution:**

1. Universal executor loads Python runtime metadata
2. Calls env_resolver to resolve `ENV_CONFIG`
3. Resolves template variables: `${RYE_PYTHON}` → `/path/to/.venv/bin/python3`
4. Passes resolved config to subprocess primitive

```python
# In rye/executor.py (pseudocode)
if executor_id == "subprocess":
    resolved_env = env_resolver.resolve(ENV_CONFIG, context)
    resolved_config = resolve_templates(config, resolved_env)
    return lilux.primitives.subprocess.execute(resolved_config)
```

### Layer 3: Tools (`__executor_id__ = "python_runtime"`)

**User tools delegating to runtimes**

```python
# .ai/tools/rye/capabilities/git.py
__tool_type__ = "python"
__executor_id__ = "python_runtime"  # ← Delegates to python runtime
__category__ = "capabilities"

def main(command: str, args: list = None) -> dict:
    """Execute git command."""
    return {"result": subprocess.run([command] + (args or []))}
```

**Execution:**

1. Universal executor loads git tool metadata
2. Checks `__executor_id__ = "python_runtime"`
3. Loads Python runtime metadata (layer 2)
4. Resolves environment via env_resolver
5. Passes to subprocess primitive (layer 1)

## Metadata Parsing

The universal executor parses metadata from multiple sources:

### Python Files

```python
# Any .ai/tools/{category}/{name}.py
__version__ = "1.0.0"
__tool_type__ = "python"          # Type: primitive, runtime, python, python_lib
__executor_id__ = "python_runtime" # Executor: None, "subprocess", "http_client", "python_runtime"
__category__ = "capabilities"      # Category: rye, python, utility, etc.

CONFIG_SCHEMA = {
    "type": "object",
    "properties": { ... },
}

ENV_CONFIG = { ... }  # Optional for runtimes

def main(**kwargs) -> dict:
    """Tool implementation."""
    pass
```

### YAML Files

```yaml
# .ai/tools/rye/mcp/mcp_stdio.yaml
name: mcp_stdio
version: "1.0.0"
tool_type: runtime
executor_id: subprocess
category: mcp

config:
  command: "${RYE_MCP_RUNNER}"
  args: ["--type", "stdio"]

env_config:
  mcp_runner:
    type: binary
    search: ["project", "system"]
    var: "RYE_MCP_RUNNER"
    fallback: "mcp"
```

## Auto-Discovery Process

```
RYE Startup
    │
    ├─→ discovery.py scans .ai/tools/
    │
    ├─→ Finds all Python files: *.py
    ├─→ Finds all YAML files: *.yaml
    │
    ├─→ For each file:
    │   ├─ Parse metadata (__tool_type__, __executor_id__, __category__)
    │   ├─ Extract CONFIG_SCHEMA
    │   ├─ Extract ENV_CONFIG (if runtime)
    │   └─ Register in tool registry
    │
    └─→ Build dynamic tool registry
        └─→ MCP server exposes all tools to LLM
```

## Executor Resolution Order

When executing a tool:

1. **Load tool from `.ai/tools/{category}/{name}.py`**
2. **Get `__executor_id__`**
3. **If `__executor_id__` is None:**
   - Execute as primitive directly via `lilux.primitives.{name}.execute()`
4. **Else:**
   - **DATA-DRIVEN:** Search `.ai/tools/**/` for executor_id
   - Load executor metadata from filesystem (not registry!)
   - If executor is runtime:
     - Resolve `ENV_CONFIG` via env_resolver
     - Merge resolved environment into parameters
   - **RECURSIVE:** Call execute with executor path
   - Continues until reaching a primitive (`__executor_id__` is None)

**Key Difference:** No hardcoded lists of executor IDs - all discovered from filesystem!

## Key Benefits

| Benefit                    | How Achieved                                        |
| -------------------------- | --------------------------------------------------- |
| **No hardcoded tools**     | Discovery scans `.ai/tools/` dynamically            |
| **No hardcoded executors** | Executor IDs resolved from filesystem (data-driven) |
| **Flexible routing**       | Metadata-driven delegation via `__executor_id__`    |
| **Environment management** | `ENV_CONFIG` declares environment needs             |
| **Language agnostic**      | Runtimes support any language with interpreter      |
| **Extensible**             | Add new primitives/runtimes via file addition       |
| **Configuration-driven**   | Tool behavior via `CONFIG_SCHEMA`, not code         |
| **Automatic discovery**    | New tools immediately available to LLM              |
| **Recursive resolution**   | Executor chains resolved automatically              |

## Related Documentation

- [[routing]] - Detailed routing examples
- [[bundle/structure]] - Tool organization in .ai/
- [[categories/overview]] - All tool categories
- [[categories/extractors]] - Schema-driven metadata extraction
- [[categories/parsers]] - Content preprocessors
