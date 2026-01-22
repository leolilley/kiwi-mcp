"""Permission system for Kiwi Agent Harness.

Provides permission context parsing, checking, and inheritance for runtime security.
"""

import fnmatch
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import xml.etree.ElementTree as ET


@dataclass
class CheckResult:
    """Result of a permission check."""

    allowed: bool
    reason: str = ""
    annealing_hint: str = ""


@dataclass
class PermissionContext:
    """Permission context parsed from directive <permissions> tag."""

    filesystem_read: List[str] = field(default_factory=list)
    filesystem_write: List[str] = field(default_factory=list)
    tool_execute: List[str] = field(default_factory=list)
    shell_commands: List[str] = field(default_factory=list)
    mcp_access: List[str] = field(default_factory=list)

    @classmethod
    def from_directive(cls, permissions_xml: str) -> "PermissionContext":
        """Parse permissions from directive XML."""
        if not permissions_xml.strip():
            return cls()

        try:
            # Wrap in root element if not already wrapped
            if not permissions_xml.strip().startswith("<permissions"):
                permissions_xml = f"<permissions>{permissions_xml}</permissions>"

            root = ET.fromstring(permissions_xml)

            context = cls()

            for perm in root.findall(".//read"):
                resource = perm.get("resource", "")
                path = perm.get("path", "")
                if resource == "filesystem" and path:
                    context.filesystem_read.append(path)

            for perm in root.findall(".//write"):
                resource = perm.get("resource", "")
                path = perm.get("path", "")
                if resource == "filesystem" and path:
                    context.filesystem_write.append(path)

            for perm in root.findall(".//execute"):
                resource = perm.get("resource", "")
                action = perm.get("action", "")
                if resource == "tool":
                    tool_id = perm.get("tool_id", action)
                    if tool_id:
                        context.tool_execute.append(tool_id)
                elif resource == "shell":
                    if action:
                        context.shell_commands.append(action)
                elif resource.startswith("mcp:"):
                    mcp_name = resource[4:]  # Remove 'mcp:' prefix
                    context.mcp_access.append(mcp_name)

            return context

        except ET.ParseError as e:
            raise ValueError(f"Invalid permissions XML: {e}")

    def can_read(self, path: str) -> bool:
        """Check if path can be read using glob patterns."""
        return self._matches_patterns(path, self.filesystem_read)

    def can_write(self, path: str) -> bool:
        """Check if path can be written using glob patterns."""
        return self._matches_patterns(path, self.filesystem_write)

    def can_execute_tool(self, tool_id: str) -> bool:
        """Check if tool can be executed."""
        return self._matches_patterns(tool_id, self.tool_execute)

    def can_run_command(self, command: str) -> bool:
        """Check if shell command can be run."""
        # Extract command name (first word)
        cmd_name = command.split()[0] if command.strip() else ""
        return self._matches_patterns(cmd_name, self.shell_commands)

    def can_access_mcp(self, mcp_name: str) -> bool:
        """Check if MCP can be accessed."""
        return self._matches_patterns(mcp_name, self.mcp_access)

    def _matches_patterns(self, target: str, patterns: List[str]) -> bool:
        """Check if target matches any of the glob patterns."""
        if not patterns:
            return False

        for pattern in patterns:
            if pattern == "*" or fnmatch.fnmatch(target, pattern):
                return True

        return False

    def create_child_context(self, child_permissions_xml: str) -> "PermissionContext":
        """Create scoped child context for subagent.

        Child permissions must be subset of parent.
        Any permission not in parent is denied.
        """
        child = self.from_directive(child_permissions_xml)

        # Intersect with parent permissions
        child.filesystem_read = [
            p
            for p in child.filesystem_read
            if any(self._pattern_contains(parent_p, p) for parent_p in self.filesystem_read)
        ]

        child.filesystem_write = [
            p
            for p in child.filesystem_write
            if any(self._pattern_contains(parent_p, p) for parent_p in self.filesystem_write)
        ]

        child.tool_execute = [
            p
            for p in child.tool_execute
            if any(self._pattern_contains(parent_p, p) for parent_p in self.tool_execute)
        ]

        child.shell_commands = [
            p
            for p in child.shell_commands
            if any(self._pattern_contains(parent_p, p) for parent_p in self.shell_commands)
        ]

        child.mcp_access = [
            p
            for p in child.mcp_access
            if any(self._pattern_contains(parent_p, p) for parent_p in self.mcp_access)
        ]

        return child

    def _pattern_contains(self, parent_pattern: str, child_pattern: str) -> bool:
        """Check if parent pattern contains/allows child pattern."""
        if parent_pattern == "*":
            return True
        if parent_pattern == child_pattern:
            return True

        # Simple containment check for now
        # More sophisticated pattern algebra could be added
        if "*" in parent_pattern:
            return fnmatch.fnmatch(child_pattern, parent_pattern)

        return child_pattern.startswith(parent_pattern)


class PermissionChecker:
    """Checks tool calls against permission context."""

    def __init__(self, context: PermissionContext):
        self.context = context

    def check_tool_call(self, tool_id: str, params: Dict[str, Any]) -> CheckResult:
        """Check if tool call is permitted."""

        # Check tool execution permission
        if not self.context.can_execute_tool(tool_id):
            return CheckResult(
                allowed=False,
                reason=f"Tool '{tool_id}' not in permitted tool list",
                annealing_hint=f"Add <execute resource='tool' tool_id='{tool_id}' /> to directive permissions",
            )

        # Check file access permissions if tool accesses files
        file_params = ["path", "file_path", "filePath", "input_file", "output_file"]
        for param_name in file_params:
            if param_name in params:
                file_path = params[param_name]
                if isinstance(file_path, str):
                    # Determine if read or write based on common patterns
                    if self._is_write_operation(tool_id, param_name):
                        if not self.context.can_write(file_path):
                            return CheckResult(
                                allowed=False,
                                reason=f"Write access denied for path: {file_path}",
                                annealing_hint=f"Add <write resource='filesystem' path='{file_path}' /> to directive permissions",
                            )
                    else:
                        if not self.context.can_read(file_path):
                            return CheckResult(
                                allowed=False,
                                reason=f"Read access denied for path: {file_path}",
                                annealing_hint=f"Add <read resource='filesystem' path='{file_path}' /> to directive permissions",
                            )

        # Check shell command permissions
        if "command" in params:
            command = params["command"]
            if isinstance(command, str) and not self.context.can_run_command(command):
                cmd_name = command.split()[0] if command.strip() else ""
                return CheckResult(
                    allowed=False,
                    reason=f"Shell command '{cmd_name}' not permitted",
                    annealing_hint=f"Add <execute resource='shell' action='{cmd_name}' /> to directive permissions",
                )

        return CheckResult(allowed=True)

    def _is_write_operation(self, tool_id: str, param_name: str) -> bool:
        """Determine if operation is a write based on tool and parameter names."""
        write_indicators = ["output", "write", "save", "create", "edit", "update", "delete"]

        tool_lower = tool_id.lower()
        param_lower = param_name.lower()

        return any(
            indicator in tool_lower or indicator in param_lower for indicator in write_indicators
        )
