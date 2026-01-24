"""ToolProxy - Central proxy for all tool calls with permission enforcement.

This is the core runtime security component that intercepts all tool calls,
enforces permissions, detects stuck patterns, and logs all operations.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .permissions import PermissionContext, PermissionChecker
from .loop_detector import LoopDetector, StuckSignal
from .audit import AuditLogger


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: Any = None
    error: Optional[str] = None
    annealing_hint: Optional[str] = None
    duration_ms: Optional[float] = None


class ToolProxy:
    """Central proxy for all tool calls with permission enforcement."""

    def __init__(
        self,
        permission_context: PermissionContext,
        primitive_executor,  # PrimitiveExecutor instance
        audit_logger: AuditLogger,
    ):
        self.permissions = PermissionChecker(permission_context)
        self.primitive_executor = primitive_executor
        self.audit = audit_logger
        self.loop_detector = LoopDetector()

    async def call_tool(self, tool_id: str, params: Dict[str, Any], session_id: str) -> ToolResult:
        """Execute a tool call with full security enforcement.

        This is the main entry point for all tool executions in the harness.
        """
        start_time = time.time()

        try:
            # 1. Check for stuck patterns
            stuck = self.loop_detector.record_call(tool_id, params)
            if stuck:
                self.audit.log_stuck_detected(session_id, stuck, tool_id)
                return ToolResult(
                    success=False,
                    error=f"Stuck pattern detected: {stuck.reason}",
                    annealing_hint=stuck.suggestion,
                )

            # 2. Check permissions
            check = self.permissions.check_tool_call(tool_id, params)
            self.audit.log_permission_check(session_id, tool_id, check, params)

            if not check.allowed:
                return ToolResult(
                    success=False,
                    error=f"Permission denied: {check.reason}",
                    annealing_hint=check.annealing_hint,
                )

            # 3. Load tool manifest
            manifest = await self._load_manifest(tool_id)
            if not manifest:
                error = f"Tool '{tool_id}' not found"
                self.audit.log_error(session_id, tool_id, error, params)
                return ToolResult(
                    success=False,
                    error=error,
                    annealing_hint="Check tool name spelling or create the tool",
                )

            # 4. Execute via PrimitiveExecutor
            execution_result = await self.primitive_executor.execute(tool_id, params)

            # Convert to ToolResult format
            duration_ms = (time.time() - start_time) * 1000
            result = ToolResult(
                success=execution_result.success,
                output=execution_result.data,
                error=execution_result.error,
                duration_ms=execution_result.duration_ms,
            )

            # Log execution
            self.audit.log_execution(
                session_id,
                tool_id,
                {"success": result.success, "output": result.output, "error": result.error},
                params,
                duration_ms,
            )

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error = f"Unexpected error during tool execution: {str(e)}"
            self.audit.log_error(session_id, tool_id, error, params)

            return ToolResult(
                success=False,
                error=error,
                duration_ms=duration_ms,
                annealing_hint="Check tool implementation and parameters",
            )

    async def _load_manifest(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Load tool metadata by ID using schema-driven extraction."""
        from kiwi_mcp.utils.resolvers import ToolResolver
        from kiwi_mcp.schemas import extract_tool_metadata
        
        resolver = ToolResolver()
        file_path = resolver.resolve(tool_id)
        if not file_path:
            return None
        
        try:
            return extract_tool_metadata(file_path)
        except Exception:
            return None

    def reset_loop_detector(self):
        """Reset the loop detector state."""
        self.loop_detector.reset()

    def get_audit_history(self, session_id: Optional[str] = None, limit: int = 100):
        """Get recent audit entries."""
        return self.audit.get_recent_entries(session_id, limit)
