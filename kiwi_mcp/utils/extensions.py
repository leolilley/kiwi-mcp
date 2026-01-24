"""Centralized tool extension registry."""

from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Global cache - single source of truth
_extensions_cache: Optional[List[str]] = None


def get_tool_extensions(project_path: Optional[Path] = None, force_reload: bool = False) -> List[str]:
    """
    Get supported tool file extensions from extractors.
    
    This is the ONLY function that should be used to get tool extensions.
    Uses a global cache to avoid repeated extractor loading.
    
    Args:
        project_path: Optional project path for extractor discovery
        force_reload: Force reload extractors (useful for testing)
    
    Returns:
        List of supported extensions (e.g., ['.py', '.js', '.yaml'])
    """
    global _extensions_cache
    
    if _extensions_cache is not None and not force_reload:
        return _extensions_cache
    
    try:
        from kiwi_mcp.schemas.tool_schema import SchemaExtractor
        extractor = SchemaExtractor()
        extractor._load_extractors(project_path)
        _extensions_cache = extractor.get_supported_extensions() or [".py"]
        logger.debug(f"Loaded tool extensions: {_extensions_cache}")
        return _extensions_cache
    except Exception as e:
        logger.warning(f"Failed to load tool extractors, defaulting to .py only: {e}")
        return [".py"]


def clear_extensions_cache():
    """Clear the extensions cache. Useful for testing."""
    global _extensions_cache
    _extensions_cache = None
