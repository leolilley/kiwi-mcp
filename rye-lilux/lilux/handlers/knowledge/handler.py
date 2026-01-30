"""
Knowledge handler for lilux.

DUMB ROUTER - no content intelligence.
All intelligence moved to RYE layer.

This handler only routes to Lilux primitives.
"""

from pathlib import Path
from typing import Any, Dict
from lilux.utils.logger import get_logger
from lilux.utils.resolvers import KnowledgeResolver, get_user_space


class KnowledgeHandler:
    """
    Kernel handler - dumb router for knowledge files.

    Does NOT understand knowledge markdown format.
    Does NOT parse frontmatter.
    Does NOT validate knowledge content.

    Only routes files to Lilux primitives.
    """

    def __init__(self, project_path: str):
        """Initialize dumb router with project path."""
        self.project_path = Path(project_path)
        self.resolver = KnowledgeResolver(self.project_path)
        self.logger = get_logger("knowledge_handler")

    def get_file_path(self, knowledge_id: str) -> Dict[str, Any]:
        """
        Resolve knowledge file path - ROUTER ONLY.

        No parsing, no validation, no intelligence.
        Just returns file path.

        Args:
            knowledge_id: ID of knowledge entry to resolve

        Returns:
            Dict with 'path', 'item_type', 'item_id'
            or dict with 'error' if not found
        """
        file_path = self.resolver.resolve(knowledge_id)

        if not file_path:
            return {
                "error": f"Knowledge entry '{knowledge_id}' not found in project or user space"
            }

        return {
            "path": str(file_path),
            "item_type": "knowledge",
            "item_id": knowledge_id,
        }

    def list_knowledge(self, source: str = "all") -> Dict[str, Any]:
        """
        List all knowledge files - ROUTER ONLY.

        No parsing, no validation.
        Just returns file paths.

        Args:
            source: "project", "user", or "all"

        Returns:
            Dict with list of file paths
        """
        paths = []

        if source in ("project", "all"):
            project_dir = self.project_path / ".ai" / "knowledge"
            if project_dir.exists():
                paths.extend(project_dir.rglob("*.md"))

        if source in ("user", "all"):
            user_dir = get_user_space() / "knowledge"
            if user_dir.exists():
                paths.extend(user_dir.rglob("*.md"))

        return {
            "knowledge_entries": [str(p) for p in paths],
            "count": len(paths),
        }

    def copy_knowledge(self, knowledge_id: str, destination: str) -> Dict[str, Any]:
        """
        Copy knowledge file between project/user spaces - ROUTER ONLY.

        No parsing, no validation.
        Just copies the file.

        Args:
            knowledge_id: ID of knowledge entry to copy
            destination: "project" or "user"

        Returns:
            Dict with 'path' or 'error'
        """
        source_path = self.resolver.resolve(knowledge_id)

        if not source_path:
            return {"error": f"Knowledge entry '{knowledge_id}' not found"}

        # Determine target directory
        if destination == "user":
            target_dir = get_user_space() / "knowledge"
        else:
            target_dir = self.project_path / ".ai" / "knowledge"

        # Preserve relative structure
        relative_path = source_path.relative_to(source_path.parents[1])
        target_path = target_dir / relative_path

        # Copy file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(source_path.read_text())

        self.logger.info(f"Copied knowledge {knowledge_id} to {destination}: {target_path}")

        return {
            "path": str(target_path),
            "item_id": knowledge_id,
            "source": "project" if str(source_path).startswith(str(self.project_path)) else "user",
            "destination": destination,
        }
