"""
Directive handler for lilux.

DUMB ROUTER - no content intelligence.
All intelligence moved to RYE layer.

This handler only routes to Lilux primitives.
"""

from pathlib import Path
from typing import Any, Dict
from lilux.utils.logger import get_logger
from lilux.utils.resolvers import DirectiveResolver


class DirectiveHandler:
    """
    Kernel handler - dumb router for directive files.

    Does NOT understand directive XML format.
    Does NOT parse directive structure.
    Does NOT validate directive content.

    Only routes files to Lilux primitives for execution.
    """

    def __init__(self, project_path: str):
        """Initialize dumb router with project path."""
        self.project_path = Path(project_path)
        self.resolver = DirectiveResolver(self.project_path)
        self.logger = get_logger("directive_handler")

    def get_file_path(self, directive_name: str) -> Dict[str, Any]:
        """
        Resolve directive file path - ROUTER ONLY.

        No parsing, no validation, no intelligence.
        Just returns the file path.

        Args:
            directive_name: Name of directive to resolve

        Returns:
            Dict with 'path', 'item_type', 'item_id'
            or dict with 'error' if not found
        """
        file_path = self.resolver.resolve(directive_name)

        if not file_path:
            return {"error": f"Directive '{directive_name}' not found in project or user space"}

        return {
            "path": str(file_path),
            "item_type": "directive",
            "item_id": directive_name,
        }

    def list_directives(self, source: str = "all") -> Dict[str, Any]:
        """
        List all directive files - ROUTER ONLY.

        No parsing, no validation.
        Just returns file paths.

        Args:
            source: "project", "user", or "all"

        Returns:
            Dict with list of file paths
        """
        paths = []

        if source in ("project", "all"):
            project_dir = self.project_path / ".ai" / "directives"
            if project_dir.exists():
                paths.extend(project_dir.rglob("*.md"))

        if source in ("user", "all"):
            user_dir = Path.home() / ".ai" / "directives"
            if user_dir.exists():
                paths.extend(user_dir.rglob("*.md"))

        return {
            "directives": [str(p) for p in paths],
            "count": len(paths),
        }
