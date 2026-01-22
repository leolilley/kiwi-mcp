"""
Tests for GitHelper class.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from kiwi_mcp.runtime.git_helper import GitHelper, GitStatus, GitDiff


class TestGitHelper:
    @pytest.fixture
    def git_helper(self, tmp_path):
        """Create GitHelper instance with temporary path."""
        return GitHelper(tmp_path)

    def test_is_available_with_git_repo(self, git_helper, tmp_path):
        """Test is_available returns True for git repository."""
        # Mock successful git rev-parse
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            assert git_helper.is_available() is True
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--git-dir"], cwd=tmp_path, capture_output=True
            )

    def test_is_available_without_git_repo(self, git_helper, tmp_path):
        """Test is_available returns False for non-git directory."""
        # Mock failed git rev-parse
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)

            assert git_helper.is_available() is False

    def test_is_available_no_git_command(self, git_helper):
        """Test is_available returns False when git command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert git_helper.is_available() is False

    @pytest.mark.asyncio
    async def test_status_parsing_no_changes(self, git_helper):
        """Test status parsing with no changes."""
        with patch.object(git_helper, "_run") as mock_run:
            mock_run.return_value = Mock(stdout="")

            status = await git_helper.status()

            assert isinstance(status, GitStatus)
            assert status.has_changes is False
            assert status.staged == []
            assert status.unstaged == []
            assert status.untracked == []

    @pytest.mark.asyncio
    async def test_status_parsing_with_changes(self, git_helper):
        """Test status parsing with various changes."""
        # Mock git status output (proper git status format)
        # Format: XY filename where X=index status, Y=working tree status
        mock_output = "M  file1.py\nA  file2.py\n?? file3.py\n M file4.py"

        with patch.object(git_helper, "_run") as mock_run:
            mock_run.return_value = Mock(stdout=mock_output)

            status = await git_helper.status()

            assert status.has_changes is True
            assert "file1.py" in status.staged  # M  -> staged modified
            assert "file2.py" in status.staged  # A  -> staged added
            assert "file4.py" in status.unstaged  # M  -> unstaged modified
            assert "file3.py" in status.untracked  # ?? -> untracked

    @pytest.mark.asyncio
    async def test_diff_stats_parsing(self, git_helper):
        """Test diff statistics parsing."""
        mock_output = " file1.py | 10 +++++++---\n file2.py | 5 ++---\n 2 files changed, 8 insertions(+), 4 deletions(-)"

        with patch.object(git_helper, "_run") as mock_run:
            mock_run.return_value = Mock(stdout=mock_output)

            diff = await git_helper.diff()

            assert isinstance(diff, GitDiff)
            assert diff.files_changed == 2
            assert diff.insertions == 8
            assert diff.deletions == 4
            assert diff.diff_text == mock_output

    @pytest.mark.asyncio
    async def test_add_all(self, git_helper):
        """Test staging all changes."""
        with patch.object(git_helper, "_run") as mock_run:
            await git_helper.add_all()
            mock_run.assert_called_once_with("add", "-A")

    @pytest.mark.asyncio
    async def test_commit_creation(self, git_helper):
        """Test commit creation and SHA retrieval."""
        with patch.object(git_helper, "_run") as mock_run:
            # Mock commit and rev-parse commands
            mock_run.side_effect = [
                Mock(),  # commit command
                Mock(stdout="abc123456789\n"),  # rev-parse command
            ]

            sha = await git_helper.commit("Test commit message")

            assert sha == "abc123456789"
            assert mock_run.call_count == 2
            mock_run.assert_any_call("commit", "-m", "Test commit message")
            mock_run.assert_any_call("rev-parse", "HEAD")

    @pytest.mark.asyncio
    async def test_reset_hard(self, git_helper):
        """Test hard reset behavior."""
        with patch.object(git_helper, "_run") as mock_run:
            await git_helper.reset_hard("HEAD~1")
            mock_run.assert_called_once_with("reset", "--hard", "HEAD~1")

        # Test default ref
        with patch.object(git_helper, "_run") as mock_run:
            await git_helper.reset_hard()
            mock_run.assert_called_once_with("reset", "--hard", "HEAD")

    @pytest.mark.asyncio
    async def test_run_method(self, git_helper, tmp_path):
        """Test the _run method subprocess execution."""
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = Mock(stdout="test output", returncode=0)

            result = await git_helper._run("status", "--porcelain")

            mock_subprocess.assert_called_once_with(
                ["git", "status", "--porcelain"], cwd=tmp_path, capture_output=True, text=True
            )
            assert result.stdout == "test output"
