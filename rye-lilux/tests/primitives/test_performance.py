"""
Performance and stress tests for primitive executors.
"""

import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from lilux.primitives import SubprocessPrimitive, HttpClientPrimitive


class TestPerformanceMetrics:
    """Performance measurement tests."""

    @pytest.fixture
    def subprocess_primitive(self):
        return SubprocessPrimitive()

    @pytest.fixture
    def http_primitive(self):
        return HttpClientPrimitive()

    @pytest.mark.asyncio
    async def test_subprocess_execution_timing(self, subprocess_primitive):
        """Test subprocess execution timing accuracy."""
        config = {
            "command": "sleep",
            "args": ["0.1"],  # 100ms sleep
            "timeout": 5,
        }

        start_time = time.time()
        result = await subprocess_primitive.execute(config, {})
        actual_duration = (time.time() - start_time) * 1000

        assert result.success is True
        # Duration should be close to actual time (within 50ms tolerance)
        assert abs(result.duration_ms - actual_duration) < 50
        # Should be at least 100ms (the sleep time)
        assert result.duration_ms >= 100

    @pytest.mark.asyncio
    async def test_http_request_timing(self, http_primitive):
        """Test HTTP request timing accuracy."""

        # Mock a response with artificial delay
        async def delayed_request(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": "test"}
            response.headers = {"content-type": "application/json"}
            response.reason_phrase = "OK"
            return response

        mock_client = AsyncMock()
        mock_client.request = delayed_request

        with patch.object(http_primitive, "_get_client", return_value=mock_client):
            config = {"method": "GET", "url": "https://api.example.com/test"}

            start_time = time.time()
            result = await http_primitive.execute(config, {})
            actual_duration = (time.time() - start_time) * 1000

            assert result.success is True
            # Duration should be close to actual time (within 50ms tolerance)
            assert abs(result.duration_ms - actual_duration) < 50
            # Should be at least 100ms (the artificial delay)
            assert result.duration_ms >= 100


class TestConcurrencyStress:
    """Stress tests for concurrent execution."""

    @pytest.fixture
    def subprocess_primitive(self):
        return SubprocessPrimitive()

    @pytest.fixture
    def http_primitive(self):
        return HttpClientPrimitive()

    @pytest.mark.asyncio
    async def test_high_concurrency_subprocess(self, subprocess_primitive):
        """Test high concurrency subprocess execution."""
        num_concurrent = 50

        configs = [
            {"command": "echo", "args": [f"Process {i}"], "timeout": 10}
            for i in range(num_concurrent)
        ]

        start_time = time.time()

        # Execute all concurrently
        tasks = [subprocess_primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks)

        execution_time = time.time() - start_time

        # All should succeed
        assert all(result.success for result in results)
        assert len(results) == num_concurrent

        # Should complete much faster than sequential execution
        # (sequential would take at least num_concurrent * min_command_time)
        assert execution_time < 5.0  # Should complete within 5 seconds

        # Verify each result is unique
        outputs = [result.stdout.strip() for result in results]
        assert len(set(outputs)) == num_concurrent

    @pytest.mark.asyncio
    async def test_high_concurrency_http(self, http_primitive):
        """Test high concurrency HTTP requests with connection pooling."""
        num_concurrent = 100

        # Mock responses
        def create_mock_response(request_id):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "request_id": request_id,
                "data": f"response_{request_id}",
            }
            response.headers = {"content-type": "application/json"}
            response.reason_phrase = "OK"
            return response

        mock_responses = [create_mock_response(i) for i in range(num_concurrent)]

        mock_client = AsyncMock()
        mock_client.request.side_effect = mock_responses

        with patch.object(http_primitive, "_get_client", return_value=mock_client):
            configs = [
                {"method": "GET", "url": f"https://api.example.com/endpoint/{i}"}
                for i in range(num_concurrent)
            ]

            start_time = time.time()

            # Execute all concurrently
            tasks = [http_primitive.execute(config, {}) for config in configs]
            results = await asyncio.gather(*tasks)

            execution_time = time.time() - start_time

            # All should succeed
            assert all(result.success for result in results)
            assert len(results) == num_concurrent

            # Should complete quickly due to async execution
            assert execution_time < 2.0

            # Verify each response is unique
            request_ids = [result.body["request_id"] for result in results]
            assert len(set(request_ids)) == num_concurrent
            assert set(request_ids) == set(range(num_concurrent))

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, subprocess_primitive):
        """Test memory usage doesn't grow excessively under load."""
        try:
            import psutil
            import os
        except ImportError:
            pytest.skip("psutil not available")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Execute many subprocess operations
        for batch in range(10):  # 10 batches of 20 operations each
            configs = [
                {"command": "echo", "args": [f"Batch {batch} Process {i}"], "timeout": 5}
                for i in range(20)
            ]

            tasks = [subprocess_primitive.execute(config, {}) for config in configs]
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(result.success for result in results)

            # Force garbage collection
            import gc

            gc.collect()

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (less than 50MB)
        assert memory_growth < 50 * 1024 * 1024, (
            f"Memory grew by {memory_growth / 1024 / 1024:.2f}MB"
        )


