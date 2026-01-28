"""Sign tool - validate and sign items."""

import asyncio
import json
import logging
from pathlib import Path
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

Batch signing: Use glob pattern in item_id (e.g., 'demos/meta/*') to sign multiple items.

Examples:
  sign(item_type='directive', item_id='my_directive', project_path='/path/to/project')
  sign(item_type='directive', item_id='demos/meta/*', project_path='/path/to/project')  # batch
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
                        "description": "Item identifier or glob pattern (e.g., 'demos/meta/*' for batch)",
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

    def _is_glob_pattern(self, item_id: str) -> bool:
        """Check if item_id is a glob pattern."""
        return "*" in item_id or "?" in item_id

    def _resolve_glob_items(self, item_type: str, pattern: str, project_path: str) -> list[str]:
        """Resolve glob pattern to list of item IDs."""
        project = Path(project_path)
        
        # Determine base directory based on item type
        type_dirs = {
            "directive": "directives",
            "tool": "tools", 
            "knowledge": "knowledge",
        }
        base_dir = project / ".ai" / type_dirs.get(item_type, item_type + "s")
        
        # File extensions
        extensions = {
            "directive": ".md",
            "tool": ".py",
            "knowledge": ".md",
        }
        ext = extensions.get(item_type, ".md")
        
        # Resolve glob - pattern can be "demos/meta/*" or just "*"
        if "/" in pattern:
            # Pattern includes subdirectory
            glob_pattern = f"{pattern}{ext}" if not pattern.endswith(ext) else pattern
        else:
            # Simple pattern like "*" - search recursively
            glob_pattern = f"**/{pattern}{ext}" if pattern != "*" else f"**/*{ext}"
        
        items = []
        for path in base_dir.glob(glob_pattern):
            if path.is_file():
                # Extract item_id (filename without extension)
                items.append(path.stem)
        
        return items

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

            # Check for batch signing (glob pattern)
            if self._is_glob_pattern(item_id):
                items = self._resolve_glob_items(item_type, item_id, project_path)
                
                if not items:
                    return self._format_response({
                        "error": f"No {item_type}s found matching pattern: {item_id}",
                        "searched_in": str(Path(project_path) / ".ai"),
                    })
                
                # Sign all items
                results = {"signed": [], "failed": [], "total": len(items)}
                
                for item in items:
                    try:
                        result = await handler.sign(item, parameters)
                        if result.get("error"):
                            results["failed"].append({
                                "item": item,
                                "error": result.get("error"),
                                "details": result.get("details", [])[:2],  # Limit detail size
                            })
                        else:
                            results["signed"].append(item)
                    except Exception as e:
                        results["failed"].append({"item": item, "error": str(e)})
                
                results["summary"] = f"Signed {len(results['signed'])}/{results['total']} items"
                if results["failed"]:
                    results["summary"] += f", {len(results['failed'])} failed"
                
                return self._format_response(results)
            
            # Single item signing
            result = await handler.sign(item_id, parameters)
            return self._format_response(result)
        except Exception as e:
            self.logger.error(f"Sign failed: {e}")
            return self._format_response({"error": str(e)})
