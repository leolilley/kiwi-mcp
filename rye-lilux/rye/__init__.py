"""
RYE - Runtime for Your Experiments

RYE provides the intelligence layer on top of Lilux kernel:
- Core directives for init, bootstrap, sync, publish
- Core tools for system, registry, RAG operations
- Knowledge base for kernel docs, patterns, procedures

Install: pip install rye-lilux
"""

__version__ = "0.1.0"

import importlib.resources
from pathlib import Path


def get_content_path() -> Path:
    """Get path to RYE .ai content bundle."""
    with importlib.resources.as_file(
        importlib.resources.files("rye").joinpath(".ai")
    ) as path:
        return path
