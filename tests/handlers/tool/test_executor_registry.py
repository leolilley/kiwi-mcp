"""Tests for ExecutorRegistry."""

import pytest
from unittest.mock import Mock

from kiwi_mcp.handlers.tool.executors import ExecutorRegistry, ToolExecutor
from kiwi_mcp.handlers.tool.manifest import ToolManifest


class MockExecutor(ToolExecutor):
    """Mock executor for testing."""

    def __init__(self, tool_type: str):
        self.tool_type = tool_type

    async def execute(self, manifest: ToolManifest, params: dict):
        return {"status": "success", "output": f"Executed {manifest.tool_id}"}

    def can_execute(self, manifest: ToolManifest) -> bool:
        return manifest.tool_type == self.tool_type


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before each test."""
    ExecutorRegistry.clear()
    yield
    ExecutorRegistry.clear()


def test_executor_registry_register_and_get():
    """Test registering and retrieving executors."""
    python_executor = MockExecutor("python")
    bash_executor = MockExecutor("bash")

    # Register executors
    ExecutorRegistry.register("python", python_executor)
    ExecutorRegistry.register("bash", bash_executor)

    # Retrieve executors
    assert ExecutorRegistry.get("python") == python_executor
    assert ExecutorRegistry.get("bash") == bash_executor
    assert ExecutorRegistry.get("unknown") is None


def test_executor_registry_list_types():
    """Test listing registered executor types."""
    python_executor = MockExecutor("python")
    bash_executor = MockExecutor("bash")

    # Initially empty
    assert ExecutorRegistry.list_types() == []

    # Register executors
    ExecutorRegistry.register("python", python_executor)
    ExecutorRegistry.register("bash", bash_executor)

    # Should list registered types
    types = ExecutorRegistry.list_types()
    assert "python" in types
    assert "bash" in types
    assert len(types) == 2


def test_executor_registry_clear():
    """Test clearing registry."""
    python_executor = MockExecutor("python")
    ExecutorRegistry.register("python", python_executor)

    assert len(ExecutorRegistry.list_types()) == 1

    ExecutorRegistry.clear()

    assert len(ExecutorRegistry.list_types()) == 0
    assert ExecutorRegistry.get("python") is None


def test_executor_registry_overwrite():
    """Test that registering same type overwrites previous executor."""
    executor1 = MockExecutor("python")
    executor2 = MockExecutor("python")

    ExecutorRegistry.register("python", executor1)
    assert ExecutorRegistry.get("python") == executor1

    ExecutorRegistry.register("python", executor2)
    assert ExecutorRegistry.get("python") == executor2
    assert ExecutorRegistry.get("python") != executor1
