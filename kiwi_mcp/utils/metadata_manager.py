"""
Centralized Metadata Management

Provides unified interface for parsing, validation, and hashing operations
across directives, scripts, and knowledge entries.
"""

import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from kiwi_mcp.utils.parsers import (
    parse_directive_file,
    parse_knowledge_file,
    parse_knowledge_entry,
    parse_script_metadata,
)
from kiwi_mcp.utils.signature_formats import get_signature_format


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content (full 64 characters)."""
    return hashlib.sha256(content.encode()).hexdigest()


def compute_unified_integrity(
    item_type: str,
    item_id: str,
    version: str,
    file_content: str,
    file_path: Path,
    metadata: Optional[Dict] = None,
) -> str:
    """
    Compute unified integrity hash using integrity.py functions.

    This computes the same hash that would be stored in the registry,
    ensuring consistency between local files and registry.

    Args:
        item_type: Type of item ('tool', 'directive', 'knowledge')
        item_id: Item identifier (tool_id, directive_name, id)
        version: Version string
        file_content: Full file content as string
        file_path: Path to the file
        metadata: Optional metadata dict (for directives/knowledge)

    Returns:
        Full 64-character SHA256 integrity hash
    """
    from kiwi_mcp.primitives.integrity import (
        compute_tool_integrity,
        compute_directive_integrity,
        compute_knowledge_integrity,
    )
    from kiwi_mcp.schemas.tool_schema import extract_tool_metadata
    from kiwi_mcp.utils.parsers import parse_knowledge_entry

    if item_type == "tool":
        # Include signature in hash computation (creates validation chain)
        manifest = extract_tool_metadata(file_path, file_path.parent)
        file_hash = hashlib.sha256(file_content.encode()).hexdigest()
        file_entry = {"path": file_path.name, "sha256": file_hash}
        return compute_tool_integrity(item_id, version, manifest, [file_entry])

    elif item_type == "directive":
        xml_content = DirectiveMetadataStrategy().extract_content_for_hash(file_content)
        return compute_directive_integrity(item_id, version, xml_content, metadata)

    elif item_type == "knowledge":
        parsed = parse_knowledge_entry(file_path)
        metadata = {
            "category": parsed.get("category"),
            "entry_type": parsed.get("entry_type"),
            "tags": parsed.get("tags", []),
        }
        return compute_knowledge_integrity(item_id, version, parsed.get("content", ""), metadata)

    else:
        raise ValueError(f"Unknown item_type: {item_type}")


def generate_timestamp() -> str:
    """Generate ISO format timestamp in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MetadataStrategy(ABC):
    """Base strategy for item-type-specific metadata operations."""

    @abstractmethod
    def extract_content_for_hash(self, file_content: str) -> str:
        """Extract the content portion that should be hashed."""

    @abstractmethod
    def format_signature(self, timestamp: str, hash: str) -> str:
        """Format signature according to item type."""

    @abstractmethod
    def extract_signature(self, file_content: str) -> Optional[Dict[str, str]]:
        """Extract signature from file content. Returns None if no signature found."""

    @abstractmethod
    def insert_signature(self, content: str, signature: str) -> str:
        """Insert signature into content."""

    @abstractmethod
    def remove_signature(self, content: str) -> str:
        """Remove existing signature from content."""


class DirectiveMetadataStrategy(MetadataStrategy):
    """Strategy for directive metadata operations (XML in markdown)."""

    def extract_content_for_hash(self, file_content: str) -> str:
        """Extract XML directive from markdown for hashing."""
        xml_content = self._extract_xml_from_content(file_content)
        if not xml_content:
            raise ValueError("No XML directive found in content")
        return xml_content

    def format_signature(self, timestamp: str, hash: str) -> str:
        """Format signature as HTML comment."""
        return f"<!-- kiwi-mcp:validated:{timestamp}:{hash} -->\n"

    def extract_signature(self, file_content: str) -> Optional[Dict[str, str]]:
        """Extract signature from HTML comment at start of file."""
        sig_match = re.match(r"^<!-- kiwi-mcp:validated:(.*?):([a-f0-9]{64}) -->", file_content)
        if not sig_match:
            return None

        return {
            "timestamp": sig_match.group(1),
            "hash": sig_match.group(2),
        }

    def insert_signature(self, content: str, signature: str) -> str:
        """Insert signature at the beginning of content."""
        # Remove old signature if present
        content_clean = self.remove_signature(content)
        return signature + content_clean

    def remove_signature(self, content: str) -> str:
        """Remove signature HTML comment from start of file."""
        return re.sub(r"^<!-- kiwi-mcp:validated:[^>]+-->\n", "", content)

    def _extract_xml_from_content(self, content: str) -> Optional[str]:
        """Extract XML directive from markdown content."""
        start_match = re.search(r"<directive[^>]*>", content)
        if not start_match:
            return None

        start_idx = start_match.start()
        end_tag = "</directive>"
        end_idx = content.rfind(end_tag)
        if end_idx == -1 or end_idx < start_idx:
            return None

        return content[start_idx : end_idx + len(end_tag)].strip()


