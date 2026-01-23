"""
Integration tests for primitive executors with real-world scenarios.
"""

import asyncio
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from kiwi_mcp.primitives import (
    SubprocessPrimitive,
    HttpClientPrimitive,
    PrimitiveExecutor,
    SubprocessResult,
    HttpResult,
)


class TestComplexSubprocessScenarios:
    """Complex subprocess execution scenarios."""

    @pytest.fixture
    def primitive(self):
        return SubprocessPrimitive()

    @pytest.mark.asyncio
    async def test_complex_shell_pipeline(self, primitive):
        """Test complex shell pipeline with multiple commands."""
        config = {
            "command": "sh",
            "args": ["-c", "echo 'line1\nline2\nline3' | grep 'line2' | wc -l"],
            "timeout": 10,
        }
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        assert "1" in result.stdout.strip()
        assert result.return_code == 0

    @pytest.mark.asyncio
    async def test_environment_variable_inheritance_and_override(self, primitive):
        """Test complex environment variable scenarios."""
        # Set up test environment
        os.environ["TEST_BASE"] = "base_value"
        os.environ["TEST_OVERRIDE"] = "original_value"

        try:
            config = {
                "command": "sh",
                "args": ["-c", 'echo "BASE=$TEST_BASE OVERRIDE=$TEST_OVERRIDE NEW=$TEST_NEW"'],
                "env": {"TEST_OVERRIDE": "overridden_value", "TEST_NEW": "new_value"},
            }
            params = {}

            result = await primitive.execute(config, params)

            assert result.success is True
            output = result.stdout.strip()
            assert "BASE=base_value" in output
            assert "OVERRIDE=overridden_value" in output
            assert "NEW=new_value" in output

        finally:
            # Clean up
            del os.environ["TEST_BASE"]
            del os.environ["TEST_OVERRIDE"]

    @pytest.mark.asyncio
    async def test_working_directory_with_file_operations(self, primitive):
        """Test working directory changes with file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            config = {"command": "cat", "args": ["test.txt"], "cwd": temp_dir}
            params = {}

            result = await primitive.execute(config, params)

            assert result.success is True
            assert "test content" in result.stdout

    @pytest.mark.asyncio
    async def test_large_output_handling(self, primitive):
        """Test handling of large output streams."""
        config = {
            "command": "sh",
            "args": [
                "-c",
                'for i in $(seq 1 1000); do echo "Line $i with some additional content to make it longer"; done',
            ],
            "timeout": 30,
        }
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 1000
        assert "Line 1 with some additional content" in lines[0]
        assert "Line 1000 with some additional content" in lines[-1]

    @pytest.mark.asyncio
    async def test_interactive_command_with_stdin(self, primitive):
        """Test interactive command that reads from stdin."""
        config = {
            "command": "python3",
            "args": [
                "-c",
                "import sys; data = sys.stdin.read(); print(f'Received: {len(data)} characters')",
            ],
            "input_data": "This is test input data that will be sent to stdin\n" * 10,
        }
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        assert "Received: 510 characters" in result.stdout

    @pytest.mark.asyncio
    async def test_concurrent_subprocess_execution(self, primitive):
        """Test concurrent execution of multiple subprocesses."""
        sleep_config = {"command": "sleep", "args": ["0.1"], "timeout": 5}

        echo_configs = [{"command": "echo", "args": [f"Process {i}"]} for i in range(4)]

        configs = [sleep_config] + echo_configs

        # Execute all concurrently
        tasks = [primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result.success for result in results)

        # Check that echo commands produced expected output
        echo_results = [r for r in results if "Process" in r.stdout]
        assert len(echo_results) == 4  # 4 echo commands

    @pytest.mark.asyncio
    async def test_environment_variable_resolution_complex(self, primitive):
        """Test complex environment variable resolution scenarios."""
        os.environ["TEST_VAR1"] = "value1"
        os.environ["TEST_VAR2"] = "value2"

        try:
            # Test multiple variables and defaults
            test_cases = [
                ("${TEST_VAR1}", "value1"),
                ("${TEST_VAR2:-default}", "value2"),
                ("${NONEXISTENT:-default_value}", "default_value"),
                ("prefix_${TEST_VAR1}_suffix", "prefix_value1_suffix"),
                ("${TEST_VAR1}_${TEST_VAR2}", "value1_value2"),
                ("${MISSING1:-${TEST_VAR1}}", "value1"),  # Nested not supported, should be literal
            ]

            for input_val, expected in test_cases:
                result = primitive._resolve_env_var(input_val)
                if "MISSING1" in input_val:
                    # This case tests that nested resolution isn't supported
                    assert "${TEST_VAR1}" in result
                else:
                    assert result == expected, f"Failed for input: {input_val}"

        finally:
            del os.environ["TEST_VAR1"]
            del os.environ["TEST_VAR2"]


class TestComplexHttpClientScenarios:
    """Complex HTTP client execution scenarios."""

    @pytest.fixture
    def primitive(self):
        return HttpClientPrimitive()

    @pytest.mark.asyncio
    async def test_complex_authentication_flow(self, primitive):
        """Test complex authentication with token refresh simulation."""
        # Mock responses for auth flow
        auth_response = MagicMock()
        auth_response.status_code = 200
        auth_response.json.return_value = {"access_token": "new_token_123", "expires_in": 3600}
        auth_response.headers = {"content-type": "application/json"}
        auth_response.reason_phrase = "OK"

        api_response = MagicMock()
        api_response.status_code = 200
        api_response.json.return_value = {"data": "protected_data"}
        api_response.headers = {"content-type": "application/json"}
        api_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.side_effect = [auth_response, api_response]

        with patch.object(primitive, "_get_client", return_value=mock_client):
            # First request: Get auth token
            auth_config = {
                "method": "POST",
                "url": "https://auth.example.com/token",
                "body": {"grant_type": "client_credentials"},
                "headers": {"Content-Type": "application/json"},
            }

            auth_result = await primitive.execute(auth_config, {})
            assert auth_result.success is True
            token = auth_result.body["access_token"]

            # Second request: Use token for API call
            api_config = {
                "method": "GET",
                "url": "https://api.example.com/protected",
                "auth": {"type": "bearer", "token": token},
            }

            api_result = await primitive.execute(api_config, {})
            assert api_result.success is True
            assert api_result.body["data"] == "protected_data"

    @pytest.mark.asyncio
    async def test_retry_with_different_error_types(self, primitive):
        """Test retry logic with different types of errors."""
        import httpx

        mock_client = AsyncMock()

        # Simulate different error types across retries
        mock_client.request.side_effect = [
            httpx.ConnectError("Connection refused"),
            httpx.TimeoutException("Request timeout"),
            httpx.ReadTimeout("Read timeout"),
            MagicMock(
                status_code=200,
                json=lambda: {"success": True},
                headers={"content-type": "application/json"},
                reason_phrase="OK",
            ),
        ]

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {
                "method": "GET",
                "url": "https://unreliable-api.example.com/data",
                "retry": {"max_attempts": 4, "backoff": "exponential"},
                "timeout": 5,
            }
            params = {}

            # Mock asyncio.sleep to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await primitive.execute(config, params)

            assert result.success is True
            assert result.body["success"] is True
            assert mock_client.request.call_count == 4

    @pytest.mark.asyncio
    async def test_large_response_handling(self, primitive):
        """Test handling of large HTTP responses."""
        # Create a large response body
        large_data = {"items": [{"id": i, "data": f"item_{i}" * 100} for i in range(1000)]}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_data
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {"method": "GET", "url": "https://api.example.com/large-dataset"}
            params = {}

            result = await primitive.execute(config, params)

            assert result.success is True
            assert len(result.body["items"]) == 1000
            assert result.body["items"][0]["id"] == 0
            assert result.body["items"][-1]["id"] == 999

    @pytest.mark.asyncio
    async def test_concurrent_http_requests(self, primitive):
        """Test concurrent HTTP requests with connection pooling."""
        mock_responses = []
        for i in range(10):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"request_id": i, "data": f"response_{i}"}
            response.headers = {"content-type": "application/json"}
            response.reason_phrase = "OK"
            mock_responses.append(response)

        mock_client = AsyncMock()
        mock_client.request.side_effect = mock_responses

        with patch.object(primitive, "_get_client", return_value=mock_client):
            configs = [
                {"method": "GET", "url": f"https://api.example.com/endpoint/{i}"} for i in range(10)
            ]

            # Execute all requests concurrently
            tasks = [primitive.execute(config, {}) for config in configs]
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(result.success for result in results)
            assert len(results) == 10

            # Verify each response
            for i, result in enumerate(results):
                assert result.body["request_id"] == i
                assert result.body["data"] == f"response_{i}"

    @pytest.mark.asyncio
    async def test_complex_url_templating_and_params(self, primitive):
        """Test complex URL templating with multiple parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {
                "method": "GET",
                "url": "https://api.example.com/users/{user_id}/posts/{post_id}/comments?limit={limit}&offset={offset}",
            }
            params = {"user_id": 123, "post_id": 456, "limit": 10, "offset": 20}

            result = await primitive.execute(config, params)

            assert result.success is True

            # Verify the URL was templated correctly
            call_args = mock_client.request.call_args
            expected_url = "https://api.example.com/users/123/posts/456/comments?limit=10&offset=20"
            assert call_args[1]["url"] == expected_url


