"""
Integration tests for PrimitiveExecutor with AuthStore.

Tests that executor properly injects authentication tokens for HTTP requests
when tools declare required_scope.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from lilux.primitives.executor import PrimitiveExecutor, ExecutionResult
from lilux.runtime.auth import AuthStore, AuthenticationRequired
from lilux.runtime.lockfile_store import LockfileStore


@pytest.fixture
def test_project_path(tmp_path):
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / ".ai").mkdir()
    (project_dir / ".ai" / "tools").mkdir()
    return project_dir


@pytest.fixture
def mock_auth_store():
    """Create a mock AuthStore for testing."""
    store = AsyncMock(spec=AuthStore)
    store.get_token = AsyncMock(return_value="test_token_123")
    return store


def create_lockfile_for_chain(project_path: Path, chain: list, category: str = "tools"):
    """Helper to create a lockfile for a mock chain."""
    store = LockfileStore(project_root=project_path)
    tool_id = chain[0]["tool_id"]
    version = chain[0]["version"]
    lockfile = store.freeze(tool_id=tool_id, version=version, category=category, chain=chain)
    store.save(lockfile, category=category, scope="project")


@pytest.mark.asyncio
async def test_executor_injects_auth_for_required_scope(test_project_path, mock_auth_store):
    """Test that executor injects auth token when tool has required_scope."""
    executor = PrimitiveExecutor(test_project_path)

    # Mock the auth store
    executor._auth_store = mock_auth_store

    # Create a mock chain with required_scope
    mock_chain = [
        {
            "tool_id": "test_tool",
            "tool_type": "api",
            "executor_id": "http_client",
            "version": "1.0.0",
            "manifest": {
                "tool_id": "test_tool",
                "tool_type": "api",
                "executor_id": "http_client",
                "required_scope": "registry:write",
                "config": {
                    "method": "POST",
                    "url": "https://api.example.com/test",
                },
            },
            "content_hash": "abc123",
            "files": [{"path": "test.py", "sha256": "hash123"}],
            "file_path": str(test_project_path / ".ai" / "tools" / "test_tool.py"),
            "source": "local",
        },
        {
            "tool_id": "http_client",
            "tool_type": "primitive",
            "executor_id": None,
            "version": "1.0.0",
            "manifest": {
                "tool_id": "http_client",
                "tool_type": "primitive",
            },
            "content_hash": "def456",
            "files": [{"path": "http.py", "sha256": "hash456"}],
            "file_path": "http_client.py",
            "source": "local",
        },
    ]

    # Create lockfile for the chain (strict enforcement)
    create_lockfile_for_chain(test_project_path, mock_chain)

    # Mock the resolver to return our test chain
    executor.resolver.resolve = AsyncMock(return_value=mock_chain)

    # Mock the HTTP primitive execution
    executor.http_client_primitive.execute = AsyncMock(
        return_value=MagicMock(
            success=True,
            body={"result": "success"},
            duration_ms=100,
            error=None,
            status_code=200,
            headers={},
        )
    )

    # Disable integrity and validation for this test
    executor.verify_integrity = False
    executor.validate_chain = False

    # Execute the tool
    result = await executor.execute("test_tool", {})

    # Verify auth token was requested
    mock_auth_store.get_token.assert_called_once_with(service="supabase", scope="registry:write")

    # Verify execution succeeded
    assert result.success


@pytest.mark.asyncio
async def test_executor_no_auth_for_public_tool(test_project_path, mock_auth_store):
    """Test that executor doesn't inject auth for tools without required_scope."""
    executor = PrimitiveExecutor(test_project_path)

    # Mock the auth store
    executor._auth_store = mock_auth_store

    # Create a mock chain WITHOUT required_scope
    mock_chain = [
        {
            "tool_id": "public_tool",
            "tool_type": "api",
            "executor_id": "http_client",
            "version": "1.0.0",
            "manifest": {
                "tool_id": "public_tool",
                "tool_type": "api",
                "executor_id": "http_client",
                # No required_scope
                "config": {
                    "method": "GET",
                    "url": "https://api.example.com/public",
                },
            },
            "content_hash": "abc123",
            "files": [{"path": "test.py", "sha256": "hash123"}],
            "file_path": str(test_project_path / ".ai" / "tools" / "public_tool.py"),
            "source": "local",
        },
        {
            "tool_id": "http_client",
            "tool_type": "primitive",
            "executor_id": None,
            "version": "1.0.0",
            "manifest": {
                "tool_id": "http_client",
                "tool_type": "primitive",
            },
            "content_hash": "def456",
            "files": [{"path": "http.py", "sha256": "hash456"}],
            "file_path": "http_client.py",
            "source": "local",
        },
    ]

    # Create lockfile for the chain (strict enforcement)
    create_lockfile_for_chain(test_project_path, mock_chain)

    # Mock the resolver
    executor.resolver.resolve = AsyncMock(return_value=mock_chain)

    # Mock the HTTP primitive
    executor.http_client_primitive.execute = AsyncMock(
        return_value=MagicMock(
            success=True,
            body={"result": "public_data"},
            duration_ms=50,
            error=None,
            status_code=200,
            headers={},
        )
    )

    # Disable integrity and validation
    executor.verify_integrity = False
    executor.validate_chain = False

    # Execute
    result = await executor.execute("public_tool", {})

    # Verify auth token was NOT requested
    mock_auth_store.get_token.assert_not_called()

    # Verify execution succeeded
    assert result.success


