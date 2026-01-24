"""Execute tool - run, publish, delete, create, update items."""

import json
import logging
from mcp.types import Tool
from kiwi_mcp.tools.base import BaseTool


class ExecuteTool(BaseTool):
    """Execute operations on items."""

    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = logging.getLogger("ExecuteTool")

    @property
    def schema(self) -> Tool:
        return Tool(
            name="execute",
            description="""Execute operations on directives, tools, or knowledge.

All three types support the same 5 actions for consistency:
- run: Execute/load content (directive returns parsed XML, tool executes code, knowledge returns content for context)
- publish: Upload to registry with version (requires 'version' parameter)
- delete: Remove from local/registry (requires 'confirm': true for safety)
- create: Validate and sign existing file - file must exist first (validates XML for directive, Python for tool, frontmatter for knowledge)
- update: Validate and update existing item

Examples:
  directive.run: Returns parsed XML for agent to follow
  tool.run: Executes Python code and returns results
  knowledge.run: Returns knowledge content to inform decisions
  
  directive.create: Validates XML syntax and adds signature (file must exist)
  tool.create: Validates Python syntax and adds signature (file must exist)
  knowledge.create: Validates frontmatter and adds signature (file must exist)
  
Note: Use create_directive, create_script, or create_knowledge directives to create files first, then use create action to validate and sign.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "tool", "knowledge"],
                        "description": "Type of item to operate on",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["run", "publish", "delete", "create", "update"],
                        "description": "Action to perform (all 5 actions supported for all types)",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Item identifier (directive_name, tool_name, or zettel_id)",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Action-specific parameters. Common parameters listed below, but directives/scripts/knowledge can accept any parameters they define in their inputs.",
                        "additionalProperties": True,
                        "properties": {
                            "version": {
                                "type": "string",
                                "description": "Version for publish action (e.g., '1.0.0')",
                            },
                            "confirm": {
                                "type": "boolean",
                                "description": "Confirmation for delete action (must be true)",
                            },
                            "content": {
                                "type": "string",
                                "description": "Content for update actions only (create action expects file to exist first)",
                            },
                            "location": {
                                "type": "string",
                                "enum": ["project", "user"],
                                "description": "Save location for create action (project=.ai/ folder, user=home directory)",
                            },
                            "category": {
                                "type": "string",
                                "description": "Category folder for create action (optional)",
                            },
                            "source": {
                                "type": "string",
                                "description": "Source for delete/run actions (local|registry|all)",
                            },
                        },
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project root (where .ai/ folder lives). Example: '/home/user/myproject'",
                    },
                },
                "required": ["item_type", "action", "item_id", "project_path"],
            },
        )

    async def execute(self, arguments: dict) -> str:
        """Execute action with dynamic handler creation."""
        item_type = arguments.get("item_type")
        action = arguments.get("action")
        item_id = arguments.get("item_id")
        parameters = arguments.get("parameters", {})
        project_path = arguments.get("project_path")

        if not item_type or not action or not item_id:
            return self._format_response({"error": "item_type, action, and item_id are required"})

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
            result = await handler.execute(action, item_id, parameters)
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return self._format_response({"error": str(e)})
