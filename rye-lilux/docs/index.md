# RYE-Lilux Documentation

## Overview

**RYE** is an AI operating system layer built on top of the **Lilux** microkernel. Together they provide a data-driven, universal tool execution platform for LLMs.

| Component | Role | Analogy |
|-----------|------|---------|
| **Lilux** | Microkernel with execution primitives | Hardware kernel |
| **RYE** | Universal executor + content bundle | Operating system |

## Architecture

```
LLM/User
    │
    └─→ RYE (5 MCP Tools)
        │
        │  Works with 3 item types:
        │  ├─→ directives (.ai/directives/)
        │  ├─→ tools (.ai/tools/)
        │  └─→ knowledge (.ai/knowledge/)
        │
        ├─→ search  - Find items by query
        ├─→ load    - Get content / copy between locations
        ├─→ execute - Run item (dispatches to handlers)
        ├─→ sign    - Validate and sign
        └─→ help    - Get help
            │
            │  Tool execution only:
            └─→ PrimitiveExecutor → Lilux Primitives
                ├─→ subprocess (shell commands)
                └─→ http_client (HTTP requests)
```

## Quick Links

### Core Concepts

- [Architecture Overview](ARCHITECTURE.md) - Full system architecture
- [Three-Layer Model](COMPLETE_DATA_DRIVEN_ARCHITECTURE.md) - Primitives → Runtimes → Tools

### RYE OS Layer

- [MCP Server](rye/mcp-server.md) - MCP server configuration
- [Universal Executor](rye/universal-executor/overview.md) - Tool routing and execution

### MCP Tools (work with directive, tool, knowledge)

- [Search](rye/mcp-tools/search.md) - Find items by query
- [Load](rye/mcp-tools/load.md) - Load content / copy between locations
- [Execute](rye/mcp-tools/execute.md) - Run items (directives, tools, knowledge)
- [Sign](rye/mcp-tools/sign.md) - Validate and sign items
- [Help](rye/mcp-tools/help.md) - Get usage help

### Tool Categories

- [Categories Overview](rye/categories/overview.md) - All tool categories
- [Primitives](rye/categories/primitives.md) - Base executors (Layer 1)
- [Runtimes](rye/categories/runtimes.md) - Language runtimes (Layer 2)

### Schema-Driven Extraction

- [Extractors](rye/categories/extractors.md) - Schema-driven metadata extraction
- [Parsers](rye/categories/parsers.md) - Content preprocessors

### Bundle Structure

- [Content Bundle](rye/bundle/structure.md) - `.ai/` directory organization

## Installation

```bash
pip install rye-lilux  # Installs both RYE + Lilux
```

## MCP Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "rye": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "rye.server"],
      "environment": {
        "USER_SPACE": "/home/user/.ai"
      }
    }
  }
}
```

## Usage Flow

1. **Search** for tools matching your needs
2. **Load** the tool schema to understand parameters
3. **Execute** the tool with appropriate parameters
4. **Sign** content when publishing to registry

## Project Status

**Architecture Complete - Implementation In Progress**

See the [implementation plan](ARCHITECTURE.md#implementation-status-summary) for current status.
