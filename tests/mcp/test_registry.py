"""Tests for MCP registry functionality."""

import pytest
from kiwi_mcp.mcp.registry import MCPConfig, get_mcp_config, register_mcp, MCP_REGISTRY


def test_mcp_config_creation():
    """Test MCPConfig dataclass creation."""
    config = MCPConfig(
        name="test",
        transport="stdio",
        command="npx",
        args=["-y", "@test/mcp-server"],
        env={"API_KEY": "${API_KEY}"},
    )

    assert config.name == "test"
    assert config.transport == "stdio"
    assert config.command == "npx"
    assert config.args == ["-y", "@test/mcp-server"]
    assert config.env == {"API_KEY": "${API_KEY}"}


def test_builtin_mcp_configs():
    """Test that built-in MCP configurations are available."""
    # Test supabase config
    supabase = get_mcp_config("supabase")
    assert supabase is not None
    assert supabase.name == "supabase"
    assert supabase.transport == "stdio"
    assert supabase.command == "npx"

    # Test github config
    github = get_mcp_config("github")
    assert github is not None
    assert github.name == "github"
    assert github.transport == "stdio"

    # Test filesystem config
    filesystem = get_mcp_config("filesystem")
    assert filesystem is not None
    assert filesystem.name == "filesystem"


def test_get_unknown_mcp():
    """Test getting unknown MCP returns None."""
    result = get_mcp_config("unknown_mcp")
    assert result is None


def test_register_new_mcp():
    """Test registering a new MCP configuration."""
    config = MCPConfig(
        name="custom", transport="stdio", command="python", args=["-m", "custom_mcp"]
    )

    # Register the MCP
    register_mcp("custom", config)

    # Verify it can be retrieved
    retrieved = get_mcp_config("custom")
    assert retrieved is not None
    assert retrieved.name == "custom"
    assert retrieved.command == "python"

    # Clean up
    if "custom" in MCP_REGISTRY:
        del MCP_REGISTRY["custom"]


def test_mcp_config_with_optional_fields():
    """Test MCP config with only required fields."""
    config = MCPConfig(name="minimal", transport="stdio")
    assert config.command is None
    assert config.args is None
    assert config.env is None
    assert config.url is None