class TestPrimitiveExecutorIntegration:
    """Integration tests for PrimitiveExecutor orchestration."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock tool registry."""
        registry = MagicMock()
        registry.resolve_chain = AsyncMock()
        return registry

    @pytest.fixture
    def executor(self, mock_registry):
        """Create PrimitiveExecutor with mock registry."""
        return PrimitiveExecutor(mock_registry)

    @pytest.mark.asyncio
    async def test_subprocess_tool_execution_via_executor(self, executor, mock_registry):
        """Test executing a subprocess tool via the executor."""
        # Mock registry to return subprocess chain
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {"command": "echo", "args": ["Hello from executor"]}},
            }
        ]

        result = await executor.execute("test_tool", {})

        assert result.success is True
        assert "Hello from executor" in result.data["stdout"]
        assert result.metadata["type"] == "subprocess"
        assert result.metadata["return_code"] == 0

    @pytest.mark.asyncio
    async def test_http_tool_execution_via_executor(self, executor, mock_registry):
        """Test executing an HTTP tool via the executor."""
        # Mock registry to return HTTP chain
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "http_client",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {"method": "GET", "url": "https://api.example.com/test"}},
            }
        ]

        # Mock the HTTP primitive
        mock_http_result = HttpResult(
            success=True,
            status_code=200,
            body={"message": "success"},
            headers={"content-type": "application/json"},
            duration_ms=100,
        )

        with patch.object(executor.http_client_primitive, "execute", return_value=mock_http_result):
            result = await executor.execute("test_http_tool", {})

            assert result.success is True
            assert result.data == {"message": "success"}
            assert result.metadata["type"] == "http_client"
            assert result.metadata["status_code"] == 200

    @pytest.mark.asyncio
    async def test_config_merging_in_chain(self, executor, mock_registry):
        """Test configuration merging across tool chain."""
        # Mock registry to return chain with multiple tools
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "extended_tool",
                "tool_type": "script",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {
                        "args": ["-c", "print('test')"],
                        "timeout": 60,  # Should override base timeout
                        "env": {"EXTENDED_VAR": "extended_value"},  # Should merge with base env
                    }
                },
            },
            {
                "depth": 1,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {
                    "config": {
                        "command": "python3",
                        "timeout": 30,
                        "env": {"BASE_VAR": "base_value"},
                    }
                },
            },
        ]

        result = await executor.execute("extended_tool", {})

        assert result.success is True
        assert "test" in result.data["stdout"]

        # Verify config merging happened (we can't directly inspect merged config,
        # but we can verify the command executed successfully with merged settings)
        mock_registry.resolve_chain.assert_called_once_with("extended_tool")

    @pytest.mark.asyncio
    async def test_error_handling_for_unknown_primitive(self, executor, mock_registry):
        """Test error handling for unknown primitive type."""
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "unknown_primitive_type",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {}},
            }
        ]

        result = await executor.execute("unknown_tool", {})

        assert result.success is False
        assert "Unknown primitive type: unknown_primitive_type" in result.error

    @pytest.mark.asyncio
    async def test_error_handling_for_missing_tool(self, executor, mock_registry):
        """Test error handling when tool is not found."""
        mock_registry.resolve_chain.return_value = []

        result = await executor.execute("nonexistent_tool", {})

        assert result.success is False
        assert "not found or has no executor chain" in result.error


