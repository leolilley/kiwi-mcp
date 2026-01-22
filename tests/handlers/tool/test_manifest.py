"""Tests for ToolManifest dataclass."""

import pytest
from pathlib import Path
import yaml
import tempfile

from kiwi_mcp.handlers.tool.manifest import ToolManifest


def test_tool_manifest_creation():
    """Test basic ToolManifest creation."""
    manifest = ToolManifest(
        tool_id="test_tool",
        tool_type="python",
        version="1.0.0",
        description="A test tool",
    )

    assert manifest.tool_id == "test_tool"
    assert manifest.tool_type == "python"
    assert manifest.version == "1.0.0"
    assert manifest.description == "A test tool"
    assert manifest.executor_config == {}
    assert manifest.parameters == []
    assert manifest.mutates_state == False


def test_tool_manifest_from_yaml():
    """Test loading manifest from YAML file."""
    manifest_data = {
        "tool_id": "yaml_tool",
        "tool_type": "python",
        "version": "2.0.0",
        "description": "Tool from YAML",
        "executor_config": {"timeout": 300},
        "parameters": [{"name": "input", "type": "string", "required": True}],
        "mutates_state": True,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(manifest_data, f)
        temp_path = Path(f.name)

    try:
        manifest = ToolManifest.from_yaml(temp_path)

        assert manifest.tool_id == "yaml_tool"
        assert manifest.tool_type == "python"
        assert manifest.version == "2.0.0"
        assert manifest.description == "Tool from YAML"
        assert manifest.executor_config == {"timeout": 300}
        assert len(manifest.parameters) == 1
        assert manifest.parameters[0]["name"] == "input"
        assert manifest.mutates_state == True

    finally:
        temp_path.unlink()


def test_tool_manifest_virtual_from_script():
    """Test generating virtual manifest from Python script."""
    script_content = '''"""Test script with docstring."""

def main(arg1, arg2="default"):
    """Main function with parameters."""
    pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        temp_path = Path(f.name)

    try:
        manifest = ToolManifest.virtual_from_script(temp_path)

        assert manifest.tool_id == temp_path.stem
        assert manifest.tool_type == "python"
        assert manifest.version == "1.0.0"
        assert manifest.description == "Test script with docstring."
        assert manifest.mutates_state == True  # Conservative default

        # Should extract parameters from main function
        param_names = [p["name"] for p in manifest.parameters]
        assert "arg1" in param_names
        assert "arg2" in param_names

    finally:
        temp_path.unlink()


def test_tool_manifest_virtual_fallback():
    """Test virtual manifest generation with parsing failure."""
    script_content = """# Invalid syntax for testing
def broken(
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        temp_path = Path(f.name)

    try:
        manifest = ToolManifest.virtual_from_script(temp_path)

        assert manifest.tool_id == temp_path.stem
        assert manifest.tool_type == "python"
        assert manifest.version == "1.0.0"
        assert manifest.description == "Legacy Python script"  # Fallback description
        assert manifest.parameters == []  # No parameters extracted

    finally:
        temp_path.unlink()
