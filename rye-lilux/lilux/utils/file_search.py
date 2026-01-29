"""
File Search Utilities

Searches for markdown and Python files in local directories.
"""

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def search_markdown_files(base_paths: List[Path], pattern: str = "*.md") -> List[Path]:
    """
    Find all markdown files in base paths.
    
    Args:
        base_paths: List of directories to search
        pattern: Glob pattern (default: "*.md")
    
    Returns:
        List of matching file paths
    """
    results = []
    for base_path in base_paths:
        if not base_path.exists():
            continue
        for file_path in base_path.rglob(pattern):
            if file_path.is_file():
                results.append(file_path)
    return results


def search_python_files(base_paths: List[Path], pattern: str = "*.py") -> List[Path]:
    """
    Find all Python files in base paths.
    
    Args:
        base_paths: List of directories to search
        pattern: Glob pattern (default: "*.py")
    
    Returns:
        List of matching file paths
    """
    results = []
    for base_path in base_paths:
        if not base_path.exists():
            continue
        for file_path in base_path.rglob(pattern):
            if file_path.is_file():
                results.append(file_path)
    return results


def score_relevance(content: str, query_terms: List[str]) -> float:
    """
    Calculate relevance score for content against query terms.
    
    Scoring:
    - All terms present: High score
    - Some terms present: Medium score
    - No terms present: Zero score
    
    Returns:
        Score from 0.0 to 100.0
    """
    if not query_terms:
        return 0.0
    
    content_lower = content.lower()
    matches = sum(1 for term in query_terms if term.lower() in content_lower)
    
    if matches == 0:
        return 0.0
    if matches == len(query_terms):
        return 100.0
    
    return (matches / len(query_terms)) * 50.0
