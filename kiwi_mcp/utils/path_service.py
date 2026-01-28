"""
Unified Path Resolution Service

Single source of truth for all path resolution in kiwi-mcp.
Consolidates DirectiveResolver, ToolResolver, KnowledgeResolver patterns.

Features:
- Caching of resolve results (including negative hits)
- Consistent recursive search semantics
- Direct path check optimization (O(1) before rglob)
- Unified user space handling
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

# Item type to directory name mapping
ITEM_TYPE_TO_DIR = {
    "directive": "directives",
    "tool": "tools",
    "knowledge": "knowledge",
}

# Default extensions by item type
DEFAULT_EXTENSIONS = {
    "directive": [".md"],
    "knowledge": [".md"],
    "tool": [".py"],  # Overridden by extractor system
}


def get_user_space() -> Path:
    """
    Get user space directory - single canonical implementation.
    
    Checks env vars in order:
    1. USER_SPACE (canonical, standard)
    2. Default: ~/.ai
    
    Returns:
        Path to user space directory
    """
    user_space = os.getenv("USER_SPACE")
    if user_space:
        return Path(user_space).expanduser()
    return Path.home() / ".ai"


@dataclass
class ResolveResult:
    """Result of a path resolution."""
    path: Optional[Path]
    source: Optional[str]  # "project" or "user"
    cached: bool = False


class PathService:
    """
    Unified path resolution service.
    
    Provides:
    - Consistent resolve semantics across all item types
    - Result caching with optional TTL
    - Direct path optimization before recursive search
    - Unified base directory computation
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize path service.
        
        Args:
            project_path: Path to project root (where .ai/ folder lives)
        """
        self.project_path = Path(project_path) if project_path else None
        self.user_space = get_user_space()
        
        # Resolve cache: (item_type, item_id, source) -> ResolveResult
        self._resolve_cache: Dict[Tuple[str, str, str], ResolveResult] = {}
        
        logger.debug(
            f"PathService initialized: project={self.project_path}, user={self.user_space}"
        )
    
    def get_base_dir(self, item_type: str, location: str) -> Optional[Path]:
        """
        Get base directory for item type and location.
        
        Args:
            item_type: "directive", "tool", or "knowledge"
            location: "project" or "user"
        
        Returns:
            Path to base directory, or None if not applicable
        """
        folder_name = ITEM_TYPE_TO_DIR.get(item_type)
        if not folder_name:
            return None
        
        if location == "project":
            if not self.project_path:
                return None
            return self.project_path / ".ai" / folder_name
        elif location == "user":
            return self.user_space / folder_name
        
        return None
    
    def get_search_paths(
        self, 
        item_type: str, 
        source: str = "local"
    ) -> List[Tuple[Path, str]]:
        """
        Get ordered list of search paths with their location labels.
        
        Args:
            item_type: "directive", "tool", or "knowledge"
            source: "local" (project then user), "project", or "user"
        
        Returns:
            List of (path, location) tuples in search order
        """
        paths = []
        
        if source in ("local", "project"):
            project_base = self.get_base_dir(item_type, "project")
            if project_base and project_base.exists():
                paths.append((project_base, "project"))
        
        if source in ("local", "user"):
            user_base = self.get_base_dir(item_type, "user")
            if user_base and user_base.exists():
                paths.append((user_base, "user"))
        
        return paths
    
    def get_extensions(self, item_type: str) -> List[str]:
        """
        Get file extensions for item type.
        
        Args:
            item_type: "directive", "tool", or "knowledge"
        
        Returns:
            List of extensions (e.g., [".py", ".js"])
        """
        if item_type == "tool":
            # Delegate to extensions module which has its own cache
            from kiwi_mcp.utils.extensions import get_tool_extensions
            exts = get_tool_extensions(self.project_path)
            # Ensure .py is always included (most common tool type)
            if ".py" not in exts:
                exts = [".py"] + list(exts)
            return exts
        
        return DEFAULT_EXTENSIONS.get(item_type, [".md"])
    
    def resolve(
        self,
        item_type: str,
        item_id: str,
        source: str = "local",
        use_cache: bool = True,
    ) -> ResolveResult:
        """
        Resolve item to filesystem path.
        
        Uses optimized search order:
        1. Check cache
        2. Try direct path (O(1)) - base_dir/{item_id}{ext}
        3. Fall back to recursive search
        
        Args:
            item_type: "directive", "tool", or "knowledge"
            item_id: Item identifier (name without extension)
            source: "local" (project then user), "project", or "user"
            use_cache: Whether to use/update cache
        
        Returns:
            ResolveResult with path (or None), source, and cache status
        """
        cache_key = (item_type, item_id, source)
        
        # Check cache
        if use_cache and cache_key in self._resolve_cache:
            result = self._resolve_cache[cache_key]
            return ResolveResult(result.path, result.source, cached=True)
        
        # Get extensions and search paths
        extensions = self.get_extensions(item_type)
        search_paths = self.get_search_paths(item_type, source)
        
        # Search in order: project before user
        for base_path, location in search_paths:
            found = self._find_in_path(base_path, item_id, extensions)
            if found:
                result = ResolveResult(found, location, cached=False)
                if use_cache:
                    self._resolve_cache[cache_key] = result
                return result
        
        # Not found - cache negative result
        result = ResolveResult(None, None, cached=False)
        if use_cache:
            self._resolve_cache[cache_key] = result
        return result
    
    def _find_in_path(
        self, 
        base_path: Path, 
        item_id: str, 
        extensions: List[str]
    ) -> Optional[Path]:
        """
        Find item in base path using optimized search.
        
        Order:
        1. Direct path: base_path/{item_id}{ext}
        2. Category path: base_path/{category}/{item_id}{ext} (one level)
        3. Recursive: base_path/**/{item_id}{ext}
        
        Args:
            base_path: Base directory to search
            item_id: Item identifier
            extensions: List of valid extensions
        
        Returns:
            Path if found, None otherwise
        """
        for ext in extensions:
            filename = f"{item_id}{ext}"
            
            # 1. Direct path check (O(1))
            direct = base_path / filename
            if direct.is_file():
                return direct
            
            # 2. One-level category check (O(subdirs))
            for subdir in base_path.iterdir():
                if subdir.is_dir():
                    category_path = subdir / filename
                    if category_path.is_file():
                        return category_path
            
            # 3. Recursive search (O(n) where n = all files)
            # Only if not found in direct or category
            for file_path in base_path.rglob(filename):
                if file_path.is_file():
                    return file_path
        
        return None
    
    def invalidate_cache(self, item_type: Optional[str] = None, item_id: Optional[str] = None):
        """
        Invalidate resolve cache.
        
        Args:
            item_type: If provided, only invalidate for this type
            item_id: If provided, only invalidate for this id
        """
        if item_type is None and item_id is None:
            self._resolve_cache.clear()
            logger.debug("PathService cache fully cleared")
            return
        
        keys_to_remove = [
            k for k in self._resolve_cache
            if (item_type is None or k[0] == item_type)
            and (item_id is None or k[1] == item_id)
        ]
        
        for key in keys_to_remove:
            del self._resolve_cache[key]
        
        logger.debug(f"PathService cache invalidated: removed {len(keys_to_remove)} entries")
    
    def extract_category_path(self, file_path: Path, item_type: str) -> str:
        """
        Extract category path from file location.
        
        Args:
            file_path: Full path to the file
            item_type: "directive", "tool", or "knowledge"
        
        Returns:
            Category path as slash-separated string (e.g., "core/api")
            or empty string if in base directory
        """
        # Determine which base path this file is under
        for location in ("project", "user"):
            base = self.get_base_dir(item_type, location)
            if base and file_path.is_relative_to(base):
                try:
                    relative = file_path.relative_to(base)
                    parts = list(relative.parent.parts)
                    return "/".join(parts) if parts else ""
                except ValueError:
                    continue
        
        return ""
    
    def validate_path(self, file_path: Path, item_type: str) -> Dict[str, Any]:
        """
        Validate file path matches expected structure.
        
        Args:
            file_path: Path to validate
            item_type: "directive", "tool", or "knowledge"
        
        Returns:
            Dict with valid, issues, category_path, location
        """
        issues = []
        location = None
        category_path = ""
        
        # Check extension
        valid_extensions = self.get_extensions(item_type)
        if file_path.suffix not in valid_extensions:
            ext_list = ", ".join(valid_extensions)
            issues.append(f"Invalid extension '{file_path.suffix}'. Expected: {ext_list}")
        
        # Determine location and validate base path
        for loc in ("project", "user"):
            base = self.get_base_dir(item_type, loc)
            if base and file_path.is_relative_to(base):
                location = loc
                category_path = self.extract_category_path(file_path, item_type)
                break
        
        if location is None:
            project_base = self.get_base_dir(item_type, "project")
            user_base = self.get_base_dir(item_type, "user")
            issues.append(
                f"Path not under expected base. "
                f"Expected: {project_base} or {user_base}"
            )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "location": location,
            "category_path": category_path,
            "path": str(file_path),
        }


# Module-level singleton for convenience
_default_service: Optional[PathService] = None


def get_path_service(project_path: Optional[Path] = None) -> PathService:
    """
    Get or create PathService instance.
    
    Uses singleton pattern for same project_path to maximize cache reuse.
    
    Args:
        project_path: Project root path
    
    Returns:
        PathService instance
    """
    global _default_service
    
    if _default_service is None or _default_service.project_path != project_path:
        _default_service = PathService(project_path)
    
    return _default_service


def clear_path_service():
    """Clear the default path service singleton. Useful for testing."""
    global _default_service
    _default_service = None
