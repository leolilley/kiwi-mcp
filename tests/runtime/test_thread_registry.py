"""
Tests for Thread Registry tool.
"""

import pytest
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import shutil

# Import the tool module
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    'thread_registry',
    Path(__file__).parent.parent.parent / '.ai' / 'tools' / 'threads' / 'thread_registry.py'
)
thread_registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thread_registry)

ThreadRegistry = thread_registry.ThreadRegistry
TranscriptWriter = thread_registry.TranscriptWriter
execute = thread_registry.execute


class TestThreadRegistry:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def db_path(self, temp_dir):
        """Create temporary database path."""
        return temp_dir / "registry.db"

    @pytest.fixture
    def registry(self, db_path):
        """Create ThreadRegistry instance."""
        return ThreadRegistry(db_path)

    def test_schema_initialization(self, registry, db_path):
        """Test that schema is initialized correctly."""
        conn = sqlite3.connect(str(db_path))
        try:
            # Check threads table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='threads'
            """)
            assert cursor.fetchone() is not None

            # Check thread_events table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='thread_events'
            """)
            assert cursor.fetchone() is not None

            # Check indexes exist
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_events_thread'
            """)
            assert cursor.fetchone() is not None

            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_threads_directive'
            """)
            assert cursor.fetchone() is not None

            # Check WAL mode
            cursor = conn.execute("PRAGMA journal_mode")
            assert cursor.fetchone()[0] == "wal"
        finally:
            conn.close()

    def test_register_thread(self, registry):
        """Test thread registration."""
        registry.register(
            thread_id="test_thread_1",
            directive_id="test_directive",
            permission_context={"capabilities": ["fs.read"]},
            cost_budget={"max_tokens": 1000},
        )

        status = registry.get_status("test_thread_1")
        assert status is not None
        assert status["thread_id"] == "test_thread_1"
        assert status["directive_id"] == "test_directive"
        assert status["status"] == "running"
        assert status["permission_context"]["capabilities"] == ["fs.read"]
        assert status["cost_budget"]["max_tokens"] == 1000

    def test_register_duplicate_thread(self, registry):
        """Test that duplicate thread registration fails."""
        registry.register(thread_id="test_thread_1", directive_id="test_directive")

        with pytest.raises(ValueError, match="already exists"):
            registry.register(thread_id="test_thread_1", directive_id="test_directive")

    def test_update_status(self, registry):
        """Test status updates."""
        registry.register(thread_id="test_thread_1", directive_id="test_directive")

        registry.update_status("test_thread_1", "completed", metadata={"usage": {"turns": 5}})

        status = registry.get_status("test_thread_1")
        assert status["status"] == "completed"
        assert status["total_usage"]["turns"] == 5

    def test_get_status_not_found(self, registry):
        """Test getting status of non-existent thread."""
        status = registry.get_status("nonexistent")
        assert status is None

    def test_query_by_directive(self, registry):
        """Test querying threads by directive."""
        registry.register(thread_id="thread_1", directive_id="directive_a")
        registry.register(thread_id="thread_2", directive_id="directive_a")
        registry.register(thread_id="thread_3", directive_id="directive_b")

        results = registry.query(directive_id="directive_a")
        assert len(results) == 2
        assert all(r["directive_id"] == "directive_a" for r in results)

    def test_query_by_status(self, registry):
        """Test querying threads by status."""
        registry.register(thread_id="thread_1", directive_id="directive_a")
        registry.register(thread_id="thread_2", directive_id="directive_a")
        registry.update_status("thread_1", "completed")

        results = registry.query(status="completed")
        assert len(results) == 1
        assert results[0]["thread_id"] == "thread_1"
        assert results[0]["status"] == "completed"

    def test_query_by_time_range(self, registry):
        """Test querying threads by time range."""
        registry.register(thread_id="thread_1", directive_id="directive_a")

        # Get creation time
        status = registry.get_status("thread_1")
        created_at = status["created_at"]

        # Query after creation
        results = registry.query(created_after=created_at)
        assert len(results) >= 1

        # Query before creation (should return empty)
        import datetime as dt
        before_time = (datetime.fromisoformat(created_at) - dt.timedelta(hours=1)).isoformat()
        results = registry.query(created_before=before_time)
        assert len(results) == 0

    def test_log_event(self, registry):
        """Test event logging."""
        registry.register(thread_id="test_thread_1", directive_id="test_directive")

        registry.log_event(
            thread_id="test_thread_1",
            event_type="tool_call",
            payload={"tool": "execute", "args_hash": "abc123"},
        )

        events = registry.get_events("test_thread_1")
        assert len(events) == 1
        assert events[0]["event_type"] == "tool_call"
        assert events[0]["payload"]["tool"] == "execute"

    def test_get_events_with_filter(self, registry):
        """Test getting events with type filter."""
        registry.register(thread_id="test_thread_1", directive_id="test_directive")

        registry.log_event("test_thread_1", "tool_call", {"tool": "execute"})
        registry.log_event("test_thread_1", "error", {"message": "Failed"})
        registry.log_event("test_thread_1", "tool_call", {"tool": "search"})

        events = registry.get_events("test_thread_1", event_type="tool_call")
        assert len(events) == 2
        assert all(e["event_type"] == "tool_call" for e in events)

    def test_parent_thread_relationship(self, registry):
        """Test parent thread relationships."""
        registry.register(thread_id="parent_thread", directive_id="directive_a")
        registry.register(
            thread_id="child_thread",
            directive_id="directive_a",
            parent_thread_id="parent_thread",
        )

        status = registry.get_status("child_thread")
        assert status["parent_thread_id"] == "parent_thread"


