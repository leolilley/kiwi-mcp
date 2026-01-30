"""RYE Tools - Intelligence layer for Lilux microkernel.

This package contains 5 intelligent MCP tools that understand content shapes
and delegate to Lilux primitives for execution.

Tools:
- search.py: Intelligent search with content type detection and relevance scoring
- load.py: Intelligent loading with source/destination resolution and protection
- execute.py: Intelligent execution with orchestration and telemetry
- sign.py: Intelligent signing with hash computation and validation
- help.py: Intelligent help with content listing and usage examples

Architecture:
RYE (OS Layer) → Lilux (Microkernel) → Primitives (Execution)

RYE Tools = Intelligent wrappers that understand content shapes
Lilux Primitives = Dumb execution (subprocess, HTTP, chains, locks, auth)
"""

from pathlib import Path
from typing import Dict, Any, Optional

from .search import SearchTool
from .load import LoadTool
from .execute import ExecuteTool
from .sign import SignTool
from .help import HelpTool


__all__ = [
    "SearchTool",
    "LoadTool",
    "ExecuteTool",
    "SignTool",
    "HelpTool",
]


# Factory function for creating tools with project path
def create_tool(tool_name: str, project_path: Optional[Path] = None) -> object:
    """
    Create a RYE tool instance with optional project path.

    Args:
        tool_name: Name of tool to create (search, load, execute, sign, help)
        project_path: Optional project path for tool

    Returns:
        Tool instance

    Raises:
        ValueError: If tool_name is unknown
    """
    Create a RYE tool instance with optional project path.

    Args:
        tool_name: Name of tool to create (search, load, execute, sign, help)
        project_path: Optional project path for the tool

    Returns:
        Tool instance

    Raises:
        ValueError: If tool_name is unknown
    """
    tool_map = {
        "search": SearchTool,
        "load": LoadTool,
        "execute": ExecuteTool,
        "sign": SignTool,
        "help": HelpTool,
    }

    tool_class = tool_map.get(tool_name.lower())
    if not tool_class:
        raise ValueError(f"Unknown tool: {tool_name}. Valid tools: {', '.join(tool_map.keys())}")

    return tool_class(project_path)


# Get MCP tool schema for RYE tools
def get_tool_schemas() -> Dict[str, Any]:
    """
    Get MCP tool schemas for all RYE tools.

    Returns:
        Dict mapping tool names to their MCP schemas
    """
    return {
        "search": {
            "name": "search",
            "description": (
                "Search for items with content understanding. "
                "Supports text and vector search with filters."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge", "all"],
                        "default": "all",
                        "description": "Type of item to search",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (natural language)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Project path (optional, uses current if not provided)",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["project", "user", "all"],
                        "default": "all",
                        "description": "Where to search from",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results to return",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["score", "date", "name"],
                        "default": "score",
                        "description": "Sort method",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags (optional)",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Filter by creation date (ISO format, optional)",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Filter by creation date (ISO format, optional)",
                    },
                },
            },
        },
        "load": {
            "name": "load",
            "description": (
                "Load items from source and optionally copy to destination. "
                "Supports project, user, and registry sources."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Type of item to load",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "ID/name of item to load",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Project path (optional, uses current if not provided)",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["project", "user", "registry"],
                        "default": "project",
                        "description": "Where to load from",
                    },
                    "destination": {
                        "type": "string",
                        "enum": ["project", "user"],
                        "description": "Where to copy to (optional)",
                    },
                    "version": {
                        "type": "string",
                        "description": "Specific version to load (registry only)",
                    },
                },
                "required": ["item_type", "item_id"],
            },
        },
        "execute": {
            "name": "execute",
            "description": (
                "Execute items with orchestration. "
                "For directives: Returns process steps. For tools: Executes via Lilux primitives."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Type of item to execute",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "ID/name of item to execute",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Project path (optional, uses current if not provided)",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Runtime parameters for the item",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": False,
                        "description": "Validate only without executing",
                    },
                },
                "required": ["item_type", "item_id"],
            },
        },
        "sign": {
            "name": "sign",
            "description": (
                "Validate and sign items. Computes unified integrity hash and adds signature. "
                "Supports re-signing with signature inclusion."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Type of item to sign",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "ID/name of item to sign",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Project path (optional, uses current if not provided)",
                    },
                    "location": {
                        "type": "string",
                        "enum": ["project", "user"],
                        "default": "project",
                        "description": "Where item is located",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category for new items (optional)",
                    },
                    "embed": {
                        "type": "boolean",
                        "default": True,
                        "description": "Auto-embed in vector store",
                    },
                },
                "required": ["item_type", "item_id"],
            },
        },
        "help": {
            "name": "help",
            "description": (
                "Get help and documentation for RYE tools and content. "
                "Lists available items with descriptions and usage examples."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Project path (optional, uses current if not provided)",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Specific topic to get help for (optional)",
                    },
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Specific item type to get help for (optional)",
                    },
                },
            },
        },
    }
