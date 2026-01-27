# Environment Resolution Architecture

**Date:** 2026-01-27  
**Status:** Revised Proposal  
**Purpose:** Define kernel-level, data-driven environment resolution for tool execution

---

## Executive Summary

Environment resolution is a **kernel-level concern** that must be **data-driven** and **extensible**. Rather than hardcoding runtime-specific logic (`_resolve_python()`, `_resolve_node()`), runtimes themselves define their interpreter resolution rules via a new `ENV_CONFIG` declaration.

**Core Principle:** Runtimes are data-driven. Just as extractors define extraction rules, runtimes should define environment rules. The kernel applies these rules generically.

---

## Terminology

| Term                    | Meaning                                                                                             |
| ----------------------- | --------------------------------------------------------------------------------------------------- |
| **Execution Primitive** | `subprocess`, `http_client` - the actual execution layer (unchanged)                                |
| **Kernel Service**      | `EnvResolver`, `AuthStore`, `LockfileStore` - trusted services called by executor                   |
| **Resolver Type**       | Strategy for finding an interpreter (e.g., `venv_python`, `node_modules`) - internal to EnvResolver |
| **Runtime**             | Tool that configures how scripts execute (e.g., `python_runtime`, `node_runtime`)                   |

---

## Design Philosophy

### Follow the Extractor Pattern

Extractors taught us the right approach:

- **Extractors don't hardcode** `_extract_python()`, `_extract_javascript()`
- **Extractors declare rules** via `EXTRACTION_RULES` with generic types (`ast_var`, `regex`, `filename`)
- **The kernel applies rules** using a generic engine

Environment resolution should work the same way:

- **Runtimes don't hardcode** interpreter resolution
- **Runtimes declare rules** via `ENV_CONFIG` with resolver types (`venv_python`, `node_modules`, `system_binary`)
- **The kernel applies rules** using a generic resolver

### Data-Driven Everything

