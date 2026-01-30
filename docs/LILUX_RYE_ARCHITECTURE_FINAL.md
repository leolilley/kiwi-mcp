# Lilux/RYE Architecture: Generic Kernel + Intelligent Content

**Date:** 2026-01-30
**Status:** Production-Ready Architecture
**Purpose:** Clear separation between Lilux (generic execution layer) and RYE (intelligent content layer)

---

## Executive Summary

**Lilux is generic. RYE is intelligent.**

- **Lilux** = Generic Execution Layer (primitives, routing, MCP tools) - **doesn't know content shapes**
- **RYE** = Intelligence Layer (directives, tools, knowledge) - **defines content formats and logic**

They are **separate packages** but developed in a **monorepo** for simplicity.

---

## Core Mental Model: Plug-in System

### Lilux = Operating System Kernel (Dumb)

**Lilux provides generic primitives and routing - knows nothing about application formats.**

| Analogy | Lilux | RYE |
|----------|---------|------|
| Operating System | Kernel (CPU, memory, I/O) | Applications that run on top |
| Plug-in System | Host application + routing | Plug-ins that use primitives |

**What Lilux Provides:**
- **Primitives**: subprocess, http_client, chains, locks, auth
- **Routing**: "You asked to execute X, let me find X and route it"
- **Handlers**: Generic routers that **don't parse XML, don't know about signatures, don't validate schemas**

**Kernel handlers are DUMB routers:**

```python
# lilux/handlers/directive/handler.py (DUMB ROUTER ONLY)

class DirectiveHandler:
    def execute(self, item_id, parameters):
        """Just find and route - don't understand content"""
        # Find the file (generic routing)
        file_path = find_content("directive", item_id)
        
        # Pass to RYE tool that understands directives
        # Kernel doesn't know what a directive looks like!
        result = call_primitive(
            primitive="tool",
            tool_id="execute_directive",  # RYE tool defines this
            params={"file": file_path, "params": parameters}
        )
        return result
```

### RYE = Intelligent Applications (Smart)

**RYE defines content shapes and domain logic - uses kernel primitives to do work.**

| What RYE Understands | Purpose |
|----------------------|---------|
| Directive XML format | How directives are structured |
| Tool metadata format | How tools are defined |
| Knowledge frontmatter format | How knowledge is organized |
| Signature formats | How signatures work |
| Domain workflows | How to orchestrate directives |

**RYE tools use kernel primitives:**

```python
# rye/.ai/tools/core/execute_directive.py (SMART - understands content)

def execute_directive(file_path, params):
    """Understand directive XML, parse, execute"""
    content = file_path.read_text()
    
    # Parse XML (RYE understands directive shape - kernel doesn't!)
    xml_data = parse_directive_xml(content)
    
    # Validate signature (RYE understands signatures - kernel doesn't!)
    if not is_valid_signature(content):
        raise ValueError("Invalid signature")
    
    # Execute using kernel primitives (dumb execution)
    for step in xml_data["steps"]:
        if step["type"] == "command":
            subprocess_primitive(step["command"])  # Use kernel primitive
        elif step["type"] == "http":
            http_primitive(step["url"])  # Use kernel primitive
```

---

## Critical Clarifications

### 1. Two Registries - Different Purposes

| Registry | Location | Purpose | Stays Where? |
|-----------|----------|---------|--------------|
| `handlers/registry.py` | `lilux/handlers/` | **TypeHandlerRegistry** - routes "directive" → DirectiveHandler, "tool" → ToolHandler | **Lilux (kernel)** |
| `core/registry.py` | `rye/.ai/tools/` | **Registry Tool** - Supabase operations (auth, sync, publish, keys) | **RYE (content)** |

**TypeHandlerRegistry stays in kernel** - it's infrastructure for routing to type handlers.
**Registry Tool goes to RYE** - it's domain intelligence for content operations.

### 2. MCP Server - NOT CLI

**WRONG thinking:**

```bash
$ lilux search "my-directive"
```

**CORRECT interaction:**

```
User: "search for lead generation directives"
LLM: [calls mcp__lilux__search(item_type="directive", query="lead generation")]
```

Lilux exposes **5 MCP tools**. Users interact through an LLM that calls these tools. The server starts via:

```bash
python -m lilux.server
```

