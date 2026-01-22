"""Audit logging for Kiwi Agent Harness.

Provides JSONL format logging for all operations, permission checks, and results.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .permissions import CheckResult


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: str
    session_id: str
    event_type: str  # "permission_check", "execution", "error", "stuck_detected"
    tool_id: str
    details: Dict[str, Any]


class AuditLogger:
    """JSONL format audit logger."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.log_dir = self.project_path / ".ai" / "logs" / "audit"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file = self.log_dir / f"{today}.jsonl"

    def log_permission_check(
        self,
        session_id: str,
        tool_id: str,
        check_result: CheckResult,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Log a permission check result."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            event_type="permission_check",
            tool_id=tool_id,
            details={
                "allowed": check_result.allowed,
                "reason": check_result.reason,
                "annealing_hint": check_result.annealing_hint,
                "params": self._sanitize_params(params) if params else {},
            },
        )
        self._write_entry(entry)

    def log_execution(
        self,
        session_id: str,
        tool_id: str,
        result: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ):
        """Log a tool execution result."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            event_type="execution",
            tool_id=tool_id,
            details={
                "success": result.get("success", False),
                "output_length": len(str(result.get("output", ""))),
                "error": result.get("error"),
                "duration_ms": duration_ms,
                "params": self._sanitize_params(params) if params else {},
            },
        )
        self._write_entry(entry)

    def log_error(
        self, session_id: str, tool_id: str, error: str, params: Optional[Dict[str, Any]] = None
    ):
        """Log an error during tool execution."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            event_type="error",
            tool_id=tool_id,
            details={"error": error, "params": self._sanitize_params(params) if params else {}},
        )
        self._write_entry(entry)

    def log_stuck_detected(
        self,
        session_id: str,
        stuck_signal: Any,  # StuckSignal from loop_detector
        current_tool_id: str,
    ):
        """Log when a stuck pattern is detected."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            event_type="stuck_detected",
            tool_id=current_tool_id,
            details={
                "pattern_type": stuck_signal.pattern_type,
                "reason": stuck_signal.reason,
                "suggestion": stuck_signal.suggestion,
                "calls_involved": len(stuck_signal.calls_involved),
            },
        )
        self._write_entry(entry)

    def _write_entry(self, entry: AuditEntry):
        """Write audit entry to JSONL file."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                json.dump(asdict(entry), f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            # Fallback logging to stderr if file write fails
            import sys

            print(f"Audit logging failed: {e}", file=sys.stderr)
            print(f"Entry: {asdict(entry)}", file=sys.stderr)

    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters for logging, removing sensitive data."""
        if not params:
            return {}

        sanitized = {}
        sensitive_keys = {
            "password",
            "token",
            "api_key",
            "secret",
            "auth",
            "credential",
            "private_key",
            "access_token",
            "refresh_token",
        }

        for key, value in params.items():
            key_lower = key.lower()

            # Redact sensitive values
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            # Truncate very long values
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...[TRUNCATED]"
            else:
                sanitized[key] = value

        return sanitized

    def get_recent_entries(
        self, session_id: Optional[str] = None, limit: int = 100
    ) -> list[AuditEntry]:
        """Get recent audit entries, optionally filtered by session."""
        entries = []

        if not self.log_file.exists():
            return entries

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Read from end of file
            for line in reversed(lines[-limit:]):
                try:
                    data = json.loads(line.strip())
                    entry = AuditEntry(**data)

                    if session_id is None or entry.session_id == session_id:
                        entries.append(entry)

                except (json.JSONDecodeError, TypeError):
                    continue  # Skip malformed entries

        except Exception:
            pass  # Return empty list on any file read error

        return list(reversed(entries))  # Return in chronological order
