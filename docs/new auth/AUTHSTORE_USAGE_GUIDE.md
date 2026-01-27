# AuthStore Usage Guide

**Quick reference for using the AuthStore system**

---

## For Tool Developers

### Declaring Auth Requirements

Tools that require authentication should declare `required_scope` in their manifest:

```python
# .ai/tools/core/registry.py

__tool_id__ = "registry"
__tool_type__ = "api"
__executor_id__ = "http_client"
__version__ = "1.0.0"

# Declare required scope for authenticated operations
__required_scope__ = "registry:write"  # For upload/publish/delete

__config__ = {
    "method": "POST",
    "url": "${SUPABASE_URL}/rest/v1/directives",
    "headers": {
        "apikey": "${SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }
}
```

### Per-Action Scopes

For tools with mixed public/private operations:

```python
# Option 1: Use separate tool files
# .ai/tools/core/registry_public.py (no required_scope)
# .ai/tools/core/registry_private.py (with required_scope)

# Option 2: Declare in tool code (future enhancement)
__scopes__ = {
    "search": None,           # Public
    "get": None,              # Public
    "upload": "registry:write",
    "publish": "registry:write",
}
```

---

## For Kernel Developers

### Using AuthStore Directly

```python
from kiwi_mcp.runtime.auth import AuthStore, AuthenticationRequired

# Initialize
auth_store = AuthStore()

# Store token (e.g., after user login)
auth_store.set_token(
    service="supabase",
    access_token="eyJhbGc...",
    refresh_token="v1.Mr5d...",
    expires_in=3600,
    scopes=["registry:read", "registry:write"]
)

# Retrieve token (with auto-refresh)
try:
    token = await auth_store.get_token(
        service="supabase",
        scope="registry:write"
    )
    print(f"Token: {token}")
except AuthenticationRequired as e:
    print(f"Auth required: {e}")

# Check authentication status
if auth_store.is_authenticated("supabase"):
    print("User is authenticated")

# Logout
auth_store.clear_token("supabase")
```

### Integration with Executor

The PrimitiveExecutor automatically handles auth injection:

```python
from kiwi_mcp.primitives.executor import PrimitiveExecutor
from pathlib import Path

# Initialize executor
executor = PrimitiveExecutor(
    project_path=Path("/path/to/project"),
    verify_integrity=True,
    validate_chain=True
)

# Execute tool (auth injected automatically)
result = await executor.execute(
    tool_id="registry",
    params={
        "action": "upload",
        "file": "model.bin"
    }
)

if result.success:
    print("Upload successful")
elif result.metadata.get("auth_required"):
    print("Authentication required. Please sign in.")
else:
    print(f"Error: {result.error}")
```

---

## For End Users

### Current (Programmatic)

Until CLI commands are implemented, tokens must be set programmatically:

```python
from kiwi_mcp.runtime.auth import AuthStore

auth_store = AuthStore()

# Obtain token from Supabase Auth (outside this system)
access_token = "..."  # From Supabase Auth API
refresh_token = "..."

# Store in keychain
auth_store.set_token(
    service="supabase",
    access_token=access_token,
    refresh_token=refresh_token,
    expires_in=3600,
    scopes=["registry:read", "registry:write"]
)
```

### Future (CLI)

When Phase B3 is complete:

```bash
# Sign in
kiwi auth signin --email user@example.com

# Check status
kiwi auth status

# Logout
kiwi auth logout
```

---

## Security Best Practices

### DO ✅

- Store tokens in OS keychain via AuthStore
- Let executor inject auth tokens automatically
- Use `required_scope` to declare auth requirements
- Clear tokens on logout with `clear_token()`
- Check authentication before operations with `is_authenticated()`

### DON'T ❌

- Never pass tokens as tool parameters
- Never store tokens in config files
- Never expose tokens in logs or error messages
- Never include tokens in tool outputs
- Never access keychain directly (use AuthStore)

---

## Troubleshooting

### "No authentication token" Error

**Symptom:** `AuthenticationRequired: No authentication token for supabase`