And communicates over **stdio** with LLM client (Claude Desktop, Cursor, etc.).

### 3. Repository Structure: Monorepo

**Single repository** containing both packages:

```
github.com/leolilley/lilux-rye/  # Monorepo
├── lilux/                          # Kernel package (pip install lilux)
│   ├── __init__.py
│   ├── server.py                   # MCP server entry point
│   ├── tools/                      # 5 primitive MCP tools
│   │   ├── __init__.py
│   │   ├── search.py               # mcp__lilux__search
│   │   ├── load.py                 # mcp__lilux__load
│   │   ├── execute.py              # mcp__lilux__execute
│   │   ├── sign.py                 # mcp__lilux__sign
│   │   └── help.py                 # mcp__lilux__help
│   │
│   ├── primitives/                 # Low-level execution primitives
│   │   ├── __init__.py
│   │   ├── executor.py             # ChainResolver, PrimitiveExecutor
│   │   ├── subprocess.py           # SubprocessPrimitive (dumb execution)
│   │   ├── http_client.py          # HttpClientPrimitive (dumb HTTP)
│   │   ├── chain_validator.py      # ChainValidator
│   │   ├── lockfile.py            # Lockfile management
│   │   └── errors.py             # Execution errors
│   │
│   ├── handlers/                   # Type-specific handlers (routers)
│   │   ├── __init__.py
│   │   ├── registry.py            # TypeHandlerRegistry (routes item types)
│   │   ├── directive/             # DirectiveHandler (router)
│   │   │   ├── __init__.py
│   │   │   └── handler.py       # Just routes, doesn't parse XML
│   │   ├── tool/                 # ToolHandler (router)
│   │   │   ├── __init__.py
│   │   │   └── handler.py       # Just routes, doesn't parse metadata
│   │   └── knowledge/            # KnowledgeHandler (router)
│   │       ├── __init__.py
│   │       └── handler.py       # Just routes, doesn't parse frontmatter
│   │
│   ├── runtime/                    # Runtime services
│   │   ├── __init__.py
│   │   ├── auth.py                # AuthStore (OS keychain)
│   │   ├── env_resolver.py          # Environment variable resolution
│   │   └── lockfile_store.py      # Lockfile persistence
│   │
│   ├── storage/
│   │   └── vector/               # Vector store infrastructure
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── local.py
│   │       ├── api_embeddings.py
│   │       ├── manager.py
│   │       └── hybrid.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── tool_schema.py        # Tool metadata extraction
│   │
│   └── utils/                      # KERNEL utilities (for routing ONLY!)
│       ├── __init__.py
│       ├── resolvers.py            # ToolResolver, PathResolver (find files)
│       ├── parsers.py             # XML, YAML, frontmatter parsing (basic only)
│       ├── validators.py          # ValidationManager (basic validation)
│       ├── schema_validator.py     # Schema validation (basic checks)
│       ├── logger.py             # Logging setup
│       ├── paths.py             # Path utilities
│       ├── extensions.py        # Extension discovery
│       ├── env_loader.py        # Environment loading
│       ├── output_manager.py    # Output formatting
│       └── __init__.py         # Exports only what's needed
│
│   ├── pyproject.toml            # Kernel package config
│   └── README.md
│
├── rye/                            # Content package (pip install rye-lilux)
│   ├── __init__.py
│   └── .ai/                        # RYE content bundle
│       ├── directives/
│       │   ├── core/               # Core directives (shadowable)
│       │   │   ├── init.md
│       │   │   ├── bootstrap.md
│       │   │   ├── sync_directives.md
│       │   │   ├── run_directive.md
│       │   │   └── ...
│       │   └── meta/               # Meta directives (orchestration)
│       │
│       ├── tools/                    # RYE tools
│       │   ├── core/               # PROTECTED - cannot override
│       │   │   ├── system.py      # Environment vars, paths, RAG
│       │   │   ├── registry.py    # Remote registry (Supabase), NOT TypeHandlerRegistry!
│       │   │   ├── rag.py         # Vector search
│       │   │   ├── telemetry.py   # Telemetry collection
│       │   │   ├── protection.py  # Protection enforcement
│       │   │   └── ...
│       │   │
│       │   ├── threads/            # PROTECTED
│       │   │   ├── create.py
│       │   │   ├── list.py
│       │   │   └── ...
│       │   │
│       │   ├── extractors/         # PROTECTED
│       │   │   └── ...
│       │   │
│       │   └── capabilities/       # PROTECTED
│       │       └── ...
│       │
│       ├── llm/                # LLM provider configs
│       │   ├── openai.py
│       │   ├── anthropic.py
│       │   └── ...
│       │
│       └── knowledge/              # Core knowledge
│           ├── lilux/             # PROTECTED - cannot override (renamed from "kernel")
│           │   ├── primitives.md
│           │   ├── handlers.md
│           │   └── architecture.md
│           │
│           └── concepts/
│               ├── ...
│
│   ├── pyproject.toml            # Content package config
│   └── README.md
│
├── tests/                          # Tests for both packages
├── pyproject.toml                  # Monorepo root config
├── .github/
│   └── workflows/
└── README.md
```

