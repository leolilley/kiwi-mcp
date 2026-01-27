"""
Tests for LockfileStore - Kernel-level lockfile management.
"""

import pytest
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from kiwi_mcp.runtime.lockfile_store import (
    LockfileStore,
    LockfileMetadata,
    ValidationResult,
)
from kiwi_mcp.primitives.lockfile import (
    Lockfile,
    LockfileRoot,
    LockfileEntry,
    LockfileError,
)


@pytest.fixture
def temp_dirs():
    """Create temporary project and user directories."""
    with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as user_dir:
        yield Path(project_dir), Path(user_dir)


@pytest.fixture
def store(temp_dirs):
    """Create a LockfileStore with temporary directories."""
    project_root, user_root = temp_dirs
    return LockfileStore(
        project_root=project_root,
        userspace_root=user_root,
    )


@pytest.fixture
def sample_chain():
    """Create a sample resolved chain."""
    return [
        {
            "tool_id": "my_script",
            "version": "1.0.0",
            "content_hash": "abc123" + "0" * 58,
            "executor_id": "python_runtime",
        },
        {
            "tool_id": "python_runtime",
            "version": "1.4.0",
            "content_hash": "def456" + "0" * 58,
            "executor_id": "subprocess",
        },
        {
            "tool_id": "subprocess",
            "version": "1.0.0",
            "content_hash": "ghi789" + "0" * 58,
            "executor_id": None,
        },
    ]


@pytest.fixture
def sample_lockfile(sample_chain):
    """Create a sample lockfile."""
    return Lockfile(
        lockfile_version=1,
        generated_at=datetime.now(timezone.utc).isoformat(),
        root=LockfileRoot(
            tool_id="my_script",
            version="1.0.0",
            integrity="abc123" + "0" * 58,
        ),
        resolved_chain=[
            LockfileEntry(
                tool_id=entry["tool_id"],
                version=entry["version"],
                integrity=entry["content_hash"],
                executor=entry.get("executor_id"),
            )
            for entry in sample_chain
        ],
    )


class TestLockfileStoreInit:
    """Tests for LockfileStore initialization."""

    def test_init_with_project_root(self, temp_dirs):
        """Store should initialize with project root."""
        project_root, user_root = temp_dirs

        store = LockfileStore(
            project_root=project_root,
            userspace_root=user_root,
        )

        assert store.project_root == project_root
        assert store.project_lockfiles == project_root / ".ai" / "lockfiles"
        assert store.user_root == user_root
        assert store.user_lockfiles == user_root / "lockfiles"

    def test_init_without_project_root(self, temp_dirs):
        """Store should work without project root (user-only)."""
        _, user_root = temp_dirs

        store = LockfileStore(
            project_root=None,
            userspace_root=user_root,
        )

        assert store.project_root is None
        assert store.project_lockfiles is None
        assert store.user_lockfiles == user_root / "lockfiles"

    def test_init_default_userspace(self, temp_dirs):
        """Store should default to ~/.ai for userspace."""
        project_root, _ = temp_dirs

        store = LockfileStore(project_root=project_root)

        assert store.user_root == Path.home() / ".ai"


class TestFreeze:
    """Tests for freeze() method."""

    def test_freeze_creates_lockfile(self, store, sample_chain):
        """Freeze should create a valid lockfile."""
        lockfile = store.freeze(
            tool_id="my_script",
            version="1.0.0",
            category="scripts",
            chain=sample_chain,
        )

        assert lockfile.lockfile_version == 1
        assert lockfile.root.tool_id == "my_script"
        assert lockfile.root.version == "1.0.0"
        assert len(lockfile.resolved_chain) == 3

    def test_freeze_with_registry_url(self, store, sample_chain):
        """Freeze should include registry URL if provided."""
        lockfile = store.freeze(
            tool_id="my_script",
            version="1.0.0",
            category="scripts",
            chain=sample_chain,
            registry_url="https://registry.example.com",
        )

        assert lockfile.registry is not None
        assert lockfile.registry.url == "https://registry.example.com"

    def test_freeze_empty_chain_raises(self, store):
        """Freeze should raise on empty chain."""
        with pytest.raises(LockfileError, match="empty chain"):
            store.freeze(
                tool_id="my_script",
                version="1.0.0",
                category="scripts",
                chain=[],
            )


