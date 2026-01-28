"""Sign tool - validate and sign items."""

import json
import logging
from mcp.types import Tool
from kiwi_mcp.tools.base import BaseTool


class SignTool(BaseTool):
    """Validate and sign directives, tools, or knowledge."""

    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = logging.getLogger("SignTool")

    @property
    def schema(self) -> Tool:
        return Tool(
            name="sign",
            description="""Validate and sign a directive, tool, or knowledge file.

File must exist first. Validates content and adds cryptographic signature:
- directive: Validates XML syntax and structure
- tool: Validates code and metadata
- knowledge: Validates frontmatter

Always allows re-signing to update signatures after changes.

Examples:
  sign(item_type='directive', item_id='my_directive', project_path='/path/to/project')
  sign(item_type='tool', item_id='my_tool', project_path='/path/to/project', parameters={'location': 'user'})
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Type of item to sign",
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
                        "description": "Sign-specific parameters",
                        "additionalProperties": True,
                        "properties": {
                            "location": {
                                "type": "string",
                                "enum": ["project", "user"],
                                "description": "Save location (project=.ai/ folder, user=home directory)",
                            },
                            "category": {
                                "type": "string",
                                "description": "Category folder (optional)",
                            },
                        },
                    },
                },
                "required": ["item_type", "item_id", "project_path"],
            },
        )

    async def execute(self, arguments: dict) -> str:
        """Sign an item with dynamic handler creation."""
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
            from kiwi_mcp.handlers.directive.handler import DirectiveHandler
            from kiwi_mcp.handlers.tool.handler import ToolHandler
            from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler

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
            result = await handler.sign(item_id, parameters)
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Sign failed: {e}")
            return self._format_response({"error": str(e)})