class TestTranscriptWriter:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def writer(self, temp_dir):
        """Create TranscriptWriter instance."""
        return TranscriptWriter(temp_dir)

    def test_write_event(self, writer, temp_dir):
        """Test writing events to transcript."""
        writer.write_event(
            thread_id="test_thread_1",
            event_type="turn_start",
            data={"turn": 1},
        )

        transcript_path = temp_dir / "test_thread_1" / "transcript.jsonl"
        assert transcript_path.exists()

        with open(transcript_path) as f:
            line = f.readline()
            event = json.loads(line)

        assert event["type"] == "turn_start"
        assert event["turn"] == 1
        assert "ts" in event

    def test_append_only(self, writer, temp_dir):
        """Test that transcript is append-only."""
        writer.write_event("test_thread_1", "turn_start", {"turn": 1})
        writer.write_event("test_thread_1", "user_message", {"content": "Hello"})
        writer.write_event("test_thread_1", "turn_end", {"turn": 1})

        transcript_path = temp_dir / "test_thread_1" / "transcript.jsonl"
        with open(transcript_path) as f:
            lines = f.readlines()

        assert len(lines) == 3
        assert json.loads(lines[0])["type"] == "turn_start"
        assert json.loads(lines[1])["type"] == "user_message"
        assert json.loads(lines[2])["type"] == "turn_end"


@pytest.mark.asyncio
class TestThreadRegistryTool:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    async def test_register_action(self, temp_dir):
        """Test register action via tool entry point."""
        result = await execute(
            "register",
            thread_id="test_thread_1",
            directive_id="test_directive",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        assert result["success"] is True
        assert result["thread_id"] == "test_thread_1"

    async def test_get_status_action(self, temp_dir):
        """Test get_status action via tool entry point."""
        # First register
        await execute(
            "register",
            thread_id="test_thread_1",
            directive_id="test_directive",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        # Then get status
        result = await execute(
            "get_status",
            thread_id="test_thread_1",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        assert result["success"] is True
        assert result["status"]["thread_id"] == "test_thread_1"
        assert result["status"]["status"] == "running"

    async def test_update_status_action(self, temp_dir):
        """Test update_status action via tool entry point."""
        # Register first
        await execute(
            "register",
            thread_id="test_thread_1",
            directive_id="test_directive",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        # Update status
        result = await execute(
            "update_status",
            thread_id="test_thread_1",
            status="completed",
            metadata={"usage": {"turns": 5}},
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        assert result["success"] is True
        assert result["status"] == "completed"

    async def test_query_action(self, temp_dir):
        """Test query action via tool entry point."""
        # Register multiple threads
        await execute(
            "register",
            thread_id="thread_1",
            directive_id="directive_a",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )
        await execute(
            "register",
            thread_id="thread_2",
            directive_id="directive_a",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        # Query
        result = await execute(
            "query",
            directive_id="directive_a",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["threads"]) == 2

    async def test_log_event_action(self, temp_dir):
        """Test log_event action via tool entry point."""
        # Register first
        await execute(
            "register",
            thread_id="test_thread_1",
            directive_id="test_directive",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
            transcript_dir=temp_dir / "transcripts",
        )

        # Log event
        result = await execute(
            "log_event",
            thread_id="test_thread_1",
            event_type="tool_call",
            payload={"tool": "execute"},
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
            transcript_dir=temp_dir / "transcripts",
        )

        assert result["success"] is True

        # Check transcript was written
        transcript_path = temp_dir / "transcripts" / "test_thread_1" / "transcript.jsonl"
        assert transcript_path.exists()

    async def test_get_events_action(self, temp_dir):
        """Test get_events action via tool entry point."""
        # Register and log events
        await execute(
            "register",
            thread_id="test_thread_1",
            directive_id="test_directive",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        await execute(
            "log_event",
            thread_id="test_thread_1",
            event_type="tool_call",
            payload={"tool": "execute"},
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        # Get events
        result = await execute(
            "get_events",
            thread_id="test_thread_1",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["events"][0]["event_type"] == "tool_call"

    async def test_unknown_action(self, temp_dir):
        """Test that unknown action returns error."""
        result = await execute(
            "unknown_action",
            _project_path=temp_dir,
            db_path=temp_dir / "registry.db",
        )

        assert result["success"] is False
        assert "Unknown action" in result["error"]
