"""
Integrity - Simple hash utilities (dumb primitive).

Content-specific integrity computation (tool, directive, knowledge)
moves to RYE OS.

Kernel provides only:
- short_hash: Display helper for hashes
"""

import hashlib


def short_hash(full_hash: str, length: int = 12) -> str:
    """
    Return shortened hash for display purposes.

    Args:
        full_hash: Full hex digest
        length: Number of characters to return

    Returns:
        First `length` characters of hash
    """
    return full_hash[:length]
