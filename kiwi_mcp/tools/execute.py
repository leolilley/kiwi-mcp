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
            description="""Execute operations on directives, scripts, or knowledge.

All three types support the same 5 actions for consistency:
- run: Execute/load content (directive returns parsed XML, script executes code, knowledge returns content for context)
- publish: Upload to registry with version (requires 'version' parameter)
- delete: Remove from local/registry (requires 'confirm': true for safety)
- create: Validate and save new item - guards against malformed content (directive validates XML, script validates Python)
- update: Validate and update existing item

Examples:
  directive.run: Returns parsed XML for agent to follow
  script.run: Executes Python code and returns results
  knowledge.run: Returns knowledge content to inform decisions
  
  directive.create: Validates XML syntax before saving
  script.create: Validates Python syntax before saving
  knowledge.create: Creates entry with metadata
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["directive", "script", "knowledge"],
                        "description": "Type of item to operate on",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["run", "publish", "delete", "create", "update"],
                        "description": "Action to perform (all 5 actions supported for all types)",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Item identifier (directive_name, script_name, or zettel_id)",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Action-specific parameters",
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
                                "description": "Content for create/update actions (markdown+XML for directive, Python for script, markdown for knowledge)",
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
                        "description": "Absolute path to project root (where .ai/ folder lives). REQUIRED for: run, delete, update, create with location='project'. Example: '/home/user/myproject'",
                    },
                },
                "required": ["item_type", "action", "item_id"],
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
            return self._format_response(
                {"error": "item_type, action, and item_id are required"}
            )

        # Validate project_path for operations that need it
        location = parameters.get("location")
        source = parameters.get("source")
        
        # Actions that require project_path
        needs_project_path = (
            action in ("run", "delete", "update") or  # These always need project context
            location == "project" or  # Creating/saving to project
            source in ("local", "all")  # Working with local files
        )
        
        if needs_project_path and not project_path:
            return self._format_response({
                "error": f"project_path is REQUIRED for action='{action}'",
                "message": f"Please provide the absolute path to your project root (where .ai/ folder lives).",
                "hint": f"Add project_path parameter to your execute() call. Example: project_path='/home/user/myproject'"
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
            result = await handler.execute(action, item_id, parameters)
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return self._format_response({"error": str(e)})
