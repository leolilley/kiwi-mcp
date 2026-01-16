"""Search tool - unified search across directives, scripts, and knowledge."""

import json
from mcp.types import Tool
from kiwi_mcp.tools.base import BaseTool
from kiwi_mcp.utils.logger import get_logger


class SearchTool(BaseTool):
    """Search for items across all Kiwi types."""

    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = get_logger("search_tool")

    @property
    def schema(self) -> Tool:
        return Tool(
            name="search",
            description="Search for directives, scripts, or knowledge entries",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "script", "knowledge"],
                        "description": "Type of item to search for",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (natural language or keywords)",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["local", "registry", "all"],
                        "default": "local",
                        "description": "Search source",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results to return",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project root (where .ai/ folder lives). Example: '/home/user/myproject'",
                    },
                },
                "required": ["item_type", "query", "project_path"],
            },
        )

    async def execute(self, arguments: dict) -> str:
        """Execute search with dynamic handler creation."""
        item_type = arguments.get("item_type")
        query = arguments.get("query")
        source = arguments.get("source", "local")
        limit = arguments.get("limit", 10)
        project_path = arguments.get("project_path")

        self.logger.info(
            f"SearchTool.execute: item_type={item_type}, query={query}, source={source}"
        )

        if not item_type or not query:
            return self._format_response({"error": "item_type and query are required"})

        if not project_path:
            return self._format_response(
                {
                    "error": "project_path is REQUIRED",
                    "message": "Please provide the absolute path to your project root (where .ai/ folder lives).",
                    "hint": "Add project_path parameter. Example: project_path='/home/user/myproject'",
                }
            )

        # Create handler dynamically with project_path
        try:
            from kiwi_mcp.handlers.directive.handler import DirectiveHandler
            from kiwi_mcp.handlers.script.handler import ScriptHandler
            from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler

            handlers = {
                "directive": DirectiveHandler,
                "script": ScriptHandler,
                "knowledge": KnowledgeHandler,
            }

            handler_class = handlers.get(item_type)
            if not handler_class:
                return self._format_response(
                    {
                        "error": f"Unknown item_type: {item_type}",
                        "supported_types": list(handlers.keys()),
                    }
                )

            handler = handler_class(project_path=project_path)
            result = await handler.search(query, source=source, limit=limit)
            self.logger.info(
                f"SearchTool result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}"
            )
            self.logger.info(
                f"SearchTool result total: {result.get('total', 'N/A') if isinstance(result, dict) else 'N/A'}"
            )
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return self._format_response({"error": str(e)})
