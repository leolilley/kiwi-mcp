"""
Tests for the capability token system.

Tests cover:
- CapabilityToken creation, serialization, and verification
- Token signing and verification with Ed25519
- Permissions→capabilities conversion
- Token attenuation (set intersection)
- Capability registry discovery
- Harness integration
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from safety_harness.capabilities import (
    CapabilityToken,
    TokenSigner,
    sign_token,
    verify_token,
    permissions_to_caps,
    mint_token,
    attenuate_token,
)

from pathlib import Path
import sys

# Add .ai/tools to path for capability imports
ai_tools_path = Path(__file__).parent.parent.parent / ".ai" / "tools"
if str(ai_tools_path) not in sys.path:
    sys.path.insert(0, str(ai_tools_path))

# Import capabilities module
try:
    import capabilities as cap_module
    load_all_capabilities = cap_module.load_all_capabilities
    is_valid_capability = cap_module.is_valid_capability
    get_registry = cap_module.get_registry
except ImportError:
    # Fallback for when .ai/tools is not accessible
    def load_all_capabilities():
        return {}
    
    def is_valid_capability(cap_id):
        return True
    
    def get_registry():
        return None


class TestCapabilityToken:
    """Test CapabilityToken dataclass."""

    def test_create_token(self):
        """Test creating a capability token."""
        exp = datetime.now(timezone.utc) + timedelta(hours=1)
        token = CapabilityToken(
            caps=["fs.read", "fs.write"],
            aud="kiwi-mcp",
            exp=exp,
            directive_id="test_directive",
            thread_id="thread-123",
        )
        
        assert token.caps == ["fs.read", "fs.write"]
        assert token.aud == "kiwi-mcp"
        assert token.directive_id == "test_directive"
        assert token.thread_id == "thread-123"
        assert token.parent_id is None
        assert token.signature is None

    def test_is_expired(self):
        """Test token expiry detection."""
        # Not expired
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = CapabilityToken(
            caps=["fs.read"],
            aud="kiwi-mcp",
            exp=future,
            directive_id="test",
            thread_id="thread-1",
        )
        assert not token.is_expired()
        
        # Expired
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_token = CapabilityToken(
            caps=["fs.read"],
            aud="kiwi-mcp",
            exp=past,
            directive_id="test",
            thread_id="thread-1",
        )
        assert expired_token.is_expired()

    def test_has_capability(self):
        """Test checking for capability in token."""
        token = CapabilityToken(
            caps=["fs.read", "fs.write", "spawn.thread"],
            aud="kiwi-mcp",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            directive_id="test",
            thread_id="thread-1",
        )
        
        assert token.has_capability("fs.read")
        assert token.has_capability("fs.write")
        assert token.has_capability("spawn.thread")
        assert not token.has_capability("registry.write")

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        exp = datetime.now(timezone.utc) + timedelta(hours=1)
        original = CapabilityToken(
            caps=["fs.read", "fs.write"],
            aud="kiwi-mcp",
            exp=exp,
            directive_id="test_directive",
            thread_id="thread-123",
            parent_id="parent-token",
            signature="sig123",
        )
        
        # Serialize
        data = original.to_dict()
        assert data["caps"] == ["fs.read", "fs.write"]
        assert data["directive_id"] == "test_directive"
        assert data["signature"] == "sig123"
        
        # Deserialize
        restored = CapabilityToken.from_dict(data)
        assert restored.caps == original.caps
        assert restored.directive_id == original.directive_id
        assert restored.parent_id == original.parent_id
        assert restored.signature == original.signature


class TestTokenSigning:
    """Test token signing and verification."""

    @pytest.fixture
    def temp_keys(self):
        """Create temporary key directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_sign_and_verify_token(self, temp_keys):
        """Test signing and verifying a token."""
        # Create signer with temp keys
        private_key_path = os.path.join(temp_keys, "private_key.pem")
        public_key_path = os.path.join(temp_keys, "public_key.pem")
        signer = TokenSigner(private_key_path, public_key_path)
        
        # Create and sign token
        token = CapabilityToken(
            caps=["fs.read", "fs.write"],
            aud="kiwi-mcp",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            directive_id="test_directive",
            thread_id="thread-123",
        )
        
        signed_token_str = signer.sign_token(token)
        assert isinstance(signed_token_str, str)
        assert len(signed_token_str) > 0
        
        # Verify token
        verified_token = signer.verify_token(signed_token_str)
        assert verified_token is not None
        assert verified_token.caps == token.caps
        assert verified_token.directive_id == token.directive_id
        assert verified_token.signature is not None

    def test_verify_tampered_token(self, temp_keys):
        """Test that tampered tokens are rejected."""
        private_key_path = os.path.join(temp_keys, "private_key.pem")
        public_key_path = os.path.join(temp_keys, "public_key.pem")
        signer = TokenSigner(private_key_path, public_key_path)
        
        token = CapabilityToken(
            caps=["fs.read"],
            aud="kiwi-mcp",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            directive_id="test",
            thread_id="thread-1",
        )
        
        signed_token_str = signer.sign_token(token)
        
        # Tamper with token
        tampered = signed_token_str[:-10] + "0000000000"
        
        # Should reject tampered token
        verified = signer.verify_token(tampered)
        assert verified is None

    def test_verify_expired_token(self, temp_keys):
        """Test that expired tokens are rejected."""
        private_key_path = os.path.join(temp_keys, "private_key.pem")
        public_key_path = os.path.join(temp_keys, "public_key.pem")
        signer = TokenSigner(private_key_path, public_key_path)
        
        token = CapabilityToken(
            caps=["fs.read"],
            aud="kiwi-mcp",
            exp=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            directive_id="test",
            thread_id="thread-1",
        )
        
        signed_token_str = signer.sign_token(token)
        
        # Should reject expired token
        verified = signer.verify_token(signed_token_str)
        assert verified is None


