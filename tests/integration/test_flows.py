"""
Integration tests for registry API flows.

Tests search, load, and execute operations across all three registry types.
"""

import pytest
from unittest.mock import MagicMock


def create_mock_response(data):
    """Helper to create a mock response with .data attribute."""
    mock = MagicMock()
    mock.data = data
    return mock


class TestDirectiveRegistryFlow:
    """Test complete directive workflow."""
    
    @pytest.mark.asyncio
    async def test_directive_search(self, directive_registry, mock_directives_search_result):
        """Test searching directives."""
        # Setup mock with proper structure - account for .or_() chaining
        execute_mock = create_mock_response(mock_directives_search_result["data"])
        # Mock the chain: table().select().or_().limit().execute()
        table_mock = directive_registry.client.table.return_value
        select_mock = table_mock.select.return_value
        or_mock = select_mock.or_.return_value
        limit_mock = or_mock.limit.return_value
        limit_mock.execute.return_value = execute_mock
        
        # Search for single term that exists
        results = await directive_registry.search("bootstrap")
        
        # Verify
        assert len(results) > 0
        assert "bootstrap" in results[0].get("name", "").lower()
    
    @pytest.mark.asyncio
    async def test_directive_search_with_category_filter(self, directive_registry, mock_directives_search_result):
        """Test searching directives with category filter."""
        execute_mock = create_mock_response([mock_directives_search_result["data"][0]])
        
        # Mock the chain: table().select().eq().or_().limit().execute()
        table_mock = directive_registry.client.table.return_value
        select_mock = table_mock.select.return_value
        eq_mock = select_mock.eq.return_value
        or_mock = eq_mock.or_.return_value
        limit_mock = or_mock.limit.return_value
        limit_mock.execute.return_value = execute_mock
        
        results = await directive_registry.search("bootstrap", category="setup")
        
        assert len(results) > 0
        assert results[0]["category"] == "setup"
    
    @pytest.mark.asyncio
    async def test_directive_search_with_tech_stack(self, directive_registry, mock_directives_search_result):
        """Test searching directives with tech stack filter."""
        execute_mock = create_mock_response(mock_directives_search_result["data"])
        # Mock the chain: table().select().or_().limit().execute()
        table_mock = directive_registry.client.table.return_value
        select_mock = table_mock.select.return_value
        or_mock = select_mock.or_.return_value
        limit_mock = or_mock.limit.return_value
        limit_mock.execute.return_value = execute_mock
        
        results = await directive_registry.search("bootstrap", tech_stack=["Python"])
        
        # Should include directives with Python in tech stack
        assert any("Python" in r.get("tech_stack", []) for r in results)
    
    @pytest.mark.asyncio
    async def test_directive_get(self, directive_registry):
        """Test getting a single directive."""
        # Setup mock
        directive_data = {
            "id": "1",
            "name": "bootstrap",
            "category": "setup",
            "description": "Bootstrap directive",
            "is_official": True,
            "download_count": 150,
            "quality_score": 95.0,
            "tech_stack": ["Python"],
        }
        version_data = {
            "version": "1.0.0",
            "content": "# Bootstrap Directive\nContent here",
            "changelog": "Initial version",
            "is_latest": True,
        }
        
        # Mock single() for directive
        directive_mock = create_mock_response(directive_data)
        version_mock = create_mock_response([version_data])
        
        table_mock = directive_registry.client.table.return_value
        table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = directive_mock
        table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = version_mock
        
        result = await directive_registry.get("bootstrap")
        
        assert result is not None
        assert result["name"] == "bootstrap"
        assert result["content"] == "# Bootstrap Directive\nContent here"
    
    @pytest.mark.asyncio
    async def test_directive_list(self, directive_registry, mock_directives_search_result):
        """Test listing directives."""
        execute_mock = create_mock_response(mock_directives_search_result["data"])
        directive_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
        results = await directive_registry.list()
        
        assert len(results) > 0
        assert "name" in results[0]
        assert "category" in results[0]


