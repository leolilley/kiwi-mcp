"""
Stress tests and complex scenarios for ChainResolver using filesystem-based tools.
"""

import pytest
import asyncio
import time
from unittest.mock import patch
from kiwi_mcp.primitives.executor import ChainResolver, PrimitiveExecutor


class TestChainResolverStress:
    """Stress tests for ChainResolver with real-world scenarios."""

    @pytest.fixture
    def project_path(self, tmp_path):
        """Create test project with tools."""
        project = tmp_path / "test_project"
        project.mkdir()
        tools_dir = project / ".ai" / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create subprocess primitive
        primitives_dir = tools_dir / "primitives"
        primitives_dir.mkdir()
        subprocess_file = primitives_dir / "subprocess.py"
        subprocess_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "primitives"
""")
        
        # Create python_runtime
        runtimes_dir = tools_dir / "runtimes"
        runtimes_dir.mkdir()
        python_runtime_file = runtimes_dir / "python_runtime.py"
        python_runtime_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:1111111111111111111111111111111111111111111111111111111111111111
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"
__config__ = {"venv": {"path": ".venv", "enabled": True, "auto_create": True}, "command": "python3", "install_deps": True}
""")
        
        # Create node_runtime
        node_runtime_file = runtimes_dir / "node_runtime.py"
        node_runtime_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:2222222222222222222222222222222222222222222222222222222222222222
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"
__config__ = {"command": "node", "install_deps": True, "package_manager": "npm"}
""")
        
        # Create data_processor tool
        utility_dir = tools_dir / "utility"
        utility_dir.mkdir()
        data_processor_file = utility_dir / "data_processor.py"
        data_processor_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:3333333333333333333333333333333333333333333333333333333333333333
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {"env": {"PYTHONPATH": "/app/lib", "DATA_CACHE_SIZE": "1000"}, "timeout": 1800, "requires": ["pandas", "numpy", "scipy"], "entrypoint": "process_data.py", "memory_limit": "2GB"}
""")
        
        # Create web_scraper tool
        web_scraper_file = utility_dir / "web_scraper.py"
        web_scraper_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:4444444444444444444444444444444444444444444444444444444444444444
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {"env": {"USER_AGENT": "WebScraper/1.0", "MAX_RETRIES": "3"}, "timeout": 600, "requires": ["requests", "beautifulsoup4", "selenium"], "entrypoint": "scraper.py", "rate_limit": 10}
""")
        
        # Create api_client tool (Node.js)
        api_client_file = utility_dir / "api_client.py"
        api_client_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:5555555555555555555555555555555555555555555555555555555555555555
__version__ = "1.0.0"
__tool_type__ = "node"
__executor_id__ = "node_runtime"
__category__ = "utility"
__config__ = {"env": {"NODE_ENV": "production", "API_TIMEOUT": "30000"}, "timeout": 300, "requires": ["axios", "lodash", "moment"], "entrypoint": "api_client.js"}
""")
        
        # Create mcp_supabase tool
        mcp_dir = tools_dir / "mcp"
        mcp_dir.mkdir()
        mcp_supabase_file = mcp_dir / "mcp_supabase.py"
        mcp_supabase_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:6666666666666666666666666666666666666666666666666666666666666666
__version__ = "1.0.0"
__tool_type__ = "mcp_server"
__executor_id__ = "subprocess"
__category__ = "mcp"
__config__ = {"env": {"SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"}, "args": ["-y", "@supabase/mcp-server-supabase@latest"], "command": "npx", "transport": "stdio"}
""")
        
        # Create data_processor variants for concurrent tests
        for i in range(100):
            variant_file = utility_dir / f"data_processor_{i}.py"
            variant_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i % 10) * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "process_data_{i}.py", "timeout": 1800}}
""")
        
        # Create large_script tool
        large_script_file = utility_dir / "large_script.py"
        # Create config with large data
        large_data = '["item_' + '", "item_'.join(str(i) for i in range(10000)) + '"]'
        nested_dict = '{' + ', '.join(f'"key_{i}": "value_{i}"' for i in range(1000)) + '}'
        large_script_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:7777777777777777777777777777777777777777777777777777777777777777
