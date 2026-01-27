# Environment Loading Issue Analysis

**Date:** 2026-01-27  
**Status:** RESOLVED  
**Issue:** CONTEXT7_API_KEY not available to tools executed via MCP

## Resolution

The issue was a **code bug** in `_build_subprocess_config` - the resolved environment from EnvResolver was not being injected into the subprocess config. The fix was to add:

```python
# In _build_subprocess_config
if resolved_env:
    env = exec_config.get("env", {})
    merged_env = dict(resolved_env)
    merged_env.update(env)
    exec_config["env"] = merged_env
```

After restarting the MCP server to pick up the code changes, the context7 tool works correctly.

---

## Original Investigation (for reference)

---

## Problem Statement

When executing tools via the kiwi-mcp MCP server (e.g., `mcp__kiwi_mcp__execute`), environment variables from `.env` files are not loaded, causing tools like `context7` to fail with:

```
"CONTEXT7_API_KEY not set in environment"
```

However, the same tool works correctly when run directly via Python with the venv activated.

---

## Root Cause Analysis

### The Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Amp (or other MCP client)                                       │
│   Calls: mcp__kiwi_mcp__execute(tool="context7", ...)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ kiwi-mcp MCP Server Process                                     │
│   Running with: ??? Python (this is the problem)                │
│                                                                 │
│   1. Receives tool execution request                            │
│   2. Calls PrimitiveExecutor.execute()                          │
│   3. PrimitiveExecutor calls EnvResolver.resolve()              │
│   4. EnvResolver tries to load .env files                       │
│      └─ Requires python-dotenv to be installed                  │
│   5. If dotenv unavailable → .env files NOT loaded              │
│   6. Resolved environment missing CONTEXT7_API_KEY              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Subprocess (tool execution)                                     │
│   Running with: Project venv Python (correctly resolved)        │
│                                                                 │
│   - Receives environment from MCP server                        │
│   - Environment is MISSING .env variables                       │
│   - Tool fails: "CONTEXT7_API_KEY not set"                      │
└─────────────────────────────────────────────────────────────────┘
```

### The Core Issue

**The MCP server process and the tool subprocess run with DIFFERENT Python environments.**

| Component       | Python Used                       | Has python-dotenv? | Has project deps? |
| --------------- | --------------------------------- | ------------------ | ----------------- |
| MCP Server      | Depends on how client starts it   | Maybe not          | Maybe not         |
| Tool Subprocess | Project venv (correctly resolved) | Yes                | Yes               |

The EnvResolver correctly resolves which Python to use for **tool execution** (the subprocess), but it runs **inside the MCP server process** which may not have python-dotenv installed.

### Why This Happens

1. **kiwi-mcp declares python-dotenv as a dependency** (pyproject.toml line 13)
2. **But the MCP client may not install kiwi-mcp properly**
   - Could run via `python /path/to/server.py` (no deps installed)
   - Could run via system Python without the package installed
   - Could run in a different venv that doesn't have kiwi-mcp installed

### Evidence

```python
# When python-dotenv is NOT available in MCP server process:
>>> from dotenv import dotenv_values
ImportError: No module named 'dotenv'

# EnvResolver gracefully degrades:
>>> resolver._load_dotenv_files()
{}  # Empty - no .env variables loaded

# Result: CONTEXT7_API_KEY never reaches the subprocess
```

---

## Why This Will Get Worse

The user correctly identifies a future concern:

> "In the future we'll have LLM threads within the MCP also running the MCP itself"

This creates nested execution contexts:

```
Amp → kiwi-mcp (env A) → subprocess (env B) → nested kiwi-mcp (env C) → subprocess (env D)
```

Each layer could have different:

- Python interpreters
- Installed packages
- Environment variables
- .env file access

**The current "graceful degradation" (silently skipping .env loading) makes debugging these issues extremely difficult.**

---

## Potential Solutions

### Solution 1: Make python-dotenv a Hard Requirement (Recommended)

**Change:** Fail fast if python-dotenv is not available instead of silently degrading.

```python
# env_resolver.py
def _load_dotenv_files(self) -> Dict[str, str]:
    try:
        from dotenv import dotenv_values
    except ImportError:
        raise RuntimeError(
            "python-dotenv is required for environment resolution. "
            "Install kiwi-mcp properly: pip install kiwi-mcp"
        )
    # ... rest of implementation
