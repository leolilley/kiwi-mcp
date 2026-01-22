"""Tests for MCP client functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from kiwi_mcp.mcp.client import MCPClient
from kiwi_mcp.mcp.registry import MCPConfig


@pytest.fixture
def mock_config():
    """Create a mock MCP configuration."""
    return MCPConfig(
        name="test",
        transport="stdio",
        command="npx",
        args=["-y", "@test/mcp-server"],
        env={"API_KEY": "${API_KEY}", "STATIC_VAR": "value"},
    )


@pytest.fixture
def mock_client(mock_config):
    """Create a mock MCP client."""
    return MCPClient(mock_config)


def test_client_initialization(mock_client, mock_config):
    """Test MCP client initialization."""
    assert mock_client.config == mock_config
    assert mock_client._session is None
    assert mock_client._tools == []


def test_env_resolution(mock_client):
    """Test environment variable resolution."""
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "test_value"

        env_template = {"API_KEY": "${API_KEY}", "STATIC": "value"}
        resolved = mock_client._resolve_env(env_template)

        assert resolved == {"API_KEY": "test_value", "STATIC": "value"}
        mock_getenv.assert_called_once_with("API_KEY", "")


def test_env_resolution_with_none():
    """Test env resolution with None input."""
    config = MCPConfig(name="test", transport="stdio")
    client = MCPClient(config)

    resolved = client._resolve_env(None)
    assert resolved == {}


@pytest.mark.asyncio
async def test_client_connect_success(mock_client):
    """Test successful MCP client connection."""
    # Mock the stdio client and session
    mock_read = AsyncMock()
    mock_write = AsyncMock()
    mock_session = AsyncMock()
    mock_tools_result = Mock()
    mock_tools_result.tools = [
        Mock(model_dump=lambda: {"name": "test_tool", "description": "A test tool"})
    ]

    with (
        patch("kiwi_mcp.mcp.client.stdio_client") as mock_stdio_client,
        patch("kiwi_mcp.mcp.client.ClientSession") as mock_session_class,
        patch("os.getenv", return_value="test_key"),
    ):
        # Setup mocks
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_stdio_client.return_value = mock_context_manager

        mock_session_class.return_value = mock_session
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)

        # Test connection
        await mock_client.connect()

        # Verify connection was established
        assert mock_client._session == mock_session
        assert len(mock_client._tools) == 1
        assert mock_client._tools[0]["name"] == "test_tool"


@pytest.mark.asyncio
async def test_list_tools(mock_client):
    """Test listing tools from MCP client."""
    # Setup mock tools
    mock_client._tools = [
        {"name": "tool1", "description": "Tool 1"},
        {"name": "tool2", "description": "Tool 2"},
    ]

    tools = await mock_client.list_tools()
    assert len(tools) == 2
    assert tools[0]["name"] == "tool1"
    assert tools[1]["name"] == "tool2"


@pytest.mark.asyncio
async def test_call_tool(mock_client):
    """Test calling a tool through MCP client."""
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.model_dump.return_value = {"result": "success"}
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    mock_client._session = mock_session

    result = await mock_client.call_tool("test_tool", {"arg": "value"})

    assert result == {"result": "success"}
    mock_session.call_tool.assert_called_once_with("test_tool", {"arg": "value"})


@pytest.mark.asyncio
async def test_client_close(mock_client):
    """Test closing MCP client connection."""
    mock_session = AsyncMock()
    mock_client._session = mock_session

    await mock_client.close()

    mock_session.__aexit__.assert_called_once_with(None, None, None)
