"""Path resolution utilities for kiwi-mcp."""

from pathlib import Path
from typing import Optional
import os


def get_user_home() -> Path:
    """Get user home directory."""
    return Path.home()


def get_user_space() -> Path:
    """
    Get user space directory from env var or default to ~/.ai
    
    Can be configured via USER_SPACE environment variable.
    """
    user_space = os.getenv("USER_SPACE")
    if user_space:
        return Path(user_space).expanduser()
    return Path.home() / ".ai"


def get_project_path(project_path: Optional[str] = None) -> Optional[Path]:
    """
    Get project path as Path object.
    
    Args:
        project_path: Optional project path string
    
    Returns:
        Path object or None if no project path provided
    """
    if project_path:
        return Path(project_path)
    return None


def resolve_item_path(
    item_id: str,
    item_type: str,
    source: str,
    project_path: Optional[str] = None
) -> Optional[Path]:
    """
    Resolve the filesystem path for an item.
    
    Args:
        item_id: Item identifier (name)
        item_type: Type of item (directive, script, knowledge)
        source: Source location (local, project, user)
        project_path: Optional project path
    
    Returns:
        Path to item if found, None otherwise
    """
    search_paths = []
    
    # Determine base directories based on item type
    if item_type == "directive":
        ext = ".md"
        if source in ("local", "project") and project_path:
            search_paths.append(Path(project_path) / ".ai" / "directives")
        if source in ("local", "user"):
            search_paths.append(get_user_space() / "directives")
    
    elif item_type == "script":
        ext = ".py"
        if source in ("local", "project") and project_path:
            search_paths.append(Path(project_path) / ".ai" / "scripts")
        if source in ("local", "user"):
            search_paths.append(get_user_space() / "scripts")
    
    elif item_type == "knowledge":
        ext = ".md"
        if source in ("local", "project") and project_path:
            search_paths.append(Path(project_path) / ".ai" / "knowledge")
        if source in ("local", "user"):
            search_paths.append(get_user_space() / "knowledge")
    
    else:
        return None
    
    # Search for item in all paths
    for base_path in search_paths:
        if not base_path.exists():
            continue
        
        # Search in all subdirectories (categories)
        for category_dir in base_path.glob("*"):
            if category_dir.is_dir():
                file_path = category_dir / f"{item_id}{ext}"
                if file_path.exists():
                    return file_path
        
        # Also check directly in base path
        direct_path = base_path / f"{item_id}{ext}"
        if direct_path.exists():
            return direct_path
    
    return None
