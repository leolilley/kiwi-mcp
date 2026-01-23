"""
Tests for ChainResolver in PrimitiveExecutor.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from kiwi_mcp.primitives.executor import ChainResolver


class TestChainResolver:
    """Test ChainResolver functionality."""

    @pytest.fixture
    def mock_registry(self):
        """Mock ToolRegistry."""
        registry = Mock()
        registry.resolve_chain = AsyncMock()
        registry.resolve_chains_batch = AsyncMock()
        return registry

    @pytest.fixture
    def resolver(self, mock_registry):
        """ChainResolver instance with mock registry."""
        return ChainResolver(mock_registry)

    @pytest.mark.asyncio
    async def test_resolve_single_chain(self, resolver, mock_registry):
        """Test resolving a single chain."""
        # Setup
        tool_id = "enrich_emails"
        expected_chain = [
            {
                "tool_id": "enrich_emails",
                "manifest": {"config": {"entrypoint": "main.py", "requires": ["httpx"]}},
            },
            {
                "tool_id": "python_runtime",
                "manifest": {"config": {"command": "python3", "venv": {"enabled": True}}},
            },
            {
                "tool_id": "subprocess",
                "manifest": {"config": {"timeout": 300, "capture_output": True}},
            },
        ]
        mock_registry.resolve_chain.return_value = expected_chain

        # Execute
        result = await resolver.resolve(tool_id)

        # Assert
        assert result == expected_chain
        mock_registry.resolve_chain.assert_called_once_with(tool_id)

        # Verify caching
        result2 = await resolver.resolve(tool_id)
        assert result2 == expected_chain
        # Should still only be called once due to caching
        assert mock_registry.resolve_chain.call_count == 1

    @pytest.mark.asyncio
    async def test_resolve_batch(self, resolver, mock_registry):
        """Test batch resolving multiple chains."""
        # Setup
        tool_ids = ["enrich_emails", "scrape_maps"]
        batch_results = {
            "enrich_emails": [{"tool_id": "enrich_emails"}, {"tool_id": "subprocess"}],
            "scrape_maps": [{"tool_id": "scrape_maps"}, {"tool_id": "subprocess"}],
        }
        mock_registry.resolve_chains_batch.return_value = batch_results

        # Execute
        result = await resolver.resolve_batch(tool_ids)

        # Assert
        assert result == batch_results
        mock_registry.resolve_chains_batch.assert_called_once_with(tool_ids)

    @pytest.mark.asyncio
    async def test_resolve_batch_with_cache(self, resolver, mock_registry):
        """Test batch resolve with some items already cached."""
        # Setup - cache one item first
        cached_chain = [{"tool_id": "enrich_emails"}]
        resolver._chain_cache["enrich_emails"] = cached_chain

        tool_ids = ["enrich_emails", "scrape_maps"]
        batch_results = {"scrape_maps": [{"tool_id": "scrape_maps"}, {"tool_id": "subprocess"}]}
        mock_registry.resolve_chains_batch.return_value = batch_results

        # Execute
        result = await resolver.resolve_batch(tool_ids)

        # Assert
        expected = {"enrich_emails": cached_chain, "scrape_maps": batch_results["scrape_maps"]}
        assert result == expected
        # Should only request uncached items
        mock_registry.resolve_chains_batch.assert_called_once_with(["scrape_maps"])

    def test_merge_configs_child_overrides(self, resolver):
        """Test config merging where child overrides parent."""
        chain = [
            {
                "tool_id": "enrich_emails",
                "manifest": {
                    "config": {"entrypoint": "main.py", "requires": ["httpx"], "timeout": 120}
                },
            },
            {
                "tool_id": "python_runtime",
                "manifest": {
                    "config": {
                        "command": "python3",
                        "venv": {"enabled": True, "path": "/tmp/venv"},
                        "timeout": 60,  # Should be overridden by child
                    }
                },
            },
            {
                "tool_id": "subprocess",
                "manifest": {
                    "config": {
                        "timeout": 300,  # Should be overridden by child
                        "capture_output": True,
                    }
                },
            },
        ]

        result = resolver.merge_configs(chain)

        expected = {
            "entrypoint": "main.py",
            "requires": ["httpx"],
            "timeout": 120,  # From leaf (enrich_emails)
            "command": "python3",
            "venv": {"enabled": True, "path": "/tmp/venv"},
            "capture_output": True,
        }
        assert result == expected

    def test_deep_merge(self, resolver):
        """Test deep merging of nested dictionaries."""
        base = {
            "venv": {"enabled": False, "path": "/default"},
            "timeout": 300,
            "env": {"PATH": "/usr/bin"},
        }
        override = {
            "venv": {"enabled": True, "requirements": ["httpx"]},
            "timeout": 120,
            "env": {"PYTHONPATH": "/app"},
        }

        result = resolver._deep_merge(base, override)

        expected = {
            "venv": {
                "enabled": True,  # Overridden
                "path": "/default",  # Preserved from base
                "requirements": ["httpx"],  # Added from override
            },
            "timeout": 120,  # Overridden
            "env": {
                "PATH": "/usr/bin",  # Preserved from base
                "PYTHONPATH": "/app",  # Added from override
            },
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_cache_hit(self, resolver, mock_registry):
        """Test that cache prevents duplicate registry calls."""
        # Setup cache
        tool_id = "test_tool"
        cached_chain = [{"tool_id": "test_tool"}]
        resolver._chain_cache[tool_id] = cached_chain

        # Execute
        result = await resolver.resolve(tool_id)

        # Assert
        assert result == cached_chain
        # Registry should not be called
        mock_registry.resolve_chain.assert_not_called()

    def test_merge_configs_empty_chain(self, resolver):
        """Test merging with empty chain."""
        result = resolver.merge_configs([])
        assert result == {}

    def test_merge_configs_no_manifest(self, resolver):
        """Test merging when items have no manifest."""
        chain = [
            {"tool_id": "tool1"},  # No manifest
            {"tool_id": "tool2", "manifest": {}},  # Empty manifest
            {"tool_id": "tool3", "manifest": {"config": {"key": "value"}}},
        ]

        result = resolver.merge_configs(chain)
        assert result == {"key": "value"}
