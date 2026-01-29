"""
Registry for language-specific signature formats.

Loads signature format configuration from extractor tools and provides
a unified interface for getting the appropriate comment syntax for each file type.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Global cache: extension -> signature format
_signature_formats: Optional[Dict[str, Dict[str, Any]]] = None


def get_signature_format(file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get signature format for a file based on its extension.
    
    Args:
        file_path: Path to the file
        project_path: Optional project path for extractor discovery
        
    Returns:
        Signature format dict with 'prefix' and 'after_shebang' keys.
        Example: {"prefix": "#", "after_shebang": True}
    """
    global _signature_formats
    
    # Load formats if not cached
    if _signature_formats is None:
        _signature_formats = _load_signature_formats(project_path)
    
    ext = file_path.suffix.lower()
    format_config = _signature_formats.get(ext)
    
    if format_config:
        return format_config
    
    # Default to Python-style comments
    logger.warning(f"No signature format found for extension '{ext}', using default '#' prefix")
    return {"prefix": "#", "after_shebang": True}


def _load_signature_formats(project_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Load signature formats from all extractors.
    
    Searches for extractor tools in project/.ai/tools/extractors, cwd/.ai/tools/extractors,
    and userspace/tools/extractors, and extracts their SIGNATURE_FORMAT configuration.
    
    Args:
        project_path: Optional project path for extractor discovery
        
    Returns:
        Dictionary mapping file extensions to signature format configurations
    """
    from lilux.schemas.tool_schema import Bootstrap
    from lilux.utils.resolvers import get_user_space
    
    formats = {}
    
    # Build search paths for extractors
    search_paths = []
    if project_path:
        search_paths.append(project_path / ".ai" / "tools" / "extractors")
    search_paths.append(Path.cwd() / ".ai" / "tools" / "extractors")
    search_paths.append(get_user_space() / "tools" / "extractors")
    
    # Load extractors from all search paths
    for extractors_dir in search_paths:
        if not extractors_dir.exists():
            continue
            
        for file_path in extractors_dir.glob("*.py"):
            # Skip private/internal files
            if file_path.name.startswith("_"):
                continue
            
            # Load extractor configuration
            extractor_data = Bootstrap.load_extractor(file_path)
            if not extractor_data:
                continue
            
            # Get signature format (use default if not specified)
            sig_format = extractor_data.get("signature_format", {"prefix": "#", "after_shebang": True})
            
            # Register format for all extensions this extractor handles
            for ext in extractor_data["extensions"]:
                formats[ext.lower()] = sig_format
    
    logger.debug(f"Loaded signature formats for extensions: {list(formats.keys())}")
    return formats


def clear_signature_formats_cache():
    """
    Clear the signature formats cache.
    
    Useful for testing or when extractors are modified and need to be reloaded.
    """
    global _signature_formats
    _signature_formats = None
    logger.debug("Cleared signature formats cache")
