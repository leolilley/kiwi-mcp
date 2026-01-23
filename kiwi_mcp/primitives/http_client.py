"""
HttpClientPrimitive for making HTTP requests with retry logic.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import httpx


@dataclass
class HttpResult:
    """Result of HTTP request execution."""

    success: bool
    status_code: int
    body: Any
    headers: Dict[str, str]
    duration_ms: int
    error: Optional[str] = None


class HttpClientPrimitive:
    """Primitive for making HTTP requests."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def execute(self, config: Dict[str, Any], params: Dict[str, Any]) -> HttpResult:
        """
        Execute an HTTP request.

        Args:
            config: Configuration from tool definition
            params: Runtime parameters

        Returns:
            HttpResult with response details
        """
        start_time = time.time()

        try:
            # Extract configuration
            method = config.get("method", "GET").upper()
            url = config.get("url")
            if not url:
                raise ValueError("url is required in config")

            headers = config.get("headers", {})
            body = config.get("body")
            timeout = config.get("timeout", 30)
            retry_config = config.get("retry", {})
            auth_config = config.get("auth", {})

            # Resolve environment variables in URL and headers
            url = self._resolve_env_var(url)
            resolved_headers = {}
            for key, value in headers.items():
                resolved_headers[key] = self._resolve_env_var(str(value))

            # Template URL with params
            url = url.format(**params)

            # Setup authentication
            if auth_config:
                auth_type = auth_config.get("type")
                if auth_type == "bearer":
                    token = self._resolve_env_var(auth_config.get("token", ""))
                    resolved_headers["Authorization"] = f"Bearer {token}"
                elif auth_type == "api_key":
                    key = self._resolve_env_var(auth_config.get("key", ""))
                    key_header = auth_config.get("header", "X-API-Key")
                    resolved_headers[key_header] = key

            # Get HTTP client
            client = await self._get_client()

            # Retry logic
            max_attempts = retry_config.get("max_attempts", 1)
            backoff = retry_config.get("backoff", "exponential")

            last_error = None

            for attempt in range(max_attempts):
                try:
                    # Make request
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=resolved_headers,
                        content=json.dumps(body)
                        if body and method in ["POST", "PUT", "PATCH"]
                        else None,
                        timeout=timeout,
                    )

                    # Parse response body
                    try:
                        response_body = response.json()
                    except (json.JSONDecodeError, ValueError):
                        response_body = response.text

                    duration_ms = int((time.time() - start_time) * 1000)

                    # Check if request was successful
                    success = 200 <= response.status_code < 400
                    error_msg = (
                        None
                        if success
                        else f"HTTP {response.status_code}: {response.reason_phrase}"
                    )

                    return HttpResult(
                        success=success,
                        status_code=response.status_code,
                        body=response_body,
                        headers=dict(response.headers),
                        duration_ms=duration_ms,
                        error=error_msg,
                    )

                except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
                    last_error = str(e)

                    # If this is the last attempt, return error
                    if attempt == max_attempts - 1:
                        break

                    # Calculate backoff delay
                    if backoff == "exponential":
                        delay = 2**attempt
                    else:
                        delay = 1

                    await asyncio.sleep(delay)

            # All attempts failed
            duration_ms = int((time.time() - start_time) * 1000)
            return HttpResult(
                success=False,
                status_code=0,
                body=None,
                headers={},
                duration_ms=duration_ms,
                error=f"Request failed after {max_attempts} attempts: {last_error}",
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return HttpResult(
                success=False,
                status_code=0,
                body=None,
                headers={},
                duration_ms=duration_ms,
                error=f"Unexpected error: {e}",
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    def _resolve_env_var(self, value: str) -> str:
        """
        Resolve environment variables with default syntax: ${VAR:-default}

        Args:
            value: String that may contain environment variable references

        Returns:
            String with environment variables resolved
        """
        if not isinstance(value, str):
            return str(value)

        import re

        # Pattern for ${VAR:-default} syntax
        pattern = r"\$\{([^}]+)\}"

        def replace_var(match):
            var_expr = match.group(1)

            # Check for default value syntax
            if ":-" in var_expr:
                var_name, default_value = var_expr.split(":-", 1)
                return os.environ.get(var_name.strip(), default_value)
            else:
                return os.environ.get(var_expr, "")

        return re.sub(pattern, replace_var, value)

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
