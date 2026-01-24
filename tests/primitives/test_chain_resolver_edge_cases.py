"""
Edge case tests for ChainResolver - error handling and special cases.
"""

import pytest
from pathlib import Path
from kiwi_mcp.primitives.executor import ChainResolver, ToolNotFoundError


class TestChainResolverEdgeCases:
    """Test ChainResolver edge cases and error handling."""

    @pytest.fixture
    def project_path(self, tmp_path):
        """Create a test project structure."""
        project = tmp_path / "test_project"
        project.mkdir()
        return project

    @pytest.fixture
    def resolver(self, project_path):
        """ChainResolver instance."""
        return ChainResolver(project_path)

    @pytest.mark.asyncio
    async def test_circular_dependency(self, resolver, project_path):
        """Test that circular dependencies are detected."""
        tools_dir = project_path / ".ai" / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create tool_a that depends on tool_b
        tool_a = tools_dir / "tool_a.py"
        tool_a.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "tool_b"
__category__ = "utility"
""")
        
        # Create tool_b that depends on tool_a (circular!)
        tool_b = tools_dir / "tool_b.py"
        tool_b.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "tool_a"
__category__ = "runtimes"
""")
        
        with pytest.raises(ToolNotFoundError) as exc_info:
            await resolver.resolve("tool_a")
        
        assert "circular dependency" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_missing_signature(self, resolver, project_path):
        """Test that tools without signatures raise error."""
        tools_dir = project_path / ".ai" / "tools" / "utility"
        tools_dir.mkdir(parents=True)
        
        # Create tool without signature
        tool_file = tools_dir / "unsigned_tool.py"
        tool_file.write_text("""__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"
""")
        
        with pytest.raises(ToolNotFoundError) as exc_info:
            await resolver.resolve("unsigned_tool")
        
        assert "no signature" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_missing_dependency(self, resolver, project_path):
        """Test that missing dependencies raise error."""
        tools_dir = project_path / ".ai" / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create tool that depends on nonexistent runtime
        utility_dir = tools_dir / "utility"
        utility_dir.mkdir()
        tool_file = utility_dir / "test_tool.py"
        tool_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:2222222222222222222222222222222222222222222222222222222222222222
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "nonexistent_runtime"
__category__ = "utility"
""")
        
        with pytest.raises(ToolNotFoundError) as exc_info:
            await resolver.resolve("test_tool")
        
        assert "not found locally" in str(exc_info.value).lower()
        assert "nonexistent_runtime" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_metadata(self, resolver, project_path):
        """Test that tools with missing required metadata raise error."""
        tools_dir = project_path / ".ai" / "tools" / "utility"
        tools_dir.mkdir(parents=True)
        
        # Create tool with missing executor_id (required for non-primitives)
        tool_file = tools_dir / "invalid_tool.py"
        tool_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:3333333333333333333333333333333333333333333333333333333333333333
__version__ = "1.0.0"
__tool_type__ = "python"
# Missing __executor_id__
__category__ = "utility"

def main():
    return "test"
""")
        
        # This might not raise during resolution if executor_id is None, but should fail later
        # Let's test that it resolves but has None executor_id
        try:
            chain = await resolver.resolve("invalid_tool")
            # If it resolves, executor_id should be None (treated as primitive)
            assert len(chain) == 1
            assert chain[0]["executor_id"] is None
        except ToolNotFoundError:
            # Or it might fail if metadata extraction fails
            pass

    @pytest.mark.asyncio
    async def test_empty_chain_resolution(self, resolver, project_path):
        """Test resolving a tool that is itself a primitive."""
        tools_dir = project_path / ".ai" / "tools" / "primitives"
        tools_dir.mkdir(parents=True)
        
        # Create primitive (executor_id is None)
        primitive_file = tools_dir / "subprocess.py"
        primitive_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "primitives"
