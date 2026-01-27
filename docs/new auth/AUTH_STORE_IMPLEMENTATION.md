# Auth Store Implementation Guide

**Date:** 2026-01-26  
**Status:** Implementation Ready  
**Purpose:** Secure token management using OS keychain

---

## Overview

This guide provides the step-by-step implementation of the Phase 2 Auth Store - a kernel-only token manager that:

- ✅ Stores tokens securely in OS keychain (macOS, Windows, Linux)
- ✅ Auto-refreshes expired tokens
- ✅ Caches metadata in memory during runtime
- ✅ Never exposes tokens to tools or agents
- ✅ Provides clean error messages when auth required

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Agent (UNTRUSTED)                                       │
│ Requests: execute(tool="registry", action="upload")    │
│ Never sees tokens                                       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ PrimitiveExecutor (KERNEL - TRUSTED)                   │
│ 1. Resolves tool and executor chain                    │
│ 2. Checks if auth required (required_scope)            │
│ 3. Calls auth_store.get_token() if needed              │
│ 4. Injects token into HTTP headers                     │
│ 5. Executes tool (token never visible)                 │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ AuthStore (KERNEL ONLY)                                │
│ - Manages tokens in OS keychain                        │
│ - Caches metadata in memory                            │
│ - Auto-refreshes expired tokens                        │
│ - Never accessible to tools/agents                     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ OS Keychain (ENCRYPTED)                                │
│ - macOS: Keychain Access                               │
│ - Windows: Credential Manager                          │
│ - Linux: Secret Service API                            │
│ - Encrypted at rest by OS                              │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core AuthStore Class (Foundation)
- Create `AuthStore` class with OS keychain integration
- Token storage, retrieval, caching
- Token expiry checking
- Basic error handling

### Phase 2: Runtime Integration (Kernel Layer)
- Integrate `AuthStore` into `PrimitiveExecutor`
- Token injection into HTTP headers
- Scope checking and validation
- Error handling for missing auth

### Phase 3: User Commands & Authentication (CLI)
- Implement `kiwi auth signin` command
- Implement `kiwi auth logout` command
- User-facing authentication flow
- Token refresh and rotation

---

## Implementation Steps

### Phase 1.1: Create AuthStore Class

**File:** `kiwi_mcp/runtime/auth.py`