| Component  | Declares           | Applied By        |
| ---------- | ------------------ | ----------------- |
| Extractors | `EXTRACTION_RULES` | SchemaExtractor   |
| Runtimes   | `ENV_CONFIG`       | EnvResolver       |
| Tools      | `CONFIG`           | PrimitiveExecutor |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Runtime Tool (python_runtime.py, node_runtime.py, etc.)        │
│                                                                 │
│   ENV_CONFIG = {                                                │
│       "interpreter": {                                          │
│           "type": "venv_python",   ← resolver type              │
│           "search": ["project", "kiwi", "user", "system"],      │
│           "var": "KIWI_PYTHON",                                 │
│           "fallback": "python3",                                │
│       },                                                        │
│       "env": { "PYTHONUNBUFFERED": "1" },                       │
│   }                                                             │
│                                                                 │
│   CONFIG = {                                                    │
│       "command": "${KIWI_PYTHON}",                              │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Executor (Orchestrator)                                         │
│   1. Resolve tool chain → get runtime's ENV_CONFIG              │
│   2. Call env_resolver.resolve(env_config) → resolved env       │
│   3. Template CONFIG using resolved env                         │
│   4. Pass to execution primitive (subprocess or http_client)    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ EnvResolver (Kernel Service)                                    │
│                                                                 │
│   Resolver types (internal strategies):                         │
│   ├─ venv_python    → search venv paths for python              │
│   ├─ node_modules   → search node_modules paths for node        │
│   ├─ system_binary  → find binary in PATH                       │
│   ├─ version_manager→ resolve via rbenv/nvm/asdf                │
│   └─ (extensible)   → add new types as needed                   │
│                                                                 │
│   Applies rules from ENV_CONFIG, returns resolved env dict      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Execution Primitives (UNCHANGED)                                │
│   ├─ subprocess   → execute shell commands                      │
│   └─ http_client  → make HTTP requests                          │
│                                                                 │
│   - Receive fully resolved env from executor                    │
│   - NO resolution logic                                         │
│   - Truly "dumb"                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Runtime ENV_CONFIG Specification

### Python Runtime Example

```python
# .ai/tools/runtimes/python_runtime.py

__version__ = "2.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"

# Environment configuration - declares HOW to resolve interpreter
ENV_CONFIG = {
    "interpreter": {
        "type": "venv_python",  # Resolver type
        "search": ["project", "kiwi", "user", "system"],
        "var": "KIWI_PYTHON",
        "fallback": "python3",
    },
    "env": {
        "PYTHONUNBUFFERED": "1",
    },
}

CONFIG = {
    "command": "${KIWI_PYTHON}",
    "args": [],
    "timeout": 300,
    "capture_output": True,
}
```

### Node Runtime Example

```python
# .ai/tools/runtimes/node_runtime.py

__version__ = "2.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"

ENV_CONFIG = {
    "interpreter": {
        "type": "node_modules",  # Resolver type
        "search": ["project", "kiwi", "user", "system"],
        "var": "KIWI_NODE",
        "fallback": "node",
    },
    "env": {
        "NODE_ENV": "production",
    },
}

CONFIG = {
    "command": "${KIWI_NODE}",
    "args": [],
    "timeout": 300,
    "capture_output": True,
}
```

### Deno Runtime Example (Future)

```python
# .ai/tools/runtimes/deno_runtime.py

ENV_CONFIG = {
    "interpreter": {
        "type": "system_binary",  # Resolver type
        "binary": "deno",
        "var": "KIWI_DENO",
        "fallback": "deno",
    },
    "env": {
        "DENO_DIR": "${HOME}/.cache/deno",
    },
}

CONFIG = {
    "command": "${KIWI_DENO}",
    "args": ["run", "--allow-all"],
}
```

### Ruby Runtime Example (Future)

```python
# .ai/tools/runtimes/ruby_runtime.py

ENV_CONFIG = {
    "interpreter": {
        "type": "version_manager",  # Resolver type
        "manager": "rbenv",  # or "rvm", "asdf"
        "var": "KIWI_RUBY",
        "fallback": "ruby",
    },
    "env": {},
}

CONFIG = {
    "command": "${KIWI_RUBY}",
    "args": [],
}
```

---

## ENV_CONFIG Schema

### Interpreter Resolution

```python
"interpreter": {
    # Required: Resolver type (how to find the interpreter)
    "type": str,  # "venv_python", "node_modules", "system_binary", "version_manager"

    # Required: Environment variable to set with resolved path
    "var": str,  # e.g., "KIWI_PYTHON"

    # Optional: Search order for resolution
    "search": List[str],  # ["project", "kiwi", "user", "system"]

    # Optional: Fallback if resolution fails
    "fallback": str,  # e.g., "python3"

    # Type-specific options
    "binary": str,       # For system_binary: name to find in PATH
    "manager": str,      # For version_manager: which version manager
    "version": str,      # For version_manager: specific version
}
```

### Search Locations

The `search` array specifies where to look, in order:

| Key         | Python Paths                   | Node Paths                           | Description         |
| ----------- | ------------------------------ | ------------------------------------ | ------------------- |
| `"project"` | `.venv/bin/python`             | `node_modules/.bin/node`             | User's project env  |
| `"kiwi"`    | `.ai/scripts/.venv/bin/python` | `.ai/scripts/node_modules/.bin/node` | Kiwi tool env       |
| `"user"`    | `~/.ai/.venv/bin/python`       | `~/.ai/node_modules/.bin/node`       | User-level kiwi env |
| `"system"`  | `which python3`                | `which node`                         | System PATH         |

### Environment Variables

```python
"env": {
    # Static values
    "KEY": "value",

    # Reference other env vars
    "PATH_EXT": "${HOME}/.local/bin",

    # Reference resolved interpreter
    "PYTHON_BIN": "${KIWI_PYTHON}",
}
```

---

## Resolver Types

These are internal strategies within `EnvResolver` - **not execution primitives**.

### `venv_python`

Resolves Python interpreter from virtual environment locations.

**Config options:**

- `search`: List of locations to check (`["project", "kiwi", "user", "system"]`)
- `var`: Environment variable to set
- `fallback`: Binary name if not found

**Resolution logic:**

```
project  → {project}/.venv/bin/python
kiwi     → {project}/.ai/scripts/.venv/bin/python
user     → ~/.ai/.venv/bin/python
system   → which python3 || which python
```

### `node_modules`

Resolves Node.js from node_modules locations.

**Config options:**

- `search`: List of locations to check
- `var`: Environment variable to set
- `fallback`: Binary name if not found

**Resolution logic:**

```
project  → {project}/node_modules/.bin/node
kiwi     → {project}/.ai/scripts/node_modules/.bin/node
user     → ~/.ai/node_modules/.bin/node
system   → which node
```

### `system_binary`

Resolves any binary from system PATH.

**Config options:**

- `binary`: Name of binary to find
- `var`: Environment variable to set
- `fallback`: Fallback if not found

**Resolution logic:**

```
which {binary} || fallback
```

### `version_manager`

Resolves interpreter via version managers (rbenv, nvm, asdf, etc.).

**Config options:**

- `manager`: Version manager name (`rbenv`, `nvm`, `asdf`)
- `version`: Specific version (optional)
- `var`: Environment variable to set
- `fallback`: Fallback if not found

**Resolution logic:**

```
rbenv  → ~/.rbenv/versions/{version}/bin/ruby || which ruby
nvm    → ~/.nvm/versions/node/{version}/bin/node || which node
asdf   → ~/.asdf/installs/{plugin}/{version}/bin/{plugin}
```

### Adding New Resolver Types

New resolver types can be added to `EnvResolver` without changing runtimes:

```python
# Future: conda environments
"interpreter": {
    "type": "conda_env",
    "env_name": "myenv",
    "var": "KIWI_PYTHON",
}
```

Just add the corresponding method in `EnvResolver`:

```python
def _resolve_conda_env(self, config: Dict[str, Any]) -> Optional[str]:
    """Resolve Python from conda environment."""
    env_name = config.get("env_name")
    # ... resolution logic
```

---

## EnvResolver Implementation

```python
"""
Kernel-level environment resolver.

Applies ENV_CONFIG rules from runtimes to produce resolved environment.
All resolution is pure (no side effects, no venv creation).
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Any

from kiwi_mcp.utils.env_loader import load_dotenv_files
from kiwi_mcp.utils.resolvers import get_user_space


class EnvResolver:
    """
    Generic environment resolver (kernel service).

    Applies ENV_CONFIG rules using resolver types.
    No hardcoded runtime-specific logic.
    """

    # Registry of resolver types → method names
    RESOLVER_TYPES = {
        "venv_python": "_resolve_venv_python",
        "node_modules": "_resolve_node_modules",
        "system_binary": "_resolve_system_binary",
        "version_manager": "_resolve_version_manager",
    }

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = Path(project_path) if project_path else None
        self.user_space = get_user_space()

    def resolve(
        self,
        env_config: Optional[Dict[str, Any]] = None,
        tool_env: Optional[Dict[str, str]] = None,
        include_dotenv: bool = True,
    ) -> Dict[str, str]:
        """
        Resolve environment using ENV_CONFIG rules.

        Args:
            env_config: ENV_CONFIG from runtime (interpreter rules, static env)
            tool_env: Additional env vars from tool CONFIG
            include_dotenv: Whether to load .env files

        Returns:
            Fully resolved environment dict
        """
        env_config = env_config or {}

        # 1. Start with system environment
        env = os.environ.copy()

        # 2. Load .env files
        if include_dotenv:
            dotenv_vars = load_dotenv_files(self.project_path)
            env.update(dotenv_vars)

        # 3. Apply interpreter resolution
        interpreter_config = env_config.get("interpreter")
        if interpreter_config:
            resolved_path = self._resolve_interpreter(interpreter_config)
            var_name = interpreter_config.get("var", "INTERPRETER")
            if resolved_path:
                env[var_name] = resolved_path
            elif interpreter_config.get("fallback"):
                env[var_name] = interpreter_config["fallback"]

        # 4. Apply static env from ENV_CONFIG
        static_env = env_config.get("env", {})
        for key, value in static_env.items():
            env[key] = self._expand_value(value, env)

        # 5. Apply tool-level env overrides
        if tool_env:
            for key, value in tool_env.items():
                env[key] = self._expand_value(str(value), env)

        return env

    def _resolve_interpreter(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Resolve interpreter using the appropriate resolver type.

        Dispatches to resolver method based on config["type"].
        """
        resolver_type = config.get("type")
        if not resolver_type:
            return None

        method_name = self.RESOLVER_TYPES.get(resolver_type)
        if not method_name:
            # Unknown resolver type - return fallback
            return config.get("fallback")

        method = getattr(self, method_name)
        return method(config)

    def _resolve_venv_python(self, config: Dict[str, Any]) -> Optional[str]:
        """Resolve Python from venv locations."""
        search = config.get("search", ["kiwi", "user", "system"])
        locations = self._build_python_locations()

        for key in search:
            path = locations.get(key)
            if path is None:
                continue
            if isinstance(path, str):
                return path  # system binary path
            if path.exists():
                return str(path)

        return config.get("fallback")

    def _resolve_node_modules(self, config: Dict[str, Any]) -> Optional[str]:
        """Resolve Node from node_modules locations."""
        search = config.get("search", ["kiwi", "user", "system"])
        locations = self._build_node_locations()

        for key in search:
            path = locations.get(key)
            if path is None:
                continue
            if isinstance(path, str):
                return path
            if path.exists():
                return str(path)

        return config.get("fallback")

    def _resolve_system_binary(self, config: Dict[str, Any]) -> Optional[str]:
        """Resolve binary from system PATH."""
        binary = config.get("binary")
        if not binary:
            return config.get("fallback")

        path = shutil.which(binary)
        return path or config.get("fallback")

    def _resolve_version_manager(self, config: Dict[str, Any]) -> Optional[str]:
        """Resolve via version manager (rbenv, nvm, asdf, etc.)."""
        manager = config.get("manager")
        version = config.get("version")
        fallback = config.get("fallback")

        if manager == "rbenv":
            return self._resolve_rbenv(version) or fallback
        elif manager == "nvm":
            return self._resolve_nvm(version) or fallback
        elif manager == "asdf":
            return self._resolve_asdf(config.get("plugin"), version) or fallback

        return fallback

    def _build_python_locations(self) -> Dict[str, Any]:
        """Build Python search locations."""
        bin_dir = "Scripts" if os.name == "nt" else "bin"
        python_exe = "python.exe" if os.name == "nt" else "python"

        locations = {
            "system": shutil.which("python3") or shutil.which("python"),
            "user": self.user_space / ".venv" / bin_dir / python_exe,
        }

        if self.project_path:
            locations["project"] = self.project_path / ".venv" / bin_dir / python_exe
            locations["kiwi"] = self.project_path / ".ai" / "scripts" / ".venv" / bin_dir / python_exe

        return locations

    def _build_node_locations(self) -> Dict[str, Any]:
        """Build Node search locations."""
        node_exe = "node.exe" if os.name == "nt" else "node"

        locations = {
            "system": shutil.which("node"),
            "user": self.user_space / "node_modules" / ".bin" / node_exe,
        }

        if self.project_path:
            locations["project"] = self.project_path / "node_modules" / ".bin" / node_exe
            locations["kiwi"] = self.project_path / ".ai" / "scripts" / "node_modules" / ".bin" / node_exe

        return locations

    def _resolve_rbenv(self, version: Optional[str]) -> Optional[str]:
        """Resolve Ruby via rbenv."""
        rbenv_root = Path(os.environ.get("RBENV_ROOT", Path.home() / ".rbenv"))
        if version:
            path = rbenv_root / "versions" / version / "bin" / "ruby"
            if path.exists():
                return str(path)
        return shutil.which("ruby")

    def _resolve_nvm(self, version: Optional[str]) -> Optional[str]:
        """Resolve Node via nvm."""
        nvm_dir = Path(os.environ.get("NVM_DIR", Path.home() / ".nvm"))
        if version:
            path = nvm_dir / "versions" / "node" / version / "bin" / "node"
            if path.exists():
                return str(path)
        return shutil.which("node")

    def _resolve_asdf(self, plugin: Optional[str], version: Optional[str]) -> Optional[str]:
        """Resolve via asdf version manager."""
        if not plugin:
            return None
        asdf_dir = Path(os.environ.get("ASDF_DATA_DIR", Path.home() / ".asdf"))
        if version:
            path = asdf_dir / "installs" / plugin / version / "bin" / plugin
            if path.exists():
                return str(path)
        return shutil.which(plugin)

    def _expand_value(self, value: str, env: Dict[str, str]) -> str:
        """Expand ${VAR} and ${VAR:-default} in value."""
        import re

        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            return env.get(var_name, default)

        return re.sub(pattern, replacer, value)
```

---

## Executor Integration

```python
class PrimitiveExecutor:
    def __init__(self, project_path: Optional[Path] = None):
        self.env_resolver = EnvResolver(project_path)

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ExecutionResult:
        # 1. Resolve tool chain
        chain = await self.resolver.resolve(tool_name)

        # 2. Extract ENV_CONFIG from runtime in chain
        env_config = self._get_env_config_from_chain(chain)

        # 3. Get tool-level env overrides
        merged_config = self._merge_chain_configs(chain)
        tool_env = merged_config.get("env", {})

        # 4. Resolve environment (kernel service)
        env = self.env_resolver.resolve(
            env_config=env_config,
            tool_env=tool_env,
        )

        # 5. Template config using resolved env
        templated_config = self._template_config(merged_config, env)
        templated_config["env"] = env

        # 6. Execute via primitive (subprocess or http_client)
        return await self._execute_primitive(templated_config, params)

    def _get_env_config_from_chain(self, chain: List[ToolMetadata]) -> Optional[Dict]:
        """Extract ENV_CONFIG from runtime tool in chain."""
        for tool in chain:
            if tool.tool_type == "runtime":
                return tool.metadata.get("env_config")
        return None
```

---

## Metadata Extraction

The existing extraction system needs to extract `ENV_CONFIG` from runtimes.

Add to `python_extractor.py` EXTRACTION_RULES:

```python
EXTRACTION_RULES = {
    # ... existing rules ...

    "env_config": {
        "type": "ast_var",
        "name": "ENV_CONFIG",
    },
}
```

---

## Benefits

### ✅ No Hardcoded Runtime Logic

- No `_resolve_python()`, `_resolve_node()` methods in kernel
- New runtimes just add `ENV_CONFIG` declaration
- Kernel applies rules generically via resolver types

### ✅ Follows Extractor Pattern

- Same mental model: declare rules, kernel applies
- Consistent architecture across the codebase
- Familiar pattern for contributors

### ✅ Extensible Resolver Types

- Add new resolver types to EnvResolver as needed
- Runtimes can use new types immediately
- Minimal kernel changes for new patterns

### ✅ Self-Documenting

- Runtime's `ENV_CONFIG` shows exactly how it resolves
- No hidden logic scattered across kernel
- Easy to debug and understand

### ✅ Execution Primitives Unchanged

- `subprocess` and `http_client` remain the only execution primitives
- They receive fully resolved env from executor
- Stay truly "dumb"

---

## Migration Path

### Phase 1: Add ENV_CONFIG Support

- [ ] Add `env_config` to extraction rules
- [ ] Create `EnvResolver` kernel service
- [ ] Unit tests for each resolver type

### Phase 2: Update Runtimes

- [ ] Add `ENV_CONFIG` to `python_runtime.py`
- [ ] Add `ENV_CONFIG` to `node_runtime.py`
- [ ] Update `CONFIG.command` to use `${KIWI_PYTHON}` etc.

### Phase 3: Integrate with Executor

- [ ] Update executor to extract ENV_CONFIG from chain
- [ ] Call `env_resolver.resolve()` before templating
- [ ] Remove hardcoded env logic from executor

### Phase 4: Cleanup

- [ ] Remove `PROJECT_VENV_PYTHON` references (or alias)
- [ ] Update documentation
- [ ] Add more runtime examples

---

## Backward Compatibility

### Variable Aliasing

During transition, alias old variable names:

```python
# In python_runtime.py ENV_CONFIG
ENV_CONFIG = {
    "interpreter": {
        "type": "venv_python",
        "var": "KIWI_PYTHON",
        # ...
    },
    "env": {
        # Backward compat alias
        "PROJECT_VENV_PYTHON": "${KIWI_PYTHON}",
    },
}
```

### Runtime Version Bump

Update `__version__` in runtimes when adding `ENV_CONFIG`:

- `python_runtime.py`: 1.0.4 → 2.0.0
- `node_runtime.py`: 1.0.0 → 2.0.0

---

## Future Resolver Types

New resolver types can be added to `EnvResolver` for new resolution patterns:

```python
# Conda environments
"interpreter": {
    "type": "conda_env",
    "env_name": "myenv",
    "var": "KIWI_PYTHON",
}

# Pipx installed tools
"interpreter": {
    "type": "pipx",
    "package": "black",
    "var": "KIWI_BLACK",
}

# Homebrew installed binaries
"interpreter": {
    "type": "homebrew",
    "formula": "python@3.11",
    "var": "KIWI_PYTHON",
}
```

---

## Comparison with Previous Approach

| Aspect                      | Hardcoded Methods         | Data-Driven (This)                  |
| --------------------------- | ------------------------- | ----------------------------------- |
| Adding new runtime          | Add `_resolve_X()` method | Add `ENV_CONFIG` to runtime         |
| Kernel changes needed       | Yes, for each runtime     | No, unless new resolver type needed |
| Runtime controls resolution | No                        | Yes                                 |
| Testability                 | Test kernel methods       | Test resolver types + configs       |
| Discoverability             | Read kernel code          | Read runtime's ENV_CONFIG           |

---

## References

- [python_extractor.py](file:///home/leo/projects/kiwi-mcp/.ai/tools/extractors/python_extractor.py) - Extractor pattern reference
- [AUTH_STORE_IMPLEMENTATION.md](./AUTH_STORE_IMPLEMENTATION.md) - Kernel service pattern
- [LOCKFILE_IMPLEMENTATION_PLAN.md](./LOCKFILE_IMPLEMENTATION_PLAN.md) - Kernel service pattern

---

_Revised: 2026-01-27_
