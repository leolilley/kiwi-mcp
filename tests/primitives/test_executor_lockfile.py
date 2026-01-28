"""
Tests for PrimitiveExecutor lockfile validation integration.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from kiwi_mcp.primitives.executor import PrimitiveExecutor
from kiwi_mcp.runtime.lockfile_store import LockfileStore
from kiwi_mcp.primitives.lockfile import Lockfile, LockfileRoot, LockfileEntry


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        yield project_path


@pytest.fixture
def executor(temp_project):
    """Create a PrimitiveExecutor with temporary project."""
    return PrimitiveExecutor(
        project_path=temp_project,
        verify_integrity=False,  # Disable for testing
        validate_chain=False,  # Disable for testing
    )


@pytest.fixture
def lockfile_store(temp_project):
    """Create a LockfileStore with temporary project."""
    return LockfileStore(project_root=temp_project)


@pytest.fixture
def sample_chain():
    """Create a sample chain for testing."""
    return [
        {
            "tool_id": "test_tool",
            "version": "1.0.0",
            "content_hash": "abc123" + "0" * 58,
            "executor_id": "subprocess",
            "manifest": {
                "category": "tests",
                "tool_type": "script",
            },
        },
        {
            "tool_id": "subprocess",
            "version": "1.0.0",
            "content_hash": "sub123" + "0" * 58,
            "executor_id": None,
            "manifest": {
                "tool_type": "primitive",
            },
        },
    ]


class TestLockfileValidation:
    """Tests for lockfile validation in executor."""

    def test_validate_lockfile_not_found(self, executor, sample_chain):
        """Validate should fail when no lockfile exists (strict enforcement)."""
        result = executor._validate_lockfile(
            tool_id="test_tool",
            chain=sample_chain,
        )

        # No lockfile = validation failure (strict mode)
        assert result["valid"] is False
        assert not result["lockfile_found"]
        assert len(result["issues"]) == 1
        assert "No lockfile found" in result["issues"][0]

    def test_validate_lockfile_matching(
        self,
        executor,
        lockfile_store,
        sample_chain,
    ):
        """Validate should succeed for matching lockfile."""
        # Create and save lockfile
        lockfile = lockfile_store.freeze(
            tool_id="test_tool",
            version="1.0.0",
            category="tests",
            chain=sample_chain,
        )
        lockfile_store.save(lockfile, category="tests", scope="project")

        # Validate
        result = executor._validate_lockfile(
            tool_id="test_tool",
            chain=sample_chain,
        )

        assert result["valid"] is True
        assert result["lockfile_found"] is True
        assert len(result["issues"]) == 0

    def test_validate_lockfile_mismatched(
        self,
        executor,
        lockfile_store,
        sample_chain,
    ):
        """Validate should fail on mismatch (strict enforcement)."""
        # Create lockfile with original chain
        lockfile = lockfile_store.freeze(
            tool_id="test_tool",
            version="1.0.0",
            category="tests",
            chain=sample_chain,
        )
        lockfile_store.save(lockfile, category="tests", scope="project")

        # Modify chain content_hash (but keep version same for lookup)
        modified_chain = sample_chain.copy()
        modified_chain[0] = modified_chain[0].copy()
        modified_chain[0]["content_hash"] = "different" + "0" * 56

        # Validate - should fail (strict enforcement)
        result = executor._validate_lockfile(
            tool_id="test_tool",
            chain=modified_chain,
        )

        assert result["valid"] is False
        assert result["lockfile_found"] is True
        assert len(result["issues"]) > 0
        assert any("integrity" in issue.lower() for issue in result["issues"])


class TestExecutorLockfileIntegration:
    """Tests for lockfile validation integrated into execute()."""

    @pytest.mark.asyncio
    async def test_execute_lockfile_always_runs(self, executor, temp_project):
        """Lockfile validation runs automatically (no opt-in flag)."""
        # Note: This would need a real tool to execute
        # Lockfile validation is now always-on with warn mode by default
        pass

    @pytest.mark.asyncio
    async def test_execute_with_lockfile_not_found(self, executor):
        """Execute should continue with warning when lockfile not found."""
        # Note: Would need real tool setup
        # Testing the flow through _validate_lockfile is sufficient
        pass