class ToolMetadataStrategy(MetadataStrategy):
    """Strategy for tool metadata operations (language-aware)."""

    def __init__(self, file_path: Optional[Path] = None, project_path: Optional[Path] = None):
        """
        Initialize tool metadata strategy.

        Args:
            file_path: Path to the tool file (for determining signature format)
            project_path: Optional project path for extractor discovery
        """
        self.file_path = file_path
        self.project_path = project_path
        self._sig_format = None

    def _get_signature_format(self) -> Dict[str, Any]:
        """Get signature format for the tool file."""
        if self._sig_format is None:
            if self.file_path:
                self._sig_format = get_signature_format(self.file_path, self.project_path)
            else:
                # Default to Python-style if no file path provided
                self._sig_format = {"prefix": "#", "after_shebang": True}
        return self._sig_format

    def extract_content_for_hash(self, file_content: str) -> str:
        """Extract tool content for hashing (without signature)."""
        # Remove signature line to compute hash
        content_without_sig = self.remove_signature(file_content)
        # Also remove shebang if present (for consistent hashing)
        content_without_sig = re.sub(r"^#!/[^\n]*\n", "", content_without_sig)
        return content_without_sig

    def format_signature(self, timestamp: str, hash: str) -> str:
        """Format signature using file-type-specific comment syntax."""
        sig_format = self._get_signature_format()
        prefix = sig_format["prefix"]
        return f"{prefix} kiwi-mcp:validated:{timestamp}:{hash}\n"

    def extract_signature(self, file_content: str) -> Optional[Dict[str, str]]:
        """Extract signature using file-type-specific pattern."""
        sig_format = self._get_signature_format()
        prefix = re.escape(sig_format["prefix"])

        if sig_format.get("after_shebang", True):
            # Pattern: optional shebang, then signature
            sig_pattern = rf"^(?:#!/[^\n]*\n)?{prefix} kiwi-mcp:validated:(.*?):([a-f0-9]{{64}})"
        else:
            # Pattern: signature at start (no shebang expected)
            sig_pattern = rf"^{prefix} kiwi-mcp:validated:(.*?):([a-f0-9]{{64}})"

        sig_match = re.match(sig_pattern, file_content)
        if not sig_match:
            return None

        return {
            "timestamp": sig_match.group(1),
            "hash": sig_match.group(2),
        }

    def insert_signature(self, content: str, signature: str) -> str:
        """Insert signature after shebang (if present) or at start."""
        sig_format = self._get_signature_format()

        # Remove old signature if present
        content_clean = self.remove_signature(content)

        # Insert signature after shebang if configured and present
        if sig_format.get("after_shebang", True) and content_clean.startswith("#!/"):
            # Insert after shebang
            lines = content_clean.split("\n", 1)
            return lines[0] + "\n" + signature + (lines[1] if len(lines) > 1 else "")
        else:
            # Insert at start
            return signature + content_clean

    def remove_signature(self, content: str) -> str:
        """Remove signature using file-type-specific pattern."""
        sig_format = self._get_signature_format()
        prefix = re.escape(sig_format["prefix"])

        # Remove shebang if present
        content_without_shebang = re.sub(r"^#!/[^\n]*\n", "", content)

        # Remove signature line
        sig_pattern = rf"^{prefix} kiwi-mcp:validated:[^\n]+\n"
        content_without_sig = re.sub(sig_pattern, "", content_without_shebang)

        # Restore shebang if it was there
        shebang_match = re.match(r"^(#!/[^\n]*\n)", content)
        if shebang_match:
            return shebang_match.group(1) + content_without_sig
        return content_without_sig


class KnowledgeMetadataStrategy(MetadataStrategy):
    """Strategy for knowledge metadata operations (signature at top like directives)."""

    def extract_content_for_hash(self, file_content: str) -> str:
        """Extract content portion (after signature and frontmatter) for hashing."""
        # Remove signature line if present
        content_without_sig = self.remove_signature(file_content)

        # Extract content after frontmatter
        if not content_without_sig.startswith("---"):
            return content_without_sig

        end_idx = content_without_sig.find("---", 3)
        if end_idx == -1:
            return content_without_sig

        entry_content = content_without_sig[end_idx + 3 :].strip()
        return entry_content

    def format_signature(self, timestamp: str, hash: str) -> str:
        """Format signature as HTML comment at top of file."""
        return f"<!-- kiwi-mcp:validated:{timestamp}:{hash} -->\n"

    def extract_signature(self, file_content: str) -> Optional[Dict[str, str]]:
        """Extract signature from HTML comment at start of file."""
        sig_match = re.match(r"^<!-- kiwi-mcp:validated:(.*?):([a-f0-9]{64}) -->", file_content)
        if not sig_match:
            return None

        return {
            "timestamp": sig_match.group(1),
            "hash": sig_match.group(2),
        }

    def insert_signature(self, content: str, signature: str) -> str:
        """Insert signature at the beginning of content."""
        content_clean = self.remove_signature(content)
        return signature + content_clean

    def remove_signature(self, content: str) -> str:
        """Remove signature HTML comment from start of file."""
        return re.sub(r"^<!-- kiwi-mcp:validated:[^>]+-->\n", "", content)


