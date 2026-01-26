"""Help tool - usage guidance and troubleshooting."""

import json
import logging
from mcp.types import Tool
from kiwi_mcp.tools.base import BaseTool


class HelpTool(BaseTool):
    """Provide usage guidance and help."""
    
    def __init__(self, registry=None):
        """Initialize with optional registry reference."""
        self.registry = registry
        self.logger = logging.getLogger("HelpTool")

    @property
    def schema(self) -> Tool:
        return Tool(
            name="help",
            description="Get help and usage guidance for the Kiwi MCP",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": [
                            "overview",
                            "search",
                            "load",
                            "execute",
                            "directives",
                            "tools",
                            "knowledge",
                        ],
                        "description": "Help topic",
                    },
                },
            },
        )

    async def execute(self, arguments: dict) -> str:
        """Execute help."""
        topic = arguments.get("topic", "overview")

        help_topics = {
            "overview": """
Kiwi MCP - Unified MCP for directives, tools, and knowledge

This MCP provides 4 tools:
- search: Find items across all types
- load: Download from registry to local
- execute: Run, publish, delete, sign, link
- help: Get help and guidance

Types supported:
- directive: Workflow definitions and automation steps
- tool: Executable tools (Python, Bash, API, etc.)
- knowledge: Knowledge base entries

For more help, try: help(topic="search")
""",
            "search": """
search - Find items across local or registry

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- query: Search query as natural language or keywords (required)
- source: "local" | "registry" | "all" (default: "local")
- limit: Max results (default: 10)

Example:
search(item_type="directive", query="lead generation", source="registry")
""",
            "load": """
load - Download items from registry to local storage

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- item_id: Item ID to load (required)
- destination: "project" | "user" (default: "project")
- version: Specific version (optional)
- project_path: Path to project (required for destination="project")

Example:
load(item_type="directive", item_id="my_directive", destination="project")
""",
            "execute": """
execute - Run, publish, delete, sign, or link items

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- action: "run" | "publish" | "delete" | "sign" | "link" (required)
- item_id: Item ID (required)
- parameters: Action-specific parameters (object)
- project_path: Path to project (for project operations)

Actions:
- run: Execute/run the item
- publish: Publish to registry
- delete: Delete item
- sign: Validate and sign item (always allows re-signing)
- link: Create relationship between items
""",
        }

        content = help_topics.get(topic, help_topics["overview"])

        return self._format_response(
            {
                "status": "help",
                "topic": topic,
                "content": content,
            }
        )
