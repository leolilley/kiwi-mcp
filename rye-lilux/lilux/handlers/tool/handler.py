"""
Tool handler for lilux.

DUMB ROUTER - no content intelligence.
All intelligence moved to RYE layer.

This handler only routes to Lilux primitives for execution.
"""

from pathlib import Path
from typing import Any, Dict
from lilux.utils.logger import get_logger
from lilux.utils.resolvers import ToolResolver, get_user_space


class ToolHandler:
    """
    Kernel handler - dumb router for tool files.

    Does NOT understand tool metadata format.
    Does NOT parse tool executor config.
    Does NOT validate tool structure.

    Only routes files to Lilux primitives for execution.
    """

    def __init__(self, project_path: str):
        """Initialize dumb router with project path."""
        self.project_path = Path(project_path)
        self.resolver = ToolResolver(project_path=self.project_path)
        self.logger = get_logger("tool_handler")

    def get_file_path(self, tool_name: str) -> Dict[str, Any]:
        """
        Resolve tool file path - ROUTER ONLY.

        No parsing, no validation, no intelligence.
        Just returns the file path.

        Args:
            tool_name: Name of tool to resolve

        Returns:
            Dict with 'path', 'item_type', 'item_id'
            or dict with 'error' if not found
        """
        file_path = self.resolver.resolve(tool_name)

        if not file_path:
            return {
                "error": f"Tool '{tool_name}' not found in project or user space"
            }

        return {
            "path": str(file_path),
            "item_type": "tool",
            "item_id": tool_name,
        }

    def list_tools(self, source: str = "all") -> Dict[str, Any]:
        """
        List all tool files - ROUTER ONLY.

        No parsing, no validation.
        Just returns file paths.

        Args:
            source: "project", "user", or "all"

        Returns:
            Dict with list of file paths
        """
        paths = []

        if source in ("project", "all"):
            project_dir = self.project_path / ".ai" / "tools"
            if project_dir.exists():
                paths.extend(project_dir.rglob("*"))

        if source in ("user", "all"):
            user_dir = get_user_space() / "tools"
            if user_dir.exists():
                paths.extend(user_dir.rglob("*"))

        return {
            "tools": [str(p) for p in paths],
            "count": len(paths),
        }

    def copy_tool(self, tool_name: str, destination: str) -> Dict[str, Any]:
        """
        Copy tool file between project/user spaces - ROUTER ONLY.

        No parsing, no validation.
        Just copies the file.

        Args:
            tool_name: Name of tool to copy
            destination: "project" or "user"

        Returns:
            Dict with 'path' or 'error'
        """
        source_path = self.resolver.resolve(tool_name)

        if not source_path:
            return {"error": f"Tool '{tool_name}' not found"}

        # Determine target directory
        if destination == "user":
            target_dir = get_user_space() / "tools"
        else:
            target_dir = self.project_path / ".ai" / "tools"

        # Preserve relative structure
        relative_path = source_path.relative_to(source_path.parents[1])
        target_path = target_dir / relative_path

        # Copy file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(source_path.read_text())

        self.logger.info(f"Copied tool {tool_name} to {destination}: {target_path}")

        return {
            "path": str(target_path),
            "item_id": tool_name,
            "source": "project" if str(source_path).startswith(str(self.project_path)) else "user",
            "destination": destination,
        }
