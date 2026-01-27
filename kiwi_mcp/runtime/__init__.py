"""
Kernel runtime services.

This module contains trusted kernel services for:
- Environment resolution (EnvResolver)
- Authentication (AuthStore)
- Lockfile management (LockfileStore) - to be implemented
"""

from .env_resolver import EnvResolver
from .auth import AuthStore, AuthenticationRequired, RefreshError

__all__ = [
    "EnvResolver",
    "AuthStore",
    "AuthenticationRequired",
    "RefreshError",
]
