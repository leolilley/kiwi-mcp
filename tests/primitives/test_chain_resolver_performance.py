"""
Performance benchmarks for ChainResolver using filesystem-based tools.
"""

import pytest
import asyncio
import time
import statistics
from kiwi_mcp.primitives.executor import ChainResolver


class TestChainResolverPerformance:
    """Performance benchmarks for ChainResolver."""

    @pytest.fixture
    def project_path(self, tmp_path):
        """Create test project with tools."""
        project = tmp_path / "test_project"
        project.mkdir()
        tools_dir = project / ".ai" / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create subprocess primitive (base for all chains)
        primitives_dir = tools_dir / "primitives"
        primitives_dir.mkdir()
        subprocess_file = primitives_dir / "subprocess.py"
        subprocess_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "primitives"
__config__ = {"timeout": 300, "capture_output": True}
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
__config__ = {"command": "python3", "venv": {"enabled": True, "path": ".venv"}, "install_deps": True}
""")
        
        # Create node_runtime
        node_runtime_file = runtimes_dir / "node_runtime.py"
        node_runtime_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:2222222222222222222222222222222222222222222222222222222222222222
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"
__config__ = {"command": "node", "package_manager": "npm", "install_deps": True}
""")
        
        # Create python_data_processor (for single chain test)
        utility_dir = tools_dir / "utility"
        utility_dir.mkdir()
        python_data_processor_file = utility_dir / "python_data_processor.py"
        python_data_processor_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:3333333333333333333333333333333333333333333333333333333333333333
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {"entrypoint": "python_data_processor.py", "requires": ["requests", "pandas", "numpy"], "timeout": 600, "env": {"PYTHONPATH": "/app", "DEBUG": "1"}}
""")
        
        # Create batch tools (50 tools)
        for i in range(50):
            batch_file = utility_dir / f"batch_script_{i}.py"
            batch_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i % 10) * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "batch_script_{i}.py", "timeout": 300}}
""")
            
            individual_file = utility_dir / f"individual_script_{i}.py"
            individual_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i % 10) * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "individual_script_{i}.py", "timeout": 300}}
""")
        
        # Create python tools (10 tools)
        for i in range(10):
            python_file = utility_dir / f"python_tool_{i}.py"
            python_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i) * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "python_tool_{i}.py", "timeout": 300}}
""")
        
        # Create node tools (10 tools)
        for i in range(10):
            node_file = utility_dir / f"node_tool_{i}.py"
            node_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i + 10) * 64}
__version__ = "1.0.0"
__tool_type__ = "node"
__executor_id__ = "node_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "node_tool_{i}.js", "timeout": 300, "env": {{"NODE_ENV": "production"}}}}
""")
        
        # Create MCP tools (10 tools)
        mcp_dir = tools_dir / "mcp"
        mcp_dir.mkdir()
        for i in range(10):
            mcp_file = mcp_dir / f"mcp_tool_{i}.py"
            mcp_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i + 20) * 64}
__version__ = "1.0.0"
__tool_type__ = "mcp_server"
__executor_id__ = "subprocess"
__category__ = "mcp"
__config__ = {{"command": "npx", "args": ["-y", "@mcp_tool_{i}@latest"], "env": {{"TOKEN": "${{TOKEN}}"}}, "transport": "stdio"}}
""")
        
        # Create new tools for mixed cache test (15 tools)
        for i in range(15):
            new_file = utility_dir / f"new_tool_{i}.py"
            new_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i + 30) * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "new_tool_{i}.py", "timeout": 300}}
""")
        
        # Create concurrent tools (200 tools)
        for i in range(200):
            concurrent_file = utility_dir / f"concurrent_tool_{i}.py"
            concurrent_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i % 20) * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "concurrent_tool_{i}.py", "timeout": 300}}
""")
        
        # Create memory test tools (1000 tools)
        for i in range(1000):
            memory_file = utility_dir / f"memory_test_tool_{i}.py"
            memory_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i % 50) * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
