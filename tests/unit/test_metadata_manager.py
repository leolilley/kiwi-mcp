"""
Comprehensive tests for MetadataManager and all metadata strategies.

Tests hash computation, signature management, and content extraction
for directives, scripts, and knowledge entries.
"""

import pytest
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from kiwi_mcp.utils.metadata_manager import (
    compute_content_hash,
    generate_timestamp,
    MetadataStrategy,
    DirectiveMetadataStrategy,
    ScriptMetadataStrategy,
    KnowledgeMetadataStrategy,
    MetadataManager,
)


class TestHashUtilities:
    """Test hash and timestamp utility functions."""

    @pytest.mark.unit
    @pytest.mark.utils
    def test_compute_content_hash_returns_12_chars(self):
        """Should return first 12 hex characters of SHA256 hash."""
        content = "test content"
        hash_result = compute_content_hash(content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 12
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
    def test_compute_content_hash_matches_sha256_first_12(self):
        """Should match first 12 chars of SHA256 hex digest."""
        content = "test content"
        expected = hashlib.sha256(content.encode()).hexdigest()[:12]
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
        hash_value = "abc123def456"

        signature = strategy.format_signature(timestamp, hash_value)

        assert signature.startswith("<!--")
        assert signature.endswith("-->\n")
        assert timestamp in signature
        assert hash_value in signature
        assert "kiwi-mcp:validated" in signature

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_with_valid_signature(self, strategy):
        """Should extract signature from HTML comment."""
        timestamp = "2024-01-01T12:00:00Z"
        hash_value = "abc123def456"
        content = f"<!-- kiwi-mcp:validated:{timestamp}:{hash_value} -->\n# Content"

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
        content = "<!-- kiwi-mcp:invalid -->\n# Content"

        result = strategy.extract_signature(content)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_at_start(self, strategy, sample_directive_markdown):
        """Should insert signature at beginning of content."""
        signature = "<!-- kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456 -->\n"

        result = strategy.insert_signature(sample_directive_markdown, signature)

        assert result.startswith(signature)
        assert sample_directive_markdown.strip() in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_replaces_existing(self, strategy, sample_directive_markdown):
        """Should replace existing signature when inserting."""
        old_sig = "<!-- kiwi-mcp:validated:2024-01-01T11:00:00Z:oldhash -->\n"
        new_sig = "<!-- kiwi-mcp:validated:2024-01-01T12:00:00Z:newhash -->\n"
        content_with_old = old_sig + sample_directive_markdown

        result = strategy.insert_signature(content_with_old, new_sig)

        assert result.startswith(new_sig)
        assert old_sig not in result
        assert sample_directive_markdown.strip() in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_remove_signature_removes_html_comment(self, strategy, sample_directive_markdown):
        """Should remove signature HTML comment."""
        signature = "<!-- kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456 -->\n"
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


class TestScriptMetadataStrategy:
    """Test ScriptMetadataStrategy methods."""

    @pytest.fixture
    def strategy(self):
        """Create ScriptMetadataStrategy instance."""
        return ScriptMetadataStrategy()

    @pytest.fixture
    def sample_script_with_shebang(self, sample_script_content):
        """Script content with shebang."""
        return f"#!/usr/bin/env python3\n{sample_script_content}"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_removes_signature(self, strategy, sample_script_content):
        """Should extract content without signature for hashing."""
        signature = "# kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456\n"
        content_with_sig = signature + sample_script_content

        result = strategy.extract_content_for_hash(content_with_sig)

        assert signature not in result
        assert sample_script_content.strip() in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_removes_shebang(self, strategy, sample_script_with_shebang):
        """Should remove shebang for consistent hashing."""
        result = strategy.extract_content_for_hash(sample_script_with_shebang)

        assert not result.startswith("#!/")
        assert "python3" not in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_format_signature_creates_python_comment(self, strategy):
        """Should format signature as Python comment."""
        timestamp = "2024-01-01T12:00:00Z"
        hash_value = "abc123def456"

        signature = strategy.format_signature(timestamp, hash_value)

        assert signature.startswith("# kiwi-mcp:validated:")
        assert signature.endswith("\n")
        assert timestamp in signature
        assert hash_value in signature

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_after_shebang(self, strategy, sample_script_with_shebang):
        """Should extract signature after shebang."""
        signature = "# kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456\n"
        content = f"#!/usr/bin/env python3\n{signature}{sample_script_with_shebang.split(chr(10), 1)[1]}"

        result = strategy.extract_signature(content)

        assert result is not None
        assert result["timestamp"] == "2024-01-01T12:00:00Z"
        assert result["hash"] == "abc123def456"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_without_shebang(self, strategy, sample_script_content):
        """Should extract signature when no shebang."""
        signature = "# kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456\n"
        content = signature + sample_script_content

        result = strategy.extract_signature(content)

        assert result is not None
        assert result["timestamp"] == "2024-01-01T12:00:00Z"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_after_shebang(self, strategy, sample_script_with_shebang):
        """Should insert signature after shebang if present."""
        signature = "# kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456\n"

        result = strategy.insert_signature(sample_script_with_shebang, signature)

        lines = result.split("\n")
        assert lines[0].startswith("#!/")
        assert lines[1] == signature.strip()

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_at_start_without_shebang(self, strategy, sample_script_content):
        """Should insert signature at start when no shebang."""
        signature = "# kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456\n"

        result = strategy.insert_signature(sample_script_content, signature)

        assert result.startswith(signature)

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_remove_signature_preserves_shebang(self, strategy, sample_script_with_shebang):
        """Should preserve shebang when removing signature."""
        signature = "# kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456\n"
        content = f"#!/usr/bin/env python3\n{signature}{sample_script_with_shebang.split(chr(10), 1)[1]}"

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
zettel_id: 001-test
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
        assert "zettel_id" not in result
        assert "---" not in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_content_for_hash_without_frontmatter(self, strategy, sample_knowledge_content):
        """Should return entire content when no frontmatter."""
        result = strategy.extract_content_for_hash(sample_knowledge_content)

        assert result == sample_knowledge_content

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_format_signature_creates_yaml_fields(self, strategy):
        """Should format signature as YAML frontmatter fields."""
        timestamp = "2024-01-01T12:00:00Z"
        hash_value = "abc123def456"

        signature = strategy.format_signature(timestamp, hash_value)

        assert "validated_at:" in signature
        assert "content_hash:" in signature
        assert timestamp in signature
        assert hash_value in signature

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_from_frontmatter(self, strategy):
        """Should extract signature from YAML frontmatter."""
        content = """---
zettel_id: 001-test
title: Test
validated_at: 2024-01-01T12:00:00Z
content_hash: abc123def456
---

Content here
"""
        result = strategy.extract_signature(content)

        assert result is not None
        assert result["timestamp"] == "2024-01-01T12:00:00Z"
        assert result["hash"] == "abc123def456"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_extract_signature_missing_fields(self, strategy):
        """Should return None when signature fields missing."""
        content = """---
zettel_id: 001-test
title: Test
---

Content here
"""
        result = strategy.extract_signature(content)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_insert_signature_updates_frontmatter(self, strategy, sample_knowledge_with_frontmatter):
        """Should update frontmatter with signature fields."""
        signature = "validated_at: 2024-01-01T12:00:00Z\ncontent_hash: abc123def456"

        result = strategy.insert_signature(sample_knowledge_with_frontmatter, signature)

        assert "validated_at: 2024-01-01T12:00:00Z" in result
        assert "content_hash: abc123def456" in result
        assert "zettel_id: 001-test" in result  # Preserves other fields

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_remove_signature_removes_fields(self, strategy):
        """Should remove signature fields from frontmatter."""
        content = """---
zettel_id: 001-test
title: Test
validated_at: 2024-01-01T12:00:00Z
content_hash: abc123def456
---

Content here
"""
        result = strategy.remove_signature(content)

        assert "validated_at:" not in result
        assert "content_hash:" not in result
        assert "zettel_id: 001-test" in result  # Preserves other fields
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
    def test_get_strategy_for_script(self):
        """Should return ScriptMetadataStrategy for script type."""
        strategy = MetadataManager.get_strategy("script")

        assert isinstance(strategy, ScriptMetadataStrategy)

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
        result = MetadataManager.parse_file("directive", sample_directive_file)

        assert isinstance(result, dict)
        assert result["name"] == "test_directive"
        assert "parsed" in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_parse_file_script(self, sample_script_file):
        """Should parse script file using appropriate parser."""
        result = MetadataManager.parse_file("script", sample_script_file)

        assert isinstance(result, dict)
        assert result["name"] == "test_script"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_parse_file_knowledge(self, sample_knowledge_file):
        """Should parse knowledge file using appropriate parser."""
        result = MetadataManager.parse_file("knowledge", sample_knowledge_file)

        assert isinstance(result, dict)
        assert result["zettel_id"] == "001-test"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_directive(self, sample_directive_file):
        """Should compute hash for directive content."""
        file_content = sample_directive_file.read_text()
        hash_result = MetadataManager.compute_hash("directive", file_content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 12

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_script(self, sample_script_file):
        """Should compute hash for script content."""
        file_content = sample_script_file.read_text()
        hash_result = MetadataManager.compute_hash("script", file_content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 12

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_knowledge(self, sample_knowledge_file):
        """Should compute hash for knowledge content."""
        file_content = sample_knowledge_file.read_text()
        hash_result = MetadataManager.compute_hash("knowledge", file_content)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 12

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_create_signature_directive(self, sample_directive_file):
        """Should create signature for directive."""
        file_content = sample_directive_file.read_text()
        signature = MetadataManager.create_signature("directive", file_content)

        assert signature.startswith("<!--")
        assert "kiwi-mcp:validated" in signature
        # Signature format: <!-- kiwi-mcp:validated:TIMESTAMP:HASH -->
        # Extract the inner part (between <!-- and -->)
        inner = signature.replace("<!-- ", "").replace(" -->\n", "").strip()
        # Should have kiwi-mcp:validated: prefix
        assert inner.startswith("kiwi-mcp:validated:")
        # Should end with 12-char hash
        assert len(inner.split(":")[-1]) == 12

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_create_signature_script(self, sample_script_file):
        """Should create signature for script."""
        file_content = sample_script_file.read_text()
        signature = MetadataManager.create_signature("script", file_content)

        assert signature.startswith("# kiwi-mcp:validated")
        # Signature format: # kiwi-mcp:validated:TIMESTAMP:HASH
        parts = signature.replace("# ", "").replace("\n", "").split(":")
        assert len(parts) >= 3  # kiwi-mcp, validated, TIMESTAMP (which has colons), HASH
        assert parts[0] == "kiwi-mcp"
        assert parts[1] == "validated"

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_verify_signature_valid(self, sample_directive_file):
        """Should verify valid signature."""
        file_content = sample_directive_file.read_text()
        # Add signature first
        signed_content = MetadataManager.sign_content("directive", file_content)

        result = MetadataManager.verify_signature("directive", signed_content)

        assert result is not None
        assert result["status"] == "valid"
        assert "hash" in result
        assert "validated_at" in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_verify_signature_modified(self, sample_directive_file):
        """Should detect modified content."""
        file_content = sample_directive_file.read_text()
        signed_content = MetadataManager.sign_content("directive", file_content)

        # Modify content
        modified_content = signed_content.replace("Test directive", "Modified directive")

        result = MetadataManager.verify_signature("directive", modified_content)

        assert result is not None
        assert result["status"] == "modified"
        assert "original_hash" in result
        assert "current_hash" in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_verify_signature_missing(self, sample_directive_file):
        """Should return None when no signature."""
        file_content = sample_directive_file.read_text()

        result = MetadataManager.verify_signature("directive", file_content)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_sign_content_directive(self, sample_directive_file):
        """Should add signature to directive content."""
        file_content = sample_directive_file.read_text()
        signed = MetadataManager.sign_content("directive", file_content)

        assert signed.startswith("<!--")
        assert "kiwi-mcp:validated" in signed
        assert file_content.strip() in signed

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_sign_content_script(self, sample_script_file):
        """Should add signature to script content."""
        file_content = sample_script_file.read_text()
        signed = MetadataManager.sign_content("script", file_content)

        assert "# kiwi-mcp:validated" in signed
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
    def test_verify_signature_invalid_xml_directive(self):
        """Should handle invalid XML gracefully."""
        invalid_content = "<!-- kiwi-mcp:validated:2024-01-01T12:00:00Z:abc123def456 -->\n# No XML"

        result = MetadataManager.verify_signature("directive", invalid_content)

        assert result is not None
        assert result["status"] == "invalid"
        assert "reason" in result

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_sign_content_replaces_existing_signature(self, sample_directive_file):
        """Should replace existing signature when signing."""
        file_content = sample_directive_file.read_text()
        # Add signature twice
        signed1 = MetadataManager.sign_content("directive", file_content)
        signed2 = MetadataManager.sign_content("directive", signed1)

        # Should only have one signature
        sig_count = signed2.count("kiwi-mcp:validated")
        assert sig_count == 1

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_empty_content_script(self):
        """Should handle empty script content."""
        hash_result = MetadataManager.compute_hash("script", "")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 12

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_empty_content_knowledge(self):
        """Should handle empty knowledge content."""
        hash_result = MetadataManager.compute_hash("knowledge", "")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 12

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_compute_hash_empty_directive_raises_error(self):
        """Should raise error for empty directive content (no XML)."""
        with pytest.raises(ValueError, match="No XML directive found"):
            MetadataManager.compute_hash("directive", "")

    @pytest.mark.unit
    @pytest.mark.metadata
    def test_verify_signature_malformed_timestamp(self):
        """Should handle malformed timestamp in signature."""
        content = "<!-- kiwi-mcp:validated:invalid-timestamp:abc123def456 -->\n# Content"

        result = MetadataManager.verify_signature("directive", content)

        # Should still extract and verify hash
        assert result is not None