**Key characteristics:**
- **Lilux** = Generic infrastructure (knows nothing about content shapes)
- **RYE** = Intelligence (defines content shapes, domain logic)
- **RYE tools** = Plug-ins that extend kernel functionality
- **Kernel handlers** = Generic routers (don't understand content)

---

## Package Separation

### Package 1: `lilux` (Generic Kernel)

**Contains ONLY:**

| Component               | Purpose                                                      | Why?                        |
| ---------------------- | ------------------------------------------------------------ | ---------------------------- |
| `server.py`            | MCP server with 5 tools                                       | Kernel infrastructure         |
| `tools/`              | Search, Load, Execute, Sign, Help (MCP interface)            | Kernel interface             |
| `primitives/`         | Subprocess, HTTP, ChainResolver, Integrity                   | Dumb execution primitives    |
| `handlers/`           | Directive/Tool/Knowledge type handlers (routers only!)            | Kernel routing infrastructure |
| `handlers/registry.py` | **TypeHandlerRegistry** - routes item types to handlers            | Kernel routing              |
| `runtime/`            | AuthStore, env_resolver, lockfile_store                          | Kernel infrastructure         |
| `storage/vector/`     | Vector store infrastructure                                      | Kernel infrastructure         |
| `schemas/tool_schema.py` | Tool metadata extraction                                         | Kernel infrastructure         |
| `utils/parsers.py`     | **Basic** XML/YAML parsing (enough for routing, not validation)    | Kernel needs for routing     |
| `utils/validators.py`  | **Basic** validation (enough for routing, not content validation)   | Kernel needs for routing     |
| `utils/resolvers.py`   | ToolResolver, PathResolver (find where content is)                 | Kernel needs for routing     |
| `utils/logger.py`     | Logging setup                                                 | Kernel infrastructure         |
| `utils/env_loader.py`   | Environment loading                                           | Kernel infrastructure         |
| `utils/output_manager.py` | Output formatting                                           | Kernel infrastructure         |
| `utils/paths.py`     | Path utilities                                              | Kernel infrastructure         |
| `utils/extensions.py`  | Extension discovery                                         | Kernel infrastructure         |

**Install:**
```bash
pip install lilux
```

**Entry point:**
```bash
python -m lilux.server
```

**PyPI Package:**
```toml
[project]
name = "lilux"
version = "0.1.0"
description = "Lilux MCP Kernel - Generic execution layer with primitives"

dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "packaging>=24.0",
    "jsonschema>=4.0.0",
    "keyring>=23.0.0",
]

[project.scripts]
lilux = "lilux.server:main"
```

### Package 2: `rye-lilux` (Intelligent Content Bundle)

**Contains ONLY:**

| Component                    | Purpose                                | Why?                              |
| --------------------------- | -------------------------------------- | ---------------------------------- |
| `.ai/directives/core/`    | Core directives (shadowable)           | RYE intelligence                   |
| `.ai/directives/meta/`    | Meta directives (orchestration)        | RYE intelligence                   |
| `.ai/tools/core/system.py`  | System utilities (understands directives) | Extends kernel functionality       |
| `.ai/tools/core/registry.py` | **Registry Tool** (Supabase auth, sync) | RYE intelligence (not TypeHandlerRegistry) |
| `.ai/tools/core/rag.py`     | Vector search (understands .ai/ content) | RYE intelligence                   |
| `.ai/tools/core/telemetry.py` | Telemetry collection                        | RYE intelligence                   |
| `.ai/tools/core/protection.py` | Protection enforcement for RYE content       | RYE infrastructure                |
| `.ai/tools/threads/`       | Threading infrastructure                     | RYE intelligence                   |
| `.ai/tools/extractors/`     | Metadata extractors                        | RYE intelligence                   |
| `.ai/tools/capabilities/`   | Capability management                       | RYE intelligence                   |
| `.ai/tools/llm/`          | LLM provider configurations                 | RYE intelligence                   |
| `.ai/knowledge/lilux/`    | Kernel documentation (PROTECTED - renamed from "kernel") | RYE intelligence                |
| `.ai/knowledge/concepts/`   | Domain concepts                          | RYE intelligence                   |

**Install:**
```bash
pip install rye-lilux  # Gets both rye + lilux dependency
```

**PyPI Package:**
```toml
[project]
name = "rye-lilux"
version = "0.1.0"
description = "RYE content layer for Lilux MCP - intelligent content with domain logic"

dependencies = [
    "lilux>=0.1.0",  # ← Depends on kernel
]

[tool.setuptools]
packages = ["rye"]
package-data = { "rye" = [".ai/**/*"] }  # Bundle .ai/ folder
```

---

## Dependency Flow

```
User Installs: pip install rye-lilux

          pip install rye-lilux
                     │
                     ├─> lilux>=0.1.0 (generic kernel)
                     │    ├── server.py
                     │    ├── tools/ (5 MCP tools)
                     │    ├── primitives/ (dumb execution)
                     │    ├── handlers/ (routers)
                     │    └── utils/ (kernel routing only)
                     │
                     └─> rye-lilux (intelligent content)
                          ├── .ai/directives/
                          └── .ai/tools/ (core, threads, extractors, capabilities)
```

**Result:** User gets full system (generic kernel + intelligent content) in one install.

---

## Architecture Diagram: Plug-in System

```
┌────────────────────────────────────────────────────────────┐
│                USER'S LLM CLIENT                         │
│         (Claude Desktop, Cursor, etc.)                  │
├────────────────────────────────────────────────────────────┤
│                                                          │
│  User: "init my workspace"                               │
│  LLM: [calls mcp__lilux__execute(...)]                  │
└────────────────────────────────────────────────────────────┘
                          │ MCP (stdio)
                          ▼
┌────────────────────────────────────────────────────────────┐
│           LILUX KERNEL (Generic Layer)                │
│                                                          │
│  Kernel Primitives (DUMB - no content knowledge):      │
│  ┌──────────────────────────────────────────────────┐       │
│  │ subprocess_primitive  (just runs commands)     │       │
│  │ http_primitive       (just makes HTTP requests)  │       │
│  │ chain_primitive      (just resolves chains)       │       │
│  │ lock_primitive       (just manages locks)         │       │
│  │ auth_primitive       (just gets credentials)      │       │
│  │                                                  │       │
│  │ These are DUMB - don't know about directives,  │       │
│  │ tools, or knowledge formats                      │       │
│  └──────────────────────────────────────────────────┘       │
│                                                           │
│  Kernel Handlers (DUMB ROUTERS):                    │
│  ┌──────────────────────────────────────────────────┐       │
│  │ TypeHandlerRegistry: "Directive -> Directive    │       │
│  │                       Handler, Tool -> Tool    │       │
│  │                       Handler"                    │       │
│  │                                                  │       │
│  │ DirectiveHandler: "Find directive file,    │       │
│  │                    route to RYE tool"         │       │
│  │                    (doesn't parse XML)         │       │
│  │                                                  │       │
│  │ ToolHandler: "Find tool file,              │       │
│  │            route to RYE tool"               │       │
│  │            (doesn't parse metadata)         │       │
│  │                                                  │       │
│  │ KnowledgeHandler: "Find knowledge file,       │       │
│  │                   route to RYE tool"          │       │
│  │                   (doesn't parse frontmatter)    │       │
│  └──────────────────────────────────────────────────┘       │
│                                                           │
│  Kernel MCP Tools (Generic Interface):               │
│  ┌──────────────────────────────────────────────────┐       │
│  │ search: "Search for items in .ai/"          │       │
│  │ load: "Load item content from .ai/"           │       │
│  │ execute: "Route item to RYE tool"            │       │
│  │ sign: "Route signing to RYE tool"            │       │
│  │ help: "Show what's available"                 │       │
│  └──────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────┘
                          │ uses
                          ▼
┌────────────────────────────────────────────────────────────┐
│         RYE CONTENT (Intelligence Layer)                │
│                                                          │
│  RYE Tools (Understand Content Shapes):              │
│  ┌──────────────────────────────────────────────────┐       │
│  │ execute_directive: "Parse XML, validate,     │       │
│  │                     execute using primitives"   │       │
│  │                                              │       │
│  │ execute_tool: "Parse Python, validate,    │       │
│  │                execute using primitives"         │       │
│  │                                              │       │
│  │ sign_item: "Validate signature format,       │       │
│  │             sign with kernel primitive"         │       │
│  │                                              │       │
│  │ search_content: "Vector search, keyword    │       │
│  │                  search on .ai/ content"       │       │
│  │                                              │       │
│  │ registry: "Supabase auth, sync,          │       │
│  │           publish (not TypeHandlerRegistry)" │       │
│  └──────────────────────────────────────────────────┘       │
│                                                           │
│  Domain Knowledge (Defines Content Shapes):            │
│  ├── "Directives look like <directive>...</directive>"    │
│  ├── "Tools have metadata header in comments"            │
│  ├── "Knowledge has frontmatter YAML"                   │
│  └── "Signatures use kiwi-mcp:validated: format"      │
└────────────────────────────────────────────────────────────┘
```

---

## Protected vs Shadowable Content

### Protected Content (Cannot Override)

RYE provides **protected** core infrastructure that users cannot override:

| Protected Path                | Purpose                                                  |
| --------------------------- | -------------------------------------------------------- |
| `.ai/tools/core/`            | Core system tools (system, registry, rag, telemetry, protection) |
| `.ai/tools/threads/`        | Threading infrastructure                                      |
| `.ai/tools/extractors/`      | Metadata extractors                                        |
| `.ai/tools/capabilities/`      | Capability management                                        |
| `.ai/knowledge/lilux/`      | Kernel documentation (primitives, handlers, architecture)         |

These are **always** used from bundled RYE content, even if user creates same paths.

### Shadowable Content (Can Override)

Users can **override** by creating same paths in userspace or project:

| Shadowable Path          | Purpose                                      |
| ---------------------- | -------------------------------------------- |
| `.ai/directives/core/`   | Core directives (init, bootstrap, sync, run) |
| `.ai/directives/meta/`   | Meta directives (orchestration)              |

If user creates `~/.ai/directives/core/init.md`, it **shadows** bundled one.

---

## Content Loading: How Lilux Finds RYE Content

### Content Search Order

When Lilux needs to find directives/tools/knowledge, it searches in this order:

```
1. Project .ai/ (if project_path provided)
   /path/to/project/.ai/directives/
   /path/to/project/.ai/tools/
   /path/to/project/.ai/knowledge/

2. Userspace (default: ~/.ai/)
   ~/.ai/directives/
   ~/.ai/tools/
   ~/.ai/knowledge/

3. Bundled RYE content (from rye package)
   site-packages/rye/.ai/directives/
   site-packages/rye/.ai/tools/
   site-packages/rye/.ai/knowledge/
```

### Code Implementation

**In `lilux/config.py` or `lilux/utils/resolvers.py`:**

```python
from pathlib import Path
import sys

def get_content_root() -> Path | None:
    """Get path to bundled .ai/ content from rye package"""
    try:
        import rye
        rye_path = Path(rye.__file__).parent
        ai_path = rye_path / ".ai"
        if ai_path.exists():
            return ai_path
    except ImportError:
        pass
    return None

BUNDLED_CONTENT = get_content_root()

def get_content_dirs(project_path: Path | None = None) -> list[Path]:
    """Get all content directories in priority order"""
    dirs = []

    # 1. Project .ai/
    if project_path:
        project_ai = project_path / ".ai"
        if project_ai.exists():
            dirs.append(project_ai)

    # 2. Userspace
    userspace = Path.home() / ".ai"
    if userspace.exists():
        dirs.append(userspace)

    # 3. Bundled RYE content
    if BUNDLED_CONTENT:
        dirs.append(BUNDLED_CONTENT)

    return dirs
```

---

## User Spaces

### Userspace Location

Configurable via `USER_SPACE` environment variable. Default: `~/.ai/`

```
$USER_SPACE/              # Default: ~/.ai/
├── directives/          # User's custom directives
├── tools/               # User's custom tools
├── knowledge/           # User's knowledge entries
├── keys/
│   └── trusted/*.pub    # Trusted author public keys
├── cache/
│   └── vectors/         # Pre-computed embeddings
├── config.yaml          # User settings (telemetry, etc.)
├── telemetry.yaml       # Execution stats
├── .env                # CI secrets (fallback)
└── AGENTS.md           # Command dispatch table
```

### Secrets Storage

**Primary: System Keyring** (via Python `keyring` library)

| Secret              | Keyring Service | Keyring Key     |
| ------------------- | --------------- | ---------------- |
| Registry token      | `rye`           | `registry-token`  |
| Private signing key | `rye`           | `signing-key`     |

Works with:
- macOS Keychain
- Windows Credential Manager
- Linux Secret Service (GNOME Keyring, KWallet)

**Fallback: .env file** (for CI/headless)

```bash
# ~/.ai/.env (or project .ai/.env)
REGISTRY_TOKEN=sb-xxx...
SIGNING_KEY=base64-encoded-pem...
# or
SIGNING_KEY_FILE=/path/to/private.pem
```

---

## MCP Configuration

### Example: Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "rye": {
      "command": "/home/leo/projects/kiwi-mcp/rye-lilux/.venv/bin/python",
      "args": ["-m", "lilux.server"],
      "environment": {
        "USER_SPACE": "/home/leo/.ai",
        "EMBEDDING_URL": "https://openrouter.ai/api/v1/embeddings",
        "EMBEDDING_API_KEY": "sk-or-...",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "EMBEDDING_AUTH_HEADER": "Authorization",
        "EMBEDDING_AUTH_FORMAT": "Bearer {key}",
        "VECTOR_DB_URL": "postgresql://postgres...:5432/postgres"
      },
      "enabled": true
    }
  }
}
```

**Key points:**
- Command points to **kernel** entry point: `python -m lilux.server`
- Environment variables configure RAG infrastructure
- Kernel automatically loads RYE content from installed `rye` package

---

## What Belongs Where: The Decision Matrix

### In **Lilux Kernel** (`lilux/` package) ✅

| Module                     | Purpose                                  | Why?                        |
| ------------------------ | ---------------------------------------- | ---------------------------- |
| `handlers/registry.py`    | **TypeHandlerRegistry** (routes types)     | Kernel routing              |
| `handlers/directive/handler.py` | Generic router (doesn't parse XML)   | Kernel routing              |
| `handlers/tool/handler.py`      | Generic router (doesn't parse metadata) | Kernel routing              |
| `handlers/knowledge/handler.py` | Generic router (doesn't parse frontmatter) | Kernel routing   |
| `primitives/subprocess.py`      | Dumb execution (shell commands)    | Kernel primitive            |
| `primitives/http_client.py`     | Dumb execution (HTTP requests)    | Kernel primitive            |
| `utils/resolvers.py`           | Path resolution (find files)         | Kernel needs for routing    |
| `utils/parsers.py`             | Basic XML/YAML parsing (enough for routing) | Kernel needs for routing |
| `utils/validators.py`          | Basic validation (enough for routing)  | Kernel needs for routing    |
| `utils/schema_validator.py`     | Basic schema validation                 | Kernel needs for routing    |
| `utils/logger.py`             | Logging setup                             | Kernel infrastructure       |
| `utils/env_loader.py`          | Environment loading                         | Kernel infrastructure       |
| `utils/output_manager.py`      | Output formatting                         | Kernel infrastructure       |
| `utils/paths.py`             | Path utilities                            | Kernel infrastructure       |
| `utils/extensions.py`          | Extension discovery                       | Kernel infrastructure       |

### In **RYE Content** (`rye/.ai/` package) ✅

| Module                          | Purpose                                    | Why?                             |
| ------------------------------- | ------------------------------------------ | --------------------------------- |
| `.ai/tools/core/system.py`    | Understands directives (parses XML)        | RYE intelligence                  |
| `.ai/tools/core/execute_directive.py` | Executes directives using primitives   | RYE intelligence                  |
| `.ai/tools/core/execute_tool.py`      | Executes tools using primitives         | RYE intelligence                  |
| `.ai/tools/core/sign_item.py`         | Signs items using primitives            | RYE intelligence                  |
| `.ai/tools/core/registry.py`        | **Registry Tool** (Supabase auth, sync)  | RYE intelligence (not TypeHandlerRegistry) |
| `.ai/tools/core/rag.py`           | Vector search on .ai/ content          | RYE intelligence                  |
| `.ai/tools/core/telemetry.py`     | Telemetry collection                   | RYE intelligence                  |
| `.ai/tools/threads/`              | Threading infrastructure                | RYE intelligence                  |
| `.ai/tools/extractors/`          | Metadata extractors                   | RYE intelligence                  |
| `.ai/tools/capabilities/`        | Capability management                  | RYE intelligence                  |
| `.ai/directives/core/init.md`     | Project initialization                | RYE intelligence                  |
| `.ai/directives/core/bootstrap.md` | Project bootstrap                     | RYE intelligence                  |
| `.ai/knowledge/lilux/`            | Kernel documentation (PROTECTED)        | RYE intelligence                  |

**Defines content shapes:**
- ✅ What directives look like (XML structure)
- ✅ What tools look like (metadata headers)
- ✅ What knowledge looks like (frontmatter YAML)
- ✅ How signatures work (format, validation)
- ✅ Domain workflows (init, bootstrap, sync)

### ❌ DON'T Put in Kernel (`lilux/`)

| Wrongly Placed        | Should Be In          | Why?                          |
| -------------------- | --------------------- | ------------------------------- |
| `.ai/directives/`     | `rye/.ai/directives/` | Content, not kernel           |
| `.ai/tools/core/`     | `rye/.ai/tools/core/` | Content, not kernel           |
| `metadata_manager.py`  | `rye/.ai/tools/`      | RYE-level intelligence       |
| `env_manager.py`       | `rye/.ai/tools/`      | RYE-level intelligence       |
| `file_search.py`       | `rye/.ai/tools/`      | RYE-level intelligence       |
| `xml_error_helper.py`  | `rye/.ai/tools/`      | RYE-level intelligence       |
| `signature_formats.py`  | `rye/.ai/tools/`      | RYE-level intelligence       |

These are **content intelligence**, not kernel infrastructure.

---

## Summary: The Consistent Mental Model

**Yes! This is consistent:**

```
LILUX = Operating System Kernel
├── Doesn't know about applications
├── Provides primitives (CPU, memory, I/O)
├── Provides routing (process scheduler)
├── DUMB - just executes
└── Applications plug in and use primitives

