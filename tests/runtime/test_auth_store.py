"""
Unit tests for AuthStore.

Tests the kernel-level authentication store with OS keychain integration.
"""

import pytest
import keyring
from keyring.backends.fail import Keyring as FailKeyring
from datetime import datetime, timedelta, timezone
from kiwi_mcp.runtime.auth import AuthStore, AuthenticationRequired, RefreshError


@pytest.fixture(autouse=True, scope="session")
def setup_test_keyring():
    """Configure keyring to use in-memory backend for testing."""
    # Use the in-memory backend from keyrings.alt
    from keyrings.alt.file import PlaintextKeyring

    keyring.set_keyring(PlaintextKeyring())


@pytest.fixture
def auth_store():
    """Create an AuthStore instance for testing."""
    return AuthStore(service_name="test_kiwi_mcp")


@pytest.fixture
def cleanup_auth_store(auth_store):
    """Cleanup fixture that removes test tokens after each test."""
    yield auth_store
    # Cleanup after test
    try:
        auth_store.clear_token("test_service")
    except Exception:
        pass


@pytest.mark.asyncio
async def test_set_and_get_token(cleanup_auth_store):
    """Test storing and retrieving token."""
    store = cleanup_auth_store

    # Set token
    store.set_token(
        service="test_service",
        access_token="test_token_123",
        expires_in=3600,
        scopes=["read", "write"],
    )

    # Get token
    token = await store.get_token("test_service")
    assert token == "test_token_123"


@pytest.mark.asyncio
async def test_set_token_with_refresh(cleanup_auth_store):
    """Test storing token with refresh token."""
    store = cleanup_auth_store

    store.set_token(
        service="test_service",
        access_token="access_token_123",
        refresh_token="refresh_token_456",
        expires_in=3600,
        scopes=["admin"],
    )

    token = await store.get_token("test_service")
    assert token == "access_token_123"

    # Check metadata includes refresh token flag
    metadata = store.get_cached_metadata("test_service")
    assert metadata is not None
    assert metadata["has_refresh_token"] is True
    assert "admin" in metadata["scopes"]


@pytest.mark.asyncio
async def test_missing_token_raises_error(auth_store):
    """Test that missing token raises AuthenticationRequired."""
    with pytest.raises(AuthenticationRequired) as exc_info:
        await auth_store.get_token("nonexistent_service")

    assert "No authentication token" in str(exc_info.value)
    assert "kiwi auth signin" in str(exc_info.value)


@pytest.mark.asyncio
async def test_is_authenticated(cleanup_auth_store):
    """Test is_authenticated check."""
    store = cleanup_auth_store

    # Not authenticated
    assert not store.is_authenticated("test_service")

    # Set token
    store.set_token(service="test_service", access_token="test_token", expires_in=3600)

    # Now authenticated
    assert store.is_authenticated("test_service")


@pytest.mark.asyncio
async def test_cache_metadata(cleanup_auth_store):
    """Test that metadata is cached."""
    store = cleanup_auth_store

    store.set_token(service="test_service", access_token="test_token", scopes=["admin", "user"])

    metadata = store.get_cached_metadata("test_service")
    assert metadata is not None
    assert "admin" in metadata["scopes"]
    assert "user" in metadata["scopes"]
    assert "access_token" not in metadata  # Never expose token
    assert "refresh_token" not in metadata  # Never expose token


@pytest.mark.asyncio
async def test_clear_token(cleanup_auth_store):
    """Test clearing token removes it from keychain and cache."""
    store = cleanup_auth_store

    store.set_token(service="test_service", access_token="test_token", expires_in=3600)

    # Verify token exists
    assert store.is_authenticated("test_service")

    # Clear token
    store.clear_token("test_service")

    # Verify token is gone
    assert not store.is_authenticated("test_service")

    # Should raise error when trying to get
    with pytest.raises(AuthenticationRequired):
        await store.get_token("test_service")


@pytest.mark.asyncio
async def test_expired_token_without_refresh(cleanup_auth_store):
    """Test expired token without refresh token raises error."""
    store = cleanup_auth_store

    # Set token that expires immediately
    store.set_token(
        service="test_service",
        access_token="test_token",
        expires_in=-1,  # Already expired
        refresh_token=None,
    )

    # Should raise error for expired token
    with pytest.raises(AuthenticationRequired) as exc_info:
        await store.get_token("test_service")

    assert "expired" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_scope_validation(cleanup_auth_store):
    """Test that token scope is validated."""
    store = cleanup_auth_store

    store.set_token(
        service="test_service", access_token="test_token", expires_in=3600, scopes=["read"]
    )

    # Should work for matching scope
    token = await store.get_token("test_service", scope="read")
    assert token == "test_token"

    # Should work without scope
    token = await store.get_token("test_service")
    assert token == "test_token"

    # Should fail for missing scope
    with pytest.raises(AuthenticationRequired) as exc_info:
        await store.get_token("test_service", scope="write")

    assert "scope" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_token_caching(cleanup_auth_store):
    """Test that tokens are cached during runtime."""
    store = cleanup_auth_store

    # Set token
    store.set_token(service="test_service", access_token="test_token", expires_in=3600)

    # First get - from cache
    token1 = await store.get_token("test_service")

    # Second get - should use cache
    token2 = await store.get_token("test_service")

    assert token1 == token2 == "test_token"

    # Verify cache exists
    metadata = store.get_cached_metadata("test_service")
    assert metadata is not None


@pytest.mark.asyncio
async def test_multiple_services(cleanup_auth_store):
    """Test managing tokens for multiple services."""
    store = cleanup_auth_store

    # Set tokens for different services
    store.set_token(service="service1", access_token="token1", expires_in=3600)

    store.set_token(service="service2", access_token="token2", expires_in=3600)

    # Get tokens
    token1 = await store.get_token("service1")
    token2 = await store.get_token("service2")

    assert token1 == "token1"
    assert token2 == "token2"

    # Clear one service
    store.clear_token("service1")

    # service1 should be gone
    with pytest.raises(AuthenticationRequired):
        await store.get_token("service1")

    # service2 should still work
    token2_again = await store.get_token("service2")
    assert token2_again == "token2"

    # Cleanup
    store.clear_token("service2")


@pytest.mark.asyncio
async def test_refresh_not_implemented(cleanup_auth_store):
    """Test that refresh token logic raises NotImplementedError."""
    store = cleanup_auth_store

    # Set expired token with refresh token
    store.set_token(
        service="test_service",
        access_token="old_token",
        refresh_token="refresh_token",
        expires_in=-1,  # Expired
    )

    # Should raise RefreshError (not implemented)
    with pytest.raises(AuthenticationRequired) as exc_info:
        await store.get_token("test_service")

    # Should mention refresh failed
    assert "refresh" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_metadata_does_not_expose_tokens(cleanup_auth_store):
    """Test that get_cached_metadata never exposes actual tokens."""
    store = cleanup_auth_store

    store.set_token(
        service="test_service",
        access_token="secret_access_token",
        refresh_token="secret_refresh_token",
        expires_in=3600,
        scopes=["admin"],
    )

    metadata = store.get_cached_metadata("test_service")

    # Should have metadata
    assert metadata is not None
    assert "expires_at" in metadata
    assert "scopes" in metadata
    assert "created_at" in metadata
    assert metadata["has_refresh_token"] is True

    # Should NEVER have actual tokens
    assert "access_token" not in metadata
    assert "refresh_token" not in metadata
    assert "secret_access_token" not in str(metadata)
    assert "secret_refresh_token" not in str(metadata)
