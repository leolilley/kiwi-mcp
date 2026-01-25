# Init Process Design

**Date:** 2026-01-25  
**Status:** Draft  
**Author:** Kiwi Team  
**Phase:** 8 (Deep Implementation Plan)

---

## Executive Summary

This document defines the **remote-first initialization process** for Kiwi MCP. Users connect to the MCP like any other, run an `init` directive remotely (no local files initially), which bootstraps their userspace with core tools and the harness.

**Core Principle:** System information is a first-class `item_type`. The LLM queries it through the standard 4 meta-tools, just like directives, tools, and knowledge. No special injection, no conditional handling.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     INIT FLOW (Remote-First)                             │
│                                                                          │
│  User connects MCP → runs init directive → MCP bootstraps userspace     │
│                                                                          │
│  Before init: No ~/.ai folder exists                                     │
│  After init:  Full Kiwi userspace with harness, runtimes, core tools    │
│                                                                          │
│  Key insight: Init directive uses the same tools as everything else:    │
│  execute(system, run, paths) → knows where to create userspace          │
│  load(directive, init) → loads init directive from registry             │
│  execute(directive, run, init) → runs the init steps                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Problem We Solved

### The Old Approach (Rejected)

The previous design had these problems:

```python
# WRONG - Special conditional handling
async def _run_directive(self, directive_name: str, params: dict) -> dict:
    if directive_name == "init" and not self._userspace_exists():
        directive_data = await self._load_from_registry(directive_name)
    else:
        directive_data = await self.load(directive_name)

    # WRONG - Magic context injection
    execution_context = ExecutionContext(...)
    return {
        "directive": directive_data,
        "_context": execution_context.to_dict(),  # ← Hidden magic
    }
```

Problems:

1. **Special cases** - `init` is treated differently from other directives
2. **Hidden injection** - `_context` is magic, not discoverable
3. **Not composable** - Other directives that need system info must use the same hack
4. **Not permission-controlled** - No way to limit what system info is exposed

### The New Approach: System as an Item Type

System information is a first-class `item_type`, accessed through the standard 4 meta-tools:

```
search(item_type="system", query="userspace")
load(item_type="system", item_id="paths")
execute(item_type="system", action="run", item_id="paths")
help(topic="system")
```

This means:

1. **No special cases** - Init is just a directive that queries system info
2. **Discoverable** - LLM can search for what system info is available
3. **Composable** - Any directive can query system info the same way
4. **Permission-controlled** - System items have explicit access controls

---

## The System Item Type

### Design Philosophy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SYSTEM AS ITEM TYPE                              │
│                                                                          │
│  Kiwi's 4 meta-tools work with 4 item types:                             │
│                                                                          │
│  BEFORE:                                                                 │
│  • directive (workflow instructions)                                     │
│  • tool (executable scripts)                                             │
│  • knowledge (domain information)                                        │
│                                                                          │
│  AFTER:                                                                  │
│  • directive (workflow instructions)                                     │
│  • tool (executable scripts)                                             │
│  • knowledge (domain information)                                        │
│  • system (runtime environment info) ← NEW                               │
│                                                                          │
│  Same API, same patterns, same permission model.                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### System Items Catalog

The system item type exposes a fixed catalog of items:

| Item ID   | Description         | Fields                                                             |
| --------- | ------------------- | ------------------------------------------------------------------ |
| `paths`   | Filesystem paths    | `userspace_dir`, `home_dir`, `cwd`, `temp_dir`, `userspace_exists` |
| `runtime` | Runtime environment | `platform`, `os_name`, `arch`, `python_version`                    |
| `shell`   | Shell configuration | `shell`, `shell_name`, `supports_bash`, `supports_powershell`      |
| `mcp`     | MCP server info     | `kiwi_version`, `server_name`, `capabilities`                      |

### Security: Allowlist Only