@pytest.mark.asyncio
async def test_executor_handles_missing_auth(test_project_path):
    """Test that executor returns clear error when auth is required but missing."""
    executor = PrimitiveExecutor(test_project_path)

    # Create a mock auth store that raises AuthenticationRequired
    mock_store = AsyncMock(spec=AuthStore)
    mock_store.get_token = AsyncMock(
        side_effect=AuthenticationRequired(
            "No authentication token for supabase. Please sign in with: kiwi auth signin"
        )
    )
    executor._auth_store = mock_store

    # Create a mock chain with required_scope
    mock_chain = [
        {
            "tool_id": "auth_tool",
            "tool_type": "api",
            "executor_id": "http_client",
            "version": "1.0.0",
            "manifest": {
                "tool_id": "auth_tool",
                "tool_type": "api",
                "executor_id": "http_client",
                "required_scope": "registry:write",
                "config": {
                    "method": "POST",
                    "url": "https://api.example.com/auth",
                },
            },
            "content_hash": "abc123",
            "files": [{"path": "test.py", "sha256": "hash123"}],
            "file_path": str(test_project_path / ".ai" / "tools" / "auth_tool.py"),
            "source": "local",
        },
        {
            "tool_id": "http_client",
            "tool_type": "primitive",
            "executor_id": None,
            "version": "1.0.0",
            "manifest": {
                "tool_id": "http_client",
                "tool_type": "primitive",
            },
            "content_hash": "def456",
            "files": [{"path": "http.py", "sha256": "hash456"}],
            "file_path": "http_client.py",
            "source": "local",
        },
    ]

    # Create lockfile for the chain (strict enforcement)
    create_lockfile_for_chain(test_project_path, mock_chain)

    # Mock the resolver
    executor.resolver.resolve = AsyncMock(return_value=mock_chain)

    # Disable integrity and validation
    executor.verify_integrity = False
    executor.validate_chain = False

    # Execute
    result = await executor.execute("auth_tool", {})

    # Verify execution failed with auth error
    assert not result.success
    assert "authentication" in result.error.lower()
    assert "kiwi auth signin" in result.error
    assert result.metadata.get("auth_required") is True


@pytest.mark.asyncio
async def test_extract_required_scope():
    """Test _extract_required_scope helper method."""
    executor = PrimitiveExecutor(Path("/tmp"))

    # Test with required_scope in first tool
    chain = [
        {"tool_id": "tool1", "manifest": {"required_scope": "registry:write"}},
        {"tool_id": "tool2", "manifest": {}},
    ]

    scope = executor._extract_required_scope(chain)
    assert scope == "registry:write"

    # Test with no required_scope
    chain = [{"tool_id": "tool1", "manifest": {}}, {"tool_id": "tool2", "manifest": {}}]

    scope = executor._extract_required_scope(chain)
    assert scope is None

    # Test with required_scope in parent tool
    chain = [
        {"tool_id": "tool1", "manifest": {}},
        {"tool_id": "tool2", "manifest": {"required_scope": "admin:read"}},
    ]

    scope = executor._extract_required_scope(chain)
    assert scope == "admin:read"
