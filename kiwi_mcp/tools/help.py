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
                            "sign",
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

This MCP provides 5 tools:
- search: Find items across all types
- load: Download/copy items between locations
- execute: Run/execute items
- sign: Validate and sign items
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
- source: "project" | "user" | "all" (default: "project")
- limit: Max results (default: 10)

Example:
search(item_type="directive", query="lead generation", source="project")
""",
            "load": """
load - Download/copy items between locations

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- item_id: Item ID to load (required)
- source: "project" | "user" (where to load from)
- destination: "project" | "user" (where to copy to, optional)
- project_path: Path to project (required)

Example:
load(item_type="directive", item_id="my_directive", source="user", destination="project")
""",
            "execute": """
execute - Run/execute an item

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- item_id: Item ID to execute (required)
- parameters: Execution parameters (object)
- project_path: Path to project (required)

Examples:
execute(item_type="directive", item_id="create_tool", project_path="/path/to/project")
execute(item_type="tool", item_id="scraper", parameters={"url": "..."}, project_path="/path/to/project")
""",
            "sign": """
sign - Validate and sign an item

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- item_id: Item ID to sign (required)
- project_path: Path to project (required)
- parameters: Sign parameters (location, category)

Always allows re-signing to update signatures after changes.

Example:
sign(item_type="directive", item_id="my_directive", project_path="/path/to/project")
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
