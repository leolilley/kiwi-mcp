import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class GitStatus:
    has_changes: bool
    staged: list[str]
    unstaged: list[str]
    untracked: list[str]


@dataclass
class GitDiff:
    files_changed: int
    insertions: int
    deletions: int
    diff_text: str


class GitHelper:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def is_available(self) -> bool:
        """Check if this is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"], cwd=self.repo_path, capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    async def status(self) -> GitStatus:
        """Get current repository status."""
        result = await self._run("status", "--porcelain")
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Git status format: XY filename (where X=index, Y=working tree)
        # For " A  file2.py": X=' ', Y='A' means file2.py is staged as new (A in index position)
        # But that's wrong. Let me check git documentation...

        # Actually, git status shows:
        # First char = index status (staged changes)
        # Second char = working tree status (unstaged changes)

        staged = []
        unstaged = []
        untracked = []

        for line in lines:
            if len(line) < 3:
                continue
            if line[:2] == "??":
                untracked.append(line[3:])
            else:
                index_status = line[0]
                wt_status = line[1]
                filename = line[3:]

                if index_status != " " and index_status != "?":
                    staged.append(filename)
                if wt_status != " " and wt_status != "?":
                    unstaged.append(filename)

        return GitStatus(
            has_changes=bool(lines), staged=staged, unstaged=unstaged, untracked=untracked
        )

    async def diff(self, staged: bool = False) -> GitDiff:
        """Get diff of changes."""
        args = ["diff", "--stat"]
        if staged:
            args.append("--staged")

        result = await self._run(*args)
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Parse diff stat output
        files_changed = 0
        insertions = 0
        deletions = 0

        for line in lines:
            if "file" in line and "changed" in line:
                # Summary line: "3 files changed, 45 insertions(+), 12 deletions(-)"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        if "file" in parts[i + 1]:
                            files_changed = int(part)
                        elif "insertion" in parts[i + 1]:
                            insertions = int(part)
                        elif "deletion" in parts[i + 1]:
                            deletions = int(part)

        return GitDiff(
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            diff_text=result.stdout,
        )

    async def add_all(self) -> None:
        """Stage all changes."""
        await self._run("add", "-A")

    async def commit(self, message: str) -> str:
        """Create commit, return SHA."""
        await self._run("commit", "-m", message)
        result = await self._run("rev-parse", "HEAD")
        return result.stdout.strip()

    async def reset_hard(self, ref: str = "HEAD") -> None:
        """Reset to ref, discarding changes."""
        await self._run("reset", "--hard", ref)

    async def _run(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.repo_path, capture_output=True, text=True)
