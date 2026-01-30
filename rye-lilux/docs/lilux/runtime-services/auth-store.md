**Source:** Original implementation: `kiwi_mcp/runtime/auth.py` in kiwi-mcp

# AuthStore Service

## Purpose

Secure credential management using OS keychain integration. Stores authentication tokens safely and provides automatic refresh on expiry.

## Security Architecture

AuthStore uses a **kernel-only security model**:

```
AuthStore (kernel-only access)
    ↓
OS Keychain
├── macOS: Keychain Access
├── Windows: Credential Manager
└── Linux: Secret Service API (freedesktop.org)
```

**Key principle:** Tokens are stored in OS-protected storage, never in memory/files.

## Key Classes

### AuthStore

The credential management service:

```python
class AuthStore:
    def __init__(self, service_name: str = "kiwi-mcp"):
        """Initialize auth store with service name."""
    
    def set_token(
        self,
        service: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None
    ) -> None:
        """Store token securely in OS keychain."""
    
    async def get_token(
        self,
        service: str,
        scope: Optional[str] = None
    ) -> str:
        """Retrieve token with automatic refresh on expiry."""
    
    def is_authenticated(self, service: str) -> bool:
        """Check if service has valid authentication."""
    
    def clear_token(self, service: str) -> None:
        """Logout from service."""
```

### Exceptions

```python
class AuthenticationRequired(Exception):
    """Raised when authentication is required but token is missing."""

class RefreshError(Exception):
    """Raised when token refresh fails."""
```

## Usage Pattern

### Store a Token

```python
from lilux.runtime import AuthStore

auth = AuthStore()

# Store JWT token (e.g., from Supabase)
auth.set_token(
    service="supabase",
    access_token="eyJhbGciOiJIUzI1NiIs...",
    refresh_token="your_refresh_token",
    expires_in=3600,  # 1 hour
    scopes=["registry:read", "registry:write"]
)
```

### Retrieve a Token

```python
# Get token (automatically refreshes if expired)
token = await auth.get_token(service="supabase", scope="registry:read")

# Use in HTTP request
result = await http_client.execute(
    config={
        "method": "GET",
        "url": "https://registry.example.com/api",
        "auth_type": "bearer",
        "auth_token": token
    },
    params={}
)
```

### Check Authentication Status

```python
if auth.is_authenticated("supabase"):
    print("Authenticated to Supabase")
    token = await auth.get_token("supabase")
else:
    print("Not authenticated")
```

### Logout

```python
# Clear token from keychain
auth.clear_token("supabase")
```

## Token Management

### Token Lifecycle

1. **Store:** `set_token()` saves to OS keychain
2. **Use:** `get_token()` retrieves from keychain
3. **Refresh:** Auto-refresh if expired
4. **Clear:** `clear_token()` removes from keychain

### Automatic Refresh

```python
# Token expires in 1 hour
auth.set_token(
    service="api",
    access_token="expires_soon",
    refresh_token="can_refresh",
    expires_in=3600
)

# ... 1 hour passes ...

# get_token() detects expiry and refreshes automatically
token = await auth.get_token(service="api")  # Refreshed!
```

### Scope-Based Access

```python
# Store with specific scopes
auth.set_token(
    service="registry",
    access_token="jwt...",
    scopes=["registry:read", "registry:write"]
)

# Check specific scope
token = await auth.get_token(service="registry", scope="registry:write")
# Raises AuthenticationRequired if scope not authorized
```

## Architecture Role

AuthStore is part of the **runtime services layer**:

1. **Secure storage** - OS-protected keychain
2. **Token lifecycle** - Store, refresh, clear
3. **Scope management** - Fine-grained permissions
4. **Kernel-only** - No tool access to raw tokens

## RYE Relationship

RYE's universal executor uses AuthStore to:
- Retrieve auth tokens for HTTP requests
- Validate credentials before tool execution
- Support multi-service authentication

**Pattern:**
```python
# RYE's executor
config = tool.config
if config.get("auth_type") == "bearer":
    token = await auth_store.get_token(
        service=config["service"],
        scope=config.get("scope")
    )
    config["auth_token"] = token

# Then execute HTTP primitive
result = await http_client.execute(config, params)
```

See `[[rye/categories/runtimes]]` for AUTH_CONFIG schema.

## OS Keychain Integration

### macOS

Uses native **Keychain Access**:

