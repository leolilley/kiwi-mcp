"""
Primitive executors for the unified tools architecture.

This module provides the foundational classes for executing tools:
- SubprocessPrimitive: Execute shell commands and scripts
- HttpClientPrimitive: Make HTTP requests with retry logic
- PrimitiveExecutor: Orchestrator that routes to the correct primitive
"""

from .subprocess import SubprocessPrimitive, SubprocessResult
from .http_client import HttpClientPrimitive, HttpResult
from .executor import PrimitiveExecutor

__all__ = [
    "SubprocessPrimitive",
    "SubprocessResult",
    "HttpClientPrimitive",
    "HttpResult",
    "PrimitiveExecutor",
]
