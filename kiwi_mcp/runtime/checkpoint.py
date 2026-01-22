from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import uuid
from typing import Optional
from .git_helper import GitHelper


@dataclass
class Checkpoint:
    id: str
    created_at: datetime
    session_id: str
    operation: str
    git_sha: Optional[str]
    context: dict


class CheckpointManager:
    def __init__(self, project_path: Path, git_helper: GitHelper):
        self.project_path = project_path
        self.checkpoints_dir = project_path / ".ai" / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.git = git_helper

    async def create(self, session_id: str, operation: str, context: dict = None) -> Checkpoint:
        """Create checkpoint before risky operation."""
        checkpoint_id = f"cp_{uuid.uuid4().hex[:12]}"

        # Create git commit if available
        git_sha = None
        if self.git.is_available():
            status = await self.git.status()
            if status.has_changes:
                await self.git.add_all()
                git_sha = await self.git.commit(f"checkpoint: {operation} ({checkpoint_id})")

        checkpoint = Checkpoint(
            id=checkpoint_id,
            created_at=datetime.now(),
            session_id=session_id,
            operation=operation,
            git_sha=git_sha,
            context=context or {},
        )

        # Persist metadata
        self._save(checkpoint)

        return checkpoint

    async def restore(self, checkpoint_id: str) -> bool:
        """Restore state to checkpoint."""
        checkpoint = self._load(checkpoint_id)
        if not checkpoint:
            return False

        if checkpoint.git_sha and self.git.is_available():
            await self.git.reset_hard(checkpoint.git_sha)

        return True

    def list(self, session_id: str = None) -> list[Checkpoint]:
        """List all checkpoints, optionally filtered by session."""
        checkpoints = []
        for path in self.checkpoints_dir.glob("*.json"):
            checkpoint = self._load(path.stem)
            if checkpoint and (not session_id or checkpoint.session_id == session_id):
                checkpoints.append(checkpoint)

        # Sort by creation time (most recent first)
        return sorted(checkpoints, key=lambda c: c.created_at, reverse=True)

    def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint (metadata only, git history preserved)."""
        path = self.checkpoints_dir / f"{checkpoint_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def _save(self, checkpoint: Checkpoint) -> None:
        path = self.checkpoints_dir / f"{checkpoint.id}.json"
        path.write_text(
            json.dumps(
                {
                    "id": checkpoint.id,
                    "created_at": checkpoint.created_at.isoformat(),
                    "session_id": checkpoint.session_id,
                    "operation": checkpoint.operation,
                    "git_sha": checkpoint.git_sha,
                    "context": checkpoint.context,
                },
                indent=2,
            )
        )

    def _load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        path = self.checkpoints_dir / f"{checkpoint_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Checkpoint(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            session_id=data["session_id"],
            operation=data["operation"],
            git_sha=data["git_sha"],
            context=data["context"],
        )
