"""
Tests for IntegrityVerifier - centralized integrity verification.
"""

import pytest
from kiwi_mcp.primitives.integrity_verifier import IntegrityVerifier
from kiwi_mcp.utils.metadata_manager import MetadataManager, compute_unified_integrity


class TestIntegrityVerifier:
    """Test IntegrityVerifier functionality."""

    @pytest.fixture
    def project_path(self, tmp_path):
        """Create a test project with a tool."""
        project = tmp_path / "test_project"
        project.mkdir()
        
        tools_dir = project / ".ai" / "tools" / "utility"
        tools_dir.mkdir(parents=True)
        
        # Create a tool file
        tool_file = tools_dir / "test_tool.py"
        tool_content = """__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"

def main():
    return "test"
"""
        tool_file.write_text(tool_content)
        
        # Sign the tool
        content_hash = compute_unified_integrity(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_content=tool_content,
            file_path=tool_file
        )
        signed_content = MetadataManager.sign_content_with_hash(
            "tool", tool_content, content_hash, file_path=tool_file, project_path=project
        )
        tool_file.write_text(signed_content)
        
        return project

    @pytest.fixture
    def verifier(self):
        """IntegrityVerifier instance."""
        return IntegrityVerifier()

    def test_verify_single_file_success(self, verifier, project_path):
        """Test successful verification of a single file."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        file_content = tool_file.read_text()
        
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=tool_file, project_path=project_path)
        
        result = verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=stored_hash,
            project_path=project_path
        )
        
        assert result.success is True
        assert result.verified_count == 1
        assert result.error is None

    def test_verify_single_file_modified(self, verifier, project_path):
        """Test verification fails when content is modified."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        file_content = tool_file.read_text()
        
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=tool_file, project_path=project_path)
        
        # Modify the file
        tool_file.write_text(file_content + "\n# Modified")
        
        result = verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=stored_hash,
            project_path=project_path
        )
        
        assert result.success is False
        assert "mismatch" in result.error.lower() or "modified" in result.error.lower()

    def test_verify_single_file_wrong_hash(self, verifier, project_path):
        """Test verification fails with wrong stored hash."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        wrong_hash = "0" * 64
        
        result = verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=wrong_hash,
            project_path=project_path
        )
        
        assert result.success is False
        assert "mismatch" in result.error.lower()

    def test_verify_single_file_caching(self, verifier, project_path):
        """Test that verified files are cached."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        file_content = tool_file.read_text()
        
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=tool_file, project_path=project_path)
        
        # First verification
        result1 = verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=stored_hash,
            project_path=project_path
        )
        assert result1.success is True
        assert result1.cached_count == 0  # First time, not cached
        
        # Second verification should use cache
        result2 = verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=stored_hash,
            project_path=project_path
        )
        assert result2.success is True
        assert result2.cached_count == 1  # Cached

    def test_verify_single_file_failed_cache(self, verifier, project_path):
        """Test that failed verifications are cached."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        wrong_hash = "0" * 64
        
        # First failure
        result1 = verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=wrong_hash,
            project_path=project_path
        )
        assert result1.success is False
        
        # Second failure should use failed cache
        result2 = verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=wrong_hash,
            project_path=project_path
        )
        assert result2.success is False
        assert "Previously failed" in result2.error

    def test_verify_chain_success(self, verifier):
        """Test successful verification of a chain."""
        # Create a chain with valid hashes
        chain = [
            {
                "tool_id": "test_tool",
                "version": "1.0.0",
                "manifest": {},
                "content_hash": "a" * 64,
                "files": [{"path": "test.py", "sha256": "b" * 64}]
            },
            {
                "tool_id": "python_runtime",
                "version": "1.0.0",
                "manifest": {},
                "content_hash": "c" * 64,
                "files": [{"path": "runtime.py", "sha256": "d" * 64}]
            }
        ]
        
        # Mock the integrity computation to match
        from unittest.mock import patch
        with patch('kiwi_mcp.primitives.integrity_verifier.compute_tool_integrity') as mock_compute:
            mock_compute.side_effect = lambda tool_id, version, manifest, files: {
                "test_tool": "a" * 64,
                "python_runtime": "c" * 64
            }[tool_id]
            
            result = verifier.verify_chain(chain)
            
            assert result.success is True
            assert result.verified_count == 2

    def test_verify_chain_missing_hash(self, verifier):
        """Test verification fails when chain link has no hash."""
        chain = [
            {
                "tool_id": "test_tool",
                "version": "1.0.0",
                "manifest": {},
                # Missing content_hash
            }
        ]
        
        result = verifier.verify_chain(chain)
        
        assert result.success is False
        assert "No integrity hash found" in result.error
        assert result.failed_at == 0
        assert result.failed_tool_id == "test_tool"

    def test_verify_chain_mismatch(self, verifier):
        """Test verification fails when computed hash doesn't match stored."""
        chain = [
            {
                "tool_id": "test_tool",
                "version": "1.0.0",
                "manifest": {},
                "content_hash": "a" * 64,  # Stored hash
                "files": [{"path": "test.py", "sha256": "b" * 64}]
            }
        ]
        
        # Mock integrity computation to return different hash
        from unittest.mock import patch
        with patch('kiwi_mcp.primitives.integrity_verifier.compute_tool_integrity') as mock_compute:
            mock_compute.return_value = "b" * 64  # Different from stored
            
            result = verifier.verify_chain(chain)
            
            assert result.success is False
            assert "mismatch" in result.error.lower()
            assert result.failed_at == 0
            assert result.failed_tool_id == "test_tool"

    def test_is_verified(self, verifier, project_path):
        """Test is_verified cache check."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        file_content = tool_file.read_text()
        
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=tool_file, project_path=project_path)
        
        # Not verified yet
        assert verifier.is_verified(stored_hash) is False
        
        # Verify it
        verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=stored_hash,
            project_path=project_path
        )
        
        # Now should be verified
        assert verifier.is_verified(stored_hash) is True

    def test_invalidate(self, verifier, project_path):
        """Test invalidating a cached verification."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        file_content = tool_file.read_text()
        
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=tool_file, project_path=project_path)
        
        # Verify and cache
        verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=stored_hash,
            project_path=project_path
        )
        
        assert verifier.is_verified(stored_hash) is True
        
        # Invalidate
        verifier.invalidate(stored_hash)
        
        assert verifier.is_verified(stored_hash) is False

    def test_clear_cache(self, verifier, project_path):
        """Test clearing all caches."""
        tool_file = project_path / ".ai" / "tools" / "utility" / "test_tool.py"
        file_content = tool_file.read_text()
        
        stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=tool_file, project_path=project_path)
        
        # Verify and cache
        verifier.verify_single_file(
            item_type="tool",
            item_id="test_tool",
            version="1.0.0",
            file_path=tool_file,
            stored_hash=stored_hash,
            project_path=project_path
        )
        
        assert verifier.is_verified(stored_hash) is True
        
        # Clear cache
        verifier.clear_cache()
        
        assert verifier.is_verified(stored_hash) is False
        stats = verifier.get_cache_stats()
        assert stats["verified_count"] == 0
        assert stats["failed_count"] == 0

    def test_get_cache_stats(self, verifier):
        """Test getting cache statistics."""
        stats = verifier.get_cache_stats()
        
        assert "verified_count" in stats
        assert "failed_count" in stats
        assert stats["verified_count"] == 0
        assert stats["failed_count"] == 0
