"""Tests for MCP client pool functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from kiwi_mcp.mcp.pool import MCPClientPool
from kiwi_mcp.mcp.registry import MCPConfig


@pytest.fixture
def pool():
    """Create a fresh MCP client pool."""
    return MCPClientPool()


@pytest.mark.asyncio
async def test_get_client_creates_new_client(pool):
    """Test that get_client creates a new client for unknown MCP."""
    mock_config = MCPConfig(name="test", transport="stdio")
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=[{"name": "tool1"}])

    with (
        patch("kiwi_mcp.mcp.pool.get_mcp_config", return_value=mock_config),
        patch("kiwi_mcp.mcp.pool.MCPClient", return_value=mock_client),
    ):
        client = await pool.get_client("test")

        assert client == mock_client
        assert "test" in pool._clients
        assert pool._clients["test"] == mock_client
        mock_client.connect.assert_called_once()
        mock_client.list_tools.assert_called_once()


@pytest.mark.asyncio
async def test_get_client_reuses_existing_client(pool):
    """Test that get_client reuses existing client connection."""
    mock_client = AsyncMock()
    pool._clients["test"] = mock_client

    client = await pool.get_client("test")

    assert client == mock_client
    # Should not call connect or list_tools again
    mock_client.connect.assert_not_called()
    mock_client.list_tools.assert_not_called()


@pytest.mark.asyncio
async def test_get_client_unknown_mcp_raises_error(pool):
    """Test that get_client raises error for unknown MCP."""
    with patch("kiwi_mcp.mcp.pool.get_mcp_config", return_value=None):
        with pytest.raises(ValueError, match="Unknown MCP: unknown"):
            await pool.get_client("unknown")


@pytest.mark.asyncio
async def test_get_tool_schemas_returns_all_tools(pool):
    """Test getting all tool schemas from an MCP."""
    mock_schemas = [
        {"name": "tool1", "description": "Tool 1"},
        {"name": "tool2", "description": "Tool 2"},
    ]

    # Mock the get_client method to avoid connection
    pool.get_client = AsyncMock()
    pool._schemas["test"] = mock_schemas

    result = await pool.get_tool_schemas("test")

    assert result == mock_schemas
    pool.get_client.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_get_tool_schemas_with_filter(pool):
    """Test getting filtered tool schemas from an MCP."""
    mock_schemas = [
        {"name": "tool1", "description": "Tool 1"},
        {"name": "tool2", "description": "Tool 2"},
        {"name": "tool3", "description": "Tool 3"},
    ]

    # Mock the get_client method to avoid connection
    pool.get_client = AsyncMock()
    pool._schemas["test"] = mock_schemas

    result = await pool.get_tool_schemas("test", tool_filter=["tool1", "tool3"])

    expected = [
        {"name": "tool1", "description": "Tool 1"},
        {"name": "tool3", "description": "Tool 3"},
    ]
    assert result == expected


@pytest.mark.asyncio
async def test_call_tool_delegates_to_client(pool):
    """Test that call_tool delegates to the correct client."""
    mock_client = AsyncMock()
    mock_client.call_tool = AsyncMock(return_value={"result": "success"})

    pool.get_client = AsyncMock(return_value=mock_client)

    result = await pool.call_tool("test", "tool1", {"arg": "value"})

    assert result == {"result": "success"}
    pool.get_client.assert_called_once_with("test")
    mock_client.call_tool.assert_called_once_with("tool1", {"arg": "value"})


@pytest.mark.asyncio
async def test_close_all_closes_all_clients(pool):
    """Test that close_all closes all client connections."""
    mock_client1 = AsyncMock()
    mock_client2 = AsyncMock()

    pool._clients = {"client1": mock_client1, "client2": mock_client2}
    pool._schemas = {"client1": [], "client2": []}

    await pool.close_all()

    mock_client1.close.assert_called_once()
    mock_client2.close.assert_called_once()
    assert len(pool._clients) == 0
    assert len(pool._schemas) == 0


@pytest.mark.asyncio
async def test_concurrent_client_access_uses_locks(pool):
    """Test that concurrent access to same MCP uses locks properly."""
    import asyncio

    mock_config = MCPConfig(name="test", transport="stdio")
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=[])

    # Counter to track how many times client is created
    create_count = 0

    def create_mock_client(*args, **kwargs):
        nonlocal create_count
        create_count += 1
        return mock_client

    with (
        patch("kiwi_mcp.mcp.pool.get_mcp_config", return_value=mock_config),
        patch("kiwi_mcp.mcp.pool.MCPClient", side_effect=create_mock_client),
    ):
        # Start multiple concurrent requests for the same MCP
        tasks = [pool.get_client("test") for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All should return the same client instance
        assert all(client == mock_client for client in results)
        # Client should only be created once due to locking
        assert create_count == 1
        mock_client.connect.assert_called_once()
