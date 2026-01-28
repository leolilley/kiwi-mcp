"""
Tests for EnvResolver kernel service.

Tests all resolver types in isolation with no side effects.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from kiwi_mcp.runtime.env_resolver import EnvResolver


class TestEnvResolverInit:
    """Test EnvResolver initialization."""

    def test_init_with_project_path(self):
        """Test initialization with project path."""
        project = Path("/tmp/test-project")
        resolver = EnvResolver(project_path=project)

        assert resolver.project_path == project
        assert resolver.user_space == Path.home() / ".ai"

    def test_init_without_project_path(self):
        """Test initialization without project path."""
        resolver = EnvResolver()

        assert resolver.project_path is None
        assert resolver.user_space == Path.home() / ".ai"

    def test_init_with_custom_user_space(self):
        """Test initialization with USER_SPACE override."""
        custom_space = "/tmp/custom-ai"
        with patch.dict(os.environ, {"USER_SPACE": custom_space}):
            resolver = EnvResolver()
            assert resolver.user_space == Path(custom_space)


class TestExpandValue:
    """Test ${VAR} expansion."""

    def test_simple_expansion(self):
        """Test simple ${VAR} expansion."""
        resolver = EnvResolver()
        env = {"HOME": "/home/user", "PATH": "/usr/bin"}

        result = resolver._expand_value("${HOME}/bin", env)
        assert result == "/home/user/bin"

    def test_expansion_with_default(self):
        """Test ${VAR:-default} expansion."""
        resolver = EnvResolver()
        env = {"HOME": "/home/user"}

        # Var exists - use value
        result = resolver._expand_value("${HOME:-/tmp}", env)
        assert result == "/home/user"

        # Var missing - use default
        result = resolver._expand_value("${MISSING:-/tmp}", env)
        assert result == "/tmp"

    def test_multiple_expansions(self):
        """Test multiple variable expansions in one string."""
        resolver = EnvResolver()
        env = {"HOME": "/home/user", "USER": "alice"}

        result = resolver._expand_value("${HOME}/projects/${USER}", env)
        assert result == "/home/user/projects/alice"

    def test_no_expansion_needed(self):
        """Test strings without variables."""
        resolver = EnvResolver()
        env = {}

        result = resolver._expand_value("/usr/bin/python3", env)
        assert result == "/usr/bin/python3"


class TestSystemBinaryResolver:
    """Test system_binary resolver type."""

    def test_resolve_existing_binary(self):
        """Test resolving an existing system binary."""
        resolver = EnvResolver()

        # Use a binary that definitely exists
        python_path = shutil.which("python3") or shutil.which("python")
        if not python_path:
            pytest.skip("No python available in PATH")

        config = {
            "type": "system_binary",
            "binary": "python3" if shutil.which("python3") else "python",
            "var": "TEST_PYTHON",
        }

        result = resolver._resolve_system_binary(config)
        assert result is not None
        assert Path(result).exists()

    def test_resolve_missing_binary_with_fallback(self):
        """Test resolving missing binary returns fallback."""
        resolver = EnvResolver()

        config = {
            "type": "system_binary",
            "binary": "nonexistent-binary-xyz",
            "var": "TEST_BIN",
            "fallback": "fallback-binary",
        }

        result = resolver._resolve_system_binary(config)
        assert result == "fallback-binary"

    def test_resolve_missing_binary_no_fallback(self):
        """Test resolving missing binary without fallback."""
        resolver = EnvResolver()

        config = {
            "type": "system_binary",
            "binary": "nonexistent-binary-xyz",
            "var": "TEST_BIN",
        }

        result = resolver._resolve_system_binary(config)
        assert result is None


class TestVenvPythonResolver:
    """Test venv_python resolver type."""

    def test_resolve_system_python(self):
        """Test falling back to system Python."""
        resolver = EnvResolver(project_path=Path("/nonexistent"))

        config = {
            "type": "venv_python",
            "search": ["system"],
            "var": "KIWI_PYTHON",
        }

        result = resolver._resolve_venv_python(config)
        # Should find system python
        assert result is not None
        if result:  # May be None on systems without python
            assert "python" in result.lower()

    def test_resolve_with_existing_project_venv(self, tmp_path):
        """Test resolving Python from project venv."""
        # Create mock project venv
        project = tmp_path / "project"
        venv_dir = project / ".venv" / "bin"
        venv_dir.mkdir(parents=True)
        python_path = venv_dir / "python"
        python_path.touch()
        python_path.chmod(0o755)

        resolver = EnvResolver(project_path=project)

        config = {
            "type": "venv_python",
            "search": ["project", "system"],
            "var": "KIWI_PYTHON",
        }

        result = resolver._resolve_venv_python(config)
        assert result == str(python_path)

    def test_resolve_with_kiwi_venv(self, tmp_path):
        """Test resolving Python from kiwi venv."""
        # Create mock kiwi venv
        project = tmp_path / "project"
        kiwi_venv = project / ".ai" / "scripts" / ".venv" / "bin"
        kiwi_venv.mkdir(parents=True)
        python_path = kiwi_venv / "python"
        python_path.touch()
        python_path.chmod(0o755)

        resolver = EnvResolver(project_path=project)

        config = {
            "type": "venv_python",
            "search": ["kiwi", "system"],
            "var": "KIWI_PYTHON",
        }

        result = resolver._resolve_venv_python(config)
        assert result == str(python_path)

    def test_resolve_search_order(self, tmp_path):
        """Test that search order is respected."""
        # Create both project and kiwi venvs
        project = tmp_path / "project"

        project_venv = project / ".venv" / "bin"
        project_venv.mkdir(parents=True)
        project_python = project_venv / "python"
        project_python.touch()
        project_python.chmod(0o755)

        kiwi_venv = project / ".ai" / "scripts" / ".venv" / "bin"
        kiwi_venv.mkdir(parents=True)
        kiwi_python = kiwi_venv / "python"
        kiwi_python.touch()
        kiwi_python.chmod(0o755)

        resolver = EnvResolver(project_path=project)

        # Search project first
        config = {
            "type": "venv_python",
            "search": ["project", "kiwi"],
            "var": "KIWI_PYTHON",
        }
        result = resolver._resolve_venv_python(config)
        assert result == str(project_python)

        # Search kiwi first
        config["search"] = ["kiwi", "project"]
        result = resolver._resolve_venv_python(config)
        assert result == str(kiwi_python)


class TestNodeModulesResolver:
    """Test node_modules resolver type."""

    def test_resolve_system_node(self):
        """Test falling back to system Node."""
        resolver = EnvResolver(project_path=Path("/nonexistent"))

        config = {
            "type": "node_modules",
            "search": ["system"],
            "var": "KIWI_NODE",
        }

        result = resolver._resolve_node_modules(config)
        # May be None if node not installed
        if result:
            assert "node" in result.lower()

    def test_resolve_with_project_node_modules(self, tmp_path):
        """Test resolving Node from project node_modules."""
        project = tmp_path / "project"
        node_bin = project / "node_modules" / ".bin"
        node_bin.mkdir(parents=True)
        node_path = node_bin / "node"
        node_path.touch()
        node_path.chmod(0o755)

        resolver = EnvResolver(project_path=project)

        config = {
            "type": "node_modules",
            "search": ["project", "system"],
            "var": "KIWI_NODE",
        }

        result = resolver._resolve_node_modules(config)
        assert result == str(node_path)


class TestVersionManagerResolvers:
    """Test version manager resolvers (rbenv, nvm, asdf)."""

    def test_resolve_rbenv_without_version(self):
        """Test rbenv resolver falls back to system ruby."""
        resolver = EnvResolver()

        result = resolver._resolve_rbenv(version=None)
        # Should return system ruby path or None
        if result:
            assert "ruby" in result.lower()

    def test_resolve_nvm_without_version(self):
        """Test nvm resolver falls back to system node."""
        resolver = EnvResolver()

        result = resolver._resolve_nvm(version=None)
        # Should return system node path or None
        if result:
            assert "node" in result.lower()

    def test_resolve_asdf_without_plugin(self):
        """Test asdf resolver requires plugin."""
        resolver = EnvResolver()

        result = resolver._resolve_asdf(plugin=None, version="1.0.0")
        assert result is None

    def test_resolve_version_manager_unknown(self):
        """Test unknown version manager returns fallback."""
        resolver = EnvResolver()

        config = {
            "type": "version_manager",
            "manager": "unknown-manager",
            "var": "TEST_BIN",
            "fallback": "fallback-bin",
        }

        result = resolver._resolve_version_manager(config)
        assert result == "fallback-bin"


class TestResolveMethod:
    """Test main resolve() method."""

    def test_resolve_without_config(self):
        """Test resolve with no ENV_CONFIG."""
        resolver = EnvResolver()

        env = resolver.resolve()

        # Should return system env
        assert "PATH" in env
        assert "HOME" in env

    def test_resolve_with_interpreter_config(self):
        """Test resolve with interpreter config."""
        resolver = EnvResolver()

        env_config = {
            "interpreter": {
                "type": "system_binary",
                "binary": "python3",
                "var": "KIWI_PYTHON",
                "fallback": "python",
            }
        }

        env = resolver.resolve(env_config=env_config)

        # Should have KIWI_PYTHON set
        assert "KIWI_PYTHON" in env
        assert env["KIWI_PYTHON"] is not None

    def test_resolve_with_static_env(self):
        """Test resolve with static environment variables."""
        resolver = EnvResolver()

        env_config = {
            "env": {
                "CUSTOM_VAR": "custom_value",
                "PYTHONUNBUFFERED": "1",
            }
        }

        env = resolver.resolve(env_config=env_config)

        assert env["CUSTOM_VAR"] == "custom_value"
        assert env["PYTHONUNBUFFERED"] == "1"

    def test_resolve_with_expansion(self):
        """Test resolve with variable expansion."""
        resolver = EnvResolver()

        env_config = {
            "interpreter": {
                "type": "system_binary",
                "binary": "python3",
                "var": "KIWI_PYTHON",
                "fallback": "python",
            },
            "env": {
                "PYTHON_BIN": "${KIWI_PYTHON}",
                "CUSTOM_PATH": "${HOME}/custom",
            },
        }

        env = resolver.resolve(env_config=env_config)

        assert env["PYTHON_BIN"] == env["KIWI_PYTHON"]
        assert env["CUSTOM_PATH"].endswith("/custom")

    def test_resolve_with_tool_env_override(self):
        """Test that tool env overrides static env."""
        resolver = EnvResolver()

        env_config = {
            "env": {
                "MY_VAR": "from_config",
            }
        }

        tool_env = {
            "MY_VAR": "from_tool",
        }

        env = resolver.resolve(env_config=env_config, tool_env=tool_env)

        # Tool env should win
        assert env["MY_VAR"] == "from_tool"

    def test_resolve_with_fallback_interpreter(self):
        """Test resolve uses fallback when interpreter not found."""
        resolver = EnvResolver(project_path=Path("/nonexistent"))

        env_config = {
            "interpreter": {
                "type": "venv_python",
                "search": ["project", "kiwi"],  # Skip system
                "var": "KIWI_PYTHON",
                "fallback": "python3",
            }
        }

        env = resolver.resolve(env_config=env_config)

        # Should use fallback since project/kiwi don't exist
        assert env["KIWI_PYTHON"] == "python3"


class TestOSPortability:
    """Test OS-specific behavior."""

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_windows_paths(self):
        """Test Windows-specific path handling."""
        resolver = EnvResolver(project_path=Path("C:/project"))
        locations = resolver._build_python_locations()

        # Should use Scripts instead of bin
        assert "Scripts" in str(locations["project"])
        assert "python.exe" in str(locations["project"])

    def test_unix_paths(self):
        """Test Unix-specific path handling."""
        with patch("os.name", "posix"):
            resolver = EnvResolver(project_path=Path("/project"))
            locations = resolver._build_python_locations()

            # Should use bin
            assert "/bin/python" in str(locations["project"])

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_node_windows_paths(self):
        """Test Windows Node paths."""
        resolver = EnvResolver(project_path=Path("C:/project"))
        locations = resolver._build_node_locations()

        # Should use .exe extension
        assert "node.exe" in str(locations["project"])


class TestDotenvLoading:
    """Test .env file loading."""

    def test_load_dotenv_without_python_dotenv(self):
        """Test dotenv loading when python-dotenv not installed."""
        resolver = EnvResolver()

        # Mock the import to fail
        with patch.dict("sys.modules", {"dotenv": None}):
            env_vars = resolver._load_dotenv_files()
            assert env_vars == {}

    def test_load_dotenv_files(self, tmp_path):
        """Test loading .env files in correct precedence."""
        pytest.importorskip("dotenv")  # Skip if python-dotenv not installed

        project = tmp_path / "project"
        project.mkdir()

        # Create .env file
        env_file = project / ".env"
        env_file.write_text("VAR1=value1\nVAR2=value2\n")

        # Create .env.local file (should override)
        env_local = project / ".env.local"
        env_local.write_text("VAR2=local_value\nVAR3=value3\n")

        resolver = EnvResolver(project_path=project)
        env_vars = resolver._load_dotenv_files()

        assert env_vars["VAR1"] == "value1"
        assert env_vars["VAR2"] == "local_value"  # .env.local wins
        assert env_vars["VAR3"] == "value3"


class TestResolverRegistry:
    """Test resolver type registry."""

    def test_all_resolver_types_have_methods(self):
        """Test that all registered resolver types have corresponding methods."""
        resolver = EnvResolver()

        for resolver_type, method_name in resolver.RESOLVER_TYPES.items():
            assert hasattr(resolver, method_name), (
                f"Resolver type '{resolver_type}' missing method '{method_name}'"
            )
            method = getattr(resolver, method_name)
            assert callable(method), f"Method '{method_name}' is not callable"

    def test_unknown_resolver_type(self):
        """Test that unknown resolver types return fallback."""
        resolver = EnvResolver()

        env_config = {
            "interpreter": {
                "type": "unknown_type",
                "var": "TEST_VAR",
                "fallback": "fallback_value",
            }
        }

        env = resolver.resolve(env_config=env_config)
        assert env["TEST_VAR"] == "fallback_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