class TestPermissionsToCaps:
    """Test conversion from directive permissions to capabilities."""

    def test_filesystem_permissions(self):
        """Test filesystem permission conversion."""
        perms = [
            {"tag": "read", "attrs": {"resource": "filesystem"}},
            {"tag": "write", "attrs": {"resource": "filesystem"}},
        ]
        
        caps = permissions_to_caps(perms)
        assert "fs.read" in caps
        assert "fs.write" in caps

    def test_tool_permissions(self):
        """Test tool permission conversion."""
        perms = [
            {"tag": "execute", "attrs": {"resource": "tool", "id": "bash"}},
            {"tag": "execute", "attrs": {"resource": "tool", "id": "pytest"}},
        ]
        
        caps = permissions_to_caps(perms)
        assert "tool.bash" in caps
        assert "tool.pytest" in caps

    def test_spawn_permission(self):
        """Test spawn thread permission conversion."""
        perms = [
            {"tag": "execute", "attrs": {"resource": "spawn", "action": "thread"}},
        ]
        
        caps = permissions_to_caps(perms)
        assert "spawn.thread" in caps

    def test_registry_permission(self):
        """Test registry write permission conversion."""
        perms = [
            {"tag": "execute", "attrs": {"resource": "registry", "action": "write"}},
        ]
        
        caps = permissions_to_caps(perms)
        assert "registry.write" in caps

    def test_kiwi_mcp_permissions(self):
        """Test kiwi-mcp permission conversion."""
        perms = [
            {"tag": "execute", "attrs": {"resource": "kiwi-mcp", "action": "execute"}},
            {"tag": "execute", "attrs": {"resource": "kiwi-mcp", "action": "read"}},
            {"tag": "execute", "attrs": {"resource": "kiwi-mcp", "action": "write"}},
        ]
        
        caps = permissions_to_caps(perms)
        assert "kiwi-mcp.execute" in caps
        assert "kiwi-mcp.read" in caps
        assert "kiwi-mcp.write" in caps

    def test_empty_permissions(self):
        """Test conversion of empty permissions list."""
        caps = permissions_to_caps([])
        assert caps == []

    def test_sorted_output(self):
        """Test that capabilities are sorted."""
        perms = [
            {"tag": "write", "attrs": {"resource": "filesystem"}},
            {"tag": "read", "attrs": {"resource": "filesystem"}},
        ]
        
        caps = permissions_to_caps(perms)
        assert caps == ["fs.read", "fs.write"]  # Alphabetically sorted