RYE = Applications / Utilities
├── Understands application formats (directives, tools, knowledge)
├── Uses kernel primitives to do work
├── Provides domain logic (how to execute directives, how to manage tools)
├── SMART - understands content shapes
└── Plug into kernel via MCP tools
```

**Analogy:**

| Component        | Lilux | RYE |
| -------------- | ------- | ----- |
| Analogy        | OS Kernel | Applications |
| Provides       | Hardware primitives (CPU, memory, I/O) | Application logic (document editors, browsers, games) |
| Knowledge      | Dumb - just runs instructions | Smart - understands formats, workflows |
| Extensibility  | New primitives can be added | New applications/tools can be created |

**Bottom line:**

- User installs: `pip install rye-lilux` → gets both kernel + intelligent content
- Lilux = Engine (generic execution)
- RYE = Software (intelligent applications)
- They work together: RYE defines what to do, Lilux provides how to do it

---

## Next Steps

### 1. Fix Kernel to be Dumb

Remove content intelligence from kernel:

- Kernel handlers: Remove `metadata_manager`, signature validation
- Keep only: Path resolution, basic parsing, routing

### 2. Move Intelligence to RYE

Create RYE tools that:
- Parse directive XML
- Validate signatures
- Define content shapes
- Use kernel primitives to execute

### 3. Install and Test

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux
pip install -e .
python -m lilux.server
```

### 4. Configure LLM Client

Add the MCP config from "MCP Configuration" section above.

---

**Document Status: Final & Production-Ready**
**Last Updated: 2026-01-30**
**Author: Kiwi MCP Team**
