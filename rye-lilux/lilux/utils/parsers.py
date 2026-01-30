"""
Kernel Parsers - Minimal routing helpers only.

This is the KERNEL version - contains only basic helpers for routing.
Full parsing intelligence moves to RYE OS layer.
"""

from pathlib import Path


def extract_extension(file_path: Path) -> str:
    """Extract file extension for type routing."""
    return file_path.suffix.lower()


def is_xml_file(file_path: Path) -> bool:
    """Check if file is XML (basic routing check)."""
    return file_path.suffix.lower() in [".xml"]


def is_markdown_file(file_path: Path) -> bool:
    """Check if file is markdown (basic routing check)."""
    return file_path.suffix.lower() in [".md"]


# REMOVED: parse_directive_file - moved to RYE
# REMOVED: parse_knowledge_entry - moved to RYE
# REMOVED: parse_script_metadata - moved to RYE
# REMOVED: SchemaExtractor - moved to RYE
# REMOVED: All complex parsing logic - intelligence moves to RYE
