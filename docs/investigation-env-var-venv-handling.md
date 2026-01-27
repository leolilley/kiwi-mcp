# Environment Variable Resolution and Virtual Environment Handling

**Status:** Investigation  
**Focus:** Architecture alignment, separation of concerns, data-driven configuration  
**Project:** Kiwi MCP

## Overview

This investigation addresses a mismatch between where environment variables are set and where they're resolved in Kiwi MCP's executor and primitive layers. The goal is to maintain Kiwi's data-driven architecture ("kernel stays dumb") while properly handling Python virtual environment detection and path resolution.

## Architecture Context

Kiwi MCP uses a data-driven architecture with clear separation:

```
Tools (self-contained configs)
    ↓
Executors (tool-specific runners like python_runtime)
    ↓
Primitives (generic operations like subprocess)
    ↓
OS/System layer
```

**Core principle:** The kernel contains no tool-specific logic—everything is configured via data. Tools declare what they need; the system provides infrastructure to fulfill those needs.

## Current Problem

There's a separation of concerns mismatch between **environment variable setup** (in executor) and **environment variable resolution** (in subprocess primitive). This mismatch becomes more apparent when considering **multiple runtimes** (Python, Node.js, etc.), each with different dependency management and environment requirements.

### Code Locations

**Executor (`executor.py`, lines ~719-729):**

```python
# Ensure Python output is unbuffered for reliable stdout capture
env = exec_config.get("env", {}).copy()
if "PYTHONUNBUFFERED" not in env:
    env["PYTHONUNBUFFERED"] = "1"

# Set PROJECT_VENV_PYTHON if project_path has a .venv
if self.project_path:
    venv_python = self.project_path / ".venv" / "bin" / "python"
    if venv_python.exists():
        env["PROJECT_VENV_PYTHON"] = str(venv_python)

exec_config["env"] = env
```

**Subprocess primitive (`subprocess.py`, lines ~52-54):**

```python
# Prepare environment first (merge os.environ with config env_vars)
env = os.environ.copy()
for key, value in env_vars.items():
    env[key] = str(value)

# Resolve environment variables in command and args using merged env
command = self._resolve_env_var(command, env)
args = [self._resolve_env_var(arg, env) for arg in args]
```

**Runtime tool config (`python_runtime.py`):**

```python
CONFIG = {
    "command": "${PROJECT_VENV_PYTHON:-python3}",
    ...
}
```

### Problems with Current Approach

| Issue                                          | Impact                                       | Principle Violated        |
| ---------------------------------------------- | -------------------------------------------- | ------------------------- |
| Hardcoded venv logic in executor               | Difficult to extend for other venv scenarios | Kernel should be "dumb"   |
| Executor checks `.venv` existence              | Tool-specific knowledge leaks into kernel    | Data-driven configuration |
| Tight coupling between executor and subprocess | Changes to one affect the other              | Separation of concerns    |
| Logic not reusable                             | Other tools duplicating venv detection       | DRY principle             |
| Mixed concerns                                 | Setup in executor, resolution in subprocess  | Single responsibility     |

## Existing Infrastructure

### EnvManager (Python-Specific)

**`EnvManager` class** (`kiwi_mcp/utils/env_manager.py`):

- ✅ Manages project-level and user-level Python virtual environments
- ✅ `build_subprocess_env()` — sets up `PATH`, `VIRTUAL_ENV`, `PYTHONPATH`
- ✅ `.env` file loading
- ✅ `get_python()` — retrieves venv Python path
- ✅ `install_packages()` — pip install support
- ✅ `check_packages()` — dependency validation
- ❌ Currently **not used** by executor or subprocess primitive
- ⚠️ **Python-specific** — doesn't handle Node.js, Ruby, Go, etc.

### Runtime Tools (Configuration-Based)

**Python Runtime** (`.ai/tools/runtimes/python_runtime.py`):

```python
CONFIG = {
    "command": "${PROJECT_VENV_PYTHON:-python3}",
    "env": {"PYTHONUNBUFFERED": "1"}
}
```

- Uses `${PROJECT_VENV_PYTHON:-python3}` syntax
- Executor injects `PROJECT_VENV_PYTHON` if `.venv` exists
- Works but hardcoded logic in executor

**Node.js Runtime** (`.ai/tools/runtimes/node_runtime.py`):