System items are **read-only** and expose only **allowlisted, safe information**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SECURITY MODEL                                   │
│                                                                          │
│  EXPOSED (safe):                                                         │
│  • Platform (linux, darwin, win32)                                       │
│  • Home directory path                                                   │
│  • Userspace directory path                                              │
│  • Shell name (bash, zsh, powershell)                                    │
│  • MCP version                                                           │
│  • Userspace exists flag                                                 │
│                                                                          │
│  NOT EXPOSED (sensitive):                                                │
│  • Full environment variables                                            │
│  • API keys                                                              │
│  • Tokens                                                                │
│  • Network configuration                                                 │
│  • User credentials                                                      │
│                                                                          │
│  Actions allowed:                                                        │
│  • run: ✓ (returns info)                                                 │
│  • create/update/delete/publish: ✗ (read-only)                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation: SystemHandler

### Handler Structure

```python
# kiwi_mcp/handlers/system/handler.py

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class SystemItem:
    """A system information item."""
    item_id: str
    title: str
    description: str
    fields: dict

class SystemHandler:
    """
    Handler for system item type.

    Virtual provider - no filesystem dependency.
    Returns computed runtime information.
    """

    # Stable catalog of system items
    CATALOG = {
        "paths": {
            "title": "Filesystem Paths",
            "description": "Project, userspace, and home directory paths",
        },
        "runtime": {
            "title": "Runtime Environment",
            "description": "Platform, OS, architecture, Python version",
        },
        "shell": {
            "title": "Shell Configuration",
            "description": "Shell type and capabilities",
        },
        "mcp": {
            "title": "MCP Server Info",
            "description": "Kiwi version and capabilities",
        },
    }

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = project_path

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search system items by query."""
        results = []
        query_lower = query.lower()

        for item_id, meta in self.CATALOG.items():
            # Simple text matching
            if (query_lower in item_id.lower() or
                query_lower in meta["title"].lower() or
                query_lower in meta["description"].lower()):
                results.append({
                    "item_id": item_id,
                    "item_type": "system",
                    "title": meta["title"],
                    "description": meta["description"],
                    "source": "local",
                })

        return results[:limit]

    async def load(self, item_id: str) -> dict:
        """Load system item by ID."""
        if item_id not in self.CATALOG:
            return {"error": f"Unknown system item: {item_id}"}

        # Compute the item
        return await self._compute_item(item_id)

    async def execute(self, action: str, item_id: str, parameters: dict) -> dict:
        """Execute action on system item."""

        # System items are read-only
        if action not in ("run",):
            return {
                "error": f"System items are read-only. Action '{action}' not allowed.",
                "allowed_actions": ["run"],
            }

        if item_id not in self.CATALOG:
            return {"error": f"Unknown system item: {item_id}"}

        # Run returns the computed item
        return await self._compute_item(item_id)

    async def _compute_item(self, item_id: str) -> dict:
        """Compute system item values (fresh each time)."""

        if item_id == "paths":
            return self._get_paths()
        elif item_id == "runtime":
            return self._get_runtime()
        elif item_id == "shell":
            return self._get_shell()
        elif item_id == "mcp":
            return self._get_mcp()
        else:
            return {"error": f"Unknown system item: {item_id}"}

    def _get_paths(self) -> dict:
        """Get filesystem paths."""
        userspace_dir = os.environ.get(
            "KIWI_USERSPACE_DIR",
            os.path.expanduser("~/.ai")
        )
        userspace_path = Path(userspace_dir)

        return {
            "item_id": "paths",
            "item_type": "system",
            "data": {
                "userspace_dir": userspace_dir,
                "userspace_exists": userspace_path.exists(),
                "home_dir": os.path.expanduser("~"),
                "cwd": os.getcwd(),
                "temp_dir": os.environ.get("TMPDIR", "/tmp"),
                "project_path": self.project_path,
            }
        }

    def _get_runtime(self) -> dict:
        """Get runtime environment info."""
        import platform

        return {
            "item_id": "runtime",
            "item_type": "system",
            "data": {
                "platform": sys.platform,  # linux, darwin, win32
                "os_name": platform.system(),  # Linux, Darwin, Windows
                "os_release": platform.release(),
                "arch": platform.machine(),  # x86_64, arm64
                "python_version": platform.python_version(),
            }
        }

    def _get_shell(self) -> dict:
        """Get shell configuration."""
        shell = os.environ.get("SHELL", "")
        shell_name = os.path.basename(shell) if shell else "unknown"

        return {
            "item_id": "shell",
            "item_type": "system",
            "data": {
                "shell": shell,
                "shell_name": shell_name,  # bash, zsh, fish, etc.
                "supports_bash": shell_name in ("bash", "zsh", "sh"),
                "supports_powershell": sys.platform == "win32",
                "path_separator": os.sep,
            }
        }

    def _get_mcp(self) -> dict:
        """Get MCP server info."""
        from kiwi_mcp.server import __version__, __package_name__

        return {
            "item_id": "mcp",
            "item_type": "system",
            "data": {
                "kiwi_version": __version__,
                "server_name": __package_name__,
                "item_types": ["directive", "tool", "knowledge", "system"],
                "actions": ["run", "create", "update", "delete", "publish"],
            }
        }
```

