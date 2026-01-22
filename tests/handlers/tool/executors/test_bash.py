"""
Tests for BashExecutor
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest

from kiwi_mcp.handlers.tool.executors.bash import BashExecutor
from kiwi_mcp.handlers.tool.executors.base import ExecutionResult


@pytest.fixture
def bash_executor():
    """Create a BashExecutor instance."""
    return BashExecutor()


@pytest.fixture
def mock_manifest():
    """Create a mock tool manifest."""
    manifest = Mock()
    manifest.tool_type = "bash"
    manifest.executor_config = {}
    return manifest


@pytest.fixture
def temp_script():
    """Create a temporary bash script."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write("#!/bin/bash\necho Hello from $KIWI_NAME")
        script_path = Path(f.name)

    yield script_path

    # Cleanup
    script_path.unlink()


class TestBashExecutor:
    """Test suite for BashExecutor."""

    def test_can_execute_bash_type(self, bash_executor, mock_manifest):
        """Test that executor can handle bash tool type."""
        mock_manifest.tool_type = "bash"
        assert bash_executor.can_execute(mock_manifest) is True

    def test_cannot_execute_other_types(self, bash_executor, mock_manifest):
        """Test that executor rejects non-bash tool types."""
        mock_manifest.tool_type = "python"
        assert bash_executor.can_execute(mock_manifest) is False

        mock_manifest.tool_type = "api"
        assert bash_executor.can_execute(mock_manifest) is False

    @pytest.mark.asyncio
    async def test_execute_with_env_vars(self, bash_executor, mock_manifest, temp_script):
        """Test that executor runs script with environment variables."""
        mock_manifest.file_path = temp_script.parent / "tool.yaml"
        mock_manifest.executor_config = {"entrypoint": temp_script.name, "timeout": 10}

        params = {"name": "World"}

        with patch.object(bash_executor, "_resolve_script", return_value=temp_script):
            result = await bash_executor.execute(mock_manifest, params)

        assert result.success is True
        assert "Hello from World" in result.output

    @pytest.mark.asyncio
    async def test_execute_with_missing_required_command(self, bash_executor, mock_manifest):
        """Test that executor fails when required command is missing."""
        mock_manifest.executor_config = {"requires": {"commands": ["nonexistent_command_xyz"]}}
        mock_manifest.file_path = "/fake/path/tool.yaml"  # Add file_path for _resolve_script

        result = await bash_executor.execute(mock_manifest, {})

        assert result.success is False
        assert "Required command not found: nonexistent_command_xyz" in result.error

    @pytest.mark.asyncio
    async def test_execute_timeout(self, bash_executor, mock_manifest):
        """Test that executor times out correctly."""
        # Create a script that sleeps longer than timeout
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\nsleep 5")
            sleep_script = Path(f.name)

        try:
            mock_manifest.executor_config = {"timeout": 1}  # 1 second timeout

            with patch.object(bash_executor, "_resolve_script", return_value=sleep_script):
                result = await bash_executor.execute(mock_manifest, {})

            assert result.success is False
            assert "timed out after 1s" in result.error
        finally:
            sleep_script.unlink()

    @pytest.mark.asyncio
    async def test_execute_script_error(self, bash_executor, mock_manifest):
        """Test that executor handles script execution errors."""
        # Create a script that exits with error
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\necho 'Error message' >&2\nexit 1")
            error_script = Path(f.name)

        try:
            mock_manifest.executor_config = {}

            with patch.object(bash_executor, "_resolve_script", return_value=error_script):
                result = await bash_executor.execute(mock_manifest, {})

            assert result.success is False
            assert "Error message" in result.error
        finally:
            error_script.unlink()

    def test_resolve_script_default_entrypoint(self, bash_executor):
        """Test script resolution with default entrypoint."""
        manifest = Mock()
        manifest.file_path = Path("/path/to/tool.yaml")
        manifest.executor_config = {}

        script_path = bash_executor._resolve_script(manifest)
        assert script_path == Path("/path/to") / "script.sh"

    def test_resolve_script_custom_entrypoint(self, bash_executor):
        """Test script resolution with custom entrypoint."""
        manifest = Mock()
        manifest.file_path = Path("/path/to/tool.yaml")
        manifest.executor_config = {"entrypoint": "custom.sh"}

        script_path = bash_executor._resolve_script(manifest)
        assert script_path == Path("/path/to") / "custom.sh"
