"""RYE Help Tool - Intelligent help with content understanding.

Uses Lilux primitives for path resolution but adds:
- Content listing and categorization
- Tool descriptions from XML/frontmatter
- Usage examples for each tool
- Protected vs shadowable content indication
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json

# Import Lilux primitives dynamically
from lilux.utils.resolvers import DirectiveResolver, ToolResolver, KnowledgeResolver, get_user_space
from lilux.utils.logger import get_logger


class HelpTool:
    """Intelligent help tool with content understanding."""

    def __init__(self, project_path: Optional[str] = None):
        """Initialize help tool with project path."""
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.logger = get_logger("rye_help")

        # Initialize resolvers for each item type
        self.directive_resolver = DirectiveResolver(self.project_path)
        self.tool_resolver = ToolResolver(self.project_path)
        self.knowledge_resolver = KnowledgeResolver(self.project_path)

        # Protected paths knowledge (RYE intelligence)
        self.PROTECTED_PATHS = ["core", "system", "lilux"]

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute help with RYE intelligence.

        Args:
            arguments: Help parameters
                - project_path: Project path (optional, uses current if not provided)
                - topic: Specific topic to get help for (optional)
                - item_type: Specific item type to get help for (optional)

        Returns:
            Dict with help content and RYE-curated descriptions
        """
        try:
            # Extract arguments
            project_path = Path(arguments.get("project_path", self.project_path))
            topic = arguments.get("topic")
            item_type = arguments.get("item_type")

            # Update project path if changed
            self.project_path = project_path
            self.directive_resolver = DirectiveResolver(project_path)
            self.tool_resolver = ToolResolver(project_path)
            self.knowledge_resolver = KnowledgeResolver(project_path)

            # Route to appropriate help
            if topic:
                return await self._get_topic_help(topic)
            elif item_type:
                return await self._get_item_type_help(item_type)
            else:
                return await self._get_general_help()
        except Exception as e:
            self.logger.error(f"Help failed: {e}")
            return {"error": str(e), "message": "Failed to generate help"}

    async def _get_general_help(self) -> Dict[str, Any]:
        """
        Get general help information (RYE intelligence).

        Shows:
        - All available tools
        - All item types
        - All available actions
        - Usage examples
        """
        # Get counts of each item type
        items = await self._list_all_items()

        return {
            "topic": "general",
            "description": "RYE - AI operating system running on Lilux microkernel",
            "tools": self._get_tool_descriptions(),
            "item_types": {
                "directive": {
                    "description": "Workflow definitions that tell the agent HOW to accomplish tasks",
                    "count": items.get("directive_count", 0),
                },
                "tool": {
                    "description": "Executable scripts that DO the actual work (subprocess, HTTP, etc.)",
                    "count": items.get("tool_count", 0),
                },
                "knowledge": {
                    "description": "Domain information, patterns, learnings, and documentation",
                    "count": items.get("knowledge_count", 0),
                },
            },
            "actions": self._get_action_descriptions(),
            "usage_examples": self._get_usage_examples(),
            "protected_content": {
                "description": "RYE core content that cannot be overridden",
                "protected_paths": self.PROTECTED_PATHS,
            },
        }

    async def _get_topic_help(self, topic: str) -> Dict[str, Any]:
        """
        Get help for a specific topic (RYE intelligence).

        Topics:
        - tool: Specific tool help
        - item_type: Help for specific item type
        - actions: Help for available actions
        - architecture: Lilux/RYE architecture
        - protected: Information about protected content
        """
        topic_lower = topic.lower()

        if topic_lower in ["directive", "tool", "knowledge"]:
            return await self._get_item_type_help(topic_lower)
        elif topic_lower == "actions":
            return {
                "topic": "actions",
                "description": "Available actions for RYE tools",
                "actions": self._get_action_descriptions(),
            }
        elif topic_lower == "architecture":
            return {
                "topic": "architecture",
                "description": "Lilux/RYE microkernel + OS architecture",
                "summary": {
                    "lilux": "Microkernel - provides dumb execution primitives (subprocess, HTTP, chains, locks, auth)",
                    "rye": "Operating System - provides intelligent MCP tools that understand content shapes",
                },
                "separation": "RYE uses Lilux primitives for execution but adds intelligence on top",
            }
        elif topic_lower == "protected":
            return {
                "topic": "protected_content",
                "description": "RYE core content that cannot be overridden",
                "protected_paths": self.PROTECTED_PATHS,
                "note": "User space and project space can shadow RYE core content, but cannot override it",
            }
        else:
            return {
                "error": f"Unknown topic: {topic}",
                "valid_topics": [
                    "directive",
                    "tool",
                    "knowledge",
                    "actions",
                    "architecture",
                    "protected",
                ],
            }

    async def _get_item_type_help(self, item_type: str) -> Dict[str, Any]:
        """
        Get help for a specific item type (RYE intelligence).

        Lists all items of that type with descriptions.
        """
        items = await self._list_items_of_type(item_type)

        return {
            "topic": item_type,
            "description": self._get_item_type_description(item_type),
            "items": items,
            "total": len(items),
        }

    async def _list_all_items(self) -> Dict[str, Any]:
        """List all items of all types (RYE intelligence)."""
        result = {}

        for item_type in ["directive", "tool", "knowledge"]:
            items = await self._list_items_of_type(item_type)
            result[f"{item_type}_count"] = len(items)

        return result

    async def _list_items_of_type(self, item_type: str) -> List[Dict[str, Any]]:
        """
        List all items of a specific type (RYE intelligence).

        Returns:
            List of items with enriched metadata
        """
        items = []

        # Get resolver for item type
        resolver = self._get_resolver(item_type)
        if not resolver:
            return []

        # Search both project and user spaces
        search_paths = [
            self.project_path / ".ai",
            get_user_space(),
        ]

        for search_base in search_paths:
            type_dir = search_base / self._get_type_dir(item_type)
            if not type_dir.exists():
                continue

            # List all files in directory
            for file_path in type_dir.rglob("*"):
                if file_path.is_file():
                    item_info = await self._extract_item_info(file_path, item_type)
                    if item_info:
                        items.append(item_info)

        return items

    async def _extract_item_info(self, file_path: Path, item_type: str) -> Optional[Dict[str, Any]]:
        """
        Extract item information with RYE intelligence.

        Extracts:
        - Title/name from content
        - Description from content
        - Protected status
        - Source (project/user)
        """
        try:
            # Determine source
            source = "project" if ".ai/" in str(file_path) else "user"

            # Extract title/description based on item type
            if item_type == "directive":
                from lilux.utils.parsers import parse_directive_file

                data = parse_directive_file(file_path)
                title = data.get("description", "")
                description = data.get("description", "")
                protected = self._is_protected(file_path, "directive")
            elif item_type == "tool":
                from lilux.schemas import extract_tool_metadata

                meta = extract_tool_metadata(file_path, self.project_path)
                title = meta.get("name", "")
                description = meta.get("description", "")
                protected = self._is_protected(file_path, "tool")
            elif item_type == "knowledge":
                from lilux.utils.parsers import parse_knowledge_entry

                data = parse_knowledge_entry(file_path)
                title = data.get("title", "")
                description = data.get("title", "")
                protected = self._is_protected(file_path, "knowledge")
            else:
                return None

            return {
                "name": file_path.stem,
                "path": str(file_path),
                "item_type": item_type,
                "title": title,
                "description": description,
                "source": source,
                "protected": protected,
            }
        except Exception as e:
            self.logger.warning(f"Failed to extract info from {file_path}: {e}")
            return None

    def _get_resolver(self, item_type: str):
        """Get appropriate resolver for item type."""
        if item_type == "directive":
            return self.directive_resolver
        elif item_type == "tool":
            return self.tool_resolver
        elif item_type == "knowledge":
            return self.knowledge_resolver
        return None

    def _get_type_dir(self, item_type: str) -> str:
        """Get directory name for item type (RYE knowledge)."""
        type_dirs = {
            "directive": "directives",
            "tool": "tools",
            "knowledge": "knowledge",
        }
        return type_dirs.get(item_type, "items")

    def _is_protected(self, file_path: Path, item_type: str) -> bool:
        """
        Check if item is protected RYE content (RYE knowledge).

        Protected items are in core/ or system/ subdirectories.
        """
        path_str = str(file_path)

        for protected in self.PROTECTED_PATHS:
            if f"/{protected}/" in path_str:
                return True

        return False

    def _get_item_type_description(self, item_type: str) -> str:
        """Get description for item type (RYE intelligence)."""
        descriptions = {
            "directive": (
                "Directives are XML workflows that tell the agent HOW to accomplish tasks. "
                "They define process steps, inputs, and permissions."
            ),
            "tool": (
                "Tools are executable scripts that DO the actual work. "
                "They use Lilux primitives (subprocess, HTTP, chains, etc.) for execution."
            ),
            "knowledge": (
                "Knowledge entries are domain information stored as markdown with YAML frontmatter. "
                "They contain patterns, learnings, API facts, and documentation."
            ),
        }
        return descriptions.get(item_type, "")

    def _get_tool_descriptions(self) -> Dict[str, Any]:
        """Get descriptions for all RYE tools (RYE intelligence)."""
        return {
            "search": {
                "description": (
                    "Search for items with content understanding. "
                    "Supports text and vector search with filters."
                ),
                "usage": "search(item_type='directive', query='lead generation', limit=10)",
                "parameters": [
                    "item_type: directive, tool, or knowledge",
                    "query: Search query (natural language)",
                    "source: project, user, or all (default: all)",
                    "limit: Maximum results (default: 10)",
                    "sort_by: score, date, or name (default: score)",
                    "category: Filter by category (optional)",
                    "tags: Filter by tags (optional)",
                    "date_from: Filter by creation date (optional)",
                    "date_to: Filter by creation date (optional)",
                ],
            },
            "load": {
                "description": (
                    "Load items from source and optionally copy to destination. "
                    "Supports project, user, and registry sources."
                ),
                "usage": "load(item_type='tool', item_id='scraper', source='registry', destination='project')",
                "parameters": [
                    "item_type: directive, tool, or knowledge",
                    "item_id: ID/name of item to load",
                    "project_path: Project path (optional)",
                    "source: Where to load from - project, user, or registry (default: project)",
                    "destination: Where to copy to (optional). If same as source, read-only mode.",
                    "version: Specific version to load (registry only)",
                ],
            },
            "execute": {
                "description": (
                    "Execute items with orchestration. "
                    "For directives: Returns process steps. For tools: Executes via Lilux primitives."
                ),
                "usage": "execute(item_type='tool', item_id='scraper', parameters={'url': 'https://example.com'})",
                "parameters": [
                    "item_type: directive, tool, or knowledge",
                    "item_id: ID/name of item to execute",
                    "project_path: Project path (optional)",
                    "parameters: Runtime parameters for the item",
                    "dry_run: If True, validate only without executing",
                ],
            },
            "sign": {
                "description": (
                    "Validate and sign items. Computes unified integrity hash and adds signature. "
                    "Supports re-signing with signature inclusion."
                ),
                "usage": "sign(item_type='directive', item_id='bootstrap', location='project')",
                "parameters": [
                    "item_type: directive, tool, or knowledge",
                    "item_id: ID/name of item to sign",
                    "project_path: Project path (optional)",
                    "location: project or user (default: project)",
                    "category: Category for new items (optional)",
                    "embed: Auto-embed in vector store (default: True)",
                ],
            },
            "help": {
                "description": (
                    "Get help and documentation for RYE tools and content. "
                    "Lists available items with descriptions and usage examples."
                ),
                "usage": "help(topic='actions') or help(item_type='directive')",
                "parameters": [
                    "project_path: Project path (optional)",
                    "topic: Specific topic to get help for (optional)",
                    "item_type: Specific item type to get help for (optional)",
                ],
            },
        }

    def _get_action_descriptions(self) -> Dict[str, Any]:
        """Get descriptions for available actions (RYE intelligence)."""
        return {
            "search": "Find items by query with filters",
            "load": "Load items from source and optionally copy to destination",
            "execute": "Execute items (directives return steps, tools execute via primitives)",
            "sign": "Validate and sign items with integrity hash",
            "run": "Alias for execute (same functionality)",
            "create": "Create new items (not yet implemented)",
            "update": "Update existing items (not yet implemented)",
            "delete": "Delete items (not yet implemented)",
            "publish": "Publish items to registry (not yet implemented)",
        }

    def _get_usage_examples(self) -> List[str]:
        """Get usage examples for RYE tools (RYE intelligence)."""
        return [
            "Search for directives:",
            "  search(item_type='directive', query='init')",
            "",
            "Load a tool from registry:",
            "  load(item_type='tool', item_id='scraper', source='registry', destination='project')",
            "",
            "Execute a directive:",
            "  execute(item_type='directive', item_id='bootstrap', parameters={'project_path': '.'})",
            "",
            "Sign a knowledge entry:",
            "  sign(item_type='knowledge', item_id='api-patterns', location='project')",
            "",
            "Get help for specific item type:",
            "  help(item_type='tool')",
            "",
            "Get help for architecture:",
            "  help(topic='architecture')",
        ]
