"""
Tests for the unified search tool across directives, scripts, and knowledge.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from kiwi_mcp.tools.search import SearchTool


class TestSearchTool:
    """Test cases for SearchTool."""

    @pytest.fixture
    def project_path(self, tmp_path):
        """Create a test project structure."""
        project = tmp_path / "test_project"
        project.mkdir()

        # Create .ai directory structure
        ai_dir = project / ".ai"
        ai_dir.mkdir()

        # Create directives directory
        directives_dir = ai_dir / "directives"
        directives_dir.mkdir()

        # Create tools directory
        tools_dir = ai_dir / "tools"
        tools_dir.mkdir()

        # Create knowledge directory
        knowledge_dir = ai_dir / "knowledge"
        knowledge_dir.mkdir()

        return str(project)

    @pytest.fixture
    def search_tool(self):
        """Create a SearchTool instance."""
        return SearchTool()

    @pytest.mark.asyncio
    async def test_search_directive_type(self, search_tool, project_path):
        """Test searching for directives by type."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "test_directive",
                            "type": "directive",
                            "title": "Test Directive",
                            "score": 0.95,
                        }
                    ],
                    "total": 1,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {
                    "item_type": "directive",
                    "query": "test directive",
                    "project_path": project_path,
                    "limit": 10,
                }
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions
            assert result_data is not None
            assert "results" in result_data or "items" in result_data
            assert result_data.get("search_type") == "keyword"
            mock_handler.assert_called_once_with(project_path=project_path)

    @pytest.mark.asyncio
    async def test_search_tool_type(self, search_tool, project_path):
        """Test searching for tools by type."""
        with patch("kiwi_mcp.handlers.tool.handler.ToolHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {"id": "test_tool", "type": "tool", "title": "Test Tool", "score": 0.88}
                    ],
                    "total": 1,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {
                    "item_type": "tool",
                    "query": "test tool",
                    "project_path": project_path,
                    "limit": 10,
                }
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions
            assert result_data is not None
            assert "results" in result_data or "items" in result_data
            assert result_data.get("search_type") == "keyword"
            mock_handler.assert_called_once_with(project_path=project_path)

    @pytest.mark.asyncio
    async def test_search_knowledge_type(self, search_tool, project_path):
        """Test searching for knowledge entries by type."""
        with patch("kiwi_mcp.handlers.knowledge.handler.KnowledgeHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "kb-001",
                            "type": "knowledge",
                            "title": "Test Knowledge",
                            "score": 0.92,
                        }
                    ],
                    "total": 1,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {
                    "item_type": "knowledge",
                    "query": "test knowledge",
                    "project_path": project_path,
                    "limit": 10,
                }
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions
            assert result_data is not None
            assert "results" in result_data or "items" in result_data
            assert result_data.get("search_type") == "keyword"
            mock_handler.assert_called_once_with(project_path=project_path)

    @pytest.mark.asyncio
    async def test_search_indicates_search_type_keyword(self, search_tool, project_path):
        """Test that search indicates keyword search type when vector search unavailable."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "test_directive",
                            "type": "directive",
                            "title": "Test Directive",
                            "score": 0.95,
                        }
                    ],
                    "total": 1,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {"item_type": "directive", "query": "test", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should indicate keyword search
            assert result_data.get("search_type") == "keyword"
            assert result_data.get("quality") == "good"

    @pytest.mark.asyncio
    async def test_search_indicates_search_type_hybrid(self, search_tool, project_path):
        """Test that search indicates hybrid/vector search type when available."""
        # Create vector directory to simulate vector search availability
        vector_path = Path(project_path) / ".ai" / "vector"
        vector_path.mkdir(parents=True, exist_ok=True)

        with patch.object(search_tool, "_vector_search", new_callable=AsyncMock) as mock_vector:
            mock_vector.return_value = json.dumps(
                {
                    "items": [
                        {
                            "id": "test_directive",
                            "type": "directive",
                            "score": 0.95,
                            "preview": "Test content",
                            "metadata": {},
                            "source": "project",
                        }
                    ],
                    "total": 1,
                    "query": "test",
                    "search_type": "vector_hybrid",
                    "source": "local",
                }
            )

            # Execute search
            result = await search_tool.execute(
                {"item_type": "directive", "query": "test", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should indicate vector/hybrid search
            assert result_data.get("search_type") == "vector_hybrid"

    @pytest.mark.asyncio
    async def test_search_fallback_when_no_vector(self, search_tool, project_path):
        """Test that search falls back to keyword search when vector search unavailable."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "test_directive",
                            "type": "directive",
                            "title": "Test Directive",
                            "score": 0.95,
                        }
                    ],
                    "total": 1,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Verify vector search is not available
            assert not search_tool._has_vector_search(project_path)

            # Execute search
            result = await search_tool.execute(
                {"item_type": "directive", "query": "test", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should use keyword search as fallback
            assert result_data.get("search_type") == "keyword"
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_project_path(self, search_tool, project_path):
        """Test that search requires and uses project_path parameter."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={"results": [], "total": 0, "query": "test"}
            )
            mock_handler.return_value = mock_instance

            # Execute search with project_path
            result = await search_tool.execute(
                {"item_type": "directive", "query": "test", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should succeed with project_path
            assert result_data is not None
            mock_handler.assert_called_once_with(project_path=project_path)

    @pytest.mark.asyncio
    async def test_search_missing_project_path(self, search_tool):
        """Test that search fails gracefully when project_path is missing."""
        # Execute search without project_path
        result = await search_tool.execute({"item_type": "directive", "query": "test"})

        # Parse result
        result_data = json.loads(result)

        # Assertions - should indicate error
        assert "error" in result_data
        assert (
            "project_path" in result_data.get("error", "").lower()
            or "project_path" in result_data.get("message", "").lower()
        )

    @pytest.mark.asyncio
    async def test_search_missing_query(self, search_tool, project_path):
        """Test that search fails gracefully when query is missing."""
        # Execute search without query
        result = await search_tool.execute({"item_type": "directive", "project_path": project_path})

        # Parse result
        result_data = json.loads(result)

        # Assertions - should indicate error
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_search_missing_item_type(self, search_tool, project_path):
        """Test that search fails gracefully when item_type is missing."""
        # Execute search without item_type
        result = await search_tool.execute({"query": "test", "project_path": project_path})

        # Parse result
        result_data = json.loads(result)

        # Assertions - should indicate error
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_search_invalid_item_type(self, search_tool, project_path):
        """Test that search fails gracefully with invalid item_type."""
        # Execute search with invalid item_type
        result = await search_tool.execute(
            {"item_type": "invalid_type", "query": "test", "project_path": project_path}
        )

        # Parse result
        result_data = json.loads(result)

        # Assertions - should indicate error
        assert "error" in result_data
        assert "Unknown item_type" in result_data.get("error", "")

    @pytest.mark.asyncio
    async def test_search_with_limit(self, search_tool, project_path):
        """Test that search respects limit parameter."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {"id": f"directive_{i}", "type": "directive", "score": 0.9 - i * 0.05}
                        for i in range(5)
                    ],
                    "total": 5,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Execute search with limit
            result = await search_tool.execute(
                {
                    "item_type": "directive",
                    "query": "test",
                    "project_path": project_path,
                    "limit": 5,
                }
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should pass limit to handler
            assert result_data is not None
            mock_instance.search.assert_called_once_with("test", source="local", limit=5)

    @pytest.mark.asyncio
    async def test_search_with_source(self, search_tool, project_path):
        """Test that search respects source parameter."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={"results": [], "total": 0, "query": "test"}
            )
            mock_handler.return_value = mock_instance

            # Execute search with source
            result = await search_tool.execute(
                {
                    "item_type": "directive",
                    "query": "test",
                    "project_path": project_path,
                    "source": "local",
                }
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should pass source to handler
            assert result_data is not None
            mock_instance.search.assert_called_once_with("test", source="local", limit=10)

    def test_search_tool_schema(self, search_tool):
        """Test that search tool has correct schema."""
        schema = search_tool.schema

        # Assertions
        assert schema.name == "search"
        assert "item_type" in schema.inputSchema["properties"]
        assert "query" in schema.inputSchema["properties"]
        assert "project_path" in schema.inputSchema["properties"]
        assert "limit" in schema.inputSchema["properties"]
        assert "source" in schema.inputSchema["properties"]

        # Check required fields
        assert "item_type" in schema.inputSchema["required"]
        assert "query" in schema.inputSchema["required"]
        assert "project_path" in schema.inputSchema["required"]

    def test_search_tool_schema_enums(self, search_tool):
        """Test that search tool schema has correct enum values."""
        schema = search_tool.schema

        # Check item_type enum
        item_type_enum = schema.inputSchema["properties"]["item_type"]["enum"]
        assert "directive" in item_type_enum
        assert "tool" in item_type_enum
        assert "knowledge" in item_type_enum

        # Check source enum
        source_enum = schema.inputSchema["properties"]["source"]["enum"]
        assert "local" in source_enum

    def test_has_vector_search_when_exists(self, search_tool, project_path):
        """Test _has_vector_search returns True when vector directory exists."""
        # Create vector directory
        vector_path = Path(project_path) / ".ai" / "vector"
        vector_path.mkdir(parents=True, exist_ok=True)

        # Assertions
        assert search_tool._has_vector_search(project_path) is True

    def test_has_vector_search_when_not_exists(self, search_tool, project_path):
        """Test _has_vector_search returns False when vector directory doesn't exist."""
        # Assertions - vector directory not created
        assert search_tool._has_vector_search(project_path) is False

    def test_has_vector_search_with_invalid_path(self, search_tool):
        """Test _has_vector_search handles invalid paths gracefully."""
        # Assertions - should return False for invalid path
        assert search_tool._has_vector_search("/nonexistent/path") is False

    @pytest.mark.asyncio
    async def test_search_quality_indicator(self, search_tool, project_path):
        """Test that search results include quality indicator."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "test_directive",
                            "type": "directive",
                            "title": "Test Directive",
                            "score": 0.95,
                        }
                    ],
                    "total": 1,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {"item_type": "directive", "query": "test", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should include quality indicator
            assert result_data.get("quality") == "good"
            if "results" in result_data:
                for item in result_data["results"]:
                    assert item.get("quality") == "good"

    @pytest.mark.asyncio
    async def test_search_handler_exception_handling(self, search_tool, project_path):
        """Test that search handles handler exceptions gracefully."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler to raise exception
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(side_effect=Exception("Handler error"))
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {"item_type": "directive", "query": "test", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions - should handle error gracefully
            assert "error" in result_data

    @pytest.mark.asyncio
    async def test_search_multiple_results(self, search_tool, project_path):
        """Test search with multiple results."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler with multiple results
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": f"directive_{i}",
                            "type": "directive",
                            "title": f"Test Directive {i}",
                            "score": 0.95 - i * 0.05,
                        }
                        for i in range(3)
                    ],
                    "total": 3,
                    "query": "test",
                }
            )
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {"item_type": "directive", "query": "test", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions
            assert result_data.get("total") == 3
            assert len(result_data.get("results", [])) == 3

    @pytest.mark.asyncio
    async def test_search_empty_results(self, search_tool, project_path):
        """Test search with no results."""
        with patch("kiwi_mcp.handlers.directive.handler.DirectiveHandler") as mock_handler:
            # Setup mock handler with no results
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(
                return_value={"results": [], "total": 0, "query": "nonexistent"}
            )
            mock_handler.return_value = mock_instance

            # Execute search
            result = await search_tool.execute(
                {"item_type": "directive", "query": "nonexistent", "project_path": project_path}
            )

            # Parse result
            result_data = json.loads(result)

            # Assertions
            assert result_data.get("total") == 0
            assert len(result_data.get("results", [])) == 0
