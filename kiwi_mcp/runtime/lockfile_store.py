"""
Kernel-level lockfile storage for reproducible tool execution.

Implements hierarchical local-first storage with project/user precedence.
Lockfiles capture resolved chains with exact versions and integrity hashes.

Storage Structure:
  .ai/lockfiles/
    {category}/
      {tool_name}@{version}.lock.json
      {tool_name}@{version}.{chain_hash}.lock.json  # Multiple chains if needed
    .index.json

  ~/.ai/lockfiles/
    {category}/
      {tool_name}@{version}.lock.json
    .index.json
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

from kiwi_mcp.primitives.lockfile import (
    Lockfile,
    LockfileManager,
    LockfileError,
)

logger = logging.getLogger(__name__)


@dataclass
class LockfileMetadata:
    """Metadata about a lockfile for listing and management."""

    tool_id: str
    version: str
    category: str
    chain_hash: str
    path: Path
    scope: Literal["project", "user"]
    created_at: str
    last_validated: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of lockfile validation against a resolved chain."""

    is_valid: bool
    issues: List[str] = field(default_factory=list)
    lockfile: Optional[Lockfile] = None


class LockfileStore:
    """
    Kernel-level lockfile storage with hierarchical project/user structure.

    Features:
    - Local-first storage (no network dependency)
    - Project and user scopes (project takes precedence)
    - Category-based organization
    - Fast index-based lookups
    - Stale lockfile pruning
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        userspace_root: Optional[Path] = None,
    ):
        """
        Initialize lockfile store.

        Args:
            project_root: Project root containing .ai/ folder (optional)
            userspace_root: User home directory for global lockfiles (default: ~/.ai)
        """
        # Project-level lockfiles
        self.project_root = Path(project_root) if project_root else None
        self.project_lockfiles = (
            self.project_root / ".ai" / "lockfiles" if self.project_root else None
        )

        # User-level lockfiles
        if userspace_root:
            self.user_root = Path(userspace_root)
        else:
            self.user_root = Path.home() / ".ai"
        self.user_lockfiles = self.user_root / "lockfiles"

        # Lockfile manager for freeze/validate operations
        self.manager = LockfileManager()

        # In-memory index cache
        self._project_index: Optional[Dict[str, Any]] = None
        self._user_index: Optional[Dict[str, Any]] = None

    def freeze(
        self,
        tool_id: str,
        version: str,
        category: str,
        chain: List[Dict[str, Any]],
        registry_url: Optional[str] = None,
    ) -> Lockfile:
        """
        Create a lockfile from a resolved chain.

        Args:
            tool_id: Tool identifier
            version: Tool version
            category: Tool category (for storage organization)
            chain: Resolved chain from ChainResolver
            registry_url: Optional registry URL for provenance

        Returns:
            Generated Lockfile
        """
        if not chain:
            raise LockfileError(f"Cannot create lockfile from empty chain for {tool_id}")

        # Ensure root tool matches
        root_tool = chain[0]
        if root_tool.get("tool_id") != tool_id:
            logger.warning(
                f"Root tool mismatch: expected {tool_id}, got {root_tool.get('tool_id')}"
            )

        # Use LockfileManager to create the lockfile
        lockfile = self.manager.freeze(chain, registry_url)

        logger.info(f"Froze lockfile for {tool_id}@{version} with {len(chain)} entries")

        return lockfile

    def save(
        self,
        lockfile: Lockfile,
        category: str,
        scope: Literal["project", "user"] = "project",
        chain_hash: Optional[str] = None,
    ) -> Path:
        """
        Save lockfile to filesystem.

        Args:
            lockfile: Lockfile to save
            category: Category for organization
            scope: Where to save (project or user)
            chain_hash: Optional chain hash for multiple chains per tool+version

        Returns:
            Path where lockfile was saved

        Raises:
            LockfileError: If project_root not set for project scope
        """
        if scope == "project":
            if not self.project_lockfiles:
                raise LockfileError("Cannot save to project scope: project_root not set")
            base_dir = self.project_lockfiles
        else:
            base_dir = self.user_lockfiles

        # Create category directory
        category_dir = base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Build filename
        tool_id = lockfile.root.tool_id
        version = lockfile.root.version

        if chain_hash:
            filename = f"{tool_id}@{version}.{chain_hash[:12]}.lock.json"
        else:
            filename = f"{tool_id}@{version}.lock.json"

        filepath = category_dir / filename

        # Save using LockfileManager
        self.manager.save(lockfile, filepath)

        # Update index
        self._update_index(
            tool_id=tool_id,
            version=version,
            category=category,
            filepath=filepath,
            scope=scope,
            lockfile=lockfile,
        )

        logger.info(f"Saved lockfile to {filepath}")

        return filepath

    def load(
        self,
        tool_id: str,
        version: str,
        category: str,
    ) -> Optional[Lockfile]:
        """
        Load lockfile with project > user precedence.

        Args:
            tool_id: Tool identifier
            version: Tool version
            category: Tool category

        Returns:
            Loaded Lockfile or None if not found
        """
        # Try project first (higher precedence)
        if self.project_lockfiles:
            lockfile = self._load_from_scope(tool_id, version, category, "project")
            if lockfile:
                logger.debug(f"Loaded lockfile for {tool_id}@{version} from project")
                return lockfile

        # Fall back to user
        lockfile = self._load_from_scope(tool_id, version, category, "user")
        if lockfile:
            logger.debug(f"Loaded lockfile for {tool_id}@{version} from user")
            return lockfile

        logger.debug(f"No lockfile found for {tool_id}@{version}")
        return None

    def _load_from_scope(
        self,
        tool_id: str,
        version: str,
        category: str,
        scope: Literal["project", "user"],
    ) -> Optional[Lockfile]:
        """Load lockfile from specific scope."""
        base_dir = self.project_lockfiles if scope == "project" else self.user_lockfiles

        if not base_dir:
            return None

        # Build expected path
        filename = f"{tool_id}@{version}.lock.json"
        filepath = base_dir / category / filename

        if not filepath.exists():
            return None

        try:
            lockfile = self.manager.load(filepath)

            # Update last_validated in index
            self._touch_lockfile(tool_id, version, category, scope)

            return lockfile
        except LockfileError as e:
            logger.error(f"Failed to load lockfile from {filepath}: {e}")
            return None

    def validate_chain(
        self,
        lockfile: Lockfile,
        chain: List[Dict[str, Any]],
    ) -> ValidationResult:
        """
        Validate a resolved chain against a lockfile.

        Args:
            lockfile: Expected lockfile
            chain: Resolved chain to validate

        Returns:
            ValidationResult with validity and issues
        """
        result = self.manager.validate_against_chain(lockfile, chain)

        return ValidationResult(
            is_valid=result["valid"],
            issues=result["issues"],
            lockfile=lockfile,
        )

    def list_lockfiles(
        self,
        category: Optional[str] = None,
        scope: Optional[Literal["project", "user"]] = None,
    ) -> List[LockfileMetadata]:
        """
        List all lockfiles, optionally filtered by category and/or scope.

        Args:
            category: Optional category filter
            scope: Optional scope filter (project, user, or both if None)

        Returns:
            List of lockfile metadata
        """
        lockfiles = []

        # List from project
        if (scope is None or scope == "project") and self.project_lockfiles:
            lockfiles.extend(self._list_from_scope("project", category))

        # List from user
        if scope is None or scope == "user":
            lockfiles.extend(self._list_from_scope("user", category))

        # Sort by tool_id, then version
        lockfiles.sort(key=lambda x: (x.tool_id, x.version))

        return lockfiles

    def _list_from_scope(
        self,
        scope: Literal["project", "user"],
        category_filter: Optional[str] = None,
    ) -> List[LockfileMetadata]:
        """List lockfiles from a specific scope."""
        base_dir = self.project_lockfiles if scope == "project" else self.user_lockfiles

        if not base_dir or not base_dir.exists():
            return []

        lockfiles = []

        # Iterate through categories
        for category_dir in base_dir.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name

            # Apply category filter
            if category_filter and category != category_filter:
                continue

            # Find all .lock.json files
            for lockfile_path in category_dir.glob("*.lock.json"):
                # Parse filename: {tool_id}@{version}[.{chain_hash}].lock.json
                name = lockfile_path.stem  # Remove .json
                if name.endswith(".lock"):
                    name = name[:-5]  # Remove .lock

                # Split on @ to get tool_id and rest
                parts = name.split("@", 1)
                if len(parts) != 2:
                    logger.warning(f"Invalid lockfile name: {lockfile_path}")
                    continue

                tool_id = parts[0]
                version_and_hash = parts[1]

                # Check if there's a chain hash
                # Version format: X.Y.Z (3 parts with dots)
                # Chain hash format: X.Y.Z.HASH (4+ parts with dots)
                version_parts = version_and_hash.split(".")
                if len(version_parts) > 3:
                    # Has chain hash - version is first 3 parts, rest is hash
                    version = ".".join(version_parts[:3])
                    chain_hash = ".".join(version_parts[3:])
                else:
                    # No chain hash - entire string is version
                    version = version_and_hash
                    chain_hash = "default"

                # Get metadata from index or file
                metadata = self._get_lockfile_metadata(
                    tool_id=tool_id,
                    version=version,
                    category=category,
                    chain_hash=chain_hash,
                    path=lockfile_path,
                    scope=scope,
                )

                lockfiles.append(metadata)

        return lockfiles

    def _get_lockfile_metadata(
        self,
        tool_id: str,
        version: str,
        category: str,
        chain_hash: str,
        path: Path,
        scope: Literal["project", "user"],
    ) -> LockfileMetadata:
        """Get metadata for a lockfile."""
        # Check index first
        index = self._load_index(scope)
        key = f"{category}/{tool_id}@{version}"

        if key in index.get("lockfiles", {}):
            entry = index["lockfiles"][key]
            return LockfileMetadata(
                tool_id=tool_id,
                version=version,
                category=category,
                chain_hash=entry.get("chain_hash", chain_hash),
                path=path,
                scope=scope,
                created_at=entry.get("created_at", "unknown"),
                last_validated=entry.get("last_validated"),
            )

        # Fall back to file metadata
        stat = path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()

        return LockfileMetadata(
            tool_id=tool_id,
            version=version,
            category=category,
            chain_hash=chain_hash,
            path=path,
            scope=scope,
            created_at=created_at,
            last_validated=None,
        )

    def prune_stale(
        self,
        max_age_days: int = 90,
        scope: Optional[Literal["project", "user"]] = None,
    ) -> int:
        """
        Remove lockfiles not validated recently.

        Args:
            max_age_days: Maximum age in days without validation
            scope: Optional scope filter (prune both if None)

        Returns:
            Number of lockfiles pruned
        """
        now = datetime.now(timezone.utc)
        pruned = 0

        # Prune from project
        if (scope is None or scope == "project") and self.project_lockfiles:
            pruned += self._prune_from_scope("project", now, max_age_days)

        # Prune from user
        if scope is None or scope == "user":
            pruned += self._prune_from_scope("user", now, max_age_days)

        logger.info(f"Pruned {pruned} stale lockfiles (>{max_age_days} days)")

        return pruned

    def _prune_from_scope(
        self,
        scope: Literal["project", "user"],
        now: datetime,
        max_age_days: int,
    ) -> int:
        """Prune lockfiles from a specific scope."""
        base_dir = self.project_lockfiles if scope == "project" else self.user_lockfiles

        if not base_dir or not base_dir.exists():
            return 0

        index = self._load_index(scope)
        pruned = 0

        # Check each lockfile
        for key, entry in list(index.get("lockfiles", {}).items()):
            last_validated = entry.get("last_validated")

            if not last_validated:
                # No validation timestamp - check creation time
                created_at = entry.get("created_at")
                if created_at:
                    created_dt = datetime.fromisoformat(created_at)
                    age_days = (now - created_dt).days

                    if age_days > max_age_days:
                        self._delete_lockfile_by_key(key, scope, index)
                        pruned += 1
            else:
                # Check last validation time
                validated_dt = datetime.fromisoformat(last_validated)
                age_days = (now - validated_dt).days

                if age_days > max_age_days:
                    self._delete_lockfile_by_key(key, scope, index)
                    pruned += 1

        # Save updated index
        self._save_index(scope, index)

        return pruned

    def _delete_lockfile_by_key(
        self,
        key: str,
        scope: Literal["project", "user"],
        index: Dict[str, Any],
    ) -> None:
        """Delete a lockfile by its index key."""
        entry = index["lockfiles"].get(key)
        if not entry:
            return

        # Get file path
        base_dir = self.project_lockfiles if scope == "project" else self.user_lockfiles
        filepath = base_dir / entry["path"]

        # Delete file
        if filepath.exists():
            filepath.unlink()
            logger.debug(f"Deleted stale lockfile: {filepath}")

        # Remove from index
        del index["lockfiles"][key]

    def _load_index(self, scope: Literal["project", "user"]) -> Dict[str, Any]:
        """Load index for a scope."""
        # Check cache
        if scope == "project":
            if self._project_index is not None:
                return self._project_index
            base_dir = self.project_lockfiles
        else:
            if self._user_index is not None:
                return self._user_index
            base_dir = self.user_lockfiles

        if not base_dir:
            return {"version": "1", "lockfiles": {}}

        index_path = base_dir / ".index.json"

        if not index_path.exists():
            return {"version": "1", "lockfiles": {}}

        try:
            with open(index_path) as f:
                index = json.load(f)

            # Cache it
            if scope == "project":
                self._project_index = index
            else:
                self._user_index = index

            return index
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load index from {index_path}: {e}")
            return {"version": "1", "lockfiles": {}}

    def _save_index(
        self,
        scope: Literal["project", "user"],
        index: Dict[str, Any],
    ) -> None:
        """Save index for a scope."""
        base_dir = self.project_lockfiles if scope == "project" else self.user_lockfiles

        if not base_dir:
            return

        base_dir.mkdir(parents=True, exist_ok=True)
        index_path = base_dir / ".index.json"

        # Update cache
        if scope == "project":
            self._project_index = index
        else:
            self._user_index = index

        # Save to disk
        try:
            with open(index_path, "w") as f:
                json.dump(index, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save index to {index_path}: {e}")

    def _update_index(
        self,
        tool_id: str,
        version: str,
        category: str,
        filepath: Path,
        scope: Literal["project", "user"],
        lockfile: Lockfile,
    ) -> None:
        """Update index with a new/updated lockfile."""
        index = self._load_index(scope)

        # Compute key
        key = f"{category}/{tool_id}@{version}"

        # Get relative path
        base_dir = self.project_lockfiles if scope == "project" else self.user_lockfiles
        if base_dir is None:
            raise LockfileError(f"Cannot update index: base_dir is None for scope {scope}")
        rel_path = filepath.relative_to(base_dir)

        # Compute chain hash
        chain_hash = self._compute_chain_hash(lockfile)

        # Update entry
        index["lockfiles"][key] = {
            "path": str(rel_path),
            "chain_hash": chain_hash,
            "created_at": lockfile.generated_at,
            "last_validated": lockfile.generated_at,
            "scope": scope,
        }

        # Update index timestamp
        index["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save index
        self._save_index(scope, index)

    def _touch_lockfile(
        self,
        tool_id: str,
        version: str,
        category: str,
        scope: Literal["project", "user"],
    ) -> None:
        """Update last_validated timestamp for a lockfile."""
        index = self._load_index(scope)

        key = f"{category}/{tool_id}@{version}"

        if key in index.get("lockfiles", {}):
            index["lockfiles"][key]["last_validated"] = datetime.now(timezone.utc).isoformat()
            self._save_index(scope, index)

    def _compute_chain_hash(self, lockfile: Lockfile) -> str:
        """Compute a hash of the resolved chain for indexing."""
        import hashlib

        # Create canonical representation
        chain_repr = []
        for entry in lockfile.resolved_chain:
            chain_repr.append(f"{entry.tool_id}@{entry.version}:{entry.integrity}")

        chain_str = "|".join(chain_repr)
        return hashlib.sha256(chain_str.encode()).hexdigest()[:12]
