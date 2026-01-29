"""
Tests for ToolValidator

Tests the Layer 1 (definition-time) validation for unified tools.
"""

import pytest
from pathlib import Path
from lilux.utils.validators import ToolValidator, ValidationManager


class TestToolValidator:
    """Test ToolValidator class - Layer 1 definition-time validation."""

    @pytest.fixture
    def validator(self):
        """Create ToolValidator instance."""
        return ToolValidator()

    # Filename validation tests

    def test_validate_filename_match_valid_python(self, validator):
        """Test filename validation for Python tools."""
        file_path = Path("test_tool.py")
        parsed_data = {"tool_id": "test_tool", "tool_type": "python"}

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is True
        assert result["issues"] == []

    def test_validate_filename_match_valid_yaml(self, validator):
        """Test filename validation for YAML tools."""
        file_path = Path("api_tool.yaml")
        parsed_data = {"tool_id": "api_tool", "tool_type": "api"}

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is True
        assert result["issues"] == []

    def test_validate_filename_match_valid_shell(self, validator):
        """Test filename validation for shell tools."""
        file_path = Path("deploy_script.sh")
        parsed_data = {"tool_id": "deploy_script", "tool_type": "bash"}

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is True
        assert result["issues"] == []

    def test_validate_filename_match_missing_tool_id(self, validator):
        """Test filename validation with missing tool_id."""
        file_path = Path("test_tool.py")
        parsed_data = {"tool_type": "python"}

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is False
        assert "Tool ID not found" in result["issues"][0]

    def test_validate_filename_match_wrong_extension(self, validator):
        """Test filename validation with unsupported extension."""
        file_path = Path("test_tool.txt")
        parsed_data = {"tool_id": "test_tool", "tool_type": "python"}

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is False
        assert "Unsupported file extension" in result["issues"][0]

    def test_validate_filename_match_name_mismatch(self, validator):
        """Test filename validation with name mismatch."""
        file_path = Path("wrong_name.py")
        parsed_data = {"tool_id": "test_tool", "tool_type": "python"}

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is False
        assert "mismatch" in result["issues"][0].lower()

    def test_validate_filename_match_uses_name_fallback(self, validator):
        """Test that 'name' field is used as fallback for tool_id."""
        file_path = Path("my_script.py")
        parsed_data = {"name": "my_script", "tool_type": "python"}

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is True

    # Metadata validation tests

    def test_validate_metadata_valid_python_tool(self, validator):
        """Test metadata validation for valid Python tool."""
        parsed_data = {
            "tool_id": "my_script",
            "tool_type": "python",
            "version": "1.0.0",
            "executor": "python_runtime",
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_metadata_valid_primitive(self, validator):
        """Test metadata validation for valid primitive (no executor required)."""
        parsed_data = {
            "tool_id": "subprocess",
            "tool_type": "primitive",
            "version": "1.0.0",
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_metadata_missing_tool_id(self, validator):
        """Test metadata validation with missing tool_id."""
        parsed_data = {
            "tool_type": "python",
            "version": "1.0.0",
            "executor": "python_runtime",
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is False
        assert any("tool id" in issue.lower() for issue in result["issues"])

    def test_validate_metadata_missing_tool_type(self, validator):
        """Test metadata validation with missing tool_type."""
        parsed_data = {
            "tool_id": "my_script",
            "version": "1.0.0",
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is False
        assert any("tool type" in issue.lower() for issue in result["issues"])

    def test_validate_metadata_missing_executor_for_non_primitive(self, validator):
        """Test metadata validation requires executor_id for non-primitive tools."""
        parsed_data = {
            "tool_id": "my_script",
            "tool_type": "custom_type",
            "version": "1.0.0",
            # Missing executor_id
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is False
        assert any("executor" in issue.lower() for issue in result["issues"])

    def test_validate_metadata_missing_version(self, validator):
        """Test metadata validation with missing version."""
        parsed_data = {
            "tool_id": "my_script",
            "tool_type": "python",
            "executor": "python_runtime",
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is False
        assert any("version" in issue.lower() for issue in result["issues"])

    def test_validate_metadata_invalid_version(self, validator):
        """Test metadata validation with invalid version format."""
        parsed_data = {
            "tool_id": "my_script",
            "tool_type": "python",
            "version": "not-semver",
            "executor": "python_runtime",
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is False
        assert any("version" in issue.lower() and "semver" in issue.lower() for issue in result["issues"])

    def test_validate_metadata_non_primitive_requires_executor(self, validator):
        """Test that non-primitive tools require executor_id."""
        parsed_data = {
            "tool_id": "my_script",
            "tool_type": "python",
            "version": "1.0.0",
            # Missing executor
        }

        result = validator.validate_metadata(parsed_data)

        assert result["valid"] is False
        assert any("executor" in issue.lower() for issue in result["issues"])

    def test_validate_metadata_accepts_executor_id_or_executor(self, validator):
        """Test that both executor_id and executor field names work."""
        # Test with executor_id
        parsed_data1 = {
            "tool_id": "my_script",
            "tool_type": "python",
            "version": "1.0.0",
            "executor_id": "python_runtime",
        }

        # Test with executor
        parsed_data2 = {
            "tool_id": "my_script",
            "tool_type": "python",
            "version": "1.0.0",
            "executor": "python_runtime",
        }

        assert validator.validate_metadata(parsed_data1)["valid"] is True
        assert validator.validate_metadata(parsed_data2)["valid"] is True

    def test_validate_metadata_dynamic_tool_types(self, validator):
        """Test that tool_type is completely dynamic - any string is valid."""
        dynamic_types = {"python", "bash", "api", "docker", "mcp", "runtime", "mcp_server", "mcp_tool", "custom_type", "my_special_tool"}

        for tool_type in dynamic_types:
            parsed_data = {
                "tool_id": f"test_{tool_type}",
                "tool_type": tool_type,
                "version": "1.0.0",
            }
            # Add executor for non-primitives
            if tool_type != "primitive":
                parsed_data["executor"] = "subprocess"

            result = validator.validate_metadata(parsed_data)
            assert result["valid"] is True, f"tool_type '{tool_type}' should be valid (dynamic)"


class TestValidationManagerToolRouting:
    """Test ValidationManager routes tool types correctly."""

    def test_get_validator_for_tool(self):
        """Test getting validator for 'tool' type."""
        validator = ValidationManager.get_validator("tool")
        assert isinstance(validator, ToolValidator)

    def test_get_validator_for_tool_subtypes(self):
        """Test tool subtypes are routed to ToolValidator."""
        subtypes = ["primitive", "runtime", "mcp_server", "mcp_tool", "api"]

        for subtype in subtypes:
            validator = ValidationManager.get_validator(subtype)
            assert isinstance(validator, ToolValidator), f"'{subtype}' should use ToolValidator"

    def test_tool_validator_in_validators_dict(self):
        """Test ToolValidator is in VALIDATORS dict."""
        assert "tool" in ValidationManager.VALIDATORS
        assert isinstance(ValidationManager.VALIDATORS["tool"], ToolValidator)
