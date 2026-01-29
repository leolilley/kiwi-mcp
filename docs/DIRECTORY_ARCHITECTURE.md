# Directory Architecture Design

**Status:** APPROVED  
**Date:** 2026-01-30

---

## The Two Packages

### 1. `lilux` (Kernel Only)

`pip install lilux` - Just the kernel:

- "Dumb" MCP server with 5 primitive tools (search, load, execute, sign, help)
- Handlers for directive/tool/knowledge parsing
- Runtime services: AuthStore (uses OS keyring), EnvResolver
- **No bundled content** - just Python code

### 2. `rye-lilux` (Kernel + Content Bundle)

`pip install rye-lilux` - Gets you everything:

- Includes lilux kernel
- Includes RYE content bundle (tools, directives, knowledge)
- **Protected** core tools - users can shadow directives but not tools/knowledge

---

## Directory Locations

### A. Package Space (Read-Only, ships with pip)

**pip install lilux:**

```
site-packages/
  lilux/                    # Kernel code only
    server.py
    tools/
    handlers/
    runtime/
    utils/
```

**pip install rye-lilux:**

```
site-packages/
  rye_lilux/
    lilux/                  # Kernel (same as standalone)
      server.py
      tools/
      handlers/
      runtime/
      utils/

    rye/                    # RYE content bundle
      .ai/
        tools/
          core/             # PROTECTED (system, registry, rag, telemetry/)
          primitives/       # PROTECTED (http_client, subprocess)
          runtimes/         # PROTECTED (auth shim, env_resolver shim)
          capabilities/     # PROTECTED
        directives/
          core/             # Shadowable by user
        knowledge/
          lilux/            # PROTECTED
          rye/              # PROTECTED
```

**Resolution:** Use `importlib.resources` to find package content at runtime.

---

### B. Project Space (Per-Project Customizations)

```
<project>/
  .ai/
    directives/             # Project-specific directives
    tools/                  # Project-specific tools
    knowledge/              # Project-specific knowledge
    AGENTS.md               # Project agent instructions
```

**Env var:** Detected from `project_path` parameter passed to MCP tools.

---

### C. User Space (Global User Customizations)

Where user's global content lives (not project-specific).

```
~/.ai/                      # Default, or $USER_SPACE
  directives/               # User's global directives
  tools/                    # User's global tools
  knowledge/                # User's global knowledge
  AGENTS.md                 # User's global agent instructions
```

**Env var:** `USER_SPACE` (defaults to `~/.ai/`)

**Cross-platform:** `~` expands correctly on all platforms:

- Linux/macOS: `/home/user/.ai/` or `/Users/user/.ai/`
- Windows: `C:\Users\user\.ai\`

**Note:** Lilux kernel does NOT save content. This is purely for user customizations.

---

### D. RYE State (Runtime State, NOT Content)

RYE tools need persistent state. This is NOT content - it's app state.

**Owner:** RYE tools (registry, telemetry), NOT lilux kernel.

```
$XDG_STATE_HOME/rye/        # ~/.local/state/rye/ on Linux
  signing-keys/
    {id}.private.pem
    {id}.public.pem
    primary.pem             # Symlink to active key
  sessions/
    {session_id}.json       # Temporary, for device auth flow
  telemetry.yaml
```

**Auth tokens:** Stored in OS keyring via kernel AuthStore (no files).

**Cross-platform state locations:**

- Linux: `$XDG_STATE_HOME/rye/` → `~/.local/state/rye/`
- macOS: `~/Library/Application Support/rye/`
- Windows: `%LOCALAPPDATA%\rye\`

---

### E. Lilux Cache (Kernel-Level, Ephemeral)

Kernel-level caching for primitives. Re-downloadable/rebuildable.

```
$XDG_CACHE_HOME/lilux/      # ~/.cache/lilux/ on Linux
  http/                     # HTTP response cache (http_client primitive)
  vectors/                  # Vector embeddings cache
```

**Cross-platform cache locations:**

- Linux: `$XDG_CACHE_HOME/lilux/` → `~/.cache/lilux/`
- macOS: `~/Library/Caches/lilux/`
- Windows: `%LOCALAPPDATA%\lilux\Cache\`

---

## Resolution Order

When searching for a directive/tool/knowledge:

1. **Project space:** `<project>/.ai/<type>/`
2. **User space:** `$USER_SPACE/<type>/` (default `~/.ai/<type>/`)
3. **Package space:** `rye_lilux/rye/.ai/<type>/` (via importlib.resources)

---

## Final Structure Summary

```
# Package (read-only, pip installed)
site-packages/rye_lilux/
  lilux/                        # Kernel
  rye/.ai/                      # Bundled RYE content

# Project (per-project customizations)
<project>/.ai/                  # Highest priority

# User content (global customizations)
~/.ai/                          # $USER_SPACE
  directives/
  tools/
  knowledge/
  AGENTS.md

# RYE state (runtime, not content)
~/.local/state/rye/             # $XDG_STATE_HOME/rye/
  signing-keys/
  sessions/
  telemetry.yaml

# Lilux cache (kernel, ephemeral)
~/.cache/lilux/                 # $XDG_CACHE_HOME/lilux/
  http/
  vectors/
```

---

## Environment Variables

| Var                  | Purpose                | Default           |
| -------------------- | ---------------------- | ----------------- |
| `USER_SPACE`         | User content directory | `~/.ai/`          |
| `XDG_STATE_HOME`     | XDG state base         | `~/.local/state/` |
| `XDG_CACHE_HOME`     | XDG cache base         | `~/.cache/`       |
| `RYE_REGISTRY_URL`   | Registry API URL       | Supabase URL      |
| `RYE_REGISTRY_TOKEN` | CI auth override       | (none)            |

---

## Ownership Summary

| What            | Owner         | Location                                     |
| --------------- | ------------- | -------------------------------------------- |
| Kernel code     | lilux         | `site-packages/lilux/` or `rye_lilux/lilux/` |
| Bundled content | rye           | `site-packages/rye_lilux/rye/.ai/`           |
| User content    | user          | `$USER_SPACE/` (default `~/.ai/`)            |
| Project content | user          | `<project>/.ai/`                             |
| Auth tokens     | lilux kernel  | OS keyring                                   |
| Signing keys    | rye registry  | `$XDG_STATE_HOME/rye/`                       |
| Sessions        | rye registry  | `$XDG_STATE_HOME/rye/`                       |
| Telemetry       | rye telemetry | `$XDG_STATE_HOME/rye/`                       |
| HTTP cache      | lilux kernel  | `$XDG_CACHE_HOME/lilux/`                     |
| Vector cache    | lilux kernel  | `$XDG_CACHE_HOME/lilux/`                     |
