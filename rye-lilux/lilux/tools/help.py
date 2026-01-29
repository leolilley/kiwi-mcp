"""Help tool - usage guidance and troubleshooting."""

import json
import logging
from mcp.types import Tool
from lilux.tools.base import BaseTool


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
            description="Get help and usage guidance for the Lilux MCP",
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
                            "commands",
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
Lilux MCP - 5-Primitive Kernel

Lilux is a minimal MCP kernel providing 5 primitives for working with directives, tools, and knowledge:

5 Primitives:
- search: Find items by query across project, user, or registry
- load: Get or copy items between locations (project ↔ user ↔ registry)
- execute: Run directives, tools, and other items with parameters
- sign: Validate and cryptographically sign items
- help: Get help and usage guidance

Supported Item Types:
- directive: Workflow instructions (HOW to accomplish tasks)
- tool: Executable tools including Python scripts, APIs, Bash (DO the actual work)
- knowledge: Domain information, patterns, learnings

Use these 5 primitives to orchestrate complex workflows across your project.

For more help: help(topic="search"), help(topic="commands")
""",
            "search": """
search - Find items by query

Searches for directives, tools, and knowledge entries across project, user space, or registry.

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- query: Natural language search query or keywords (required)
- source: "project" | "user" | "registry" | "all" (default: "project")
- limit: Maximum results to return (default: 10)
- project_path: Path to project root (required for "project" source)

Returns: Array of matching items with title, ID, source, and relevance score

Example:
  search(item_type="directive", query="generate leads", source="project", project_path="/path")
  search(item_type="tool", query="scraper", limit=5)
""",
            "load": """
load - Get or copy items between locations

Loads item details from a source location. Optionally copies to a destination.

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- item_id: Item identifier to load (required)
- source: "project" | "user" | "registry" (required)
- destination: "project" | "user" (optional - copy to this location if specified)
- project_path: Path to project root (required)
- version: Specific version to load from registry (optional)

Returns: Full item details (content, metadata, signature status)

Read-only mode: If destination matches source or is omitted, just returns item details without copying.

Examples:
  load(item_type="directive", item_id="my_directive", source="project", project_path="/path")
  load(item_type="tool", item_id="scraper", source="registry", destination="project", project_path="/path")
""",
            "execute": """
execute - Run/execute an item

Executes a directive, tool, or other item with optional parameters.

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- item_id: Item identifier to execute (required)
- parameters: Execution parameters as object (optional)
- project_path: Path to project root (required)
- dry_run: Validate without executing (optional, default: false)

Returns: Execution result including status, output, and any generated artifacts

Examples:
  execute(item_type="directive", item_id="create_tool", project_path="/path")
  execute(item_type="tool", item_id="scraper", parameters={"url": "https://..."}, project_path="/path")
  execute(item_type="directive", item_id="workflow", dry_run=true, project_path="/path")
""",
            "sign": """
sign - Validate and cryptographically sign items

Validates item structure and applies a cryptographic signature.

Parameters:
- item_type: "directive" | "tool" | "knowledge" (required)
- item_id: Item identifier to sign (required, supports glob patterns like "demos/meta/*")
- project_path: Path to project root (required)
- parameters: Optional sign-specific parameters
  - location: "project" | "user" (where to save signed item)
  - category: Category folder (optional)

Returns: Signature details (hash, timestamp, valid status)

Notes:
- Always allows re-signing to update signatures after changes
- Supports batch signing with glob patterns
- Required before publishing items to registry

Examples:
  sign(item_type="directive", item_id="my_directive", project_path="/path")
  sign(item_type="directive", item_id="demos/meta/*", project_path="/path")  # batch
  sign(item_type="tool", item_id="scraper", project_path="/path", parameters={"location": "user"})
""",
            "commands": """
## Natural Language → MCP Tool Mapping

Map user commands to the 5 Lilux primitives.

| User Says | MCP Tool Call |
|-----------|---------------|
| "search for X" | `search(item_type="directive", query="X", project_path="...")` |
| "find tools about X" | `search(item_type="tool", query="X", project_path="...")` |
| "find knowledge about X" | `search(item_type="knowledge", query="X", project_path="...")` |
| "load directive X" | `load(item_type="directive", item_id="X", source="project", project_path="...")` |
| "get X from registry" | `load(item_type="directive", item_id="X", source="registry", project_path="...")` |
| "copy X to project" | `load(item_type="directive", item_id="X", source="registry", destination="project", project_path="...")` |
| "run directive X" | `execute(item_type="directive", item_id="X", project_path="...")` |
| "execute tool X" | `execute(item_type="tool", item_id="X", project_path="...")` |
| "sign directive X" | `sign(item_type="directive", item_id="X", project_path="...")` |
| "help with search" | `help(topic="search")` |
| "show commands" | `help(topic="commands")` |

### Modifiers & Parameters

| Modifier | Effect |
|----------|--------|
| "from user space" | `source="user"` |
| "from registry" | `source="registry"` |
| "to project" | `destination="project"` |
| "to user space" | `destination="user"` |
| "dry run" | `parameters={"dry_run": true}` |
| "in registry" | `source="registry"` |
| "batch" or "glob pattern" | `item_id="pattern/*"` for batch operations |

### Item Types

- `item_type="directive"` - Workflow instructions
- `item_type="tool"` - Executable tools
- `item_type="knowledge"` - Knowledge entries

### Common Patterns

**Search & Execute:**
1. `search(item_type="directive", query="...", project_path="...")`
2. `load(item_type="directive", item_id="result_id", source="project", project_path="...")`
3. `execute(item_type="directive", item_id="result_id", project_path="...")`

**Load & Sign:**
1. `load(item_type="directive", item_id="X", source="registry", destination="project", project_path="...")`
2. `sign(item_type="directive", item_id="X", project_path="...")`
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
