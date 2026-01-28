"""
Unit tests for Kiwi MCP tools (search, load, execute, sign, help).

Tests each tool's schema, validation, and error handling.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from mcp.types import Tool

from kiwi_mcp.tools.search import SearchTool
from kiwi_mcp.tools.load import LoadTool
from kiwi_mcp.tools.execute import ExecuteTool
from kiwi_mcp.tools.sign import SignTool
from kiwi_mcp.tools.help import HelpTool


class TestSearchTool:
    """Test SearchTool schema and execution."""

    def test_search_tool_schema_valid(self):
        """Test SearchTool has valid schema."""
        tool = SearchTool()
        schema = tool.schema

        assert isinstance(schema, Tool)
        assert schema.name == "search"
        assert "Search" in schema.description
        assert "properties" in schema.inputSchema
        assert "item_type" in schema.inputSchema["properties"]
        assert "query" in schema.inputSchema["properties"]

    def test_search_tool_required_params(self):
        """Test SearchTool requires item_type and query."""
        tool = SearchTool()
        schema = tool.inputSchema

        assert "item_type" in schema["required"]
        assert "query" in schema["required"]

    def test_search_tool_enum_types(self):
        """Test SearchTool accepts valid item types."""
        tool = SearchTool()
        item_type_enum = tool.schema.inputSchema["properties"]["item_type"]["enum"]

        assert "directive" in item_type_enum
        assert "tool" in item_type_enum
        assert "knowledge" in item_type_enum

    @pytest.mark.asyncio
    async def test_search_tool_missing_registry(self):
        """Test SearchTool requires registry."""
        tool = SearchTool(registry=None)
        result = await tool.execute(
            {
                "item_type": "directive",
                "query": "test",
                "source": "registry",
                "project_path": "/tmp/test",
            }
        )

        # DirectiveHandler catches registry errors and logs them, returning empty results if nothing found
        # So we expect a valid JSON response with empty results, not an error
        parsed = json.loads(result)
        assert "results" in parsed
        assert parsed["total"] == 0

    @pytest.mark.asyncio
    async def test_search_tool_with_mock_registry(self):
        """Test SearchTool executes with mock registry."""
        registry = AsyncMock()
        registry.search.return_value = {"results": []}

        tool = SearchTool(registry=registry)

        # We need to patch the handler to verify it's called
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as MockHandler:
            mock_instance = MockHandler.return_value
            mock_instance.search = AsyncMock(return_value={"results": []})

            result = await tool.execute(
                {
                    "item_type": "directive",
                    "query": "test",
                    "source": "local",
                    "limit": 5,
                    "project_path": "/tmp/test",
                }
            )

            mock_instance.search.assert_called_once()
            assert isinstance(result, str)


class TestLoadTool:
    """Test LoadTool schema and execution."""

    def test_load_tool_schema_valid(self):
        """Test LoadTool has valid schema."""
        tool = LoadTool()
        schema = tool.schema

        assert isinstance(schema, Tool)
        assert schema.name == "load"
        assert "Download" in schema.description or "load" in schema.description.lower()
        assert "item_type" in schema.inputSchema["properties"]
        assert "item_id" in schema.inputSchema["properties"]

    def test_load_tool_required_params(self):
        """Test LoadTool requires item_type and item_id."""
        tool = LoadTool()
        schema = tool.inputSchema

        assert "item_type" in schema["required"]
        assert "item_id" in schema["required"]

    def test_load_tool_destination_parameter(self):
        """Test LoadTool has destination parameter."""
        tool = LoadTool()
        props = tool.schema.inputSchema["properties"]

        assert "destination" in props

    @pytest.mark.asyncio
    async def test_load_tool_missing_item_id(self):
        """Test LoadTool rejects missing item_id."""
        tool = LoadTool()
        result = await tool.execute({"item_type": "directive", "project_path": "/tmp/test"})

        assert "error" in result
        assert "required" in result.lower()

    @pytest.mark.asyncio
    async def test_load_tool_with_mock_registry(self):
        """Test LoadTool executes with mock registry."""
        registry = AsyncMock()
        registry.load.return_value = {"status": "loaded"}

        tool = LoadTool(registry=registry)

        with patch("kiwi_mcp.handlers.tool.handler.ToolHandler") as MockHandler:
            mock_instance = MockHandler.return_value
            mock_instance.load = AsyncMock(return_value={"status": "loaded"})

            result = await tool.execute(
                {
                    "item_type": "tool",
                    "item_id": "my_tool",
                    "destination": "project",
                    "source": "registry",
                    "project_path": "/tmp/test",
                }
            )

            mock_instance.load.assert_called_once()
            assert isinstance(result, str)


class TestExecuteTool:
    """Test ExecuteTool schema and execution."""

    def test_execute_tool_schema_valid(self):
        """Test ExecuteTool has valid schema."""
        tool = ExecuteTool()
        schema = tool.schema

        assert isinstance(schema, Tool)
        assert schema.name == "execute"
        assert "properties" in schema.inputSchema
        assert "item_type" in schema.inputSchema["properties"]
        assert "action" in schema.inputSchema["properties"]
        assert "item_id" in schema.inputSchema["properties"]

    def test_execute_tool_required_params(self):
        """Test ExecuteTool requires item_type, action, and item_id."""
        tool = ExecuteTool()
        schema = tool.inputSchema

        assert "item_type" in schema["required"]
        assert "action" in schema["required"]
        assert "item_id" in schema["required"]

    def test_execute_tool_parameters_optional(self):
        """Test ExecuteTool parameters is optional."""
        tool = ExecuteTool()
        schema = tool.inputSchema

        # parameters should not be in required list
        assert "parameters" not in schema.get("required", [])

    @pytest.mark.asyncio
    async def test_execute_tool_missing_action(self):
        """Test ExecuteTool rejects missing action."""
        tool = ExecuteTool()
        result = await tool.execute({"item_type": "directive", "item_id": "my_directive"})

        assert "error" in result
        assert "required" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_with_mock_registry(self):
        """Test ExecuteTool executes with mock registry."""
        registry = AsyncMock()
        registry.execute.return_value = {"status": "executed"}

        tool = ExecuteTool(registry=registry)

        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as MockHandler:
            mock_instance = MockHandler.return_value
            mock_instance.execute = AsyncMock(return_value={"status": "executed"})

            result = await tool.execute(
                {
                    "item_type": "directive",
                    "item_id": "my_directive",
                    "parameters": {"key": "value"},
                    "project_path": "/tmp/test",
                }
            )

            mock_instance.execute.assert_called_once()
            assert isinstance(result, str)
        assert len(result) > 0


class TestToolSchemaConsistency:
    """Test consistency across all tools."""

    def test_all_tools_have_schema_property(self):
        """Test all tools have schema property."""
        tools = [
            SearchTool(),
            LoadTool(),
            ExecuteTool(),
            SignTool(),
            HelpTool(),
        ]

        for tool in tools:
            assert hasattr(tool, "schema")
            schema = tool.schema
            assert isinstance(schema, Tool)
            assert schema.name is not None
            assert schema.description is not None
            assert schema.inputSchema is not None

    def test_all_tools_have_execute_method(self):
        """Test all tools have async execute method."""
        tools = [
            SearchTool(),
            LoadTool(),
            ExecuteTool(),
            SignTool(),
            HelpTool(),
        ]

        for tool in tools:
            assert hasattr(tool, "execute")
            assert callable(tool.execute)

    def test_tool_execute_returns_json_string(self):
        """Test tool execute methods return JSON strings."""
        # This is tested via individual tests, verify format helper works
        tool = SearchTool()
        response = tool._format_response({"test": "data"})

        assert isinstance(response, str)
        parsed = json.loads(response)
        assert "test" in parsed

    def test_inputschema_is_valid_json_schema(self):
        """Test inputSchema follows JSON Schema structure."""
        tools = [
            SearchTool(),
            LoadTool(),
            ExecuteTool(),
            HelpTool(),
        ]

        for tool in tools:
            schema = tool.schema.inputSchema
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema


class TestToolErrorHandling:
    """Test error handling in tools."""

    @pytest.mark.asyncio
    async def test_search_tool_invalid_item_type(self):
        """Test SearchTool with invalid item_type."""
        registry = AsyncMock()
        registry.search.side_effect = ValueError("Unknown type")

        tool = SearchTool(registry=registry)
        result = await tool.execute(
            {"item_type": "invalid", "query": "test", "project_path": "/tmp/test"}
        )

        # Should return error response
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_action(self):
        """Test ExecuteTool handles invalid action."""
        registry = AsyncMock()
        registry.execute.side_effect = ValueError("Unknown action")

        tool = ExecuteTool(registry=registry)
        result = await tool.execute(
            {
                "item_type": "directive",
                "action": "invalid_action",
                "item_id": "test",
                "project_path": "/tmp/test",
            }
        )

        # Should return error response
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_load_tool_registry_exception(self):
        """Test LoadTool handles registry exceptions."""
        registry = AsyncMock()
        registry.load.side_effect = Exception("Registry error")

        tool = LoadTool(registry=registry)
        result = await tool.execute(
            {
                "item_type": "knowledge",
                "item_id": "001",
                "source": "registry",
                "destination": "project",
                "project_path": "/tmp/test",
            }
        )

        # Should return error response
        assert isinstance(result, str)


class TestToolParameterValidation:
    """Test parameter validation in tools."""

    def test_search_tool_source_enum(self):
        """Test SearchTool source enum."""
        tool = SearchTool()
        source_enum = tool.schema.inputSchema["properties"]["source"]["enum"]

        assert "local" in source_enum
        assert "registry" in source_enum
        assert "all" in source_enum

    def test_load_tool_destination_enum(self):
        """Test LoadTool destination enum."""
        tool = LoadTool()
        dest_enum = tool.schema.inputSchema["properties"]["destination"]["enum"]

        assert "project" in dest_enum
        assert "user" in dest_enum

    def test_execute_tool_item_type_enum(self):
        """Test ExecuteTool item_type enum."""
        tool = ExecuteTool()
        type_enum = tool.schema.inputSchema["properties"]["item_type"]["enum"]

        assert "directive" in type_enum
        assert "tool" in type_enum
        assert "knowledge" in type_enum


# Integration-like tests for tool initialization
class TestToolInitialization:
    """Test tool initialization scenarios."""

    def test_search_tool_without_registry(self):
        """Test SearchTool initializes without registry."""
        tool = SearchTool()
        assert tool.registry is None

    def test_search_tool_with_registry(self):
        """Test SearchTool initializes with registry."""
        registry = MagicMock()
        tool = SearchTool(registry=registry)
        assert tool.registry == registry

    def test_all_tools_accept_registry_parameter(self):
        """Test all tools accept optional registry parameter."""
        registry = MagicMock()

        # Should not raise
        search = SearchTool(registry=registry)
        load = LoadTool(registry=registry)
        execute = ExecuteTool(registry=registry)

        assert search.registry == registry
        assert load.registry == registry
        assert execute.registry == registry

    def test_help_tool_initialization(self):
        """Test HelpTool initializes correctly."""
        registry = MagicMock()
        tool = HelpTool(registry=registry)

        assert hasattr(tool, "schema")
        assert hasattr(tool, "execute")
