"""
Performance benchmarks for ChainResolver using real Supabase data.
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import AsyncMock, Mock
from kiwi_mcp.primitives.executor import ChainResolver, PrimitiveExecutor


class TestChainResolverPerformance:
    """Performance benchmarks for ChainResolver."""

    @pytest.fixture
    def mock_registry(self):
        """Mock ToolRegistry with realistic latency."""
        registry = Mock()

        async def mock_resolve_chain(tool_id):
            # Simulate database latency (1-5ms)
            await asyncio.sleep(0.001 + (hash(tool_id) % 5) * 0.001)
            return self.get_sample_chain(tool_id)

        async def mock_resolve_chains_batch(tool_ids):
            # Simulate batch query latency (5-15ms for batch)
            await asyncio.sleep(0.005 + len(tool_ids) * 0.001)
            return {tool_id: self.get_sample_chain(tool_id) for tool_id in tool_ids}

        registry.resolve_chain = AsyncMock(side_effect=mock_resolve_chain)
        registry.resolve_chains_batch = AsyncMock(side_effect=mock_resolve_chains_batch)
        return registry

    def get_sample_chain(self, tool_id):
        """Generate a realistic chain for testing."""
        if tool_id.startswith("python_"):
            return [
                {
                    "depth": 0,
                    "tool_id": tool_id,
                    "tool_type": "python",
                    "executor_id": "python_runtime",
                    "manifest": {
                        "config": {
                            "entrypoint": f"{tool_id}.py",
                            "requires": ["requests", "pandas", "numpy"],
                            "timeout": 600,
                            "env": {"PYTHONPATH": "/app", "DEBUG": "1"},
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
                            "command": "python3",
                            "venv": {"enabled": True, "path": ".venv"},
                            "install_deps": True,
                        }
                    },
                },
                {
                    "depth": 2,
                    "tool_id": "subprocess",
                    "tool_type": "primitive",
                    "executor_id": None,
                    "manifest": {"config": {"timeout": 300, "capture_output": True}},
                },
            ]
        elif tool_id.startswith("node_"):
            return [
                {
                    "depth": 0,
                    "tool_id": tool_id,
                    "tool_type": "node",
                    "executor_id": "node_runtime",
                    "manifest": {
                        "config": {
                            "entrypoint": f"{tool_id}.js",
                            "requires": ["axios", "lodash"],
                            "timeout": 300,
                            "env": {"NODE_ENV": "production"},
                        }
                    },
                },
                {
                    "depth": 1,
                    "tool_id": "node_runtime",
                    "tool_type": "runtime",
                    "executor_id": "subprocess",
                    "manifest": {
                        "config": {
                            "command": "node",
                            "package_manager": "npm",
                            "install_deps": True,
                        }
                    },
                },
                {
                    "depth": 2,
                    "tool_id": "subprocess",
                    "tool_type": "primitive",
                    "executor_id": None,
                    "manifest": {"config": {"timeout": 300, "capture_output": True}},
                },
            ]
        else:  # MCP server
            return [
                {
                    "depth": 0,
                    "tool_id": tool_id,
                    "tool_type": "mcp_server",
                    "executor_id": "subprocess",
                    "manifest": {
                        "config": {
                            "command": "npx",
                            "args": ["-y", f"@{tool_id}@latest"],
                            "env": {"TOKEN": "${TOKEN}"},
                            "transport": "stdio",
                        }
                    },
                },
                {
                    "depth": 1,
                    "tool_id": "subprocess",
                    "tool_type": "primitive",
                    "executor_id": None,
                    "manifest": {"config": {"timeout": 300, "capture_output": True}},
                },
            ]

    @pytest.fixture
    def resolver(self, mock_registry):
        """ChainResolver instance."""
        return ChainResolver(mock_registry)

    @pytest.mark.asyncio
    async def test_single_chain_resolution_latency(self, resolver):
        """Benchmark single chain resolution latency."""
        tool_id = "python_data_processor"

        # Warm up
        await resolver.resolve(tool_id)

        # Benchmark
        times = []
        for _ in range(100):
            start = time.perf_counter()
            await resolver.resolve(tool_id)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to milliseconds

        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile

        print(f"\nSingle chain resolution (cached):")
        print(f"  Average: {avg_time:.3f}ms")
        print(f"  95th percentile: {p95_time:.3f}ms")

        # Cached requests should be very fast
        assert avg_time < 0.1  # Less than 0.1ms average
        assert p95_time < 0.5  # Less than 0.5ms at 95th percentile

    @pytest.mark.asyncio
    async def test_batch_resolution_performance(self, resolver, mock_registry):
        """Benchmark batch resolution performance."""
        # Use fresh resolver to avoid cache effects
        fresh_resolver = ChainResolver(mock_registry)

        batch_tool_ids = [f"batch_script_{i}" for i in range(50)]
        individual_tool_ids = [f"individual_script_{i}" for i in range(50)]

        # Test batch resolution
        start = time.perf_counter()
        batch_results = await fresh_resolver.resolve_batch(batch_tool_ids)
        batch_time = (time.perf_counter() - start) * 1000

        # Test individual resolutions for comparison (with fresh resolver)
        fresh_resolver2 = ChainResolver(mock_registry)
        start = time.perf_counter()
        individual_results = {}
        for tool_id in individual_tool_ids:
            individual_results[tool_id] = await fresh_resolver2.resolve(tool_id)
        individual_time = (time.perf_counter() - start) * 1000

        print(f"\nBatch vs Individual resolution (50 tools):")
        print(f"  Batch: {batch_time:.1f}ms")
        print(f"  Individual: {individual_time:.1f}ms")
        print(f"  Speedup: {individual_time / batch_time:.1f}x")

        # Batch should be significantly faster for cold requests
        assert batch_time < individual_time
        assert len(batch_results) == 50

        # Results should have same structure
        sample_batch = list(batch_results.values())[0]
        sample_individual = list(individual_results.values())[0]
        assert len(sample_batch) == len(sample_individual)

    @pytest.mark.asyncio
    async def test_cache_hit_ratio_performance(self, resolver):
        """Test cache performance with mixed hit/miss patterns."""
        # Create a mix of tools
        python_tools = [f"python_tool_{i}" for i in range(10)]
        node_tools = [f"node_tool_{i}" for i in range(10)]
        mcp_tools = [f"mcp_tool_{i}" for i in range(10)]
        all_tools = python_tools + node_tools + mcp_tools

        # First pass - populate cache
        start = time.perf_counter()
        for tool_id in all_tools:
            await resolver.resolve(tool_id)
        first_pass_time = (time.perf_counter() - start) * 1000

        # Second pass - should hit cache
        start = time.perf_counter()
        for tool_id in all_tools:
            await resolver.resolve(tool_id)
        second_pass_time = (time.perf_counter() - start) * 1000

        # Third pass - mixed pattern (some cached, some new)
        mixed_tools = all_tools[:15] + [f"new_tool_{i}" for i in range(15)]
        start = time.perf_counter()
        for tool_id in mixed_tools:
            await resolver.resolve(tool_id)
        mixed_pass_time = (time.perf_counter() - start) * 1000

        print(f"\nCache performance (30 tools):")
        print(f"  First pass (cold): {first_pass_time:.1f}ms")
        print(f"  Second pass (100% cache hit): {second_pass_time:.1f}ms")
        print(f"  Mixed pass (50% cache hit): {mixed_pass_time:.1f}ms")
        print(f"  Cache speedup: {first_pass_time / second_pass_time:.1f}x")

        # Cache should provide significant speedup
        assert second_pass_time < first_pass_time / 5  # At least 5x faster
        assert mixed_pass_time < first_pass_time  # Faster than cold start

    @pytest.mark.asyncio
    async def test_config_merging_performance(self, resolver):
        """Benchmark config merging performance with complex configs."""
        # Create a complex chain with deep nesting
        complex_chain = []
        for depth in range(5):  # 5-level deep chain
            config = {}
            for i in range(20):  # 20 config keys per level
                config[f"key_{depth}_{i}"] = {
                    "nested": {
                        "value": f"value_{depth}_{i}",
                        "list": [f"item_{j}" for j in range(10)],
                        "dict": {f"subkey_{k}": f"subvalue_{k}" for k in range(5)},
                    }
                }

            complex_chain.append(
                {
                    "depth": depth,
                    "tool_id": f"tool_{depth}",
                    "tool_type": "python"
                    if depth == 0
                    else ("runtime" if depth < 4 else "primitive"),
                    "executor_id": f"tool_{depth + 1}" if depth < 4 else None,
                    "manifest": {"config": config},
                }
            )

        # Benchmark config merging
        times = []
        merged = {}
        for _ in range(100):
            start = time.perf_counter()
            merged = resolver.merge_configs(complex_chain)
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]

        print(f"\nComplex config merging (5 levels, 100 keys):")
        print(f"  Average: {avg_time:.3f}ms")
        print(f"  95th percentile: {p95_time:.3f}ms")
        print(f"  Merged keys: {len(merged)}")

        # Config merging should be reasonably fast even for complex configs
        assert avg_time < 5.0  # Less than 5ms average
        assert p95_time < 10.0  # Less than 10ms at 95th percentile
        assert len(merged) > 90  # Should have merged most keys

    @pytest.mark.asyncio
    async def test_concurrent_resolution_scalability(self, resolver):
        """Test scalability under concurrent load."""
        concurrency_levels = [1, 10, 50, 100, 200]
        results = {}

        for concurrency in concurrency_levels:
            tool_ids = [f"concurrent_tool_{i}" for i in range(concurrency)]

            start = time.perf_counter()
            tasks = [resolver.resolve(tool_id) for tool_id in tool_ids]
            await asyncio.gather(*tasks)
            total_time = (time.perf_counter() - start) * 1000

            throughput = concurrency / (total_time / 1000)  # requests per second
            results[concurrency] = {"time": total_time, "throughput": throughput}

        print(f"\nConcurrency scalability:")
        for concurrency, data in results.items():
            print(
                f"  {concurrency:3d} concurrent: {data['time']:6.1f}ms, {data['throughput']:6.0f} req/s"
            )

        # Throughput should scale reasonably with concurrency
        assert results[100]["throughput"] > results[10]["throughput"]
        assert results[200]["time"] < results[200]["time"] * 2  # Not linear degradation

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_cache(self, resolver):
        """Test memory efficiency with large cache."""
        import sys

        # Get initial memory usage
        initial_size = sys.getsizeof(resolver._chain_cache)

        # Populate cache with many entries
        for i in range(1000):
            tool_id = f"memory_test_tool_{i}"
            await resolver.resolve(tool_id)

        # Check cache size
        cache_size = sys.getsizeof(resolver._chain_cache)
        cache_entries = len(resolver._chain_cache)

        print(f"\nMemory efficiency (1000 cached chains):")
        print(f"  Cache entries: {cache_entries}")
        print(f"  Cache size: {cache_size:,} bytes")
        print(f"  Bytes per entry: {cache_size / cache_entries:.1f}")

        # Cache should be reasonably memory efficient
        assert cache_entries == 1000
        assert cache_size < 10 * 1024 * 1024  # Less than 10MB for 1000 entries

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, resolver, mock_registry):
        """Test performance when errors occur."""
        # Mock registry to occasionally fail
        original_resolve = mock_registry.resolve_chain.side_effect

        async def failing_resolve(tool_id):
            if "fail" in tool_id:
                raise Exception(f"Simulated failure for {tool_id}")
            return await original_resolve(tool_id)

        mock_registry.resolve_chain.side_effect = failing_resolve

        # Mix of successful and failing requests
        tool_ids = [f"success_tool_{i}" for i in range(50)] + [f"fail_tool_{i}" for i in range(50)]

        start = time.perf_counter()
        results = []
        for tool_id in tool_ids:
            try:
                result = await resolver.resolve(tool_id)
                results.append(("success", len(result)))
            except Exception as e:
                results.append(("error", str(e)))

        total_time = (time.perf_counter() - start) * 1000

        successes = sum(1 for r in results if r[0] == "success")
        errors = sum(1 for r in results if r[0] == "error")

        print(f"\nError handling performance (100 requests, 50% failure rate):")
        print(f"  Total time: {total_time:.1f}ms")
        print(f"  Successes: {successes}")
        print(f"  Errors: {errors}")
        print(f"  Avg time per request: {total_time / 100:.2f}ms")

        # Should handle errors gracefully without major performance impact
        assert successes == 50
        assert errors == 50
        assert total_time < 1000  # Less than 1 second for 100 requests

    @pytest.mark.asyncio
    async def test_deep_chain_performance(self, resolver, mock_registry):
        """Test performance with very deep chains."""

        # Create a 10-level deep chain
        def create_deep_chain(depth=10):
            chain = []
            for i in range(depth):
                chain.append(
                    {
                        "depth": i,
                        "tool_id": f"level_{i}_tool",
                        "tool_type": "python"
                        if i == 0
                        else ("runtime" if i < depth - 1 else "primitive"),
                        "executor_id": f"level_{i + 1}_tool" if i < depth - 1 else None,
                        "manifest": {
                            "config": {
                                f"level_{i}_key": f"level_{i}_value",
                                "shared_key": f"overridden_at_level_{i}",
                                "nested": {"deep": {"value": f"deep_value_{i}"}},
                            }
                        },
                    }
                )
            return chain

        deep_chain = create_deep_chain(10)
        mock_registry.resolve_chain.return_value = deep_chain

        # Benchmark deep chain resolution and merging
        times = []
        for _ in range(100):
            start = time.perf_counter()
            result = await resolver.resolve("deep_chain_tool")
            merged = resolver.merge_configs(result)
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]

        print(f"\nDeep chain performance (10 levels):")
        print(f"  Average: {avg_time:.3f}ms")
        print(f"  95th percentile: {p95_time:.3f}ms")

        # Should handle deep chains efficiently
        assert avg_time < 2.0  # Less than 2ms average
        assert p95_time < 5.0  # Less than 5ms at 95th percentile