```

**Pros:**

- Clear error message tells user exactly what's wrong
- Forces proper installation of kiwi-mcp
- No silent failures

**Cons:**

- Breaking change for anyone running MCP server incorrectly
- Requires users to fix their MCP client configuration

---

### Solution 2: Built-in .env Parser (No External Dependency)

**Change:** Implement a simple .env parser that doesn't require python-dotenv.

```python
def _parse_env_file(self, path: Path) -> Dict[str, str]:
    """Parse .env file without external dependencies."""
    env_vars = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # Handle quoted values
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars
```

**Pros:**

- Works regardless of how MCP server is started
- Zero external dependencies for core functionality
- python-dotenv can still be used for advanced features (multiline, interpolation)

**Cons:**

- Duplicates functionality
- May not handle all .env edge cases (multiline values, escape sequences)
- Two code paths to maintain

---

### Solution 3: Wrapper Script Approach

**Change:** Have the subprocess run a wrapper that loads .env in the venv context.

```python
# The subprocess command becomes:
# python -c "from dotenv import load_dotenv; load_dotenv(); exec(open('tool.py').read())"
```

**Pros:**

- .env loading happens in the correct Python environment
- MCP server doesn't need python-dotenv

**Cons:**

- Complex command construction
- Harder to debug
- Security concerns with exec()

---

### Solution 4: Environment Passthrough from MCP Client

**Change:** Require MCP clients to load .env files and pass them via environment.

```json
// MCP client config
{
  "kiwi-mcp": {
    "command": "python",
    "args": ["-m", "kiwi_mcp.server"],
    "env": {
      "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}" // Client loads from .env
    }
  }
}
```

**Pros:**

- Clear separation of concerns
- MCP server doesn't need to know about .env files

**Cons:**

- Requires manual configuration per variable
- Breaks the "just works" experience
- Different clients handle env differently

---

### Solution 5: Hybrid Approach (Recommended)

**Change:** Combine solutions 1 and 2:

1. **Built-in simple parser** for basic KEY=value .env files
2. **Use python-dotenv** if available for advanced features
3. **Warn** (not fail) if neither works, with clear guidance

```python
def _load_dotenv_files(self) -> Dict[str, str]:
    env_vars = {}

    # Collect all .env file paths
    env_paths = self._get_env_file_paths()

    for path in env_paths:
        if not path.exists():
            continue

        # Try python-dotenv first (handles advanced cases)
        try:
            from dotenv import dotenv_values
            vars = dotenv_values(path)
            env_vars.update(vars)
            logger.debug(f"Loaded {len(vars)} vars from {path} (via python-dotenv)")
            continue
        except ImportError:
            pass

        # Fall back to simple parser
        try:
            vars = self._parse_env_file_simple(path)
            env_vars.update(vars)
            logger.debug(f"Loaded {len(vars)} vars from {path} (via simple parser)")
        except Exception as e:
            logger.warning(f"Failed to parse {path}: {e}")

    if not env_vars and env_paths:
        logger.warning(
            "No .env variables loaded. For best results, ensure kiwi-mcp "
            "is properly installed: pip install kiwi-mcp"
        )

    return env_vars
```

**Pros:**

- Works in any environment (no hard dependency)
- Uses best available parser
- Clear warnings help debugging
- Graceful degradation with visibility

**Cons:**

- More code to maintain
- Two parsing implementations

---

## Recommendation

**Implement Solution 5 (Hybrid Approach)** because:

1. **It solves the immediate problem** - .env files load even without python-dotenv
2. **It's future-proof** - nested MCP contexts will work
3. **It's debuggable** - warnings tell users what's happening
4. **It's backward compatible** - existing setups keep working
5. **It follows the data-driven philosophy** - no special configuration needed

### Implementation Priority

1. Add simple .env parser to EnvResolver
2. Add fallback logic (try python-dotenv, fall back to simple parser)
3. Add warning when no .env files could be loaded
4. Update documentation on proper kiwi-mcp installation

---

## Additional Considerations

### MCP Client Configuration Best Practice

Document that MCP clients should run kiwi-mcp properly:

```json
{
  "kiwi-mcp": {
    "command": "/path/to/project/.venv/bin/python",
    "args": ["-m", "kiwi_mcp.server"],
    "cwd": "/path/to/project"
  }
}
```

Or with pipx:

```json
{
  "kiwi-mcp": {
    "command": "pipx",
    "args": ["run", "kiwi-mcp"]
  }
}
```

### Testing

Add test that verifies .env loading works without python-dotenv:

```python
def test_env_loading_without_dotenv(monkeypatch):
    # Simulate missing python-dotenv
    monkeypatch.setitem(sys.modules, 'dotenv', None)

    resolver = EnvResolver(project_path=tmp_path)
    env = resolver.resolve()

    assert "MY_VAR" in env  # From .env file via simple parser
```

---

## References

- [ENVIRONMENT_RESOLUTION_ARCHITECTURE.md](./ENVIROMENT_RESOLUTION_ARCHETECTURE.md)
- [pyproject.toml](/home/leo/projects/kiwi-mcp/pyproject.toml) - python-dotenv dependency
- [env_resolver.py](/home/leo/projects/kiwi-mcp/kiwi_mcp/runtime/env_resolver.py) - Current implementation