**Solution:**
1. User needs to sign in (when CLI exists: `kiwi auth signin`)
2. Or set token programmatically (see above)

### "Token expired" Error

**Symptom:** `AuthenticationRequired: Token expired and refresh failed`

**Solution:**
1. Refresh token logic not yet implemented
2. User needs to sign in again
3. Future: automatic refresh will handle this

### "Token does not have required scope" Error

**Symptom:** `AuthenticationRequired: Token for supabase does not have required scope: registry:write`

**Solution:**
1. User's token lacks necessary permissions
2. Sign in again with correct scopes
3. Check if user has necessary access rights

### Keyring Backend Not Available (Testing)

**Symptom:** `keyring.errors.NoKeyringError: No recommended backend was available`

**Solution:**
```python
# In test fixtures
import keyring
from keyrings.alt.file import PlaintextKeyring

@pytest.fixture(autouse=True, scope="session")
def setup_test_keyring():
    keyring.set_keyring(PlaintextKeyring())
```

---

## Token Lifecycle

```
User Signs In
    ↓
Token stored in OS keychain (encrypted)
    ↓
Token cached in memory (for performance)
    ↓
Tool execution requests auth
    ↓
Executor checks token expiry
    ↓
If expired: Try refresh (not yet implemented)
    ↓
If refresh fails: Raise AuthenticationRequired
    ↓
If valid: Inject token into HTTP headers
    ↓
Execute tool (token never visible to agent)
    ↓
User Signs Out
    ↓
Token removed from keychain and cache
```

---

## API Reference

### AuthStore

```python
class AuthStore:
    def __init__(self, service_name: str = "kiwi-mcp"): ...
    
    def set_token(
        self,
        service: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None,
    ) -> None: ...
    
    async def get_token(
        self,
        service: str,
        scope: Optional[str] = None
    ) -> str: ...
    
    def clear_token(self, service: str) -> None: ...
    
    def is_authenticated(self, service: str) -> bool: ...
    
    def get_cached_metadata(self, service: str) -> Optional[Dict]: ...
```

### Exceptions

```python
class AuthenticationRequired(Exception):
    """Raised when authentication is required but token is missing/invalid."""
    
class RefreshError(Exception):
    """Raised when token refresh fails."""
```

---

## Examples

### Example 1: Public Tool (No Auth)

```python
# .ai/tools/examples/public_api.py
__tool_id__ = "public_api"
__tool_type__ = "api"
__executor_id__ = "http_client"
# No required_scope - public tool

__config__ = {
    "method": "GET",
    "url": "https://api.github.com/repos/owner/repo"
}
```

### Example 2: Authenticated Tool

```python
# .ai/tools/examples/private_api.py
__tool_id__ = "private_api"
__tool_type__ = "api"
__executor_id__ = "http_client"
__required_scope__ = "api:write"  # Requires auth

__config__ = {
    "method": "POST",
    "url": "https://api.example.com/private/endpoint"
}
```

### Example 3: Testing with Auth

```python
import pytest
from kiwi_mcp.primitives.executor import PrimitiveExecutor
from kiwi_mcp.runtime.auth import AuthStore

@pytest.fixture
async def authenticated_executor(tmp_path):
    executor = PrimitiveExecutor(tmp_path)
    
    # Set up auth
    auth_store = AuthStore()
    auth_store.set_token(
        service="supabase",
        access_token="test_token",
        expires_in=3600
    )
    executor._auth_store = auth_store
    
    return executor

@pytest.mark.asyncio
async def test_authenticated_operation(authenticated_executor):
    result = await authenticated_executor.execute("private_tool", {})
    assert result.success
```

---

## Related Documentation

- [AUTH_STORE_IMPLEMENTATION.md](./AUTH_STORE_IMPLEMENTATION.md) - Implementation details
- [AGENT_CREDENTIAL_SECURITY.md](./AGENT_CREDENTIAL_SECURITY.md) - Security architecture
- [STREAM_B_IMPLEMENTATION_SUMMARY.md](./STREAM_B_IMPLEMENTATION_SUMMARY.md) - What was built

---

_Last Updated: 2026-01-27_
