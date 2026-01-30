"""RYE Load Tool - Intelligent content loading with protection.

Uses Lilux primitives for file I/O but adds:
- Source/destination resolution (project/user/registry)
- Registry integration (HTTP download)
- Content validation
- Protection enforcement (core RYE content cannot be overridden)
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Literal, Optional
import json

# Import Lilux primitives dynamically
from lilux.utils.resolvers import DirectiveResolver, ToolResolver, KnowledgeResolver, get_user_space
from lilux.utils.logger import get_logger


class LoadTool:
    """Intelligent load tool with source/destination resolution."""

    # Registry URL mapping (RYE intelligence)
    REGISTRY_URLS = {
        "directive": "https://registry.kiwi-mcp.org/directives",
        "tool": "https://registry.kiwi-mcp.org/tools",
        "knowledge": "https://registry.kiwi-mcp.org/knowledge",
    }

    # Protected paths that cannot be overridden (RYE knowledge)
    PROTECTED_PATHS = {
        "core",  # Core directives
        "system",  # System tools
    }

    def __init__(self, project_path: Optional[str] = None):
        """Initialize load tool with project path."""
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.logger = get_logger("rye_load")

        # Initialize resolvers for each item type
        self.directive_resolver = DirectiveResolver(self.project_path)
        self.tool_resolver = ToolResolver(self.project_path)
        self.knowledge_resolver = KnowledgeResolver(self.project_path)

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute load with RYE intelligence.

        Args:
            arguments: Load parameters
                - item_type: "directive", "tool", or "knowledge"
                - item_id: ID/name of item to load
                - project_path: Project path (optional, uses current if not provided)
                - source: Where to load from - "project", "user", or "registry"
                - destination: Where to copy to (optional). If same as source, read-only mode.
                - version: Specific version to load (registry only)

        Returns:
            Dict with loaded item data and validation status
        """
        try:
            # Extract arguments
            item_type = arguments.get("item_type")
            item_id = arguments.get("item_id")
            project_path = Path(arguments.get("project_path", self.project_path))
            source = arguments.get("source", "project")
            destination = arguments.get("destination")
            version = arguments.get("version")

            if not item_type or not item_id:
                return {"error": "item_type and item_id are required"}

            # RYE INTELLIGENCE: Check protection
            if self._is_protected_path(item_id):
                return {
                    "error": f"Cannot load or override protected RYE content: {item_id}",
                    "protected": True,
                    "suggestion": "User space and project space can shadow RYE core content, but cannot override it",
                }

            # Update resolvers if project_path changed
            self.project_path = project_path
            self.directive_resolver = DirectiveResolver(project_path)
            self.tool_resolver = ToolResolver(project_path)
            self.knowledge_resolver = KnowledgeResolver(project_path)

            # Route to appropriate loader
            if item_type == "directive":
                return await self._load_directive(item_id, source, destination, version)
            elif item_type == "tool":
                return await self._load_tool(item_id, source, destination, version)
            elif item_type == "knowledge":
                return await self._load_knowledge(item_id, source, destination)
            else:
                return {
                    "error": f"Unknown item_type: {item_type}",
                    "valid_types": ["directive", "tool", "knowledge"],
                }
        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            return {"error": str(e), "message": f"Failed to load {item_id}"}

    async def _load_directive(
        self,
        directive_name: str,
        source: str,
        destination: Optional[str],
        version: Optional[str],
    ) -> Dict[str, Any]:
        """Load directive with RYE intelligence."""
        # Handle registry load
        if source == "registry":
            return await self._load_from_registry("directive", directive_name, destination, version)

        # Handle local loads
        return await self._load_local_item(
            "directive",
            directive_name,
            source,
            destination,
        )

    async def _load_tool(
        self,
        tool_name: str,
        source: str,
        destination: Optional[str],
        version: Optional[str],
    ) -> Dict[str, Any]:
        """Load tool with RYE intelligence."""
        # Handle registry load
        if source == "registry":
            return await self._load_from_registry("tool", tool_name, destination, version)

        # Handle local loads
        return await self._load_local_item(
            "tool",
            tool_name,
            source,
            destination,
        )

    async def _load_knowledge(
        self,
        knowledge_id: str,
        source: str,
        destination: Optional[str],
    ) -> Dict[str, Any]:
        """Load knowledge entry with RYE intelligence."""
        # Handle registry load
        if source == "registry":
            return await self._load_from_registry("knowledge", knowledge_id, destination)

        # Handle local loads
        return await self._load_local_item(
            "knowledge",
            knowledge_id,
            source,
            destination,
        )

    async def _load_local_item(
        self,
        item_type: str,
        item_id: str,
        source: str,
        destination: Optional[str],
    ) -> Dict[str, Any]:
        """
        Load item from local source (project or user) with RYE intelligence.

        RYE adds:
        - Path validation
        - Content parsing and validation
        - Copy operations between spaces
        """
        # Get resolver for item type
        resolver = self._get_resolver(item_type)
        if not resolver:
            return {"error": f"Unsupported item type: {item_type}"}

        # Find source file
        if source == "project":
            search_base = self.project_path / ".ai"
        else:  # user
            search_base = get_user_space()

        # Find file in appropriate subdirectory
        file_path = self._find_item_path(search_base, item_type, item_id)

        if not file_path or not file_path.exists():
            return {
                "error": f"{item_type.title()} '{item_id}' not found in {source} space",
                "source": source,
                "searched_in": str(search_base),
            }

        # Determine if this is read-only mode
        is_read_only = destination is None or (source == destination)

        if not is_read_only:
            # RYE INTELLIGENCE: Copy to destination
            target_base = (
                self.project_path / ".ai" if destination == "project" else get_user_space()
            )
            target_path = target_base / self._get_type_dir(item_type) / file_path.name

            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file using Lilux subprocess primitive
            await self._copy_file(file_path, target_path)

            self.logger.info(f"Copied {item_type} from {source} to {destination}: {target_path}")

            # Parse and validate copied file (RYE intelligence)
            parsed_data = self._parse_item(item_type, target_path)
            parsed_data["source"] = source
            parsed_data["destination"] = destination
            parsed_data["path"] = str(target_path)

            return parsed_data
        else:
            # Read-only mode: parse and return (RYE intelligence)
            parsed_data = self._parse_item(item_type, file_path)
            parsed_data["source"] = source
            parsed_data["path"] = str(file_path)
            parsed_data["mode"] = "read_only"

            return parsed_data

    async def _load_from_registry(
        self,
        item_type: str,
        item_id: str,
        destination: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load item from remote registry with RYE intelligence.

        RYE adds:
        - Registry URL resolution
        - HTTP download with auth
        - Content validation after download
        """
        try:
            # RYE INTELLIGENCE: Resolve registry URL
            base_url = self.REGISTRY_URLS.get(item_type)
            if not base_url:
                return {"error": f"Registry not supported for item type: {item_type}"}

            # Build download URL
            url = f"{base_url}/{item_id}"
            if version:
                url = f"{url}@{version}"

            # Get credentials from Lilux runtime auth store (RYE intelligence)
            from lilux.runtime.auth import AuthStore

            token = await AuthStore.get("rye", "registry-token")

            # Download using Lilux HTTP primitive (RYE delegates to Lilux)
            from lilux.primitives.http_client import HttpClientPrimitive

            http_client = HttpClientPrimitive()

            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            http_result = await http_client.execute(
                {"url": url, "method": "GET", "headers": headers},
                {},
            )

            if not http_result.success:
                return {
                    "error": f"Failed to download from registry: {http_result.error}",
                    "url": url,
                    "status_code": http_result.status_code,
                }

            # Determine destination path
            dest_base = self.project_path / ".ai" if destination == "project" else get_user_space()
            dest_dir = dest_base / self._get_type_dir(item_type)
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Determine file extension
            ext = self._get_extension(item_type)
            dest_path = dest_dir / f"{item_id}{ext}"

            # Write downloaded content
            dest_path.write_text(http_result.body)

            # Parse and validate downloaded content (RYE intelligence)
            parsed_data = self._parse_item(item_type, dest_path)
            parsed_data["source"] = "registry"
            parsed_data["destination"] = destination or "user"
            parsed_data["path"] = str(dest_path)
            parsed_data["version"] = version
            parsed_data["validated"] = True  # RYE intelligence

            return parsed_data
        except Exception as e:
            self.logger.error(f"Registry load failed: {e}")
            return {"error": str(e), "message": f"Failed to load from registry"}

    def _get_resolver(self, item_type: str):
        """Get appropriate resolver for item type."""
        if item_type == "directive":
            return self.directive_resolver
        elif item_type == "tool":
            return self.tool_resolver
        elif item_type == "knowledge":
            return self.knowledge_resolver
        return None

    def _find_item_path(self, base_path: Path, item_type: str, item_id: str) -> Optional[Path]:
        """Find item file in base path."""
        type_dir = base_path / self._get_type_dir(item_type)

        if not type_dir.exists():
            return None

        # Try exact match first
        ext = self._get_extension(item_type)
        exact_path = type_dir / f"{item_id}{ext}"
        if exact_path.exists():
            return exact_path

        # Fallback: recursive search
        for file_path in type_dir.rglob(f"*{ext}"):
            if item_id in file_path.stem:
                return file_path

        return None

    def _get_type_dir(self, item_type: str) -> str:
        """Get directory name for item type (RYE knowledge)."""
        type_dirs = {
            "directive": "directives",
            "tool": "tools",
            "knowledge": "knowledge",
        }
        return type_dirs.get(item_type, "items")

    def _get_extension(self, item_type: str) -> str:
        """Get file extension for item type (RYE knowledge)."""
        extensions = {
            "directive": ".md",
            "tool": ".py",
            "knowledge": ".md",
        }
        return extensions.get(item_type, "")

    async def _copy_file(self, source: Path, target: Path):
        """Copy file using Lilux subprocess primitive (RYE delegates to Lilux)."""
        from lilux.primitives.subprocess import SubprocessPrimitive

        subprocess = SubprocessPrimitive()
        result = await subprocess.execute(
            {"command": "cp", "args": [str(source), str(target)]},
            {},
        )

        if not result.success:
            raise RuntimeError(f"Failed to copy file: {result.stderr}")

    def _parse_item(self, item_type: str, file_path: Path) -> Dict[str, Any]:
        """
        Parse item content with RYE intelligence.

        RYE knows how to parse:
        - Directives: XML format
        - Tools: Metadata headers
        - Knowledge: Frontmatter
        """
        try:
            if item_type == "directive":
                # Parse directive XML (RYE intelligence)
                from lilux.utils.parsers import parse_directive_file

                return parse_directive_file(file_path)

            elif item_type == "tool":
                # Parse tool metadata (RYE intelligence)
                from lilux.schemas import extract_tool_metadata

                return extract_tool_metadata(file_path, self.project_path)

            elif item_type == "knowledge":
                # Parse knowledge frontmatter (RYE intelligence)
                from lilux.utils.parsers import parse_knowledge_entry

                return parse_knowledge_entry(file_path)

            return {"error": f"Unknown item type: {item_type}"}
        except Exception as e:
            self.logger.warning(f"Failed to parse {file_path}: {e}")
            return {
                "error": f"Failed to parse {item_type}",
                "details": str(e),
                "path": str(file_path),
            }

    def _is_protected_path(self, item_id: str) -> bool:
        """
        Check if item is protected RYE content (RYE knowledge).

        Protected items cannot be overridden by user content.
        """
        # Check if item starts with protected path
        for protected in self.PROTECTED_PATHS:
            if item_id.startswith(protected):
                return True

        return False
