# Lilux/RYE Architecture: Refined & Clarified

**Date:** 2026-01-30
**Status:** Production-Ready Architecture
**Purpose:** Clear separation between Lilux (kernel) and RYE (content), with migration path for MCP server

---

## Executive Summary

**Lilux is dumb. RYE is smart.**

- **Lilux** = Kernel/Infrastructure (5 MCP tools, primitives, handlers, storage)
- **RYE** = Content/Intelligence (directives, tools, knowledge in `.ai/`)

They are **separate packages** but developed in a **monorepo** for simplicity.

---

## Critical Clarifications

### 1. MCP Server - NOT CLI

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

And communicates over **stdio** with the LLM client (Claude Desktop, Cursor, etc.).

### 2. Repository Structure: Monorepo

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
│   ├── primitives/                 # Low-level execution
│   │   ├── __init__.py
│   │   ├── executor.py             # ChainResolver, PrimitiveExecutor
│   │   ├── subprocess.py           # SubprocessPrimitive
│   │   ├── http_client.py          # HttpClientPrimitive
│   │   ├── chain_validator.py      # ChainValidator
│   │   ├── integrity_verifier.py   # IntegrityVerifier
│   │   ├── lockfile.py            # Lockfile management
│   │   └── errors.py             # Execution errors
│   │
│   ├── runtime/                    # Runtime services
│   │   ├── __init__.py
│   │   ├── auth.py                # AuthStore (OS keychain)
│   │   ├── env_resolver.py          # Environment variable resolution
│   │   └── lockfile_store.py      # Lockfile persistence
│   │
│   ├── handlers/                   # Type-specific handlers
│   │   ├── __init__.py
│   │   ├── registry.py            # TypeHandlerRegistry
│   │   ├── directive/             # DirectiveHandler
│   │   │   ├── __init__.py
│   │   │   └── handler.py
│   │   ├── tool/                 # ToolHandler
│   │   │   ├── __init__.py
│   │   │   └── handler.py
│   │   └── knowledge/            # KnowledgeHandler
│   │       ├── __init__.py
│   │       └── handler.py
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
│   └── utils/                      # KERNEL utilities only!
│       ├── __init__.py
│       ├── resolvers.py            # ToolResolver, PathResolver
│       ├── parsers.py             # XML, YAML, frontmatter parsing
│       ├── validators.py          # ValidationManager
│       ├── schema_validator.py     # Schema validation
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
│       ├── tools/                    # Core tools (PROTECTED)
│       │   ├── core/               # PROTECTED - cannot override
│       │   │   ├── system.py      # Environment vars, paths, RAG
│       │   │   ├── registry.py    # Auth, sync, publish, keys
│       │   │   ├── rag.py         # Vector search, embeddings
│       │   │   └── telemetry.py   # Telemetry collection
│       │   │
│       │   ├── llm/                # LLM provider configs
│       │   │   ├── openai.py
│       │   │   ├── anthropic.py
│       │   │   └── ...
│       │   │
│       │   ├── threads/            # Threading infrastructure
│       │   │   ├── create.py
│       │   │   ├── list.py
│       │   │   └── ...
│       │   │
│       │   ├── extractors/         # Metadata extractors
│       │   │   └── ...
│       │   │
│       │   └── capabilities/       # Capability management
│       │       └── ...
│       │
│       └── knowledge/              # Core knowledge
│           ├── kernel/             # PROTECTED - cannot override
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
│   ├── kernel/                      # Lilux kernel tests
│   └── content/                     # RYE content tests
│
├── pyproject.toml                  # Monorepo root config
├── .github/
│   └── workflows/
│       ├── kernel-ci.yml
│       └── content-ci.yml
└── README.md
```

**Key characteristic:**

- **Lilux** = Infrastructure (dumb)
- **RYE** = Intelligence (smart)
- **RYE tools** extend Lilux kernel functionality

---

## Package Separation

### Package 1: `lilux` (Kernel)

**Contains ONLY:**

| Component                | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `server.py`              | MCP server with 5 tools                                |
| `tools/`                 | Search, Load, Execute, Sign, Help (MCP interface)      |
| `primitives/`            | Subprocess, HTTP, ChainResolver, Integrity             |
| `handlers/`              | Directive/Tool/Knowledge type handlers                 |
| `runtime/`               | AuthStore, env_resolver, lockfile_store                |
| `storage/vector/`        | Vector store infrastructure                            |
| `schemas/tool_schema.py` | Tool metadata extraction                               |
| `utils/*`                | ONLY kernel utilities (parsers, validators, resolvers) |

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
description = "Lilux MCP Kernel - 5 primitive tools for AI agent orchestration"

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

### Package 2: `rye-lilux` (Content Bundle)

**Contains ONLY:**

| Component                 | Purpose                          |
| ------------------------- | -------------------------------- |
| `.ai/directives/core/`    | Core directives (shadowable)     |
| `.ai/tools/core/`         | Core system tools (PROTECTED)    |
| `.ai/tools/llm/`          | LLM provider configurations      |
| `.ai/tools/threads/`      | Threading infrastructure         |
| `.ai/tools/extractors/`   | Metadata extractors              |
| `.ai/tools/capabilities/` | Capability management            |
| `.ai/knowledge/kernel/`   | Kernel documentation (PROTECTED) |
| `.ai/knowledge/concepts/` | Domain concepts                  |

**Install:**

```bash
pip install rye-lilux  # Gets both rye + lilux dependency
```

**PyPI Package:**

```toml
[project]
name = "rye-lilux"
version = "0.1.0"
description = "RYE content layer for Lilux MCP"

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
                     ├─> lilux>=0.1.0 (kernel)
                     │    ├── server.py
                     │    ├── tools/ (5 MCP tools)
                     │    ├── primitives/
                     │    ├── handlers/
                     │    └── utils/ (kernel-only)
                     │
                     └─> rye-lilux (content)
                          ├── .ai/directives/
                          └── .ai/tools/
```

**Result:** User gets full system (kernel + content) in one install.

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

| Secret              | Keyring Service | Keyring Key      |
| ------------------- | --------------- | ---------------- |
| Registry token      | `rye`           | `registry-token` |
| Private signing key | `rye`           | `signing-key`    |

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

## Protected vs Shadowable Content

### Protected Content (Cannot Override)

RYE provides **protected** core tools that users cannot override:

| Protected Path          | Purpose                                                   |
| ----------------------- | --------------------------------------------------------- |
| `.ai/tools/core/`       | Core system tools (system, registry, rag, telemetry)      |
| `.ai/knowledge/kernel/` | Kernel documentation (primitives, handlers, architecture) |

These are **always** used from bundled RYE content, even if user creates same paths.

### Shadowable Content (Can Override)

Users can **override** by creating same paths in userspace or project:

| Shadowable Path        | Purpose                                      |
| ---------------------- | -------------------------------------------- |
| `.ai/directives/core/` | Core directives (init, bootstrap, sync, run) |
| `.ai/directives/meta/` | Meta directives (orchestration)              |

If user creates `~/.ai/directives/core/init.md`, it **shadows** the bundled one.

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

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                USER'S LLM CLIENT                         │
│         (Claude Desktop, Cursor, etc.)                  │
├──────────────────────────────────────────────────────────────┤
│                                                          │
│  User: "init my workspace"                               │
│  LLM: [calls mcp__lilux__execute(...)]                  │
└──────────────────────────────────────────────────────────────┘
                          │ MCP (stdio)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  LILUX MCP SERVER                         │
│                                                          │
│  Kernel (lilux package):                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 5 Primitive Tools:                               │     │
│  │   search │ load │ execute │ sign │ help           │     │
│  │                                                    │     │
│  │ Handlers: directive │ tool │ knowledge               │     │
│  │                                                    │     │
│  │ Primitives: subprocess │ http_client │ chains        │     │
│  │                                                    │     │
│  │ Storage: vector store infrastructure                  │     │
│  │ Runtime: auth, env_resolver, lockfile_store          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                           │
│  RYE Content (rye package):                                │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ .ai/tools/core/system.py  ← paths, env vars, RAG   │     │
│  │ .ai/tools/core/registry.py ← auth, sync, publish    │     │
│  │ .ai/tools/core/rag.py  ← vector search              │     │
│  │ .ai/tools/core/telemetry.py  ← telemetry collection   │     │
│  │ .ai/tools/llm/*  ← LLM provider configs           │     │
│  │ .ai/tools/threads/*  ← threading infrastructure        │     │
│  │ .ai/knowledge/kernel/*  ← kernel docs (PROTECTED)  │     │
│  │ .ai/directives/core/*  ← init, bootstrap (shadowable)│     │
│  └────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                    USER SPACES                             │
│                                                          │
│  Userspace (~/.ai/):                                     │
│  ├── directives/          ← user's custom directives         │
│  ├── tools/               ← user's custom tools            │
│  ├── knowledge/           ← user's knowledge entries        │
│  ├── keys/trusted/*.pub   ← trusted public keys           │
│  ├── cache/vectors/       ← embeddings cache               │
│  ├── config.yaml          ← user settings                  │
│  └── AGENTS.md           ← command dispatch table         │
│                                                           │
│  System Keyring:                                          │
│  └── rye/registry-token, rye/signing-key                   │
└──────────────────────────────────────────────────────────────┘
```

---

## What Belongs Where

### In Kernel (`lilux/` package) ✅

| Module                          | Purpose           | Why?                             |
| ------------------------------- | ----------------- | -------------------------------- |
| `server.py`                     | MCP server entry  | Kernel infrastructure            |
| `tools/search.py`               | Search MCP tool   | Kernel interface                 |
| `tools/load.py`                 | Load MCP tool     | Kernel interface                 |
| `tools/execute.py`              | Execute MCP tool  | Kernel interface                 |
| `tools/sign.py`                 | Sign MCP tool     | Kernel interface                 |
| `tools/help.py`                 | Help MCP tool     | Kernel interface                 |
| `primitives/executor.py`        | Chain execution   | Kernel infrastructure            |
| `primitives/subprocess.py`      | Shell execution   | Kernel infrastructure            |
| `primitives/http_client.py`     | HTTP requests     | Kernel infrastructure            |
| `handlers/directive/handler.py` | Directive parsing | Kernel infrastructure            |
| `handlers/tool/handler.py`      | Tool execution    | Kernel infrastructure            |
| `handlers/knowledge/handler.py` | Knowledge parsing | Kernel infrastructure            |
| `utils/parsers.py`              | XML/YAML parsing  | Kernel needs for handlers        |
| `utils/validators.py`           | Validation logic  | Kernel needs for signing         |
| `utils/resolvers.py`            | Path resolution   | Kernel needs for content finding |
| `utils/logger.py`               | Logging setup     | Kernel infrastructure            |

### In Content (`rye/.ai/` package) ✅

| Module                             | Purpose                | Why?                         |
| ---------------------------------- | ---------------------- | ---------------------------- |
| `.ai/tools/core/system.py`         | System utilities       | Extends kernel functionality |
| `.ai/tools/core/registry.py`       | Registry operations    | RYE-specific content         |
| `.ai/tools/core/rag.py`            | Vector search          | RYE-specific intelligence    |
| `.ai/tools/core/telemetry.py`      | Telemetry collection   | RYE-specific content         |
| `.ai/tools/llm/*.py`               | LLM configs            | RYE-specific content         |
| `.ai/tools/threads/*.py`           | Threading              | RYE-specific content         |
| `.ai/directives/core/init.md`      | Project initialization | RYE-specific workflow        |
| `.ai/directives/core/bootstrap.md` | Project bootstrap      | RYE-specific workflow        |
| `.ai/directives/core/sync_*.md`    | Sync workflows         | RYE-specific workflow        |
| `.ai/knowledge/kernel/*.md`        | Kernel documentation   | RYE-specific knowledge       |

### ❌ DON'T Put in Kernel (`lilux/`)

| Wrongly Placed        | Should Be In          | Why?                |
| --------------------- | --------------------- | ------------------- |
| `.ai/directives/`     | `rye/.ai/directives/` | Content, not kernel |
| `.ai/tools/core/`     | `rye/.ai/tools/core/` | Content, not kernel |
| `metadata_manager.py` | `rye/.ai/tools/`      | RYE-level utility   |
| `env_manager.py`      | `rye/.ai/tools/`      | RYE-level utility   |
| `file_search.py`      | `rye/.ai/tools/`      | RYE-level utility   |

---

## Migration Path to Working MCP Server

### Current Issue

**The kernel (`lilux/`) is missing `metadata_manager.py` which handlers need.**

But `metadata_manager.py` is **NOT** a kernel utility - it's a RYE-level tool that handles:

- Directive/tool/knowledge parsing with signatures
- Signature validation
- Hash computation

### Solution: Remove Signature Dependencies from Kernel

**Option 1: Kernel is TRULY dumb (preferred)**

Kernel handlers should **not** validate signatures. They just parse and execute content.

```python
# lilux/handlers/directive/handler.py (simplified)

class DirectiveHandler:
    def parse_file(self, file_path: Path) -> dict:
        """Parse directive file - no signature validation"""
        content = file_path.read_text()

        # Extract XML (simple parsing, no signature)
        if content.strip().startswith('<directive'):
            # Parse XML content
            pass

        # Return parsed data
        return {
            "item_type": "directive",
            "item_id": "...",
            "metadata": {...},
            "content": "...",
        }
```

**Signature validation becomes a RYE tool:**

```python
# rye/.ai/tools/core/registry.py

ACTIONS = {
    "sign": "Sign a file with cryptographic signature",
    "verify": "Verify a file's signature",
}

def execute(action, file_path):
    """Handle signature operations"""
    if action == "sign":
        # Use metadata_manager logic (moved to RYE)
        sign_content(file_path)

    elif action == "verify":
        verify_signature(file_path)
```

**Option 2: Move minimal signature utilities to kernel (if needed)**

If kernel MUST validate signatures, move only what's needed:

```python
# lilux/utils/integrity.py (NEW - minimal)

def extract_signature(content: str) -> dict | None:
    """Extract signature from content footer"""
    # Minimal logic to find <!-- kiwi-mcp:validated:... --> block
    pass

def verify_integrity(content: str) -> bool:
    """Verify content has signature"""
    # Minimal check for signature presence
    return extract_signature(content) is not None
```

**Full metadata_manager stays in RYE.**

### Recommended Path

**Option 1 (truly dumb kernel) is better:**

1. Remove `metadata_manager` imports from kernel handlers
2. Handlers just parse XML/YAML and return content
3. Signature validation becomes a **RYE tool** that users run explicitly
4. Simplifies kernel significantly
5. RYE becomes responsible for content trust management

---

## MCP Server Entry Point

### What Currently Exists (`lilux/server.py`)

```python
#!/usr/bin/env python3
"""Lilux MCP Kernel - 5 primitive tools for AI agent orchestration."""

import argparse
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from lilux.tools.search import SearchTool
from lilux.tools.load import LoadTool
from lilux.tools.execute import ExecuteTool
from lilux.tools.sign import SignTool
from lilux.tools.help import HelpTool

__version__ = "0.1.0"
__package_name__ = "lilux"

class LiluxMCP:
    """Lilux MCP Kernel with 5 primitive tools."""

    def __init__(self):
        # Validate RAG config (MANDATORY)
        self.rag_config = validate_rag_config()
        self.server = Server(__package_name__)

        # Initialize 5 primitive tools
        self.tools = {
            "search": SearchTool(),
            "load": LoadTool(),
            "execute": ExecuteTool(),
            "sign": SignTool(),
            "help": HelpTool(),
        }
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [tool.schema for tool in self.tools.values()]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name not in self.tools:
                raise ValueError(f"Unknown tool: {name}")
            result = await self.tools[name].execute(arguments)
            return [TextContent(type="text", text=result)]

    async def start(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)

def main():
    parser = argparse.ArgumentParser(description="Lilux MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (default)")
    args = parser.parse_args()
    asyncio.run(run_stdio())

if __name__ == "__main__":
    main()
```

### Entry Point Configuration

**In `lilux/pyproject.toml`:**

```toml
[project.scripts]
lilux = "lilux.server:main"
```

**Usage:**

```bash
# From venv
.venv/bin/python -m lilux.server

# Or via entry point
lilux --stdio
```

---

## Next Steps to Get MCP Running

### Step 1: Fix Kernel Dependencies

Remove `metadata_manager` imports from kernel:

```bash
# Files to update:
lilux/handlers/directive/handler.py
lilux/handlers/tool/handler.py
lilux/handlers/knowledge/handler.py
lilux/primitives/integrity_verifier.py
lilux/primitives/executor.py

# Remove imports like:
from lilux.utils.metadata_manager import MetadataManager

# Replace with simple parsing (no signature validation)
```

### Step 2: Install Dependencies

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux

# Install kernel
pip install -e ./lilux

# Install content
pip install -e ./rye

# Or install whole monorepo
pip install -e .
```

### Step 3: Test MCP Server

```bash
# Set environment variables
export USER_SPACE=/home/leo/.ai
export EMBEDDING_URL=https://openrouter.ai/api/v1/embeddings
export EMBEDDING_API_KEY=sk-or-...
export EMBEDDING_MODEL=text-embedding-3-small
export VECTOR_DB_URL=postgresql://postgres...:5432/postgres

# Start server
python -m lilux.server
```

### Step 4: Configure LLM Client

Add to Claude Desktop/Cursor config:

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
        "VECTOR_DB_URL": "postgresql://postgres...:5432/postgres"
      }
    }
  }
}
```

---

## Summary

| Aspect             | Lilux (Kernel)           | RYE (Content)                                 |
| ------------------ | ------------------------ | --------------------------------------------- |
| **What**           | Execution infrastructure | Directives, tools, knowledge                  |
| **Repository**     | Monorepo: `lilux/`       | Monorepo: `rye/`                              |
| **PyPI Package**   | `lilux`                  | `rye-lilux`                                   |
| **Dependency**     | None                     | Depends on `lilux>=0.1.0`                     |
| **Entry Point**    | `python -m lilux.server` | Uses kernel entry point                       |
| **Content**        | None                     | `.ai/` folder with directives/tools/knowledge |
| **Responsibility** | Dumb - just executes     | Smart - provides intelligence                 |
| **Interaction**    | MCP tools via LLM        | MCP tools via LLM                             |

**Bottom line:**

- Kernel = Engine (pipes, pistons, wiring)
- RYE = Fuel and steering (directs where to go)

User installs: `pip install rye-lilux` → gets both engine + fuel.

---

**Document Status: Refined & Production-Ready**
**Last Updated: 2026-01-30**
**Author: Kiwi MCP Team**