class TestErrorRecoveryStress:
    """Stress tests for error recovery scenarios."""

    @pytest.fixture
    def subprocess_primitive(self):
        return SubprocessPrimitive()

    @pytest.fixture
    def http_primitive(self):
        return HttpClientPrimitive()

    @pytest.mark.asyncio
    async def test_mixed_success_failure_subprocess(self, subprocess_primitive):
        """Test handling mixed success/failure scenarios in subprocess execution."""
        configs = []
        expected_successes = 0
        expected_failures = 0

        # Mix of successful and failing commands
        for i in range(50):
            if i % 3 == 0:  # Every 3rd command fails
                configs.append(
                    {"command": "nonexistent_command_xyz", "args": [str(i)], "timeout": 5}
                )
                expected_failures += 1
            else:  # Successful commands
                configs.append({"command": "echo", "args": [f"Success {i}"], "timeout": 5})
                expected_successes += 1

        # Execute all concurrently
        tasks = [subprocess_primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks)

        # Count actual successes and failures
        actual_successes = sum(1 for result in results if result.success)
        actual_failures = sum(1 for result in results if not result.success)

        assert actual_successes == expected_successes
        assert actual_failures == expected_failures

        # Verify error messages are meaningful
        failed_results = [result for result in results if not result.success]
        for result in failed_results:
            assert "Command not found" in result.stderr or "not found" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_timeout_recovery_patterns(self, subprocess_primitive):
        """Test recovery from timeout scenarios."""
        configs = [
            # Mix of quick and slow commands
            {"command": "echo", "args": ["quick"], "timeout": 5},
            {"command": "sleep", "args": ["2"], "timeout": 1},  # Will timeout
            {"command": "echo", "args": ["quick2"], "timeout": 5},
            {"command": "sleep", "args": ["3"], "timeout": 1},  # Will timeout
            {"command": "echo", "args": ["quick3"], "timeout": 5},
        ]

        start_time = time.time()
        tasks = [subprocess_primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Should complete quickly despite timeouts (timeouts are 1 second each)
        assert total_time < 3.0  # Should be around 1-2 seconds due to concurrent execution

        # Check results
        quick_results = [r for r in results if r.success and "quick" in r.stdout]
        timeout_results = [r for r in results if not r.success and "timed out" in r.stderr]

        assert len(quick_results) == 3  # 3 quick commands should succeed
        assert len(timeout_results) == 2  # 2 sleep commands should timeout

    @pytest.mark.asyncio
    async def test_http_retry_exhaustion_patterns(self, http_primitive):
        """Test patterns when HTTP retry attempts are exhausted."""
        import httpx

        # Create configs with different retry settings
        configs = [
            {
                "method": "GET",
                "url": "https://unreliable-api.example.com/endpoint1",
                "retry": {"max_attempts": 2, "backoff": "exponential"},
            },
            {
                "method": "GET",
                "url": "https://unreliable-api.example.com/endpoint2",
                "retry": {"max_attempts": 3, "backoff": "exponential"},
            },
            {
                "method": "GET",
                "url": "https://reliable-api.example.com/endpoint3",
                "retry": {"max_attempts": 1},  # No retries, but will succeed
            },
        ]

        # Mock client with different failure patterns
        mock_client = AsyncMock()

        def side_effect(*args, **kwargs):
            url = kwargs.get("url", "")
            if "unreliable" in url:
                raise httpx.ConnectError("Connection failed")
            else:
                # Reliable endpoint succeeds
                response = MagicMock()
                response.status_code = 200
                response.json.return_value = {"success": True}
                response.headers = {"content-type": "application/json"}
                response.reason_phrase = "OK"
                return response

        mock_client.request.side_effect = side_effect

        with patch.object(http_primitive, "_get_client", return_value=mock_client):
            # Mock asyncio.sleep to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock):
                tasks = [http_primitive.execute(config, {}) for config in configs]
                results = await asyncio.gather(*tasks)

        # First two should fail (unreliable endpoints)
        assert not results[0].success
        assert not results[1].success
        assert "failed after" in results[0].error
        assert "failed after" in results[1].error

        # Third should succeed (reliable endpoint)
        assert results[2].success
        assert results[2].body["success"] is True

        # Verify retry attempts were made
        # endpoint1: 2 attempts, endpoint2: 3 attempts, endpoint3: 1 attempt = 6 total
        assert mock_client.request.call_count == 6


class TestResourceManagement:
    """Tests for proper resource management and cleanup."""

    @pytest.mark.asyncio
    async def test_http_client_connection_cleanup(self):
        """Test that HTTP client connections are properly managed."""
        primitive = HttpClientPrimitive()

        # Mock successful responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.reason_phrase = "OK"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Make multiple requests
            for i in range(10):
                config = {"method": "GET", "url": f"https://api.example.com/test/{i}"}
                result = await primitive.execute(config, {})
                assert result.success is True

            # Close the primitive
            await primitive.close()

            # Verify client was closed
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_subprocess_process_cleanup(self):
        """Test that subprocess processes are properly cleaned up."""
        # This test ensures that even if processes are killed due to timeout,
        # they are properly cleaned up and don't become zombie processes

        primitive = SubprocessPrimitive()

        config = {
            "command": "sleep",
            "args": ["10"],  # Long sleep
            "timeout": 0.5,  # Short timeout
        }

        result = await primitive.execute(config, {})

        # Should fail due to timeout
        assert not result.success
        assert "timed out" in result.stderr

        # Give a moment for cleanup
        await asyncio.sleep(0.1)

        # Check that no sleep processes are left running
        # (This is a basic check - in a real scenario you might want to check process tables)
        ps_config = {"command": "pgrep", "args": ["-f", "sleep 10"], "timeout": 5}

        ps_result = await primitive.execute(ps_config, {})
        # pgrep returns non-zero exit code when no processes found, which is what we want
        assert not ps_result.success or ps_result.stdout.strip() == ""
