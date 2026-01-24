"""Path resolution utilities for kiwi-mcp."""

from pathlib import Path
from typing import Optional, Dict, Any
import os
from kiwi_mcp.utils.extensions import get_tool_extensions


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
        item_type: Type of item (directive, tool, knowledge)
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
    
    elif item_type == "tool":
        # Tools support multiple extensions from extractors
        tool_extensions = get_tool_extensions(Path(project_path) if project_path else None)
        if source in ("local", "project") and project_path:
            search_paths.append(Path(project_path) / ".ai" / "tools")
        if source in ("local", "user"):
            search_paths.append(get_user_space() / "tools")
        
        # Search with all supported extensions
        for base_path in search_paths:
            if not base_path.exists():
                continue
            for ext in tool_extensions:
                for category_dir in base_path.glob("*"):
                    if category_dir.is_dir():
                        file_path = category_dir / f"{item_id}{ext}"
                        if file_path.exists():
                            return file_path
                direct_path = base_path / f"{item_id}{ext}"
                if direct_path.exists():
                    return direct_path
        return None
    
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


def extract_category_path(
    file_path: Path, 
    item_type: str, 
    location: str, 
    project_path: Optional[Path] = None
) -> str:
    """
    Extract category path from file location as slash-separated string.
    
    Args:
        file_path: Full path to the file
        item_type: "directive", "tool", or "knowledge"
        location: "project" or "user"
        project_path: Project root (for project location)
    
    Returns:
        Category path as string: "core/api/endpoints" or "" if in base directory
    
    Example:
        .ai/directives/core/api/endpoints/my_directive.md
        -> "core/api/endpoints"
    """
    # Determine expected base
    if location == "project":
        if not project_path:
            return ""
        expected_base = project_path / ".ai" / f"{item_type}s"
    else:
        expected_base = get_user_space() / f"{item_type}s"
    
    # Get relative path from base
    try:
        relative = file_path.relative_to(expected_base)
        # Remove filename, get directory parts
        parts = list(relative.parent.parts)
        # Join with slashes to create category path string
        return "/".join(parts) if parts else ""
    except ValueError:
        # Path not under base - return empty
        return ""


def validate_path_structure(
    file_path: Path, 
    item_type: str, 
    location: str,
    project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Validate file path matches expected structure.
    
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
    issues = []
    
    # Get valid extensions for item type
    if item_type == "tool":
        valid_extensions = get_tool_extensions(project_path)
    else:
        valid_extensions = [".md"]
    
    # Check extension
    if file_path.suffix not in valid_extensions:
        ext_list = ", ".join(valid_extensions)
        issues.append(
            f"Invalid extension '{file_path.suffix}'. "
            f"Expected one of: {ext_list} for {item_type}"
        )
    
    # Determine expected base
    if location == "project":
        if not project_path:
            issues.append("project_path required for project location")
            return {
                "valid": False, 
                "issues": issues,
                "category_path": "",
                "expected_base": "",
                "actual_path": str(file_path)
            }
        expected_base = project_path / ".ai" / f"{item_type}s"
    else:
        expected_base = get_user_space() / f"{item_type}s"
    
    # Check if path is under expected base
    try:
        relative = file_path.relative_to(expected_base)
        category_path = extract_category_path(file_path, item_type, location, project_path)
    except ValueError:
        issues.append(
            f"File path '{file_path}' is not under expected base '{expected_base}'"
        )
        category_path = ""
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "category_path": category_path,
        "expected_base": str(expected_base),
        "actual_path": str(file_path)
    }