class MetadataManager:
    """Unified metadata management interface."""

    @classmethod
    def get_strategy(
        cls, item_type: str, file_path: Optional[Path] = None, project_path: Optional[Path] = None
    ) -> MetadataStrategy:
        """
        Get metadata strategy for item type.

        Args:
            item_type: Type of item ('directive', 'tool', 'knowledge')
            file_path: Optional path to file (required for tool type to determine signature format)
            project_path: Optional project path for extractor discovery
        """
        if item_type == "directive":
            return DirectiveMetadataStrategy()
        elif item_type == "tool":
            return ToolMetadataStrategy(file_path=file_path, project_path=project_path)
        elif item_type == "knowledge":
            return KnowledgeMetadataStrategy()
        else:
            raise ValueError(
                f"Unknown item_type: {item_type}. Supported: ['directive', 'tool', 'knowledge']"
            )

    @classmethod
    def parse_file(cls, item_type: str, file_path: Path) -> Dict[str, Any]:
        """Parse file using appropriate parser."""
        if item_type == "directive":
            return parse_directive_file(file_path)
        elif item_type == "tool":
            return parse_script_metadata(file_path)
        elif item_type == "knowledge":
            return parse_knowledge_entry(file_path)
        else:
            raise ValueError(f"Unknown item_type: {item_type}")

    @classmethod
    def compute_hash(
        cls,
        item_type: str,
        file_content: str,
        file_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute hash of content using appropriate strategy."""
        strategy = cls.get_strategy(item_type, file_path=file_path, project_path=project_path)
        content_for_hash = strategy.extract_content_for_hash(file_content)
        return compute_content_hash(content_for_hash)

    @classmethod
    def create_signature(
        cls,
        item_type: str,
        file_content: str,
        file_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> str:
        """Create signature for content."""
        strategy = cls.get_strategy(item_type, file_path=file_path, project_path=project_path)
        content_for_hash = strategy.extract_content_for_hash(file_content)
        content_hash = compute_content_hash(content_for_hash)
        timestamp = generate_timestamp()
        return strategy.format_signature(timestamp, content_hash)

    @classmethod
    def create_signature_from_hash(
        cls,
        item_type: str,
        content_hash: str,
        file_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> str:
        """Create signature using a precomputed integrity hash."""
        strategy = cls.get_strategy(item_type, file_path=file_path, project_path=project_path)
        timestamp = generate_timestamp()
        return strategy.format_signature(timestamp, content_hash)

    @classmethod
    def get_signature_hash(
        cls,
        item_type: str,
        file_content: str,
        file_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> Optional[str]:
        """
        Extract integrity hash from signature without verification.

        Use this when you just need the stored hash (e.g., for chain building).
        For actual integrity verification, use IntegrityVerifier.

        Args:
            item_type: Type of item ('tool', 'directive', 'knowledge')
            file_content: File content with signature
            file_path: Path to file (required for tools)
            project_path: Project root path

        Returns:
            Full 64-character integrity hash, or None if no signature found
        """
        signature_data = cls.get_signature_info(item_type, file_content, file_path, project_path)
        return signature_data["hash"] if signature_data else None

    @classmethod
    def sign_content(
        cls,
        item_type: str,
        file_content: str,
        file_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> str:
        """Add signature to content."""
        strategy = cls.get_strategy(item_type, file_path=file_path, project_path=project_path)
        signature = cls.create_signature(
            item_type, file_content, file_path=file_path, project_path=project_path
        )
        return strategy.insert_signature(file_content, signature)

    @classmethod
    def sign_content_with_hash(
        cls,
        item_type: str,
        file_content: str,
        content_hash: str,
        file_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> str:
        """Add signature to content using a precomputed integrity hash."""
        strategy = cls.get_strategy(item_type, file_path=file_path, project_path=project_path)
        signature = cls.create_signature_from_hash(
            item_type, content_hash, file_path=file_path, project_path=project_path
        )
        return strategy.insert_signature(file_content, signature)

    @classmethod
    def get_signature_info(
        cls,
        item_type: str,
        file_content: str,
        file_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> Optional[Dict[str, str]]:
        """Get signature information without verification."""
        strategy = cls.get_strategy(item_type, file_path=file_path, project_path=project_path)
        return strategy.extract_signature(file_content)