class TestSave:
    """Tests for save() method."""

    def test_save_to_project(self, store, sample_lockfile):
        """Save should write lockfile to project scope."""
        filepath = store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="project",
        )

        assert filepath.exists()
        assert "my_script@1.0.0.lock.json" in filepath.name
        assert ".ai/lockfiles/scripts" in str(filepath)

    def test_save_to_user(self, store, sample_lockfile):
        """Save should write lockfile to user scope."""
        filepath = store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="user",
        )

        assert filepath.exists()
        assert "my_script@1.0.0.lock.json" in filepath.name
        assert "lockfiles/scripts" in str(filepath)

    def test_save_with_chain_hash(self, store, sample_lockfile):
        """Save should include chain hash in filename if provided."""
        filepath = store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="project",
            chain_hash="abc123def456",
        )

        assert filepath.exists()
        assert "my_script@1.0.0.abc123def456.lock.json" in filepath.name

    def test_save_creates_category_directory(self, store, sample_lockfile):
        """Save should create category directory if needed."""
        filepath = store.save(
            lockfile=sample_lockfile,
            category="new_category",
            scope="project",
        )

        assert filepath.parent.name == "new_category"
        assert filepath.parent.exists()

    def test_save_updates_index(self, store, sample_lockfile):
        """Save should update the index file."""
        store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="project",
        )

        # Check index exists
        index_path = store.project_lockfiles / ".index.json"
        assert index_path.exists()

        # Load and verify index
        with open(index_path) as f:
            index = json.load(f)

        assert "lockfiles" in index
        key = "scripts/my_script@1.0.0"
        assert key in index["lockfiles"]

        entry = index["lockfiles"][key]
        assert entry["created_at"] == sample_lockfile.generated_at
        assert "chain_hash" in entry

    def test_save_without_project_root_raises(self, temp_dirs, sample_lockfile):
        """Save to project should raise if project_root not set."""
        _, user_root = temp_dirs

        store = LockfileStore(
            project_root=None,
            userspace_root=user_root,
        )

        with pytest.raises(LockfileError, match="project_root not set"):
            store.save(
                lockfile=sample_lockfile,
                category="scripts",
                scope="project",
            )


class TestLoad:
    """Tests for load() method."""

    def test_load_from_project(self, store, sample_lockfile):
        """Load should retrieve lockfile from project scope."""
        # Save first
        store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="project",
        )

        # Load
        loaded = store.load(
            tool_id="my_script",
            version="1.0.0",
            category="scripts",
        )

        assert loaded is not None
        assert loaded.root.tool_id == "my_script"
        assert loaded.root.version == "1.0.0"
        assert len(loaded.resolved_chain) == 3

    def test_load_from_user(self, store, sample_lockfile):
        """Load should retrieve lockfile from user scope."""
        # Save first
        store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="user",
        )

        # Load
        loaded = store.load(
            tool_id="my_script",
            version="1.0.0",
            category="scripts",
        )

        assert loaded is not None
        assert loaded.root.tool_id == "my_script"

    def test_load_project_precedence(self, store, sample_lockfile):
        """Load should prefer project over user scope."""
        # Save to both scopes with different content
        project_lockfile = sample_lockfile
        store.save(
            lockfile=project_lockfile,
            category="scripts",
            scope="project",
        )

        user_lockfile = Lockfile(
            lockfile_version=1,
            generated_at="2020-01-01T00:00:00Z",  # Different timestamp
            root=sample_lockfile.root,
            resolved_chain=sample_lockfile.resolved_chain,
        )
        store.save(
            lockfile=user_lockfile,
            category="scripts",
            scope="user",
        )

        # Load should get project version
        loaded = store.load(
            tool_id="my_script",
            version="1.0.0",
            category="scripts",
        )

        assert loaded is not None
        assert loaded.generated_at == project_lockfile.generated_at
        assert loaded.generated_at != "2020-01-01T00:00:00Z"

    def test_load_not_found(self, store):
        """Load should return None if lockfile doesn't exist."""
        loaded = store.load(
            tool_id="nonexistent",
            version="1.0.0",
            category="scripts",
        )

        assert loaded is None

    def test_load_updates_last_validated(self, store, sample_lockfile):
        """Load should update last_validated timestamp in index."""
        # Save
        store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="project",
        )

        # Get initial timestamp
        index = store._load_index("project")
        key = "scripts/my_script@1.0.0"
        initial_validated = index["lockfiles"][key]["last_validated"]

        # Wait a bit and load
        import time

        time.sleep(0.1)

        store.load(
            tool_id="my_script",
            version="1.0.0",
            category="scripts",
        )

        # Check timestamp updated
        index = store._load_index("project")
        new_validated = index["lockfiles"][key]["last_validated"]

        assert new_validated != initial_validated


