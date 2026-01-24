"""
Path Resolution Utilities

Finds directives, tools, and knowledge entries in local filesystems.
"""

from pathlib import Path
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)


def get_user_space() -> Path:
    """Get user space directory from env var or default to ~/.ai"""
    user_space = os.getenv("USER_SPACE")
    if user_space:
        return Path(user_space).expanduser()
    return Path.home() / ".ai"


class DirectiveResolver:
    """Resolve directive file paths."""
    
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.user_space = get_user_space()
        
        self.project_directives = self.project_path / ".ai" / "directives"
        self.user_directives = self.user_space / "directives"
    
    def resolve(self, directive_name: str) -> Optional[Path]:
        """
        Find directive file in project > user order.
        
        Searches recursively in all subdirectories.
        """
        # Check project space
        if self.project_directives.exists():
            for file_path in self.project_directives.rglob(f"{directive_name}.md"):
                if file_path.is_file():
                    return file_path
        
        # Check user space
        if self.user_directives.exists():
            for file_path in self.user_directives.rglob(f"{directive_name}.md"):
                if file_path.is_file():
                    return file_path
        
        return None


class ToolResolver:
    """Resolve tool file paths."""
    
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.user_space = get_user_space()
        
        self.project_tools = self.project_path / ".ai" / "tools"
        self.user_tools = self.user_space / "tools"
    
    def resolve(self, tool_name: str) -> Optional[Path]:
        """Find tool file in project > user order."""
        if self.project_tools.exists():
            for file_path in self.project_tools.rglob(f"{tool_name}.py"):
                if file_path.is_file():
                    return file_path
        
        if self.user_tools.exists():
            for file_path in self.user_tools.rglob(f"{tool_name}.py"):
                if file_path.is_file():
                    return file_path
        
        return None


class KnowledgeResolver:
    """Resolve knowledge entry file paths."""
    
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.user_space = get_user_space()
        
        self.project_knowledge = self.project_path / ".ai" / "knowledge"
        self.user_knowledge = self.user_space / "knowledge"
    
    def resolve(self, zettel_id: str) -> Optional[Path]:
        """
        Find knowledge entry file in project > user order.
        
        Searches recursively in all subdirectories.
        """
        # Check project space
        if self.project_knowledge.exists():
            for file_path in self.project_knowledge.rglob(f"{zettel_id}.md"):
                if file_path.is_file():
                    return file_path
        
        # Check user space
        if self.user_knowledge.exists():
            for file_path in self.user_knowledge.rglob(f"{zettel_id}.md"):
                if file_path.is_file():
                    return file_path
        
        return None
