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
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
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


class ToolNotFoundError(Exception):
    """Raised when a tool cannot be found locally."""
    pass


class ChainResolver:
    """Resolves and caches executor chains from local filesystem only.
    
    Walks the chain of executor dependencies by:
    1. Resolving tool name to file path
    2. Extracting metadata from the file
    3. Following executor_id to next tool
    4. Stopping at primitives (executor_id is None)
    
    Returns chain structure with full integrity data.
    """

    def __init__(self, project_path: Path):
        """
        Initialize with project path for chain resolution.

        Args:
            project_path: Path to project root containing .ai/ folder
        """
        from pathlib import Path
        from kiwi_mcp.utils.resolvers import ToolResolver
        
        self.project_path = project_path if isinstance(project_path, Path) else Path(project_path)
        
        if not self.project_path:
            raise ValueError("project_path is required for chain resolution")
        
        self.resolver = ToolResolver(self.project_path)
        
        # Chain cache by tool_id
        self._chain_cache: Dict[str, List[Dict]] = {}
        
        # Verified integrity cache: content_hash -> verified_at timestamp
        self._integrity_cache: Dict[str, float] = {}
        
        # Validation cache: (parent_hash, child_hash) -> validation result
        self._validation_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        
        logger.debug(f"ChainResolver initialized with project_path={self.project_path}")

    async def resolve(self, tool_id: str) -> List[Dict]:
        """
        Resolve chain from local files only.
        
        Local-only resolution ensures:
        - Tools are executed from the local filesystem
        - Registry tools must be loaded first via 'load' action
        - No network dependency for execution
        
        Raises ToolNotFoundError if tool not found locally.
        """
        if tool_id in self._chain_cache:
            return self._chain_cache[tool_id]

        chain = await self._resolve_chain(tool_id)
        if chain:
            self._chain_cache[tool_id] = chain
            return chain
        
        return []

    async def _resolve_chain(self, tool_id: str) -> List[Dict[str, Any]]:
        """
        Resolve full executor chain by walking local files.

        Args:
            tool_id: Starting tool ID (e.g., "hello_node")

        Returns:
            Chain from leaf to primitive

        Raises:
            ToolNotFoundError: If tool is not found locally
        """
        from kiwi_mcp.schemas.tool_schema import extract_tool_metadata
        from kiwi_mcp.utils.metadata_manager import MetadataManager
        
        chain = []
        visited = set()
        current_id = tool_id

        while current_id:
            # Prevent infinite loops
            if current_id in visited:
                logger.error(f"Circular dependency detected: {current_id}")
                raise ToolNotFoundError(
                    f"Circular dependency in chain for '{tool_id}': {current_id} already visited"
                )
            visited.add(current_id)

            # Resolve file path
            file_path = self.resolver.resolve(current_id)
            if not file_path:
                # Tool not found locally
                if not chain:
                    # Starting tool not found
                    raise ToolNotFoundError(
                        f"Tool '{tool_id}' not found locally. "
                        f"Use 'load' action to copy from registry first."
                    )
                else:
                    # Dependency not found
                    raise ToolNotFoundError(
                        f"Dependency '{current_id}' not found locally for tool '{tool_id}'. "
                        f"Missing executor in chain: {[t['tool_id'] for t in chain]} → {current_id}"
                    )

            logger.debug(f"Resolved {current_id} to {file_path}")

            # Extract metadata
            try:
                metadata = extract_tool_metadata(file_path, self.project_path)
            except Exception as e:
                logger.error(f"Failed to extract metadata for {current_id}: {e}")
                raise ToolNotFoundError(
                    f"Failed to extract metadata from '{file_path}': {e}"
                )

            # Build chain link
            chain_link = {
                "tool_id": current_id,
                "tool_type": metadata.get("tool_type"),
                "executor_id": metadata.get("executor_id"),
                "version": metadata.get("version", "0.0.0"),
                "manifest": metadata,  # Use full metadata for integrity computation
                "file_path": str(file_path),
                "source": "local",
            }
            
            # Extract integrity hash from signature - fail if missing
            file_content = file_path.read_text()
            
            content_hash = MetadataManager.get_signature_hash(
                "tool", file_content, file_path=file_path, project_path=self.project_path
            )
            
            if not content_hash:
                raise ToolNotFoundError(
                    f"Tool '{current_id}' has no signature. "
                    f"Run execute(action='sign', item_id='{current_id}', ...) to validate."
                )
            
            # Build file hashes for integrity verification
            # Remove signature before computing file hash
            from kiwi_mcp.utils.metadata_manager import ToolMetadataStrategy
            strategy = ToolMetadataStrategy(file_path=file_path, project_path=self.project_path)
            content_without_sig = strategy.remove_signature(file_content)
            
            import hashlib
            file_hash = hashlib.sha256(content_without_sig.encode()).hexdigest()
            
            # Store both the content hash and file hashes for verification
            chain_link["content_hash"] = content_hash
            chain_link["files"] = [{
                "path": file_path.name,
                "sha256": file_hash
            }]
            logger.debug(f"Using signature hash for {current_id}: {content_hash[:12]}...")

            chain.append(chain_link)
            logger.debug(
                f"Added to chain: {current_id} ({metadata.get('tool_type')}) → {metadata.get('executor_id')}"
            )

            # Move to next executor
            current_id = metadata.get("executor_id")

            # Stop at primitives (executor_id is None)
            if current_id is None:
                logger.debug(f"Reached primitive, chain complete: {len(chain)} steps")
                break

        return chain

    async def resolve_batch(self, tool_ids: List[str]) -> Dict[str, List[Dict]]:
        """Batch resolve multiple chains from local files."""
        uncached = [t for t in tool_ids if t not in self._chain_cache]
        
        if uncached:
            results = {}
            for tool_id in uncached:
                try:
                    chain = await self._resolve_chain(tool_id)
                    results[tool_id] = chain
                    self._chain_cache[tool_id] = chain
                except ToolNotFoundError as e:
                    logger.warning(f"Tool '{tool_id}' not found: {e}")
                    results[tool_id] = []
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
        project_path: Path,
        verify_integrity: bool = True, 
        validate_chain: bool = True
    ):
        """
        Initialize with project path.

        Args:
            project_path: Project path for local chain resolution
            verify_integrity: Whether to verify integrity at every step
            validate_chain: Whether to validate parent→child relationships
        """
        self.project_path = project_path
        self.resolver = ChainResolver(project_path)
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


    def _template_config(self, config: Any, params: Dict[str, Any]) -> Any:
        """
        Template string values in config with runtime parameters.
        
        Recursively walks the config dict and replaces template strings like
        "{url}" or "{command}" with actual parameter values.
        
        Args:
            config: Configuration (dict, list, str, or primitive - may contain template strings)
            params: Runtime parameters to substitute
            
        Returns:
            Config with all template strings resolved (same type as input)
        """
        if isinstance(config, dict):
            return {k: self._template_config(v, params) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._template_config(item, params) for item in config]
        elif isinstance(config, str):
            # Single placeholder: "{param}" -> preserve type
            match = re.match(r'^\{(\w+)\}$', config.strip())
            if match is not None:
                param_name: str = match.group(1)
                if param_name in params:
                    return params[param_name]
                # Leave template as-is if param not provided
                return config
            
            # Multiple placeholders or mixed content: use format
            if '{' in config:
                try:
                    return config.format(**params)
                except KeyError:
                    # Missing param - leave as-is for validation to catch
                    return config
            
            return config
        
        # Primitive types - return as-is
        return config

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
        3. Validate parent->child relationships (if enabled)
        4. Merge configs from chain
        5. Template config with runtime params (NEW)
        6. Validate templated config against config_schema
        7. Execute via hardcoded primitive
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

            # 2. Verify integrity (unchanged)
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
            
            # 3. Validate chain relationships (unchanged)
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
                
                for warning in chain_result.get("warnings", []):
                    logger.warning(f"Chain validation warning for {tool_id}: {warning}")

            # 4. Find terminal primitive (unchanged)
            terminal_tool = chain[-1]
            if terminal_tool.get("tool_type") != "primitive":
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Invalid tool chain: terminal tool '{terminal_tool.get('tool_id')}' is not a primitive",
                )

            primitive_type = terminal_tool.get("tool_id")

            # 5. Merge configs (unchanged)
            config = self.resolver.merge_configs(chain)

            # 6. Template config with params BEFORE validation (KEY FIX)
            templated_config = self._template_config(config, params)

            # 7. Runtime parameter validation (now on TEMPLATED config)
            terminal_manifest = terminal_tool.get("manifest", {})
            validation_result = self._validate_runtime_params(templated_config, terminal_manifest)

            if not validation_result.get("valid", True):
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Parameter validation failed: {'; '.join(validation_result.get('issues', []))}",
                    metadata={"validation_issues": validation_result.get("issues", [])},
                )

            if validation_result.get("warnings"):
                for warning in validation_result["warnings"]:
                    logger.warning(f"Runtime validation warning for {tool_id}: {warning}")

            # 8. Execute with appropriate primitive (use TEMPLATED config)
            if primitive_type == "subprocess":
                # Build execution config with file path and CLI args
                exec_config = self._build_subprocess_config(templated_config, params)
                exec_params = {k: v for k, v in params.items() if not k.startswith("_")}
                result = await self.subprocess_primitive.execute(exec_config, exec_params)
                exec_result = self._convert_subprocess_result(result)
            elif primitive_type == "http_client":
                exec_params = {k: v for k, v in params.items() if not k.startswith("_")}
                # HTTP primitive handles its own templating, but we already did it
                # So we can pass templated_config directly
                result = await self.http_client_primitive.execute(templated_config, exec_params)
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