### Routing in Tools

Update each tool to route `item_type="system"` to `SystemHandler`:

```python
# kiwi_mcp/tools/execute.py (updated)

async def execute(self, arguments: dict) -> str:
    item_type = arguments.get("item_type")
    action = arguments.get("action")
    item_id = arguments.get("item_id")
    parameters = arguments.get("parameters", {})
    project_path = arguments.get("project_path")

    # System items don't require project_path
    if item_type == "system":
        from kiwi_mcp.handlers.system.handler import SystemHandler
        handler = SystemHandler(project_path=project_path)
        result = await handler.execute(action, item_id, parameters)
        return self._format_response(result)

    # Other types require project_path
    if not project_path:
        return self._format_response({
            "error": "project_path is REQUIRED for directive/tool/knowledge operations"
        })

    # ... rest of existing logic
```

---

## How Init Works Now

### The Init Directive (No Special Handling)

The init directive is just a normal directive that:

1. Queries system info using standard tools
2. Checks if userspace exists
3. Creates it if not

```xml
<directive name="init" version="1.0.0">
  <metadata>
    <description>Initialize Kiwi userspace with core tools and harness</description>
    <category>core</category>
    <author>kiwi</author>

    <permissions>
      <!-- Query system info -->
      <execute resource="kiwi-mcp" action="run" item_type="system" />
      <!-- Create userspace directories -->
      <write resource="filesystem" path="{system.paths.userspace_dir}/**" />
      <!-- Download from registry -->
      <read resource="registry" path="**" />
    </permissions>
  </metadata>

  <inputs>
    <input name="force" type="boolean" default="false">
      Force re-initialization even if userspace exists
    </input>
  </inputs>

  <process>
    <step name="get_system_info">
      <description>Query system information</description>
      <action><![CDATA[
Query system information using standard MCP tools:

1. Get paths:
   mcp__kiwi_mcp__execute(
     item_type="system",
     action="run",
     item_id="paths"
   )

   Returns:
   {
     "userspace_dir": "/home/user/.ai",
     "userspace_exists": false,
     "home_dir": "/home/user",
     "cwd": "/home/user/projects/myapp"
   }

2. Get runtime info (for platform-specific setup):
   mcp__kiwi_mcp__execute(
     item_type="system",
     action="run",
     item_id="runtime"
   )

   Returns:
   {
     "platform": "linux",
     "os_name": "Linux",
     "arch": "x86_64",
     "python_version": "3.11.5"
   }

3. Get shell info (for runtime scripts):
   mcp__kiwi_mcp__execute(
     item_type="system",
     action="run",
     item_id="shell"
   )

   Returns:
   {
     "shell": "/bin/bash",
     "shell_name": "bash",
     "supports_bash": true,
     "path_separator": "/"
   }
      ]]></action>
    </step>

    <step name="check_existing">
      <description>Check if userspace already exists</description>
      <action><![CDATA[
From the paths result, check userspace_exists:

If userspace_exists == true AND force == false:
  - Report that userspace already exists at {userspace_dir}
  - Ask user if they want to re-initialize
  - Exit if user declines

If userspace_exists == false OR force == true:
  - Proceed with initialization
      ]]></action>
    </step>

    <step name="create_structure">
      <description>Create userspace folder structure</description>
      <action><![CDATA[
Create the following directory structure using the paths from system info:

{userspace_dir}/
├── directives/
│   └── core/
├── tools/
│   └── core/
├── knowledge/
├── vectors/
├── threads/
├── logs/
├── cache/
└── config.yaml

Use platform-appropriate commands based on system.runtime.platform.
      ]]></action>
    </step>

    <step name="download_core_items">
      <description>Download core directives, tools, and knowledge from registry</description>
      <action><![CDATA[
Download core items using standard load tool:

# Core directives
for directive in [init, sync_directives, create_directive, ...]:
  mcp__kiwi_mcp__load(
    item_type="directive",
    item_id=directive,
    source="registry",
    destination="user"
  )

# Core tools
for tool in [kiwi_harness, http_client, thread_manager, ...]:
  mcp__kiwi_mcp__load(
    item_type="tool",
    item_id=tool,
    source="registry",
    destination="user"
  )

# Core knowledge
for knowledge in [kiwi-overview, directive-creation-pattern, ...]:
  mcp__kiwi_mcp__load(
    item_type="knowledge",
    item_id=knowledge,
    source="registry",
    destination="user"
  )
      ]]></action>
    </step>

    <step name="create_config">
      <description>Create user configuration</description>
      <action><![CDATA[
Create {userspace_dir}/config.yaml with system-detected values:

version: "1.0.0"
paths:
  userspace: "{system.paths.userspace_dir}"
runtime:
  platform: "{system.runtime.platform}"
  shell: "{system.shell.shell}"
registry:
  url: "https://api.kiwi.ai"
  sync_interval: "1h"
      ]]></action>
    </step>

    <step name="verify">
      <description>Verify installation</description>
      <action><![CDATA[
Verify by querying system paths again:

mcp__kiwi_mcp__execute(
  item_type="system",
  action="run",
  item_id="paths"
)

Confirm userspace_exists is now true.
      ]]></action>
    </step>
  </process>

  <outputs>
    <success>
✓ Kiwi userspace initialized at {userspace_dir}

Platform: {platform}
Shell: {shell_name}

Next steps:
- Bootstrap a project: bootstrap python|node|web
- Create your first directive: create directive my_task
- Get help: help(topic="overview")
    </success>
  </outputs>
</directive>
```