```python
CONFIG = {
    "command": "node",
    "env": {"NODE_ENV": "production"}
}
```

- Simple `node` command
- Sets `NODE_ENV=production`
- **No venv/dependency management yet**
- **No npm/yarn support**

### Pattern Analysis: What Each Runtime Needs

| Runtime | Venv Location                             | Manager    | Activation         | Deps       |
| ------- | ----------------------------------------- | ---------- | ------------------ | ---------- |
| Python  | `.venv/bin/python`                        | EnvManager | PATH + VIRTUAL_ENV | pip        |
| Node.js | `node_modules/.bin/node` (npm) or `.yarn` | ❌ None    | PATH + NODE_PATH   | npm/yarn   |
| Ruby    | `.venv/bin/ruby` or system                | ❌ None    | PATH + GEM_PATH    | bundler    |
| Go      | `$GOPATH/bin` or `/usr/bin/go`            | ❌ None    | PATH + GOPATH      | go modules |

**Critical insight:** The executor currently hardcodes Python-specific venv detection. When Node.js (or other runtimes) need similar dependency management, they'll also need environment setup—but each runtime has different requirements.

This suggests the solution should be **runtime-agnostic** and **declarative**: runtimes declare their env needs, and the executor orchestrates them.

## The Multi-Runtime Problem

The current Python-specific approach in the executor creates a **scalability problem** as Kiwi adds more runtime support.

### Current State

```
Executor._build_subprocess_config()
    ├─ Hardcoded: if self.project_path -> check .venv
    ├─ Hardcoded: env["PYTHONUNBUFFERED"] = "1"
    ├─ Hardcoded: env["PROJECT_VENV_PYTHON"] = path
    └─ Works for: python_runtime.py

python_runtime.py
    └─ CONFIG["command"] = "${PROJECT_VENV_PYTHON:-python3}"

node_runtime.py
    └─ CONFIG["command"] = "node"
       (NO venv/dependency management)
```

### Problem: What Happens with Node.js?

When we want Node.js tools to support npm dependencies, the executor would need:

- ❌ Hardcoded check for `package.json`
- ❌ Logic to detect npm vs yarn
- ❌ Logic to build NODE_PATH
- ❌ Logic to inject `npm install` hooks

This approach doesn't scale:

- **Executor becomes a tool-specific kitchen sink** (Python, Node, Ruby, Go…)
- **Each runtime duplicates its own EnvManager** (EnvManager_Node, EnvManager_Ruby…)
- **No way for tools to declare env dependencies** (only hardcoded patterns)
- **Kernel violates "stays dumb" principle**

### Solution Direction: Declarative Runtime Configuration

Instead of hardcoding, runtimes should **declare** what environment setup they need:

```python
# python_runtime.py
CONFIG = {
    "command": "${PYTHON_RUNTIME:-python3}",
    "env": {"PYTHONUNBUFFERED": "1"},
    "env_setup": {  # ← NEW: declarative setup
        "type": "python_venv",
        "paths": ["lib", "lib.python"]
    }
}

# node_runtime.py
CONFIG = {
    "command": "node",
    "env": {"NODE_ENV": "production"},
    "env_setup": {  # ← NEW: declarative setup
        "type": "npm_dependencies",
        "package_json": "package.json"
    }
}
```

The executor then becomes **generic**:

```python
# Executor only knows HOW to orchestrate, not WHAT each runtime needs
if runtime_config.get("env_setup"):
    env = orchestrate_env_setup(runtime_config["env_setup"], self.project_path)
    env.update(exec_config.get("env", {}))
```

Each runtime's **EnvManager** handles its specific logic:

- `EnvManager` (Python) ← already exists
- `EnvManagerNode` (Node.js) ← new, mirrors EnvManager
- `EnvManagerRuby` (Ruby) ← future
- `EnvManagerGo` (Go) ← future

## Investigation Questions

### 1. Separation of Concerns

**Where should venv detection and Python path resolution live?**

- Option A: In runtime tool config (e.g., `python_runtime.py`)
- Option B: In executor (as a general mechanism)
- Option C: In subprocess primitive (as part of env resolution)
- Option D: Via `EnvManager` integration
- Option E: Hybrid approach (config + EnvManager)

**Evaluation:**

