"""
Edge case and error handling tests for primitive executors.
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


class TestSubprocessEdgeCases:
    """Edge cases for subprocess execution."""

    @pytest.fixture
    def primitive(self):
        return SubprocessPrimitive()

    @pytest.mark.asyncio
    async def test_empty_command(self, primitive):
        """Test handling of empty command."""
        config = {"command": ""}
        params = {}

        result = await primitive.execute(config, params)

        assert not result.success
        assert (
            "Command not found" in result.stderr
            or "not found" in result.stderr.lower()
            or "command is required" in result.stderr
        )

    @pytest.mark.asyncio
    async def test_missing_command_config(self, primitive):
        """Test handling when command is missing from config."""
        config = {"args": ["test"]}  # No command specified
        params = {}

        result = await primitive.execute(config, params)

        assert not result.success
        assert "command is required" in result.stderr

    @pytest.mark.asyncio
    async def test_command_with_special_characters(self, primitive):
        """Test command execution with special characters."""
        config = {"command": "echo", "args": ["Hello & World | Test > /dev/null; echo Done"]}
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        assert "Hello & World | Test > /dev/null; echo Done" in result.stdout

    @pytest.mark.asyncio
    async def test_binary_output_handling(self, primitive):
        """Test handling of binary output from commands."""
        config = {
            "command": "python3",
            "args": [
                "-c",
                "import sys; sys.stdout.buffer.write(b'\\x00\\x01\\x02'); sys.stdout.flush(); print('text')",
            ],
        }
        params = {}

        result = await primitive.execute(config, params)

        # Binary output handling may fail or succeed depending on the system
        # The important thing is that it doesn't crash the primitive
        assert isinstance(result, SubprocessResult)
        if result.success:
            # If it succeeds, should handle binary data gracefully
            assert "text" in result.stdout
        else:
            # If it fails, should have a meaningful error message
            assert "codec" in result.stderr or "decode" in result.stderr

    @pytest.mark.asyncio
    async def test_unicode_handling(self, primitive):
        """Test handling of Unicode characters in input/output."""
        unicode_text = "Hello 世界 🌍 Ñoño café"

        config = {"command": "echo", "args": [unicode_text]}
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        assert unicode_text in result.stdout

    @pytest.mark.asyncio
    async def test_environment_variable_edge_cases(self, primitive):
        """Test edge cases in environment variable resolution."""
        test_cases = [
            # Empty variable name
            ("${}", "${}"),
            # Variable with special characters in name (should not resolve properly)
            ("${VAR-WITH-DASHES}", ""),  # Our regex doesn't handle dashes, so it returns empty
            # Nested braces (partial resolution)
            ("${OUTER${INNER}}", "}"),  # Our regex resolves OUTER${INNER as empty, leaving }
            # Multiple variables in one string
            ("${VAR1:-default1}_${VAR2:-default2}", "default1_default2"),
            # Variable at start, middle, and end
            ("${START:-s}_middle_${END:-e}", "s_middle_e"),
        ]

        for input_val, expected in test_cases:
            result = primitive._resolve_env_var(input_val)
            assert result == expected, f"Failed for input: {input_val}"

    @pytest.mark.asyncio
    async def test_working_directory_edge_cases(self, primitive):
        """Test edge cases with working directory."""
        # Test with non-existent directory
        config = {"command": "pwd", "cwd": "/nonexistent/directory/path"}
        params = {}

        result = await primitive.execute(config, params)

        assert not result.success
        # Should get an error about the directory not existing
        assert (
            "No such file or directory" in result.stderr or "cannot find" in result.stderr.lower()
        )

    @pytest.mark.asyncio
    async def test_zero_timeout(self, primitive):
        """Test behavior with zero timeout."""
        config = {"command": "echo", "args": ["test"], "timeout": 0}
        params = {}

        result = await primitive.execute(config, params)

        # Should either succeed very quickly or timeout immediately
        # Behavior may vary by system, so we just check it doesn't crash
        assert isinstance(result, SubprocessResult)

    @pytest.mark.asyncio
    async def test_negative_timeout(self, primitive):
        """Test behavior with negative timeout."""
        config = {"command": "echo", "args": ["test"], "timeout": -1}
        params = {}

        result = await primitive.execute(config, params)

        # Should handle gracefully (likely treat as no timeout or immediate timeout)
        assert isinstance(result, SubprocessResult)

    @pytest.mark.asyncio
    async def test_large_stdin_input(self, primitive):
        """Test handling of large stdin input."""
        # Create large input data (1MB)
        large_input = "Line of text that will be repeated many times.\n" * 20000

        config = {"command": "wc", "args": ["-l"], "input_data": large_input, "timeout": 30}
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        # Should count approximately 20000 lines
        line_count = int(result.stdout.strip())
        assert 19900 <= line_count <= 20100  # Allow some tolerance


class TestHttpClientEdgeCases:
    """Edge cases for HTTP client execution."""

    @pytest.fixture
    def primitive(self):
        return HttpClientPrimitive()

    @pytest.mark.asyncio
    async def test_missing_url_config(self, primitive):
        """Test handling when URL is missing from config."""
        config = {"method": "GET"}  # No URL specified
        params = {}

        result = await primitive.execute(config, params)

        assert not result.success
        assert "url is required" in result.error

    @pytest.mark.asyncio
    async def test_invalid_url_format(self, primitive):
        """Test handling of invalid URL formats."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = Exception("Invalid URL")

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {"method": "GET", "url": "not-a-valid-url"}
            params = {}

            result = await primitive.execute(config, params)

            assert not result.success
            assert "Invalid URL" in result.error

    @pytest.mark.asyncio
    async def test_url_templating_with_missing_params(self, primitive):
        """Test URL templating when required parameters are missing."""
        mock_client = AsyncMock()

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {
                "method": "GET",
                "url": "https://api.example.com/users/{user_id}/posts/{post_id}",
            }
            params = {"user_id": 123}  # Missing post_id

            # This should raise a KeyError when trying to format the URL
            result = await primitive.execute(config, params)

            assert not result.success
            assert "post_id" in result.error or "KeyError" in result.error

    @pytest.mark.asyncio
    async def test_response_parsing_edge_cases(self, primitive):
        """Test edge cases in response parsing."""
        test_cases = [
            # Invalid JSON response
            {
                "response_text": "invalid json {",
                "content_type": "application/json",
                "expected_body_type": str,
            },
            # Empty response
            {"response_text": "", "content_type": "application/json", "expected_body_type": str},
            # Large JSON response
            {
                "response_text": json.dumps({"data": ["item"] * 10000}),
                "content_type": "application/json",
                "expected_body_type": dict,
            },
            # Non-JSON response with JSON content-type
            {
                "response_text": "This is plain text",
                "content_type": "application/json",
                "expected_body_type": str,
            },
        ]

        for case in test_cases:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = case["response_text"]
            mock_response.headers = {"content-type": case["content_type"]}
            mock_response.reason_phrase = "OK"

            # Mock json() method behavior
            if case["expected_body_type"] == dict:
                mock_response.json.return_value = json.loads(case["response_text"])
            else:
                mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response

            with patch.object(primitive, "_get_client", return_value=mock_client):
                config = {"method": "GET", "url": "https://api.example.com/test"}
                params = {}

                result = await primitive.execute(config, params)

                assert result.success is True  # HTTP request succeeded
                assert isinstance(result.body, case["expected_body_type"])

    @pytest.mark.asyncio
    async def test_authentication_edge_cases(self, primitive):
        """Test edge cases in authentication handling."""
        test_cases = [
            # Missing token for bearer auth
            {"auth": {"type": "bearer"}, "expected_header": "Bearer "},
            # Empty token
            {"auth": {"type": "bearer", "token": ""}, "expected_header": "Bearer "},
            # Unknown auth type
            {"auth": {"type": "unknown_auth_type", "token": "test"}, "expected_header": None},
            # API key with custom header
            {
                "auth": {"type": "api_key", "key": "test_key", "header": "X-Custom-Key"},
                "expected_header": "test_key",
                "expected_header_name": "X-Custom-Key",
            },
        ]

        for case in test_cases:
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
                    "url": "https://api.example.com/protected",
                    "auth": case["auth"],
                }
                params = {}

                result = await primitive.execute(config, params)

                assert result.success is True

                # Check headers were set correctly
                call_args = mock_client.request.call_args
                headers = call_args[1]["headers"]

                if case["expected_header"] is not None:
                    if "expected_header_name" in case:
                        assert headers[case["expected_header_name"]] == case["expected_header"]
                    else:
                        assert headers.get("Authorization") == case["expected_header"]

    @pytest.mark.asyncio
    async def test_retry_with_zero_attempts(self, primitive):
        """Test retry behavior with zero max attempts."""
        import httpx

        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError("Connection failed")

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {
                "method": "GET",
                "url": "https://api.example.com/test",
                "retry": {"max_attempts": 0},
            }
            params = {}

            result = await primitive.execute(config, params)

            assert not result.success
            # Should fail immediately without retries
            assert mock_client.request.call_count == 0  # No attempts made

    @pytest.mark.asyncio
    async def test_extremely_large_response_body(self, primitive):
        """Test handling of extremely large response bodies."""
        # Create a large response (10MB of data)
        large_data = {"data": "x" * (10 * 1024 * 1024)}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_data
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch.object(primitive, "_get_client", return_value=mock_client):
            config = {"method": "GET", "url": "https://api.example.com/large-data"}
            params = {}

            result = await primitive.execute(config, params)

            assert result.success is True
            assert len(result.body["data"]) == 10 * 1024 * 1024


