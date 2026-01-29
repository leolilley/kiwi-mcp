"""
Comprehensive tests for MetadataManager and all metadata strategies.

Tests hash computation, signature management, and content extraction
for directives, scripts, and knowledge entries.
"""

import pytest
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from lilux.utils.metadata_manager import (
    compute_content_hash,
    generate_timestamp,
    MetadataStrategy,
    DirectiveMetadataStrategy,
    ToolMetadataStrategy,
    KnowledgeMetadataStrategy,
    MetadataManager,
)


class TestHashUtilities:
    """Test hash and timestamp utility functions."""

    @pytest.mark.unit
    @pytest.mark.utils
    def test_compute_content_hash_returns_full_hash(self):
        """Should return full 64-character SHA256 hex hash."""
        content = "test content"
        hash_result = compute_content_hash(content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
        assert all(c in '0123456789abcdef' for c in hash_result)

    @pytest.mark.unit
    @pytest.mark.utils
    def test_compute_content_hash_is_deterministic(self):
        """Should return same hash for same content."""
        content = "test content"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        assert hash1 == hash2

    @pytest.mark.unit
    @pytest.mark.utils
    def test_compute_content_hash_different_for_different_content(self):
        """Should return different hash for different content."""
        hash1 = compute_content_hash("content 1")
        hash2 = compute_content_hash("content 2")

        assert hash1 != hash2

    @pytest.mark.unit
    @pytest.mark.utils
    def test_compute_content_hash_matches_sha256_full(self):
        """Should match full SHA256 hex digest."""
        content = "test content"
        expected = hashlib.sha256(content.encode()).hexdigest()
        actual = compute_content_hash(content)

        assert actual == expected

    @pytest.mark.unit
    @pytest.mark.utils
    def test_generate_timestamp_returns_iso_format(self):
        """Should return ISO format timestamp in UTC."""
        timestamp = generate_timestamp()

        assert isinstance(timestamp, str)
        assert "T" in timestamp
        assert timestamp.endswith("Z")
        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    @pytest.mark.unit
    @pytest.mark.utils
    def test_generate_timestamp_is_utc(self):
        """Should generate UTC timestamps."""
        timestamp = generate_timestamp()
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        assert parsed.tzinfo is not None
        assert parsed.tzinfo.utcoffset(None).total_seconds() == 0


class TestDirectiveMetadataStrategy:
    """Test DirectiveMetadataStrategy methods."""

    @pytest.fixture
    def strategy(self):
        """Create DirectiveMetadataStrategy instance."""
        return DirectiveMetadataStrategy()

    @pytest.fixture
    def sample_directive_markdown(self, sample_directive_content):
        """Create sample directive markdown with XML."""
        return f"""# Test Directive

```xml
{sample_directive_content}
```
"""

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_with_valid_xml(self, strategy, sample_directive_markdown, sample_directive_content):
        """Should extract XML from markdown for hashing."""
        xml_content = strategy.extract_content_for_hash(sample_directive_markdown)

        assert xml_content == sample_directive_content.strip()
        assert xml_content.startswith("<directive")
        assert xml_content.endswith("</directive>")

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_with_missing_xml(self, strategy):
        """Should raise ValueError when no XML found."""
        content = "# Just markdown\nNo XML here"

        with pytest.raises(ValueError, match="No XML directive found"):
            strategy.extract_content_for_hash(content)

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_with_incomplete_xml(self, strategy):
        """Should raise ValueError when XML is incomplete."""
        content = "# Test\n```xml\n<directive name=\"test\">\n```"

        with pytest.raises(ValueError, match="No XML directive found"):
            strategy.extract_content_for_hash(content)

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_format_signature_creates_html_comment(self, strategy):
        """Should format signature as HTML comment."""
        timestamp = "2024-01-01T12:00:00Z"
        hash_value = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        signature = strategy.format_signature(timestamp, hash_value)

        assert signature.startswith("<!--")
        assert signature.endswith("-->\n")
        assert timestamp in signature
        assert hash_value in signature
        assert "lilux:validated" in signature

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_with_valid_signature(self, strategy):
        """Should extract signature from HTML comment."""
        timestamp = "2024-01-01T12:00:00Z"
        hash_value = "a" * 64
        content = f"<!-- lilux:validated:{timestamp}:{hash_value} -->\n# Content"

        result = strategy.extract_signature(content)

        assert result is not None
        assert result["timestamp"] == timestamp
        assert result["hash"] == hash_value

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_with_missing_signature(self, strategy):
        """Should return None when no signature found."""
        content = "# Just content\nNo signature here"

        result = strategy.extract_signature(content)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_with_invalid_format(self, strategy):
        """Should return None for invalid signature format."""
        content = "<!-- lilux:invalid -->\n# Content"

        result = strategy.extract_signature(content)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_at_start(self, strategy, sample_directive_markdown):
        """Should insert signature at beginning of content."""
        signature = "<!-- lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->\n"

        result = strategy.insert_signature(sample_directive_markdown, signature)

        assert result.startswith(signature)
        assert sample_directive_markdown.strip() in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_replaces_existing(self, strategy, sample_directive_markdown):
        """Should replace existing signature when inserting."""
        old_sig = "<!-- lilux:validated:2024-01-01T11:00:00Z:oldhash -->\n"
        new_sig = "<!-- lilux:validated:2024-01-01T12:00:00Z:newhash -->\n"
        content_with_old = old_sig + sample_directive_markdown

        result = strategy.insert_signature(content_with_old, new_sig)

        assert result.startswith(new_sig)
        assert old_sig not in result
        assert sample_directive_markdown.strip() in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_remove_signature_removes_html_comment(self, strategy, sample_directive_markdown):
        """Should remove signature HTML comment."""
        signature = "<!-- lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->\n"
        content_with_sig = signature + sample_directive_markdown

        result = strategy.remove_signature(content_with_sig)

        assert signature not in result
        assert sample_directive_markdown.strip() in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_remove_signature_with_no_signature(self, strategy, sample_directive_markdown):
        """Should return content unchanged when no signature."""
        result = strategy.remove_signature(sample_directive_markdown)

        assert result == sample_directive_markdown


class TestToolMetadataStrategy:
    """Test ToolMetadataStrategy methods."""

    @pytest.fixture
    def strategy(self):
        """Create ToolMetadataStrategy instance."""
        return ToolMetadataStrategy()

    @pytest.fixture
    def sample_tool_with_shebang(self, sample_tool_content):
        """Tool content with shebang."""
        return f"#!/usr/bin/env python3\n{sample_tool_content}"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_removes_signature(self, strategy, sample_tool_content):
        """Should extract content without signature for hashing."""
        signature = "# lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        content_with_sig = signature + sample_tool_content

        result = strategy.extract_content_for_hash(content_with_sig)

        assert signature not in result
        assert sample_tool_content.strip() in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_removes_shebang(self, strategy, sample_tool_with_shebang):
        """Should remove shebang for consistent hashing."""
        result = strategy.extract_content_for_hash(sample_tool_with_shebang)

        assert not result.startswith("#!/")
        assert "python3" not in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_format_signature_creates_python_comment(self, strategy):
        """Should format signature as Python comment."""
        timestamp = "2024-01-01T12:00:00Z"
        hash_value = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        signature = strategy.format_signature(timestamp, hash_value)

        assert signature.startswith("# lilux:validated:")
        assert signature.endswith("\n")
        assert timestamp in signature
        assert hash_value in signature

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_after_shebang(self, strategy, sample_tool_with_shebang):
        """Should extract signature after shebang."""
        signature = "# lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        content = f"#!/usr/bin/env python3\n{signature}{sample_tool_with_shebang.split(chr(10), 1)[1]}"

        result = strategy.extract_signature(content)

        assert result is not None
        assert result["timestamp"] == "2024-01-01T12:00:00Z"
        assert result["hash"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_without_shebang(self, strategy, sample_tool_content):
        """Should extract signature when no shebang."""
        signature = "# lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        content = signature + sample_tool_content

        result = strategy.extract_signature(content)

        assert result is not None
        assert result["timestamp"] == "2024-01-01T12:00:00Z"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_after_shebang(self, strategy, sample_tool_with_shebang):
        """Should insert signature after shebang if present."""
        signature = "# lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"

        result = strategy.insert_signature(sample_tool_with_shebang, signature)

        lines = result.split("\n")
        assert lines[0].startswith("#!/")
        assert lines[1] == signature.strip()

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_at_start_without_shebang(self, strategy, sample_tool_content):
        """Should insert signature at start when no shebang."""
        signature = "# lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"

        result = strategy.insert_signature(sample_tool_content, signature)

        assert result.startswith(signature)

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_remove_signature_preserves_shebang(self, strategy, sample_tool_with_shebang):
        """Should preserve shebang when removing signature."""
        signature = "# lilux:validated:2024-01-01T12:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        content = f"#!/usr/bin/env python3\n{signature}{sample_tool_with_shebang.split(chr(10), 1)[1]}"

        result = strategy.remove_signature(content)

        assert result.startswith("#!/")
        assert signature not in result


class TestKnowledgeMetadataStrategy:
    """Test KnowledgeMetadataStrategy methods."""

    @pytest.fixture
    def strategy(self):
        """Create KnowledgeMetadataStrategy instance."""
        return KnowledgeMetadataStrategy()

    @pytest.fixture
    def sample_knowledge_with_frontmatter(self, sample_knowledge_content):
        """Knowledge entry with YAML frontmatter."""
        return f"""---
id: 001-test
title: Test Entry
entry_type: learning
category: test
tags: []
---

{sample_knowledge_content}
"""

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_extracts_content_only(self, strategy, sample_knowledge_with_frontmatter, sample_knowledge_content):
        """Should extract only content portion (after frontmatter) for hashing."""
        result = strategy.extract_content_for_hash(sample_knowledge_with_frontmatter)

        assert result.strip() == sample_knowledge_content.strip()
        assert "id" not in result
        assert "---" not in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_without_frontmatter(self, strategy, sample_knowledge_content):
        """Should return entire content when no frontmatter."""
        result = strategy.extract_content_for_hash(sample_knowledge_content)

        assert result == sample_knowledge_content

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_format_signature_creates_html_comment(self, strategy):
        """Should format signature as HTML comment at top."""
        timestamp = "2024-01-01T12:00:00Z"
        hash_value = "a" * 64

        signature = strategy.format_signature(timestamp, hash_value)

        assert "<!-- lilux:validated:" in signature
        assert timestamp in signature
        assert hash_value in signature
        assert "-->" in signature

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_from_html_comment(self, strategy):
        """Should extract signature from HTML comment at start."""
        content = """<!-- lilux:validated:2024-01-01T12:00:00Z:""" + "a" * 64 + """ -->
---
id: 001-test
title: Test
---

Content here
"""
        result = strategy.extract_signature(content)

        assert result is not None
        assert result["timestamp"] == "2024-01-01T12:00:00Z"
        assert result["hash"] == "a" * 64

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_missing_comment(self, strategy):
        """Should return None when signature comment missing."""
        content = """---
id: 001-test
title: Test
---

Content here
"""
        result = strategy.extract_signature(content)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_at_top(self, strategy, sample_knowledge_with_frontmatter):
        """Should insert signature at beginning of content."""
        signature = "<!-- lilux:validated:2024-01-01T12:00:00Z:" + "a" * 64 + " -->\n"

        result = strategy.insert_signature(sample_knowledge_with_frontmatter, signature)

        assert result.startswith("<!-- lilux:validated:")
        assert "id: 001-test" in result  # Preserves other fields

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_remove_signature_removes_comment(self, strategy):
        """Should remove signature HTML comment from start."""
        content = """<!-- lilux:validated:2024-01-01T12:00:00Z:""" + "a" * 64 + """ -->
---
id: 001-test
title: Test
---

Content here
"""
        result = strategy.remove_signature(content)

        assert not result.startswith("<!-- lilux:validated:")
        assert "id: 001-test" in result  # Preserves other fields
        assert "Content here" in result


class TestMetadataManager:
    """Test MetadataManager class methods."""

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_get_strategy_for_directive(self):
        """Should return DirectiveMetadataStrategy for directive type."""
        strategy = MetadataManager.get_strategy("directive")

        assert isinstance(strategy, DirectiveMetadataStrategy)

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_get_strategy_for_tool(self):
        """Should return ToolMetadataStrategy for tool type."""
        strategy = MetadataManager.get_strategy("tool")

        assert isinstance(strategy, ToolMetadataStrategy)

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_get_strategy_for_knowledge(self):
        """Should return KnowledgeMetadataStrategy for knowledge type."""
        strategy = MetadataManager.get_strategy("knowledge")

        assert isinstance(strategy, KnowledgeMetadataStrategy)

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_get_strategy_invalid_type(self):
        """Should raise ValueError for unknown item type."""
        with pytest.raises(ValueError, match="Unknown item_type"):
            MetadataManager.get_strategy("invalid")

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_parse_file_directive(self, sample_directive_file):
        """Should parse directive file using appropriate parser."""
        root = Path(__file__).resolve().parent.parent.parent
        if not (root / "rye" / ".ai" / "extractors" / "directive").exists() and not (root / ".ai" / "extractors" / "directive").exists():
            pytest.skip("No directive extractors (need rye/.ai or .ai/extractors)")
        result = MetadataManager.parse_file("directive", sample_directive_file)

        assert isinstance(result, dict)
        assert result["name"] == "test_directive"
        assert "version" in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_parse_file_tool(self, sample_tool_file):
        """Should parse tool file using appropriate parser."""
        result = MetadataManager.parse_file("tool", sample_tool_file)

        assert isinstance(result, dict)
        # File is test_tool.py, so name should be test_tool (migrated from scripts to tools)
        assert result["name"] == "test_tool"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_parse_file_knowledge(self, sample_knowledge_file):
        """Should parse knowledge file using appropriate parser."""
        root = Path(__file__).resolve().parent.parent.parent
        if not (root / "rye" / ".ai" / "extractors" / "knowledge").exists() and not (root / ".ai" / "extractors" / "knowledge").exists():
            pytest.skip("No knowledge extractors (need rye/.ai or .ai/extractors)")
        result = MetadataManager.parse_file("knowledge", sample_knowledge_file)

        assert isinstance(result, dict)
        assert result["id"] == "001-test"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_directive(self, sample_directive_file):
        """Should compute hash for directive content."""
        file_content = sample_directive_file.read_text()
        hash_result = MetadataManager.compute_hash("directive", file_content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_tool(self, sample_tool_file):
        """Should compute hash for tool content."""
        file_content = sample_tool_file.read_text()
        hash_result = MetadataManager.compute_hash("tool", file_content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_knowledge(self, sample_knowledge_file):
        """Should compute hash for knowledge content."""
        file_content = sample_knowledge_file.read_text()
        hash_result = MetadataManager.compute_hash("knowledge", file_content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_create_signature_directive(self, sample_directive_file):
        """Should create signature for directive."""
        file_content = sample_directive_file.read_text()
        signature = MetadataManager.create_signature("directive", file_content)

        assert signature.startswith("<!--")
        assert "lilux:validated" in signature
        # Signature format: <!-- lilux:validated:TIMESTAMP:HASH -->
        # Extract the inner part (between <!-- and -->)
        inner = signature.replace("<!-- ", "").replace(" -->\n", "").strip()
        # Should have lilux:validated: prefix
        assert inner.startswith("lilux:validated:")
        # Should end with 64-char hash
        assert len(inner.split(":")[-1]) == 64

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_create_signature_tool(self, sample_tool_file):
        """Should create signature for tool."""
        file_content = sample_tool_file.read_text()
        signature = MetadataManager.create_signature("tool", file_content)

        assert signature.startswith("# lilux:validated")
        # Signature format: # lilux:validated:TIMESTAMP:HASH
        parts = signature.replace("# ", "").replace("\n", "").split(":")
        assert len(parts) >= 3  # lilux, validated, TIMESTAMP (which has colons), HASH
        assert parts[0] == "lilux"
        assert parts[1] == "validated"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_sign_content_directive(self, sample_directive_file):
        """Should add signature to directive content."""
        file_content = sample_directive_file.read_text()
        signed = MetadataManager.sign_content("directive", file_content)

        assert signed.startswith("<!--")
        assert "lilux:validated" in signed
        assert file_content.strip() in signed

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_sign_content_tool(self, sample_tool_file):
        """Should add signature to tool content."""
        file_content = sample_tool_file.read_text()
        signed = MetadataManager.sign_content("tool", file_content)

        assert "# lilux:validated" in signed
        assert file_content.strip() in signed

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_get_signature_info_extracts_data(self, sample_directive_file):
        """Should extract signature information."""
        file_content = sample_directive_file.read_text()
        signed_content = MetadataManager.sign_content("directive", file_content)

        result = MetadataManager.get_signature_info("directive", signed_content)

        assert result is not None
        assert "timestamp" in result
        assert "hash" in result


class TestMetadataManagerEdgeCases:
    """Test edge cases and error handling in MetadataManager."""

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_sign_content_replaces_existing_signature(self, sample_directive_file):
        """Should replace existing signature when signing."""
        file_content = sample_directive_file.read_text()
        # Add signature twice
        signed1 = MetadataManager.sign_content("directive", file_content)
        signed2 = MetadataManager.sign_content("directive", signed1)

        # Should only have one signature
        sig_count = signed2.count("lilux:validated")
        assert sig_count == 1

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_empty_content_tool(self):
        """Should handle empty tool content."""
        hash_result = MetadataManager.compute_hash("tool", "")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_empty_content_knowledge(self):
        """Should handle empty knowledge content."""
        hash_result = MetadataManager.compute_hash("knowledge", "")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_empty_directive_raises_error(self):
        """Should raise error for empty directive content (no XML)."""
        with pytest.raises(ValueError, match="No XML directive found"):
            MetadataManager.compute_hash("directive", "")