class TestValidateChain:
    """Tests for validate_chain() method."""

    def test_validate_matching_chain(self, store, sample_lockfile, sample_chain):
        """Validate should succeed for matching chain."""
        result = store.validate_chain(sample_lockfile, sample_chain)

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_validate_mismatched_version(self, store, sample_lockfile, sample_chain):
        """Validate should fail for version mismatch."""
        # Modify chain version
        modified_chain = sample_chain.copy()
        modified_chain[0] = modified_chain[0].copy()
        modified_chain[0]["version"] = "2.0.0"

        result = store.validate_chain(sample_lockfile, modified_chain)

        assert result.is_valid is False
        assert len(result.issues) > 0
        assert any("version" in issue.lower() for issue in result.issues)

    def test_validate_mismatched_integrity(self, store, sample_lockfile, sample_chain):
        """Validate should fail for integrity mismatch."""
        # Modify chain integrity
        modified_chain = sample_chain.copy()
        modified_chain[0] = modified_chain[0].copy()
        modified_chain[0]["content_hash"] = "different_hash" + "0" * 50

        result = store.validate_chain(sample_lockfile, modified_chain)

        assert result.is_valid is False
        assert len(result.issues) > 0
        assert any("integrity" in issue.lower() for issue in result.issues)

    def test_validate_wrong_length(self, store, sample_lockfile, sample_chain):
        """Validate should fail for chain length mismatch."""
        # Remove entry from chain
        short_chain = sample_chain[:2]

        result = store.validate_chain(sample_lockfile, short_chain)

        assert result.is_valid is False
        assert len(result.issues) > 0
        assert any("length" in issue.lower() for issue in result.issues)


