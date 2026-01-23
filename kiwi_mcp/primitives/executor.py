"""
PrimitiveExecutor orchestrator that routes to the correct primitive.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from .subprocess import SubprocessPrimitive, SubprocessResult
from .http_client import HttpClientPrimitive, HttpResult


@dataclass
class ExecutionResult:
    """Unified result from primitive execution."""

    success: bool
    data: Any
    duration_ms: int
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChainResolver:
    """Resolves and caches executor chains with config merging."""

    def __init__(self, registry):
        """
        Initialize with tool registry.

        Args:
            registry: ToolRegistry instance for resolving tool chains
        """
        self.registry = registry
        self._chain_cache: Dict[str, List[Dict]] = {}

    async def resolve(self, tool_id: str) -> List[Dict]:
        """Resolve chain from database or cache."""
        if tool_id in self._chain_cache:
            return self._chain_cache[tool_id]

        chain = await self.registry.resolve_chain(tool_id)
        self._chain_cache[tool_id] = chain
        return chain

    async def resolve_batch(self, tool_ids: List[str]) -> Dict[str, List[Dict]]:
        """Batch resolve multiple chains (avoids N+1)."""
        uncached = [t for t in tool_ids if t not in self._chain_cache]
        if uncached:
            results = await self.registry.resolve_chains_batch(uncached)
            self._chain_cache.update(results)
        return {t: self._chain_cache.get(t, []) for t in tool_ids}

    def merge_configs(self, chain: List[Dict]) -> Dict:
        """Merge configs from chain (child overrides parent)."""
        merged = {}
        # Process from primitive to leaf (so leaf overrides)
        for item in reversed(chain):
            manifest = item.get("manifest", {})
            config = manifest.get("config", {})
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


class PrimitiveExecutor:
    """Orchestrator that routes execution to the correct primitive."""

    def __init__(self, registry):
        """
        Initialize with tool registry.

        Args:
            registry: ToolRegistry instance for resolving tool chains
        """
        self.registry = registry
        self.resolver = ChainResolver(registry)
        self.subprocess_primitive = SubprocessPrimitive()
        self.http_client_primitive = HttpClientPrimitive()

    async def execute(self, tool_id: str, params: Dict[str, Any]) -> ExecutionResult:
        """
        Execute a tool by resolving its chain and routing to the correct primitive.

        Args:
            tool_id: ID of the tool to execute
            params: Runtime parameters

        Returns:
            ExecutionResult with unified response
        """
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

            # 2. Find terminal primitive (highest depth, no executor_id)
            terminal_tool = chain[-1]

            # The terminal tool must be a primitive
            if terminal_tool.get("tool_type") != "primitive":
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=0,
                    error=f"Invalid tool chain: terminal tool '{terminal_tool.get('tool_id')}' is not a primitive",
                )

            primitive_type = terminal_tool.get("tool_id")

            # 3. Merge configs
            config = self.resolver.merge_configs(chain)

            # 4. Execute with appropriate primitive
            if primitive_type == "subprocess":
                result = await self.subprocess_primitive.execute(config, params)
                return self._convert_subprocess_result(result)
            elif primitive_type == "http_client":
                result = await self.http_client_primitive.execute(config, params)
                return self._convert_http_result(result)
            else:
                return ExecutionResult(
                    success=False,
                    data=None,
                    duration_ms=0,
                    error=f"Unknown primitive type: {primitive_type}",
                )

        except Exception as e:
            return ExecutionResult(
                success=False, data=None, duration_ms=0, error=f"Execution failed: {e}"
            )

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
