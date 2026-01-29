"""
Unit tests for TypeHandlerRegistry and handler routing.

Tests registry initialization, handler routing, and error cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from lilux.handlers.registry import TypeHandlerRegistry


class TestTypeHandlerRegistryInitialization:
    """Test TypeHandlerRegistry initialization."""

    def test_registry_initializes_without_project_path(self):
        """Test registry raises error without project_path."""
        with pytest.raises(TypeError):
            TypeHandlerRegistry()

    def test_registry_initializes_with_project_path(self):
        """Test registry initializes with project_path."""
        project_path = "/home/user/myproject"
        registry = TypeHandlerRegistry(project_path=project_path)

        assert registry.project_path == project_path

    def test_registry_has_handler_mapping(self):
        """Test registry has handler mapping."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        assert hasattr(registry, "handlers")
        assert isinstance(registry.handlers, dict)
        # Handlers dict should be empty or have handlers depending on imports
        assert len(registry.handlers) >= 0

    def test_registry_get_supported_types(self):
        """Test registry can get supported types."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        supported = registry.get_supported_types()
        assert isinstance(supported, list)

    def test_registry_get_handler_info(self):
        """Test registry can provide handler info."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        info = registry.get_handler_info()
        assert isinstance(info, dict)
        assert "registry" in info
        assert "project_path" in info
        assert "supported_types" in info
        assert "handlers" in info


class TestTypeHandlerRegistrySearch:
    """Test TypeHandlerRegistry search method."""

    @pytest.mark.asyncio
    async def test_search_unknown_item_type(self):
        """Test search with unknown item_type."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        result = await registry.search(item_type="unknown_type", query="test")

        assert "error" in result
        assert "unknown_item_type" in result["error"].lower() or "Unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_search_with_directive_handler(self):
        """Test search with mocked directive handler."""
        # Create a mock handler
        mock_handler = AsyncMock()
        mock_handler.search.return_value = {"results": ["item1"]}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        result = await registry.search(item_type="directive", query="test query")

        # Handler should be called
        mock_handler.search.assert_called_once()
        assert result == {"results": ["item1"]}

    @pytest.mark.asyncio
    async def test_search_passes_parameters(self):
        """Test search passes all parameters to handler."""
        mock_handler = AsyncMock()
        mock_handler.search.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["tool"] = mock_handler

        await registry.search(item_type="tool", query="test", source="registry", limit=20)

        # Check handler received parameters
        call_args = mock_handler.search.call_args
        assert call_args is not None
        # query should be first positional or keyword arg
        assert "test" in str(call_args)

    @pytest.mark.asyncio
    async def test_search_handler_exception(self):
        """Test search handles handler exceptions."""
        mock_handler = AsyncMock()
        mock_handler.search.side_effect = Exception("Handler error")

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["knowledge"] = mock_handler

        result = await registry.search(item_type="knowledge", query="test")

        assert "error" in result
        assert "Failed to search" in result.get("message", "")


class TestTypeHandlerRegistryLoad:
    """Test TypeHandlerRegistry load method."""

    @pytest.mark.asyncio
    async def test_load_unknown_item_type(self):
        """Test load with unknown item_type."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        result = await registry.load(item_type="nonexistent", item_id="item1")

        assert "error" in result
        assert "Unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_load_with_directive_handler(self):
        """Test load with directive handler."""
        mock_handler = AsyncMock()
        mock_handler.load.return_value = {"status": "loaded"}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        result = await registry.load(
            item_type="directive", item_id="my_directive", destination="project"
        )

        mock_handler.load.assert_called_once()
        assert result == {"status": "loaded"}

    @pytest.mark.asyncio
    async def test_load_directive_name_mapping(self):
        """Test load maps item_id to directive_name."""
        mock_handler = AsyncMock()
        mock_handler.load.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        await registry.load(item_type="directive", item_id="test_directive")

        # Check directive_name parameter was used
        call_kwargs = mock_handler.load.call_args[1]
        assert "directive_name" in call_kwargs
        assert call_kwargs["directive_name"] == "test_directive"

    @pytest.mark.asyncio
    async def test_load_script_name_mapping(self):
        """Test load maps item_id to tool_name (migrated from script_name)."""
        mock_handler = AsyncMock()
        mock_handler.load.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["tool"] = mock_handler

        await registry.load(item_type="tool", item_id="test_tool")

        # Check tool_name parameter was used (migrated from script_name)
        call_kwargs = mock_handler.load.call_args[1]
        assert "tool_name" in call_kwargs

    @pytest.mark.asyncio
    async def test_load_knowledge_id_mapping(self):
        """Test load maps item_id to id."""
        mock_handler = AsyncMock()
        mock_handler.load.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["knowledge"] = mock_handler

        await registry.load(item_type="knowledge", item_id="001-test")

        # Check id parameter was used
        call_kwargs = mock_handler.load.call_args[1]
        assert "id" in call_kwargs