class TestListLockfiles:
    """Tests for list_lockfiles() method."""

    def test_list_empty(self, store):
        """List should return empty for no lockfiles."""
        lockfiles = store.list_lockfiles()

        assert len(lockfiles) == 0

    def test_list_single_lockfile(self, store, sample_lockfile):
        """List should return single lockfile."""
        store.save(
            lockfile=sample_lockfile,
            category="scripts",
            scope="project",
        )

        lockfiles = store.list_lockfiles()

        assert len(lockfiles) == 1
        assert lockfiles[0].tool_id == "my_script"
        assert lockfiles[0].version == "1.0.0"
        assert lockfiles[0].category == "scripts"
        assert lockfiles[0].scope == "project"

    def test_list_multiple_lockfiles(self, store, sample_lockfile):
        """List should return multiple lockfiles."""
        # Save multiple
        store.save(sample_lockfile, "scripts", "project")

        lockfile2 = Lockfile(
            lockfile_version=1,
            generated_at=datetime.now(timezone.utc).isoformat(),
            root=LockfileRoot(
                tool_id="another_script",
                version="2.0.0",
                integrity="xyz789" + "0" * 58,
            ),
            resolved_chain=[
                LockfileEntry(
                    tool_id="another_script",
                    version="2.0.0",
                    integrity="xyz789" + "0" * 58,
                )
            ],
        )
        store.save(lockfile2, "scripts", "project")

        lockfiles = store.list_lockfiles()

        assert len(lockfiles) == 2
        assert {lf.tool_id for lf in lockfiles} == {"my_script", "another_script"}

    def test_list_with_category_filter(self, store, sample_lockfile):
        """List should filter by category."""
        # Save to different categories
        store.save(sample_lockfile, "scripts", "project")

        lockfile2 = Lockfile(
            lockfile_version=1,
            generated_at=datetime.now(timezone.utc).isoformat(),
            root=LockfileRoot(
                tool_id="api_tool",
                version="1.0.0",
                integrity="api123" + "0" * 58,
            ),
            resolved_chain=[
                LockfileEntry(
                    tool_id="api_tool",
                    version="1.0.0",
                    integrity="api123" + "0" * 58,
                )
            ],
        )
        store.save(lockfile2, "apis", "project")

        # Filter by category
        lockfiles = store.list_lockfiles(category="scripts")

        assert len(lockfiles) == 1
        assert lockfiles[0].tool_id == "my_script"

    def test_list_with_scope_filter(self, store, sample_lockfile):
        """List should filter by scope."""
        # Save to both scopes
        store.save(sample_lockfile, "scripts", "project")

        lockfile2 = Lockfile(
            lockfile_version=1,
            generated_at=datetime.now(timezone.utc).isoformat(),
            root=LockfileRoot(
                tool_id="user_script",
                version="1.0.0",
                integrity="usr123" + "0" * 58,
            ),
            resolved_chain=[
                LockfileEntry(
                    tool_id="user_script",
                    version="1.0.0",
                    integrity="usr123" + "0" * 58,
                )
            ],
        )
        store.save(lockfile2, "scripts", "user")

        # Filter by scope
        project_lockfiles = store.list_lockfiles(scope="project")
        user_lockfiles = store.list_lockfiles(scope="user")

        assert len(project_lockfiles) == 1
        assert project_lockfiles[0].tool_id == "my_script"

        assert len(user_lockfiles) == 1
        assert user_lockfiles[0].tool_id == "user_script"

    def test_list_sorted_by_tool_id(self, store, sample_lockfile):
        """List should sort results by tool_id and version."""
        # Save in reverse order
        lockfile_b = Lockfile(
            lockfile_version=1,
            generated_at=datetime.now(timezone.utc).isoformat(),
            root=LockfileRoot(
                tool_id="b_script",
                version="1.0.0",
                integrity="bbb" + "0" * 61,
            ),
            resolved_chain=[
                LockfileEntry(
                    tool_id="b_script",
                    version="1.0.0",
                    integrity="bbb" + "0" * 61,
                )
            ],
        )

        lockfile_a = Lockfile(
            lockfile_version=1,
            generated_at=datetime.now(timezone.utc).isoformat(),
            root=LockfileRoot(
                tool_id="a_script",
                version="1.0.0",
                integrity="aaa" + "0" * 61,
            ),
            resolved_chain=[
                LockfileEntry(
                    tool_id="a_script",
                    version="1.0.0",
                    integrity="aaa" + "0" * 61,
                )
            ],
        )

        store.save(lockfile_b, "scripts", "project")
        store.save(lockfile_a, "scripts", "project")

        lockfiles = store.list_lockfiles()

        assert len(lockfiles) == 2
        assert lockfiles[0].tool_id == "a_script"
        assert lockfiles[1].tool_id == "b_script"


