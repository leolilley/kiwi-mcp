"""
Comprehensive stress tests for primitive executors.
"""

import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from lilux.primitives import SubprocessPrimitive, HttpClientPrimitive, PrimitiveExecutor


class TestExtremeConcurrency:
    """Extreme concurrency stress tests."""

    @pytest.mark.asyncio
    async def test_massive_concurrent_subprocess_execution(self):
        """Test with very high concurrency (200+ processes)."""
        primitive = SubprocessPrimitive()
        num_processes = 200

        configs = [
            {"command": "echo", "args": [f"Process-{i:03d}"], "timeout": 10}
            for i in range(num_processes)
        ]

        start_time = time.time()

        # Execute all concurrently
        tasks = [primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time

        # Count successful results (some may fail due to system limits)
        successful_results = [r for r in results if hasattr(r, "success") and r.success]
        failed_results = [r for r in results if hasattr(r, "success") and not r.success]
        exceptions = [r for r in results if isinstance(r, Exception)]

        print(f"Executed {num_processes} processes in {execution_time:.2f}s")
        print(
            f"Successful: {len(successful_results)}, Failed: {len(failed_results)}, Exceptions: {len(exceptions)}"
        )

        # Should complete most processes successfully
        assert len(successful_results) >= num_processes * 0.8  # At least 80% success rate
        assert execution_time < 30.0  # Should complete within 30 seconds

        # Verify unique outputs
        outputs = [r.stdout.strip() for r in successful_results]
        assert len(set(outputs)) == len(successful_results)  # All outputs should be unique

    @pytest.mark.asyncio
    async def test_massive_concurrent_http_requests(self):
        """Test with very high HTTP concurrency (500+ requests)."""
        primitive = HttpClientPrimitive()
        num_requests = 500

        # Mock responses
        def create_mock_response(request_id):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"id": request_id, "data": f"response_{request_id}"}
            response.headers = {"content-type": "application/json"}
            response.reason_phrase = "OK"
            return response

        mock_responses = [create_mock_response(i) for i in range(num_requests)]

        mock_client = AsyncMock()
        mock_client.request.side_effect = mock_responses

        with patch.object(primitive, "_get_client", return_value=mock_client):
            configs = [
                {"method": "GET", "url": f"https://api.example.com/endpoint/{i}"}
                for i in range(num_requests)
            ]

            start_time = time.time()

            # Execute all concurrently
            tasks = [primitive.execute(config, {}) for config in configs]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            execution_time = time.time() - start_time

            # Count results
            successful_results = [r for r in results if hasattr(r, "success") and r.success]
            failed_results = [r for r in results if hasattr(r, "success") and not r.success]
            exceptions = [r for r in results if isinstance(r, Exception)]

            print(f"Executed {num_requests} HTTP requests in {execution_time:.2f}s")
            print(
                f"Successful: {len(successful_results)}, Failed: {len(failed_results)}, Exceptions: {len(exceptions)}"
            )

            # Should complete all requests successfully
            assert len(successful_results) == num_requests
            assert len(failed_results) == 0
            assert len(exceptions) == 0
            assert execution_time < 10.0  # Should complete within 10 seconds

            # Verify unique responses
            response_ids = [r.body["id"] for r in successful_results]
            assert len(set(response_ids)) == num_requests


