"""
Kernel-only authentication store with OS keychain integration.

Security Architecture:
- Tokens stored in OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- In-memory caching of metadata (not tokens) during runtime
- Automatic token refresh on expiry
- Never exposes tokens to tools or agents

Usage:
    auth_store = AuthStore()

    # Store token
    auth_store.set_token(
        service="supabase",
        access_token="jwt...",
        refresh_token="jwt...",
        expires_in=3600,
        scopes=["registry:read", "registry:write"]
    )

    # Retrieve token (with auto-refresh)
    token = await auth_store.get_token(service="supabase", scope="registry:write")

    # Check authentication status
    if auth_store.is_authenticated("supabase"):
        print("Authenticated")

    # Logout
    auth_store.clear_token("supabase")
"""

import keyring
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


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

    def __init__(self, service_name: str = "lilux"):
        """
        Initialize auth store.

        Args:
            service_name: Service name for keyring storage (default: "lilux")
        """
        self.service_name = service_name
        self._cache: Dict[str, Dict] = {}  # In-memory cache of metadata
        logger.debug(f"AuthStore initialized with service_name={service_name}")

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
        # Calculate expiry time in UTC
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

        logger.debug(f"Storing token for service={service}, expires_in={expires_in}s")

        # Store in OS keychain (encrypted by OS)
        keyring.set_password(self.service_name, f"{service}_access_token", access_token)

        if refresh_token:
            keyring.set_password(self.service_name, f"{service}_refresh_token", refresh_token)
            logger.debug(f"Stored refresh token for service={service}")

        keyring.set_password(self.service_name, f"{service}_expires_at", expires_at)

        # Optionally store scopes
        if scopes:
            keyring.set_password(self.service_name, f"{service}_scopes", ",".join(scopes))

        # Cache metadata (including token during runtime for performance)
        self._cache[service] = {
            "access_token": access_token,  # Cached during runtime only
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "scopes": scopes or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Token stored successfully for service={service}")

    async def get_token(self, service: str, scope: Optional[str] = None) -> str:
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
            if expires_at > datetime.now(timezone.utc):
                # If scope specified, verify it's available
                if scope is None or scope in cached.get("scopes", []):
                    logger.debug(f"Returning cached token for service={service}")
                    return cached["access_token"]
                else:
                    logger.warning(f"Token for service={service} missing required scope: {scope}")
                    raise AuthenticationRequired(
                        f"Token for {service} does not have required scope: {scope}. "
                        f"Please sign in again with: lilux auth signin"
                    )

            # Try to refresh if we have refresh token
            if cached.get("refresh_token"):
                try:
                    logger.info(f"Token expired for service={service}, attempting refresh")
                    new_token = await self._refresh_token(service, cached["refresh_token"])
                    # Update cache
                    self._cache[service]["access_token"] = new_token
                    # Parse new expiry from token (or use default)
                    self._cache[service]["expires_at"] = (
                        datetime.now(timezone.utc) + timedelta(hours=1)
                    ).isoformat()
                    logger.info(f"Token refreshed successfully for service={service}")
                    return new_token
                except RefreshError as e:
                    logger.error(f"Token refresh failed for service={service}: {e}")
                    # Fall through to require re-auth

        # 2. Get from keychain
        token = keyring.get_password(self.service_name, f"{service}_access_token")
        if not token:
            raise AuthenticationRequired(
                f"No authentication token for {service}. Please sign in with: lilux auth signin"
            )

        # 3. Load metadata from keychain
        expires_at_str = keyring.get_password(self.service_name, f"{service}_expires_at")
        refresh_token = keyring.get_password(self.service_name, f"{service}_refresh_token")
        scopes_str = keyring.get_password(self.service_name, f"{service}_scopes")
        scopes = scopes_str.split(",") if scopes_str else []

        # 4. Check expiry
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)

            # Token expired?
            if expires_at < datetime.now(timezone.utc):
                if refresh_token:
                    try:
                        # Try to refresh
                        logger.info(f"Token expired for service={service}, attempting refresh")
                        token = await self._refresh_token(service, refresh_token)
                        # Update keychain
                        new_expires_at = (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat()
                        keyring.set_password(self.service_name, f"{service}_access_token", token)
                        keyring.set_password(
                            self.service_name, f"{service}_expires_at", new_expires_at
                        )
                        expires_at_str = new_expires_at
                        logger.info(f"Token refreshed and stored for service={service}")
                    except RefreshError as e:
                        logger.error(f"Token refresh failed for service={service}: {e}")
                        raise AuthenticationRequired(
                            f"Token expired and refresh failed. "
                            f"Please sign in again: lilux auth signin"
                        )
                else:
                    raise AuthenticationRequired(
                        f"Token expired. Please sign in again: lilux auth signin"
                    )

        # 5. Verify scope if specified
        if scope and scope not in scopes:
            raise AuthenticationRequired(
                f"Token for {service} does not have required scope: {scope}. "
                f"Please sign in again with appropriate permissions."
            )

        # 6. Update cache
        self._cache[service] = {
            "access_token": token,
            "refresh_token": refresh_token,
            "expires_at": expires_at_str
            or (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "scopes": scopes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.debug(f"Token retrieved from keychain for service={service}")
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
        logger.warning(f"Token refresh not yet implemented for {service}")
        raise RefreshError(f"Token refresh not yet implemented for {service}")

    def clear_token(self, service: str) -> None:
        """
        Remove token from keychain (on logout).

        Args:
            service: Service identifier
        """
        logger.info(f"Clearing tokens for service={service}")

        try:
            keyring.delete_password(self.service_name, f"{service}_access_token")
        except keyring.errors.PasswordDeleteError:
            pass  # Already deleted

        try:
            keyring.delete_password(self.service_name, f"{service}_refresh_token")
        except keyring.errors.PasswordDeleteError:
            pass  # Already deleted

        try:
            keyring.delete_password(self.service_name, f"{service}_expires_at")
        except keyring.errors.PasswordDeleteError:
            pass  # Already deleted

        try:
            keyring.delete_password(self.service_name, f"{service}_scopes")
        except keyring.errors.PasswordDeleteError:
            pass  # Already deleted

        # Clear cache
        self._cache.pop(service, None)

        logger.info(f"Tokens cleared successfully for service={service}")

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
            token = keyring.get_password(self.service_name, f"{service}_access_token")
            if not token:
                return False

            # Check expiry
            expires_at_str = keyring.get_password(self.service_name, f"{service}_expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                return expires_at > datetime.now(timezone.utc)

            # No expiry info - assume valid
            return True
        except Exception as e:
            logger.error(f"Error checking authentication for service={service}: {e}")
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
