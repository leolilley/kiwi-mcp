"""File operation utilities for lilux."""

from pathlib import Path
from typing import Dict, Any
import json
import yaml


def read_markdown_file(file_path: Path) -> Dict[str, Any]:
    """
    Read a markdown file with YAML frontmatter.
    
    Args:
        file_path: Path to markdown file
    
    Returns:
        Dict with 'content' and any frontmatter fields
    """
    content = file_path.read_text()
    
    # Check for YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                markdown_content = parts[2].strip()
                
                if isinstance(frontmatter, dict):
                    result = frontmatter.copy()
                    result['content'] = markdown_content
                    return result
            except yaml.YAMLError:
                pass
    
    # No frontmatter, return just content
    return {'content': content}


def write_markdown_file(file_path: Path, content: str, metadata: Dict[str, Any] = None):
    """
    Write a markdown file with optional YAML frontmatter.
    
    Args:
        file_path: Path to write to
        content: Markdown content
        metadata: Optional metadata to include as frontmatter
    """
    if metadata:
        # Write with frontmatter
        frontmatter_yaml = yaml.dump(metadata, default_flow_style=False)
        full_content = f"---\n{frontmatter_yaml}---\n\n{content}"
    else:
        full_content = content
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(full_content)


def read_json_file(file_path: Path) -> Dict[str, Any]:
    """Read JSON file."""
    return json.loads(file_path.read_text())


def write_json_file(file_path: Path, data: Dict[str, Any]):
    """Write JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2))
