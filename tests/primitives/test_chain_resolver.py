"""
Tests for ChainResolver - local filesystem chain resolution.
"""

import pytest
from pathlib import Path
from kiwi_mcp.primitives.executor import ChainResolver, ToolNotFoundError


class TestChainResolver:
    """Test ChainResolver functionality with local filesystem."""

    @pytest.fixture
    def project_path(self, tmp_path):
        """Create a test project structure."""
        project = tmp_path / "test_project"
        project.mkdir()
        
        # Create .ai/tools structure
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
        runtime_file = runtimes_dir / "python_runtime.py"
        runtime_file.write_text("""# kiwi-mcp:validated:2026-01-01T00:00:00Z:1111111111111111111111111111111111111111111111111111111111111111
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"
""")
        
        # Create test tool
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
        
        return project

    @pytest.fixture
    def resolver(self, project_path):
        """ChainResolver instance with test project."""
        return ChainResolver(project_path)

    @pytest.mark.asyncio
    async def test_resolve_single_chain(self, resolver):
        """Test resolving a single chain from local files."""
        chain = await resolver.resolve("test_tool")
        
        assert len(chain) == 3
        assert chain[0]["tool_id"] == "test_tool"
        assert chain[0]["tool_type"] == "python"
        assert chain[0]["executor_id"] == "python_runtime"
        
        assert chain[1]["tool_id"] == "python_runtime"
        assert chain[1]["tool_type"] == "runtime"
        assert chain[1]["executor_id"] == "subprocess"
        
        assert chain[2]["tool_id"] == "subprocess"
        assert chain[2]["tool_type"] == "primitive"
        assert chain[2]["executor_id"] is None

    @pytest.mark.asyncio
    async def test_resolve_chain_caching(self, resolver):
        """Test that resolved chains are cached."""
        # First call
        chain1 = await resolver.resolve("test_tool")
        
        # Second call should use cache
        chain2 = await resolver.resolve("test_tool")
        
        assert chain1 == chain2
        assert "test_tool" in resolver._chain_cache

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_tool(self, resolver):
        """Test that nonexistent tools raise ToolNotFoundError."""
        with pytest.raises(ToolNotFoundError) as exc_info:
            await resolver.resolve("nonexistent_tool")
        
        assert "not found locally" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_resolve_batch(self, resolver):
        """Test batch resolving multiple chains."""
        results = await resolver.resolve_batch(["test_tool"])
        
        assert "test_tool" in results
        assert len(results["test_tool"]) == 3

    @pytest.mark.asyncio
    async def test_resolve_batch_with_cache(self, resolver):
        """Test batch resolve with some items already cached."""
        # Cache one item first
        chain = await resolver.resolve("test_tool")
        resolver._chain_cache["test_tool"] = chain
        
        # Batch resolve should use cache
        results = await resolver.resolve_batch(["test_tool"])
        
        assert results["test_tool"] == chain

    def test_merge_configs_child_overrides(self, resolver):
        """Test config merging where child overrides parent."""
        chain = [
            {
                "tool_id": "test_tool",
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
            "timeout": 120,  # From leaf (test_tool)
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

    @pytest.mark.asyncio
    async def test_resolve_requires_project_path(self):
        """Test that project_path is required."""
        # None raises TypeError when trying to create Path(None)
        with pytest.raises((ValueError, TypeError)):
            ChainResolver(None)

    @pytest.mark.asyncio
    async def test_chain_includes_content_hash(self, resolver):
        """Test that resolved chains include content_hash from signatures."""
        chain = await resolver.resolve("test_tool")
        
        for link in chain:
            assert "content_hash" in link
            assert len(link["content_hash"]) == 64  # SHA256 hex

    @pytest.mark.asyncio
    async def test_chain_includes_file_path(self, resolver):
        """Test that resolved chains include file_path."""
        chain = await resolver.resolve("test_tool")
        
        for link in chain:
            assert "file_path" in link
            assert link["source"] == "local"
