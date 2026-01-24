thread id: T-019bac50-3127-719a-b66c-69fe1c70fdda

remember that ~/.ai is the userspace diretory which can be provided as an env var. default is ~/.ai/
remember that the project path cannot be determined by the mcp itself. the LLM calling the mcp must provide the path when it needs the mcp to do project based operations.
Userspace is fine as that is a provided env var.

# Kiwi MCP: Unified Implementation Document

**Date:** 2026-01-11  
**Author:** Leo + Agent  
**Status:** Implementation Ready  
**Source Projects:** context-kiwi, script-kiwi, knowledge-kiwi

---

## Executive Summary

This document provides everything needed to build the unified Kiwi MCP, consolidating three existing MCPs (Context Kiwi, Script Kiwi, Knowledge Kiwi) into **one MCP with 4 tools**:

| Tool      | Purpose                                    |
| --------- | ------------------------------------------ |
| `search`  | Find items across local/registry           |
| `load`    | Download from registry to local            |
| `execute` | Run, publish, delete, create, update, link |
| `help`    | Usage guidance & troubleshooting           |

**Impact:** 17 tools → 4 tools (76% reduction)

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Dependencies](#2-dependencies)
3. [Server Architecture](#3-server-architecture)
4. [Type Handler Registry Pattern](#4-type-handler-registry-pattern)
5. [Tool Specifications](#5-tool-specifications)
6. [API Layer](#6-api-layer)
7. [Storage & Resolution](#7-storage--resolution)
8. [Full Code Implementation](#8-full-code-implementation)
9. [Testing Strategy](#9-testing-strategy)
10. [Future: RAG & Auth](#10-future-rag--auth)
11. [Migration Guide](#11-migration-guide)

---

## 1. Project Structure

```
kiwi-mcp/
├── kiwi_mcp/                    # Main package
│   ├── __init__.py              # Package init with version
│   ├── server.py                # MCP server entry point
│   │
│   ├── tools/                   # 4 unified tools
│   │   ├── __init__.py
│   │   ├── base.py              # BaseTool class
│   │   ├── search.py            # SearchTool
│   │   ├── load.py              # LoadTool
│   │   ├── execute.py           # ExecuteTool
│   │   └── help.py              # HelpTool
│   │
│   ├── handlers/                # Type-specific handlers
│   │   ├── __init__.py
│   │   ├── registry.py          # TypeHandlerRegistry
│   │   │
│   │   ├── directive/           # Directive handlers
│   │   │   ├── __init__.py
│   │   │   ├── search.py
│   │   │   ├── load.py
│   │   │   ├── execute.py
│   │   │   └── loader.py        # DirectiveLoader (from context-kiwi)
│   │   │
│   │   ├── script/              # Script handlers
│   │   │   ├── __init__.py
│   │   │   ├── search.py
│   │   │   ├── load.py
│   │   │   ├── execute.py
│   │   │   └── resolver.py      # ScriptResolver (from script-kiwi)
│   │   │
│   │   └── knowledge/           # Knowledge handlers
│   │       ├── __init__.py
│   │       ├── search.py
│   │       ├── load.py
│   │       ├── execute.py
│   │       └── resolver.py      # KnowledgeResolver (from knowledge-kiwi)
│   │
│   ├── api/                     # Supabase registry clients
│   │   ├── __init__.py
│   │   ├── base.py              # BaseRegistry
│   │   ├── directive_registry.py
│   │   ├── script_registry.py
│   │   └── knowledge_registry.py
│   │
│   ├── config/                  # Configuration
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   └── utils/                   # Shared utilities
│       ├── __init__.py
│       ├── logger.py
│       ├── paths.py             # Path resolution
│       └── search.py            # Multi-term search utilities
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_tools.py
│   │   ├── test_handlers.py
│   │   └── test_api.py
│   └── integration/
│       ├── __init__.py
│       └── test_flows.py
│
├── pyproject.toml
├── pytest.ini
├── Makefile
├── README.md
├── .env.example
└── .gitignore
```

---

## 2. Dependencies

### pyproject.toml

```toml
[project]
name = "kiwi-mcp"
version = "0.1.0"
description = "Unified MCP for directives, scripts, and knowledge"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
keywords = ["mcp", "ai", "agents", "directives", "scripts", "knowledge"]

dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
    "supabase>=2.0.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "aiofiles>=23.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.1.0",
]

[project.scripts]
kiwi-mcp = "kiwi_mcp.server:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["kiwi_mcp*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py311"
```

---

## 3. Server Architecture

The server follows the pattern from the existing MCPs: a simple MCP server that registers 4 tools and dispatches calls to the appropriate handler based on the `type` parameter.

### kiwi_mcp/server.py

```python
#!/usr/bin/env python3
"""
Kiwi MCP Server

Unified MCP with 4 tools for directives, scripts, and knowledge.
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from kiwi_mcp.tools.search import SearchTool
from kiwi_mcp.tools.load import LoadTool
from kiwi_mcp.tools.execute import ExecuteTool
from kiwi_mcp.tools.help import HelpTool


class KiwiMCP:
    """Unified Kiwi MCP server with 4 tools."""

    def __init__(self):
        self.server = Server("kiwi-mcp")
        self.tools = {
            "search": SearchTool(),
            "load": LoadTool(),
            "execute": ExecuteTool(),
            "help": HelpTool(),
        }
        self._setup_handlers()

    def _setup_handlers(self):
        """Register MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return all 4 unified tools."""
            return [tool.schema for tool in self.tools.values()]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Dispatch to appropriate tool."""
            if name not in self.tools:
                return [TextContent(
                    type="text",
                    text=f'{{"error": "Unknown tool: {name}"}}'
                )]

            try:
                result = await self.tools[name].execute(arguments)
                return [TextContent(type="text", text=result)]
            except Exception as e:
                import traceback
                import json
                error = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                return [TextContent(type="text", text=json.dumps(error, indent=2))]

    async def run(self):
        """Start MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Entry point."""
    server = KiwiMCP()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
```

---

## 4. Type Handler Registry Pattern

The key architectural pattern is the TypeHandlerRegistry, which routes operations to type-specific handlers.

### kiwi_mcp/handlers/registry.py

```python
"""
Type Handler Registry

Routes operations (search, load, execute) to type-specific handlers.
"""

from typing import Any, Callable, Dict, Optional


class TypeHandlerRegistry:
    """Registry of type-specific handlers."""

    _handlers: Dict[str, Dict[str, Callable]] = {
        "directive": {},
        "script": {},
        "knowledge": {},
    }

    @classmethod
    def register(cls, type_name: str, operation: str, handler: Callable):
        """Register a handler for a type and operation."""
        if type_name not in cls._handlers:
            cls._handlers[type_name] = {}
        cls._handlers[type_name][operation] = handler

    @classmethod
    def get_handler(cls, type_name: str, operation: str) -> Optional[Callable]:
        """Get handler for type and operation."""
        return cls._handlers.get(type_name, {}).get(operation)

    @classmethod
    def dispatch(cls, type_name: str, operation: str, **kwargs) -> Any:
        """Dispatch to appropriate handler."""
        handler = cls.get_handler(type_name, operation)
        if not handler:
            raise ValueError(f"No handler for {type_name}.{operation}")
        return handler(**kwargs)

    @classmethod
    async def dispatch_async(cls, type_name: str, operation: str, **kwargs) -> Any:
        """Async dispatch to handler."""
        handler = cls.get_handler(type_name, operation)
        if not handler:
            raise ValueError(f"No handler for {type_name}.{operation}")
        return await handler(**kwargs)


# Import and register all handlers at module load
def _register_handlers():
    """Register all type handlers."""
    # Directive handlers
    from kiwi_mcp.handlers.directive.search import search_directives
    from kiwi_mcp.handlers.directive.load import load_directive
    from kiwi_mcp.handlers.directive.execute import execute_directive

    TypeHandlerRegistry.register("directive", "search", search_directives)
    TypeHandlerRegistry.register("directive", "load", load_directive)
    TypeHandlerRegistry.register("directive", "execute", execute_directive)

    # Script handlers
    from kiwi_mcp.handlers.script.search import search_scripts
    from kiwi_mcp.handlers.script.load import load_script
    from kiwi_mcp.handlers.script.execute import execute_script

    TypeHandlerRegistry.register("script", "search", search_scripts)
    TypeHandlerRegistry.register("script", "load", load_script)
    TypeHandlerRegistry.register("script", "execute", execute_script)

    # Knowledge handlers
    from kiwi_mcp.handlers.knowledge.search import search_knowledge
    from kiwi_mcp.handlers.knowledge.load import load_knowledge
    from kiwi_mcp.handlers.knowledge.execute import execute_knowledge

    TypeHandlerRegistry.register("knowledge", "search", search_knowledge)
    TypeHandlerRegistry.register("knowledge", "load", load_knowledge)
    TypeHandlerRegistry.register("knowledge", "execute", execute_knowledge)


_register_handlers()
```

---

## 5. Tool Specifications

### 5.1 Search Tool

```python
# kiwi_mcp/tools/search.py
"""
Unified Search Tool

Searches directives, scripts, or knowledge across local and registry.
"""

import json
from typing import Any
from mcp.types import Tool

from kiwi_mcp.handlers.registry import TypeHandlerRegistry


class SearchTool:
    """Search for items across sources."""

    @property
    def schema(self) -> Tool:
        return Tool(
            name="search",
            description="""Find directives, scripts, or knowledge using natural language search.

Multi-term matching: "JWT auth" matches items with both "JWT" and "auth".
Smart scoring: Name matches ranked higher than description matches.

Sources:
- "local": Search .ai/ (project) + ~/.ai/ (user)
- "registry": Search Supabase registry
- "all": Search everywhere (local first)

Examples:
- search("email campaign", type="directive")
- search("scrape Google Maps", type="script", category="scraping")
- search("deliverability", type="knowledge", source="registry")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["directive", "script", "knowledge"],
                        "description": "What to search for"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["local", "registry", "all"],
                        "default": "all",
                        "description": "Where to search"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Max results"
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Project root (required for local search)"
                    }
                },
                "required": ["query", "type"]
            }
        )

    async def execute(self, arguments: dict) -> str:
        """Execute search."""
        query = arguments.get("query")
        item_type = arguments.get("type")
        source = arguments.get("source", "all")

        if not query:
            return json.dumps({"error": "query is required"})
        if not item_type:
            return json.dumps({"error": "type is required"})
        if item_type not in ("directive", "script", "knowledge"):
            return json.dumps({"error": f"Invalid type: {item_type}"})

        # Validate project_path for local search
        if source in ("local", "all") and not arguments.get("project_path"):
            return json.dumps({
                "error": f"project_path is required when source='{source}'"
            })

        try:
            results = await TypeHandlerRegistry.dispatch_async(
                item_type, "search",
                query=query,
                source=source,
                category=arguments.get("category"),
                tags=arguments.get("tags"),
                limit=arguments.get("limit", 10),
                project_path=arguments.get("project_path")
            )

            return json.dumps({
                "query": query,
                "type": item_type,
                "source": source,
                "results": results,
                "total": len(results)
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
```

### 5.2 Load Tool

```python
# kiwi_mcp/tools/load.py
"""
Unified Load Tool

Downloads items from registry to local storage.
"""

import json
from mcp.types import Tool

from kiwi_mcp.handlers.registry import TypeHandlerRegistry


class LoadTool:
    """Download items from registry to local."""

    @property
    def schema(self) -> Tool:
        return Tool(
            name="load",
            description="""Download a directive, script, or knowledge from registry to local storage.

Destinations:
- "user": ~/.ai/{type}s/ (personal, works across projects)
- "project": .ai/{type}s/ (committed to git, team-shared)

Examples:
- load("google_maps_leads", type="script", destination="user")
- load("send_outreach", type="directive", destination="project", project_path="/path/to/project")
- load("kb-email-tips", type="knowledge", destination="user")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Item identifier"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["directive", "script", "knowledge"],
                        "description": "Item type"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["registry"],
                        "default": "registry",
                        "description": "Where to load from"
                    },
                    "destination": {
                        "type": "string",
                        "enum": ["user", "project"],
                        "description": "REQUIRED: Where to save locally"
                    },
                    "version": {
                        "type": "string",
                        "description": "Specific version (optional)"
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Required when destination='project'"
                    }
                },
                "required": ["id", "type", "destination"]
            }
        )

    async def execute(self, arguments: dict) -> str:
        """Execute load."""
        item_id = arguments.get("id")
        item_type = arguments.get("type")
        destination = arguments.get("destination")

        if not item_id:
            return json.dumps({"error": "id is required"})
        if not item_type:
            return json.dumps({"error": "type is required"})
        if not destination:
            return json.dumps({"error": "destination is required"})

        if destination == "project" and not arguments.get("project_path"):
            return json.dumps({
                "error": "project_path is required when destination='project'"
            })

        try:
            result = await TypeHandlerRegistry.dispatch_async(
                item_type, "load",
                item_id=item_id,
                source=arguments.get("source", "registry"),
                destination=destination,
                version=arguments.get("version"),
                project_path=arguments.get("project_path")
            )

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
```

### 5.3 Execute Tool

```python
# kiwi_mcp/tools/execute.py
"""
Unified Execute Tool

Handles all mutations: run, publish, delete, create, update, link.
"""

import json
from mcp.types import Tool

from kiwi_mcp.handlers.registry import TypeHandlerRegistry


class ExecuteTool:
    """Execute operations on items."""

    @property
    def schema(self) -> Tool:
        return Tool(
            name="execute",
            description="""Execute operations on directives, scripts, or knowledge.

Actions:
- run: Execute the item (directive returns steps, script runs code, knowledge returns content)
- publish: Upload to registry
- delete: Remove from local or registry
- create: Create new item locally
- update: Modify existing item
- link: (knowledge only) Link two entries

Examples:
- execute(action="run", id="send_outreach", type="directive", parameters={...})
- execute(action="run", id="google_maps_leads", type="script", parameters={...})
- execute(action="publish", id="my_script", type="script", parameters={version: "1.0.0"})
- execute(action="delete", id="old_script", type="script", parameters={confirm: true})
- execute(action="create", id="kb-new", type="knowledge", parameters={title: "...", content: "..."})
- execute(action="link", id="kb-001", type="knowledge", parameters={to: "kb-002", relationship: "references"})""",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["run", "publish", "delete", "create", "update", "link"],
                        "description": "Operation to perform"
                    },
                    "id": {
                        "type": "string",
                        "description": "Item identifier"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["directive", "script", "knowledge"],
                        "description": "Item type"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Action-specific parameters"
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Project root path"
                    }
                },
                "required": ["action", "id", "type"]
            }
        )

    async def execute(self, arguments: dict) -> str:
        """Execute the operation."""
        action = arguments.get("action")
        item_id = arguments.get("id")
        item_type = arguments.get("type")
        parameters = arguments.get("parameters", {})
        project_path = arguments.get("project_path")

        if not action:
            return json.dumps({"error": "action is required"})
        if not item_id:
            return json.dumps({"error": "id is required"})
        if not item_type:
            return json.dumps({"error": "type is required"})

        # Validate action is supported for this type
        if action == "link" and item_type != "knowledge":
            return json.dumps({"error": "link action only supported for knowledge type"})

        try:
            result = await TypeHandlerRegistry.dispatch_async(
                item_type, "execute",
                action=action,
                item_id=item_id,
                parameters=parameters,
                project_path=project_path
            )

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
```

### 5.4 Help Tool

```python
# kiwi_mcp/tools/help.py
"""
Unified Help Tool

Usage guidance and troubleshooting.
"""

import json
from mcp.types import Tool


HELP_CONTENT = {
    "overview": """
# Kiwi MCP - Unified Tool Interface

4 tools for managing directives, scripts, and knowledge:

## Tools

| Tool | Purpose |
|------|---------|
| search | Find items across local/registry |
| load | Download from registry to local |
| execute | Run, publish, delete, create, update, link |
| help | Usage guidance |

## Types

| Type | What It Stores | Purpose |
|------|---------------|---------|
| directive | Workflows, processes | Orchestration - tells agents HOW |
| script | Python code | Execution - actually DOES work |
| knowledge | Facts, patterns | Memory - stores WHAT we learned |

## Storage

- Project: .ai/directives/, .ai/scripts/, .ai/knowledge/
- User: ~/.ai/directives/, ~/.ai/scripts/, ~/.ai/knowledge/
- Registry: Supabase (shared globally)

## Quick Start

1. search("email campaign", type="directive")
2. load("send_outreach", type="directive", destination="user")
3. execute(action="run", id="send_outreach", type="directive")
""",

    "search": """
# Search Tool

Find items using natural language search.

## Parameters
- query (required): Search terms
- type (required): "directive" | "script" | "knowledge"
- source: "local" | "registry" | "all" (default)
- category: Filter by category
- tags: Filter by tags (array)
- limit: Max results (default: 10)
- project_path: Required for local search

## Examples

```

search("email deliverability", type="knowledge")
search("scrape leads", type="script", category="scraping")
search("JWT auth", type="directive", source="registry")

```
""",

    "load": """
# Load Tool

Download from registry to local storage.

## Parameters
- id (required): Item identifier
- type (required): "directive" | "script" | "knowledge"
- destination (required): "user" | "project"
- version: Specific version (optional)
- project_path: Required when destination="project"

## Examples

```

load("google_maps_leads", type="script", destination="user")
load("send_outreach", type="directive", destination="project", project_path="/path")

```
""",

    "execute": """
# Execute Tool

Perform operations on items.

## Actions

| Action | Directive | Script | Knowledge |
|--------|-----------|--------|-----------|
| run | Return parsed steps | Execute Python | Return content |
| publish | Upload to registry | Upload to registry | Upload to registry |
| delete | Remove | Remove | Remove |
| create | Create locally | Create locally | Create locally |
| update | Modify | Modify | Modify |
| link | N/A | N/A | Link entries |

## Examples

```

execute(action="run", id="send_outreach", type="directive", parameters={...})
execute(action="run", id="google_maps_leads", type="script", parameters={...})
execute(action="publish", id="my_script", type="script", parameters={version: "1.0.0"})
execute(action="delete", id="old_entry", type="knowledge", parameters={confirm: true})

```
"""
}


class HelpTool:
    """Provide usage guidance."""

    @property
    def schema(self) -> Tool:
        return Tool(
            name="help",
            description="""Get usage guidance for Kiwi MCP.

Topics: overview, search, load, execute""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you need help with"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context"
                    }
                },
                "required": ["query"]
            }
        )

    async def execute(self, arguments: dict) -> str:
        """Return help content."""
        query = arguments.get("query", "").lower()

        # Match to topic
        if "search" in query:
            content = HELP_CONTENT["search"]
        elif "load" in query or "download" in query:
            content = HELP_CONTENT["load"]
        elif "execute" in query or "run" in query or "publish" in query:
            content = HELP_CONTENT["execute"]
        else:
            content = HELP_CONTENT["overview"]

        return json.dumps({"help": content}, indent=2)
```

---

## 6. API Layer

The API layer contains registry clients for Supabase. These are ported from the existing MCPs.

### 6.1 Base Registry

```python
# kiwi_mcp/api/base.py
"""Base registry client."""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv


class BaseRegistry:
    """Base class for Supabase registry clients."""

    def __init__(self):
        load_dotenv()
        self._client: Optional[Client] = None

    @property
    def client(self) -> Optional[Client]:
        """Lazily initialize Supabase client."""
        if self._client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SECRET_KEY")

            if not url or not key:
                return None

            try:
                self._client = create_client(url.strip(), key.strip())
            except Exception as e:
                print(f"Error creating Supabase client: {e}")
                return None
        return self._client

    @property
    def is_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SECRET_KEY"))

    def _parse_search_query(self, query: str) -> list[str]:
        """Parse query into normalized terms."""
        if not query or not query.strip():
            return []

        return [
            word.strip().lower()
            for word in query.split()
            if word.strip() and len(word.strip()) >= 2
        ]

    def _calculate_relevance_score(
        self,
        query_terms: list[str],
        name: str,
        description: str = ""
    ) -> float:
        """Calculate relevance score (0-100)."""
        name_lower = name.lower()
        desc_lower = description.lower()

        # Exact name match
        name_normalized = name_lower.replace("_", " ").replace("-", " ")
        query_normalized = " ".join(query_terms)
        if name_normalized == query_normalized:
            return 100.0

        # Count matches
        name_matches = sum(1 for term in query_terms if term in name_lower)
        desc_matches = sum(1 for term in query_terms if term in desc_lower)

        score = 0.0
        if name_matches == len(query_terms):
            score = 80.0
        elif name_matches > 0:
            score = 60.0 * (name_matches / len(query_terms))

        if desc_matches == len(query_terms):
            score = max(score, 40.0)
        elif desc_matches > 0:
            score = max(score, 20.0 * (desc_matches / len(query_terms)))

        return score
```

### 6.2 Directive Registry

Port from `context-kiwi/context_kiwi/db/directives.py`:

```python
# kiwi_mcp/api/directive_registry.py
"""Directive registry client (ported from context-kiwi)."""

from typing import Any, Dict, List, Optional
from kiwi_mcp.api.base import BaseRegistry


class DirectiveRegistry(BaseRegistry):
    """Supabase client for directives table."""

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search directives in registry."""
        if not self.client:
            return []

        query_terms = self._parse_search_query(query)
        if not query_terms:
            return []

        try:
            # Build OR conditions
            or_conditions = []
            for term in query_terms:
                or_conditions.extend([
                    f"name.ilike.%{term}%",
                    f"description.ilike.%{term}%"
                ])

            query_builder = self.client.table("directives").select(
                "id, name, category, subcategory, description, is_official, "
                "download_count, quality_score, tech_stack, created_at, updated_at, "
                "tags, latest_version"
            )

            if or_conditions:
                query_builder = query_builder.or_(",".join(or_conditions))

            if category:
                query_builder = query_builder.eq("category", category)

            result = query_builder.limit(limit * 3).execute()

            directives = []
            for row in (result.data or []):
                name = row.get("name", "")
                description = row.get("description", "")
                name_desc = f"{name} {description}".lower()

                if not all(term in name_desc for term in query_terms):
                    continue

                score = self._calculate_relevance_score(query_terms, name, description)

                directives.append({
                    "id": row.get("id"),
                    "name": name,
                    "description": description,
                    "category": row.get("category"),
                    "subcategory": row.get("subcategory"),
                    "version": row.get("latest_version"),
                    "tech_stack": row.get("tech_stack", []),
                    "tags": row.get("tags", []),
                    "quality_score": row.get("quality_score"),
                    "download_count": row.get("download_count"),
                    "relevance_score": score,
                    "source": "registry"
                })

            directives.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return directives[:limit]
        except Exception as e:
            print(f"Error searching directives: {e}")
            return []

    async def get(self, name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get directive from registry."""
        if not self.client:
            return None

        try:
            # Get directive
            result = self.client.table("directives").select("*").eq("name", name).single().execute()
            if not result.data:
                return None

            directive = result.data

            # Get content from versions table
            version_query = self.client.table("directive_versions").select("*").eq(
                "directive_id", directive["id"]
            )

            if version:
                version_query = version_query.eq("version", version)
            else:
                version_query = version_query.eq("is_latest", True)

            version_result = version_query.single().execute()

            return {
                "name": directive["name"],
                "description": directive.get("description"),
                "category": directive.get("category"),
                "subcategory": directive.get("subcategory"),
                "version": version_result.data["version"] if version_result.data else None,
                "content": version_result.data["content"] if version_result.data else None,
                "tags": directive.get("tags", [])
            }
        except Exception as e:
            print(f"Error getting directive: {e}")
            return None

    async def publish(
        self,
        name: str,
        version: str,
        content: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
        changelog: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish directive to registry."""
        if not self.client:
            return {"error": "Supabase not configured"}

        try:
            # Check if exists
            existing = self.client.table("directives").select("id").eq("name", name).execute()

            if existing.data:
                directive_id = existing.data[0]["id"]
            else:
                # Create new
                result = self.client.table("directives").insert({
                    "name": name,
                    "category": category or "custom",
                    "description": description or ""
                }).execute()
                directive_id = result.data[0]["id"]

            # Mark old versions as not latest
            self.client.table("directive_versions").update(
                {"is_latest": False}
            ).eq("directive_id", directive_id).execute()

            # Insert new version
            self.client.table("directive_versions").insert({
                "directive_id": directive_id,
                "version": version,
                "content": content,
                "changelog": changelog,
                "is_latest": True
            }).execute()

            # Update latest_version
            self.client.table("directives").update(
                {"latest_version": version}
            ).eq("id", directive_id).execute()

            return {"status": "published", "name": name, "version": version}
        except Exception as e:
            return {"error": str(e)}

    async def delete(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Delete directive from registry."""
        if not self.client:
            return {"error": "Supabase not configured"}

        try:
            existing = self.client.table("directives").select("id").eq("name", name).execute()
            if not existing.data:
                return {"error": f"Directive '{name}' not found"}

            directive_id = existing.data[0]["id"]

            if version:
                self.client.table("directive_versions").delete().eq(
                    "directive_id", directive_id
                ).eq("version", version).execute()
            else:
                self.client.table("directive_versions").delete().eq(
                    "directive_id", directive_id
                ).execute()
                self.client.table("directives").delete().eq("id", directive_id).execute()

            return {"status": "deleted", "name": name, "version": version}
        except Exception as e:
            return {"error": str(e)}
```

### 6.3 Script Registry

Port from `script-kiwi/script_kiwi/api/script_registry.py`:

```python
# kiwi_mcp/api/script_registry.py
"""Script registry client (ported from script-kiwi)."""

from typing import Any, Dict, List, Optional
from kiwi_mcp.api.base import BaseRegistry


class ScriptRegistry(BaseRegistry):
    """Supabase client for scripts table."""

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search scripts in registry."""
        if not self.client:
            return []

        query_terms = self._parse_search_query(query)
        if not query_terms:
            return []

        try:
            or_conditions = []
            for term in query_terms:
                or_conditions.extend([
                    f"name.ilike.%{term}%",
                    f"description.ilike.%{term}%"
                ])

            query_builder = self.client.table("scripts").select(
                "id, name, category, subcategory, description, is_official, "
                "download_count, quality_score, tech_stack, tags, latest_version"
            )

            if or_conditions:
                query_builder = query_builder.or_(",".join(or_conditions))

            if category:
                query_builder = query_builder.eq("category", category)

            result = query_builder.limit(limit * 3).execute()

            scripts = []
            for row in (result.data or []):
                name = row.get("name", "")
                description = row.get("description", "")
                name_desc = f"{name} {description}".lower()

                if not all(term in name_desc for term in query_terms):
                    continue

                score = self._calculate_relevance_score(query_terms, name, description)

                scripts.append({
                    "name": name,
                    "description": description,
                    "category": row.get("category"),
                    "subcategory": row.get("subcategory"),
                    "version": row.get("latest_version"),
                    "tech_stack": row.get("tech_stack", []),
                    "tags": row.get("tags", []),
                    "quality_score": row.get("quality_score"),
                    "download_count": row.get("download_count"),
                    "relevance_score": score,
                    "source": "registry"
                })

            scripts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return scripts[:limit]
        except Exception as e:
            print(f"Error searching scripts: {e}")
            return []

    async def get(self, name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get script from registry."""
        if not self.client:
            return None

        try:
            result = self.client.table("scripts").select("*").eq("name", name).single().execute()
            if not result.data:
                return None

            script = result.data

            version_query = self.client.table("script_versions").select("*").eq(
                "script_id", script["id"]
            )

            if version:
                version_query = version_query.eq("version", version)
            else:
                version_query = version_query.eq("is_latest", True)

            version_result = version_query.single().execute()

            return {
                "name": script["name"],
                "description": script.get("description"),
                "category": script.get("category"),
                "subcategory": script.get("subcategory"),
                "version": version_result.data["version"] if version_result.data else None,
                "content": version_result.data["content"] if version_result.data else None,
                "dependencies": script.get("dependencies", []),
                "required_env_vars": script.get("required_env_vars", []),
                "tech_stack": script.get("tech_stack", []),
                "cost_per_unit": script.get("cost_per_unit"),
                "cost_unit": script.get("cost_unit")
            }
        except Exception as e:
            print(f"Error getting script: {e}")
            return None

    async def publish(
        self,
        name: str,
        version: str,
        content: str,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        changelog: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish script to registry."""
        if not self.client:
            return {"error": "Supabase not configured"}

        try:
            existing = self.client.table("scripts").select("id").eq("name", name).execute()

            if existing.data:
                script_id = existing.data[0]["id"]
                if metadata:
                    self.client.table("scripts").update(metadata).eq("id", script_id).execute()
            else:
                script_data = {
                    "name": name,
                    "category": category or "custom",
                    **(metadata or {})
                }
                result = self.client.table("scripts").insert(script_data).execute()
                script_id = result.data[0]["id"]

            self.client.table("script_versions").update(
                {"is_latest": False}
            ).eq("script_id", script_id).execute()

            import hashlib
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            self.client.table("script_versions").insert({
                "script_id": script_id,
                "version": version,
                "content": content,
                "content_hash": content_hash,
                "changelog": changelog,
                "is_latest": True
            }).execute()

            self.client.table("scripts").update(
                {"latest_version": version}
            ).eq("id", script_id).execute()

            return {"status": "published", "name": name, "version": version}
        except Exception as e:
            return {"error": str(e)}

    async def delete(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Delete script from registry."""
        if not self.client:
            return {"error": "Supabase not configured"}

        try:
            existing = self.client.table("scripts").select("id").eq("name", name).execute()
            if not existing.data:
                return {"error": f"Script '{name}' not found"}

            script_id = existing.data[0]["id"]

            if version:
                self.client.table("script_versions").delete().eq(
                    "script_id", script_id
                ).eq("version", version).execute()
            else:
                self.client.table("script_versions").delete().eq(
                    "script_id", script_id
                ).execute()
                self.client.table("scripts").delete().eq("id", script_id).execute()

            return {"status": "deleted", "name": name, "version": version}
        except Exception as e:
            return {"error": str(e)}
```

### 6.4 Knowledge Registry

Port from `knowledge-kiwi/knowledge_kiwi/api/knowledge_registry.py`:

```python
# kiwi_mcp/api/knowledge_registry.py
"""Knowledge registry client (ported from knowledge-kiwi)."""

from typing import Any, Dict, List, Optional
from kiwi_mcp.api.base import BaseRegistry


class KnowledgeRegistry(BaseRegistry):
    """Supabase client for knowledge_entries table."""

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search knowledge in registry."""
        if not self.client:
            return []

        query_terms = self._parse_search_query(query)
        if not query_terms:
            return []

        try:
            result = self.client.rpc(
                "search_knowledge_fulltext",
                {
                    "search_query": query,
                    "match_count": limit * 3,
                    "filter_entry_type": entry_type,
                    "filter_tags": tags,
                    "filter_category": category
                }
            ).execute()

            entries = []
            for row in result.data:
                title = row.get("title", "")
                snippet = row.get("snippet", "")
                title_snippet = f"{title} {snippet}".lower()

                if not all(term in title_snippet for term in query_terms):
                    continue

                score = self._calculate_relevance_score(query_terms, title, snippet)

                entries.append({
                    "zettel_id": row["zettel_id"],
                    "title": title,
                    "entry_type": row["entry_type"],
                    "category": row.get("category"),
                    "tags": row.get("tags", []),
                    "relevance_score": score / 100.0,
                    "snippet": snippet,
                    "source": "registry"
                })

            entries.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return entries[:limit]
        except Exception as e:
            print(f"Error searching knowledge: {e}")
            return []

    async def get(self, zettel_id: str) -> Optional[Dict[str, Any]]:
        """Get knowledge entry from registry."""
        if not self.client:
            return None

        try:
            result = self.client.table("knowledge_entries").select("*").eq(
                "zettel_id", zettel_id
            ).single().execute()

            if result.data:
                return {
                    "zettel_id": result.data["zettel_id"],
                    "title": result.data["title"],
                    "content": result.data["content"],
                    "entry_type": result.data["entry_type"],
                    "category": result.data.get("category"),
                    "tags": result.data.get("tags", []),
                    "source_type": result.data.get("source_type"),
                    "source_url": result.data.get("source_url"),
                    "version": result.data.get("version", "1.0.0")
                }
            return None
        except Exception as e:
            print(f"Error getting knowledge: {e}")
            return None

    async def publish(
        self,
        zettel_id: str,
        title: str,
        content: str,
        entry_type: str,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish knowledge to registry."""
        if not self.client:
            return {"error": "Supabase not configured"}

        try:
            existing = await self.get(zettel_id)

            entry_data = {
                "zettel_id": zettel_id,
                "title": title,
                "content": content,
                "entry_type": entry_type,
                "tags": tags or [],
                "category": category
            }

            if version:
                entry_data["version"] = version
            elif existing:
                # Auto-increment
                parts = existing.get("version", "1.0.0").split(".")
                entry_data["version"] = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
            else:
                entry_data["version"] = "1.0.0"

            if existing:
                self.client.table("knowledge_entries").update(entry_data).eq(
                    "zettel_id", zettel_id
                ).execute()
            else:
                self.client.table("knowledge_entries").insert(entry_data).execute()

            return {"status": "published", "zettel_id": zettel_id, "version": entry_data["version"]}
        except Exception as e:
            return {"error": str(e)}

    async def delete(self, zettel_id: str, cascade_relationships: bool = False) -> Dict[str, Any]:
        """Delete knowledge from registry."""
        if not self.client:
            return {"error": "Supabase not configured"}

        try:
            existing = await self.get(zettel_id)
            if not existing:
                return {"error": f"Entry '{zettel_id}' not found"}

            if cascade_relationships:
                self.client.table("knowledge_relationships").delete().eq(
                    "from_zettel_id", zettel_id
                ).execute()
                self.client.table("knowledge_relationships").delete().eq(
                    "to_zettel_id", zettel_id
                ).execute()

            self.client.table("knowledge_entries").delete().eq(
                "zettel_id", zettel_id
            ).execute()

            return {"status": "deleted", "zettel_id": zettel_id}
        except Exception as e:
            return {"error": str(e)}

    async def create_relationship(
        self,
        from_zettel_id: str,
        to_zettel_id: str,
        relationship_type: str
    ) -> Dict[str, Any]:
        """Create relationship between entries."""
        if not self.client:
            return {"error": "Supabase not configured"}

        try:
            self.client.table("knowledge_relationships").insert({
                "from_zettel_id": from_zettel_id,
                "to_zettel_id": to_zettel_id,
                "relationship_type": relationship_type
            }).execute()

            return {
                "status": "linked",
                "from": from_zettel_id,
                "to": to_zettel_id,
                "relationship": relationship_type
            }
        except Exception as e:
            return {"error": str(e)}
```

---

## 7. Storage & Resolution

### 7.1 Path Configuration

```python
# kiwi_mcp/utils/paths.py
"""Path resolution utilities."""

import os
from pathlib import Path
from typing import Optional


def get_user_home() -> Path:
    """Get user home directory for Kiwi storage."""
    env_path = os.getenv("KIWI_USER_PATH")
    if env_path:
        return Path(env_path)
    return Path.home() / ".ai"


def get_project_path(project_path: Optional[str] = None) -> Path:
    """Get project .ai directory."""
    if project_path:
        return Path(project_path) / ".ai"
    return Path.cwd() / ".ai"


def get_type_directory(base_path: Path, item_type: str) -> Path:
    """Get directory for item type."""
    type_dirs = {
        "directive": "directives",
        "script": "scripts",
        "knowledge": "knowledge"
    }
    return base_path / type_dirs.get(item_type, item_type)


def resolve_item_path(
    item_id: str,
    item_type: str,
    source: str,
    project_path: Optional[str] = None,
    category: Optional[str] = None
) -> Optional[Path]:
    """
    Resolve path to an item.

    Resolution order for "local":
    1. Project space: .ai/{type}s/
    2. User space: ~/.ai/{type}s/

    Returns None if not found.
    """
    if source == "registry":
        return None  # Registry items don't have local paths

    ext = ".md" if item_type in ("directive", "knowledge") else ".py"
    filename = f"{item_id}{ext}"

    # Check project space
    if project_path:
        project_dir = get_type_directory(get_project_path(project_path), item_type)
        if category:
            candidate = project_dir / category / filename
            if candidate.exists():
                return candidate
        for path in project_dir.rglob(filename):
            return path

    # Check user space
    user_dir = get_type_directory(get_user_home(), item_type)
    if category:
        candidate = user_dir / category / filename
        if candidate.exists():
            return candidate
    for path in user_dir.rglob(filename):
        return path

    return None
```

### 7.2 Local File Operations

```python
# kiwi_mcp/utils/files.py
"""File operations for local storage."""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml


def read_markdown_file(path: Path) -> Dict[str, Any]:
    """Read markdown file with YAML frontmatter."""
    content = path.read_text(encoding="utf-8")

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1].strip()) or {}
            except yaml.YAMLError:
                frontmatter = {}
            body = parts[2].strip()
        else:
            frontmatter = {}
            body = content
    else:
        frontmatter = {}
        body = content

    return {
        **frontmatter,
        "content": body,
        "path": str(path)
    }


def write_markdown_file(
    path: Path,
    content: str,
    frontmatter: Optional[Dict[str, Any]] = None
) -> None:
    """Write markdown file with optional frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if frontmatter:
        frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        file_content = f"---\n{frontmatter_yaml}---\n\n{content}\n"
    else:
        file_content = content

    path.write_text(file_content, encoding="utf-8")


def write_python_file(path: Path, content: str) -> None:
    """Write Python script file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

---

## 8. Full Code Implementation

### 8.1 Directive Handlers

```python
# kiwi_mcp/handlers/directive/search.py
"""Directive search handler."""

from typing import Any, Dict, List, Optional
from pathlib import Path

from kiwi_mcp.api.directive_registry import DirectiveRegistry
from kiwi_mcp.utils.paths import get_user_home, get_project_path


async def search_directives(
    query: str,
    source: str = "all",
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10,
    project_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for directives."""
    results = []

    # Search local
    if source in ("local", "all"):
        results.extend(_search_local(query, project_path, category, tags, limit))

    # Search registry
    if source in ("registry", "all"):
        registry = DirectiveRegistry()
        registry_results = await registry.search(query, category=category, tags=tags, limit=limit)

        # Avoid duplicates
        existing_names = {r["name"] for r in results}
        for item in registry_results:
            if item["name"] not in existing_names:
                results.append(item)

    # Sort by relevance
    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return results[:limit]


def _search_local(
    query: str,
    project_path: Optional[str],
    category: Optional[str],
    tags: Optional[List[str]],
    limit: int
) -> List[Dict[str, Any]]:
    """Search local directive files."""
    results = []
    query_terms = [w.lower() for w in query.split() if len(w) >= 2]

    dirs_to_search = []
    if project_path:
        dirs_to_search.append(("project", get_project_path(project_path) / "directives"))
    dirs_to_search.append(("user", get_user_home() / "directives"))

    for source_name, dir_path in dirs_to_search:
        if not dir_path.exists():
            continue

        for md_file in dir_path.rglob("*.md"):
            try:
                from kiwi_mcp.utils.files import read_markdown_file
                data = read_markdown_file(md_file)

                name = md_file.stem
                description = data.get("description", "")
                text = f"{name} {description}".lower()

                if not all(term in text for term in query_terms):
                    continue

                # Calculate score
                name_matches = sum(1 for t in query_terms if t in name.lower())
                score = 50 + (name_matches * 10)

                results.append({
                    "name": name,
                    "description": description,
                    "version": data.get("version", "1.0.0"),
                    "category": data.get("category"),
                    "tech_stack": data.get("tech_stack", []),
                    "tags": data.get("tags", []),
                    "relevance_score": score,
                    "source": source_name
                })
            except Exception:
                continue

    return results
```

```python
# kiwi_mcp/handlers/directive/load.py
"""Directive load handler."""

from typing import Any, Dict, Optional
from pathlib import Path

from kiwi_mcp.api.directive_registry import DirectiveRegistry
from kiwi_mcp.utils.paths import get_user_home, get_project_path
from kiwi_mcp.utils.files import write_markdown_file


async def load_directive(
    item_id: str,
    source: str = "registry",
    destination: str = "user",
    version: Optional[str] = None,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """Load directive from registry to local."""

    # Get from registry
    registry = DirectiveRegistry()
    directive = await registry.get(item_id, version=version)

    if not directive:
        return {"error": f"Directive '{item_id}' not found in registry"}

    if not directive.get("content"):
        return {"error": f"Directive '{item_id}' has no content"}

    # Determine destination path
    if destination == "project":
        if not project_path:
            return {"error": "project_path required for destination='project'"}
        base_dir = get_project_path(project_path) / "directives"
    else:
        base_dir = get_user_home() / "directives"

    # Add category subdirectory if present
    if directive.get("category"):
        base_dir = base_dir / directive["category"]

    file_path = base_dir / f"{item_id}.md"

    # Write file
    frontmatter = {
        "name": directive["name"],
        "version": directive.get("version", "1.0.0"),
    }
    if directive.get("description"):
        frontmatter["description"] = directive["description"]
    if directive.get("category"):
        frontmatter["category"] = directive["category"]

    write_markdown_file(file_path, directive["content"], frontmatter)

    return {
        "status": "loaded",
        "name": item_id,
        "version": directive.get("version"),
        "destination": destination,
        "path": str(file_path)
    }
```

```python
# kiwi_mcp/handlers/directive/execute.py
"""Directive execute handler."""

from typing import Any, Dict, Optional
from pathlib import Path

from kiwi_mcp.api.directive_registry import DirectiveRegistry
from kiwi_mcp.utils.paths import resolve_item_path, get_user_home, get_project_path
from kiwi_mcp.utils.files import read_markdown_file, write_markdown_file


async def execute_directive(
    action: str,
    item_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """Execute directive operations."""
    params = parameters or {}

    if action == "run":
        return await _run_directive(item_id, params, project_path)
    elif action == "publish":
        return await _publish_directive(item_id, params, project_path)
    elif action == "delete":
        return await _delete_directive(item_id, params, project_path)
    elif action == "create":
        return await _create_directive(item_id, params, project_path)
    elif action == "update":
        return await _update_directive(item_id, params, project_path)
    else:
        return {"error": f"Unknown action: {action}"}


async def _run_directive(
    item_id: str,
    params: Dict[str, Any],
    project_path: Optional[str]
) -> Dict[str, Any]:
    """Run a directive (return parsed content for agent to follow)."""

    # Try local first
    path = resolve_item_path(item_id, "directive", "local", project_path)

    if path and path.exists():
        data = read_markdown_file(path)
        return {
            "action": "run",
            "name": item_id,
            "source": "local",
            "content": data.get("content", ""),
            "inputs": params,
            "instructions": "Follow the directive steps above."
        }

    # Try registry
    registry = DirectiveRegistry()
    directive = await registry.get(item_id)

    if directive and directive.get("content"):
        return {
            "action": "run",
            "name": item_id,
            "source": "registry",
            "content": directive["content"],
            "inputs": params,
            "instructions": "Follow the directive steps above."
        }

    return {"error": f"Directive '{item_id}' not found"}


async def _publish_directive(
    item_id: str,
    params: Dict[str, Any],
    project_path: Optional[str]
) -> Dict[str, Any]:
    """Publish directive to registry."""
    version = params.get("version")
    if not version:
        return {"error": "version is required for publish"}

    # Find local file
    path = resolve_item_path(item_id, "directive", "local", project_path)
    if not path or not path.exists():
        return {"error": f"Directive '{item_id}' not found locally"}

    data = read_markdown_file(path)
    content = data.get("content", "")

    registry = DirectiveRegistry()
    return await registry.publish(
        name=item_id,
        version=version,
        content=content,
        category=data.get("category"),
        description=data.get("description"),
        changelog=params.get("changelog")
    )


async def _delete_directive(
    item_id: str,
    params: Dict[str, Any],
    project_path: Optional[str]
) -> Dict[str, Any]:
    """Delete directive."""
    if not params.get("confirm"):
        return {"error": "Set confirm=true to delete"}

    source = params.get("source", "local")
    deleted = []

    if source in ("local", "all"):
        path = resolve_item_path(item_id, "directive", "local", project_path)
        if path and path.exists():
            path.unlink()
            deleted.append(f"local:{path}")

    if source in ("registry", "all"):
        registry = DirectiveRegistry()
        result = await registry.delete(item_id, version=params.get("version"))
        if "error" not in result:
            deleted.append("registry")

    return {"status": "deleted", "name": item_id, "deleted_from": deleted}


async def _create_directive(
    item_id: str,
    params: Dict[str, Any],
    project_path: Optional[str]
) -> Dict[str, Any]:
    """Create new directive locally."""
    content = params.get("content", "")
    location = params.get("location", "project")

    if location == "project":
        if not project_path:
            return {"error": "project_path required for location='project'"}
        base_dir = get_project_path(project_path) / "directives"
    else:
        base_dir = get_user_home() / "directives"

    if params.get("category"):
        base_dir = base_dir / params["category"]

    file_path = base_dir / f"{item_id}.md"

    frontmatter = {
        "name": item_id,
        "version": params.get("version", "1.0.0"),
    }
    if params.get("description"):
        frontmatter["description"] = params["description"]
    if params.get("category"):
        frontmatter["category"] = params["category"]

    write_markdown_file(file_path, content, frontmatter)

    return {"status": "created", "name": item_id, "path": str(file_path)}


async def _update_directive(
    item_id: str,
    params: Dict[str, Any],
    project_path: Optional[str]
) -> Dict[str, Any]:
    """Update existing directive."""
    path = resolve_item_path(item_id, "directive", "local", project_path)
    if not path or not path.exists():
        return {"error": f"Directive '{item_id}' not found locally"}

    data = read_markdown_file(path)

    # Update content if provided
    content = params.get("content", data.get("content", ""))

    # Update frontmatter
    frontmatter = {
        "name": item_id,
        "version": params.get("version", data.get("version", "1.0.0")),
    }
    if params.get("description") or data.get("description"):
        frontmatter["description"] = params.get("description", data.get("description"))
    if params.get("category") or data.get("category"):
        frontmatter["category"] = params.get("category", data.get("category"))

    write_markdown_file(path, content, frontmatter)

    return {"status": "updated", "name": item_id, "path": str(path)}
```

### 8.2 Script Handlers

Similar structure to directive handlers, but for Python files:

```python
# kiwi_mcp/handlers/script/execute.py (key part)
"""Script execute handler."""

import asyncio
import sys
import importlib.util
from typing import Any, Dict, Optional
from pathlib import Path


async def _run_script(
    item_id: str,
    params: Dict[str, Any],
    project_path: Optional[str]
) -> Dict[str, Any]:
    """Execute a Python script."""
    from kiwi_mcp.utils.paths import resolve_item_path

    # Find script
    path = resolve_item_path(item_id, "script", "local", project_path)

    if not path or not path.exists():
        return {"error": f"Script '{item_id}' not found"}

    # Dry run mode
    if params.get("dry_run"):
        return {
            "action": "dry_run",
            "name": item_id,
            "path": str(path),
            "parameters": params,
            "message": "Validation passed. Set dry_run=false to execute."
        }

    try:
        # Load and execute script
        spec = importlib.util.spec_from_file_location(item_id, path)
        if not spec or not spec.loader:
            return {"error": f"Failed to load script: {item_id}"}

        module = importlib.util.module_from_spec(spec)
        sys.modules[item_id] = module
        spec.loader.exec_module(module)

        # Look for main/run/execute function
        func = None
        for name in ["main", "run", "execute"]:
            if hasattr(module, name):
                func = getattr(module, name)
                break

        if not func:
            return {"error": f"Script '{item_id}' has no main/run/execute function"}

        # Execute
        if asyncio.iscoroutinefunction(func):
            result = await func(**params)
        else:
            result = func(**params)

        return {
            "action": "run",
            "name": item_id,
            "result": result
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
```

### 8.3 Knowledge Handlers

Similar to directive handlers but with YAML frontmatter support and linking:

```python
# kiwi_mcp/handlers/knowledge/execute.py (link action)
"""Knowledge execute handler - link action."""


async def _link_knowledge(
    item_id: str,
    params: Dict[str, Any],
    project_path: Optional[str]
) -> Dict[str, Any]:
    """Link two knowledge entries."""
    to_id = params.get("to")
    relationship = params.get("relationship", "references")

    if not to_id:
        return {"error": "'to' parameter required for link action"}

    registry = KnowledgeRegistry()
    return await registry.create_relationship(
        from_zettel_id=item_id,
        to_zettel_id=to_id,
        relationship_type=relationship
    )
```

---

## 9. Testing Strategy

### conftest.py

```python
# tests/conftest.py
"""Pytest fixtures."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_project():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        (project / ".ai" / "directives").mkdir(parents=True)
        (project / ".ai" / "scripts").mkdir(parents=True)
        (project / ".ai" / "knowledge").mkdir(parents=True)
        yield project


@pytest.fixture
def sample_directive(temp_project):
    """Create sample directive file."""
    content = '''---
name: test_directive
version: 1.0.0
description: Test directive
---

# Test Directive

This is a test.
'''
    path = temp_project / ".ai" / "directives" / "test_directive.md"
    path.write_text(content)
    return path


@pytest.fixture
def sample_script(temp_project):
    """Create sample script file."""
    content = '''
def main(name: str = "World"):
    """Sample script."""
    return f"Hello, {name}!"
'''
    path = temp_project / ".ai" / "scripts" / "test_script.py"
    path.write_text(content)
    return path
```

### Sample Tests

```python
# tests/unit/test_tools.py
"""Tool tests."""

import pytest
from kiwi_mcp.tools.search import SearchTool
from kiwi_mcp.tools.execute import ExecuteTool


@pytest.mark.asyncio
async def test_search_requires_query():
    tool = SearchTool()
    result = await tool.execute({"type": "directive"})
    assert "error" in result
    assert "query" in result


@pytest.mark.asyncio
async def test_search_requires_type():
    tool = SearchTool()
    result = await tool.execute({"query": "test"})
    assert "error" in result
    assert "type" in result


@pytest.mark.asyncio
async def test_execute_requires_action():
    tool = ExecuteTool()
    result = await tool.execute({"id": "test", "type": "directive"})
    assert "error" in result
    assert "action" in result
```

---

## 10. Future: RAG & Auth

### 10.1 RAG Search (Placeholder)

The current implementation uses keyword-based search. For RAG:

```python
# kiwi_mcp/api/rag.py (future)
"""RAG-based semantic search."""

from typing import List, Dict, Any


class RAGSearch:
    """Semantic search using embeddings."""

    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        self.model = embedding_model
        # Initialize vector store connection
        pass

    async def search(
        self,
        query: str,
        item_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Semantic search using embeddings."""
        # 1. Generate query embedding
        # 2. Search vector store
        # 3. Return ranked results
        pass

    async def index_item(
        self,
        item_id: str,
        item_type: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Index item for semantic search."""
        # 1. Generate content embedding
        # 2. Store in vector store with metadata
        pass
```

### 10.2 User Auth (Placeholder)

```python
# kiwi_mcp/auth/user.py (future)
"""User authentication."""

from typing import Optional, Dict, Any


class UserAuth:
    """User authentication and API key management."""

    def __init__(self):
        self._api_key: Optional[str] = None
        self._user_id: Optional[str] = None

    async def authenticate(self, api_key: str) -> Dict[str, Any]:
        """Authenticate user with API key."""
        # Validate against Supabase
        pass

    def get_user_id(self) -> Optional[str]:
        """Get authenticated user ID."""
        return self._user_id

    def check_permission(self, action: str, resource: str) -> bool:
        """Check if user has permission."""
        # Check permissions table
        pass
```

---

## 11. Migration Guide

### From Old MCPs to Unified Kiwi

| Old Tool                          | New Tool Call                                                                                  |
| --------------------------------- | ---------------------------------------------------------------------------------------------- |
| `context_kiwi__search("auth")`    | `kiwi__search(query="auth", type="directive")`                                                 |
| `context_kiwi__run("send_email")` | `kiwi__execute(action="run", id="send_email", type="directive")`                               |
| `context_kiwi__get("template")`   | `kiwi__load(id="template", type="directive", destination="user")`                              |
| `context_kiwi__publish("my_dir")` | `kiwi__execute(action="publish", id="my_dir", type="directive", parameters={version:"1.0.0"})` |
| `script_kiwi__search("scrape")`   | `kiwi__search(query="scrape", type="script")`                                                  |
| `script_kiwi__run("google_maps")` | `kiwi__execute(action="run", id="google_maps", type="script", parameters={...})`               |
| `script_kiwi__load("script")`     | `kiwi__load(id="script", type="script", destination="user")`                                   |
| `knowledge_kiwi__search("email")` | `kiwi__search(query="email", type="knowledge")`                                                |
| `knowledge_kiwi__get("kb-001")`   | `kiwi__execute(action="run", id="kb-001", type="knowledge")`                                   |
| `knowledge_kiwi__link(...)`       | `kiwi__execute(action="link", id="kb-001", type="knowledge", parameters={to:"kb-002"})`        |

### AGENTS.md Command Dispatch

```markdown
## COMMAND DISPATCH TABLE

| User Says                         | Call This            | With These Parameters                                                |
| --------------------------------- | -------------------- | -------------------------------------------------------------------- |
| `search directive X`              | `mcp__kiwi__search`  | `query=X, type="directive"`                                          |
| `search script X`                 | `mcp__kiwi__search`  | `query=X, type="script"`                                             |
| `search knowledge X`              | `mcp__kiwi__search`  | `query=X, type="knowledge"`                                          |
| `download directive X to project` | `mcp__kiwi__load`    | `id=X, type="directive", destination="project"`                      |
| `run directive X`                 | `mcp__kiwi__execute` | `action="run", id=X, type="directive"`                               |
| `run script X with Y`             | `mcp__kiwi__execute` | `action="run", id=X, type="script", parameters=Y`                    |
| `publish script X`                | `mcp__kiwi__execute` | `action="publish", id=X, type="script"`                              |
| `delete knowledge X`              | `mcp__kiwi__execute` | `action="delete", id=X, type="knowledge", parameters={confirm:true}` |
| `link knowledge X to Y`           | `mcp__kiwi__execute` | `action="link", id=X, type="knowledge", parameters={to:Y}`           |
```

---

## Summary

This document provides the complete implementation blueprint for the unified Kiwi MCP:

1. **Project Structure**: Clean layout with tools/, handlers/, api/, utils/
2. **4 Unified Tools**: search, load, execute, help
3. **Type Handler Registry**: Routes operations to type-specific handlers
4. **API Layer**: Ported from all 3 existing MCPs
5. **Storage**: Project (.ai/) → User (~/.ai/) → Registry (Supabase)
6. **Testing**: Fixtures and sample tests
7. **Future Hooks**: RAG search and user auth placeholders

**Next Steps:**

1. Create project structure
2. Implement server.py
3. Implement 4 tools
4. Port handlers from existing MCPs
5. Port API clients
6. Add tests
7. Test end-to-end

---

_Generated: 2026-01-11_