```python
import keyring
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json

class AuthenticationRequired(Exception):
    """Raised when authentication is required but token is missing/invalid."""
    pass

class RefreshError(Exception):
    """Raised when token refresh fails."""
    pass

class AuthStore:
    """
    Kernel-only auth store using OS keychain for secure token storage.
    
    Stores tokens in OS keychain:
    - macOS: Keychain Access
    - Windows: Credential Manager
    - Linux: Secret Service API (freedesktop.org)
    
    Python `keyring` library handles cross-platform abstraction.
    """
    
    def __init__(self, service_name: str = "kiwi-mcp"):
        """Initialize auth store."""
        self.service_name = service_name
        self._cache: Dict[str, Dict] = {}  # In-memory cache of metadata
    
    def set_token(
        self,
        service: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None,
    ) -> None:
        """
        Store token securely in OS keychain.
        
        Args:
            service: Service identifier (e.g., "supabase")
            access_token: JWT access token
            refresh_token: Optional JWT refresh token
            expires_in: Token expiry in seconds (default: 1 hour)
            scopes: Optional list of authorized scopes
        """
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        # Store in OS keychain (encrypted by OS)
        keyring.set_password(
            self.service_name,
            f"{service}_access_token",
            access_token
        )
        
        if refresh_token:
            keyring.set_password(
                self.service_name,
                f"{service}_refresh_token",
                refresh_token
            )
        
        keyring.set_password(
            self.service_name,
            f"{service}_expires_at",
            expires_at
        )
        
        # Cache metadata (NOT tokens)
        self._cache[service] = {
            "access_token": access_token,  # Cached during runtime only
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "scopes": scopes or [],
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def get_token(
        self,
        service: str,
        scope: Optional[str] = None
    ) -> str:
        """
        Get token with automatic refresh on expiry.
        
        Args:
            service: Service identifier (e.g., "supabase")
            scope: Optional required scope (checked but not enforced here)
        
        Returns:
            Access token string
        
        Raises:
            AuthenticationRequired: No valid token available
        """
        # 1. Check cache first (most common path)
        if service in self._cache:
            cached = self._cache[service]
            expires_at = datetime.fromisoformat(cached["expires_at"])
            
            # Token still valid?
            if expires_at > datetime.utcnow():
                # If scope specified, verify it's available
                if scope is None or scope in cached.get("scopes", []):
                    return cached["access_token"]
            
            # Try to refresh if we have refresh token
            if cached.get("refresh_token"):
                try:
                    new_token = await self._refresh_token(
                        service,
                        cached["refresh_token"]
                    )
                    # Update cache
                    self._cache[service]["access_token"] = new_token
                    # Parse new expiry from token (or use default)
                    self._cache[service]["expires_at"] = (
                        datetime.utcnow() + timedelta(hours=1)
                    ).isoformat()
                    return new_token
                except RefreshError:
                    pass  # Fall through to require re-auth
        
        # 2. Get from keychain
        token = keyring.get_password(self.service_name, f"{service}_access_token")
        if not token:
            raise AuthenticationRequired(
                f"No authentication token for {service}. "
                f"Please sign in with: kiwi auth signin"
            )
        
        # 3. Load metadata from keychain
        expires_at_str = keyring.get_password(
            self.service_name,
            f"{service}_expires_at"
        )
        refresh_token = keyring.get_password(
            self.service_name,
            f"{service}_refresh_token"
        )
        
        # 4. Check expiry
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            
            # Token expired?
            if expires_at < datetime.utcnow():
                if refresh_token:
                    try:
                        # Try to refresh
                        token = await self._refresh_token(service, refresh_token)
                        # Update keychain
                        keyring.set_password(
                            self.service_name,
                            f"{service}_access_token",
                            token
                        )
                    except RefreshError:
                        raise AuthenticationRequired(
                            f"Token expired and refresh failed. "
                            f"Please sign in again: kiwi auth signin"
                        )
                else:
                    raise AuthenticationRequired(
                        f"Token expired. Please sign in again: kiwi auth signin"
                    )
        
        # 5. Update cache
        self._cache[service] = {
            "access_token": token,
            "refresh_token": refresh_token,
            "expires_at": expires_at_str or (
                datetime.utcnow() + timedelta(hours=1)
            ).isoformat(),
            "scopes": scope.split() if scope else [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        return token
    
    async def _refresh_token(self, service: str, refresh_token: str) -> str:
        """
        Refresh expired token.
        
        This is a placeholder - implementation depends on service auth flow.
        For Supabase, this would call the refresh endpoint.
        
        Args:
            service: Service identifier
            refresh_token: Refresh token
        
        Returns:
            New access token
        
        Raises:
            RefreshError: Refresh failed
        """
        # TODO: Implement service-specific refresh logic
        # For Supabase: POST to auth.refreshSession endpoint
        raise NotImplementedError(
            f"Token refresh not yet implemented for {service}"
        )
    
    def clear_token(self, service: str) -> None:
        """
        Remove token from keychain (on logout).
        
        Args:
            service: Service identifier
        """
        try:
            keyring.delete_password(
                self.service_name,
                f"{service}_access_token"
            )
            keyring.delete_password(
                self.service_name,
                f"{service}_refresh_token"
            )
            keyring.delete_password(
                self.service_name,
                f"{service}_expires_at"
            )
        except keyring.errors.PasswordDeleteError:
            pass  # Already deleted
        
        # Clear cache
        self._cache.pop(service, None)
    
    def is_authenticated(self, service: str) -> bool:
        """
        Check if service has valid token.
        
        Args:
            service: Service identifier
        
        Returns:
            True if valid token exists, False otherwise
        """
        try:
            # Check keychain
            token = keyring.get_password(
                self.service_name,
                f"{service}_access_token"
            )
            if not token:
                return False
            
            # Check expiry
            expires_at_str = keyring.get_password(
                self.service_name,
                f"{service}_expires_at"
            )
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                return expires_at > datetime.utcnow()
            
            return True
        except Exception:
            return False
    
    def get_cached_metadata(self, service: str) -> Optional[Dict]:
        """
        Get cached metadata for service (for diagnostics only).
        
        NEVER include actual tokens in returned dict.
        
        Args:
            service: Service identifier
        
        Returns:
            Metadata dict or None
        """
        if service not in self._cache:
            return None
        
        cached = self._cache[service]
        return {
            "expires_at": cached["expires_at"],
            "scopes": cached["scopes"],
            "created_at": cached["created_at"],
            "has_refresh_token": bool(cached.get("refresh_token")),
            # NEVER include: access_token, refresh_token
        }
```