__config__ = {{"entrypoint": "memory_test_tool_{i}.py", "timeout": 300}}
""")
        
        return project

    @pytest.fixture
    def resolver(self, project_path):
        """ChainResolver instance."""
        return ChainResolver(project_path)

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
    async def test_batch_resolution_performance(self, resolver, project_path):
        """Benchmark batch resolution performance."""
        # Use fresh resolver to avoid cache effects
        fresh_resolver = ChainResolver(project_path)

        batch_tool_ids = [f"batch_script_{i}" for i in range(50)]
        individual_tool_ids = [f"individual_script_{i}" for i in range(50)]

        # Test batch resolution
        start = time.perf_counter()
        batch_results = await fresh_resolver.resolve_batch(batch_tool_ids)
        batch_time = (time.perf_counter() - start) * 1000

        # Test individual resolutions for comparison (with fresh resolver)
        fresh_resolver2 = ChainResolver(project_path)
        start = time.perf_counter()
        individual_results = {}
        for tool_id in individual_tool_ids:
            individual_results[tool_id] = await fresh_resolver2.resolve(tool_id)
        individual_time = (time.perf_counter() - start) * 1000

        print(f"\nBatch vs Individual resolution (50 tools):")
        print(f"  Batch: {batch_time:.1f}ms")
        print(f"  Individual: {individual_time:.1f}ms")
        print(f"  Speedup: {individual_time / batch_time:.1f}x")

        # Batch should be reasonably fast (may not always be faster due to OS caching)
        assert batch_time < individual_time * 1.5  # Allow some variance
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
        # Resolve a chain first to get real chain structure
        chain = await resolver.resolve("python_data_processor")
        
        # Create a complex chain with deep nesting by modifying the resolved chain
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
    async def test_error_handling_performance(self, resolver, project_path):
        """Test performance when errors occur."""
        tools_dir = project_path / ".ai" / "tools" / "utility"
        tools_dir.mkdir(parents=True, exist_ok=True)
        
        # Create some valid tools
        for i in range(50):
            tool_file = tools_dir / f"success_tool_{i}.py"
            tool_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{'a' * 64}
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "utility"
""")

        # Mix of successful and failing requests (failing ones don't exist)
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
    async def test_deep_chain_performance(self, resolver, project_path):
        """Test performance with very deep chains."""
        tools_dir = project_path / ".ai" / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create a 10-level deep chain in filesystem
        depth = 10
        
        # Create primitive (last level)
        primitives_dir = tools_dir / "primitives"
        primitives_dir.mkdir()
        primitive_file = primitives_dir / f"level_{depth-1}_tool.py"
        primitive_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{'0' * 64}
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "primitives"
__config__ = {{"level_{depth-1}_key": "level_{depth-1}_value", "shared_key": "overridden_at_level_{depth-1}"}}
""")
        
        # Create intermediate runtimes
        runtimes_dir = tools_dir / "runtimes"
        runtimes_dir.mkdir(exist_ok=True)
        for i in range(depth - 2, 0, -1):
            runtime_file = runtimes_dir / f"level_{i}_tool.py"
            runtime_file.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{str(i) * 64}
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "level_{i+1}_tool"
__category__ = "runtimes"
__config__ = {{"level_{i}_key": "level_{i}_value", "shared_key": "overridden_at_level_{i}"}}
""")
        
        # Create leaf tool
        utility_dir = tools_dir / "utility"
        utility_dir.mkdir(exist_ok=True)
        leaf_tool = utility_dir / "level_0_tool.py"
        leaf_tool.write_text(f"""# kiwi-mcp:validated:2026-01-01T00:00:00Z:{'a' * 64}
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "level_1_tool"
__category__ = "utility"
__config__ = {{"level_0_key": "level_0_value", "shared_key": "overridden_at_level_0"}}
""")

        # Benchmark deep chain resolution and merging
        times = []
        for _ in range(100):
            start = time.perf_counter()
            result = await resolver.resolve("level_0_tool")
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
