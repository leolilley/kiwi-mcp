"""Tests for MCP schema cache functionality."""

import time
import pytest
from kiwi_mcp.mcp.schema_cache import SchemaCache, CacheEntry


@pytest.fixture
def cache():
    """Create a fresh schema cache with 1 second TTL for testing."""
    return SchemaCache(ttl_seconds=1.0)


def test_cache_entry_is_valid():
    """Test CacheEntry validity checking."""
    current_time = time.time()

    # Fresh entry should be valid
    entry = CacheEntry(schemas=[], fetched_at=current_time)
    assert entry.is_valid(ttl=3600.0) is True

    # Old entry should be invalid
    old_entry = CacheEntry(schemas=[], fetched_at=current_time - 3700)
    assert old_entry.is_valid(ttl=3600.0) is False


def test_cache_get_miss():
    """Test cache get when no entry exists."""
    cache = SchemaCache()
    result = cache.get("test_mcp")
    assert result is None


def test_cache_set_and_get():
    """Test setting and getting cache entries."""
    cache = SchemaCache()
    schemas = [{"name": "tool1"}, {"name": "tool2"}]

    cache.set("test_mcp", schemas)
    result = cache.get("test_mcp")

    assert result == schemas


def test_cache_get_with_expired_entry(cache):
    """Test that expired entries are not returned."""
    schemas = [{"name": "tool1"}]
    cache.set("test_mcp", schemas)

    # Entry should be valid immediately
    result = cache.get("test_mcp")
    assert result == schemas

    # Wait for expiry (TTL is 1 second)
    time.sleep(1.1)

    # Entry should now be expired
    result = cache.get("test_mcp")
    assert result is None


def test_cache_force_refresh():
    """Test force refresh bypasses cache."""
    cache = SchemaCache(ttl_seconds=3600)  # Long TTL
    schemas = [{"name": "tool1"}]
    cache.set("test_mcp", schemas)

    # Normal get should return cached value
    result = cache.get("test_mcp")
    assert result == schemas

    # Force refresh should return None even with valid cache
    result = cache.get("test_mcp", force_refresh=True)
    assert result is None


def test_cache_invalidate_specific():
    """Test invalidating specific cache entry."""
    cache = SchemaCache()
    schemas1 = [{"name": "tool1"}]
    schemas2 = [{"name": "tool2"}]

    cache.set("mcp1", schemas1)
    cache.set("mcp2", schemas2)

    # Both should be present
    assert cache.get("mcp1") == schemas1
    assert cache.get("mcp2") == schemas2

    # Invalidate one
    cache.invalidate("mcp1")

    # Only mcp1 should be gone
    assert cache.get("mcp1") is None
    assert cache.get("mcp2") == schemas2


def test_cache_invalidate_all():
    """Test invalidating all cache entries."""
    cache = SchemaCache()
    schemas1 = [{"name": "tool1"}]
    schemas2 = [{"name": "tool2"}]

    cache.set("mcp1", schemas1)
    cache.set("mcp2", schemas2)

    # Both should be present
    assert cache.get("mcp1") == schemas1
    assert cache.get("mcp2") == schemas2

    # Invalidate all
    cache.invalidate()

    # Both should be gone
    assert cache.get("mcp1") is None
    assert cache.get("mcp2") is None


def test_cache_invalidate_nonexistent():
    """Test invalidating non-existent entry doesn't error."""
    cache = SchemaCache()
    # Should not raise any exception
    cache.invalidate("nonexistent")


def test_cache_multiple_sets_updates_entry():
    """Test that multiple sets to same key updates the entry."""
    cache = SchemaCache()

    schemas1 = [{"name": "tool1"}]
    schemas2 = [{"name": "tool2"}]

    # Set first value
    cache.set("test_mcp", schemas1)
    assert cache.get("test_mcp") == schemas1

    # Update with new value
    cache.set("test_mcp", schemas2)
    assert cache.get("test_mcp") == schemas2