class TestPruneStale:
    """Tests for prune_stale() method."""

    def test_prune_no_lockfiles(self, store):
        """Prune should return 0 for no lockfiles."""
        pruned = store.prune_stale(max_age_days=90)

        assert pruned == 0

    def test_prune_recent_lockfiles(self, store, sample_lockfile):
        """Prune should not delete recent lockfiles."""
        store.save(sample_lockfile, "scripts", "project")

        pruned = store.prune_stale(max_age_days=90)

        assert pruned == 0

        # Verify still exists
        loaded = store.load("my_script", "1.0.0", "scripts")
        assert loaded is not None

    def test_prune_old_lockfiles(self, store, sample_lockfile):
        """Prune should delete old lockfiles."""
        # Save lockfile
        filepath = store.save(sample_lockfile, "scripts", "project")

        # Manually update index to make it old
        index = store._load_index("project")
        key = "scripts/my_script@1.0.0"

        old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        index["lockfiles"][key]["created_at"] = old_date
        index["lockfiles"][key]["last_validated"] = old_date

        store._save_index("project", index)

        # Prune
        pruned = store.prune_stale(max_age_days=90)

        assert pruned == 1

        # Verify deleted
        assert not filepath.exists()
        loaded = store.load("my_script", "1.0.0", "scripts")
        assert loaded is None

    def test_prune_with_scope_filter(self, store, sample_lockfile):
        """Prune should respect scope filter."""
        # Save to both scopes
        store.save(sample_lockfile, "scripts", "project")

        lockfile2 = Lockfile(
            lockfile_version=1,
            generated_at=datetime.now(timezone.utc).isoformat(),
            root=LockfileRoot(
                tool_id="user_script",
                version="1.0.0",
                integrity="usr" + "0" * 61,
            ),
            resolved_chain=[
                LockfileEntry(
                    tool_id="user_script",
                    version="1.0.0",
                    integrity="usr" + "0" * 61,
                )
            ],
        )
        store.save(lockfile2, "scripts", "user")

        # Make both old
        for scope in ["project", "user"]:
            index = store._load_index(scope)
            for key in index.get("lockfiles", {}).keys():
                old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
                index["lockfiles"][key]["created_at"] = old_date
                index["lockfiles"][key]["last_validated"] = old_date
            store._save_index(scope, index)

        # Prune only project
        pruned = store.prune_stale(max_age_days=90, scope="project")

        assert pruned == 1

        # Project should be deleted, user should remain
        assert store.load("my_script", "1.0.0", "scripts") is None
        assert store.load("user_script", "1.0.0", "scripts") is not None


class TestIndexManagement:
    """Tests for index management."""

    def test_index_created_on_first_save(self, store, sample_lockfile):
        """Index should be created on first save."""
        index_path = store.project_lockfiles / ".index.json"

        assert not index_path.exists()

        store.save(sample_lockfile, "scripts", "project")

        assert index_path.exists()

    def test_index_contains_metadata(self, store, sample_lockfile):
        """Index should contain lockfile metadata."""
        store.save(sample_lockfile, "scripts", "project")

        index = store._load_index("project")

        assert "version" in index
        assert "lockfiles" in index
        assert "updated_at" in index

    def test_index_caching(self, store, sample_lockfile):
        """Index should be cached in memory."""
        # Save to create index
        store.save(sample_lockfile, "scripts", "project")

        # Load index
        index1 = store._load_index("project")

        # Load again - should be same object (cached)
        index2 = store._load_index("project")

        assert index1 is index2


class TestChainHash:
    """Tests for chain hash computation."""

    def test_compute_chain_hash_deterministic(self, store, sample_lockfile):
        """Chain hash should be deterministic."""
        hash1 = store._compute_chain_hash(sample_lockfile)
        hash2 = store._compute_chain_hash(sample_lockfile)

        assert hash1 == hash2
        assert len(hash1) == 12  # Truncated to 12 chars

    def test_compute_chain_hash_different_chains(self, store, sample_lockfile):
        """Different chains should produce different hashes."""
        hash1 = store._compute_chain_hash(sample_lockfile)

        # Modify chain
        modified_lockfile = Lockfile(
            lockfile_version=sample_lockfile.lockfile_version,
            generated_at=sample_lockfile.generated_at,
            root=sample_lockfile.root,
            resolved_chain=[
                LockfileEntry(
                    tool_id="different",
                    version="1.0.0",
                    integrity="xyz" + "0" * 61,
                )
            ],
        )

        hash2 = store._compute_chain_hash(modified_lockfile)

        assert hash1 != hash2
