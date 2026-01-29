"""Tests for telemetry tools and library."""

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

# Add tools to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".ai" / "tools" / "core"))

from telemetry_lib import TelemetryContext, TelemetryStore, get_user_path


class TestTelemetryStore:
    """Test TelemetryStore class."""

    def test_record_execution_creates_file(self):
        """First execution creates telemetry.yaml."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            assert not store.path.exists()

            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
            )

            assert store.path.exists()
            data = yaml.safe_load(store.path.read_text())
            assert "test/item" in data["items"]

    def test_record_execution_increments_counters(self):
        """Multiple runs increment counters correctly."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            # First run: success
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
            )

            item = store.get("test/item")
            assert item["total_runs"] == 1
            assert item["success_count"] == 1
            assert item["failure_count"] == 0

            # Second run: success
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=110.0,
            )

            item = store.get("test/item")
            assert item["total_runs"] == 2
            assert item["success_count"] == 2

            # Third run: failure
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="failure",
                duration_ms=50.0,
                error="Test error",
            )

            item = store.get("test/item")
            assert item["total_runs"] == 3
            assert item["success_count"] == 2
            assert item["failure_count"] == 1
            assert item["last_error"] == "Test error"

    def test_running_average_calculation(self):
        """avg_duration_ms computed correctly."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            # Record three runs: 100ms, 120ms, 140ms
            # Expected average: (100 + 120 + 140) / 3 = 120
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
            )
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=120.0,
            )
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=140.0,
            )

            item = store.get("test/item")
            assert abs(item["avg_duration_ms"] - 120.0) < 0.1

    def test_clear_single_item(self):
        """Clears only specified item."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            # Create two items
            store.record_execution(
                item_id="test/item1",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
            )
            store.record_execution(
                item_id="test/item2",
                item_type="tool",
                outcome="success",
                duration_ms=200.0,
            )

            # Clear only item1
            store.clear("test/item1")

            assert store.get("test/item1") is None
            assert store.get("test/item2") is not None

    def test_clear_all(self):
        """Clears entire items dict."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            # Create items
            store.record_execution(
                item_id="test/item1",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
            )
            store.record_execution(
                item_id="test/item2",
                item_type="tool",
                outcome="success",
                duration_ms=200.0,
            )

            # Clear all
            store.clear(None)

            data = yaml.safe_load(store.path.read_text())
            assert data["items"] == {}

    def test_concurrent_writes(self):
        """File locking handles concurrent writes."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)

            def record_item(item_num: int):
                store = TelemetryStore(user_path)
                for i in range(5):
                    store.record_execution(
                        item_id=f"test/item{item_num}",
                        item_type="directive",
                        outcome="success",
                        duration_ms=100.0,
                    )
                    time.sleep(0.001)

            # Start multiple threads
            threads = [threading.Thread(target=record_item, args=(i,)) for i in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Verify all writes succeeded
            store = TelemetryStore(user_path)
            item = store.get("test/item0")
            assert item["total_runs"] == 5

            item = store.get("test/item1")
            assert item["total_runs"] == 5

            item = store.get("test/item2")
            assert item["total_runs"] == 5

    def test_tracking_primitives(self):
        """Records HTTP and subprocess calls."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            store.record_execution(
                item_id="test/item",
                item_type="tool",
                outcome="success",
                duration_ms=100.0,
                http_calls=5,
                subprocess_calls=2,
            )

            item = store.get("test/item")
            assert item["http_calls"] == 5
            assert item["subprocess_calls"] == 2

    def test_path_tracking(self):
        """Tracks and deduplicates paths."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            # Record with path
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
                path="/home/user/.ai/directives/test/item.md",
            )

            item = store.get("test/item")
            assert "/home/user/.ai/directives/test/item.md" in item["paths"]

            # Record same item with different path
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
                path="/home/user/project/.ai/directives/item.md",
            )

            item = store.get("test/item")
            assert len(item["paths"]) == 2

            # Record with same path (should not duplicate)
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
                path="/home/user/.ai/directives/test/item.md",
            )

            item = store.get("test/item")
            assert len(item["paths"]) == 2

    def test_last_execution_info(self):
        """Tracks last execution info."""
        with TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir)
            store = TelemetryStore(user_path)

            # Successful run
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="success",
                duration_ms=100.0,
            )

            item = store.get("test/item")
            assert item["last_outcome"] == "success"
            assert item["last_error"] is None
            assert item["last_run"] is not None

            # Failed run
            store.record_execution(
                item_id="test/item",
                item_type="directive",
                outcome="failure",
                duration_ms=100.0,
                error="Something broke",
            )

            item = store.get("test/item")
            assert item["last_outcome"] == "failure"
            assert item["last_error"] == "Something broke"


class TestTelemetryContext:
    """Test TelemetryContext dataclass."""

    def test_context_initialization(self):
        """Context initializes with zero counters."""
        ctx = TelemetryContext()
        assert ctx.http_calls == 0
        assert ctx.subprocess_calls == 0

    def test_context_tracking(self):
        """Context tracks calls."""
        ctx = TelemetryContext()
        ctx.http_calls += 5
        ctx.subprocess_calls += 2
        assert ctx.http_calls == 5
        assert ctx.subprocess_calls == 2
