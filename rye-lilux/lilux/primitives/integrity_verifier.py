"""
Integrity Verifier - Simple hash verification (dumb primitive).

This is the only integrity check the kernel provides.
Signature validation is RYE's responsibility.
"""

from pathlib import Path
from typing import Optional
import hashlib


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of content (dumb primitive).

    This is the only integrity check the kernel provides.
    Signature validation is RYE's responsibility.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def verify_file_integrity(file_path: Path, expected_hash: str) -> bool:
    """
    Verify file matches expected hash (dumb primitive).
    """
    actual_hash = compute_content_hash(file_path.read_text())
    return actual_hash == expected_hash