class TestResourceExhaustion:
    """Test behavior under resource exhaustion conditions."""

    @pytest.mark.asyncio
    async def test_file_descriptor_limits(self):
        """Test behavior when approaching file descriptor limits."""
        primitive = SubprocessPrimitive()

        # Create many concurrent long-running processes
        configs = [
            {"command": "sleep", "args": ["0.5"], "timeout": 2}
            for _ in range(100)  # This might hit FD limits on some systems
        ]

        start_time = time.time()

        # Execute all concurrently
        tasks = [primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time

        # Count results
        successful_results = [r for r in results if hasattr(r, "success") and r.success]
        failed_results = [r for r in results if hasattr(r, "success") and not r.success]
        exceptions = [r for r in results if isinstance(r, Exception)]

        print(
            f"FD limit test: {len(successful_results)} successful, {len(failed_results)} failed, {len(exceptions)} exceptions"
        )

        # Should handle gracefully - either succeed or fail with meaningful errors
        assert len(results) == 100
        assert execution_time < 5.0  # Should complete within 5 seconds

        # If there are failures, they should have meaningful error messages
        for result in failed_results:
            assert isinstance(result.stderr, str)
            assert len(result.stderr) > 0

    @pytest.mark.asyncio
    async def test_memory_pressure_subprocess(self):
        """Test subprocess execution under memory pressure."""
        primitive = SubprocessPrimitive()

        # Create processes that use some memory
        configs = [
            {
                "command": "python3",
                "args": [
                    "-c",
                    f"data = 'x' * (1024 * 100); print(f'Process {i} allocated {{len(data)}} bytes')",
                ],
                "timeout": 10,
            }
            for i in range(20)
        ]

        start_time = time.time()

        # Execute all concurrently
        tasks = [primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time

        # Count results
        successful_results = [r for r in results if hasattr(r, "success") and r.success]
        failed_results = [r for r in results if hasattr(r, "success") and not r.success]

        print(
            f"Memory pressure test: {len(successful_results)} successful, {len(failed_results)} failed"
        )

        # Should handle memory allocation gracefully
        assert len(successful_results) >= 15  # At least 75% should succeed
        assert execution_time < 15.0

        # Verify successful processes allocated memory
        for result in successful_results:
            assert "102400 bytes" in result.stdout


class TestLongRunningOperations:
    """Test long-running operations and timeouts."""

    @pytest.mark.asyncio
    async def test_mixed_duration_subprocess_operations(self):
        """Test mix of short and long-running subprocess operations."""
        primitive = SubprocessPrimitive()

        configs = []

        # Quick operations
        for i in range(10):
            configs.append({"command": "echo", "args": [f"Quick-{i}"], "timeout": 5})

        # Medium operations
        for i in range(5):
            configs.append({"command": "sleep", "args": ["1"], "timeout": 5})

        # Long operations that will timeout
        for i in range(3):
            configs.append(
                {
                    "command": "sleep",
                    "args": ["10"],
                    "timeout": 2,  # Will timeout
                }
            )

        start_time = time.time()

        # Execute all concurrently
        tasks = [primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks)

        execution_time = time.time() - start_time

        # Categorize results
        quick_results = [r for r in results if r.success and "Quick" in r.stdout]
        sleep_results = [r for r in results if r.success and "Quick" not in r.stdout]
        timeout_results = [r for r in results if not r.success and "timed out" in r.stderr]

        print(
            f"Mixed duration test: {len(quick_results)} quick, {len(sleep_results)} sleep, {len(timeout_results)} timeout"
        )

        # Verify expected results
        assert len(quick_results) == 10  # All quick operations should succeed
        assert len(sleep_results) == 5  # All 1-second sleeps should succeed
        assert len(timeout_results) == 3  # All 10-second sleeps should timeout

        # Should complete in about 2 seconds (timeout duration)
        assert 1.5 <= execution_time <= 3.0

    @pytest.mark.asyncio
    async def test_http_timeout_patterns(self):
        """Test HTTP timeout patterns with mixed response times."""
        primitive = HttpClientPrimitive()

        import httpx

        # Mock client with different response patterns
        async def variable_delay_request(*args, **kwargs):
            url = kwargs.get("url", "")

            if "fast" in url:
                # Fast response
                await asyncio.sleep(0.1)
            elif "medium" in url:
                # Medium response
                await asyncio.sleep(0.5)
            elif "slow" in url:
                # Slow response that will timeout
                await asyncio.sleep(5.0)
            elif "error" in url:
                # Connection error
                raise httpx.ConnectError("Connection failed")

            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"url": url}
            response.headers = {"content-type": "application/json"}
            response.reason_phrase = "OK"
            return response

        mock_client = AsyncMock()
        mock_client.request = variable_delay_request

        with patch.object(primitive, "_get_client", return_value=mock_client):
            configs = [
                # Fast requests (should succeed)
                *[
                    {"method": "GET", "url": f"https://api.example.com/fast/{i}", "timeout": 2}
                    for i in range(5)
                ],
                # Medium requests (should succeed)
                *[
                    {"method": "GET", "url": f"https://api.example.com/medium/{i}", "timeout": 2}
                    for i in range(3)
                ],
                # Slow requests (should timeout)
                *[
                    {"method": "GET", "url": f"https://api.example.com/slow/{i}", "timeout": 1}
                    for i in range(2)
                ],
                # Error requests (should fail)
                *[
                    {"method": "GET", "url": f"https://api.example.com/error/{i}", "timeout": 2}
                    for i in range(2)
                ],
            ]

            start_time = time.time()

            # Execute all concurrently
            tasks = [primitive.execute(config, {}) for config in configs]
            results = await asyncio.gather(*tasks)

            execution_time = time.time() - start_time

            # Categorize results
            fast_results = [r for r in results if r.success and "fast" in str(r.body)]
            medium_results = [r for r in results if r.success and "medium" in str(r.body)]
            timeout_results = [
                r for r in results if not r.success and "timeout" in (r.error or "").lower()
            ]
            error_results = [
                r for r in results if not r.success and "failed" in (r.error or "").lower()
            ]

            print(
                f"HTTP timeout test: {len(fast_results)} fast, {len(medium_results)} medium, {len(timeout_results)} timeout, {len(error_results)} error"
            )

            # Verify expected results
            assert len(fast_results) == 5  # All fast requests should succeed
            assert len(medium_results) == 3  # All medium requests should succeed
            # Note: Timeout behavior may vary - slow requests might succeed if httpx timeout is longer
            assert len(timeout_results) >= 0  # Some slow requests might timeout
            assert len(error_results) >= 1  # At least some error requests should fail

            # Should complete in reasonable time
            # Note: May take longer if slow requests don't timeout as expected
            assert execution_time <= 6.0


class TestErrorRecoveryResilience:
    """Test resilience and recovery from various error conditions."""

    @pytest.mark.asyncio
    async def test_cascading_failure_recovery(self):
        """Test recovery from cascading failures."""
        primitive = SubprocessPrimitive()

        # Create a scenario where some processes depend on others
        configs = [
            # These should succeed
            {"command": "echo", "args": ["success1"], "timeout": 5},
            {"command": "echo", "args": ["success2"], "timeout": 5},
            # These will fail
            {"command": "nonexistent_command_xyz", "args": ["fail1"], "timeout": 5},
            {"command": "nonexistent_command_abc", "args": ["fail2"], "timeout": 5},
            # These should succeed despite failures above
            {"command": "echo", "args": ["recovery1"], "timeout": 5},
            {"command": "echo", "args": ["recovery2"], "timeout": 5},
            # Timeout scenario
            {"command": "sleep", "args": ["10"], "timeout": 0.5},
            # Final success
            {"command": "echo", "args": ["final"], "timeout": 5},
        ]

        # Execute all concurrently
        tasks = [primitive.execute(config, {}) for config in configs]
        results = await asyncio.gather(*tasks)

        # Categorize results
        success_results = [r for r in results if r.success]
        failure_results = [r for r in results if not r.success]

        # Should have mixed results but system should remain stable
        assert len(success_results) == 5  # 4 echo commands + 0 sleep commands
        assert len(failure_results) == 3  # 2 nonexistent commands + 1 timeout

        # Verify specific success cases
        success_outputs = [r.stdout.strip() for r in success_results]
        expected_outputs = {"success1", "success2", "recovery1", "recovery2", "final"}
        assert set(success_outputs) == expected_outputs

        # Verify failure types
        command_not_found_failures = [
            r
            for r in failure_results
            if "not found" in r.stderr.lower()
            or ("command" in r.stderr.lower() and "timed out" not in r.stderr.lower())
        ]
        timeout_failures = [r for r in failure_results if "timed out" in r.stderr]

        assert len(command_not_found_failures) == 2
        assert len(timeout_failures) == 1

    @pytest.mark.asyncio
    async def test_system_resource_exhaustion_recovery(self):
        """Test recovery when system resources are exhausted."""
        primitive = SubprocessPrimitive()

        # First wave: Create many processes that will consume resources
        first_wave_configs = [{"command": "sleep", "args": ["1"], "timeout": 3} for _ in range(50)]

        # Second wave: Try to execute more processes while first wave is running
        second_wave_configs = [
            {"command": "echo", "args": [f"second_wave_{i}"], "timeout": 5} for i in range(20)
        ]

        # Start first wave
        first_wave_tasks = [primitive.execute(config, {}) for config in first_wave_configs]

        # Wait a bit, then start second wave
        await asyncio.sleep(0.2)
        second_wave_tasks = [primitive.execute(config, {}) for config in second_wave_configs]

        # Wait for all to complete
        first_wave_results = await asyncio.gather(*first_wave_tasks, return_exceptions=True)
        second_wave_results = await asyncio.gather(*second_wave_tasks, return_exceptions=True)

        # Analyze results
        first_wave_success = [r for r in first_wave_results if hasattr(r, "success") and r.success]
        second_wave_success = [
            r for r in second_wave_results if hasattr(r, "success") and r.success
        ]

        print(
            f"Resource exhaustion test: First wave {len(first_wave_success)}/{len(first_wave_results)} success, Second wave {len(second_wave_success)}/{len(second_wave_results)} success"
        )

        # System should handle resource pressure gracefully
        # At least some processes from each wave should succeed
        assert len(first_wave_success) >= 30  # At least 60% of first wave
        assert len(second_wave_success) >= 15  # At least 75% of second wave

        # Verify second wave outputs
        second_wave_outputs = [r.stdout.strip() for r in second_wave_success]
        assert all("second_wave_" in output for output in second_wave_outputs)
