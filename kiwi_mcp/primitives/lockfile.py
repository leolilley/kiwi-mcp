"""
Lockfile Manager - Reproducible tool execution with pinned versions.

Lockfiles capture a fully resolved chain with exact versions and 
integrity hashes, enabling reproducible execution across environments.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LOCKFILE_VERSION = 1


@dataclass
class LockfileEntry:
    """Single entry in the resolved chain."""
    
    tool_id: str
    version: str
    integrity: str
    executor: Optional[str] = None


@dataclass
class LockfileRoot:
    """Root tool information."""
    
    tool_id: str
    version: str
    integrity: str


@dataclass
class LockfileRegistry:
    """Registry information for provenance."""
    
    url: str
    fetched_at: str


@dataclass
class Lockfile:
    """Complete lockfile structure."""
    
    lockfile_version: int
    generated_at: str
    root: LockfileRoot
    resolved_chain: List[LockfileEntry]
    registry: Optional[LockfileRegistry] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "lockfile_version": self.lockfile_version,
            "generated_at": self.generated_at,
            "root": asdict(self.root),
            "resolved_chain": [asdict(e) for e in self.resolved_chain],
            "registry": asdict(self.registry) if self.registry else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lockfile":
        """Create Lockfile from dictionary."""
        return cls(
            lockfile_version=data["lockfile_version"],
            generated_at=data["generated_at"],
            root=LockfileRoot(**data["root"]),
            resolved_chain=[LockfileEntry(**e) for e in data["resolved_chain"]],
            registry=LockfileRegistry(**data["registry"]) if data.get("registry") else None
        )


class LockfileError(Exception):
    """Error during lockfile operations."""
    pass


class LockfileManager:
    """Manages lockfile creation and consumption."""
    
    def __init__(self, registry_url: Optional[str] = None):
        """
        Initialize lockfile manager.
        
        Args:
            registry_url: Optional registry URL for provenance
        """
        self.registry_url = registry_url
    
    def freeze(
        self, 
        chain: List[Dict[str, Any]],
        registry_url: Optional[str] = None
    ) -> Lockfile:
        """
        Create a lockfile from a resolved and verified chain.
        
        Args:
            chain: Resolved chain from leaf to primitive
            registry_url: Optional registry URL override
            
        Returns:
            Lockfile with pinned versions and integrities
        """
        if not chain:
            raise LockfileError("Cannot create lockfile from empty chain")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Build entries from chain
        entries = []
        for tool in chain:
            entry = LockfileEntry(
                tool_id=tool.get("tool_id", ""),
                version=tool.get("version", ""),
                integrity=tool.get("content_hash") or tool.get("integrity", ""),
                executor=tool.get("executor_id")
            )
            entries.append(entry)
        
        # Root is the first tool (the one requested)
        root_tool = chain[0]
        root = LockfileRoot(
            tool_id=root_tool.get("tool_id", ""),
            version=root_tool.get("version", ""),
            integrity=root_tool.get("content_hash") or root_tool.get("integrity", "")
        )
        
        # Registry info
        reg_url = registry_url or self.registry_url
        registry = LockfileRegistry(url=reg_url, fetched_at=now) if reg_url else None
        
        return Lockfile(
            lockfile_version=LOCKFILE_VERSION,
            generated_at=now,
            root=root,
            resolved_chain=entries,
            registry=registry
        )
    
    def save(self, lockfile: Lockfile, path: Path) -> None:
        """
        Save lockfile to disk.
        
        Args:
            lockfile: Lockfile to save
            path: Path to save to (e.g., "tool.lock.json")
        """
        path = Path(path)
        with open(path, "w") as f:
            json.dump(lockfile.to_dict(), f, indent=2)
        
        logger.info(f"Saved lockfile to {path}")
    
    def load(self, path: Path) -> Lockfile:
        """
        Load lockfile from disk.
        
        Args:
            path: Path to lockfile
            
        Returns:
            Loaded Lockfile
            
        Raises:
            LockfileError: If file not found or invalid
        """
        path = Path(path)
        
        if not path.exists():
            raise LockfileError(f"Lockfile not found: {path}")
        
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise LockfileError(f"Invalid lockfile JSON: {e}")
        
        # Validate version
        version = data.get("lockfile_version")
        if version != LOCKFILE_VERSION:
            raise LockfileError(
                f"Unsupported lockfile version: {version} (expected {LOCKFILE_VERSION})"
            )
        
        return Lockfile.from_dict(data)
    
    def validate_against_chain(
        self, 
        lockfile: Lockfile, 
        chain: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate that a resolved chain matches the lockfile.
        
        Args:
            lockfile: Expected lockfile
            chain: Resolved chain to validate
            
        Returns:
            Dict with valid, issues
        """
        issues = []
        
        if len(chain) != len(lockfile.resolved_chain):
            issues.append(
                f"Chain length mismatch: lockfile has {len(lockfile.resolved_chain)}, "
                f"resolved has {len(chain)}"
            )
            return {"valid": False, "issues": issues}
        
        for i, (expected, actual) in enumerate(zip(lockfile.resolved_chain, chain)):
            actual_id = actual.get("tool_id", "")
            actual_version = actual.get("version", "")
            actual_integrity = actual.get("content_hash") or actual.get("integrity", "")
            
            if expected.tool_id != actual_id:
                issues.append(
                    f"Tool ID mismatch at position {i}: "
                    f"lockfile={expected.tool_id}, resolved={actual_id}"
                )
            
            if expected.version != actual_version:
                issues.append(
                    f"Version mismatch for {expected.tool_id}: "
                    f"lockfile={expected.version}, resolved={actual_version}"
                )
            
            if expected.integrity and actual_integrity:
                if expected.integrity != actual_integrity:
                    issues.append(
                        f"Integrity mismatch for {expected.tool_id}@{expected.version}: "
                        f"lockfile={expected.integrity[:12]}, resolved={actual_integrity[:12]}"
                    )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def get_pinned_versions(self, lockfile: Lockfile) -> Dict[str, str]:
        """
        Extract tool_id -> version mapping from lockfile.
        
        Useful for resolving with pinned versions.
        
        Args:
            lockfile: Lockfile to extract from
            
        Returns:
            Dict mapping tool_id to pinned version
        """
        return {
            entry.tool_id: entry.version 
            for entry in lockfile.resolved_chain
        }