- A (Config only): Doesn't work—can't know venv path at config time
- B (Executor): Current approach; violates "kernel stays dumb"
- C (Subprocess): Too late; subprocess doesn't know about project context
- D (EnvManager): Cleanest; encapsulates venv logic, designed for this
- E (Hybrid): EnvManager + executor coordination (recommended)

### 2. Data-Driven Approach

**How can we make this configurable without hardcoding?**

Current approach: Executor checks `.venv`, tool uses `${PROJECT_VENV_PYTHON:-python3}`

**Options:**

- Option A: Runtime tools declare venv requirements in config

  ```yaml
  requires:
    - venv # Signals executor to detect and inject venv paths
  ```

- Option B: Standard env var pattern that executors resolve

  ```yaml
  command: "${PROJECT_VENV_PYTHON:-python3}"
  ```

- Option C: EnvManager integration point in executor

  ```python
  env_manager = EnvManager(project_path)
  env.update(env_manager.build_subprocess_env())
  ```

- Option D: Runtime tool specifies Python directly
  ```yaml
  python_path: "${project_root}/.venv/bin/python"
  ```

**Evaluation:**

- A: Flexible but adds metadata overhead
- B: Current approach; not ideal but works
- C: **Recommended**—leverages existing infrastructure
- D: Too specific, breaks abstraction

### 3. Environment Variable Resolution

**What's the right order of operations?**

Current flow:

1. Executor creates env dict with `PYTHONUNBUFFERED`, `PROJECT_VENV_PYTHON`
2. Executor passes to subprocess
3. Subprocess merges with `os.environ`
4. Subprocess resolves `${VAR:-default}` syntax

**Issues:**

- Executor-injected vars merged in subprocess, not in config
- No guarantee executor vars are available during resolution

**Proposed flow:**

1. Executor calls `EnvManager.build_subprocess_env()` → returns full env dict
2. Executor merges config env vars into this dict
3. Executor passes complete env to subprocess
4. Subprocess resolves `${VAR:-default}` using this env
5. Subprocess also merges `os.environ` as fallback

### 4. Architecture Alignment

**How does this fit with the data-driven philosophy?**

**Current concern:** Executor has hardcoded venv detection logic.

**Proposed alignment:**

- Executor becomes a **configurator**, not a tool-specific runner
- It orchestrates infrastructure (EnvManager, env setup) based on config
- Tools declare needs in config; executor fulfills them
- Primitives remain tool-agnostic (just run subprocess with env)

**Example:**

```python
# executor.py becomes more generic
class Executor:
    def __init__(self, config, project_path):
        self.config = config
        self.project_path = project_path

    def prepare_env(self):
        """Prepare environment using EnvManager if project context exists."""
        env = os.environ.copy()

        # Use EnvManager for project venv setup
        if self.project_path:
            env_manager = EnvManager(self.project_path)
            env.update(env_manager.build_subprocess_env())

        # Merge config env vars
        env.update(self.config.get("env", {}))

        return env
```

### 5. Multi-Runtime Architecture

**How should we structure environment setup for multiple runtimes?**

**Critical question:** Do we solve just Python's venv problem, or design a system that scales to Node, Ruby, Go?

**Options:**

- Option A: **Hardcode each runtime in executor** (current approach for Python)
  - Pro: Simple, works now
  - Con: Doesn't scale; executor becomes kitchen sink
  - Con: Each new runtime adds executor logic
- Option B: **Declarative env_setup in runtime config** (recommended)
  - Pro: Scales to any runtime
  - Pro: Keeps executor generic ("dumb")
  - Pro: Each runtime owns its logic via EnvManager
  - Con: Requires runtime-specific EnvManager implementations
  - Con: Adds abstraction layer
- Option C: **Hook-based system**

  - Runtimes register hooks (e.g., `setup_env()`, `install_deps()`)
  - Executor calls hooks during execution
  - Pro: Flexible, extensible
  - Con: Runtime-specific code still lives in executor layer
  - Con: Harder to test in isolation

- Option D: **Separate "environment runtime" type**
  - Create an "env_setup" tool type
  - Runtimes declare dependencies on env_setup tools
  - E.g., `python_runtime` → depends on `python_env_setup` → depends on `venv`
  - Pro: Composable, fully data-driven
  - Con: Complex orchestration
  - Con: Performance overhead

**Evaluation:**

- A: **Not viable** for multi-runtime scaling
- B: **Recommended**—good balance of simplicity and extensibility
- C: Possible but less clean than B
- D: Over-engineered for current use case

