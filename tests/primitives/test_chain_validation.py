"""
Tests for the package-manager-style tool chain validation system.

Tests:
- Integrity computation (canonical hashing)
- Integrity verification
- Chain validation (parent→child schemas)
- Lockfile management
"""

import pytest
import json
import tempfile
from pathlib import Path

from kiwi_mcp.primitives.integrity import (
    compute_tool_integrity,
    compute_file_hash,
    verify_file_integrity,
    short_hash,
)
from kiwi_mcp.primitives.integrity_verifier import IntegrityVerifier, VerificationResult
from kiwi_mcp.primitives.chain_validator import ChainValidator, ChainValidationResult
from kiwi_mcp.primitives.lockfile import Lockfile, LockfileManager, LockfileError


class TestIntegrity:
    """Tests for integrity computation."""
    
    def test_compute_tool_integrity_deterministic(self):
        """Same inputs should always produce same hash."""
        manifest = {"tool_id": "test", "version": "1.0.0"}
        files = [{"path": "main.py", "sha256": "abc123", "is_executable": True}]
        
        hash1 = compute_tool_integrity("test", "1.0.0", manifest, files)
        hash2 = compute_tool_integrity("test", "1.0.0", manifest, files)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex
    
    def test_compute_tool_integrity_order_independent(self):
        """File order shouldn't affect hash (they're sorted internally)."""
        manifest = {"tool_id": "test", "version": "1.0.0"}
        files1 = [
            {"path": "a.py", "sha256": "aaa", "is_executable": True},
            {"path": "b.py", "sha256": "bbb", "is_executable": False},
        ]
        files2 = [
            {"path": "b.py", "sha256": "bbb", "is_executable": False},
            {"path": "a.py", "sha256": "aaa", "is_executable": True},
        ]
        
        hash1 = compute_tool_integrity("test", "1.0.0", manifest, files1)
        hash2 = compute_tool_integrity("test", "1.0.0", manifest, files2)
        
        assert hash1 == hash2
    
    def test_compute_tool_integrity_manifest_order_independent(self):
        """Manifest key order shouldn't affect hash."""
        manifest1 = {"a": 1, "b": 2, "c": 3}
        manifest2 = {"c": 3, "a": 1, "b": 2}
        
        hash1 = compute_tool_integrity("test", "1.0.0", manifest1, None)
        hash2 = compute_tool_integrity("test", "1.0.0", manifest2, None)
        
        assert hash1 == hash2
    
    def test_compute_tool_integrity_changes_with_version(self):
        """Different versions should produce different hashes."""
        manifest = {"tool_id": "test"}
        
        hash1 = compute_tool_integrity("test", "1.0.0", manifest, None)
        hash2 = compute_tool_integrity("test", "1.0.1", manifest, None)
        
        assert hash1 != hash2
    
    def test_compute_tool_integrity_changes_with_manifest(self):
        """Different manifests should produce different hashes."""
        hash1 = compute_tool_integrity("test", "1.0.0", {"key": "value1"}, None)
        hash2 = compute_tool_integrity("test", "1.0.0", {"key": "value2"}, None)
        
        assert hash1 != hash2
    
    def test_compute_tool_integrity_changes_with_files(self):
        """Different files should produce different hashes."""
        manifest = {"tool_id": "test"}
        files1 = [{"path": "main.py", "sha256": "hash1", "is_executable": True}]
        files2 = [{"path": "main.py", "sha256": "hash2", "is_executable": True}]
        
        hash1 = compute_tool_integrity("test", "1.0.0", manifest, files1)
        hash2 = compute_tool_integrity("test", "1.0.0", manifest, files2)
        
        assert hash1 != hash2
    
    def test_compute_file_hash(self):
        """File hash should be SHA256."""
        content = "print('hello world')"
        hash1 = compute_file_hash(content)
        hash2 = compute_file_hash(content)
        
        assert hash1 == hash2
        assert len(hash1) == 64
    
    def test_verify_file_integrity_success(self):
        """Verification should pass for matching content."""
        content = "test content"
        expected = compute_file_hash(content)
        
        assert verify_file_integrity(content, expected) is True
    
    def test_verify_file_integrity_failure(self):
        """Verification should fail for mismatched content."""
        assert verify_file_integrity("content", "wrong_hash") is False
    
    def test_short_hash(self):
        """Short hash should truncate correctly."""
        full = "abcdef1234567890"
        assert short_hash(full) == "abcdef123456"
        assert short_hash(full, 6) == "abcdef"


