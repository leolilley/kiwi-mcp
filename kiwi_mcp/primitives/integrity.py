"""
Integrity - Canonical content-addressed hashing for tools, directives, and knowledge.

Provides deterministic integrity computation that changes if ANY 
execution-relevant byte changes in the content or metadata.

All integrity functions follow the same pattern:
1. Build a canonical payload with sorted keys
2. Serialize to JSON with no extra whitespace
3. Return SHA256 hex digest (64 characters)
"""

import hashlib
import json
from typing import Any, Dict, List, Optional


# =============================================================================
# Tool Integrity
# =============================================================================


def compute_tool_integrity(
    tool_id: str,
    version: str,
    manifest: Dict[str, Any],
    files: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Compute deterministic integrity hash for a tool version.
    
    The integrity changes if ANY execution-relevant byte changes.
    This is the content-addressed identity of a tool version.
    
    Args:
        tool_id: Tool identifier
        version: Semver version string
        manifest: Tool manifest dict
        files: List of file dicts with {path, sha256}
        
    Returns:
        SHA256 hex digest (64 characters)
    """
    # Sort files for determinism
    sorted_files = []
    if files:
        sorted_files = sorted(files, key=lambda f: f.get("path", ""))
        sorted_files = [
            {
                "path": f.get("path", ""),
                "sha256": f.get("sha256", "")
            }
            for f in sorted_files
        ]
    
    # Build canonical payload
    payload = {
        "tool_id": tool_id,
        "version": version,
        "manifest": manifest,
        "files": sorted_files
    }
    
    # Canonical JSON: sorted keys, no extra whitespace
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_file_hash(content: str) -> str:
    """
    Compute SHA256 hash of file content.
    
    Args:
        content: File content as string
        
    Returns:
        SHA256 hex digest
    """
    return hashlib.sha256(content.encode()).hexdigest()


def verify_file_integrity(content: str, expected_hash: str) -> bool:
    """
    Verify file content matches expected hash.
    
    Args:
        content: File content to verify
        expected_hash: Expected SHA256 hex digest
        
    Returns:
        True if hash matches
    """
    return compute_file_hash(content) == expected_hash


def short_hash(full_hash: str, length: int = 12) -> str:
    """
    Return shortened hash for display purposes.
    
    Args:
        full_hash: Full hex digest
        length: Number of characters to return
        
    Returns:
        First `length` characters of hash
    """
    return full_hash[:length]


# =============================================================================
# Directive Integrity
# =============================================================================


def compute_directive_integrity(
    directive_name: str,
    version: str,
    xml_content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute deterministic integrity hash for a directive version.
    
    The integrity changes if ANY relevant byte changes in the directive.
    
    Args:
        directive_name: Directive identifier (e.g., "research_topic")
        version: Semver version string
        xml_content: The XML directive content (extracted from markdown)
        metadata: Optional metadata dict (category, author, model_tier, etc.)
        
    Returns:
        SHA256 hex digest (64 characters)
    """
    # Compute hash of XML content for determinism
    xml_hash = hashlib.sha256(xml_content.encode()).hexdigest()
    
    # Build canonical payload
    payload = {
        "directive_name": directive_name,
        "version": version,
        "xml_hash": xml_hash,
        "metadata": metadata or {},
    }
    
    # Canonical JSON: sorted keys, no extra whitespace
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_directive_integrity(
    directive_name: str,
    version: str,
    xml_content: str,
    stored_hash: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Verify directive content matches stored integrity hash.
    
    Args:
        directive_name: Directive identifier
        version: Version string
        xml_content: The XML directive content
        stored_hash: Expected integrity hash
        metadata: Optional metadata dict
        
    Returns:
        True if computed hash matches stored hash
    """
    computed = compute_directive_integrity(directive_name, version, xml_content, metadata)
    return computed == stored_hash


# =============================================================================
# Knowledge Integrity
# =============================================================================


def compute_knowledge_integrity(
    zettel_id: str,
    version: str,
    content: str,
    frontmatter: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute deterministic integrity hash for a knowledge entry version.
    
    The integrity changes if ANY relevant byte changes in the entry.
    
    Args:
        zettel_id: Zettel identifier (e.g., "20260124-api-patterns")
        version: Semver version string
        content: The markdown content (after frontmatter)
        frontmatter: Frontmatter dict (excluding validation fields)
        
    Returns:
        SHA256 hex digest (64 characters)
    """
    # Compute hash of content for determinism
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    
    # Clean frontmatter: remove validation fields that would cause circular dependency
    clean_frontmatter = {}
    if frontmatter:
        for key, value in frontmatter.items():
            if key not in ("validated_at", "content_hash", "integrity"):
                clean_frontmatter[key] = value
    
    # Build canonical payload
    payload = {
        "zettel_id": zettel_id,
        "version": version,
        "content_hash": content_hash,
        "frontmatter": clean_frontmatter,
    }
    
    # Canonical JSON: sorted keys, no extra whitespace
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_knowledge_integrity(
    zettel_id: str,
    version: str,
    content: str,
    stored_hash: str,
    frontmatter: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Verify knowledge entry content matches stored integrity hash.
    
    Args:
        zettel_id: Zettel identifier
        version: Version string
        content: The markdown content
        stored_hash: Expected integrity hash
        frontmatter: Frontmatter dict
        
    Returns:
        True if computed hash matches stored hash
    """
    computed = compute_knowledge_integrity(zettel_id, version, content, frontmatter)
    return computed == stored_hash
