"""
RYE Knowledge Handler - Intelligence layer for knowledge parsing and validation.

Migrated from Lilux to RYE to maintain clean microkernel separation.
Contains ALL knowledge intelligence moved from Lilux kernel.
"""

import hashlib
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from lilux.utils.logger import get_logger
except ImportError:
    # Fallback for testing without Lilux
    import logging

    def get_logger(name):
        return logging.getLogger(name)


class KnowledgeHandler:
    """Intelligent handler for knowledge content parsing and validation."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.logger = get_logger("rye_knowledge_handler")

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse knowledge markdown with frontmatter.

        Args:
            file_path: Path to knowledge file

        Returns:
            Parsed knowledge data structure
        """
        try:
            content = file_path.read_text()
            return self._parse_knowledge_entry(content)
        except Exception as e:
            self.logger.error(f"Failed to parse knowledge {file_path}: {e}")
            raise

    def validate(self, parsed: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """
        Validate knowledge structure and frontmatter.

        Args:
            parsed: Parsed knowledge data
            file_path: Path to knowledge file

        Returns:
            Validation result with issues if any
        """
        issues = []
        warnings = []

        # Validate required fields
        required_fields = ["id", "title", "entry_type"]
        for field in required_fields:
            if not parsed.get(field):
                issues.append(f"Missing required field: {field}")

        # Validate ID format
        entry_id = parsed.get("id", "")
        if entry_id and not re.match(r"^[a-z0-9][a-z0-9_-]*$", entry_id):
            warnings.append(
                f"ID should use lowercase, numbers, underscores, and hyphens: {entry_id}"
            )

        # Validate entry_type
        entry_type = parsed.get("entry_type", "")
        valid_types = [
            "pattern",
            "learning",
            "reference",
            "concept",
            "decision",
            "insight",
            "procedure",
            "api_fact",
            "experiment",
            "template",
            "workflow",
        ]
        if entry_type and entry_type not in valid_types:
            warnings.append(
                f"Unknown entry type: {entry_type}. Valid types: {', '.join(valid_types)}"
            )

        # Validate version format
        version = parsed.get("version", "")
        if version and not re.match(r"^\d+\.\d+\.\d+$", version):
            issues.append(f"Invalid version format: {version}. Expected: X.Y.Z")

        # Validate tags
        tags = parsed.get("tags", [])
        if tags and not isinstance(tags, list):
            issues.append("Tags must be a list")
        elif tags:
            for i, tag in enumerate(tags):
                if not isinstance(tag, str):
                    issues.append(f"Tag {i} must be a string")

        # Validate content
        content = parsed.get("content", "")
        if not content.strip():
            warnings.append("Knowledge content is empty")

        # Validate schema if present
        schema = parsed.get("schema")
        if schema and not isinstance(schema, dict):
            issues.append("Schema must be a JSON Schema dictionary")

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def compute_integrity(self, parsed: Dict[str, Any], content: str) -> str:
        """
        Compute canonical integrity hash for a knowledge entry.

        Args:
            parsed: Parsed knowledge data
            content: Raw file content

        Returns:
            SHA256 hex digest (64 characters)
        """
        # Extract frontmatter and content for hashing
        frontmatter, body = self._extract_content_for_hash(content)

        # Build canonical content for hashing
        metadata = {
            "id": parsed.get("id", ""),
            "version": parsed.get("version", "1.0.0"),
            "title": parsed.get("title", ""),
            "entry_type": parsed.get("entry_type", ""),
            "category": parsed.get("category", ""),
        }

        # Create canonical representation
        canonical_parts = [
            f"id:{metadata['id']}",
            f"version:{metadata['version']}",
            f"title:{metadata['title']}",
            f"entry_type:{metadata['entry_type']}",
            f"category:{metadata['category']}",
            f"frontmatter:{frontmatter}",
            f"content:{body}",
        ]

        canonical_content = "|".join(canonical_parts)
        return hashlib.sha256(canonical_content.encode()).hexdigest()

    def extract_signature(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract signature from content.

        Args:
            content: File content with potential signature

        Returns:
            Signature data if found, None otherwise
        """
        # Look for signature comment at end of file
        signature_pattern = r"<!--\s*kiwi-mcp:validated:([^:]+):([^:]+):([^\s]+)\s*-->"
        match = re.search(signature_pattern, content)

        if match:
            return {
                "hash": match.group(1),
                "signature": match.group(2),
                "item_id": match.group(3),
                "format": "kiwi-mcp",
            }

        return None

    def add_signature(self, content: str, hash: str) -> str:
        """
        Add signature to content.

        Args:
            content: Original content
            hash: Computed hash to sign

        Returns:
            Content with signature added
        """
        # Remove existing signature
        content = self._remove_existing_signature(content)

        # Add new signature
        signature = (
            f"\n<!-- kiwi-mcp:validated:{hash}:SIGNATURE:{self._extract_item_id(content)} -->"
        )
        return content + signature

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from knowledge content.

        Args:
            content: Raw file content

        Returns:
            Dict with extracted metadata
        """
        parsed = self._parse_knowledge_entry(content)

        metadata = {
            "id": parsed.get("id", ""),
            "title": parsed.get("title", ""),
            "entry_type": parsed.get("entry_type", ""),
            "category": parsed.get("category", ""),
            "version": parsed.get("version", "1.0.0"),
            "author": parsed.get("author", ""),
            "tags": parsed.get("tags", []),
            "references": parsed.get("references", []),
            "extends": parsed.get("extends", []),
            "created_at": parsed.get("created_at"),
            "updated_at": parsed.get("updated_at"),
        }

        return metadata

    def _parse_knowledge_entry(self, content: str) -> Dict[str, Any]:
        """
        Parse knowledge markdown with frontmatter.

        Args:
            content: Markdown file content

        Returns:
            Parsed knowledge structure
        """
        # Remove signature first
        content = self._remove_existing_signature(content)

        # Check for frontmatter
        if not content.startswith("---"):
            # No frontmatter, treat as plain content
            return {
                "content": content.strip(),
            }

        # Split frontmatter and content
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid frontmatter format")

        frontmatter_str = parts[1].strip()
        body = parts[2].strip()

        # Parse YAML frontmatter
        try:
            frontmatter = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}")

        result = frontmatter.copy()
        result["content"] = body

        return result

    def _extract_content_for_hash(self, content: str) -> tuple[str, str]:
        """
        Extract frontmatter and body for hashing.

        Args:
            content: Full file content

        Returns:
            Tuple of (frontmatter_str, body_str)
        """
        # Remove signature
        content = self._remove_existing_signature(content)

        # Check for frontmatter
        if not content.startswith("---"):
            # No frontmatter
            return "", content.strip()

        # Split frontmatter and content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return "", content.strip()

        frontmatter_str = parts[1].strip()
        body = parts[2].strip()

        return frontmatter_str, body

    def _remove_existing_signature(self, content: str) -> str:
        """Remove existing signature from content."""
        signature_pattern = r"\n<!--\s*kiwi-mcp:validated:.*?-->"
        return re.sub(signature_pattern, "", content, flags=re.DOTALL)

    def _extract_item_id(self, content: str) -> str:
        """Extract item ID from knowledge content."""
        try:
            parsed = self._parse_knowledge_entry(content)
            return parsed.get("id", "")
        except:
            return ""