class TestIntegrityVerifier:
    """Tests for IntegrityVerifier."""
    
    def test_verify_chain_empty(self):
        """Empty chain should succeed."""
        verifier = IntegrityVerifier()
        result = verifier.verify_chain([])
        
        assert result.success is True
        assert result.verified_count == 0
    
    def test_verify_chain_no_hash(self):
        """Tools without hash should fail verification (strict mode)."""
        verifier = IntegrityVerifier()
        chain = [{"tool_id": "test", "version": "1.0.0", "manifest": {}}]
        
        result = verifier.verify_chain(chain)
        
        assert result.success is False
        assert "no integrity hash" in result.error.lower()
        assert result.failed_tool_id == "test"
        assert result.failed_at == 0
    
    def test_verify_chain_valid_hash(self):
        """Valid hash should pass verification."""
        verifier = IntegrityVerifier()
        
        manifest = {"tool_id": "test"}
        files = []
        expected_hash = compute_tool_integrity("test", "1.0.0", manifest, files)
        
        chain = [{
            "tool_id": "test",
            "version": "1.0.0",
            "manifest": manifest,
            "content_hash": expected_hash,
            "files": files,
        }]
        
        result = verifier.verify_chain(chain)
        
        assert result.success is True
        assert result.verified_count == 1
    
    def test_verify_chain_invalid_hash(self):
        """Invalid hash should fail verification."""
        verifier = IntegrityVerifier()
        
        chain = [{
            "tool_id": "test",
            "version": "1.0.0",
            "manifest": {"tool_id": "test"},
            "content_hash": "invalid_hash",
            "files": [],
        }]
        
        result = verifier.verify_chain(chain)
        
        assert result.success is False
        assert "mismatch" in result.error.lower()
        assert result.failed_tool_id == "test"
    
    def test_verify_chain_caching(self):
        """Verified hashes should be cached."""
        verifier = IntegrityVerifier()
        
        manifest = {"tool_id": "test"}
        expected_hash = compute_tool_integrity("test", "1.0.0", manifest, [])
        
        chain = [{
            "tool_id": "test",
            "version": "1.0.0",
            "manifest": manifest,
            "content_hash": expected_hash,
            "files": [],
        }]
        
        # First verification
        result1 = verifier.verify_chain(chain)
        assert result1.cached_count == 0
        
        # Second verification should use cache
        result2 = verifier.verify_chain(chain)
        assert result2.cached_count == 1
    
    def test_is_verified(self):
        """Check if hash is verified."""
        verifier = IntegrityVerifier()
        
        manifest = {"tool_id": "test"}
        expected_hash = compute_tool_integrity("test", "1.0.0", manifest, [])
        
        assert verifier.is_verified(expected_hash) is False
        
        chain = [{
            "tool_id": "test",
            "version": "1.0.0",
            "manifest": manifest,
            "content_hash": expected_hash,
            "files": [],
        }]
        verifier.verify_chain(chain)
        
        assert verifier.is_verified(expected_hash) is True
    
    def test_clear_cache(self):
        """Cache should be clearable."""
        verifier = IntegrityVerifier()
        
        manifest = {"tool_id": "test"}
        expected_hash = compute_tool_integrity("test", "1.0.0", manifest, [])
        
        chain = [{
            "tool_id": "test",
            "version": "1.0.0",
            "manifest": manifest,
            "content_hash": expected_hash,
            "files": [],
        }]
        verifier.verify_chain(chain)
        
        assert verifier.is_verified(expected_hash) is True
        
        verifier.clear_cache()
        
        assert verifier.is_verified(expected_hash) is False


class TestChainValidator:
    """Tests for ChainValidator."""
    
    def test_validate_chain_empty(self):
        """Empty chain should succeed."""
        validator = ChainValidator()
        result = validator.validate_chain([])
        
        assert result.valid is True
    
    def test_validate_chain_single_tool(self):
        """Single tool chain should succeed (nothing to validate)."""
        validator = ChainValidator()
        result = validator.validate_chain([{"tool_id": "test"}])
        
        assert result.valid is True
    
    def test_validate_chain_primitive_parent(self):
        """Primitive parents don't need to validate children."""
        validator = ChainValidator()
        
        chain = [
            {"tool_id": "my_script", "tool_type": "script"},
            {"tool_id": "subprocess", "tool_type": "primitive"},
        ]
        
        result = validator.validate_chain(chain)
        
        assert result.valid is True
    
    def test_validate_chain_no_schema_fails(self):
        """Missing child_schemas should fail validation."""
        validator = ChainValidator()
        
        chain = [
            {"tool_id": "my_script", "tool_type": "script"},
            {"tool_id": "python_runtime", "tool_type": "runtime", "manifest": {}},
        ]
        
        result = validator.validate_chain(chain)
        
        assert result.valid is False
        assert len(result.issues) > 0
        assert "child_schemas" in result.issues[0].lower()
        assert "python_runtime" in result.issues[0]
    
    def test_validate_chain_with_matching_schema(self):
        """Matching schema should validate successfully."""
        validator = ChainValidator()
        
        child = {
            "tool_id": "my_script",
            "tool_type": "script",
            "manifest": {"entrypoint": "main.py"},
        }
        
        parent = {
            "tool_id": "python_runtime",
            "tool_type": "runtime",
            "manifest": {
                "validation": {
                    "child_schemas": [{
                        "match": {"tool_type": "script"},
                        "schema": {
                            "type": "object",
                            "properties": {
                                "tool_type": {"const": "script"}
                            }
                        }
                    }]
                }
            }
        }
        
        result = validator.validate_chain([child, parent])
        
        assert result.valid is True
    
    def test_validate_chain_no_matching_schema(self):
        """No matching schema should fail."""
        validator = ChainValidator()
        
        child = {"tool_id": "my_api", "tool_type": "api"}
        parent = {
            "tool_id": "python_runtime",
            "tool_type": "runtime",
            "manifest": {
                "validation": {
                    "child_schemas": [{
                        "match": {"tool_type": "script"},
                        "schema": {}
                    }]
                }
            }
        }
        
        result = validator.validate_chain([child, parent])
        
        assert result.valid is False
        assert "No schema matches" in result.issues[0]


