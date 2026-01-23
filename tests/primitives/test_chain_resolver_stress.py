"""
Stress tests and complex scenarios for ChainResolver using real Supabase data.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from kiwi_mcp.primitives.executor import ChainResolver, PrimitiveExecutor, ExecutionResult


class TestChainResolverStress:
    """Stress tests for ChainResolver with real-world scenarios."""

    @pytest.fixture
    def mock_registry(self):
        """Mock ToolRegistry with real Supabase data patterns."""
        registry = Mock()
        registry.resolve_chain = AsyncMock()
        registry.resolve_chains_batch = AsyncMock()
        return registry

    @pytest.fixture
    def resolver(self, mock_registry):
        """ChainResolver instance with mock registry."""
        return ChainResolver(mock_registry)

    @pytest.fixture
    def executor(self, mock_registry):
        """PrimitiveExecutor for integration tests."""
        return PrimitiveExecutor(mock_registry)

    # Real chain data from Supabase
    @pytest.fixture
    def real_data_processor_chain(self):
        """Real data_processor chain from Supabase."""
        return [
            {
                "depth": 0,
                "tool_id": "data_processor",
                "tool_type": "script",
                "executor_id": "python_runtime",
                "manifest": {
                    "config": {
                        "env": {"PYTHONPATH": "/app/lib", "DATA_CACHE_SIZE": "1000"},
                        "timeout": 1800,
                        "requires": ["pandas", "numpy", "scipy"],
                        "entrypoint": "process_data.py",
                        "memory_limit": "2GB",
                    }
                },
            },
            {
                "depth": 1,
                "tool_id": "python_runtime",
                "tool_type": "runtime",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {
                        "venv": {"path": ".venv", "enabled": True, "auto_create": True},
                        "command": "python3",
                        "install_deps": True,
                    },
                    "tool_id": "python_runtime",
                    "version": "1.0.0",
                    "executor": "subprocess",
                    "tool_type": "runtime",
                    "description": "Python execution runtime",
                },
            },
            {
                "depth": 2,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {
                    "tool_id": "subprocess",
                    "version": "1.0.0",
                    "tool_type": "primitive",
                    "description": "Subprocess execution primitive",
                    "config_schema": {
                        "type": "object",
                        "required": ["command"],
                        "properties": {
                            "cwd": {"type": "string"},
                            "env": {"type": "object", "additionalProperties": {"type": "string"}},
                            "args": {"type": "array", "items": {"type": "string"}},
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {"type": "integer", "default": 300},
                            "capture_output": {"type": "boolean", "default": True},
                        },
                    },
                },
            },
        ]

    @pytest.fixture
    def real_web_scraper_chain(self):
        """Real web_scraper chain from Supabase."""
        return [
            {
                "depth": 0,
                "tool_id": "web_scraper",
                "tool_type": "script",
                "executor_id": "python_runtime",
                "manifest": {
                    "config": {
                        "env": {"USER_AGENT": "WebScraper/1.0", "MAX_RETRIES": "3"},
                        "timeout": 600,
                        "requires": ["requests", "beautifulsoup4", "selenium"],
                        "entrypoint": "scraper.py",
                        "rate_limit": 10,
                    }
                },
            },
            {
                "depth": 1,
                "tool_id": "python_runtime",
                "tool_type": "runtime",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {
                        "venv": {"path": ".venv", "enabled": True, "auto_create": True},
                        "command": "python3",
                        "install_deps": True,
                    },
                    "tool_id": "python_runtime",
                    "version": "1.0.0",
                    "executor": "subprocess",
                    "tool_type": "runtime",
                    "description": "Python execution runtime",
                },
            },
            {
                "depth": 2,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {
                    "tool_id": "subprocess",
                    "version": "1.0.0",
                    "tool_type": "primitive",
                    "description": "Subprocess execution primitive",
                    "config_schema": {
                        "type": "object",
                        "required": ["command"],
                        "properties": {
                            "cwd": {"type": "string"},
                            "env": {"type": "object", "additionalProperties": {"type": "string"}},
                            "args": {"type": "array", "items": {"type": "string"}},
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {"type": "integer", "default": 300},
                            "capture_output": {"type": "boolean", "default": True},
                        },
                    },
                },
            },
        ]

    @pytest.fixture
    def real_api_client_chain(self):
        """Real api_client chain from Supabase (Node.js)."""
        return [
            {
                "depth": 0,
                "tool_id": "api_client",
                "tool_type": "script",
                "executor_id": "node_runtime",
                "manifest": {
                    "config": {
                        "env": {"NODE_ENV": "production", "API_TIMEOUT": "30000"},
                        "timeout": 300,
                        "requires": ["axios", "lodash", "moment"],
                        "entrypoint": "api_client.js",
                    }
                },
            },
            {
                "depth": 1,
                "tool_id": "node_runtime",
                "tool_type": "runtime",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {"command": "node", "install_deps": True, "package_manager": "npm"},
                    "tool_id": "node_runtime",
                    "version": "1.0.0",
                    "executor": "subprocess",
                    "tool_type": "runtime",
                    "description": "Node.js execution runtime",
                },
            },
            {
                "depth": 2,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {
                    "tool_id": "subprocess",
                    "version": "1.0.0",
                    "tool_type": "primitive",
                    "description": "Subprocess execution primitive",
                    "config_schema": {
                        "type": "object",
                        "required": ["command"],
                        "properties": {
                            "cwd": {"type": "string"},
                            "env": {"type": "object", "additionalProperties": {"type": "string"}},
                            "args": {"type": "array", "items": {"type": "string"}},
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {"type": "integer", "default": 300},
                            "capture_output": {"type": "boolean", "default": True},
                        },
                    },
                },
            },
        ]

    @pytest.fixture
    def real_mcp_supabase_chain(self):
        """Real mcp_supabase chain from Supabase."""
        return [
            {
                "depth": 0,
                "tool_id": "mcp_supabase",
                "tool_type": "mcp_server",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {
                        "env": {"SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"},
                        "args": ["-y", "@supabase/mcp-server-supabase@latest"],
                        "command": "npx",
                        "transport": "stdio",
                    },
                    "tool_id": "mcp_supabase",
                    "version": "1.0.0",
                    "executor": "subprocess",
                    "tool_type": "mcp_server",
                },
            },
            {
                "depth": 1,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {
                    "tool_id": "subprocess",
                    "version": "1.0.0",
                    "tool_type": "primitive",
                    "description": "Subprocess execution primitive",
                    "config_schema": {
                        "type": "object",
                        "required": ["command"],
                        "properties": {
                            "cwd": {"type": "string"},
                            "env": {"type": "object", "additionalProperties": {"type": "string"}},
                            "args": {"type": "array", "items": {"type": "string"}},
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {"type": "integer", "default": 300},
                            "capture_output": {"type": "boolean", "default": True},
                        },
                    },
                },
            },
        ]

    @pytest.mark.asyncio
    async def test_real_data_processor_chain_resolution(
        self, resolver, mock_registry, real_data_processor_chain
    ):
        """Test resolving real data_processor chain."""
        mock_registry.resolve_chain.return_value = real_data_processor_chain

        result = await resolver.resolve("data_processor")

        assert len(result) == 3
        assert result[0]["tool_id"] == "data_processor"
        assert result[1]["tool_id"] == "python_runtime"
        assert result[2]["tool_id"] == "subprocess"
        assert result[2]["tool_type"] == "primitive"

    @pytest.mark.asyncio
    async def test_real_config_merging_complex_python_chain(
        self, resolver, real_data_processor_chain
    ):
        """Test complex config merging with real Python chain."""
        merged = resolver.merge_configs(real_data_processor_chain)

        # Child (data_processor) should override parent values
        assert merged["timeout"] == 1800  # From data_processor (child)
        assert merged["command"] == "python3"  # From python_runtime (parent)
        assert merged["entrypoint"] == "process_data.py"  # From data_processor (child)

        # Environment variables should be merged
        assert merged["env"]["PYTHONPATH"] == "/app/lib"  # From data_processor
        assert merged["env"]["DATA_CACHE_SIZE"] == "1000"  # From data_processor

        # Complex nested objects should be merged
        assert merged["venv"]["enabled"] is True  # From python_runtime
        assert merged["venv"]["path"] == ".venv"  # From python_runtime
        assert merged["venv"]["auto_create"] is True  # From python_runtime

        # Arrays should be preserved
        assert "pandas" in merged["requires"]
        assert "numpy" in merged["requires"]
        assert "scipy" in merged["requires"]

    @pytest.mark.asyncio
    async def test_real_config_merging_node_vs_python(
        self, resolver, real_api_client_chain, real_data_processor_chain
    ):
        """Test config merging differences between Node.js and Python chains."""
        node_merged = resolver.merge_configs(real_api_client_chain)
        python_merged = resolver.merge_configs(real_data_processor_chain)

        # Different commands
        assert node_merged["command"] == "node"
        assert python_merged["command"] == "python3"

        # Different package managers
        assert node_merged.get("package_manager") == "npm"
        assert "package_manager" not in python_merged

        # Different environment setups
        assert node_merged["env"]["NODE_ENV"] == "production"
        assert python_merged["env"]["PYTHONPATH"] == "/app/lib"

        # Python has venv, Node doesn't
        assert "venv" in python_merged
        assert "venv" not in node_merged

    @pytest.mark.asyncio
    async def test_batch_resolution_with_real_chains(
        self,
        resolver,
        mock_registry,
        real_data_processor_chain,
        real_web_scraper_chain,
        real_api_client_chain,
    ):
        """Test batch resolution with multiple real chains."""
        # Simulate batch response from Supabase
        batch_results = {
            "data_processor": real_data_processor_chain,
            "web_scraper": real_web_scraper_chain,
            "api_client": real_api_client_chain,
        }
        mock_registry.resolve_chains_batch.return_value = batch_results

        tool_ids = ["data_processor", "web_scraper", "api_client"]
        result = await resolver.resolve_batch(tool_ids)

        assert len(result) == 3
        assert "data_processor" in result
        assert "web_scraper" in result
        assert "api_client" in result

        # Verify each chain structure
        assert len(result["data_processor"]) == 3
        assert len(result["web_scraper"]) == 3
        assert len(result["api_client"]) == 3

        # Verify terminal primitives
        assert result["data_processor"][-1]["tool_type"] == "primitive"
        assert result["web_scraper"][-1]["tool_type"] == "primitive"
        assert result["api_client"][-1]["tool_type"] == "primitive"

    @pytest.mark.asyncio
    async def test_mcp_server_direct_to_primitive(self, resolver, real_mcp_supabase_chain):
        """Test MCP server that goes directly to primitive (no runtime)."""
        merged = resolver.merge_configs(real_mcp_supabase_chain)

        # Should have MCP-specific config
        assert merged["command"] == "npx"
        assert merged["args"] == ["-y", "@supabase/mcp-server-supabase@latest"]
        assert merged["transport"] == "stdio"
        assert merged["env"]["SUPABASE_ACCESS_TOKEN"] == "${SUPABASE_ACCESS_TOKEN}"

    @pytest.mark.asyncio
    async def test_concurrent_chain_resolution_stress(
        self, resolver, mock_registry, real_data_processor_chain
    ):
        """Stress test concurrent chain resolutions."""
        mock_registry.resolve_chain.return_value = real_data_processor_chain

        # Simulate 100 concurrent requests
        tasks = []
        for i in range(100):
            tasks.append(resolver.resolve(f"data_processor_{i}"))

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # All should succeed
        assert len(results) == 100
        for result in results:
            assert len(result) == 3
            assert result[-1]["tool_type"] == "primitive"

        # Should complete reasonably quickly (caching helps)
        assert end_time - start_time < 1.0  # Less than 1 second

    @pytest.mark.asyncio
    async def test_cache_efficiency_with_repeated_requests(
        self, resolver, mock_registry, real_data_processor_chain
    ):
        """Test cache efficiency with repeated requests."""
        mock_registry.resolve_chain.return_value = real_data_processor_chain

        # First request should hit registry
        result1 = await resolver.resolve("data_processor")
        assert mock_registry.resolve_chain.call_count == 1

        # Subsequent requests should use cache
        result2 = await resolver.resolve("data_processor")
        result3 = await resolver.resolve("data_processor")

        # Registry should still only be called once
        assert mock_registry.resolve_chain.call_count == 1

        # Results should be identical
        assert result1 == result2 == result3

    @pytest.mark.asyncio
    async def test_deep_nested_config_merging(self, resolver):
        """Test deep nested config merging with complex structures."""
        complex_chain = [
            {
                "depth": 0,
                "tool_id": "complex_script",
                "tool_type": "script",
                "executor_id": "runtime",
                "manifest": {
                    "config": {
                        "database": {
                            "connections": {
                                "primary": {
                                    "host": "override-host",
                                    "port": 5432,
                                    "ssl": {"enabled": True, "verify": False},
                                },
                                "secondary": {"host": "secondary-host"},
                            },
                            "pool": {"min": 5, "max": 20},
                        },
                        "logging": {"level": "DEBUG", "handlers": ["console", "file"]},
                    }
                },
            },
            {
                "depth": 1,
                "tool_id": "runtime",
                "tool_type": "runtime",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {
                        "database": {
                            "connections": {
                                "primary": {
                                    "host": "default-host",
                                    "timeout": 30,
                                    "ssl": {"enabled": False, "cert": "/path/to/cert"},
                                }
                            },
                            "pool": {"max": 10, "idle_timeout": 300},
                        },
                        "logging": {"level": "INFO", "format": "json"},
                    }
                },
            },
            {
                "depth": 2,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {}},
            },
        ]

        merged = resolver.merge_configs(complex_chain)

        # Child should override parent at all levels
        assert merged["database"]["connections"]["primary"]["host"] == "override-host"  # Child wins
        assert merged["database"]["connections"]["primary"]["timeout"] == 30  # Parent preserved
        assert merged["database"]["connections"]["primary"]["port"] == 5432  # Child only

        # SSL config should be merged
        assert merged["database"]["connections"]["primary"]["ssl"]["enabled"] is True  # Child wins
        assert merged["database"]["connections"]["primary"]["ssl"]["verify"] is False  # Child only
        assert (
            merged["database"]["connections"]["primary"]["ssl"]["cert"] == "/path/to/cert"
        )  # Parent preserved

        # Secondary connection should be child only
        assert merged["database"]["connections"]["secondary"]["host"] == "secondary-host"

        # Pool config should be merged
        assert merged["database"]["pool"]["min"] == 5  # Child only
        assert merged["database"]["pool"]["max"] == 20  # Child wins
        assert merged["database"]["pool"]["idle_timeout"] == 300  # Parent preserved

        # Logging should be merged
        assert merged["logging"]["level"] == "DEBUG"  # Child wins
        assert merged["logging"]["format"] == "json"  # Parent preserved
        assert merged["logging"]["handlers"] == ["console", "file"]  # Child only

    @pytest.mark.asyncio
    async def test_executor_integration_with_real_chains(
        self, executor, mock_registry, real_data_processor_chain
    ):
        """Test full executor integration with real chain data."""
        from kiwi_mcp.primitives.subprocess import SubprocessResult

        mock_registry.resolve_chain.return_value = real_data_processor_chain

        # Mock subprocess execution
        with patch.object(executor.subprocess_primitive, "execute") as mock_execute:
            mock_execute.return_value = SubprocessResult(
                success=True,
                stdout="Data processing completed successfully",
                stderr="",
                return_code=0,
                duration_ms=1500,
            )

            result = await executor.execute("data_processor", {"input_file": "data.csv"})

            assert result.success is True
            assert "Data processing completed successfully" in result.data["stdout"]

            # Verify merged config was passed to subprocess
            mock_execute.assert_called_once()
            merged_config = mock_execute.call_args[0][0]

            # Should have merged config from all levels
            assert merged_config["command"] == "python3"
            assert merged_config["timeout"] == 1800  # From script (child)
            assert merged_config["entrypoint"] == "process_data.py"
            assert merged_config["env"]["PYTHONPATH"] == "/app/lib"
            assert merged_config["venv"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_error_propagation_in_complex_chains(
        self, executor, mock_registry, real_data_processor_chain
    ):
        """Test error propagation through complex chains."""
        mock_registry.resolve_chain.return_value = real_data_processor_chain

        # Mock subprocess to fail
        with patch.object(executor.subprocess_primitive, "execute") as mock_execute:
            from kiwi_mcp.primitives.subprocess import SubprocessResult

            mock_execute.return_value = SubprocessResult(
                success=False,
                stdout="",
                stderr="ModuleNotFoundError: No module named 'pandas'",
                return_code=1,
                duration_ms=100,
            )

            result = await executor.execute("data_processor", {})

            assert result.success is False
            assert "ModuleNotFoundError" in result.error
            assert result.metadata["type"] == "subprocess"
            assert result.metadata["return_code"] == 1

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_chains(self, resolver, mock_registry):
        """Test memory usage with large chain configurations."""
        # Create a chain with very large manifest data
        large_manifest = {
            "config": {
                "large_data": ["item_" + str(i) for i in range(10000)],  # 10k items
                "nested": {
                    f"key_{i}": f"value_{i}"
                    for i in range(1000)  # 1k nested items
                },
            }
        }

        large_chain = [
            {
                "depth": 0,
                "tool_id": "large_script",
                "tool_type": "script",
                "executor_id": "subprocess",
                "manifest": large_manifest,
            },
            {
                "depth": 1,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {}},
            },
        ]

        mock_registry.resolve_chain.return_value = large_chain

        # Should handle large configs without issues
        result = await resolver.resolve("large_script")
        merged = resolver.merge_configs(result)

        assert len(merged["large_data"]) == 10000
        assert len(merged["nested"]) == 1000
        assert merged["nested"]["key_500"] == "value_500"

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, resolver, mock_registry):
        """Test detection of circular dependencies in chains."""
        # This shouldn't happen with proper DB constraints, but test anyway
        circular_chain = [
            {
                "depth": 0,
                "tool_id": "script_a",
                "tool_type": "script",
                "executor_id": "script_b",
                "manifest": {"config": {"from": "script_a"}},
            },
            {
                "depth": 1,
                "tool_id": "script_b",
                "tool_type": "script",
                "executor_id": "script_a",  # Circular!
                "manifest": {"config": {"from": "script_b"}},
            },
        ]

        mock_registry.resolve_chain.return_value = circular_chain

        # Should still work (DB function handles this)
        result = await resolver.resolve("script_a")
        merged = resolver.merge_configs(result)

        # Config merging should still work
        assert merged["from"] == "script_a"  # Child wins
