"""Tests for permission system."""

import pytest
from kiwi_mcp.runtime.permissions import PermissionContext, PermissionChecker, CheckResult


class TestPermissionContext:
    """Test PermissionContext parsing and checking."""

    def test_empty_permissions(self):
        """Test empty permissions context."""
        context = PermissionContext.from_directive("")
        assert context.filesystem_read == []
        assert context.filesystem_write == []
        assert context.tool_execute == []
        assert context.shell_commands == []
        assert context.mcp_access == []

    def test_parse_filesystem_permissions(self):
        """Test parsing filesystem permissions."""
        xml = """
        <permissions>
            <read resource="filesystem" path="**/*.py" />
            <write resource="filesystem" path="output/*" />
        </permissions>
        """
        context = PermissionContext.from_directive(xml)
        assert "**/*.py" in context.filesystem_read
        assert "output/*" in context.filesystem_write

    def test_parse_tool_permissions(self):
        """Test parsing tool execution permissions."""
        xml = """
        <permissions>
            <execute resource="tool" tool_id="git_status" />
            <execute resource="tool" action="health_check" />
        </permissions>
        """
        context = PermissionContext.from_directive(xml)
        assert "git_status" in context.tool_execute
        assert "health_check" in context.tool_execute

    def test_parse_shell_permissions(self):
        """Test parsing shell command permissions."""
        xml = """
        <permissions>
            <execute resource="shell" action="git" />
            <execute resource="shell" action="npm" />
        </permissions>
        """
        context = PermissionContext.from_directive(xml)
        assert "git" in context.shell_commands
        assert "npm" in context.shell_commands

    def test_parse_mcp_permissions(self):
        """Test parsing MCP access permissions."""
        xml = """
        <permissions>
            <execute resource="mcp:github" action="*" />
            <execute resource="mcp:supabase" action="query" />
        </permissions>
        """
        context = PermissionContext.from_directive(xml)
        assert "github" in context.mcp_access
        assert "supabase" in context.mcp_access

    def test_can_read_glob_patterns(self):
        """Test glob pattern matching for read permissions."""
        context = PermissionContext(filesystem_read=["**/*.py", "config.json"])

        assert context.can_read("src/main.py")
        assert context.can_read("tests/test_file.py")
        assert context.can_read("config.json")
        assert not context.can_read("data.txt")
        assert not context.can_read("config.yaml")

    def test_can_write_glob_patterns(self):
        """Test glob pattern matching for write permissions."""
        context = PermissionContext(filesystem_write=["output/*", "logs/*.log"])

        assert context.can_write("output/result.json")
        assert context.can_write("logs/app.log")
        assert not context.can_write("src/main.py")
        assert not context.can_write("logs/config.yaml")

    def test_can_execute_tool(self):
        """Test tool execution permission checking."""
        context = PermissionContext(tool_execute=["git_*", "health_check"])

        assert context.can_execute_tool("git_status")
        assert context.can_execute_tool("git_commit")
        assert context.can_execute_tool("health_check")
        assert not context.can_execute_tool("deploy_app")

    def test_can_run_command(self):
        """Test shell command permission checking."""
        context = PermissionContext(shell_commands=["git", "npm"])

        assert context.can_run_command("git status")
        assert context.can_run_command("npm install")
        assert not context.can_run_command("rm -rf /")
        assert not context.can_run_command("sudo apt update")

    def test_wildcard_permissions(self):
        """Test wildcard permissions."""
        context = PermissionContext(filesystem_read=["*"], tool_execute=["*"], shell_commands=["*"])

        assert context.can_read("any/file.txt")
        assert context.can_execute_tool("any_tool")
        assert context.can_run_command("any command")

    def test_create_child_context(self):
        """Test creating child context with restricted permissions."""
        parent = PermissionContext(
            filesystem_read=["**/*"],
            filesystem_write=["output/*"],
            tool_execute=["git_*", "health_check"],
            shell_commands=["git", "npm"],
        )

        child_xml = """
        <permissions>
            <read resource="filesystem" path="src/*" />
            <write resource="filesystem" path="output/temp/*" />
            <execute resource="tool" tool_id="git_status" />
            <execute resource="shell" action="git" />
        </permissions>
        """

        child = parent.create_child_context(child_xml)

        # Child should have subset of parent permissions
        assert "src/*" in child.filesystem_read
        assert "output/temp/*" in child.filesystem_write
        assert "git_status" in child.tool_execute
        assert "git" in child.shell_commands

    def test_invalid_xml(self):
        """Test handling of invalid XML."""
        with pytest.raises(ValueError, match="Invalid permissions XML"):
            PermissionContext.from_directive("<invalid>xml")


class TestPermissionChecker:
    """Test PermissionChecker functionality."""

    def test_allowed_tool_call(self):
        """Test allowed tool call."""
        context = PermissionContext(tool_execute=["git_status"])
        checker = PermissionChecker(context)

        result = checker.check_tool_call("git_status", {})
        assert result.allowed
        assert result.reason == ""

    def test_denied_tool_call(self):
        """Test denied tool call."""
        context = PermissionContext(tool_execute=["git_status"])
        checker = PermissionChecker(context)

        result = checker.check_tool_call("deploy_app", {})
        assert not result.allowed
        assert "not in permitted tool list" in result.reason
        assert "execute resource='tool'" in result.annealing_hint

    def test_file_read_permission_check(self):
        """Test file read permission checking."""
        context = PermissionContext(tool_execute=["read_file"], filesystem_read=["src/*"])
        checker = PermissionChecker(context)

        # Allowed read
        result = checker.check_tool_call("read_file", {"path": "src/main.py"})
        assert result.allowed

        # Denied read
        result = checker.check_tool_call("read_file", {"path": "config/secret.json"})
        assert not result.allowed
        assert "Read access denied" in result.reason

    def test_file_write_permission_check(self):
        """Test file write permission checking."""
        context = PermissionContext(tool_execute=["write_file"], filesystem_write=["output/*"])
        checker = PermissionChecker(context)

        # Allowed write
        result = checker.check_tool_call("write_file", {"output_file": "output/result.json"})
        assert result.allowed

        # Denied write
        result = checker.check_tool_call("write_file", {"output_file": "src/main.py"})
        assert not result.allowed
        assert "Write access denied" in result.reason

    def test_shell_command_permission_check(self):
        """Test shell command permission checking."""
        context = PermissionContext(tool_execute=["bash"], shell_commands=["git"])
        checker = PermissionChecker(context)

        # Allowed command
        result = checker.check_tool_call("bash", {"command": "git status"})
        assert result.allowed

        # Denied command
        result = checker.check_tool_call("bash", {"command": "rm -rf /"})
        assert not result.allowed
        assert "Shell command 'rm' not permitted" in result.reason

    def test_write_operation_detection(self):
        """Test detection of write operations."""
        checker = PermissionChecker(PermissionContext())

        # Write operations
        assert checker._is_write_operation("write_file", "output_path")
        assert checker._is_write_operation("create_document", "file_path")
        assert checker._is_write_operation("edit_config", "path")
        assert checker._is_write_operation("save_data", "location")

        # Read operations
        assert not checker._is_write_operation("read_file", "input_path")
        assert not checker._is_write_operation("get_data", "source")
        assert not checker._is_write_operation("fetch_info", "path")