class TestLockfileManager:
    """Tests for LockfileManager."""
    
    def test_freeze_creates_lockfile(self):
        """Freeze should create a valid lockfile."""
        manager = LockfileManager(registry_url="https://example.com")
        
        chain = [
            {"tool_id": "my_script", "version": "1.0.0", "content_hash": "abc123", "executor_id": "python_runtime"},
            {"tool_id": "python_runtime", "version": "1.4.0", "content_hash": "def456", "executor_id": "subprocess"},
            {"tool_id": "subprocess", "version": "1.0.0", "content_hash": "ghi789", "executor_id": None},
        ]
        
        lockfile = manager.freeze(chain)
        
        assert lockfile.lockfile_version == 1
        assert lockfile.root.tool_id == "my_script"
        assert lockfile.root.version == "1.0.0"
        assert len(lockfile.resolved_chain) == 3
        assert lockfile.registry.url == "https://example.com"
    
    def test_freeze_empty_chain_fails(self):
        """Freeze should fail on empty chain."""
        manager = LockfileManager()
        
        with pytest.raises(LockfileError):
            manager.freeze([])
    
    def test_save_and_load(self):
        """Lockfile should round-trip through save/load."""
        manager = LockfileManager()
        
        chain = [
            {"tool_id": "test", "version": "1.0.0", "content_hash": "abc", "executor_id": None},
        ]
        lockfile = manager.freeze(chain)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.lock.json"
            
            manager.save(lockfile, path)
            loaded = manager.load(path)
            
            assert loaded.root.tool_id == lockfile.root.tool_id
            assert loaded.root.version == lockfile.root.version
            assert len(loaded.resolved_chain) == len(lockfile.resolved_chain)
    
    def test_load_missing_file(self):
        """Loading missing file should fail."""
        manager = LockfileManager()
        
        with pytest.raises(LockfileError) as exc:
            manager.load(Path("/nonexistent/file.json"))
        
        assert "not found" in str(exc.value).lower()
    
    def test_validate_against_chain_success(self):
        """Matching chain should validate."""
        manager = LockfileManager()
        
        chain = [
            {"tool_id": "test", "version": "1.0.0", "content_hash": "abc123"},
        ]
        lockfile = manager.freeze(chain)
        
        result = manager.validate_against_chain(lockfile, chain)
        
        assert result["valid"] is True
    
    def test_validate_against_chain_version_mismatch(self):
        """Version mismatch should fail."""
        manager = LockfileManager()
        
        chain = [{"tool_id": "test", "version": "1.0.0", "content_hash": "abc"}]
        lockfile = manager.freeze(chain)
        
        different_chain = [{"tool_id": "test", "version": "2.0.0", "content_hash": "abc"}]
        result = manager.validate_against_chain(lockfile, different_chain)
        
        assert result["valid"] is False
        assert "mismatch" in result["issues"][0].lower()
    
    def test_validate_against_chain_integrity_mismatch(self):
        """Integrity mismatch should fail."""
        manager = LockfileManager()
        
        chain = [{"tool_id": "test", "version": "1.0.0", "content_hash": "abc"}]
        lockfile = manager.freeze(chain)
        
        different_chain = [{"tool_id": "test", "version": "1.0.0", "content_hash": "xyz"}]
        result = manager.validate_against_chain(lockfile, different_chain)
        
        assert result["valid"] is False
        assert "integrity" in result["issues"][0].lower()
    
    def test_get_pinned_versions(self):
        """Should extract version mapping from lockfile."""
        manager = LockfileManager()
        
        chain = [
            {"tool_id": "a", "version": "1.0.0", "content_hash": "x"},
            {"tool_id": "b", "version": "2.0.0", "content_hash": "y"},
        ]
        lockfile = manager.freeze(chain)
        
        versions = manager.get_pinned_versions(lockfile)
        
        assert versions == {"a": "1.0.0", "b": "2.0.0"}
