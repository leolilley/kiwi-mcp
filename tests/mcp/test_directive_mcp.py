"""Tests for directive MCP parsing functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
from kiwi_mcp.handlers.directive.handler import DirectiveHandler


@pytest.fixture
def handler(tmp_path):
    """Create a directive handler with temporary project path."""
    return DirectiveHandler(str(tmp_path))


def test_parse_mcps_empty():
    """Test parsing empty MCP declarations."""
    handler = DirectiveHandler("/tmp")

    # Empty directive data
    result = handler._parse_mcps({})
    assert result == []

    # No mcps section
    result = handler._parse_mcps({"parsed": {}})
    assert result == []


def test_parse_mcps_single():
    """Test parsing single MCP declaration."""
    handler = DirectiveHandler("/tmp")

    directive_data = {
        "parsed": {
            "mcps": {
                "mcp": {
                    "_attrs": {
                        "name": "github",
                        "required": "true",
                        "tools": "list_repos,get_repo",
                        "refresh": "false",
                    }
                }
            }
        }
    }

    result = handler._parse_mcps(directive_data)
    expected = [
        {"name": "github", "required": True, "tools": ["list_repos", "get_repo"], "refresh": False}
    ]

    assert result == expected


def test_parse_mcps_multiple():
    """Test parsing multiple MCP declarations."""
    handler = DirectiveHandler("/tmp")

    directive_data = {
        "parsed": {
            "mcps": {
                "mcp": [
                    {"_attrs": {"name": "github", "required": "true"}},
                    {
                        "_attrs": {
                            "name": "supabase",
                            "required": "false",
                            "tools": "query",
                            "refresh": "true",
                        }
                    },
                ]
            }
        }
    }

    result = handler._parse_mcps(directive_data)
    expected = [
        {"name": "github", "required": True, "tools": None, "refresh": False},
        {"name": "supabase", "required": False, "tools": ["query"], "refresh": True},
    ]

    assert result == expected


def test_parse_mcps_minimal_attributes():
    """Test parsing MCP with minimal attributes."""
    handler = DirectiveHandler("/tmp")

    directive_data = {"parsed": {"mcps": {"mcp": {"_attrs": {"name": "filesystem"}}}}}

    result = handler._parse_mcps(directive_data)
    expected = [
        {
            "name": "filesystem",
            "required": False,  # Default
            "tools": None,  # Default (all tools)
            "refresh": False,  # Default
        }
    ]

    assert result == expected


def test_parse_mcps_with_empty_tools():
    """Test parsing MCP with empty tools attribute."""
    handler = DirectiveHandler("/tmp")

    directive_data = {"parsed": {"mcps": {"mcp": {"_attrs": {"name": "test", "tools": ""}}}}}

    result = handler._parse_mcps(directive_data)
    expected = [
        {
            "name": "test",
            "required": False,
            "tools": None,  # Empty string should result in None
            "refresh": False,
        }
    ]

    assert result == expected


@pytest.mark.asyncio
async def test_run_directive_with_mcps_success(handler):
    """Test running directive with successful MCP connections."""
    # Mock the directive file and parsing
    from unittest.mock import MagicMock
    mock_file_path = MagicMock(spec=Path)
    # Mock read_text to return valid directive content (needed for signature verification)
    mock_file_path.read_text.return_value = """<!-- kiwi-mcp:validated:2024-01-01T00:00:00Z:abc123 -->

# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="test">
      <action>Test action</action>
    </step>
  </process>
