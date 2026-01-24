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
    parse_knowledge_entry,
    parse_script_metadata,
)


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content (first 12 hex characters)."""
    return hashlib.sha256(content.encode()).hexdigest()[:12]


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
        sig_match = re.match(r"^<!-- kiwi-mcp:validated:(.*?):([a-f0-9]{12}) -->", file_content)
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
        start_match = re.search(r'<directive[^>]*>', content)
        if not start_match:
            return None

        start_idx = start_match.start()
        end_tag = '</directive>'
        end_idx = content.rfind(end_tag)
        if end_idx == -1 or end_idx < start_idx:
            return None

        return content[start_idx:end_idx + len(end_tag)].strip()


class ToolMetadataStrategy(MetadataStrategy):
    """Strategy for tool metadata operations (Python files)."""

    def extract_content_for_hash(self, file_content: str) -> str:
        """Extract tool content for hashing (without signature)."""
        # Remove signature line to compute hash
        content_without_sig = self.remove_signature(file_content)
        # Also remove shebang if present (for consistent hashing)
        content_without_sig = re.sub(r"^#!/[^\n]*\n", "", content_without_sig)
        return content_without_sig

    def format_signature(self, timestamp: str, hash: str) -> str:
        """Format signature as Python comment."""
        return f"# kiwi-mcp:validated:{timestamp}:{hash}\n"

    def extract_signature(self, file_content: str) -> Optional[Dict[str, str]]:
        """Extract signature from Python comment (after optional shebang)."""
        sig_pattern = r"^(?:#!/[^\n]*\n)?# kiwi-mcp:validated:(.*?):([a-f0-9]{12})"
        sig_match = re.match(sig_pattern, file_content)

        if not sig_match:
            return None

        return {
            "timestamp": sig_match.group(1),
            "hash": sig_match.group(2),
        }

    def insert_signature(self, content: str, signature: str) -> str:
        """Insert signature after shebang (if present) or at start."""
        # Remove old signature if present
        content_clean = self.remove_signature(content)

        if content_clean.startswith("#!/"):
            # Insert after shebang
            lines = content_clean.split("\n", 1)
            return lines[0] + "\n" + signature + (lines[1] if len(lines) > 1 else "")
        else:
            # Insert at start
            return signature + content_clean

    def remove_signature(self, content: str) -> str:
        """Remove signature Python comment from file."""
        # Remove shebang if present
        content_without_shebang = re.sub(r"^#!/[^\n]*\n", "", content)
        # Remove signature line
        content_without_sig = re.sub(r"^# kiwi-mcp:validated:[^\n]+\n", "", content_without_shebang)
        # Restore shebang if it was there
        shebang_match = re.match(r"^(#!/[^\n]*\n)", content)
        if shebang_match:
            return shebang_match.group(1) + content_without_sig
        return content_without_sig


class KnowledgeMetadataStrategy(MetadataStrategy):
    """Strategy for knowledge metadata operations (YAML frontmatter in markdown)."""

    def extract_content_for_hash(self, file_content: str) -> str:
        """Extract content portion (after frontmatter) for hashing."""
        if not file_content.startswith("---"):
            return file_content

        end_idx = file_content.find("---", 3)
        if end_idx == -1:
            return file_content

        # Extract content after frontmatter
        entry_content = file_content[end_idx + 3:].strip()
        return entry_content

    def format_signature(self, timestamp: str, hash: str) -> str:
        """Format signature as YAML frontmatter fields (not standalone)."""
        # This is used when creating/updating frontmatter
        # The full frontmatter is created in the handler
        return f"validated_at: {timestamp}\ncontent_hash: {hash}"

    def extract_signature(self, file_content: str) -> Optional[Dict[str, str]]:
        """Extract signature from YAML frontmatter."""
        if not file_content.startswith("---"):
            return None

        end_idx = file_content.find("---", 3)
        if end_idx == -1:
            return None

        yaml_content = file_content[3:end_idx].strip()

        # Parse frontmatter for signature fields
        stored_timestamp = None
        stored_hash = None

        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "validated_at":
                    stored_timestamp = value
                elif key == "content_hash":
                    stored_hash = value

        if not stored_timestamp or not stored_hash:
            return None

        return {
            "timestamp": stored_timestamp,
            "hash": stored_hash,
        }

    def insert_signature(self, content: str, signature: str) -> str:
        """Insert signature into YAML frontmatter."""
        # For knowledge entries, signature is part of frontmatter
        # This method is not typically used directly - frontmatter is rebuilt in handler
        # But we provide it for consistency
        if not content.startswith("---"):
            # No frontmatter, create one
            return f"---\n{signature}\n---\n\n{content}"

        # Update existing frontmatter
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return content

        yaml_content = content[3:end_idx].strip()
        entry_content = content[end_idx + 3:].strip()

        # Update or add signature fields
        lines = yaml_content.split("\n")
        updated_lines = []
        has_validated_at = False
        has_content_hash = False

        for line in lines:
            if line.startswith("validated_at:"):
                updated_lines.append(f"validated_at: {signature.split('validated_at: ')[1].split('\\n')[0]}")
                has_validated_at = True
            elif line.startswith("content_hash:"):
                updated_lines.append(f"content_hash: {signature.split('content_hash: ')[1].split('\\n')[0]}")
                has_content_hash = True
            else:
                updated_lines.append(line)

        # Add missing fields
        sig_lines = signature.split("\n")
        for sig_line in sig_lines:
            if sig_line.startswith("validated_at:") and not has_validated_at:
                updated_lines.append(sig_line)
            elif sig_line.startswith("content_hash:") and not has_content_hash:
                updated_lines.append(sig_line)

        updated_yaml = "\n".join(updated_lines)
        return f"---\n{updated_yaml}\n---\n\n{entry_content}"

    def remove_signature(self, content: str) -> str:
        """Remove signature fields from YAML frontmatter."""
        if not content.startswith("---"):
            return content

        end_idx = content.find("---", 3)
        if end_idx == -1:
            return content

        yaml_content = content[3:end_idx].strip()
        entry_content = content[end_idx + 3:].strip()

        # Remove signature fields
        lines = [line for line in yaml_content.split("\n") 
                 if not line.strip().startswith("validated_at:") 
                 and not line.strip().startswith("content_hash:")]

        updated_yaml = "\n".join(lines)
        return f"---\n{updated_yaml}\n---\n\n{entry_content}"


class MetadataManager:
    """Unified metadata management interface."""

    STRATEGIES = {
        "directive": DirectiveMetadataStrategy(),
        "tool": ToolMetadataStrategy(),
        "knowledge": KnowledgeMetadataStrategy(),
    }

    @classmethod
    def get_strategy(cls, item_type: str) -> MetadataStrategy:
        """Get metadata strategy for item type."""
        strategy = cls.STRATEGIES.get(item_type)
        if not strategy:
            raise ValueError(f"Unknown item_type: {item_type}. Supported: {list(cls.STRATEGIES.keys())}")
        return strategy

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
    def compute_hash(cls, item_type: str, file_content: str) -> str:
        """Compute hash of content using appropriate strategy."""
        strategy = cls.get_strategy(item_type)
        content_for_hash = strategy.extract_content_for_hash(file_content)
        return compute_content_hash(content_for_hash)

    @classmethod
    def create_signature(cls, item_type: str, file_content: str) -> str:
        """Create signature for content."""
        strategy = cls.get_strategy(item_type)
        content_for_hash = strategy.extract_content_for_hash(file_content)
        content_hash = compute_content_hash(content_for_hash)
        timestamp = generate_timestamp()
        return strategy.format_signature(timestamp, content_hash)

    @classmethod
    def verify_signature(cls, item_type: str, file_content: str) -> Optional[Dict[str, Any]]:
        """
        Verify signature in file content.
        
        Returns:
            None if no signature found
            {"status": "valid", "validated_at": str, "hash": str} if valid
            {"status": "modified", "validated_at": str, "original_hash": str, "current_hash": str, "warning": str} if modified
            {"status": "invalid", "reason": str} if invalid format
        """
        strategy = cls.get_strategy(item_type)
        signature_data = strategy.extract_signature(file_content)

        if not signature_data:
            return None

        stored_timestamp = signature_data["timestamp"]
        stored_hash = signature_data["hash"]

        # Extract content for hashing
        try:
            content_for_hash = strategy.extract_content_for_hash(file_content)
        except ValueError as e:
            return {"status": "invalid", "reason": str(e)}

        current_hash = compute_content_hash(content_for_hash)

        if current_hash == stored_hash:
            return {
                "status": "valid",
                "validated_at": stored_timestamp,
                "hash": stored_hash,
            }
        else:
            return {
                "status": "modified",
                "validated_at": stored_timestamp,
                "original_hash": stored_hash,
                "current_hash": current_hash,
                "warning": "Content modified since last validation. Consider running 'update' to re-validate.",
            }

    @classmethod
    def sign_content(cls, item_type: str, file_content: str) -> str:
        """Add signature to content."""
        strategy = cls.get_strategy(item_type)
        signature = cls.create_signature(item_type, file_content)
        return strategy.insert_signature(file_content, signature)

    @classmethod
    def get_signature_info(cls, item_type: str, file_content: str) -> Optional[Dict[str, str]]:
        """Get signature information without verification."""
        strategy = cls.get_strategy(item_type)
        return strategy.extract_signature(file_content)
