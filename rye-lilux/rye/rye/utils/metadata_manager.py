"""
RYE Metadata Manager - Centralized metadata extraction, validation, and integrity.

This implements the intelligence layer for metadata management, signature handling,
and content integrity across directives, tools, and knowledge entries.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import hashlib
import re
import json
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation operations."""

    valid: bool
    issues: List[str]
    warnings: List[str]


class BaseMetadataStrategy(ABC):
    """Base class for metadata strategies."""

    @abstractmethod
    def extract_content_for_hash(self, content: str) -> str:
        """Extract canonical content for hashing."""

    @abstractmethod
    def remove_signature(self, content: str) -> str:
        """Remove signature from content."""

    @abstractmethod
    def add_signature(self, content: str, signature: str) -> str:
        """Add signature to content."""

    @abstractmethod
    def extract_signature(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract signature from content."""

    @abstractmethod
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content."""


class DirectiveMetadataStrategy(BaseMetadataStrategy):
    """Strategy for directive metadata (XML parsing)."""

    def extract_content_for_hash(self, content: str) -> str:
        """Extract canonical content for hashing (remove signatures)."""
        # Remove signature blocks from directive content
        signature_pattern = r"<!--\s*kiwi-mcp:validated:[^>]*-->"
        return re.sub(signature_pattern, "", content, flags=re.DOTALL)

    def remove_signature(self, content: str) -> str:
        """Remove signature from directive content."""
        signature_pattern = r"<!--\s*kiwi-mcp:validated:[^>]*-->"
        return re.sub(signature_pattern, "", content, flags=re.DOTALL)

    def add_signature(self, content: str, signature: str) -> str:
        """Add signature to directive content."""
        return f"{content}\n<!-- kiwi-mcp:validated:{signature} -->"

    def extract_signature(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract signature from directive content."""
        signature_pattern = r"<!--\s*kiwi-mcp:validated:([^>]+)-->"
        match = re.search(signature_pattern, content)
        if match:
            signature_data = match.group(1).split(":")
            if len(signature_data) >= 2:
                return {"hash": signature_data[0], "signature": signature_data[1]}
        return None

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from directive XML."""
        metadata = {}

        # Extract name from directive tag
        name_match = re.search(r'<directive\s+name="([^"]+)"', content)
        if name_match:
            metadata["name"] = name_match.group(1)

        # Extract description from description tag
        desc_match = re.search(r"<description>(.*?)</description>", content, re.DOTALL)
        if desc_match:
            metadata["description"] = desc_match.group(1).strip()

        # Extract version from version tag
        version_match = re.search(r"<version>(.*?)</version>", content)
        if version_match:
            metadata["version"] = version_match.group(1).strip()

        # Extract author from author tag
        author_match = re.search(r"<author>(.*?)</author>", content)
        if author_match:
            metadata["author"] = author_match.group(1).strip()

        # Extract category from category tag
        category_match = re.search(r"<category>(.*?)</category>", content)
        if category_match:
            metadata["category"] = category_match.group(1).strip()

        # Extract required fields
        required_match = re.search(r"<required>(.*?)</required>", content, re.DOTALL)
        if required_match:
            required_str = required_match.group(1).strip()
            metadata["required"] = [
                field.strip() for field in required_str.split(",") if field.strip()
            ]

        # Extract model configuration
        model_match = re.search(r"<model>(.*?)</model>", content, re.DOTALL)
        if model_match:
            model_config = model_match.group(1).strip()
            metadata["model"] = model_config

        return metadata


class ToolMetadataStrategy(BaseMetadataStrategy):
    """Strategy for tool metadata (Python header parsing)."""

    def extract_content_for_hash(self, content: str) -> str:
        """Extract canonical content for hashing (remove signatures and metadata header)."""
        # Remove signature blocks
        signature_pattern = r"#\s*kiwi-mcp:validated:[^#]*"
        content = re.sub(signature_pattern, "", content, flags=re.DOTALL)

        # Remove metadata header (everything before the first non-comment line)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith("#"):
                return "\n".join(lines[i:])
        return content

    def remove_signature(self, content: str) -> str:
        """Remove signature from tool content."""
        signature_pattern = r"#\s*kiwi-mcp:validated:[^#]*"
        return re.sub(signature_pattern, "", content, flags=re.DOTALL)

    def add_signature(self, content: str, signature: str) -> str:
        """Add signature to tool content."""
        return f"{content}\n# kiwi-mcp:validated:{signature}"

    def extract_signature(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract signature from tool content."""
        signature_pattern = r"#\s*kiwi-mcp:validated:([^#]+)"
        match = re.search(signature_pattern, content)
        if match:
            signature_data = match.group(1).split(":")
            if len(signature_data) >= 2:
                return {"hash": signature_data[0], "signature": signature_data[1]}
        return None

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from tool Python file."""
        metadata = {}

        # Extract tool metadata header (everything between TOOL_METADATA and code)
        header_pattern = r"# TOOL_METADATA\n(.*?)\n\n"
        header_match = re.search(header_pattern, content, re.DOTALL)

        if header_match:
            header_content = header_match.group(1)
            for line in header_content.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

        # Extract tool name from function name or metadata
        name_match = re.search(r"def\s+(\w+)\s*\(", content)
        if name_match and "tool_name" not in metadata:
            metadata["tool_name"] = name_match.group(1)

        # Extract description from docstring or metadata
        if "description" not in metadata:
            docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if docstring_match:
                metadata["description"] = docstring_match.group(1).strip()

        return metadata


class KnowledgeMetadataStrategy(BaseMetadataStrategy):
    """Strategy for knowledge metadata (Markdown frontmatter parsing)."""

    def extract_content_for_hash(self, content: str) -> str:
        """Extract canonical content for hashing (remove signatures and frontmatter)."""
        # Remove signature blocks
        signature_pattern = r"<!--\s*kiwi-mcp:validated:[^>]*-->"
        content = re.sub(signature_pattern, "", content, flags=re.DOTALL)

        # Remove YAML frontmatter
        frontmatter_pattern = r"^---\n(.*?)\n---\n"
        return re.sub(frontmatter_pattern, "", content, flags=re.DOTALL | re.MULTILINE)

    def remove_signature(self, content: str) -> str:
        """Remove signature from knowledge content."""
        signature_pattern = r"<!--\s*kiwi-mcp:validated:[^>]*-->"
        return re.sub(signature_pattern, "", content, flags=re.DOTALL)

    def add_signature(self, content: str, signature: str) -> str:
        """Add signature to knowledge content."""
        return f"{content}\n<!-- kiwi-mcp:validated:{signature} -->"

    def extract_signature(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract signature from knowledge content."""
        signature_pattern = r"<!--\s*kiwi-mcp:validated:([^>]+)-->"
        match = re.search(signature_pattern, content)
        if match:
            signature_data = match.group(1).split(":")
            if len(signature_data) >= 2:
                return {"hash": signature_data[0], "signature": signature_data[1]}
        return None

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from knowledge markdown file."""
        metadata = {}

        # Extract YAML frontmatter
        frontmatter_pattern = r"^---\n(.*?)\n---\n"
        frontmatter_match = re.search(frontmatter_pattern, content, re.DOTALL | re.MULTILINE)

        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            try:
                metadata = yaml.safe_load(frontmatter) or {}
            except:
                # Fallback to manual parsing
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()

        # Extract title from frontmatter or first heading
        if "title" not in metadata:
            title_match = re.search(r"^#\s+(.*?)$", content, re.MULTILINE)
            if title_match:
                metadata["title"] = title_match.group(1).strip()

        # Extract summary from first paragraph
        if "summary" not in metadata:
            summary_match = re.search(r"^(.*?)\n\n", content, re.DOTALL)
            if summary_match:
                metadata["summary"] = summary_match.group(1).strip()

        return metadata


class MetadataManager:
    """Manage metadata extraction, validation, and integrity."""

    @staticmethod
    def get_strategy(item_type: str, **kwargs) -> BaseMetadataStrategy:
        """Get metadata strategy for item type."""
        strategies = {
            "directive": DirectiveMetadataStrategy(),
            "tool": ToolMetadataStrategy(),
            "knowledge": KnowledgeMetadataStrategy(),
        }

        if item_type not in strategies:
            raise ValueError(f"Unknown item type: {item_type}")

        return strategies[item_type]

    @staticmethod
    def extract_metadata(file_path: Path, item_type: str) -> Dict[str, Any]:
        """Extract metadata from content."""
        content = file_path.read_text()
        strategy = MetadataManager.get_strategy(item_type)
        return strategy.extract_metadata(content)

    @staticmethod
    def compute_integrity(item_type: str, content: str, **kwargs) -> str:
        """Compute unified integrity hash."""
        strategy = MetadataManager.get_strategy(item_type)
        canonical_content = strategy.extract_content_for_hash(content)
        return hashlib.sha256(canonical_content.encode()).hexdigest()

    @staticmethod
    def add_signature(content: str, hash: str, item_type: str) -> str:
        """Add signature to content."""
        strategy = MetadataManager.get_strategy(item_type)
        return strategy.add_signature(content, hash)

    @staticmethod
    def extract_signature(content: str, item_type: str) -> Optional[Dict[str, Any]]:
        """Extract signature from content."""
        strategy = MetadataManager.get_strategy(item_type)
        signature = strategy.extract_signature(content)
        if signature:
            return {"hash": signature}
        return None

    @staticmethod
    def get_signature_hash(content: str, item_type: str) -> Optional[str]:
        """Get hash from signature."""
        strategy = MetadataManager.get_strategy(item_type)
        signature = strategy.extract_signature(content)
        return signature.get("hash") if signature else None

    @staticmethod
    def validate_metadata(item_type: str, metadata: Dict[str, Any]) -> ValidationResult:
        """Validate metadata structure."""
        strategy = MetadataManager.get_strategy(item_type)
        # This would call specific validation logic for each strategy
        return ValidationResult(valid=True, issues=[], warnings=[])

    @staticmethod
    def sign_content(item_type: str, content: str, **kwargs) -> str:
        """Sign content with unified integrity hash."""
        content_hash = MetadataManager.compute_integrity(item_type, content)
        return MetadataManager.add_signature(content, content_hash, item_type)


# Import yaml if available for frontmatter parsing
try:
    import yaml
except ImportError:
    yaml = None
    print("Warning: PyYAML not available, knowledge frontmatter parsing may be limited")
