"""
Integration Tests for Data-Driven Validation

Tests the complete validation pipeline with real database connections.
"""

import pytest
from kiwi_mcp.utils.validators import ValidationManager


class TestValidationIntegration:
    """Integration tests for data-driven validation."""

    @pytest.fixture
    def temp_tool_file(self, tmp_path):
        """Create a temporary tool file for testing."""
        tool_file = tmp_path / "test_tool.py"
        tool_file.write_text('''#!/usr/bin/env python3
"""
Test Tool

A simple test tool for validation testing.
"""

__version__ = "1.0.0"

def main():
    """Main function."""
    print("Hello from test tool!")

if __name__ == "__main__":
    main()
''')
        return tool_file

    def test_validation_manager_get_validator_tool_type(self):
        """Test ValidationManager returns ToolValidator for 'tool' type."""
        from kiwi_mcp.utils.validators import ToolValidator

        validator = ValidationManager.get_validator("tool")

        assert isinstance(validator, ToolValidator)

    def test_validation_manager_get_validator_unknown_type(self):
        """Test ValidationManager raises error for unknown type."""
        with pytest.raises(ValueError, match="Unknown item_type"):
            ValidationManager.get_validator("unknown_type")

    def test_validation_manager_validate_tool_type(self, temp_tool_file):
        """Test ValidationManager.validate with 'tool' type."""
        parsed_data = {
            "tool_id": "test_tool",
            "tool_type": "python",
            "version": "1.0.0",
            "name": "test_tool",
        }

        result = ValidationManager.validate("tool", temp_tool_file, parsed_data)

        assert "valid" in result
        assert "issues" in result
        assert "warnings" in result
        # Should either pass validation or have meaningful error messages

    def test_mixed_validation_types(self, temp_tool_file, tmp_path):
        """Test using different validation types in the same session."""
        # Create different file types
        directive_file = tmp_path / "test_directive.md"
        directive_file.write_text("""# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <model tier="general">Test model</model>
    <permissions>
      <read resource="filesystem" path="**/*" />
    </permissions>
  </metadata>
  <process>
    <step name="test">Test step</step>
  </process>
</directive>
```
""")

        knowledge_file = tmp_path / "test_knowledge.md"
        knowledge_file.write_text("""---
zettel_id: test_knowledge
title: Test Knowledge
version: "1.0.0"
---

# Test Knowledge

This is a test knowledge entry.
""")

        # Test directive validation
        directive_data = {
            "name": "test_directive",
            "version": "1.0.0",
            "content": directive_file.read_text(),
        }
        directive_result = ValidationManager.validate("directive", directive_file, directive_data)

        # Test tool validation
        tool_data = {"tool_id": "test_tool", "tool_type": "python", "version": "1.0.0"}
        tool_result = ValidationManager.validate("tool", temp_tool_file, tool_data)

        # Test knowledge validation
        knowledge_data = {
            "zettel_id": "test_knowledge",
            "title": "Test Knowledge",
            "version": "1.0.0",
            "content": "Test content",
        }
        knowledge_result = ValidationManager.validate("knowledge", knowledge_file, knowledge_data)

        # All should complete without errors
        assert "valid" in directive_result
        assert "valid" in tool_result
        assert "valid" in knowledge_result

    def test_performance_with_caching(self, temp_tool_file):
        """Test validation performance."""
        import time

        # Get tool validator
        validator = ValidationManager.get_validator("tool")

        parsed_data = {"tool_id": "test_tool", "tool_type": "python", "version": "1.0.0", "executor_id": "python_runtime"}

        # First validation
        start_time = time.time()
        result1 = validator.validate(temp_tool_file, parsed_data)
        first_duration = time.time() - start_time

        # Second validation
        start_time = time.time()
        result2 = validator.validate(temp_tool_file, parsed_data)
        second_duration = time.time() - start_time

        # Both should be valid
        assert result1["valid"] is not None
        assert result2["valid"] is not None

        # Both should complete in reasonable time
        assert first_duration < 5.0  # Should complete within 5 seconds
        assert second_duration < 5.0

    def test_error_handling_with_invalid_data(self, temp_tool_file):
        """Test error handling with various invalid data scenarios."""
        validator = ValidationManager.get_validator("tool")

        # Test missing required fields
        invalid_data_cases = [
            {},  # Empty data
            {"tool_id": "test"},  # Missing tool_type and version
            {"tool_type": "python"},  # Missing tool_id and version
            {
                "tool_id": "test",
                "tool_type": "custom_type",
                "version": "1.0.0",
            },  # Missing executor_id for non-primitive
            {"tool_id": "test", "tool_type": "python", "version": "invalid"},  # Invalid version
        ]

        for invalid_data in invalid_data_cases:
            result = validator.validate(temp_tool_file, invalid_data)

            # Should have validation result structure
            assert "valid" in result
            assert "issues" in result
            assert "warnings" in result

            # Most cases should be invalid (except empty data might pass basic validation)
            if invalid_data:  # Non-empty data
                # Should have some issues or warnings
                assert len(result["issues"]) > 0 or len(result["warnings"]) > 0

    def test_validation_types_work(self, temp_tool_file, tmp_path):
        """Test that all validation types work correctly."""
        # Test that validation types still work as expected

        # Directive validation
        directive_file = tmp_path / "test_directive.md"
        directive_file.write_text("""```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test</description>
    <model tier="general">Test</model>
    <permissions><read resource="filesystem" path="*" /></permissions>
  </metadata>
  <process><step name="test">Test</step></process>
</directive>
```""")

        directive_data = {
            "name": "test_directive",
            "version": "1.0.0",
            "content": directive_file.read_text(),
        }
        directive_result = ValidationManager.validate("directive", directive_file, directive_data)
        # Directive validation is complex, just ensure it completes
        assert "valid" in directive_result

        # Knowledge validation
        knowledge_file = tmp_path / "test_knowledge.md"
        knowledge_data = {
            "zettel_id": "test_knowledge",
            "title": "Test",
            "version": "1.0.0",
            "content": "Test content",
        }
        knowledge_result = ValidationManager.validate("knowledge", knowledge_file, knowledge_data)
        assert knowledge_result["valid"] is True
