"""Path resolution utilities for kiwi-mcp.

This module provides backwards-compatible wrappers around PathService.
For new code, prefer using PathService directly.
"""

from pathlib import Path
from typing import Optional, Dict, Any

# Import from canonical source
from kiwi_mcp.utils.path_service import (
    PathService,
    get_user_space,
    ITEM_TYPE_TO_DIR,
)

# Re-export for backwards compatibility
__all__ = [
    "get_user_home",
    "get_user_space",
    "get_project_path",
    "resolve_item_path",
    "extract_category_path",
    "validate_path_structure",
]


def get_user_home() -> Path:
    """Get user home directory."""
    return Path.home()


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
    
    Delegates to PathService for consistent resolution semantics.
    
    Args:
        item_id: Item identifier (name)
        item_type: Type of item (directive, tool, knowledge)
        source: Source location (local, project, user)
        project_path: Optional project path
    
    Returns:
        Path to item if found, None otherwise
    """
    service = PathService(Path(project_path) if project_path else None)
    result = service.resolve(item_type, item_id, source=source)
    return result.path


def extract_category_path(
    file_path: Path, 
    item_type: str, 
    location: str, 
    project_path: Optional[Path] = None
) -> str:
    """
    Extract category path from file location as slash-separated string.
    
    Delegates to PathService for consistent handling.
    
    Args:
        file_path: Full path to the file
        item_type: "directive", "tool", or "knowledge"
        location: "project" or "user" (ignored, auto-detected)
        project_path: Project root (for project location)
    
    Returns:
        Category path as string: "core/api/endpoints" or "" if in base directory
    
    Example:
        .ai/directives/core/api/endpoints/my_directive.md
        -> "core/api/endpoints"
    """
    service = PathService(project_path)
    return service.extract_category_path(file_path, item_type)


def validate_path_structure(
    file_path: Path, 
    item_type: str, 
    location: str,
    project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Validate file path matches expected structure.
    
    Delegates to PathService for consistent validation.
    
    Expected: .ai/{type}/{category}/{subcategory}/.../{name}.{ext}
    
    Args:
        file_path: Path to validate
        item_type: "directive", "tool", or "knowledge"
        location: "project" or "user"
        project_path: Project root (for project location)
    
    Returns:
        {
            "valid": bool,
            "issues": List[str],
            "category_path": str,  # Extracted category path (slash-separated)
            "expected_base": str,  # Expected base directory
            "actual_path": str
        }
    """
    service = PathService(project_path)
    result = service.validate_path(file_path, item_type)
    
    # Add expected_base for backwards compatibility
    expected_base = service.get_base_dir(item_type, location)
    result["expected_base"] = str(expected_base) if expected_base else ""
    
    return result



