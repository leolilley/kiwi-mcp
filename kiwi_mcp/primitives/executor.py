"""
PrimitiveExecutor orchestrator that routes to the correct primitive.

Package-Manager-Style Execution Pipeline:
1. Resolve chain (with caching)
2. Verify integrity at every step (hash validation)
3. Validate parent→child relationships (schema validation)
4. Validate runtime parameters against config_schema
5. Execute via hardcoded primitive (subprocess or http_client)

Only subprocess and http_client contain actual execution code.
Everything else is data-driven configuration.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from .subprocess import SubprocessPrimitive, SubprocessResult
from .http_client import HttpClientPrimitive, HttpResult

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Unified result from primitive execution."""

    success: bool
    data: Any
    duration_ms: int
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionContext:
    """Context for a single execution with verification status."""
    
    chain: List[Dict[str, Any]] = field(default_factory=list)
    integrity_verified: bool = False
    chain_validated: bool = False
    verification_cached: int = 0
    validation_cached: int = 0


class ChainResolver:
    """Resolves and caches executor chains with full integrity data."""

    def __init__(self, registry, project_path: Optional['Path'] = None):
        """
        Initialize with registry and optional project path for local resolution.

        Args:
            registry: ToolRegistry instance (kept for backward compatibility)
            project_path: Optional path for local chain resolution
        """
        self.registry = registry
        self.project_path = project_path
        
        # Lazy-loaded local resolver
        self._local_resolver = None
        
        # Chain cache by tool_id
        self._chain_cache: Dict[str, List[Dict]] = {}
        
        # Verified integrity cache: content_hash -> verified_at timestamp
        self._integrity_cache: Dict[str, float] = {}
        
        # Validation cache: (parent_hash, child_hash) -> validation result
        self._validation_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def _get_local_resolver(self):
        """Lazy-load local chain resolver."""
        if self._local_resolver is None and self.project_path:
            from pathlib import Path
            from .local_chain_resolver import LocalChainResolver
            path_obj = self.project_path if isinstance(self.project_path, Path) else Path(self.project_path)
            self._local_resolver = LocalChainResolver(path_obj)
        return self._local_resolver

    async def resolve(self, tool_id: str) -> List[Dict]:
        """
        Resolve chain from local files only.
        
        Local-only resolution ensures:
        - Tools are executed from the local filesystem
        - Registry tools must be loaded first via 'load' action
        - No network dependency for execution
        
        Raises an error if tool not found locally (instead of falling back to registry).
        """
        if tool_id in self._chain_cache:
            return self._chain_cache[tool_id]

        # Try local resolution
        local_resolver = self._get_local_resolver()
        if local_resolver:
            try:
                chain = await local_resolver.resolve_chain(tool_id)
                if chain:
                    self._chain_cache[tool_id] = chain
                    return chain
            except Exception as e:
                # Re-raise local resolution errors (don't fallback to registry)
                logger.error(f"Failed to resolve chain for '{tool_id}': {e}")
                raise
        
        # No local resolver configured - return empty chain
        # This maintains backward compatibility when project_path is not provided
        return []

    async def resolve_batch(self, tool_ids: List[str]) -> Dict[str, List[Dict]]:
        """Batch resolve multiple chains from local files."""
        uncached = [t for t in tool_ids if t not in self._chain_cache]
        
        if uncached:
            local_resolver = self._get_local_resolver()
            if local_resolver:
                results = await local_resolver.resolve_chains_batch(uncached)
                self._chain_cache.update(results)
            else:
                # No local resolver - return empty chains for uncached
                for tool_id in uncached:
                    self._chain_cache[tool_id] = []
        
        return {t: self._chain_cache.get(t, []) for t in tool_ids}

    def merge_configs(self, chain: List[Dict]) -> Dict:
        """Merge configs from chain (child overrides parent)."""
        merged = {}
        # Process from primitive to leaf (so leaf overrides)
        for item in reversed(chain):
            manifest = item.get("manifest", {})
            config = manifest.get("config")
            if config:  # Only merge if config is not None
                merged = self._deep_merge(merged, config)
        return merged

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dicts (override wins)."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def is_integrity_verified(self, content_hash: str) -> bool:
        """Check if integrity has been verified this session."""
        return content_hash in self._integrity_cache
    
    def mark_integrity_verified(self, content_hash: str) -> None:
        """Mark an integrity as verified."""
        self._integrity_cache[content_hash] = time.time()
    
    def is_pair_validated(self, parent_hash: str, child_hash: str) -> bool:
        """Check if parent→child pair has been validated this session."""
        return (parent_hash, child_hash) in self._validation_cache
    
    def cache_pair_validation(
        self, 
        parent_hash: str, 
        child_hash: str, 
        result: Dict[str, Any]
    ) -> None:
        """Cache a parent→child validation result."""
        self._validation_cache[(parent_hash, child_hash)] = result
    
    def get_cached_validation(
        self, 
        parent_hash: str, 
        child_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached validation result."""
        return self._validation_cache.get((parent_hash, child_hash))
    
    def invalidate_tool(self, tool_id: str) -> None:
        """Invalidate caches when a tool is updated."""
        # Remove from chain cache
        self._chain_cache.pop(tool_id, None)
        
        # Remove any chains that include this tool
        for cached_id, chain in list(self._chain_cache.items()):
            if any(t.get("tool_id") == tool_id for t in chain):
                self._chain_cache.pop(cached_id, None)
    
    def clear_caches(self) -> None:
        """Clear all caches."""
        self._chain_cache.clear()
        self._integrity_cache.clear()
        self._validation_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "chain_cache": len(self._chain_cache),
            "integrity_cache": len(self._integrity_cache),
            "validation_cache": len(self._validation_cache),
        }


class PrimitiveExecutor:
    """Orchestrator that routes execution to the correct primitive.

    Implements the full package-manager-style execution pipeline:
    1. Resolve chain
    2. Verify integrity at every step
    3. Validate parent→child relationships
    4. Validate runtime parameters
    5. Execute via primitive
    
    Only subprocess and http_client are hardcoded. Everything else is data.
    """

    def __init__(
        self, 
        registry, 
        project_path: Optional['Path'] = None,
        verify_integrity: bool = True, 
        validate_chain: bool = True
    ):
        """
        Initialize with tool registry and optional project path.

        Args:
            registry: ToolRegistry instance (kept for backward compatibility)
            project_path: Optional project path for local chain resolution
            verify_integrity: Whether to verify integrity at every step
            validate_chain: Whether to validate parent→child relationships
        """
        self.registry = registry
        self.project_path = project_path
        self.resolver = ChainResolver(registry, project_path)
        self.subprocess_primitive = SubprocessPrimitive()
        self.http_client_primitive = HttpClientPrimitive()
        
        # Configuration
        self.verify_integrity = verify_integrity
        self.validate_chain = validate_chain
        
        # Lazy-loaded components
        self._schema_validator = None
        self._integrity_verifier = None
        self._chain_validator = None

    def _get_schema_validator(self):
        """Lazy-load schema validator to avoid circular imports."""
        if self._schema_validator is None:
            try:
                from kiwi_mcp.utils.schema_validator import SchemaValidator
                self._schema_validator = SchemaValidator()
            except ImportError:
                logger.warning("SchemaValidator not available - runtime validation disabled")
                self._schema_validator = False  # Mark as unavailable
        return self._schema_validator if self._schema_validator else None
    
    def _get_integrity_verifier(self):
        """Lazy-load integrity verifier."""
        if self._integrity_verifier is None:
            from .integrity_verifier import IntegrityVerifier
            self._integrity_verifier = IntegrityVerifier()
        return self._integrity_verifier
    
    def _get_chain_validator(self):
        """Lazy-load chain validator."""
        if self._chain_validator is None:
            from .chain_validator import ChainValidator
            self._chain_validator = ChainValidator(self._get_schema_validator())
        return self._chain_validator

    def _validate_runtime_params(
        self, merged_config: Dict[str, Any], terminal_manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate merged config against tool's config_schema.

        This is Layer 2 validation: data-driven per-tool parameter validation.
        The schema comes from the primitive's manifest, implementing
        "everything else is data".

        Args:
            merged_config: The merged configuration from the chain
            terminal_manifest: The terminal primitive's manifest containing config_schema

        Returns:
            Validation result with valid, issues, and warnings
        """
        config_schema = terminal_manifest.get("config_schema")

        if not config_schema:
            # No schema defined - allow execution (primitives may not require validation)
            return {"valid": True, "issues": [], "warnings": []}

        schema_validator = self._get_schema_validator()
        if not schema_validator:
            return {
                "valid": True,
                "issues": [],
                "warnings": ["jsonschema not available - skipping runtime validation"],
            }

        if not schema_validator.is_available():
            return {
                "valid": True,
                "issues": [],
                "warnings": ["jsonschema library not installed - skipping runtime validation"],
            }

        return schema_validator.validate(merged_config, config_schema)

    async def execute(
        self, 
        tool_id: str, 
        params: Dict[str, Any],
        lockfile: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute a tool by resolving its chain and routing to the correct primitive.

        Pipeline:
        1. Resolve chain (with caching)
        2. Verify integrity at every step (if enabled)
        3. Validate parent→child relationships (if enabled)
        4. Validate runtime parameters against config_schema
        5. Execute via hardcoded primitive

        Args:
            tool_id: ID of the tool to execute
            params: Runtime parameters
            lockfile: Optional lockfile for pinned execution

        Returns:
            ExecutionResult with unified response
        """
        start_time = time.time()
        context = ExecutionContext()
        
        try:
            # 1. Resolve chain
            chain = await self.resolver.resolve(tool_id)
            if not chain:
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=0,
                    error=f"Tool '{tool_id}' not found or has no executor chain",
                )
            context.chain = chain

            # 2. Verify integrity at every step (if enabled)
            if self.verify_integrity:
                integrity_result = self._verify_chain_integrity(chain)
                if not integrity_result["success"]:
                    return ExecutionResult(
                        success=False,
                        data=None,
                        duration_ms=int((time.time() - start_time) * 1000),
                        error=integrity_result["error"],
                        metadata={"integrity_failure": True},
                    )
                context.integrity_verified = True
                context.verification_cached = integrity_result.get("cached_count", 0)
            
            # 3. Validate parent→child relationships (if enabled)
            if self.validate_chain:
                chain_result = self._validate_chain_relationships(chain)
                if not chain_result["valid"]:
                    return ExecutionResult(
                        success=False,
                        data=None,
                        duration_ms=int((time.time() - start_time) * 1000),
                        error=f"Chain validation failed: {'; '.join(chain_result['issues'])}",
                        metadata={"chain_validation_failure": True},
                    )
                context.chain_validated = True
                
                # Log warnings
                for warning in chain_result.get("warnings", []):
                    logger.warning(f"Chain validation warning for {tool_id}: {warning}")

            # 4. Find terminal primitive
            terminal_tool = chain[-1]
            if terminal_tool.get("tool_type") != "primitive":
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Invalid tool chain: terminal tool '{terminal_tool.get('tool_id')}' is not a primitive",
                )

            primitive_type = terminal_tool.get("tool_id")

            # 5. Merge configs
            config = self.resolver.merge_configs(chain)

            # 6. Runtime parameter validation (Layer 2)
            terminal_manifest = terminal_tool.get("manifest", {})
            validation_result = self._validate_runtime_params(config, terminal_manifest)

            if not validation_result.get("valid", True):
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Parameter validation failed: {'; '.join(validation_result.get('issues', []))}",
                    metadata={"validation_issues": validation_result.get("issues", [])},
                )

            # Log any warnings but continue execution
            if validation_result.get("warnings"):
                for warning in validation_result["warnings"]:
                    logger.warning(f"Runtime validation warning for {tool_id}: {warning}")

            # 7. Execute with appropriate primitive
            if primitive_type == "subprocess":
                # Build execution config with file path and CLI args
                exec_config = self._build_subprocess_config(config, params)
                # Remove internal params before passing to subprocess
                exec_params = {k: v for k, v in params.items() if not k.startswith("_")}
                result = await self.subprocess_primitive.execute(exec_config, exec_params)
                exec_result = self._convert_subprocess_result(result)
            elif primitive_type == "http_client":
                # Remove internal params for HTTP (like _file_path)
                exec_params = {k: v for k, v in params.items() if not k.startswith("_")}
                result = await self.http_client_primitive.execute(config or {}, exec_params)
                exec_result = self._convert_http_result(result)
            else:
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Unknown primitive type: {primitive_type}",
                )
            
            # Add execution context to metadata
            if exec_result.metadata is None:
                exec_result.metadata = {}
            exec_result.metadata["integrity_verified"] = context.integrity_verified
            exec_result.metadata["chain_validated"] = context.chain_validated
            exec_result.metadata["chain_length"] = len(chain)
            
            return exec_result

        except Exception as e:
            logger.exception(f"Execution failed for {tool_id}")
            return ExecutionResult(
                success=False, 
                data=None, 
                duration_ms=int((time.time() - start_time) * 1000), 
                error=f"Execution failed: {e}"
            )
    
    def _verify_chain_integrity(self, chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify integrity of every tool in the chain.
        
        Uses caching to avoid re-verification of already-verified tools.
        """
        verifier = self._get_integrity_verifier()
        
        # Check cache first for each tool
        tools_to_verify = []
        cached_count = 0
        
        for tool in chain:
            content_hash = tool.get("content_hash") or tool.get("integrity")
            if content_hash and self.resolver.is_integrity_verified(content_hash):
                cached_count += 1
            else:
                tools_to_verify.append(tool)
        
        # If all cached, return success
        if not tools_to_verify:
            return {"success": True, "cached_count": cached_count}
        
        # Verify uncached tools
        result = verifier.verify_chain(tools_to_verify)
        
        if result.success:
            # Cache newly verified integrities
            for tool in tools_to_verify:
                content_hash = tool.get("content_hash") or tool.get("integrity")
                if content_hash:
                    self.resolver.mark_integrity_verified(content_hash)
        
        return {
            "success": result.success,
            "error": result.error,
            "cached_count": cached_count,
            "verified_count": result.verified_count,
        }
    
    def _validate_chain_relationships(self, chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate parent→child relationships in the chain.
        
        Uses caching to avoid re-validation of already-validated pairs.
        """
        validator = self._get_chain_validator()
        
        issues = []
        warnings = []
        cached_count = 0
        
        # Check each pair
        for i in range(len(chain) - 1):
            child = chain[i]
            parent = chain[i + 1]
            
            parent_hash = parent.get("content_hash") or parent.get("integrity", "")
            child_hash = child.get("content_hash") or child.get("integrity", "")
            
            # Check cache
            if parent_hash and child_hash:
                cached = self.resolver.get_cached_validation(parent_hash, child_hash)
                if cached is not None:
                    cached_count += 1
                    if not cached.get("valid", True):
                        issues.extend(cached.get("issues", []))
                    warnings.extend(cached.get("warnings", []))
                    continue
            
            # Validate this pair
            result = validator._validate_pair(parent, child)
            
            # Cache result
            if parent_hash and child_hash:
                self.resolver.cache_pair_validation(parent_hash, child_hash, result)
            
            if not result.get("valid", True):
                for issue in result.get("issues", []):
                    issues.append(f"[{parent.get('tool_id')}→{child.get('tool_id')}] {issue}")
            
            for warning in result.get("warnings", []):
                warnings.append(f"[{parent.get('tool_id')}→{child.get('tool_id')}] {warning}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "cached_count": cached_count,
        }

    def _build_subprocess_config(
        self, 
        config: Dict[str, Any], 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build subprocess config with file path and CLI args.
        
        Injects the _file_path from params into config args, and converts
        user params to CLI-style arguments.
        
        Args:
            config: Merged config from chain (command, args, env, etc.)
            params: Runtime params including _file_path and user inputs
            
        Returns:
            Config dict ready for subprocess execution
        """
        exec_config = config.copy()
        args = list(config.get("args", []))
        
        # Inject file path as first arg (for python/script execution)
        file_path = params.get("_file_path")
        if file_path:
            args.insert(0, file_path)
        
        # Convert user params to CLI args (--key value)
        for key, value in params.items():
            if key.startswith("_"):
                continue  # Skip internal params
            if value is None:
                continue
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            else:
                args.append(f"--{key}")
                args.append(str(value))
        
        exec_config["args"] = args
        return exec_config

    def _convert_subprocess_result(self, result: SubprocessResult) -> ExecutionResult:
        """Convert SubprocessResult to ExecutionResult."""
        return ExecutionResult(
            success=result.success,
            data={
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.return_code,
            },
            duration_ms=result.duration_ms,
            error=result.stderr if not result.success else None,
            metadata={"type": "subprocess", "return_code": result.return_code},
        )

    def _convert_http_result(self, result: HttpResult) -> ExecutionResult:
        """Convert HttpResult to ExecutionResult."""
        return ExecutionResult(
            success=result.success,
            data=result.body,
            duration_ms=result.duration_ms,
            error=result.error,
            metadata={
                "type": "http_client",
                "status_code": result.status_code,
                "headers": result.headers,
            },
        )

    async def close(self):
        """Close resources."""
        await self.http_client_primitive.close()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        stats = self.resolver.get_cache_stats()
        
        if self._integrity_verifier:
            stats["integrity_verifier"] = self._integrity_verifier.get_cache_stats()
        
        if self._schema_validator and hasattr(self._schema_validator, "get_cache_stats"):
            stats["schema_validator"] = self._schema_validator.get_cache_stats()
        
        return stats