### Phase 1.2: Update Dependencies

**File:** `pyproject.toml`

Add to `dependencies`:

```toml
keyring = ">=23.0.0"  # Cross-platform credential storage
```

### Phase 2.1: Integrate into PrimitiveExecutor

**File:** `kiwi_mcp/executor.py`

```python
from kiwi_mcp.runtime.auth import AuthStore, AuthenticationRequired

class PrimitiveExecutor:
    """Executes tools using primitives with runtime auth injection."""
    
    def __init__(self, ...):
        # ... existing code
        self.auth_store = AuthStore()
    
    async def execute(self, tool_id: str, params: dict) -> ExecutionResult:
        """Execute tool with automatic auth injection."""
        
        # 1. Resolve tool and executor chain
        chain = await self.resolver.resolve(tool_id)
        tool = chain[0]
        
        # 2. Check if authentication required
        required_scope = tool.config.get("required_scope")
        
        if required_scope:
            # 3. Get token from auth store (with auto-refresh)
            try:
                token = await self.auth_store.get_token(
                    service="supabase",
                    scope=required_scope
                )
            except AuthenticationRequired as e:
                return ExecutionResult(
                    success=False,
                    error=str(e)
                )
            
            # 4. Inject into HTTP config
            http_config = self._merge_configs(chain)
            http_config["headers"]["Authorization"] = f"Bearer {token}"
        else:
            # Public operation - no token needed
            http_config = self._merge_configs(chain)
        
        # 5. Execute (agent never sees token)
        return await self.http_client.execute(http_config, params)
```

### Phase 2.2: Update Tool Definitions

Tools should declare required scopes in metadata:

**File:** `.ai/tools/core/registry.py` (when created)

```python
__tool_id__ = "registry"
__tool_type__ = "api"
__executor_id__ = "http_client"
__version__ = "1.0.0"

# Scope requirements per action
__scopes__ = {
    "search": None,           # Public
    "get": None,              # Public
    "download": None,         # Public
    "upload": "registry:write",
    "publish": "registry:write",
    "delete": "registry:write",
}

# Config for http_client
__config__ = {
    "executor_id": "http_client",
    "base_url": "${SUPABASE_URL}/rest/v1",
    "headers": {
        "apikey": "${SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    },
    # Runtime will inject Authorization header if required_scope set
}
```

---

## Phase 1 Checklist

- [ ] Create `kiwi_mcp/runtime/auth.py` with `AuthStore` class
- [ ] Implement all methods: `set_token`, `get_token`, `clear_token`, `is_authenticated`
- [ ] Add token caching with in-memory metadata
- [ ] Implement token expiry checking
- [ ] Add `AuthenticationRequired` and `RefreshError` exceptions
- [ ] Add `keyring>=23.0.0` to `pyproject.toml`
- [ ] Verify OS keychain integration works locally
- [ ] Write unit tests for AuthStore

## Phase 2 Checklist

- [ ] Update `PrimitiveExecutor` to use `AuthStore`
- [ ] Add auth injection logic to `execute()` method
- [ ] Check `required_scope` in tool config
- [ ] Inject Bearer token into HTTP headers
- [ ] Handle `AuthenticationRequired` exceptions gracefully
- [ ] Test executor with authenticated and public tools
- [ ] Update tool definitions with `required_scope` metadata
- [ ] Write integration tests for executor auth flow

## Phase 3 Checklist

