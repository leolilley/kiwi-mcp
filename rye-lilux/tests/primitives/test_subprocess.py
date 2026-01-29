"""
Tests for SubprocessPrimitive.
"""

import asyncio
import os
import pytest
from lilux.primitives.subprocess import SubprocessPrimitive, SubprocessResult


class TestSubprocessPrimitive:
    """Test cases for SubprocessPrimitive."""

    @pytest.fixture
    def primitive(self):
        """Create SubprocessPrimitive instance."""
        return SubprocessPrimitive()

    @pytest.mark.asyncio
    async def test_execute_simple_command(self, primitive):
        """Test executing a simple command."""
        config = {"command": "echo", "args": ["hello", "world"]}
        params = {}

        result = await primitive.execute(config, params)

        assert isinstance(result, SubprocessResult)
        assert result.success is True
        assert "hello world" in result.stdout
        assert result.return_code == 0
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_with_env_vars(self, primitive):
        """Test executing command with environment variables."""
        config = {
            "command": "sh",
            "args": ["-c", "echo $TEST_VAR"],
            "env": {"TEST_VAR": "test_value"},
        }
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        assert "test_value" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_timeout(self, primitive):
        """Test command timeout handling."""
        config = {"command": "sleep", "args": ["2"], "timeout": 1}
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is False
        assert "timed out" in result.stderr
        assert result.return_code == -1

    @pytest.mark.asyncio
    async def test_resolve_env_var_default(self, primitive):
        """Test environment variable resolution with defaults."""
        # Test with existing env var
        os.environ["TEST_EXISTING"] = "existing_value"
        result = primitive._resolve_env_var("${TEST_EXISTING}")
        assert result == "existing_value"

        # Test with default value
        result = primitive._resolve_env_var("${TEST_NONEXISTENT:-default_value}")
        assert result == "default_value"

        # Test with no default
        result = primitive._resolve_env_var("${TEST_NONEXISTENT}")
        assert result == ""

        # Clean up
        del os.environ["TEST_EXISTING"]

    @pytest.mark.asyncio
    async def test_execute_command_not_found(self, primitive):
        """Test handling of command not found error."""
        config = {"command": "nonexistent_command_12345"}
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is False
        assert "Command not found" in result.stderr
        assert result.return_code == -1

    @pytest.mark.asyncio
    async def test_execute_with_input_data(self, primitive):
        """Test executing command with stdin input."""
        config = {"command": "cat", "input_data": "hello from stdin"}
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        assert "hello from stdin" in result.stdout