class TestTokenMinting:
    """Test token minting."""

    def test_mint_token(self):
        """Test minting a new token."""
        caps = ["fs.read", "fs.write"]
        token = mint_token(
            caps=caps,
            directive_id="deploy",
            thread_id="thread-1",
            exp_hours=2,
        )
        
        assert token.caps == sorted(caps)  # Should be sorted
        assert token.aud == "kiwi-mcp"
        assert token.directive_id == "deploy"
        assert token.thread_id == "thread-1"
        assert token.parent_id is None
        assert not token.is_expired()

    def test_mint_token_with_parent(self):
        """Test minting a token with parent ID."""
        token = mint_token(
            caps=["fs.read"],
            directive_id="child",
            thread_id="thread-2",
            parent_id="parent-token",
        )
        
        assert token.parent_id == "parent-token"

    def test_mint_token_default_expiry(self):
        """Test that tokens default to 1 hour expiry."""
        token = mint_token(
            caps=["fs.read"],
            directive_id="test",
            thread_id="thread-1",
        )
        
        # Check expiry is approximately 1 hour from now
        now = datetime.now(timezone.utc)
        delta = (token.exp - now).total_seconds()
        # Should be within 60 seconds of 1 hour (3600 seconds)
        assert 3540 < delta < 3660


class TestTokenAttenuation:
    """Test token attenuation on thread spawn."""

    def test_attenuation_intersection(self):
        """Test that attenuation implements set intersection."""
        # Parent has: fs.read, fs.write, spawn.thread
        # Child wants: fs.write, tool.bash
        # Child gets: fs.write (intersection)
        
        parent_token = mint_token(
            caps=["fs.read", "fs.write", "spawn.thread"],
            directive_id="parent",
            thread_id="thread-1",
        )
        
        child_caps = ["fs.write", "tool.bash"]
        child_token = attenuate_token(parent_token, child_caps)
        
        # Child should only get fs.write (both parent has AND child declared)
        assert child_token.caps == ["fs.write"]
        # Child should NOT get tool.bash (parent doesn't have)
        # Child should NOT get fs.read (child didn't declare)
        # Child should NOT get spawn.thread (child didn't declare)

    def test_attenuation_empty_intersection(self):
        """Test attenuation when there's no intersection."""
        parent_token = mint_token(
            caps=["fs.read"],
            directive_id="parent",
            thread_id="thread-1",
        )
        
        child_caps = ["tool.bash", "spawn.thread"]
        child_token = attenuate_token(parent_token, child_caps)
        
        # No intersection - child gets nothing
        assert child_token.caps == []

    def test_attenuation_no_escalation(self):
        """Test that child cannot escalate privileges."""
        parent_token = mint_token(
            caps=["fs.read"],
            directive_id="parent",
            thread_id="thread-1",
        )
        
        # Child tries to declare more capabilities than parent has
        child_caps = ["fs.read", "fs.write", "registry.write", "spawn.thread"]
        child_token = attenuate_token(parent_token, child_caps)
        
        # Child should only get what parent has
        assert child_token.caps == ["fs.read"]

    def test_attenuation_preserves_metadata(self):
        """Test that attenuation preserves token metadata."""
        parent_token = mint_token(
            caps=["fs.read", "fs.write"],
            directive_id="parent",
            thread_id="thread-1",
        )
        
        child_token = attenuate_token(parent_token, ["fs.read"])
        
        # Should preserve audience and expiry from parent
        assert child_token.aud == parent_token.aud
        assert child_token.exp == parent_token.exp
        # Should track parent
        assert child_token.parent_id == "parent"

    def test_attenuation_full_subset(self):
        """Test attenuation when child capabilities are subset of parent."""
        parent_token = mint_token(
            caps=["fs.read", "fs.write", "spawn.thread"],
            directive_id="parent",
            thread_id="thread-1",
        )
        
        child_caps = ["fs.read"]  # Subset of parent
        child_token = attenuate_token(parent_token, child_caps)
        
        assert child_token.caps == ["fs.read"]