class TestRealWorldScenarios:
    """Real-world integration scenarios."""

    @pytest.mark.asyncio
    async def test_git_operations_workflow(self):
        """Test a git operations workflow using subprocess primitive."""
        primitive = SubprocessPrimitive()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize git repo
            init_config = {"command": "git", "args": ["init"], "cwd": temp_dir}
            result = await primitive.execute(init_config, {})
            assert result.success is True

            # Configure git user
            config_user = {
                "command": "git",
                "args": ["config", "user.name", "Test User"],
                "cwd": temp_dir,
            }
            result = await primitive.execute(config_user, {})
            assert result.success is True

            config_email = {
                "command": "git",
                "args": ["config", "user.email", "test@example.com"],
                "cwd": temp_dir,
            }
            result = await primitive.execute(config_email, {})
            assert result.success is True

            # Create and add a file
            test_file = Path(temp_dir) / "README.md"
            test_file.write_text("# Test Repository\n\nThis is a test.")

            add_config = {"command": "git", "args": ["add", "README.md"], "cwd": temp_dir}
            result = await primitive.execute(add_config, {})
            assert result.success is True

            # Commit the file
            commit_config = {
                "command": "git",
                "args": ["commit", "-m", "Initial commit"],
                "cwd": temp_dir,
            }
            result = await primitive.execute(commit_config, {})
            assert result.success is True
            assert "Initial commit" in result.stdout

            # Check status
            status_config = {"command": "git", "args": ["status", "--porcelain"], "cwd": temp_dir}
            result = await primitive.execute(status_config, {})
            assert result.success is True
            assert result.stdout.strip() == ""  # Should be clean

    @pytest.mark.asyncio
    async def test_api_data_processing_workflow(self):
        """Test API data processing workflow using HTTP primitive."""
        primitive = HttpClientPrimitive()

        # Mock a multi-step API workflow
        responses = [
            # Step 1: Get auth token
            MagicMock(
                status_code=200,
                json=lambda: {"token": "auth_token_123", "expires_in": 3600},
                headers={"content-type": "application/json"},
                reason_phrase="OK",
            ),
            # Step 2: Get user list
            MagicMock(
                status_code=200,
                json=lambda: {
                    "users": [
                        {"id": 1, "name": "Alice", "email": "alice@example.com"},
                        {"id": 2, "name": "Bob", "email": "bob@example.com"},
                    ],
                    "total": 2,
                },
                headers={"content-type": "application/json"},
                reason_phrase="OK",
            ),
            # Step 3: Get user details for Alice
            MagicMock(
                status_code=200,
                json=lambda: {
                    "id": 1,
                    "name": "Alice",
                    "email": "alice@example.com",
                    "profile": {"department": "Engineering", "role": "Developer"},
                },
                headers={"content-type": "application/json"},
                reason_phrase="OK",
            ),
        ]

        mock_client = AsyncMock()
        mock_client.request.side_effect = responses

        with patch.object(primitive, "_get_client", return_value=mock_client):
            # Step 1: Authenticate
            auth_config = {
                "method": "POST",
                "url": "https://api.example.com/auth",
                "body": {"username": "admin", "password": "secret"},
            }
            auth_result = await primitive.execute(auth_config, {})
            assert auth_result.success is True
            token = auth_result.body["token"]

            # Step 2: Get users
            users_config = {
                "method": "GET",
                "url": "https://api.example.com/users",
                "auth": {"type": "bearer", "token": token},
            }
            users_result = await primitive.execute(users_config, {})
            assert users_result.success is True
            assert len(users_result.body["users"]) == 2

            # Step 3: Get detailed info for first user
            user_id = users_result.body["users"][0]["id"]
            details_config = {
                "method": "GET",
                "url": "https://api.example.com/users/{user_id}",
                "auth": {"type": "bearer", "token": token},
            }
            details_result = await primitive.execute(details_config, {"user_id": user_id})
            assert details_result.success is True
            assert details_result.body["profile"]["department"] == "Engineering"