__version__ = "1.0.0"
__tool_type__ = "bash"
__executor_id__ = "subprocess"
__category__ = "utility"
__config__ = {{"large_data": {large_data}, "nested": {nested_dict}}}
""")
        
        # Create script_a and script_b for circular dependency test
        script_a_file = utility_dir / "script_a.py"
        script_a_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:8888888888888888888888888888888888888888888888888888888888888888
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "script_b"
__category__ = "utility"
__config__ = {"from": "script_a"}
""")
        
        script_b_file = utility_dir / "script_b.py"
        script_b_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:9999999999999999999999999999999999999999999999999999999999999999
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "script_a"
__category__ = "utility"
__config__ = {"from": "script_b"}
""")
        
        return project

    @pytest.fixture
    def resolver(self, project_path):
        """ChainResolver instance with test project."""
        return ChainResolver(project_path)

    @pytest.fixture
    def executor(self, project_path):
        """PrimitiveExecutor for integration tests."""
        return PrimitiveExecutor(project_path=project_path)

    # Chain data fixtures for config merging tests (no filesystem needed)
    @pytest.fixture
    def real_data_processor_chain(self):
        """Real data_processor chain data for config merging tests."""
        return [
            {
                "depth": 0,
                "tool_id": "data_processor",
                "tool_type": "python",
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

    @pytest.fixture
    def real_web_scraper_chain(self):
        """Real web_scraper chain data for config merging tests."""
        return [
            {
                "depth": 0,
                "tool_id": "web_scraper",
                "tool_type": "python",
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

    @pytest.fixture
    def real_api_client_chain(self):
        """Real api_client chain data for config merging tests."""
        return [
            {
                "depth": 0,
                "tool_id": "api_client",
                "tool_type": "node",
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

    @pytest.fixture
    def real_mcp_supabase_chain(self):
        """Real mcp_supabase chain data for config merging tests."""
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
                },
            },
            {
                "depth": 1,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {}},
            },
        ]

    @pytest.mark.asyncio
    async def test_real_data_processor_chain_resolution(self, resolver):
        """Test resolving real data_processor chain from filesystem."""
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
    async def test_batch_resolution_with_real_chains(self, resolver):
        """Test batch resolution with multiple real chains from filesystem."""
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
    async def test_concurrent_chain_resolution_stress(self, resolver):
        """Stress test concurrent chain resolutions."""
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
    async def test_cache_efficiency_with_repeated_requests(self, resolver):
        """Test cache efficiency with repeated requests."""
        # First request should read from filesystem
        result1 = await resolver.resolve("data_processor")

        # Subsequent requests should use cache
        result2 = await resolver.resolve("data_processor")
        result3 = await resolver.resolve("data_processor")

        # Results should be identical
        assert result1 == result2 == result3

    @pytest.mark.asyncio
    async def test_deep_nested_config_merging(self, resolver):
        """Test deep nested config merging with complex structures."""
        complex_chain = [
            {
                "depth": 0,
                "tool_id": "complex_script",
                "tool_type": "python",
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
    async def test_executor_integration_with_real_chains(self, executor):
        """Test full executor integration with real chain data."""
        from kiwi_mcp.primitives.subprocess import SubprocessResult

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
    async def test_error_propagation_in_complex_chains(self, executor):
        """Test error propagation through complex chains."""
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
    async def test_memory_usage_with_large_chains(self, resolver):
        """Test memory usage with large chain configurations."""
        # Should handle large configs without issues
        result = await resolver.resolve("large_script")
        merged = resolver.merge_configs(result)

        assert len(merged["large_data"]) == 10000
        assert len(merged["nested"]) == 1000
        assert merged["nested"]["key_500"] == "value_500"

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, resolver):
        """Test detection of circular dependencies in chains."""
        # This should be detected by the resolver
        with pytest.raises(Exception):  # Should raise an error for circular dependency
            await resolver.resolve("script_a")