</directive>
```
"""
    mock_file_path.__str__ = lambda self=None: "/tmp/test.md"
    mock_directive_data = {
        "name": "test_directive",
        "description": "Test directive",
        "version": "1.0.0",
        "parsed": {
            "process": {
                "step": {
                    "_attrs": {"name": "test"},
                    "action": "Test action",
                }
            },
            "inputs": {"input": []},
            "mcps": {"mcp": {"_attrs": {"name": "github", "required": "false"}}},
        },
    }

    mock_schemas = [{"name": "list_repos", "description": "List repositories"}]

    with (
        patch.object(handler.resolver, "resolve", return_value=mock_file_path),
        patch(
            "kiwi_mcp.handlers.directive.handler.parse_directive_file",
            return_value=mock_directive_data,
        ),
        patch("kiwi_mcp.handlers.directive.handler.ValidationManager.validate_and_embed") as mock_validate,
        patch("kiwi_mcp.handlers.directive.handler.MetadataManager.verify_signature") as mock_verify,
        patch.object(handler.schema_cache, "get", return_value=None),
        patch.object(
            handler.mcp_pool, "get_tool_schemas", return_value=mock_schemas
        ) as mock_get_schemas,
        patch.object(handler.schema_cache, "set") as mock_cache_set,
    ):
        # Mock validation and metadata checks (static methods)
        mock_validate.return_value = {"valid": True, "issues": []}
        mock_verify.return_value = {"status": "valid"}

        result = await handler._run_directive("test_directive", {})

        # Verify MCP tools were fetched and cached
        mock_get_schemas.assert_called_once_with("github", None)
        mock_cache_set.assert_called_once_with("github", mock_schemas)

        # Verify result includes tool context
        assert result["status"] == "ready"
        assert "tool_context" in result
        assert "github" in result["tool_context"]
        assert result["tool_context"]["github"]["available"] is True
        assert result["tool_context"]["github"]["tools"] == mock_schemas
        assert "call_format" in result


@pytest.mark.asyncio
async def test_run_directive_with_required_mcp_failure(handler):
    """Test running directive when required MCP connection fails."""
    from unittest.mock import MagicMock
    mock_file_path = MagicMock(spec=Path)
    # Mock read_text to return valid directive content (needed for signature verification)
    mock_file_path.read_text.return_value = """<!-- kiwi-mcp:validated:2024-01-01T00:00:00Z:abc123 -->

# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="test">
      <action>Test action</action>
    </step>
  </process>
</directive>
```
"""
    mock_file_path.__str__ = lambda self=None: "/tmp/test.md"
    mock_directive_data = {
        "name": "test_directive",
        "description": "Test directive",
        "version": "1.0.0",
        "parsed": {
            "mcps": {
                "mcp": {
                    "_attrs": {
                        "name": "github",
                        "required": "true",  # Required MCP
                    }
                }
            }
        },
    }

    with (
        patch.object(handler.resolver, "resolve", return_value=mock_file_path),
        patch(
            "kiwi_mcp.handlers.directive.handler.parse_directive_file",
            return_value=mock_directive_data,
        ),
            patch("kiwi_mcp.handlers.directive.handler.ValidationManager.validate_and_embed") as mock_validate,
            patch("kiwi_mcp.handlers.directive.handler.MetadataManager.verify_signature") as mock_verify,
        patch.object(handler.schema_cache, "get", return_value=None),
        patch.object(
            handler.mcp_pool, "get_tool_schemas", side_effect=Exception("Connection failed")
        ),
    ):
        # Mock validation and metadata checks (static methods)
        mock_validate.return_value = {"valid": True, "issues": []}
        mock_verify.return_value = {"status": "valid"}

        result = await handler._run_directive("test_directive", {})

        # Should return error for required MCP failure
        assert "error" in result
        assert "Required MCP 'github' connection failed" in result["error"]
        assert "Connection failed" in result["mcp_error"]


@pytest.mark.asyncio
async def test_run_directive_with_optional_mcp_failure(handler):
    """Test running directive when optional MCP connection fails."""
    from unittest.mock import MagicMock
    mock_file_path = MagicMock(spec=Path)
    # Mock read_text to return valid directive content (needed for signature verification)
    mock_file_path.read_text.return_value = """<!-- kiwi-mcp:validated:2024-01-01T00:00:00Z:abc123 -->

# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <permissions>
      <allow type="read" scope="all" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
  <process>
    <step name="test">
      <action>Test action</action>
    </step>
  </process>
</directive>
```
"""
    mock_file_path.__str__ = lambda self=None: "/tmp/test.md"
    mock_directive_data = {
        "name": "test_directive",
        "description": "Test directive",
        "version": "1.0.0",
        "parsed": {
            "process": {
                "step": {
                    "_attrs": {"name": "test"},
                    "action": "Test action",
                }
            },
            "inputs": {"input": []},
            "mcps": {
                "mcp": {
                    "_attrs": {
                        "name": "github",
                        "required": "false",  # Optional MCP
                    }
                }
            },
        },
    }

    with (
        patch.object(handler.resolver, "resolve", return_value=mock_file_path),
        patch(
            "kiwi_mcp.handlers.directive.handler.parse_directive_file",
            return_value=mock_directive_data,
        ),
            patch("kiwi_mcp.handlers.directive.handler.ValidationManager.validate_and_embed") as mock_validate,
            patch("kiwi_mcp.handlers.directive.handler.MetadataManager.verify_signature") as mock_verify,
        patch.object(handler.schema_cache, "get", return_value=None),
        patch.object(
            handler.mcp_pool, "get_tool_schemas", side_effect=Exception("Connection failed")
        ),
    ):
        # Mock validation and metadata checks (static methods)
        mock_validate.return_value = {"valid": True, "issues": []}
        mock_verify.return_value = {"status": "valid"}

        result = await handler._run_directive("test_directive", {})

        # Should succeed but mark MCP as unavailable
        assert result["status"] == "ready"
        assert "tool_context" in result
        assert "github" in result["tool_context"]
        assert result["tool_context"]["github"]["available"] is False
        assert "error" in result["tool_context"]["github"]