class TestToolRegistryFlow:
    """Test complete tool workflow."""
    
    @pytest.mark.asyncio
    async def test_tool_search(self, tool_registry, mock_tools_search_result):
        """Test searching tools."""
        # Tool registry uses RPC call, not table queries
        rpc_mock = MagicMock()
        rpc_result = create_mock_response([
            {
                "id": "1",
                "tool_id": "google_maps_scraper",
                "name": "google_maps_scraper",
                "tool_type": "script",
                "category": "scraping",
                "description": "Scrape business locations from Google Maps",
                "executor_id": "python_runtime",
                "latest_version": "2.1.0",
                "rank": 0.95,
            }
        ])
        rpc_mock.execute.return_value = rpc_result
        tool_registry.client.rpc.return_value = rpc_mock
        
        results = await tool_registry.search("scrape google maps")
        
        assert len(results) > 0
        assert any("google" in r.get("name", "").lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_tool_search_multi_term(self, tool_registry):
        """Test multi-term tool search filters by multiple terms."""
        # Tool registry uses RPC call, not table queries
        rpc_mock = MagicMock()
        rpc_result = create_mock_response([
            {
                "id": "1",
                "tool_id": "web_scraper",
                "name": "web_scraper",
                "tool_type": "script",
                "category": "scraping",
                "description": "Scrape and extract data from websites",
                "executor_id": "python_runtime",
                "latest_version": "2.0.0",
                "rank": 0.90,
            }
        ])
        rpc_mock.execute.return_value = rpc_result
        tool_registry.client.rpc.return_value = rpc_mock
        
        # Both "scrape" and "data" should match
        results = await tool_registry.search("scrape data")
        
        assert len(results) > 0
        combined = f"{results[0].get('name', '')} {results[0].get('description', '')}".lower()
        assert "scrape" in combined and "data" in combined
    
    @pytest.mark.asyncio
    async def test_tool_get(self, tool_registry):
        """Test getting a single tool."""
        tool_data = {
            "id": "1",
            "name": "google_maps_scraper",
            "category": "scraping",
            "description": "Scrape Google Maps",
            "is_official": True,
            "download_count": 500,
            "quality_score": 98.0,
            "tech_stack": ["Python", "Selenium"],
            "tags": ["scraping"],
        }
        version_data = {
            "id": "version-uuid-1",  # Need id for tool_version_id lookup
            "version": "2.1.0",
            "content": "#!/usr/bin/env python3\n# Tool content",
            "changelog": "Bug fixes",
            "is_latest": True,
        }
        
        # Mock the tool query (first call to table("tools"))
        tool_mock = create_mock_response(tool_data)
        # Mock the version query (second call to table("tool_versions"))
        version_mock = create_mock_response([version_data])
        # Mock the files query (third call to table("tool_version_files"))
        files_mock = create_mock_response([])
        
        # Create separate query builders for each table with proper chaining
        # Tools table: table("tools").select(...).eq(...).single().execute()
        tools_table = MagicMock()
        tools_result = create_mock_response(tool_data)
        tools_table.select.return_value.eq.return_value.single.return_value.execute.return_value = tools_result
        
        # Versions table: table("tool_versions").select(...).eq(...).order(...).eq(...).limit(...).execute()
        versions_table = MagicMock()
        versions_result = create_mock_response([version_data])
        versions_table.select.return_value.eq.return_value.order.return_value.eq.return_value.limit.return_value.execute.return_value = versions_result
        
        # Files table: table("tool_version_files").select(...).eq(...).execute()
        files_table = MagicMock()
        files_result = create_mock_response([])
        files_table.select.return_value.eq.return_value.execute.return_value = files_result
        
        # Make table() return different mocks for different calls
        call_count = [0]
        def table_side_effect(table_name):
            call_count[0] += 1
            if call_count[0] == 1:  # First call: tools
                return tools_table
            elif call_count[0] == 2:  # Second call: tool_versions
                return versions_table
            elif call_count[0] == 3:  # Third call: tool_version_files
                return files_table
            return MagicMock()
        
        tool_registry.client.table.side_effect = table_side_effect
        
        result = await tool_registry.get("google_maps_scraper")
        
        assert result is not None
        assert result.get("name") == "google_maps_scraper" or result.get("tool_id") == "google_maps_scraper"
        assert result.get("version") == "2.1.0"
    
    @pytest.mark.asyncio
    async def test_tool_list(self, tool_registry, mock_tools_search_result):
        """Test listing tools."""
        execute_mock = create_mock_response(mock_tools_search_result["data"])
        tool_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
        results = await tool_registry.list()
        
        assert len(results) > 0
        assert "name" in results[0]
        assert "category" in results[0]


class TestKnowledgeRegistryFlow:
    """Test complete knowledge workflow."""
    
    @pytest.mark.asyncio
    async def test_knowledge_search(self, knowledge_registry, mock_knowledge_search_result):
        """Test searching knowledge entries."""
        rpc_mock = create_mock_response(mock_knowledge_search_result["data"])
        knowledge_registry.client.rpc.return_value.execute.return_value = rpc_mock
        
        results = await knowledge_registry.search("email deliverability")
        
        assert len(results) > 0
        assert any("email" in r.get("title", "").lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_knowledge_search_with_filters(self, knowledge_registry, mock_knowledge_search_result):
        """Test searching knowledge with entry_type filter."""
        rpc_mock = create_mock_response(mock_knowledge_search_result["data"])
        knowledge_registry.client.rpc.return_value.execute.return_value = rpc_mock
        
        results = await knowledge_registry.search(
            "email",
            entry_type="pattern",
            tags=["email"]
        )
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_knowledge_get(self, knowledge_registry):
        """Test getting a single knowledge entry."""
        entry_data = {
            "zettel_id": "001-email-deliverability",
            "title": "Email Deliverability Best Practices",
            "content": "# Email Deliverability\n\nContent here...",
            "entry_type": "pattern",
            "category": "email-infrastructure",
            "tags": ["email", "smtp"],
            "version": "1.0.0",
        }
        
        # Mock rpc() call (primary method)
        entry_mock = create_mock_response([entry_data])
        rpc_mock = knowledge_registry.client.rpc.return_value
        rpc_mock.execute.return_value = entry_mock
        
        result = await knowledge_registry.get("001-email-deliverability")
        
        assert result is not None
        assert result["zettel_id"] == "001-email-deliverability"
        assert result["entry_type"] == "pattern"
    
    @pytest.mark.asyncio
    async def test_knowledge_publish(self, knowledge_registry):
        """Test publishing a knowledge entry."""
        # Mock get for existing check
        existing_mock = create_mock_response(None)
        insert_mock = create_mock_response([{"id": "new-entry"}])
        
        table_mock = knowledge_registry.client.table.return_value
        table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_mock
        table_mock.insert.return_value.execute.return_value = insert_mock
        
        result = await knowledge_registry.publish(
            zettel_id="003-new-entry",
            title="New Entry",
            content="# New Entry\n\nContent",
            entry_type="learning",
            category="testing",
            tags=["testing", "new"]
        )
        
        assert result["status"] == "success"
        assert result["zettel_id"] == "003-new-entry"
    
    @pytest.mark.asyncio
    async def test_knowledge_list(self, knowledge_registry, mock_knowledge_search_result):
        """Test listing knowledge entries."""
        execute_mock = create_mock_response(mock_knowledge_search_result["data"])
        knowledge_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
        results = await knowledge_registry.list()
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_knowledge_get_relationships(self, knowledge_registry):
        """Test getting relationships for an entry."""
        outgoing_data = [
            {
                "from_zettel_id": "001",
                "to_zettel_id": "002",
                "relationship_type": "references"
            }
        ]
        incoming_data = [
            {
                "from_zettel_id": "003",
                "to_zettel_id": "001",
                "relationship_type": "references"
            }
        ]
        
        outgoing_mock = create_mock_response(outgoing_data)
        incoming_mock = create_mock_response(incoming_data)
        
        table_mock = knowledge_registry.client.table.return_value
        select_mock = MagicMock()
        eq_mock_1 = MagicMock()
        eq_mock_2 = MagicMock()
        
        eq_mock_1.execute.return_value = outgoing_mock
        eq_mock_2.execute.return_value = incoming_mock
        
        select_mock.eq.side_effect = [eq_mock_1, eq_mock_2]
        table_mock.select.return_value = select_mock
        
        result = await knowledge_registry.get_relationships("001")
        
        assert len(result["outgoing"]) > 0
        assert len(result["incoming"]) > 0


class TestCrossRegistryIntegration:
    """Test interactions across all three registries."""
    
    @pytest.mark.asyncio
    async def test_all_registries_configured(self, directive_registry, tool_registry, knowledge_registry):
        """Test that all registries are configured."""
        # All should be configured with the test environment
        assert directive_registry.is_configured
        assert tool_registry.is_configured
        assert knowledge_registry.is_configured
    
    @pytest.mark.asyncio
    async def test_query_parsing_consistent(self, directive_registry, tool_registry, knowledge_registry):
        """Test that all registries parse queries consistently."""
        test_query = "multiple word query"
        
        terms_directive = directive_registry._parse_search_query(test_query)
        terms_tool = tool_registry._parse_search_query(test_query)
        terms_knowledge = knowledge_registry._parse_search_query(test_query)
        
        assert terms_directive == terms_tool == terms_knowledge
        assert len(terms_directive) == 3  # "multiple", "word", "query"
    
    @pytest.mark.asyncio
    async def test_relevance_scoring_consistent(self, directive_registry, tool_registry, knowledge_registry):
        """Test that relevance scoring is consistent across registries."""
        query_terms = ["email", "validation"]
        text1 = "Email Validation Service"
        text2 = "Validate email addresses"
        
        score_d = directive_registry._calculate_relevance_score(query_terms, text1, text2)
        score_t = tool_registry._calculate_relevance_score(query_terms, text1, text2)
        score_k = knowledge_registry._calculate_relevance_score(query_terms, text1, text2)
        
        assert score_d == score_t == score_k


class TestErrorHandling:
    """Test error handling across registries."""
    
    @pytest.mark.asyncio
    async def test_search_handles_errors(self, directive_registry):
        """Test that search handles errors gracefully."""
        # Mock client.table to raise exception
        directive_registry.client.table.side_effect = Exception("Connection error")
        
        results = await directive_registry.search("test")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_get_handles_errors(self, directive_registry):
        """Test that get handles errors gracefully."""
        directive_registry.client.table.side_effect = Exception("Connection error")
        
        result = await directive_registry.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_publish_handles_errors(self, directive_registry):
        """Test that publish returns error dict on failure."""
        directive_registry.client.table.side_effect = Exception("Connection error")
        
        result = await directive_registry.publish(
            name="test",
            version="1.0.0",
            content="test",
            category="test"
        )
        
        assert "error" in result
