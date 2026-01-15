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
        # Setup mock with proper structure
        execute_mock = create_mock_response(mock_directives_search_result["data"])
        directive_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
        # Search for single term that exists
        results = await directive_registry.search("bootstrap")
        
        # Verify
        assert len(results) > 0
        assert "bootstrap" in results[0].get("name", "").lower()
    
    @pytest.mark.asyncio
    async def test_directive_search_with_category_filter(self, directive_registry, mock_directives_search_result):
        """Test searching directives with category filter."""
        execute_mock = create_mock_response([mock_directives_search_result["data"][0]])
        
        chain = directive_registry.client.table.return_value.select.return_value
        chain.eq.return_value.limit.return_value.execute.return_value = execute_mock
        
        results = await directive_registry.search("bootstrap", category="setup")
        
        assert len(results) > 0
        assert results[0]["category"] == "setup"
    
    @pytest.mark.asyncio
    async def test_directive_search_with_tech_stack(self, directive_registry, mock_directives_search_result):
        """Test searching directives with tech stack filter."""
        execute_mock = create_mock_response(mock_directives_search_result["data"])
        
        directive_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
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


class TestScriptRegistryFlow:
    """Test complete script workflow."""
    
    @pytest.mark.asyncio
    async def test_script_search(self, script_registry, mock_scripts_search_result):
        """Test searching scripts."""
        execute_mock = create_mock_response(mock_scripts_search_result["data"])
        script_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
        results = await script_registry.search("scrape google maps")
        
        assert len(results) > 0
        assert any("google" in r.get("name", "").lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_script_search_multi_term(self, script_registry):
        """Test multi-term script search filters by multiple terms."""
        # Test data with all required terms ("scrape" and "data" both present)
        test_data = [
            {
                "id": "1",
                "name": "web_scraper",
                "category": "scraping",
                "description": "Scrape and extract data from websites",
                "is_official": False,
                "download_count": 300,
                "quality_score": 90.0,
                "tech_stack": ["Python"],
                "tags": ["scraping", "data"],
                "success_rate": 0.92,
                "estimated_cost_usd": 0.02,
                "latest_version": "2.0.0",
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-01-10T00:00:00Z",
            }
        ]
        execute_mock = create_mock_response(test_data)
        script_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
        # Both "scrape" and "data" should match
        results = await script_registry.search("scrape data")
        
        assert len(results) > 0
        combined = f"{results[0].get('name', '')} {results[0].get('description', '')}".lower()
        assert "scrape" in combined and "data" in combined
    
    @pytest.mark.asyncio
    async def test_script_get(self, script_registry):
        """Test getting a single script."""
        script_data = {
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
            "version": "2.1.0",
            "content": "#!/usr/bin/env python3\n# Script content",
            "changelog": "Bug fixes",
            "is_latest": True,
        }
        
        script_mock = create_mock_response(script_data)
        version_mock = create_mock_response([version_data])
        
        table_mock = script_registry.client.table.return_value
        table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = script_mock
        table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = version_mock
        
        result = await script_registry.get("google_maps_scraper")
        
        assert result is not None
        assert result["name"] == "google_maps_scraper"
        assert result["version"] == "2.1.0"
    
    @pytest.mark.asyncio
    async def test_script_list(self, script_registry, mock_scripts_search_result):
        """Test listing scripts."""
        execute_mock = create_mock_response(mock_scripts_search_result["data"])
        script_registry.client.table.return_value.select.return_value.limit.return_value.execute.return_value = execute_mock
        
        results = await script_registry.list()
        
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
        
        entry_mock = create_mock_response(entry_data)
        knowledge_registry.client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = entry_mock
        
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
    async def test_all_registries_configured(self, directive_registry, script_registry, knowledge_registry):
        """Test that all registries are configured."""
        # All should be configured with the test environment
        assert directive_registry.is_configured
        assert script_registry.is_configured
        assert knowledge_registry.is_configured
    
    @pytest.mark.asyncio
    async def test_query_parsing_consistent(self, directive_registry, script_registry, knowledge_registry):
        """Test that all registries parse queries consistently."""
        test_query = "multiple word query"
        
        terms_directive = directive_registry._parse_search_query(test_query)
        terms_script = script_registry._parse_search_query(test_query)
        terms_knowledge = knowledge_registry._parse_search_query(test_query)
        
        assert terms_directive == terms_script == terms_knowledge
        assert len(terms_directive) == 3  # "multiple", "word", "query"
    
    @pytest.mark.asyncio
    async def test_relevance_scoring_consistent(self, directive_registry, script_registry, knowledge_registry):
        """Test that relevance scoring is consistent across registries."""
        query_terms = ["email", "validation"]
        text1 = "Email Validation Service"
        text2 = "Validate email addresses"
        
        score_d = directive_registry._calculate_relevance_score(query_terms, text1, text2)
        score_s = script_registry._calculate_relevance_score(query_terms, text1, text2)
        score_k = knowledge_registry._calculate_relevance_score(query_terms, text1, text2)
        
        assert score_d == score_s == score_k


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
