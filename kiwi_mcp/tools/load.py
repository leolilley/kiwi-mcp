"""Load tool - download from registry to local."""

import json
import logging
from mcp.types import Tool
from kiwi_mcp.tools.base import BaseTool


class LoadTool(BaseTool):
    """Load items from registry to local storage."""
    
    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = logging.getLogger("LoadTool")

    @property
    def schema(self) -> Tool:
        return Tool(
            name="load",
            description="Load/download items from registry to local storage",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "script", "knowledge"],
                        "description": "Type of item",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Item ID to load",
                    },
                    "destination": {
                        "type": "string",
                        "enum": ["project", "user"],
                        "default": "project",
                        "description": "Where to save the item",
                    },
                    "version": {
                        "type": "string",
                        "description": "Specific version to load (optional)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project root (where .ai/ folder lives). Required for destination='project'. Example: '/home/user/myproject'",
                    },
                },
                "required": ["item_type", "item_id"],
            },
        )

    async def execute(self, arguments: dict) -> str:
        """Execute load with dynamic handler creation."""
        item_type = arguments.get("item_type")
        item_id = arguments.get("item_id")
        destination = arguments.get("destination", "project")
        version = arguments.get("version")
        project_path = arguments.get("project_path")

        if not item_type or not item_id:
            return self._format_response(
                {"error": "item_type and item_id are required"}
            )

        # Validate project_path for project destination
        if destination == "project" and not project_path:
            return self._format_response({
                "error": "project_path is required when destination='project'",
                "message": "Please provide the absolute path to your project root (where .ai/ folder lives)."
            })

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
                return self._format_response({
                    "error": f"Unknown item_type: {item_type}",
                    "supported_types": list(handlers.keys())
                })
            
            handler = handler_class(project_path=project_path)
            result = await handler.load(item_id, destination=destination, version=version)
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            return self._format_response({"error": str(e)})
