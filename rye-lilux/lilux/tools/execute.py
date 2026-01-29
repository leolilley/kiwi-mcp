"""Execute tool - execute directives, tools, or knowledge items."""

import json
import logging
from mcp.types import Tool
from lilux.tools.base import BaseTool


class ExecuteTool(BaseTool):
    """Execute directives, tools, or knowledge items."""

    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = logging.getLogger("ExecuteTool")

    @property
    def schema(self) -> Tool:
        return Tool(
            name="execute",
            description="""Execute a directive, tool, or knowledge item.

- directive: Returns parsed XML for agent to follow
- tool: Executes tool code and returns results
- knowledge: Returns knowledge content to inform decisions

Examples:
  execute(item_type='directive', item_id='create_tool', project_path='/path/to/project')
  execute(item_type='tool', item_id='scraper', project_path='/path/to/project', parameters={'url': 'https://...'})
  execute(item_type='knowledge', item_id='api_patterns', project_path='/path/to/project')
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Type of item to execute",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Item identifier (directive_name, tool_name, or id)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project root (where .ai/ folder lives). Example: '/home/user/myproject'",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Execution parameters. Directives/tools/knowledge can accept any parameters they define in their inputs.",
                        "additionalProperties": True,
                        "properties": {
                            "dry_run": {
                                "type": "boolean",
                                "description": "Validate without executing (tools only)",
                            },
                        },
                    },
                },
                "required": ["item_type", "item_id", "project_path"],
            },
        )

    async def execute(self, arguments: dict) -> str:
        """Execute item with dynamic handler creation."""
        item_type = arguments.get("item_type")
        item_id = arguments.get("item_id")
        parameters = arguments.get("parameters", {})
        project_path = arguments.get("project_path")

        if not item_type or not item_id:
            return self._format_response({"error": "item_type and item_id are required"})

        if not project_path:
            return self._format_response(
                {
                    "error": "project_path is REQUIRED",
                    "message": "Please provide the absolute path to your project root (where .ai/ folder lives).",
                    "hint": "Add project_path parameter. Example: project_path='/home/user/myproject'",
                }
            )

        try:
            from lilux.handlers.directive.handler import DirectiveHandler
            from lilux.handlers.tool.handler import ToolHandler
            from lilux.handlers.knowledge.handler import KnowledgeHandler

            handlers = {
                "directive": DirectiveHandler,
                "tool": ToolHandler,
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
            result = await handler.execute(item_id, parameters)
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return self._format_response({"error": str(e)})
