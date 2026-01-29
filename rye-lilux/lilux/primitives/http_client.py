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
class StreamDestination:
    """Where streaming events go.

    NOTE (A.7): Only 'return' is a built-in http_client sink (buffers in memory).
    All other sinks (file_sink, null_sink, websocket_sink) are data-driven tools.
    See Appendix A.7 for sink architecture and tool configurations.
    """
    type: str  # "return" (built-in), or tool-based: "file_sink", "null_sink", "websocket_sink"
    path: Optional[str] = None  # For file_sink
    config: Optional[Dict[str, Any]] = None  # For tool-based sinks
    format: str = "jsonl"  # "jsonl" | "raw"


@dataclass
class StreamConfig:
    """Configuration for streaming HTTP."""
    transport: str  # "sse" | "websocket"
    destinations: List[StreamDestination]
    buffer_events: bool = False  # Include in result.body?
    max_buffer_size: int = 10_000  # Prevent OOM


@dataclass
class HttpResult:
    """Result of HTTP request execution."""

    success: bool
    status_code: int
    body: Any  # Can be buffered events if stream mode
    headers: Dict[str, str]
    duration_ms: int
    error: Optional[str] = None

    # New streaming fields
    stream_events_count: Optional[int] = None
    stream_destinations: Optional[List[str]] = None


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
        mode = params.get("mode", "sync")

        if mode == "sync":
            return await self._execute_sync(config, params)
        elif mode == "stream":
            return await self._execute_stream(config, params)
        else:
            raise ValueError(f"Unknown mode: {mode}. Must be 'sync' or 'stream'")

    async def _execute_sync(self, config: Dict[str, Any], params: Dict[str, Any]) -> HttpResult:
        """
        Execute a synchronous HTTP request.

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

    async def _execute_stream(self, config: Dict[str, Any], params: Dict[str, Any]) -> HttpResult:
        """Execute streaming HTTP request with destination fan-out.

        Sinks are pre-instantiated by the tool executor BEFORE http_client execution
        (during chain resolution). They are passed to http_client via __sinks parameter.
        See tool chain resolution section above for sink instantiation logic.
        """
        start_time = time.time()

        try:
            # Extract pre-instantiated sinks from params (provided by tool executor)
            sinks = params.pop("__sinks", [])

            # Determine if we should buffer for return
            should_buffer = any(isinstance(s, ReturnSink) for s in sinks)

            # Extract configuration (similar to sync)
            method = config.get("method", "GET").upper()
            url = config.get("url")
            if not url:
                raise ValueError("url is required in config")

            headers = config.get("headers", {})
            body_config = config.get("body")
            # Template body with params
            body = self._template_body(body_config, params) if body_config else None
            timeout = config.get("timeout", 30)
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

            # Build request content
            request_content = None
            if body and method in ["POST", "PUT", "PATCH"]:
                request_content = json.dumps(body)

            # Stream the request
            async with client.stream(
                method=method,
                url=url,
                headers=resolved_headers,
                content=request_content,
                timeout=timeout,
            ) as response:
                event_count = 0

                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        event_data = line[5:].strip()  # Remove "data: " prefix
                        if event_data:  # Skip empty events
                            event_count += 1

                            # Fan-out to all pre-instantiated sinks
                            for sink in sinks:
                                await sink.write(event_data)

                # Close all sinks
                for sink in sinks:
                    await sink.close()

                # Get buffered events from ReturnSink if present
                body = None
                if should_buffer:
                    return_sink = next((s for s in sinks if isinstance(s, ReturnSink)), None)
                    if return_sink:
                        body = return_sink.get_events()

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
                    body=body,
                    headers=dict(response.headers),
                    duration_ms=duration_ms,
                    error=error_msg,
                    stream_events_count=event_count,
                    stream_destinations=[type(s).__name__ for s in sinks] if sinks else None,
                )

        except Exception as e:
            # Close sinks on error
            sinks = params.get("__sinks", [])
            for sink in sinks:
                try:
                    await sink.close()
                except Exception:
                    pass

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

    def _template_body(self, body: Any, params: Dict[str, Any]) -> Any:
        """Recursively template body with parameters.
        
        Walks dict/list/str structures and replaces {param_name} with values.
        If a string contains only a single template placeholder, the value type is preserved.
        """
        if isinstance(body, dict):
            return {k: self._template_body(v, params) for k, v in body.items()}
        elif isinstance(body, list):
            return [self._template_body(item, params) for item in body]
        elif isinstance(body, str):
            # Check if string is a single template placeholder (e.g., "{param}")
            import re
            match = re.match(r'^\{(\w+)\}$', body.strip())
            if match:
                param_name = match.group(1)
                if param_name in params:
                    # Return the actual value, preserving its type
                    return params[param_name]
                else:
                    raise ValueError(f"Missing parameter for template: {param_name}")
            else:
                # Multiple placeholders or mixed content - use format (returns string)
                try:
                    return body.format(**params)
                except KeyError as e:
                    raise ValueError(f"Missing parameter for template: {e}")
        else:
            # Primitive types (int, bool, None) - return as-is
            return body

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


class ReturnSink:
    """Buffer events for inclusion in result. Built into http_client."""

    def __init__(self, max_size: int = 10000):
        self.buffer: List[str] = []
        self.max_size = max_size

    async def write(self, event: str) -> None:
        if len(self.buffer) < self.max_size:
            self.buffer.append(event)

    async def close(self) -> None:
        pass

    def get_events(self) -> List[str]:
        return self.buffer