class TestCapabilityRegistry:
    """Test capability discovery registry."""

    def test_load_all_capabilities(self):
        """Test loading all registered capabilities."""
        caps = load_all_capabilities()
        
        assert isinstance(caps, dict)
        assert len(caps) > 0
        
        # Check for expected capabilities
        assert "fs.read" in caps
        assert "fs.write" in caps

    def test_is_valid_capability(self):
        """Test capability validation."""
        assert is_valid_capability("fs.read")
        assert is_valid_capability("fs.write")
        assert is_valid_capability("spawn.thread")
        
        # Invalid capabilities
        assert not is_valid_capability("invalid.cap")
        assert not is_valid_capability("nonexistent")

    def test_registry_discovery(self):
        """Test that registry discovers all capability modules."""
        registry = get_registry()
        caps = registry.all()
        
        # Check modules are discovered
        modules = {cap["module"] for cap in caps.values()}
        assert len(modules) >= 5  # At least fs, net, db, git, process, mcp

    def test_list_by_resource(self):
        """Test listing capabilities by resource."""
        registry = get_registry()
        
        fs_caps = registry.list_by_resource("filesystem")
        assert "fs.read" in fs_caps
        assert "fs.write" in fs_caps
        
        git_caps = registry.list_by_resource("git")
        assert "git.read" in git_caps


class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.fixture
    def temp_keys(self):
        """Create temporary key directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_full_token_lifecycle(self, temp_keys):
        """Test full token lifecycle: create, sign, verify."""
        signer = TokenSigner(
            os.path.join(temp_keys, "private_key.pem"),
            os.path.join(temp_keys, "public_key.pem"),
        )
        
        # 1. Directive defines permissions
        perms = [
            {"tag": "read", "attrs": {"resource": "filesystem"}},
            {"tag": "write", "attrs": {"resource": "filesystem"}},
            {"tag": "execute", "attrs": {"resource": "tool", "id": "bash"}},
        ]
        
        # 2. Harness converts permissions to capabilities
        caps = permissions_to_caps(perms)
        assert "fs.read" in caps
        assert "fs.write" in caps
        assert "tool.bash" in caps
        
        # 3. Harness mints token
        token = mint_token(
            caps=caps,
            directive_id="deploy",
            thread_id="thread-1",
        )
        
        # 4. Harness signs token
        signed_token_str = signer.sign_token(token)
        
        # 5. Tool receives and verifies token
        verified_token = signer.verify_token(signed_token_str)
        assert verified_token is not None
        assert verified_token.has_capability("fs.read")
        assert verified_token.has_capability("fs.write")
        assert verified_token.has_capability("tool.bash")

    def test_parent_child_thread_scenario(self, temp_keys):
        """Test parent spawning child thread with attenuated token."""
        signer = TokenSigner(
            os.path.join(temp_keys, "private_key.pem"),
            os.path.join(temp_keys, "public_key.pem"),
        )
        
        # 1. Parent thread spawned with broad permissions
        parent_perms = [
            {"tag": "read", "attrs": {"resource": "filesystem"}},
            {"tag": "write", "attrs": {"resource": "filesystem"}},
            {"tag": "execute", "attrs": {"resource": "spawn", "action": "thread"}},
        ]
        parent_caps = permissions_to_caps(parent_perms)
        parent_token = mint_token(
            caps=parent_caps,
            directive_id="orchestrator",
            thread_id="parent-1",
        )
        
        signed_parent = signer.sign_token(parent_token)
        verified_parent = signer.verify_token(signed_parent)
        
        # 2. Parent spawns child with limited permissions
        child_declared_caps = ["fs.write"]  # Child only wants to write
        child_token = attenuate_token(verified_parent, child_declared_caps)
        
        # 3. Verify child is attenuated
        assert child_token.caps == ["fs.write"]
        assert not child_token.has_capability("spawn.thread")
        
        # 4. Sign and verify child token
        signed_child = signer.sign_token(child_token)
        verified_child = signer.verify_token(signed_child)
        assert verified_child.has_capability("fs.write")
        assert not verified_child.has_capability("spawn.thread")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=safety_harness.capabilities"])