### 5. Alternative Approaches

**Alternative A: Middleware Pattern**
Create an env injection middleware that runs between executor and subprocess:

```
Executor → EnvInjectorMiddleware → Subprocess
```

**Alternative B: Dedicated Venv Resolver**
Create a "python_venv_runtime" executor that handles Python-specific setup:

```
Tool → python_venv_runtime executor → subprocess primitive
```

**Alternative C: Config-only Approach**
Move all venv detection to tool config time (requires project discovery at tool definition):

```yaml
config:
  env:
    PYTHON_BIN: "${project.venv_python:-python3}"
```

**Evaluation:**

- Alternative A: Adds complexity, good for testability
- Alternative B: Tool-specific; breaks architecture
- Alternative C: **Not feasible**—venv path unknown at config time

## Constraints

- ✓ Must work for project-level tools (with `.venv`)
- ✓ Must work for user-level tools (with `~/.ai/.venv`)
- ✓ Must not break existing tools using `python3` directly
- ✓ Must maintain data-driven architecture
- ✓ Must support `${VAR:-default}` syntax
- ✓ Should integrate cleanly with `EnvManager`

## Recommended Approach

**Principle:** Design for multiple runtimes from day one. Python should be a reference implementation, not the special case.

### Overall Architecture

```
Executor
├─ Detects runtime_config.env_setup
├─ Calls appropriate EnvManager (Python/Node/Ruby/Go)
├─ EnvManager handles:
│   ├─ Venv detection and creation
│   ├─ build_subprocess_env() with PATH/PYTHONPATH setup
│   └─ Dependency management (pip/npm/bundler/go mod)
├─ Merges config env vars
└─ Passes complete env to subprocess

Subprocess
├─ Receives fully prepared env
├─ Resolves ${VAR:-default} syntax
└─ Executes with no env knowledge
```

### Phase 1: Generalize Python Support (Immediate)

**Goal:** Move Python-specific logic from executor to EnvManager, making it available to executor via declarative config.

**Changes:**

1. **Update executor to use EnvManager:**

   ```python
   # executor.py: _prepare_environment()
   from kiwi_mcp.utils.env_manager import EnvManager

   env = {}
   if self.project_path:
       env_manager = EnvManager(self.project_path)
       env.update(env_manager.build_subprocess_env())

   env.update(exec_config.get("env", {}))
   ```

2. **Update python_runtime.py to declare env needs:**

   ```python
   CONFIG = {
       "command": "${PYTHON_RUNTIME:-python3}",
       "env": {"PYTHONUNBUFFERED": "1"},
       "env_setup": {
           "type": "python_venv",
           "create": True,  # Auto-create venv
           "paths": ["lib", "lib.python"]
       }
   }
   ```

3. **Remove hardcoded venv logic from executor**
   - Delete lines 724-728 from executor.py
   - Logic now lives in EnvManager

**Benefits now:**

- Executor is cleaner
- Python support is reusable
- Ready for next phase

### Phase 2: Node.js Support (Foundational for Scaling)

**Goal:** Add npm/yarn support using same pattern, proving the architecture scales.

**Changes:**

1. **Create `EnvManagerNode`** (`kiwi_mcp/utils/env_manager_node.py`):

   ```python
   class EnvManagerNode:
       def __init__(self, project_path):
           self.project_path = project_path

       def build_subprocess_env(self, search_paths=None, extra_vars=None):
           # Detect npm vs yarn
           # Run npm install if package.json exists
           # Setup NODE_PATH
           # Return prepared env
   ```

2. **Update node_runtime.py to declare env needs:**

   ```python
   CONFIG = {
       "command": "node",
       "env": {"NODE_ENV": "production"},
       "env_setup": {
           "type": "npm_dependencies",
           "package_json": "package.json",
           "create": True  # Auto-run npm install
       }
   }
   ```

3. **Update executor to delegate to appropriate EnvManager:**
   ```python
   # executor.py: _setup_runtime_env()
   env_setup = exec_config.get("env_setup", {})
   if env_setup.get("type") == "python_venv":
       env = EnvManager(self.project_path).build_subprocess_env(...)
   elif env_setup.get("type") == "npm_dependencies":
       env = EnvManagerNode(self.project_path).build_subprocess_env(...)
   ```

**Benefits:**

