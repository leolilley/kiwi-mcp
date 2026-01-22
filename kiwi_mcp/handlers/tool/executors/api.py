"""
API Executor for Tool Harness

Executes API calls with authentication and parameter handling.
"""

import os
import httpx
from typing import Dict, Any, Optional

from .base import ToolExecutor, ExecutionResult


class APIExecutor(ToolExecutor):
    """Executor for API-based tools."""

    async def execute(self, manifest, params: Dict[str, Any]) -> ExecutionResult:
        """Execute an API call with the given parameters."""
        config = manifest.executor_config

        # Build request
        method = config.get("method", "GET").upper()
        url = self._substitute_variables(config["endpoint"], params)
        headers = self._build_headers(config, params)

        # Build body for POST/PUT
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            body = self._build_body(config, params)

        # Make request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    timeout=config.get("timeout", 30),
                )

                return ExecutionResult(
                    success=response.is_success,
                    output=response.text,
                    error=None if response.is_success else f"HTTP {response.status_code}",
                )
            except httpx.RequestError as e:
                return ExecutionResult(success=False, output="", error=str(e))

    def _substitute_variables(self, template: str, params: Dict[str, Any]) -> str:
        """Substitute ${variable} patterns in the template string."""
        result = template
        for key, value in params.items():
            result = result.replace(f"${{{key}}}", str(value))
        return result

    def _build_headers(self, config: dict, params: dict) -> dict:
        """Build HTTP headers including authentication."""
        headers = config.get("headers", {}).copy()

        # Add auth
        if "auth" in config:
            auth = config["auth"]
            if auth["type"] == "bearer":
                token = params.get(auth.get("token_param")) or os.getenv(auth.get("token_env"))
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            elif auth["type"] == "api_key":
                key = params.get(auth.get("key_param")) or os.getenv(auth.get("key_env"))
                if key:
                    headers[auth.get("header", "X-API-Key")] = key

        return headers

    def _build_body(self, config: dict, params: dict) -> Optional[dict]:
        """Build request body from parameters."""
        if "body" in config:
            # Use configured body template and substitute variables
            body_template = config["body"]
            if isinstance(body_template, dict):
                result = {}
                for key, value in body_template.items():
                    if isinstance(value, str):
                        result[key] = self._substitute_variables(value, params)
                    else:
                        result[key] = value
                return result

        # Default: use all parameters as body
        return params

    def can_execute(self, manifest) -> bool:
        """Check if this executor can handle the given manifest."""
        return manifest.tool_type == "api"
