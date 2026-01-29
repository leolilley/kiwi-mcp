"""
Tests for HttpClientPrimitive.
"""

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from lilux.primitives.http_client import HttpClientPrimitive, HttpResult


class TestHttpClientPrimitive:
    """Test cases for HttpClientPrimitive."""

    @pytest.fixture
    def primitive(self):
        """Create HttpClientPrimitive instance."""
        return HttpClientPrimitive()

    @pytest.mark.asyncio
    async def test_execute_get_request(self, primitive):
        """Test executing a GET request."""
        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "success"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {"method": "GET", "url": "https://api.example.com/data"}
            params = {}

            result = await primitive.execute(config, params)

            assert isinstance(result, HttpResult)
            assert result.success is True
            assert result.status_code == 200
            assert result.body == {"message": "success"}
            assert result.duration_ms >= 0
            assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_post_with_body(self, primitive):
        """Test executing a POST request with body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "Created"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {
                "method": "POST",
                "url": "https://api.example.com/items",
                "body": {"name": "test item"},
            }
            params = {}

            result = await primitive.execute(config, params)

            assert result.success is True
            assert result.status_code == 201
            assert result.body == {"id": 123}

            # Verify the request was made with JSON body
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args[1]["method"] == "POST"
            assert call_args[1]["url"] == "https://api.example.com/items"
            assert call_args[1]["content"] == json.dumps({"name": "test item"})

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, primitive):
        """Test retry logic on request failure."""
        mock_client = AsyncMock()

        # First call fails, second succeeds
        import httpx

        mock_client.request.side_effect = [
            httpx.ConnectError("Connection failed"),
            MagicMock(
                status_code=200,
                json=lambda: {"retry": "success"},
                headers={"content-type": "application/json"},
                reason_phrase="OK",
            ),
        ]

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {
                "method": "GET",
                "url": "https://api.example.com/data",
                "retry": {"max_attempts": 2, "backoff": "exponential"},
            }
            params = {}

            # Mock asyncio.sleep to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await primitive.execute(config, params)

            assert result.success is True
            assert result.body == {"retry": "success"}
            assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_auth_bearer_token(self, primitive):
        """Test Bearer token authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"authenticated": True}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {
                "method": "GET",
                "url": "https://api.example.com/protected",
                "auth": {"type": "bearer", "token": "test_token_123"},
            }
            params = {}

            result = await primitive.execute(config, params)

            assert result.success is True

            # Verify Authorization header was set
            call_args = mock_client.request.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test_token_123"

    @pytest.mark.asyncio
    async def test_resolve_env_var_default(self, primitive):
        """Test environment variable resolution with defaults."""
        # Test with existing env var
        os.environ["TEST_TOKEN"] = "secret_token"
        result = primitive._resolve_env_var("${TEST_TOKEN}")
        assert result == "secret_token"

        # Test with default value
        result = primitive._resolve_env_var("${MISSING_TOKEN:-default_token}")
        assert result == "default_token"

        # Clean up
        del os.environ["TEST_TOKEN"]

    @pytest.mark.asyncio
    async def test_url_templating(self, primitive):
        """Test URL templating with parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user_id": 123}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {"method": "GET", "url": "https://api.example.com/users/{user_id}"}
            params = {"user_id": 123}

            result = await primitive.execute(config, params)

            assert result.success is True

            # Verify URL was templated correctly
            call_args = mock_client.request.call_args
            assert call_args[1]["url"] == "https://api.example.com/users/123"