- Proves architecture works for multiple runtimes
- Executor stays generic
- Each runtime owns its logic
- No hardcoding

### Phase 3+: Future Runtimes

With foundation set, adding Ruby, Go, etc. is straightforward:

- Create `EnvManagerRuby`, `EnvManagerGo`
- Add to runtime configs
- Executor needs no changes

### Architecture Changes

**1. Leverage `EnvManager` in executor**

Move venv detection from hardcoded logic to `EnvManager` integration:

```python
# executor.py
from kiwi_mcp.utils.env_manager import EnvManager

def _prepare_environment(self, exec_config: dict) -> dict:
    """Prepare environment with venv support using EnvManager."""
    env = {}

    # 1. Start with EnvManager setup if project context exists
    if self.project_path:
        env_manager = EnvManager(self.project_path)
        env.update(env_manager.build_subprocess_env())

    # 2. Merge config environment variables
    env.update(exec_config.get("env", {}))

    # 3. Ensure Python is unbuffered for reliable stdout
    if "PYTHONUNBUFFERED" not in env:
        env["PYTHONUNBUFFERED"] = "1"

    return env
```

**2. Update subprocess primitive to use prepared env**

```python
# subprocess.py
def run(self, command: str, args: list, env: dict = None, **kwargs):
    """Execute subprocess with proper environment handling."""
    # Use provided env (already prepared by executor)
    # or fall back to merging os.environ
    if env:
        run_env = env
    else:
        run_env = os.environ.copy()

    # Resolve variables in command and args
    command = self._resolve_env_var(command, run_env)
    args = [self._resolve_env_var(arg, run_env) for arg in args]

    # Execute subprocess
    return subprocess.run(
        [command] + args,
        env=run_env,
        ...
    )
```

**3. Keep runtime tool config unchanged**

`python_runtime.py` continues to use:

```python
CONFIG = {
    "command": "${PROJECT_VENV_PYTHON:-python3}",
    ...
}
```

This works because:

- `PROJECT_VENV_PYTHON` is set by EnvManager if venv exists
- Falls back to `python3` if not set

### Data Flow

```
Tool config (python_runtime)
    ↓
Executor receives config
    ↓
Executor calls EnvManager.build_subprocess_env()
    ↓
Executor merges config env vars
    ↓
Executor calls subprocess with prepared env
    ↓
Subprocess resolves ${VAR:-default} using env
    ↓
Subprocess executes with full environment
```

### Benefits

| Benefit                | Why                                                       |
| ---------------------- | --------------------------------------------------------- |
| Kernel stays dumb      | EnvManager handles venv logic, executor just orchestrates |
| Data-driven            | No hardcoded paths; all via config                        |
| Separation of concerns | Executor = setup; subprocess = execution                  |
| Reusable               | EnvManager available to all tools                         |
| Maintainable           | One place for venv logic (EnvManager)                     |
| Extensible             | Tools can declare env needs in config                     |
| Backward compatible    | Existing tools continue to work                           |

## Implementation Steps

### Phase 1: Refactor Executor

1. Remove hardcoded `.venv` check from executor
2. Integrate `EnvManager` into `_prepare_environment()`
3. Maintain `PYTHONUNBUFFERED` injection
4. Update executor tests

### Phase 2: Update Subprocess

1. Accept prepared env dict from executor
2. Keep variable resolution logic
3. Fall back to `os.environ` if no env provided
4. Update subprocess tests

### Phase 3: Verify Runtime Tools

1. Confirm `python_runtime` still works with new flow
2. Test both project and user-level venv scenarios
3. Test fallback to `python3` when no venv exists

### Phase 4: Documentation

1. Update architecture docs explaining env handling
2. Add EnvManager integration guide for new runtimes
3. Document the `${VAR:-default}` syntax

## Testing Strategy

**Test cases:**

- ✓ Project with `.venv/bin/python` → uses it
- ✓ Project without `.venv` → falls back to `python3`
- ✓ User-level `~/.ai/.venv` → uses it
- ✓ Config env vars override EnvManager vars
- ✓ `${VAR:-default}` resolves correctly
- ✓ Existing tools continue to work
- ✓ `PYTHONUNBUFFERED` always set
- ✓ `os.environ` available as fallback

## Open Questions for Discussion

### Immediate (Python-focused)

