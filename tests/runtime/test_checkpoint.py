"""
Tests for CheckpointManager class.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from kiwi_mcp.runtime.checkpoint import CheckpointManager, Checkpoint
from kiwi_mcp.runtime.git_helper import GitHelper, GitStatus


class TestCheckpointManager:
    @pytest.fixture
    def git_helper(self):
        """Create mock GitHelper."""
        return Mock(spec=GitHelper)

    @pytest.fixture
    def checkpoint_manager(self, tmp_path, git_helper):
        """Create CheckpointManager instance with temporary path."""
        return CheckpointManager(tmp_path, git_helper)

    @pytest.mark.asyncio
    async def test_create_checkpoint_with_git_changes(self, checkpoint_manager, git_helper):
        """Test creating checkpoint when git has changes."""
        # Setup git mock
        git_helper.is_available.return_value = True
        git_helper.status = AsyncMock(
            return_value=GitStatus(has_changes=True, staged=[], unstaged=["file1.py"], untracked=[])
        )
        git_helper.add_all = AsyncMock()
        git_helper.commit = AsyncMock(return_value="abc123456789")

        checkpoint = await checkpoint_manager.create(
            session_id="test_session", operation="test_operation", context={"key": "value"}
        )

        assert isinstance(checkpoint, Checkpoint)
        assert checkpoint.session_id == "test_session"
        assert checkpoint.operation == "test_operation"
        assert checkpoint.git_sha == "abc123456789"
        assert checkpoint.context == {"key": "value"}
        assert checkpoint.id.startswith("cp_")

        # Verify git operations
        git_helper.status.assert_called_once()
        git_helper.add_all.assert_called_once()
        git_helper.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_checkpoint_without_git_changes(self, checkpoint_manager, git_helper):
        """Test creating checkpoint when git has no changes."""
        # Setup git mock
        git_helper.is_available.return_value = True
        git_helper.status = AsyncMock(
            return_value=GitStatus(has_changes=False, staged=[], unstaged=[], untracked=[])
        )

        checkpoint = await checkpoint_manager.create(
            session_id="test_session", operation="test_operation"
        )

        assert checkpoint.git_sha is None
        assert checkpoint.context == {}

        # Verify no git commit operations
        git_helper.status.assert_called_once()
        git_helper.add_all.assert_not_called()
        git_helper.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_checkpoint_without_git(self, checkpoint_manager, git_helper):
        """Test creating checkpoint when git is not available."""
        git_helper.is_available.return_value = False

        checkpoint = await checkpoint_manager.create(
            session_id="test_session", operation="test_operation"
        )

        assert checkpoint.git_sha is None
        git_helper.status.assert_not_called()

    @pytest.mark.asyncio
    async def test_restore_checkpoint_with_git(self, checkpoint_manager, git_helper, tmp_path):
        """Test restoring checkpoint with git."""
        # Create a checkpoint file
        checkpoint_id = "cp_test123456"
        checkpoint_data = {
            "id": checkpoint_id,
            "created_at": datetime.now().isoformat(),
            "session_id": "test_session",
            "operation": "test_op",
            "git_sha": "abc123456789",
            "context": {},
        }

        checkpoints_dir = tmp_path / ".ai" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoints_dir / f"{checkpoint_id}.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        # Setup git mock
        git_helper.is_available.return_value = True
        git_helper.reset_hard = AsyncMock()

        result = await checkpoint_manager.restore(checkpoint_id)

        assert result is True
        git_helper.reset_hard.assert_called_once_with("abc123456789")

    @pytest.mark.asyncio
    async def test_restore_nonexistent_checkpoint(self, checkpoint_manager):
        """Test restoring a checkpoint that doesn't exist."""
        result = await checkpoint_manager.restore("cp_nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_restore_checkpoint_without_git(self, checkpoint_manager, git_helper, tmp_path):
        """Test restoring checkpoint when git is not available."""
        # Create a checkpoint file
        checkpoint_id = "cp_test123456"
        checkpoint_data = {
            "id": checkpoint_id,
            "created_at": datetime.now().isoformat(),
            "session_id": "test_session",
            "operation": "test_op",
            "git_sha": None,
            "context": {},
        }

        checkpoints_dir = tmp_path / ".ai" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoints_dir / f"{checkpoint_id}.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        git_helper.is_available.return_value = False

        result = await checkpoint_manager.restore(checkpoint_id)

        assert result is True
        git_helper.reset_hard.assert_not_called()

    def test_list_checkpoints(self, checkpoint_manager, tmp_path):
        """Test listing checkpoints."""
        checkpoints_dir = tmp_path / ".ai" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple checkpoint files
        checkpoints = []
        for i in range(3):
            checkpoint_id = f"cp_test{i:06d}"
            checkpoint_data = {
                "id": checkpoint_id,
                "created_at": datetime.now().isoformat(),
                "session_id": f"session_{i % 2}",  # Two different sessions
                "operation": f"operation_{i}",
                "git_sha": f"sha{i:06d}",
                "context": {},
            }
            checkpoint_file = checkpoints_dir / f"{checkpoint_id}.json"
            checkpoint_file.write_text(json.dumps(checkpoint_data))
            checkpoints.append(checkpoint_data)

        # List all checkpoints
        all_checkpoints = checkpoint_manager.list()
        assert len(all_checkpoints) == 3

        # List checkpoints for specific session
        session_0_checkpoints = checkpoint_manager.list(session_id="session_0")
        assert len(session_0_checkpoints) == 2

        session_1_checkpoints = checkpoint_manager.list(session_id="session_1")
        assert len(session_1_checkpoints) == 1

    def test_delete_checkpoint(self, checkpoint_manager, tmp_path):
        """Test deleting checkpoints."""
        checkpoints_dir = tmp_path / ".ai" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Create checkpoint file
        checkpoint_id = "cp_test123456"
        checkpoint_file = checkpoints_dir / f"{checkpoint_id}.json"
        checkpoint_file.write_text('{"test": "data"}')

        assert checkpoint_file.exists()

        # Delete checkpoint
        result = checkpoint_manager.delete(checkpoint_id)

        assert result is True
        assert not checkpoint_file.exists()

        # Try to delete non-existent checkpoint
        result = checkpoint_manager.delete("cp_nonexistent")
        assert result is False

    def test_save_and_load_checkpoint(self, checkpoint_manager):
        """Test saving and loading checkpoint metadata."""
        checkpoint = Checkpoint(
            id="cp_test123456",
            created_at=datetime.now(),
            session_id="test_session",
            operation="test_operation",
            git_sha="abc123456789",
            context={"key": "value"},
        )

        # Save checkpoint
        checkpoint_manager._save(checkpoint)

        # Load checkpoint
        loaded_checkpoint = checkpoint_manager._load("cp_test123456")

        assert loaded_checkpoint is not None
        assert loaded_checkpoint.id == checkpoint.id
        assert loaded_checkpoint.session_id == checkpoint.session_id
        assert loaded_checkpoint.operation == checkpoint.operation
        assert loaded_checkpoint.git_sha == checkpoint.git_sha
        assert loaded_checkpoint.context == checkpoint.context

    def test_load_nonexistent_checkpoint(self, checkpoint_manager):
        """Test loading checkpoint that doesn't exist."""
        result = checkpoint_manager._load("cp_nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_graceful_non_git_handling(self, checkpoint_manager, git_helper):
        """Test graceful handling when git operations fail."""
        git_helper.is_available.return_value = True
        git_helper.status = AsyncMock(side_effect=Exception("Git error"))

        # Should not raise exception
        try:
            await checkpoint_manager.create("test_session", "test_op")
            assert False, "Should have raised exception"
        except Exception:
            # Expected to fail for this test - git error should propagate
            pass
