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
            description="Load items from specified source (project, user, or registry)",
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
                    "source": {
                        "type": "string",
                        "enum": ["project", "user", "registry"],
                        "description": "Where to load from: 'project' (local .ai/), 'user' (mcp env variable), or 'registry' (remote Supabase)",
                    },
                    "destination": {
                        "type": "string",
                        "enum": ["project", "user"],
                        "description": "Where to save/return from: 'project' or 'user' (REQUIRED)",
                    },
                    "version": {
                        "type": "string",
                        "description": "Specific version to load (registry only)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project root (where .ai/ folder lives). REQUIRED for source='project' or destination='project'. Example: '/home/user/myproject'",
                    },
                },
                "required": ["item_type", "item_id", "source", "destination"],
            },
        )

    async def execute(self, arguments: dict) -> str:
        """Execute load with dynamic handler creation."""
        item_type = arguments.get("item_type")
        item_id = arguments.get("item_id")
        source = arguments.get("source")
        destination = arguments.get("destination")
        version = arguments.get("version")
        project_path = arguments.get("project_path")

        # Validate required parameters
        if not item_type or not item_id:
            return self._format_response(
                {"error": "item_type and item_id are required"}
            )
        
        if not source:
            return self._format_response({
                "error": "source is REQUIRED",
                "message": "Specify source='project', source='user', or source='registry'"
            })
        
        if not destination:
            return self._format_response({
                "error": "destination is REQUIRED",
                "message": "Specify destination='project' or destination='user'"
            })

        # Validate project_path when needed
        if (source == "project" or destination == "project") and not project_path:
            return self._format_response({
                "error": "project_path is REQUIRED for source='project' or destination='project'",
                "message": "Please provide the absolute path to your project root (where .ai/ folder lives).",
                "hint": "Add project_path parameter. Example: project_path='/home/user/myproject'"
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
            
            # Call load with appropriate parameters based on item type
            if item_type == "knowledge":
                include_relationships = arguments.get("include_relationships", False)
                result = await handler.load(
                    item_id,
                    source=source,
                    destination=destination,
                    include_relationships=include_relationships
                )
            else:  # directive or script
                result = await handler.load(
                    item_id,
                    source=source,
                    destination=destination,
                    version=version
                )
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            return self._format_response({"error": str(e)})
