"""
Primitive executors for the unified tools architecture.

This module provides the foundational classes for executing tools:
- SubprocessPrimitive: Execute shell commands and scripts
- HttpClientPrimitive: Make HTTP requests with retry logic
- PrimitiveExecutor: Orchestrator that routes to the correct primitive

Package-manager style validation:
- IntegrityVerifier: Hash verification at every chain step
- ChainValidator: Parent→child schema validation
- LockfileManager: Reproducible execution with pinned versions
"""

from .subprocess import SubprocessPrimitive, SubprocessResult
from .http_client import HttpClientPrimitive, HttpResult
from .executor import PrimitiveExecutor, ExecutionResult, ChainResolver
from .integrity import (
    compute_tool_integrity,
    compute_directive_integrity,
    compute_knowledge_integrity,
)
from .integrity_verifier import IntegrityVerifier, VerificationResult
from .chain_validator import ChainValidator, ChainValidationResult
from .lockfile import Lockfile, LockfileManager, LockfileError
from .errors import (
    ToolChainError,
    FailedToolContext,
    ValidationError,
    ConfigValidationError,
)

__all__ = [
    # Primitives (hardcoded execution)
    "SubprocessPrimitive",
    "SubprocessResult",
    "HttpClientPrimitive",
    "HttpResult",
    # Executor
    "PrimitiveExecutor",
    "ExecutionResult",
    "ChainResolver",
    # Integrity
    "compute_tool_integrity",
    "compute_directive_integrity",
    "compute_knowledge_integrity",
    "IntegrityVerifier",
    "VerificationResult",
    # Validation
    "ChainValidator",
    "ChainValidationResult",
    # Lockfile
    "Lockfile",
    "LockfileManager",
    "LockfileError",
    # Error handling
    "ToolChainError",
    "FailedToolContext",
    "ValidationError",
    "ConfigValidationError",
]
