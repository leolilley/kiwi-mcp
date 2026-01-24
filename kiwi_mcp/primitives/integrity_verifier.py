"""
Integrity Verifier - Hash verification at every chain step.

Ensures that tool content hasn't been tampered with by verifying
the computed integrity matches the stored integrity for each tool
in the execution chain.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .integrity import compute_tool_integrity, short_hash

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of integrity verification."""
    
    success: bool
    error: Optional[str] = None
    failed_at: Optional[int] = None
    failed_tool_id: Optional[str] = None
    verified_count: int = 0
    cached_count: int = 0
    duration_ms: int = 0
    
    @property
    def all_verified(self) -> bool:
        return self.success and self.verified_count > 0


class IntegrityVerifier:
    """Verifies tool integrity at every step of the execution chain."""
    
    def __init__(self):
        """Initialize verifier with empty cache."""
        # Cache of verified integrities (content_hash -> verified timestamp)
        self._verified_cache: Dict[str, float] = {}
        # Set of known-bad hashes to fail fast
        self._failed_cache: Set[str] = set()
    
    def verify_chain(self, chain: List[Dict[str, Any]]) -> VerificationResult:
        """
        Verify integrity of every tool in the chain.
        
        Args:
            chain: Resolved chain from leaf to primitive
            
        Returns:
            VerificationResult with success/failure and details
        """
        start_time = time.time()
        verified_count = 0
        cached_count = 0
        
        for i, tool in enumerate(chain):
            tool_id = tool.get("tool_id", "unknown")
            stored_hash = tool.get("content_hash") or tool.get("integrity")
            
            # Fail if no stored hash - we cannot verify integrity without it
            if not stored_hash:
                duration_ms = int((time.time() - start_time) * 1000)
                return VerificationResult(
                    success=False,
                    error=f"No integrity hash found for {tool_id}@{tool.get('version', 'unknown')} - cannot verify integrity",
                    failed_at=i,
                    failed_tool_id=tool_id,
                    verified_count=verified_count,
                    cached_count=cached_count,
                    duration_ms=duration_ms
                )
            
            # Check failed cache first (fail fast)
            if stored_hash in self._failed_cache:
                duration_ms = int((time.time() - start_time) * 1000)
                return VerificationResult(
                    success=False,
                    error=f"Previously failed integrity for {tool_id}",
                    failed_at=i,
                    failed_tool_id=tool_id,
                    verified_count=verified_count,
                    cached_count=cached_count,
                    duration_ms=duration_ms
                )
            
            # Check verified cache
            if stored_hash in self._verified_cache:
                cached_count += 1
                verified_count += 1
                continue
            
            # Compute and verify integrity
            try:
                computed = compute_tool_integrity(
                    tool_id=tool_id,
                    version=tool.get("version", "0.0.0"),
                    manifest=tool.get("manifest", {}),
                    files=tool.get("files") or tool.get("file_hashes")
                )
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                return VerificationResult(
                    success=False,
                    error=f"Failed to compute integrity for {tool_id}: {e}",
                    failed_at=i,
                    failed_tool_id=tool_id,
                    verified_count=verified_count,
                    cached_count=cached_count,
                    duration_ms=duration_ms
                )
            
            if computed != stored_hash:
                # Add to failed cache
                self._failed_cache.add(stored_hash)
                
                duration_ms = int((time.time() - start_time) * 1000)
                return VerificationResult(
                    success=False,
                    error=(
                        f"Integrity mismatch for {tool_id}@{tool.get('version')}: "
                        f"computed={short_hash(computed)}, stored={short_hash(stored_hash)}"
                    ),
                    failed_at=i,
                    failed_tool_id=tool_id,
                    verified_count=verified_count,
                    cached_count=cached_count,
                    duration_ms=duration_ms
                )
            
            # Cache successful verification
            self._verified_cache[stored_hash] = time.time()
            verified_count += 1
        
        duration_ms = int((time.time() - start_time) * 1000)
        return VerificationResult(
            success=True,
            verified_count=verified_count,
            cached_count=cached_count,
            duration_ms=duration_ms
        )
    
    def verify_single(self, tool: Dict[str, Any]) -> VerificationResult:
        """
        Verify integrity of a single tool.
        
        Args:
            tool: Tool dict with manifest, files, and stored hash
            
        Returns:
            VerificationResult
        """
        return self.verify_chain([tool])
    
    def is_verified(self, content_hash: str) -> bool:
        """
        Check if a hash has been previously verified.
        
        Args:
            content_hash: The stored content hash
            
        Returns:
            True if previously verified
        """
        return content_hash in self._verified_cache
    
    def invalidate(self, content_hash: str) -> None:
        """
        Invalidate a cached verification.
        
        Args:
            content_hash: Hash to invalidate
        """
        self._verified_cache.pop(content_hash, None)
        self._failed_cache.discard(content_hash)
    
    def clear_cache(self) -> None:
        """Clear all cached verifications."""
        self._verified_cache.clear()
        self._failed_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "verified_count": len(self._verified_cache),
            "failed_count": len(self._failed_cache),
        }