1. **EnvManager scope:** Should `EnvManager` be the authoritative source for all env setup, or just venv?
2. **Backward compatibility:** Are there tools depending on current executor behavior that we need to support?
3. **User-level venv:** Should executor auto-detect `~/.ai/.venv`, or only project-level `.venv`?
4. **Env var namespacing:** Should we use `KIWI_*` prefix for injected vars to avoid conflicts?
5. **EnvManager initialization:** Cost of creating EnvManager on every execution—cache or lazy init?

### Multi-Runtime Architecture

6. **EnvManager pattern:** Should all runtimes follow Python's EnvManager pattern (class + method-based)?

   - Alternative: Plugin-based system where runtimes register env setup functions?
   - Trade-off: Structure vs flexibility

7. **Dependency auto-install:** Should env setup auto-install dependencies (e.g., `npm install`)?

   - Python's `EnvManager.get_python()` auto-creates venv
   - Should `EnvManagerNode` auto-run `npm install` on `build_subprocess_env()`?
   - Trade-off: Convenience vs explicit control

8. **Node.js detection:** How to detect npm vs yarn vs pnpm?

   - Check `package-lock.json` vs `yarn.lock` vs `pnpm-lock.yaml`?
   - User preference config?
   - Check what's installed on PATH first?

9. **Executor env_setup registry:** How should executor know which EnvManager to use?

   - Hardcoded dispatch (not scalable)
   - Dynamic import by type string?
   - Plugin registration system?

10. **Testing:** How to test multi-runtime env setup without requiring all runtimes installed?
    - Mock EnvManager implementations?
    - Test fixtures?
    - Integration tests only?

## Summary

### Problem Statement

Kiwi MCP has hardcoded Python venv detection in the executor layer, violating the "kernel stays dumb" principle. This becomes a critical scalability issue when adding Node.js and other runtimes, which have their own dependency management and environment setup needs.

### Key Findings

1. **EnvManager exists but is unused** — Excellent infrastructure for Python exists but isn't integrated
2. **Multi-runtime architecture missing** — No pattern for Node, Ruby, Go beyond hardcoded special cases
3. **Separation of concerns broken** — Executor sets up env vars, subprocess resolves them—should be unified
4. **Scalability risk** — Adding Node, Ruby, Go requires executor changes, violates data-driven philosophy

### Recommended Solution (Two Phases)

**Phase 1: Generalize Python (Immediate)**

- Move venv detection from executor to EnvManager
- Update executor to call `EnvManager.build_subprocess_env()`
- Update `python_runtime.py` to declare `env_setup` needs
- Remove hardcoded venv logic from executor

**Phase 2: Add Node.js (Proves Architecture)**

- Create `EnvManagerNode` mirroring `EnvManager`
- Update `node_runtime.py` to declare `env_setup` needs
- Update executor to delegate to appropriate EnvManager based on runtime type
- Demonstrates pattern works for multiple runtimes

**Result:** Executor stays "dumb", each runtime owns its environment setup logic, architecture scales to Ruby, Go, etc.

### Data-Driven Pattern

```python
# Runtime config declares what it needs
CONFIG = {
    "command": "node",
    "env": {"NODE_ENV": "production"},
    "env_setup": {
        "type": "npm_dependencies",
        "package_json": "package.json",
        "create": True
    }
}

# Executor orchestrates, doesn't hardcode
if env_setup := exec_config.get("env_setup"):
    EnvManager = load_env_manager(env_setup["type"])
    env = EnvManager(project_path).build_subprocess_env()
```

### Risk Mitigation

- Backward compatible with existing tools
- Python support fully tested before Node rollout
- Each runtime's EnvManager independently testable
- `${VAR:-default}` syntax still supported

## References

- `kiwi_mcp/executor.py` — Current executor logic (lines 719-729)
- `kiwi_mcp/primitives/subprocess.py` — Subprocess primitive (lines 52-59)
- `kiwi_mcp/utils/env_manager.py` — Python EnvManager (excellent reference implementation)
- `.ai/tools/runtimes/python_runtime.py` — Python runtime config
- `.ai/tools/runtimes/node_runtime.py` — Node.js runtime config (needs env_setup added)

---

**Document Version:** 1.1  
**Last Updated:** 2026-01-26  
**Status:** Ready for Architecture Review and Implementation Planning  
**Key Insight:** Design the solution for multiple runtimes from the start. This is not just a Python venv problem—it's a runtime environment abstraction problem that scales to any language.