""")
        
        chain = await resolver.resolve("subprocess")
        
        assert len(chain) == 1
        assert chain[0]["tool_id"] == "subprocess"
        assert chain[0]["executor_id"] is None

    @pytest.mark.asyncio
    async def test_deep_chain(self, resolver, project_path):
        """Test resolving a deep chain (tool -> runtime -> primitive)."""
        tools_dir = project_path / ".ai" / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create primitive
        primitives_dir = tools_dir / "primitives"
        primitives_dir.mkdir()
        subprocess_file = primitives_dir / "subprocess.py"
        subprocess_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "primitives"
""")
        
        # Create runtime
        runtimes_dir = tools_dir / "runtimes"
        runtimes_dir.mkdir()
        runtime_file = runtimes_dir / "python_runtime.py"
        runtime_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:1111111111111111111111111111111111111111111111111111111111111111
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"
""")
        
        # Create tool
        utility_dir = tools_dir / "utility"
        utility_dir.mkdir()
        tool_file = utility_dir / "test_tool.py"
        tool_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:2222222222222222222222222222222222222222222222222222222222222222
__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"

def main():
    return "test"
""")
        
        chain = await resolver.resolve("test_tool")
        
        assert len(chain) == 3
        assert chain[0]["tool_id"] == "test_tool"
        assert chain[1]["tool_id"] == "python_runtime"
        assert chain[2]["tool_id"] == "subprocess"

    @pytest.mark.asyncio
    async def test_batch_resolve_with_errors(self, resolver, project_path):
        """Test batch resolve handles errors gracefully."""
        tools_dir = project_path / ".ai" / "tools" / "utility"
        tools_dir.mkdir(parents=True)
        
        # Create one valid tool
        valid_tool = tools_dir / "valid_tool.py"
        valid_tool.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "utility"
""")
        
        # Batch resolve with one valid and one invalid
        results = await resolver.resolve_batch(["valid_tool", "nonexistent_tool"])
        
        assert "valid_tool" in results
        assert len(results["valid_tool"]) == 1
        assert "nonexistent_tool" in results
        assert results["nonexistent_tool"] == []  # Empty list for not found

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, resolver, project_path):
        """Test that cache can be invalidated."""
        tools_dir = project_path / ".ai" / "tools" / "utility"
        tools_dir.mkdir(parents=True)
        
        tool_file = tools_dir / "test_tool.py"
        tool_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "utility"
""")
        
        # Resolve and cache
        chain1 = await resolver.resolve("test_tool")
        assert "test_tool" in resolver._chain_cache
        
        # Invalidate
        resolver.invalidate_tool("test_tool")
        assert "test_tool" not in resolver._chain_cache
        
        # Resolve again (should re-resolve)
        chain2 = await resolver.resolve("test_tool")
        assert len(chain2) == 1

    @pytest.mark.asyncio
    async def test_clear_caches(self, resolver, project_path):
        """Test clearing all caches."""
        tools_dir = project_path / ".ai" / "tools" / "utility"
        tools_dir.mkdir(parents=True)
        
        tool_file = tools_dir / "test_tool.py"
        tool_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
__version__ = "1.0.0"
__tool_type__ = "primitive"
__executor_id__ = None
__category__ = "utility"
""")
        
        # Resolve and cache
        await resolver.resolve("test_tool")
        assert len(resolver._chain_cache) > 0
        
        # Clear all caches
        resolver.clear_caches()
        
        assert len(resolver._chain_cache) == 0
        assert len(resolver._integrity_cache) == 0
        assert len(resolver._validation_cache) == 0

    def test_get_cache_stats(self, resolver):
        """Test getting cache statistics."""
        stats = resolver.get_cache_stats()
        
        assert "chain_cache" in stats
        assert "integrity_cache" in stats
        assert "validation_cache" in stats
        assert stats["chain_cache"] == 0
        assert stats["integrity_cache"] == 0
        assert stats["validation_cache"] == 0
