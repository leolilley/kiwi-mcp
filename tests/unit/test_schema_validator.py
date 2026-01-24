"""
Tests for SchemaValidator

Tests the JSON Schema validation engine.
"""

import pytest
from unittest.mock import Mock, patch
from kiwi_mcp.utils.schema_validator import SchemaValidator


class TestSchemaValidator:
    """Test SchemaValidator class."""

    @pytest.fixture
    def validator(self):
        """Create SchemaValidator instance."""
        return SchemaValidator()

    def test_init_without_jsonschema(self, validator):
        """Test initialization when jsonschema is not available."""
        with patch.object(validator, "_jsonschema_available", False):
            result = validator.validate({"test": "data"}, {"type": "object"})

            assert result["valid"] is True
            assert len(result["warnings"]) > 0
            assert "JSON Schema validation not available" in result["warnings"][0]

    @patch("builtins.__import__")
    def test_init_with_jsonschema(self, mock_import):
        """Test initialization when jsonschema is available."""
        mock_jsonschema = Mock()
        mock_jsonschema.Draft7Validator = Mock()
        mock_jsonschema.Draft202012Validator = Mock()
        
        def import_side_effect(name, *args, **kwargs):
            if name == "jsonschema":
                return mock_jsonschema
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect

        validator = SchemaValidator()

        assert validator._jsonschema_available is True
        assert validator._jsonschema is mock_jsonschema

    def test_is_available_false(self, validator):
        """Test is_available returns False when jsonschema not available."""
        validator._jsonschema_available = False
        assert validator.is_available() is False

    def test_is_available_true(self, validator):
        """Test is_available returns True when jsonschema available."""
        validator._jsonschema_available = True
        assert validator.is_available() is True

    @patch("builtins.__import__")
    def test_validate_valid_data(self, mock_import, validator):
        """Test validation with valid data."""
        # Mock jsonschema components
        mock_jsonschema = Mock()
        mock_validator_instance = Mock()
        mock_validator_instance.iter_errors.return_value = []  # No errors
        mock_jsonschema.Draft7Validator.return_value = mock_validator_instance
        mock_jsonschema.Draft7Validator.check_schema = Mock()
        
        def import_side_effect(name, *args, **kwargs):
            if name == "jsonschema":
                return mock_jsonschema
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect

        validator._jsonschema = mock_jsonschema
        validator._jsonschema_available = True
        validator._Draft7Validator = mock_jsonschema.Draft7Validator

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        data = {"name": "test"}

        result = validator.validate(data, schema)

        assert result["valid"] is True
        assert result["issues"] == []
        assert result["warnings"] == []

    @patch("builtins.__import__")
    def test_validate_invalid_data(self, mock_import, validator):
        """Test validation with invalid data."""
        # Mock validation error
        mock_jsonschema = Mock()
        mock_error = Mock()
        mock_error.message = "Test error message"
        mock_error.validator = "type"
        mock_error.validator_value = "string"
        mock_error.instance = 123
        mock_error.absolute_path = ["name"]

        mock_validator_instance = Mock()
        mock_validator_instance.iter_errors.return_value = [mock_error]
        mock_jsonschema.Draft7Validator.return_value = mock_validator_instance
        mock_jsonschema.Draft7Validator.check_schema = Mock()
        
        def import_side_effect(name, *args, **kwargs):
            if name == "jsonschema":
                return mock_jsonschema
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect

        validator._jsonschema = mock_jsonschema
        validator._jsonschema_available = True
        validator._Draft7Validator = mock_jsonschema.Draft7Validator

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        data = {"name": 123}  # Invalid: should be string

        result = validator.validate(data, schema)

        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert "name" in result["issues"][0]

    @patch("builtins.__import__")
    def test_validate_invalid_schema(self, mock_import, validator):
        """Test validation with invalid schema."""
        # Mock schema error
        mock_jsonschema = Mock()
        schema_error = Mock()
        schema_error.message = "Invalid schema"
        mock_jsonschema.Draft7Validator.check_schema.side_effect = Exception("Invalid schema")
        mock_jsonschema.SchemaError = Exception  # Mock the exception class
        
        def import_side_effect(name, *args, **kwargs):
            if name == "jsonschema":
                return mock_jsonschema
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect

        validator._jsonschema = mock_jsonschema
        validator._jsonschema_available = True
        validator._Draft7Validator = mock_jsonschema.Draft7Validator

        schema = {"type": "invalid_type"}  # Invalid schema
        data = {"name": "test"}

        result = validator.validate(data, schema)

        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert "Invalid schema" in result["issues"][0]

    def test_format_error_type_error(self, validator):
        """Test error formatting for type errors."""
        mock_error = Mock()
        mock_error.message = "Test message"
        mock_error.validator = "type"
        mock_error.validator_value = "string"
        mock_error.instance = 123
        mock_error.absolute_path = ["name"]

        formatted = validator._format_error(mock_error)

        assert "name" in formatted
        assert "Expected type 'string'" in formatted
        assert "got 'int'" in formatted

    def test_format_error_required_error(self, validator):
        """Test error formatting for required field errors."""
        mock_error = Mock()
        mock_error.message = "Test message"
        mock_error.validator = "required"
        mock_error.validator_value = ["name", "email"]
        mock_error.instance = {}
        mock_error.absolute_path = []

        formatted = validator._format_error(mock_error)

        assert "Missing required properties" in formatted
        assert "'name'" in formatted
        assert "'email'" in formatted

    def test_format_error_enum_error(self, validator):
        """Test error formatting for enum errors."""
        mock_error = Mock()
        mock_error.message = "Test message"
        mock_error.validator = "enum"
        mock_error.validator_value = ["option1", "option2"]
        mock_error.instance = "invalid"
        mock_error.absolute_path = ["choice"]

        formatted = validator._format_error(mock_error)

        assert "choice" in formatted
        assert "Value must be one of" in formatted
        assert "option1" in formatted
        assert "option2" in formatted

    def test_format_error_pattern_error(self, validator):
        """Test error formatting for pattern errors."""
        mock_error = Mock()
        mock_error.message = "Test message"
        mock_error.validator = "pattern"
        mock_error.validator_value = "^[a-z]+$"
        mock_error.instance = "Invalid123"
        mock_error.absolute_path = ["field"]

        formatted = validator._format_error(mock_error)

        assert "field" in formatted
        assert "does not match pattern" in formatted
        assert "^[a-z]+$" in formatted

    def test_format_error_length_errors(self, validator):
        """Test error formatting for length errors."""
        # Test minLength
        mock_error = Mock()
        mock_error.message = "Test message"
        mock_error.validator = "minLength"
        mock_error.validator_value = 5
        mock_error.instance = "abc"
        mock_error.absolute_path = ["text"]

        formatted = validator._format_error(mock_error)

        assert "text" in formatted
        assert "String too short" in formatted
        assert "minimum 5" in formatted
        assert "got 3" in formatted

        # Test maxLength
        mock_error.validator = "maxLength"
        mock_error.validator_value = 3
        mock_error.instance = "abcdef"

        formatted = validator._format_error(mock_error)

        assert "String too long" in formatted
        assert "maximum 3" in formatted
        assert "got 6" in formatted

    def test_format_error_nested_path(self, validator):
        """Test error formatting with nested paths."""
        mock_error = Mock()
        mock_error.message = "Test message"
        mock_error.validator = "type"
        mock_error.validator_value = "string"
        mock_error.instance = 123
        mock_error.absolute_path = ["user", "profile", "name"]

        formatted = validator._format_error(mock_error)

        assert "user.profile.name" in formatted
        assert "Expected type 'string'" in formatted

    def test_format_error_array_index(self, validator):
        """Test error formatting with array indices."""
        mock_error = Mock()
        mock_error.message = "Test message"
        mock_error.validator = "type"
        mock_error.validator_value = "string"
        mock_error.instance = 123
        mock_error.absolute_path = ["items", 0, "name"]

        formatted = validator._format_error(mock_error)

        assert "items[0].name" in formatted
        assert "Expected type 'string'" in formatted

    def test_format_error_fallback(self, validator):
        """Test error formatting fallback for exceptions."""
        mock_error = Mock()
        mock_error.message = "Original message"
        # Create a mock that raises when iterated
        mock_path = Mock()
        def iter_side_effect():
            raise Exception("Path error")
        mock_path.__iter__ = iter_side_effect
        mock_error.absolute_path = mock_path

        formatted = validator._format_error(mock_error)

        assert formatted == "Original message"

    @patch("kiwi_mcp.utils.schema_validator.json.dumps")
    def test_get_validator_caching(self, mock_dumps, validator):
        """Test validator caching functionality."""
        mock_dumps.return_value = "schema_key"

        # Mock jsonschema
        mock_validator_instance = Mock()
        validator._jsonschema_available = True
        validator._Draft7Validator = Mock(return_value=mock_validator_instance)

        schema = {"type": "object"}

        # First call should create and cache validator
        result1 = validator._get_validator(schema)
        assert result1 is mock_validator_instance
        assert "schema_key" in validator._compiled_schemas

        # Second call should return cached validator
        result2 = validator._get_validator(schema)
        assert result2 is mock_validator_instance
        assert validator._Draft7Validator.call_count == 1  # Only called once

    def test_clear_cache(self, validator):
        """Test cache clearing."""
        validator._compiled_schemas["test"] = Mock()

        validator.clear_cache()

        assert len(validator._compiled_schemas) == 0

    def test_get_cache_stats(self, validator):
        """Test cache statistics."""
        validator._compiled_schemas["schema1"] = Mock()
        validator._compiled_schemas["schema2"] = Mock()
        validator._jsonschema_available = True

        stats = validator.get_cache_stats()

        assert stats["compiled_schemas"] == 2
        assert stats["jsonschema_available"] is True