### The Flow (No Special Cases)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INIT FLOW WITH SYSTEM ITEM TYPE                      │
│                                                                              │
│  User: "init my kiwi workspace"                                              │
│          │                                                                   │
│          ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  MCP receives: execute(directive, run, init)                            │ │
│  │                                                                          │ │
│  │  Normal flow - no special handling:                                      │ │
│  │  1. Load "init" directive from registry (it's not local yet)             │ │
│  │  2. Return directive to LLM                                              │ │
│  └────────────────────────────┬────────────────────────────────────────────┘ │
│                               │                                              │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  LLM follows init directive steps:                                       │ │
│  │                                                                          │ │
│  │  Step 1: execute(system, run, paths)                                     │ │
│  │          → { userspace_dir: "~/.ai", userspace_exists: false }           │ │
│  │                                                                          │ │
│  │  Step 2: execute(system, run, runtime)                                   │ │
│  │          → { platform: "linux", arch: "x86_64" }                         │ │
│  │                                                                          │ │
│  │  Step 3: Create directories at userspace_dir                             │ │
│  │                                                                          │ │
│  │  Step 4: load(directive, init, source=registry, destination=user)        │ │
│  │          load(tool, kiwi_harness, source=registry, destination=user)     │ │
│  │          ... etc                                                         │ │
│  │                                                                          │ │
│  │  Step 5: execute(system, run, paths)                                     │ │
│  │          → { userspace_dir: "~/.ai", userspace_exists: true }            │ │
│  │                                                                          │ │
│  │  Done! No magic, just standard tool calls.                               │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## How Intent Handler Uses This

The `intent_handler` directive (from MCP Wrapper) uses the same pattern:

```xml
<step name="get_context">
  <description>Get system context for response formatting</description>
  <action><![CDATA[
Query system info to understand the execution context:

# Get platform for platform-specific formatting
system_runtime = mcp__kiwi_mcp__execute(
  item_type="system",
  action="run",
  item_id="runtime"
)

# Get MCP info for capability awareness
system_mcp = mcp__kiwi_mcp__execute(
  item_type="system",
  action="run",
  item_id="mcp"
)

Use this info to:
- Format paths correctly for the platform
- Understand available capabilities
- Adapt responses to the environment
  ]]></action>
</step>
```

---

## Discovery: How LLMs Find System Info

### Via Search

```python
# LLM can search for system information naturally
search(item_type="system", query="home directory")
# Returns: [{ item_id: "paths", title: "Filesystem Paths", ... }]

search(item_type="system", query="platform")
# Returns: [{ item_id: "runtime", title: "Runtime Environment", ... }]
```

### Via Help

```python
help(topic="system")
# Returns documentation about system item type:
#
# System Items - Runtime environment information
#
# Available items:
# - paths: Filesystem paths (userspace_dir, home_dir, cwd)
# - runtime: Platform and version info (platform, arch, python_version)
# - shell: Shell configuration (shell_name, supports_bash)
# - mcp: MCP server info (kiwi_version, capabilities)
#
# Example:
#   execute(item_type="system", action="run", item_id="paths")
```

---

## Implementation Phases

### Phase 1: SystemHandler (1 day)

1. Create `kiwi_mcp/handlers/system/handler.py`
2. Implement `_get_paths()`, `_get_runtime()`, `_get_shell()`, `_get_mcp()`
3. Add tests

**Files:**

- `kiwi_mcp/handlers/system/__init__.py` (new)
- `kiwi_mcp/handlers/system/handler.py` (new)
- `tests/handlers/test_system.py` (new)

### Phase 2: Tool Routing (0.5 day)

1. Update `ExecuteTool` to route `system` type
2. Update `SearchTool` to route `system` type
3. Update `LoadTool` to route `system` type (load = execute for system)
4. Update `HelpTool` with system topic

**Files:**

- `kiwi_mcp/tools/execute.py` (modify)
- `kiwi_mcp/tools/search.py` (modify)
- `kiwi_mcp/tools/load.py` (modify)
- `kiwi_mcp/tools/help.py` (modify)

### Phase 3: Init Directive (0.5 day)

1. Update init directive to use system item type
2. Test full init flow
3. Add to registry

**Files:**

- Registry: `directives/core/init.md` (update)
- `tests/integration/test_init.py` (new)

---

## Success Metrics

- [ ] `execute(system, run, paths)` returns correct paths
- [ ] `execute(system, run, runtime)` returns correct platform info
- [ ] `search(system, "userspace")` returns paths item
- [ ] `help(topic="system")` documents system items
- [ ] Init directive works without special handling
- [ ] Intent handler can query system info
- [ ] No sensitive information exposed
- [ ] System items are read-only

---

## Related Documents

- `THREAD_AND_STREAMING_ARCHITECTURE.md` - Harness and thread design
- `MCP_WRAPPER_DESIGN.md` - Intent handler using system info
- `KNOWLEDGE_SYSTEM_DESIGN.md` - RAG-based help system
