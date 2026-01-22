"""
Tests for APIExecutor
"""

import os
from unittest.mock import Mock, AsyncMock, patch

import pytest
import httpx

from kiwi_mcp.handlers.tool.executors.api import APIExecutor
from kiwi_mcp.handlers.tool.executors.base import ExecutionResult


@pytest.fixture
def api_executor():
    """Create an APIExecutor instance."""
    return APIExecutor()


@pytest.fixture
def mock_manifest():
    """Create a mock API tool manifest."""
    manifest = Mock()
    manifest.tool_type = "api"
    manifest.executor_config = {"endpoint": "https://api.example.com/test"}
    return manifest


class TestAPIExecutor:
    """Test suite for APIExecutor."""

    def test_can_execute_api_type(self, api_executor, mock_manifest):
        """Test that executor can handle API tool type."""
        mock_manifest.tool_type = "api"
        assert api_executor.can_execute(mock_manifest) is True

    def test_cannot_execute_other_types(self, api_executor, mock_manifest):
        """Test that executor rejects non-API tool types."""
        mock_manifest.tool_type = "python"
        assert api_executor.can_execute(mock_manifest) is False

        mock_manifest.tool_type = "bash"
        assert api_executor.can_execute(mock_manifest) is False

    @pytest.mark.asyncio
    async def test_execute_get_request(self, api_executor, mock_manifest):
        """Test that executor makes GET requests correctly."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.text = '{"status": "ok"}'

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await api_executor.execute(mock_manifest, {})

        assert result.success is True
        assert '{"status": "ok"}' in result.output

    @pytest.mark.asyncio
    async def test_execute_post_request(self, api_executor, mock_manifest):
        """Test that executor makes POST requests with body."""
        mock_manifest.executor_config["method"] = "POST"
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.text = '{"created": true}'

        params = {"name": "test", "value": 123}

        with patch("httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            result = await api_executor.execute(mock_manifest, params)

            # Verify POST request was made with JSON body
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "POST"
            assert call_args[1]["json"] == params

        assert result.success is True
        assert '{"created": true}' in result.output

    @pytest.mark.asyncio
    async def test_execute_with_bearer_auth(self, api_executor, mock_manifest):
        """Test that executor handles bearer token authentication."""
        mock_manifest.executor_config["auth"] = {"type": "bearer", "token_param": "token"}
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.text = '{"authenticated": true}'

        params = {"token": "secret123"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            result = await api_executor.execute(mock_manifest, params)

            # Verify Authorization header was set
            call_args = mock_request.call_args
            assert call_args[1]["headers"]["Authorization"] == "Bearer secret123"

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_api_key_auth(self, api_executor, mock_manifest):
        """Test that executor handles API key authentication."""
        mock_manifest.executor_config["auth"] = {
            "type": "api_key",
            "key_param": "api_key",
            "header": "X-API-Key",
        }
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.text = '{"authenticated": true}'

        params = {"api_key": "key123"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            result = await api_executor.execute(mock_manifest, params)

            # Verify API key header was set
            call_args = mock_request.call_args
            assert call_args[1]["headers"]["X-API-Key"] == "key123"

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_environment_auth(self, api_executor, mock_manifest):
        """Test that executor uses environment variables for auth."""
        mock_manifest.executor_config["auth"] = {"type": "bearer", "token_env": "API_TOKEN"}
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.text = '{"authenticated": true}'

        with patch.dict(os.environ, {"API_TOKEN": "env_token"}):
            with patch("httpx.AsyncClient") as mock_client:
                mock_request = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.request = mock_request

                result = await api_executor.execute(mock_manifest, {})

                # Verify environment token was used
                call_args = mock_request.call_args
                assert call_args[1]["headers"]["Authorization"] == "Bearer env_token"

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, api_executor, mock_manifest):
        """Test that executor handles timeout correctly."""
        mock_manifest.executor_config["timeout"] = 5

        with patch("httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            mock_client.return_value.__aenter__.return_value.request = mock_request

            result = await api_executor.execute(mock_manifest, {})

        assert result.success is False
        assert "Request timed out" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_http_error(self, api_executor, mock_manifest):
        """Test that executor handles HTTP errors correctly."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.text = '{"error": "Not found"}'

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await api_executor.execute(mock_manifest, {})

        assert result.success is False
        assert "HTTP 404" in result.error
        assert '{"error": "Not found"}' in result.output

    def test_substitute_variables(self, api_executor):
        """Test variable substitution in URLs."""
        template = "https://api.example.com/${resource}/${id}"
        params = {"resource": "users", "id": "123"}

        result = api_executor._substitute_variables(template, params)
        assert result == "https://api.example.com/users/123"

    def test_build_headers_no_auth(self, api_executor):
        """Test header building without authentication."""
        config = {"headers": {"Content-Type": "application/json"}}
        params = {}

        headers = api_executor._build_headers(config, params)
        assert headers == {"Content-Type": "application/json"}

    def test_build_body_with_template(self, api_executor):
        """Test body building with template."""
        config = {"body": {"name": "${name}", "count": "${count}", "static": "value"}}
        params = {"name": "test", "count": "10"}

        body = api_executor._build_body(config, params)
        expected = {"name": "test", "count": "10", "static": "value"}
        assert body == expected

    def test_build_body_default_params(self, api_executor):
        """Test body building defaults to all parameters."""
        config = {}
        params = {"key1": "value1", "key2": "value2"}

        body = api_executor._build_body(config, params)
        assert body == params
