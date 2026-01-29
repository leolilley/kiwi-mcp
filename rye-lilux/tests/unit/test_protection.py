"""Tests for protection enforcement."""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "rye" / ".ai" / "tools" / "core"))

from protection import (
    is_protected_path,
    check_shadow_allowed,
    validate_file_path,
    PROTECTED_PREFIXES,
    execute,
)


class TestProtectedPaths:
    """Test protected path detection."""

    def test_tool_core_is_protected(self):
        """Core tools are protected."""
        assert is_protected_path("tool", "core/registry") is True
        assert is_protected_path("tool", "core/system") is True
        assert is_protected_path("tool", "core/rag") is True

    def test_tool_primitives_is_protected(self):
        """Primitives are protected."""
        assert is_protected_path("tool", "primitives/http_client") is True
        assert is_protected_path("tool", "primitives/subprocess") is True

    def test_tool_runtimes_is_protected(self):
        """Runtimes are protected."""
        assert is_protected_path("tool", "runtimes/auth") is True
        assert is_protected_path("tool", "runtimes/env_resolver") is True

    def test_tool_capabilities_is_protected(self):
        """Capabilities are protected."""
        assert is_protected_path("tool", "capabilities/capability_tokens") is True

    def test_tool_user_namespace_not_protected(self):
        """User tools are not protected."""
        assert is_protected_path("tool", "my_tool") is False
        assert is_protected_path("tool", "utility/scraper") is False
        assert is_protected_path("tool", "custom/my_http_client") is False

    def test_knowledge_lilux_is_protected(self):
        """Lilux knowledge is protected."""
        assert is_protected_path("knowledge", "lilux/overview") is True
        assert is_protected_path("knowledge", "lilux/primitives") is True

    def test_knowledge_rye_is_protected(self):
        """RYE knowledge is protected."""
        assert is_protected_path("knowledge", "rye/threading") is True
        assert is_protected_path("knowledge", "rye/harness") is True

    def test_knowledge_user_namespace_not_protected(self):
        """User knowledge is not protected."""
        assert is_protected_path("knowledge", "my_notes") is False
        assert is_protected_path("knowledge", "patterns/api_design") is False
        assert is_protected_path("knowledge", "concepts/my_concept") is False

    def test_directives_never_protected(self):
        """Directives are NEVER protected - always shadowable."""
        assert is_protected_path("directive", "core/init") is False
        assert is_protected_path("directive", "core/bootstrap") is False
        assert is_protected_path("directive", "anything") is False


class TestShadowAllowed:
    """Test shadow permission checking."""

    def test_tool_core_shadow_not_allowed(self):
        """Cannot shadow core tools."""
        allowed, error = check_shadow_allowed("tool", "core/registry")
        assert allowed is False
        assert "protected" in error.lower()

    def test_tool_user_shadow_allowed(self):
        """Can shadow user tools."""
        allowed, error = check_shadow_allowed("tool", "my_tool")
        assert allowed is True
        assert error is None

    def test_knowledge_lilux_shadow_not_allowed(self):
        """Cannot shadow lilux knowledge."""
        allowed, error = check_shadow_allowed("knowledge", "lilux/overview")
        assert allowed is False
        assert "protected" in error.lower()

    def test_knowledge_user_shadow_allowed(self):
        """Can shadow user knowledge."""
        allowed, error = check_shadow_allowed("knowledge", "my_notes")
        assert allowed is True
        assert error is None

    def test_directive_always_shadowable(self):
        """Directives can always be shadowed."""
        allowed, error = check_shadow_allowed("directive", "core/init")
        assert allowed is True
        assert error is None

        allowed, error = check_shadow_allowed("directive", "core/bootstrap")
        assert allowed is True
        assert error is None


class TestValidateFilePath:
    """Test file path validation."""

    def test_tool_in_core_not_allowed(self):
        """Cannot write tools to core/ in project space."""
        path = Path("/project/.ai/tools/core/my_tool.py")
        valid, error = validate_file_path("tool", path, "project")
        assert valid is False
        assert "core/" in error

    def test_tool_in_user_namespace_allowed(self):
        """Can write tools to user namespace."""
        path = Path("/project/.ai/tools/utility/my_tool.py")
        valid, error = validate_file_path("tool", path, "project")
        assert valid is True
        assert error is None

    def test_knowledge_in_lilux_not_allowed(self):
        """Cannot write knowledge to lilux/ namespace."""
        path = Path("/home/user/.ai/knowledge/lilux/my_doc.md")
        valid, error = validate_file_path("knowledge", path, "user")
        assert valid is False
        assert "lilux/" in error

    def test_knowledge_in_patterns_allowed(self):
        """Can write knowledge to patterns/."""
        path = Path("/project/.ai/knowledge/patterns/my_pattern.md")
        valid, error = validate_file_path("knowledge", path, "project")
        assert valid is True
        assert error is None

    def test_directive_anywhere_allowed(self):
        """Directives can go anywhere."""
        path = Path("/project/.ai/directives/core/my_directive.md")
        valid, error = validate_file_path("directive", path, "project")
        assert valid is True
        assert error is None


class TestExecuteAction:
    """Test execute function actions."""

    @pytest.mark.asyncio
    async def test_check_protected_tool(self):
        """Check action returns protection status."""
        result = await execute("check", {
            "item_type": "tool",
            "item_id": "core/registry",
        })
        
        assert result["is_protected"] is True
        assert result["shadow_allowed"] is False
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_check_unprotected_tool(self):
        """Check action for unprotected item."""
        result = await execute("check", {
            "item_type": "tool",
            "item_id": "my_tool",
        })
        
        assert result["is_protected"] is False
        assert result["shadow_allowed"] is True
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_validate_protected_path(self):
        """Validate action rejects protected path."""
        result = await execute("validate", {
            "item_type": "tool",
            "file_path": "/project/.ai/tools/core/my_tool.py",
            "location": "project",
        })
        
        assert result["valid"] is False
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_validate_allowed_path(self):
        """Validate action allows user path."""
        result = await execute("validate", {
            "item_type": "tool",
            "file_path": "/project/.ai/tools/utility/my_tool.py",
            "location": "project",
        })
        
        assert result["valid"] is True
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        """Unknown action returns error."""
        result = await execute("unknown", {})
        assert "error" in result
        assert "valid_actions" in result
