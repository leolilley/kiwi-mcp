"""
Path Resolution Utilities

Thin wrappers around PathService for backwards compatibility.
All resolution logic is delegated to PathService.
"""

from pathlib import Path
from typing import Optional
import logging

from lilux.utils.path_service import (
    PathService,
    get_user_space,
    ITEM_TYPE_TO_DIR,
)

logger = logging.getLogger(__name__)

# Re-export get_user_space for backwards compatibility
__all__ = ["get_user_space", "DirectiveResolver", "ToolResolver", "KnowledgeResolver"]


class DirectiveResolver:
    """Resolve directive file paths. Thin wrapper around PathService."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self._service = PathService(self.project_path)
        
        # Expose base paths for backwards compatibility
        self.user_space = self._service.user_space
        self.project_directives = self._service.get_base_dir("directive", "project") or (
            self.project_path / ".ai" / "directives"
        )
        self.user_directives = self._service.get_base_dir("directive", "user") or (
            self.user_space / "directives"
        )

    def resolve(self, directive_name: str) -> Optional[Path]:
        """
        Find directive file in project > user order.

        Args:
            directive_name: Name of directive (without extension)

        Returns:
            Path to directive file, or None if not found
        """
        result = self._service.resolve("directive", directive_name, source="local")
        return result.path


class ToolResolver:
    """Resolve tool file paths. Thin wrapper around PathService."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self._service = PathService(self.project_path)
        
        # Expose base paths for backwards compatibility
        self.user_space = self._service.user_space
        self.project_tools = self._service.get_base_dir("tool", "project") or (
            self.project_path / ".ai" / "tools"
        )
        self.user_tools = self._service.get_base_dir("tool", "user") or (
            self.user_space / "tools"
        )

    def resolve(self, tool_name: str) -> Optional[Path]:
        """
        Find tool file in project > user order.

        Args:
            tool_name: Name of tool (without extension)

        Returns:
            Path to tool file, or None if not found
        """
        result = self._service.resolve("tool", tool_name, source="local")
        return result.path


class KnowledgeResolver:
    """Resolve knowledge entry file paths. Thin wrapper around PathService."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self._service = PathService(self.project_path)
        
        # Expose base paths for backwards compatibility
        self.user_space = self._service.user_space
        self.project_knowledge = self._service.get_base_dir("knowledge", "project") or (
            self.project_path / ".ai" / "knowledge"
        )
        self.user_knowledge = self._service.get_base_dir("knowledge", "user") or (
            self.user_space / "knowledge"
        )

    def resolve(self, id: str) -> Optional[Path]:
        """
        Find knowledge entry file in project > user order.

        Args:
            id: Knowledge entry ID (without extension)

        Returns:
            Path to knowledge file, or None if not found
        """
        result = self._service.resolve("knowledge", id, source="local")
        return result.path
