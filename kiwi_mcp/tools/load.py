"""Load tool - load/inspect items or copy between locations."""

import json
import logging
from mcp.types import Tool
from kiwi_mcp.tools.base import BaseTool


class LoadTool(BaseTool):
    """Load items for inspection or copy between locations.
    
    When destination is omitted or equals source: read-only inspection (returns content).
    When destination differs from source: copies the item to destination.
    """

    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = logging.getLogger("LoadTool")

    @property
    def schema(self) -> Tool:
        return Tool(
            name="load",
            description="""Load items for inspection or copy between locations.

When destination is omitted: Read-only mode - returns item content without copying.
When destination equals source: Same as above - just returns content.
When destination differs from source: Copies the item to destination location.

Use cases:
- Inspect a directive/script before running it: load(source="project")
- Download from registry to project: load(source="registry", destination="project")
- Copy from user space to project: load(source="user", destination="project")
""",
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
                        "description": "Where to load from: 'project' (local .ai/), 'user' (~/.ai/), or 'registry' (remote Supabase)",
                    },
                    "destination": {
                        "type": "string",
                        "enum": ["project", "user"],
                        "description": "Where to copy to (optional). If omitted or same as source, just returns content without copying.",
                    },
                    "version": {
                        "type": "string",
                        "description": "Specific version to load (registry only)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project root (where .ai/ folder lives). Example: '/home/user/myproject'",
                    },
                },
                "required": ["item_type", "item_id", "source", "project_path"],
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
            return self._format_response({"error": "item_type and item_id are required"})

        if not source:
            return self._format_response(
                {
                    "error": "source is REQUIRED",
                    "message": "Specify source='project', source='user', or source='registry'",
                }
            )

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

            # Call load with appropriate parameters based on item type
            if item_type == "knowledge":
                include_relationships = arguments.get("include_relationships", False)
                result = await handler.load(
                    item_id,
                    source=source,
                    destination=destination,  # Can be None for read-only
                    include_relationships=include_relationships,
                )
            else:  # directive or script
                result = await handler.load(
                    item_id, source=source, destination=destination, version=version
                )
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            return self._format_response({"error": str(e)})
