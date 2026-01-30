**Source:** Original implementation: `rye/` and `lilux/` package structure in kiwi-mcp

# RYE Package Structure

## Overview

RYE is an operating system layer built on top of the Lilux microkernel. The package combines both components:

```
rye-lilux/
├── rye/                      # RYE OS Layer (main package)
│   ├── __init__.py
│   ├── server.py             # MCP server entry point
│   ├── executor.py           # Universal executor
│   ├── discovery.py          # Tool auto-discovery
│   ├── .ai/                  # Content bundle
│   │   ├── tools/
│   │   ├── directives/
│   │   └── knowledge/
│   └── pyproject.toml
│
├── lilux/                    # Lilux Microkernel (dependency)
│   ├── __init__.py
│   ├── primitives/           # Execution primitives
│   │   ├── subprocess.py
│   │   ├── http_client.py
│   │   ├── auth.py
│   │   ├── lockfile.py
│   │   └── chain_validator.py
│   ├── runtimes/             # Language runtimes
│   │   ├── python_runtime.py
│   │   ├── node_runtime.py
│   │   └── mcp_http_runtime.py
│   ├── handlers/             # Content handlers
│   │   ├── xml_handler.py
│   │   ├── frontmatter_handler.py
│   │   └── metadata_handler.py
│   ├── registry/             # Tool registry
│   │   └── registry.py
│   └── pyproject.toml
│
└── docs/                     # Documentation
    ├── rye/                  # RYE documentation
    ├── lilux/                # Lilux documentation
    └── ARCHITECTURE.md
```

## Package Dependencies

### Lilux (Microkernel)

```toml
# lilux/pyproject.toml
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

**Role:** Provides dumb execution primitives (subprocess, HTTP, auth, etc.)

### RYE (OS Layer)

```toml
# rye/pyproject.toml
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

**Role:** Provides intelligent universal executor + content understanding + tool discovery

## Key Directory Purposes

### RYE Core (`rye/`)

| File | Purpose |
|------|---------|
| `server.py` | MCP server entry point (`python -m rye.server`) |
| `executor.py` | Universal executor routing logic |
| `discovery.py` | Auto-discover tools from `.ai/tools/` |
| `__init__.py` | Package initialization |

### Lilux Primitives (`lilux/primitives/`)

Base execution implementations that don't delegate anywhere:

| File | Purpose | `__executor_id__` |
|------|---------|-------------------|
| `subprocess.py` | Shell command execution | `None` |
| `http_client.py` | HTTP requests with retry | `None` |
| `auth.py` | Keychain/credential access | `None` |
| `lockfile.py` | Lockfile data structures | `None` |
| `chain_validator.py` | Chain validation logic | `None` |

### Lilux Runtimes (`lilux/runtimes/`)

Language-specific executors that delegate to primitives:

| File | Purpose | Delegates To |
|------|---------|--------------|
| `python_runtime.py` | Python script execution | `subprocess` |
| `node_runtime.py` | Node.js script execution | `subprocess` |
| `mcp_http_runtime.py` | MCP HTTP client | `http_client` |

### Content Bundle (`rye/.ai/`)

Organized tool definitions, directives, and knowledge:

```
.ai/
├── tools/
│   ├── rye/              # RYE bundled tools
│   │   ├── primitives/   # Execution primitives (2 files)
│   │   ├── runtimes/     # Runtime schemas (3 files)
│   │   ├── capabilities/ # System capabilities (6 files)
│   │   ├── telemetry/    # Telemetry tools (7 files)
│   │   ├── extractors/   # Data extractors (3 dirs)
│   │   ├── protocol/     # Protocol tools (1 file)
│   │   ├── sinks/        # Event sinks (3 files)
│   │   ├── threads/      # Async execution (12 files + yaml)
│   │   ├── mcp/          # MCP tools (yaml files)
│   │   ├── llm/          # LLM configs (yaml files)
│   │   ├── registry/     # Registry operations (1 file)
│   │   ├── parsers/      # Data parsers (4 files)
│   │   ├── utility/      # Utilities (3 files)
│   │   ├── examples/     # Examples (2 files)
│   │   └── python/       # Python libraries (shared)
│   │       └── lib/
│   │
│   └── {other}/          # User/custom tools (any category)
│
├── directives/           # Workflow definitions (XML)
│   ├── *.xml
│   └── ...
│
└── knowledge/            # Knowledge entries (Markdown)
    ├── *.md
    └── ...
```

## Installation and Usage

### User Installation

```bash
# Users install RYE (gets both packages)
pip install rye-lilux

# RYE server starts automatically with LLM clients
# Claude Desktop / Cursor config:
{
  "mcpServers": {
    "rye": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "rye.server"],
      "environment": {"USER_SPACE": "/home/user/.ai"},
      "enabled": true
    }
  }
}
```

### Developer Installation

```bash
# Install both packages for development
pip install -e lilux/
pip install -e rye/
```

## Relationship to Lilux

**Lilux provides the dumb primitives, RYE provides the smart OS layer:**

- **Lilux** (`lilux/primitives/`, `lilux/runtimes/`) - Base execution implementations
- **RYE** (`rye/executor.py`, `rye/discovery.py`) - Universal executor + tool discovery
- **RYE `.ai/`** - All tool definitions (data, not code)

**Flow:**
1. User/LLM calls RYE
2. RYE auto-discovers tools from `.ai/tools/`
3. RYE universal executor loads tool metadata
4. RYE routes to appropriate Lilux primitive based on `__executor_id__`
5. Lilux primitive executes and returns result

## Related Documentation

- [[principles]] - Core RYE principles
- [[universal-executor/overview]] - Universal executor architecture
- [[bundle/structure]] - Content bundle detailed structure
- [[lilux/primitives/overview]] - Lilux primitive implementations
