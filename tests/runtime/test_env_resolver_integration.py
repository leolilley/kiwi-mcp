"""
Integration tests for EnvResolver with PrimitiveExecutor.

Tests that ENV_CONFIG from runtimes is properly extracted and applied.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from kiwi_mcp.primitives.executor import PrimitiveExecutor
from kiwi_mcp.runtime.env_resolver import EnvResolver


class TestEnvResolverIntegration:
    """Test EnvResolver integration with executor."""

    @pytest.fixture
    def project_path(self):
        """Create a temporary project path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            # Create .ai structure
            (project / ".ai" / "tools" / "runtimes").mkdir(parents=True)
            (project / ".ai" / "tools" / "extractors").mkdir(parents=True)
            (project / ".ai" / "tools" / "primitives").mkdir(parents=True)
            (project / ".ai" / "tools" / "python").mkdir(parents=True)
            yield project

    def test_env_resolver_instantiation(self, project_path):
        """Test that executor can instantiate with EnvResolver."""
        executor = PrimitiveExecutor(
            project_path=project_path,
            verify_integrity=False,  # Skip verification for this test
            validate_chain=False,
        )

        assert executor.env_resolver is not None
        assert executor.env_resolver.project_path == project_path

    def test_get_env_config_from_chain_no_runtime(self):
        """Test extracting ENV_CONFIG when no runtime in chain."""
        executor = PrimitiveExecutor(
            project_path=Path("/tmp/test"),
            verify_integrity=False,
            validate_chain=False,
        )

        # Chain with no runtime
        chain = [
            {
                "tool_id": "test_tool",
                "tool_type": "python",
                "manifest": {},
            },
            {
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "manifest": {},
            },
        ]

        env_config = executor._get_env_config_from_chain(chain)
        assert env_config is None

    def test_get_env_config_from_chain_with_runtime(self):
        """Test extracting ENV_CONFIG from runtime in chain."""
        executor = PrimitiveExecutor(
            project_path=Path("/tmp/test"),
            verify_integrity=False,
            validate_chain=False,
        )

        # Chain with runtime that has ENV_CONFIG
        chain = [
            {
                "tool_id": "test_tool",
                "tool_type": "python",
                "manifest": {},
            },
            {
                "tool_id": "python_runtime",
                "tool_type": "runtime",
                "manifest": {
                    "env_config": {
                        "interpreter": {
                            "type": "venv_python",
                            "search": ["system"],
                            "var": "KIWI_PYTHON",
                            "fallback": "python3",
                        },
                        "env": {
                            "PYTHONUNBUFFERED": "1",
                        },
                    },
                },
            },
            {
                "tool_id": "subprocess",
                "tool_type": "primitive",
                "manifest": {},
            },
        ]

        env_config = executor._get_env_config_from_chain(chain)
        assert env_config is not None
        assert "interpreter" in env_config
        assert env_config["interpreter"]["type"] == "venv_python"
        assert env_config["interpreter"]["var"] == "KIWI_PYTHON"

    def test_env_resolution_in_executor(self):
        """Test that environment is resolved before templating."""
        executor = PrimitiveExecutor(
            project_path=Path("/tmp/test"),
            verify_integrity=False,
            validate_chain=False,
        )

        # Simulate ENV_CONFIG resolution
        env_config = {
            "interpreter": {
                "type": "system_binary",
                "binary": "python3",
                "var": "KIWI_PYTHON",
                "fallback": "python",
            },
            "env": {
                "PYTHONUNBUFFERED": "1",
            },
        }

        resolved_env = executor.env_resolver.resolve(env_config=env_config)

        # Should have KIWI_PYTHON set
        assert "KIWI_PYTHON" in resolved_env
        assert resolved_env["KIWI_PYTHON"] is not None
        assert "PYTHONUNBUFFERED" in resolved_env
        assert resolved_env["PYTHONUNBUFFERED"] == "1"

        # Test templating with resolved env
        config = {
            "command": "${KIWI_PYTHON}",
            "args": ["-u", "-c", "print('hello')"],
        }

        template_params = {**resolved_env}
        templated = executor._template_config(config, template_params)

        # Command should be templated
        assert templated["command"] != "${KIWI_PYTHON}"
        assert "python" in templated["command"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
