"""
Tests for directive and knowledge integrity functions.

These tests verify the canonical content-addressed hashing for
directives and knowledge entries.
"""

import pytest
from kiwi_mcp.primitives.integrity import (
    compute_directive_integrity,
    verify_directive_integrity,
    compute_knowledge_integrity,
    verify_knowledge_integrity,
    short_hash,
)


class TestDirectiveIntegrity:
    """Tests for directive integrity computation."""

    def test_compute_directive_integrity_basic(self):
        """Test basic directive integrity computation."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        metadata = {"category": "test", "description": "A test directive"}
        
        result = compute_directive_integrity("test", "1.0.0", xml, metadata)
        
        assert result is not None
        assert len(result) == 64  # SHA256 hex digest
        assert result.isalnum()

    def test_compute_directive_integrity_deterministic(self):
        """Test that same inputs produce same hash."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        metadata = {"category": "test", "description": "A test directive"}
        
        hash1 = compute_directive_integrity("test", "1.0.0", xml, metadata)
        hash2 = compute_directive_integrity("test", "1.0.0", xml, metadata)
        
        assert hash1 == hash2

    def test_compute_directive_integrity_changes_with_name(self):
        """Test that different name produces different hash."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        metadata = {"category": "test"}
        
        hash1 = compute_directive_integrity("test", "1.0.0", xml, metadata)
        hash2 = compute_directive_integrity("test2", "1.0.0", xml, metadata)
        
        assert hash1 != hash2

    def test_compute_directive_integrity_changes_with_version(self):
        """Test that different version produces different hash."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        metadata = {"category": "test"}
        
        hash1 = compute_directive_integrity("test", "1.0.0", xml, metadata)
        hash2 = compute_directive_integrity("test", "2.0.0", xml, metadata)
        
        assert hash1 != hash2

    def test_compute_directive_integrity_changes_with_xml(self):
        """Test that different XML produces different hash."""
        xml1 = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        xml2 = '<directive name="test" version="1.0.0"><process><step>Do other thing</step></process></directive>'
        metadata = {"category": "test"}
        
        hash1 = compute_directive_integrity("test", "1.0.0", xml1, metadata)
        hash2 = compute_directive_integrity("test", "1.0.0", xml2, metadata)
        
        assert hash1 != hash2

    def test_compute_directive_integrity_changes_with_metadata(self):
        """Test that different metadata produces different hash."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        metadata1 = {"category": "test"}
        metadata2 = {"category": "production"}
        
        hash1 = compute_directive_integrity("test", "1.0.0", xml, metadata1)
        hash2 = compute_directive_integrity("test", "1.0.0", xml, metadata2)
        
        assert hash1 != hash2

    def test_compute_directive_integrity_none_metadata(self):
        """Test with None metadata."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        
        hash1 = compute_directive_integrity("test", "1.0.0", xml, None)
        hash2 = compute_directive_integrity("test", "1.0.0", xml, {})
        
        # Both None and {} should produce same result
        assert hash1 == hash2

    def test_verify_directive_integrity_success(self):
        """Test successful verification."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        metadata = {"category": "test"}
        
        computed_hash = compute_directive_integrity("test", "1.0.0", xml, metadata)
        
        assert verify_directive_integrity("test", "1.0.0", xml, computed_hash, metadata)

    def test_verify_directive_integrity_failure(self):
        """Test failed verification."""
        xml = '<directive name="test" version="1.0.0"><process><step>Do thing</step></process></directive>'
        modified_xml = '<directive name="test" version="1.0.0"><process><step>Modified</step></process></directive>'
        metadata = {"category": "test"}
        
        original_hash = compute_directive_integrity("test", "1.0.0", xml, metadata)
        
        assert not verify_directive_integrity("test", "1.0.0", modified_xml, original_hash, metadata)


class TestKnowledgeIntegrity:
    """Tests for knowledge entry integrity computation."""

    def test_compute_knowledge_integrity_basic(self):
        """Test basic knowledge integrity computation."""
        content = "This is some knowledge content about APIs."
        frontmatter = {
            "zettel_id": "20260124-api",
            "title": "API Patterns",
            "entry_type": "pattern",
            "category": "architecture",
            "tags": ["api", "rest"],
        }
        
        result = compute_knowledge_integrity("20260124-api", "1.0.0", content, frontmatter)
        
        assert result is not None
        assert len(result) == 64
        assert result.isalnum()

    def test_compute_knowledge_integrity_deterministic(self):
        """Test that same inputs produce same hash."""
        content = "Knowledge content"
        frontmatter = {"zettel_id": "test", "title": "Test"}
        
        hash1 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter)
        hash2 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter)
        
        assert hash1 == hash2

    def test_compute_knowledge_integrity_changes_with_id(self):
        """Test that different zettel_id produces different hash."""
        content = "Knowledge content"
        frontmatter = {"title": "Test"}
        
        hash1 = compute_knowledge_integrity("id1", "1.0.0", content, frontmatter)
        hash2 = compute_knowledge_integrity("id2", "1.0.0", content, frontmatter)
        
        assert hash1 != hash2

    def test_compute_knowledge_integrity_changes_with_version(self):
        """Test that different version produces different hash."""
        content = "Knowledge content"
        frontmatter = {"title": "Test"}
        
        hash1 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter)
        hash2 = compute_knowledge_integrity("test", "2.0.0", content, frontmatter)
        
        assert hash1 != hash2

    def test_compute_knowledge_integrity_changes_with_content(self):
        """Test that different content produces different hash."""
        content1 = "Knowledge content v1"
        content2 = "Knowledge content v2"
        frontmatter = {"title": "Test"}
        
        hash1 = compute_knowledge_integrity("test", "1.0.0", content1, frontmatter)
        hash2 = compute_knowledge_integrity("test", "1.0.0", content2, frontmatter)
        
        assert hash1 != hash2

    def test_compute_knowledge_integrity_changes_with_frontmatter(self):
        """Test that different frontmatter produces different hash."""
        content = "Knowledge content"
        frontmatter1 = {"title": "Test 1"}
        frontmatter2 = {"title": "Test 2"}
        
        hash1 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter1)
        hash2 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter2)
        
        assert hash1 != hash2

    def test_compute_knowledge_integrity_excludes_validation_fields(self):
        """Test that validation fields in frontmatter are excluded."""
        content = "Knowledge content"
        frontmatter1 = {"title": "Test", "validated_at": "2026-01-24", "content_hash": "abc123"}
        frontmatter2 = {"title": "Test", "validated_at": "2026-01-25", "content_hash": "def456"}
        frontmatter3 = {"title": "Test"}
        
        hash1 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter1)
        hash2 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter2)
        hash3 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter3)
        
        # All should be equal because validation fields are excluded
        assert hash1 == hash2 == hash3

    def test_compute_knowledge_integrity_excludes_integrity_field(self):
        """Test that integrity field itself is excluded from computation."""
        content = "Knowledge content"
        frontmatter1 = {"title": "Test", "integrity": "old_hash"}
        frontmatter2 = {"title": "Test"}
        
        hash1 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter1)
        hash2 = compute_knowledge_integrity("test", "1.0.0", content, frontmatter2)
        
        assert hash1 == hash2

    def test_compute_knowledge_integrity_none_frontmatter(self):
        """Test with None frontmatter."""
        content = "Knowledge content"
        
        hash1 = compute_knowledge_integrity("test", "1.0.0", content, None)
        hash2 = compute_knowledge_integrity("test", "1.0.0", content, {})
        
        assert hash1 == hash2

    def test_verify_knowledge_integrity_success(self):
        """Test successful verification."""
        content = "Knowledge content"
        frontmatter = {"title": "Test", "tags": ["a", "b"]}
        
        computed_hash = compute_knowledge_integrity("test", "1.0.0", content, frontmatter)
        
        assert verify_knowledge_integrity("test", "1.0.0", content, computed_hash, frontmatter)

    def test_verify_knowledge_integrity_failure(self):
        """Test failed verification."""
        content = "Original content"
        modified_content = "Modified content"
        frontmatter = {"title": "Test"}
        
        original_hash = compute_knowledge_integrity("test", "1.0.0", content, frontmatter)
        
        assert not verify_knowledge_integrity("test", "1.0.0", modified_content, original_hash, frontmatter)


class TestShortHash:
    """Tests for short hash utility."""

    def test_short_hash_default_length(self):
        """Test default 12-character short hash."""
        full_hash = "a" * 64
        result = short_hash(full_hash)
        
        assert len(result) == 12
        assert result == "a" * 12

    def test_short_hash_custom_length(self):
        """Test custom length short hash."""
        full_hash = "a" * 64
        
        assert len(short_hash(full_hash, 8)) == 8
        assert len(short_hash(full_hash, 16)) == 16
        assert len(short_hash(full_hash, 32)) == 32

    def test_short_hash_with_real_hash(self):
        """Test with actual computed hash."""
        xml = '<directive name="test" version="1.0.0"></directive>'
        full_hash = compute_directive_integrity("test", "1.0.0", xml, None)
        
        short = short_hash(full_hash)
        assert len(short) == 12
        assert full_hash.startswith(short)