```
Keychain Access.app → Generic Password → "kiwi-mcp" → supabase_access_token
```

### Windows

Uses **Credential Manager**:

```
Control Panel → Credentials → Windows Credentials → "kiwi-mcp" → supabase_access_token
```

### Linux

Uses **Secret Service API** (freedesktop.org):

```
Secret Service API (KWallet, GNOME Keyring, etc.)
→ "kiwi-mcp" service
→ "supabase_access_token" key
```

## In-Memory Caching

AuthStore caches **metadata only**, not tokens:

```python
# Cached in memory (metadata)
_cache = {
    "supabase": {
        "expires_at": "2026-01-30T12:30:00Z",
        "scopes": ["registry:read", "registry:write"]
    }
}

# NOT cached in memory (always from keychain)
token = keyring.get_password(...)  # From OS keychain
```

This provides:
- Fast metadata checks
- Token always encrypted (keychain)
- Safe for long-running processes

## Multi-Service Support

Store credentials for multiple services:

```python
# Store Supabase token
auth.set_token(
    service="supabase",
    access_token="supabase_jwt...",
    expires_in=3600
)

# Store API key
auth.set_token(
    service="api",
    access_token="api_key...",
    expires_in=86400
)

# Retrieve specific service
supabase_token = await auth.get_token("supabase")
api_token = await auth.get_token("api")
```

## Error Handling

### Authentication Required

```python
try:
    token = await auth.get_token("missing_service")
except AuthenticationRequired:
    print("No token stored for this service")
    # Prompt user to authenticate
```

### Refresh Failed

```python
try:
    token = await auth.get_token("expired_service")
except RefreshError:
    print("Token refresh failed")
    # Token expired and refresh token invalid
    # User must authenticate again
```

## Practical Examples

### Authenticate to Supabase Registry

```python
# 1. User authenticates
auth = AuthStore()

# 2. Store their token (comes from OAuth flow)
auth.set_token(
    service="supabase",
    access_token="eyJhbGciOiJIUzI1NiIs...",
    refresh_token="your_refresh_token",
    expires_in=3600,
    scopes=["registry:read", "registry:write"]
)

# 3. Later, use token in registry requests
token = await auth.get_token("supabase", scope="registry:read")

result = await http_client.execute(
    config={
        "method": "GET",
        "url": "https://registry.example.com/tools",
        "auth_type": "bearer",
        "auth_token": token
    },
    params={}
)
```

### Store API Keys

```python
# API key that doesn't expire
auth.set_token(
    service="stripe",
    access_token="sk_live_abc123...",
    expires_in=31536000  # 1 year (effectively no expiry)
)

# Use in API calls
token = await auth.get_token("stripe")
```

## Testing

```python
import pytest
from lilux.runtime import AuthStore, AuthenticationRequired

@pytest.mark.asyncio
async def test_store_and_retrieve_token():
    auth = AuthStore()
    
    # Store token
    auth.set_token(
        service="test",
        access_token="test_token_123",
        expires_in=3600
    )
    
    # Retrieve token
    token = await auth.get_token("test")
    assert token == "test_token_123"

@pytest.mark.asyncio
async def test_missing_token():
    auth = AuthStore()
    
    with pytest.raises(AuthenticationRequired):
        await auth.get_token("nonexistent_service")

def test_authentication_status():
    auth = AuthStore()
    
    auth.set_token(
        service="test",
        access_token="test_token",
        expires_in=3600
    )
    
    assert auth.is_authenticated("test")
    assert not auth.is_authenticated("missing")
```

## Limitations and Design

### By Design (Not a Bug)

1. **OS keychain required**
   - Relies on OS-level encryption
   - Not available in some containers

2. **No token rotation by default**
   - Must call `set_token()` to update
   - Refresh happens on retrieval

3. **No revocation list**
   - Doesn't check if token was revoked remotely
   - Use `get_token()` for freshness check

4. **Scope validation optional**
   - Scopes stored but not enforced
   - RYE enforces scope requirements

## Security Notes

- Tokens encrypted at rest (OS keychain)
- Never logged in plaintext
- Cleared on `clear_token()`
- Works with restricted file permissions

## Next Steps

- See EnvResolver: `[[lilux/runtime-services/env-resolver]]`
- See LockfileStore: `[[lilux/runtime-services/lockfile-store]]`
- See primitives: `[[lilux/primitives/overview]]`