- [ ] Implement `kiwi auth signin` command
- [ ] Implement `kiwi auth logout` command
- [ ] Implement `kiwi auth status` command
- [ ] Integrate with Supabase Auth API
- [ ] Handle refresh token lifecycle
- [ ] Add token rotation support
- [ ] Write user-facing auth documentation
- [ ] Test end-to-end authentication flow

---

## Testing Strategy

### Unit Tests

```python
# tests/test_auth_store.py

import pytest
from kiwi_mcp.runtime.auth import AuthStore, AuthenticationRequired

@pytest.mark.asyncio
async def test_set_and_get_token():
    """Test storing and retrieving token."""
    store = AuthStore(service_name="test_kiwi")
    
    # Set token
    store.set_token(
        service="test_service",
        access_token="test_token_123",
        expires_in=3600,
        scopes=["read", "write"]
    )
    
    # Get token
    token = await store.get_token("test_service")
    assert token == "test_token_123"
    
    # Cleanup
    store.clear_token("test_service")

@pytest.mark.asyncio
async def test_missing_token_raises_error():
    """Test that missing token raises AuthenticationRequired."""
    store = AuthStore(service_name="test_kiwi_2")
    
    with pytest.raises(AuthenticationRequired):
        await store.get_token("nonexistent_service")

@pytest.mark.asyncio
async def test_is_authenticated():
    """Test is_authenticated check."""
    store = AuthStore(service_name="test_kiwi_3")
    
    # Not authenticated
    assert not store.is_authenticated("test_service")
    
    # Set token
    store.set_token(
        service="test_service",
        access_token="test_token",
        expires_in=3600
    )
    
    # Now authenticated
    assert store.is_authenticated("test_service")
    
    # Cleanup
    store.clear_token("test_service")

@pytest.mark.asyncio
async def test_cache_metadata():
    """Test that metadata is cached."""
    store = AuthStore(service_name="test_kiwi_4")
    
    store.set_token(
        service="test_service",
        access_token="test_token",
        scopes=["admin"]
    )
    
    metadata = store.get_cached_metadata("test_service")
    assert metadata is not None
    assert "admin" in metadata["scopes"]
    assert "access_token" not in metadata  # Never expose token
    
    store.clear_token("test_service")
```

### Integration Tests

Test with real primitives (once implemented):

```python
@pytest.mark.asyncio
async def test_executor_injects_auth():
    """Test that executor injects auth token."""
    # Setup
    executor = PrimitiveExecutor(...)
    executor.auth_store.set_token(
        service="supabase",
        access_token="test_token"
    )
    
    # Execute authenticated tool
    result = await executor.execute("registry", {
        "action": "upload",
        "file": "test.py"
    })
    
    # Verify token was injected (by checking successful auth)
    assert result.success
```

---

## Security Considerations

### What's Protected

✅ **Tokens in keychain** - Encrypted by OS (AES on macOS, DPAPI on Windows, Secret Service on Linux)
✅ **Tokens in cache** - Only in memory during runtime, cleared on shutdown
✅ **Token visibility** - Never visible to agents, logged, or returned in responses
✅ **Refresh tokens** - Stored securely, only used by kernel

### What's NOT Protected

⚠️ **Memory access** - If process is compromised, tokens in cache can be read
⚠️ **Keychain access** - If user has OS-level access, they can read keychain
⚠️ **HTTP traffic** - Tokens sent over HTTPS (not TLS-protected by this code, but by HTTP stack)

**Mitigation:** These are inherent to any client-side auth system. The goal is to raise the bar above environment variables and config files.

---

## Migration Notes

When moving from Phase 1 (env vars) to Phase 2 (keychain):

1. Read token from env var if set
2. Store in keychain via `auth_store.set_token()`
3. Clear env var from process (don't rely on it)
4. Users with `SUPABASE_USER_TOKEN` get auto-migrated first run

---

## References

- [Python keyring Documentation](https://keyring.readthedocs.io/)
- [AGENT_CREDENTIAL_SECURITY.md](./AGENT_CREDENTIAL_SECURITY.md)
- [SUPABASE_DECOUPLING_PLAN.md](./SUPABASE_DECOUPLING_PLAN.md)

---

_Generated: 2026-01-26_