class TestPrimitiveExecutorEdgeCases:
    """Edge cases for PrimitiveExecutor orchestration."""

    @pytest.fixture
    def mock_registry(self):
        registry = MagicMock()
        registry.resolve_chain = AsyncMock()
        return registry

    @pytest.fixture
    def executor(self, mock_registry):
        return PrimitiveExecutor(mock_registry)

    @pytest.mark.asyncio
    async def test_empty_tool_chain(self, executor, mock_registry):
        """Test handling of empty tool chain."""
        mock_registry.resolve_chain.return_value = []

        result = await executor.execute("empty_tool", {})

        assert not result.success
        assert "not found or has no executor chain" in result.error

    @pytest.mark.asyncio
    async def test_tool_chain_with_no_primitive(self, executor, mock_registry):
        """Test handling of tool chain with no primitive specified."""
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "no_primitive_tool",
                "tool_type": "python",
                "executor_id": None,
                "manifest": {"config": {"command": "echo", "args": ["test"]}},
            }
        ]

        result = await executor.execute("no_primitive_tool", {})

        # Should fail with clear error message
        assert result.success is False
        assert (
            "Invalid tool chain: terminal tool 'no_primitive_tool' is not a primitive"
            in result.error
        )

    @pytest.mark.asyncio
    async def test_config_merging_with_conflicting_values(self, executor, mock_registry):
        """Test config merging when there are conflicting values."""
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "override_tool",
                "tool_type": "python",
                "executor_id": "python_runtime",
                "manifest": {
                    "config": {
                        "args": ["test"],
                        "timeout": 60,  # Should override base timeout
                        "env": {
                            "VAR1": "override_value",
                            "VAR3": "new_value",
                        },  # Should merge/override env
                    }
                },
            },
            {
                "depth": 1,
                "tool_id": "python_runtime",
                "tool_type": "runtime",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {
                        "command": "python3",
                        "timeout": 30,
                        "env": {"VAR1": "base_value", "VAR2": "base_value2"},
                    }
                },
            },
            {
                "depth": 2,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {}},
            },
        ]

        # Mock subprocess primitive to avoid actual execution
        with patch.object(executor.subprocess_primitive, "execute") as mock_execute:
            from kiwi_mcp.primitives.subprocess import SubprocessResult

            mock_execute.return_value = SubprocessResult(
                success=True, stdout="test output", stderr="", return_code=0, duration_ms=100
            )

            result = await executor.execute("override_tool", {})

            # Should succeed with merged configuration
            assert result.success is True

            # Verify the config was merged correctly
            mock_execute.assert_called_once()
            merged_config = mock_execute.call_args[0][0]

            # Child should override parent values
            assert merged_config["timeout"] == 60  # From child (override_tool)
            assert merged_config["command"] == "python3"  # From parent (python_runtime)
            assert merged_config["args"] == ["test"]  # From child (override_tool)

            # Environment should be merged
            assert merged_config["env"]["VAR1"] == "override_value"  # Child overrides
            assert merged_config["env"]["VAR2"] == "base_value2"  # Parent preserved
            assert merged_config["env"]["VAR3"] == "new_value"  # Child adds
        assert "test" in result.data["stdout"]

    @pytest.mark.asyncio
    async def test_registry_resolve_chain_exception(self, executor, mock_registry):
        """Test handling when registry.resolve_chain raises an exception."""
        mock_registry.resolve_chain.side_effect = Exception("Registry error")

        result = await executor.execute("problematic_tool", {})

        # Should handle the exception gracefully
        assert not result.success
        assert "Execution failed: Registry error" in result.error

    @pytest.mark.asyncio
    async def test_primitive_execution_exception(self, executor, mock_registry):
        """Test handling when primitive execution raises an exception."""
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {"command": "echo", "args": ["test"]}},
            }
        ]

        # Mock subprocess primitive to raise an exception
        with patch.object(
            executor.subprocess_primitive, "execute", side_effect=Exception("Primitive error")
        ):
            result = await executor.execute("exception_tool", {})

            assert not result.success
            assert "Execution failed: Primitive error" in result.error

    @pytest.mark.asyncio
    async def test_config_merging_with_non_dict_values(self, executor, mock_registry):
        """Test config merging when config contains non-dict values."""
        mock_registry.resolve_chain.return_value = [
            {
                "depth": 0,
                "tool_id": "override_tool",
                "tool_type": "bash",
                "executor_id": "subprocess",
                "manifest": {
                    "config": {
                        "args": ["override"],  # Should replace, not merge
                        "timeout": 60,
                    }
                },
            },
            {
                "depth": 1,
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "executor_id": None,
                "manifest": {"config": {"command": "echo", "args": ["base"], "timeout": 30}},
            },
        ]

        result = await executor.execute("override_tool", {})

        # Should succeed with the override args
        assert result.success is True
        assert "override" in result.data["stdout"]
        assert "base" not in result.data["stdout"]


class TestResourceLimitsAndBoundaries:
    """Test resource limits and boundary conditions."""

    @pytest.mark.asyncio
    async def test_subprocess_with_memory_intensive_command(self):
        """Test subprocess execution with memory-intensive commands."""
        primitive = SubprocessPrimitive()

        # Command that uses some memory but should complete
        config = {
            "command": "python3",
            "args": ["-c", "data = 'x' * (1024 * 1024); print(f'Created {len(data)} bytes')"],
            "timeout": 30,
        }
        params = {}

        result = await primitive.execute(config, params)

        assert result.success is True
        assert "1048576 bytes" in result.stdout

    @pytest.mark.asyncio
    async def test_http_with_many_headers(self):
        """Test HTTP request with many headers."""
        primitive = HttpClientPrimitive()

        # Create many headers
        many_headers = {f"X-Custom-Header-{i}": f"value_{i}" for i in range(100)}

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
                "url": "https://api.example.com/test",
                "headers": many_headers,
            }
            params = {}

            result = await primitive.execute(config, params)

            assert result.success is True

            # Verify all headers were passed
            call_args = mock_client.request.call_args
            passed_headers = call_args[1]["headers"]
            assert len(passed_headers) >= 100  # Should have at least our 100 headers
