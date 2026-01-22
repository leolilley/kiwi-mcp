"""
Tool handler for kiwi-mcp.

Implements search, load, execute operations for tools.
Handles LOCAL file operations directly, only uses registry for REMOTE operations.

This is the renamed and refactored ScriptHandler with executor pattern support.
"""

from typing import Dict, Any, Optional, List, Literal
from pathlib import Path

from kiwi_mcp.handlers import SortBy
from kiwi_mcp.api.script_registry import ScriptRegistry  # Still using ScriptRegistry for now
from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import ScriptResolver, get_user_space
from kiwi_mcp.utils.parsers import parse_script_metadata
from kiwi_mcp.utils.file_search import search_python_files, score_relevance
from kiwi_mcp.utils.output_manager import OutputManager, truncate_for_response
from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.utils.validators import ValidationManager, compare_versions

from .manifest import ToolManifest
from .executors import ExecutorRegistry, ExecutionResult
from .executors.python import PythonExecutor
from .executors.bash import BashExecutor
from .executors.api import APIExecutor


class ToolHandler:
    """Handler for tool operations with executor abstraction."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.resolver = ScriptResolver(
            project_path=self.project_path
        )  # Still using ScriptResolver for compatibility
        self.registry = ScriptRegistry()  # Still using ScriptRegistry for compatibility
        self.logger = get_logger("tool_handler")

        # Output manager for saving large results
        self.output_manager = OutputManager(project_path=self.project_path)

        # Initialize and register executors
        self._setup_executors()

    def _setup_executors(self):
        """Setup and register available executors."""
        # Register Python executor
        python_executor = PythonExecutor(self.project_path)
        ExecutorRegistry.register("python", python_executor)

        # Register Bash executor
        bash_executor = BashExecutor()
        ExecutorRegistry.register("bash", bash_executor)

        # Register API executor
        api_executor = APIExecutor()
        ExecutorRegistry.register("api", api_executor)

    async def search(
        self, query: str, source: str = "all", limit: int = 10, sort_by: SortBy = "score"
    ) -> Dict[str, Any]:
        """
        Search for tools/scripts.

        Args:
            query: Search query
            source: "local", "registry", or "all"
            limit: Max results
            sort_by: Sort method ("score", "date", "name")

        Returns:
            Dict with search results
        """
        results = []

        # Search local files
        if source in ["local", "all"]:
            local_results = await self._search_local(query, limit)
            results.extend(local_results)

        # Search registry
        if source in ["registry", "all"]:
            registry_results = await self._search_registry(query, limit, sort_by)
            results.extend(registry_results)

        # Sort and limit
        if sort_by == "score":
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
        elif sort_by == "date":
            results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda x: x.get("name", ""))

        return {"results": results[:limit], "total": len(results), "query": query, "source": source}

    async def _search_local(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search local tool/script files."""
        results = []

        # Search paths
        search_dirs = []
        project_scripts = self.project_path / ".ai" / "scripts"
        if project_scripts.exists():
            search_dirs.append(project_scripts)

        user_scripts = get_user_space() / "scripts"
        if user_scripts.exists():
            search_dirs.append(user_scripts)

        # Search each directory
        for search_dir in search_dirs:
            files = search_python_files(search_dir, query)

            for file_path in files:
                try:
                    script = parse_script_metadata(file_path)

                    # Calculate relevance score
                    searchable_text = f"{script['name']} {script['description']}"
                    score = score_relevance(
                        [query], searchable_text
                    )  # Fix: pass list instead of string

                    results.append(
                        {
                            "name": script["name"],
                            "description": script["description"],
                            "source": "project" if ".ai/" in str(file_path) else "user",
                            "path": str(file_path),
                            "score": score,
                            "tool_type": self._detect_tool_type(file_path),
                        }
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to parse {file_path}: {e}")

        return results

    async def _search_registry(
        self, query: str, limit: int, sort_by: SortBy
    ) -> List[Dict[str, Any]]:
        """Search registry for tools/scripts."""
        if not self.registry.is_configured:
            return []

        try:
            results = await self.registry.search(query, limit=limit)  # Remove sort_by for now

            # Add source marker
            for result in results:
                result["source"] = "registry"
                result["tool_type"] = "python"  # Default for registry scripts

            return results
        except Exception as e:
            self.logger.error(f"Registry search failed: {e}")
            return []

    def _detect_tool_type(self, file_path: Path) -> str:
        """Detect tool type from file extension or manifest."""
        # Check for tool.yaml manifest in same directory
        manifest_path = file_path.parent / "tool.yaml"
        if manifest_path.exists():
            try:
                manifest = ToolManifest.from_yaml(manifest_path)
                return manifest.tool_type
            except Exception:
                pass

        # Default based on file extension
        if file_path.suffix == ".py":
            return "python"
        elif file_path.suffix == ".sh":
            return "bash"
        else:
            return "unknown"

    async def load(
        self,
        tool_name: str,
        source: Literal["project", "user", "registry"],
        destination: Optional[Literal["project", "user"]] = None,
    ) -> Dict[str, Any]:
        """
        Load tool from specified source.

        Args:
            tool_name: Name of tool
            source: Where to load from - "project" | "user" | "registry"
            destination: Where to copy to (optional). If None or same as source, read-only mode.

        Returns:
            Dict with tool details
        """
        self.logger.info(
            f"ToolHandler.load: tool={tool_name}, source={source}, destination={destination}"
        )

        try:
            # Determine if this is read-only mode (no copy)
            is_read_only = destination is None or (source == destination and source != "registry")

            # LOAD FROM REGISTRY
            if source == "registry":
                if not self.registry.is_configured:
                    return {
                        "error": "Registry not configured",
                        "message": "Set SUPABASE_URL and SUPABASE_KEY to load from registry",
                    }

                # Get from registry
                tool_data = await self.registry.get(tool_name)
                if not tool_data:
                    return {"error": f"Tool '{tool_name}' not found in registry"}

                # For registry, default destination to "project" if not specified
                effective_destination = destination or "project"

                # Determine target path based on destination
                if effective_destination == "user":
                    target_dir = get_user_space() / "scripts"
                else:  # destination == "project"
                    target_dir = self.project_path / ".ai" / "scripts"

                target_dir.mkdir(parents=True, exist_ok=True)

                # Determine category subdirectory
                category = tool_data.get("category", "utility")
                category_dir = target_dir / category
                category_dir.mkdir(exist_ok=True)

                # Write script file (for now, treating as Python script)
                target_file = category_dir / f"{tool_name}.py"
                target_file.write_text(tool_data["content"])

                self.logger.info(f"Downloaded tool from registry to: {target_file}")

                # Create virtual manifest
                manifest = ToolManifest.virtual_from_script(target_file)

                return {
                    "name": tool_name,
                    "path": str(target_file),
                    "content": tool_data["content"],
                    "source": "registry",
                    "destination": effective_destination,
                    "manifest": {
                        "tool_id": manifest.tool_id,
                        "tool_type": manifest.tool_type,
                        "version": manifest.version,
                        "description": manifest.description,
                    },
                    "message": f"Tool downloaded from registry to {effective_destination}",
                }

            # LOAD FROM LOCAL (project or user)
            else:
                file_path = self.resolver.resolve(tool_name)
                if not file_path:
                    return {"error": f"Tool '{tool_name}' not found locally"}

                # If copying to different location
                if not is_read_only:
                    # Determine target location
                    if destination == "user":
                        target_dir = get_user_space() / "scripts"
                    else:  # destination == "project"
                        target_dir = self.project_path / ".ai" / "scripts"

                    target_dir.mkdir(parents=True, exist_ok=True)

                    # Copy with same relative structure
                    relative_path = file_path.relative_to(
                        file_path.parents[1]
                    )  # Remove scripts/ part
                    target_file = target_dir / relative_path

                    # Create target directory structure
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    target_file.write_text(file_path.read_text())

                    self.logger.info(f"Copied tool from {source} to {destination}: {target_file}")
                    file_path = target_file  # Use new path for metadata extraction

                # Extract metadata
                tool_metadata = parse_script_metadata(file_path)

                # Create manifest (virtual or from file)
                manifest_path = file_path.parent / "tool.yaml"
                if manifest_path.exists():
                    manifest = ToolManifest.from_yaml(manifest_path)
                else:
                    manifest = ToolManifest.virtual_from_script(file_path)

                result = {
                    "name": tool_name,
                    "path": str(file_path),
                    "content": file_path.read_text(),
                    "source": source,
                    "manifest": {
                        "tool_id": manifest.tool_id,
                        "tool_type": manifest.tool_type,
                        "version": manifest.version,
                        "description": manifest.description,
                        "parameters": manifest.parameters,
                    },
                    "metadata": tool_metadata,
                }

                if not is_read_only:
                    result["destination"] = destination
                    result["message"] = f"Tool copied from {source} to {destination}"

                return result

        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            return {"error": str(e)}

    async def execute(
        self,
        action: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a tool or perform tool operation.

        Args:
            action: "run", "publish", "delete", "create", "update"
            tool_name: Name of tool to execute
            parameters: Tool parameters (for run action)
            dry_run: If True, validate without executing

        Returns:
            Dict with execution result
        """
        # Extract dry_run from parameters if present
        params = parameters or {}
        if params and "dry_run" in params:
            dry_run = params.pop("dry_run")

        try:
            if action == "run":
                return await self._run_tool(tool_name, params, dry_run)

            elif action == "publish":
                return await self._publish_tool(tool_name, params.get("version"))

            elif action == "delete":
                return await self._delete_tool(tool_name, params.get("confirm", False))

            elif action == "create":
                return await self._create_tool(
                    tool_name,
                    params.get("content"),
                    params.get("location", "project"),
                    params.get("category"),
                )

            elif action == "update":
                return await self._update_tool(tool_name, params.get("updates", {}))

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return {"error": str(e)}

    async def _run_tool(
        self, tool_name: str, params: Dict[str, Any], dry_run: bool
    ) -> Dict[str, Any]:
        """Execute a tool using appropriate executor."""
        # Find tool file
        file_path = self.resolver.resolve(tool_name)
        if not file_path:
            return {
                "error": f"Tool '{tool_name}' not found locally",
                "suggestion": "Use load() to download from registry first",
            }

        # Create or load manifest
        manifest_path = file_path.parent / "tool.yaml"
        if manifest_path.exists():
            manifest = ToolManifest.from_yaml(manifest_path)
        else:
            manifest = ToolManifest.virtual_from_script(file_path)

        # Signature validation (reusing existing logic)
        file_content = file_path.read_text()
        signature_status = MetadataManager.verify_signature(
            "script", file_content
        )  # Still using "script" type

        if signature_status:
            if signature_status.get("status") == "modified":
                return {
                    "status": "error",
                    "error": "Tool content has been modified since last validation",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the tool",
                }
            elif signature_status.get("status") == "invalid":
                return {
                    "status": "error",
                    "error": "Tool signature is invalid",
                    "signature": signature_status,
                    "path": str(file_path),
                    "solution": "Use execute action 'update' or 'create' to re-validate the tool",
                }

        # Validate tool using centralized validator
        script_meta = parse_script_metadata(file_path)
        validation_result = ValidationManager.validate(
            "script", file_path, script_meta
        )  # Still using "script" type
        if not validation_result["valid"]:
            return {
                "status": "error",
                "error": "Tool validation failed",
                "details": validation_result["issues"],
                "path": str(file_path),
            }

        if dry_run:
            return {
                "status": "validation_passed",
                "message": "Tool is ready to execute",
                "path": str(file_path),
                "manifest": {
                    "tool_id": manifest.tool_id,
                    "tool_type": manifest.tool_type,
                    "version": manifest.version,
                },
            }

        # Get executor for tool type
        executor = ExecutorRegistry.get(manifest.tool_type)
        if not executor:
            return {
                "status": "error",
                "error": f"No executor available for tool type '{manifest.tool_type}'",
                "available_types": ExecutorRegistry.list_types(),
            }

        # Execute using appropriate executor
        try:
            result = await executor.execute(manifest, params)

            # Convert ExecutionResult to expected format
            if result.success:
                return {
                    "status": "success",
                    "data": {"output": result.output},
                    "metadata": {
                        "duration_ms": result.duration_ms,
                        "tool_type": manifest.tool_type,
                        "executor": executor.__class__.__name__,
                    },
                }
            else:
                return {
                    "status": "error",
                    "error": result.error or "Unknown execution error",
                    "metadata": {
                        "duration_ms": result.duration_ms,
                        "tool_type": manifest.tool_type,
                        "executor": executor.__class__.__name__,
                    },
                }

        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return {"status": "error", "error": str(e)}

    # Placeholder methods for other actions (delegate to script handler for now)
    async def _publish_tool(self, tool_name: str, version: Optional[str]) -> Dict[str, Any]:
        """Publish tool to registry."""
        return {"error": "Tool publishing not yet implemented"}

    async def _delete_tool(self, tool_name: str, confirm: bool) -> Dict[str, Any]:
        """Delete tool."""
        return {"error": "Tool deletion not yet implemented"}

    async def _create_tool(
        self, tool_name: str, content: str, location: str, category: str
    ) -> Dict[str, Any]:
        """Create new tool."""
        return {"error": "Tool creation not yet implemented"}

    async def _update_tool(self, tool_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update tool."""
        return {"error": "Tool updates not yet implemented"}
