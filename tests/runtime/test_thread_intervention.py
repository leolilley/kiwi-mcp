"""
Tests for Thread Intervention Tools.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import shutil

# Import the tool modules
import importlib.util
import sys

def load_tool_module(name, project_path=None):
    """Load a tool module dynamically from the actual project."""
    if project_path is None:
        project_path = Path(__file__).parent.parent.parent
    
    spec = importlib.util.spec_from_file_location(
        name,
        project_path / '.ai' / 'tools' / 'threads' / f'{name}.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
class TestReadTranscript:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def transcript_file(self, temp_dir):
        """Create a test transcript file."""
        thread_id = "test_thread_read"
        transcript_path = temp_dir / ".ai" / "threads" / thread_id / "transcript.jsonl"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write some test entries
        entries = [
            {"ts": "2026-01-26T10:00:00Z", "type": "user_message", "content": "Hello"},
            {"ts": "2026-01-26T10:00:01Z", "type": "assistant_message", "content": "Hi there"},
            {"ts": "2026-01-26T10:00:02Z", "type": "tool_call", "tool": "execute"},
        ]
        
        with open(transcript_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        
        return temp_dir, thread_id

    async def test_read_transcript_success(self, transcript_file):
        """Test reading transcript successfully."""
        temp_dir, thread_id = transcript_file
        
        read_tool = load_tool_module("read_transcript")
        result = await read_tool.execute(thread_id, last_n=10, _project_path=temp_dir)
        
        assert result["success"] is True
        assert result["thread_id"] == thread_id
        assert result["count"] == 3
        assert len(result["entries"]) == 3
        assert result["entries"][0]["type"] == "user_message"

    async def test_read_transcript_last_n(self, transcript_file):
        """Test reading only last N entries."""
        temp_dir, thread_id = transcript_file
        
        read_tool = load_tool_module("read_transcript")
        result = await read_tool.execute(thread_id, last_n=2, _project_path=temp_dir)
        
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["entries"]) == 2

    async def test_read_transcript_not_found(self, temp_dir):
        """Test reading non-existent transcript."""
        read_tool = load_tool_module("read_transcript")
        result = await read_tool.execute("nonexistent_thread", _project_path=temp_dir)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()


@pytest.mark.asyncio
class TestInjectMessage:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    async def test_inject_system_message(self, temp_dir):
        """Test injecting a system message."""
        thread_id = "test_thread_inject"
        inject_tool = load_tool_module("inject_message")
        
        result = await inject_tool.execute(
            thread_id=thread_id,
            role="system",
            content="Test system message",
            _project_path=temp_dir,
        )
        
        assert result["success"] is True
        assert result["thread_id"] == thread_id
        assert result["role"] == "system"
        assert result["content"] == "Test system message"
        
        # Verify transcript was written
        transcript_path = temp_dir / ".ai" / "threads" / thread_id / "transcript.jsonl"
        assert transcript_path.exists()
        
        with open(transcript_path) as f:
            entry = json.loads(f.readline())
            assert entry["type"] == "injected_message"
            assert entry["role"] == "system"
            assert entry["content"] == "Test system message"

    async def test_inject_user_message(self, temp_dir):
        """Test injecting a user message."""
        thread_id = "test_thread_inject_user"
        inject_tool = load_tool_module("inject_message")
        
        result = await inject_tool.execute(
            thread_id=thread_id,
            role="user",
            content="Test user message",
            _project_path=temp_dir,
        )
        
        assert result["success"] is True
        assert result["role"] == "user"

    async def test_inject_invalid_role(self, temp_dir):
        """Test injecting with invalid role."""
        inject_tool = load_tool_module("inject_message")
        
        result = await inject_tool.execute(
            thread_id="test",
            role="invalid",
            content="Test",
            _project_path=temp_dir,
        )
        
        assert result["success"] is False
        assert "Invalid role" in result["error"]


@pytest.mark.asyncio
class TestPauseThread:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    async def test_pause_thread(self, temp_dir):
        """Test pausing a thread."""
        # First register a thread
        thread_registry = load_tool_module("thread_registry")
        await thread_registry.execute(
            "register",
            thread_id="test_pause",
            directive_id="test",
            _project_path=temp_dir,
        )
        
        # Then pause it
        pause_tool = load_tool_module("pause_thread")
        result = await pause_tool.execute(
            thread_id="test_pause",
            reason="Test pause",
            _project_path=temp_dir,
        )
        
        assert result["success"] is True
        assert result["status"] == "paused"
        assert result["reason"] == "Test pause"
        
        # Verify status in registry
        status_result = await thread_registry.execute(
            "get_status",
            thread_id="test_pause",
            _project_path=temp_dir,
        )
        assert status_result["status"]["status"] == "paused"

    async def test_pause_nonexistent_thread(self, temp_dir):
        """Test pausing a non-existent thread."""
        pause_tool = load_tool_module("pause_thread")
        result = await pause_tool.execute(
            thread_id="nonexistent",
            _project_path=temp_dir,
        )
        
        assert result["success"] is False


@pytest.mark.asyncio
class TestResumeThread:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    async def test_resume_thread(self, temp_dir):
        """Test resuming a paused thread."""
        # Register and pause a thread
        thread_registry = load_tool_module("thread_registry")
        await thread_registry.execute(
            "register",
            thread_id="test_resume",
            directive_id="test",
            _project_path=temp_dir,
        )
        
        pause_tool = load_tool_module("pause_thread")
        await pause_tool.execute(
            thread_id="test_resume",
            _project_path=temp_dir,
        )
        
        # Resume it
        resume_tool = load_tool_module("resume_thread")
        result = await resume_tool.execute(
            thread_id="test_resume",
            _project_path=temp_dir,
        )
        
        assert result["success"] is True
        assert result["status"] == "running"
        
        # Verify status in registry
        status_result = await thread_registry.execute(
            "get_status",
            thread_id="test_resume",
            _project_path=temp_dir,
        )
        assert status_result["status"]["status"] == "running"

    async def test_resume_with_message(self, temp_dir):
        """Test resuming with injected message."""
        # Register and pause a thread
        thread_registry = load_tool_module("thread_registry")
        await thread_registry.execute(
            "register",
            thread_id="test_resume_msg",
            directive_id="test",
            _project_path=temp_dir,
        )
        
        pause_tool = load_tool_module("pause_thread")
        await pause_tool.execute(
            thread_id="test_resume_msg",
            _project_path=temp_dir,
        )
        
        # Resume with message
        resume_tool = load_tool_module("resume_thread")
        result = await resume_tool.execute(
            thread_id="test_resume_msg",
            inject_message="Resume message",
            _project_path=temp_dir,
        )
        
        assert result["success"] is True
        assert result["message_injected"] is True
        
        # Verify message was injected
        transcript_path = temp_dir / ".ai" / "threads" / "test_resume_msg" / "transcript.jsonl"
        if transcript_path.exists():
            with open(transcript_path) as f:
                lines = f.readlines()
                # Check if resume message is in transcript
                assert any("Resume message" in line for line in lines)

    async def test_resume_not_paused(self, temp_dir):
        """Test resuming a thread that's not paused."""
        # Register a running thread
        thread_registry = load_tool_module("thread_registry")
        await thread_registry.execute(
            "register",
            thread_id="test_resume_running",
            directive_id="test",
            _project_path=temp_dir,
        )
        
        # Try to resume (should fail)
        resume_tool = load_tool_module("resume_thread")
        result = await resume_tool.execute(
            thread_id="test_resume_running",
            _project_path=temp_dir,
        )
        
        assert result["success"] is False
        assert "not paused" in result["error"].lower()