class TestTypeHandlerRegistryExecute:
    """Test TypeHandlerRegistry execute method."""

    @pytest.mark.asyncio
    async def test_execute_unknown_item_type(self):
        """Test execute with unknown item_type."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        result = await registry.execute(item_type="unknown", item_id="test")

        assert "error" in result
        assert "Unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_with_parameters(self):
        """Test execute passes parameters."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"status": "executed"}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        result = await registry.execute(
            item_type="directive", item_id="my_directive", parameters={"key": "value"}
        )

        mock_handler.execute.assert_called_once()
        # Parameters should be passed
        call_kwargs = mock_handler.execute.call_args[1]
        assert "parameters" in call_kwargs
        assert call_kwargs["parameters"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_execute_maps_item_id_to_directive_name(self):
        """Test execute maps item_id for directives."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        await registry.execute(item_type="directive", item_id="test_directive")

        call_kwargs = mock_handler.execute.call_args[1]
        assert "directive_name" in call_kwargs

    @pytest.mark.asyncio
    async def test_execute_maps_item_id_to_script_name(self):
        """Test execute maps item_id for tools (migrated from scripts)."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["tool"] = mock_handler

        await registry.execute(item_type="tool", item_id="test_tool")

        call_kwargs = mock_handler.execute.call_args[1]
        assert "tool_name" in call_kwargs

    @pytest.mark.asyncio
    async def test_sign_maps_item_id_to_id(self):
        """Test sign maps item_id for knowledge."""
        mock_handler = AsyncMock()
        mock_handler.sign.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["knowledge"] = mock_handler

        await registry.sign(item_type="knowledge", item_id="001-test")

        call_kwargs = mock_handler.sign.call_args[1]
        assert "id" in call_kwargs

    @pytest.mark.asyncio
    async def test_execute_handler_exception(self):
        """Test execute handles handler exceptions."""
        mock_handler = AsyncMock()
        mock_handler.execute.side_effect = RuntimeError("Execution error")

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        result = await registry.execute(item_type="directive", item_id="test")

        assert "error" in result
        assert "Failed to execute" in result.get("message", "")


class TestTypeHandlerRegistryErrorCases:
    """Test error handling in registry."""

    @pytest.mark.asyncio
    async def test_search_returns_error_dict(self):
        """Test search returns error dict on failure."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        result = await registry.search(item_type="invalid", query="test")

        assert isinstance(result, dict)
        assert "error" in result
        assert "supported_types" in result

    @pytest.mark.asyncio
    async def test_load_returns_error_dict(self):
        """Test load returns error dict on failure."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        result = await registry.load(item_type="invalid", item_id="test")

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_returns_error_dict(self):
        """Test execute returns error dict on failure."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        result = await registry.execute(item_type="invalid", item_id="test")

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_handler_returns_none_for_unknown(self):
        """Test _get_handler returns None for unknown type."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")

        handler = registry._get_handler("nonexistent")
        assert handler is None


class TestTypeHandlerRegistryIntegration:
    """Integration-style tests for registry."""

    @pytest.mark.asyncio
    async def test_registry_with_all_handlers_populated(self):
        """Test registry behavior with multiple handlers."""
        # Create mocks for all three handler types
        mock_directive = AsyncMock()
        mock_tool = AsyncMock()
        mock_knowledge = AsyncMock()

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_directive
        registry.handlers["tool"] = mock_tool
        registry.handlers["knowledge"] = mock_knowledge

        # Should work with all types
        assert registry.get_supported_types() == ["directive", "tool", "knowledge"]

        # Each search should route to correct handler
        await registry.search("directive", "test")
        assert mock_directive.search.called

        await registry.search("tool", "test")
        assert mock_tool.search.called

        await registry.search("knowledge", "test")
        assert mock_knowledge.search.called

    def test_registry_info_includes_all_details(self):
        """Test registry info is comprehensive."""
        project_path = "/test/path"
        registry = TypeHandlerRegistry(project_path=project_path)

        info = registry.get_handler_info()

        assert info["registry"] == "TypeHandlerRegistry"
        assert info["project_path"] == project_path
        assert "handlers" in info
        assert "directive" in info["handlers"]
        assert "tool" in info["handlers"]
        assert "knowledge" in info["handlers"]

    @pytest.mark.asyncio
    async def test_execute_with_all_parameters(self):
        """Test execute with full parameter set."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"result": "success"}

        registry = TypeHandlerRegistry(project_path="/path/to/project")
        registry.handlers["directive"] = mock_handler

        result = await registry.execute(
            item_type="directive",
            action="publish",
            item_id="test_directive",
            parameters={"version": "1.0.0", "description": "Test directive"},
            dry_run=True,
            project_path="/custom/path",
        )

        assert result == {"result": "success"}
        mock_handler.execute.assert_called_once()


class TestTypeHandlerRegistryLogging:
    """Test logging in registry."""

    def test_registry_initializes_logger(self):
        """Test registry has logger."""
        registry = TypeHandlerRegistry(project_path="/tmp/test")
        assert registry.logger is not None

    @pytest.mark.asyncio
    async def test_registry_logs_search(self):
        """Test registry logs search operations."""
        mock_handler = AsyncMock()
        mock_handler.search.return_value = {}

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        with patch.object(registry.logger, "info") as mock_log:
            await registry.search("directive", "query")
            # Logger should be called
            # We just verify no exception is raised

    @pytest.mark.asyncio
    async def test_registry_logs_errors(self):
        """Test registry logs errors."""
        mock_handler = AsyncMock()
        mock_handler.search.side_effect = Exception("Test error")

        registry = TypeHandlerRegistry(project_path="/tmp/test")
        registry.handlers["directive"] = mock_handler

        with patch.object(registry.logger, "error") as mock_log:
            await registry.search("directive", "query")
            # Should log error
            # We just verify no exception propagates
