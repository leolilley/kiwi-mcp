"""
JSON Schema Validation Engine

Provides JSON Schema validation with custom error formatting and performance optimizations.
"""

import json
from typing import Any, Dict, List, Optional


class SchemaValidator:
    """JSON Schema validation engine with performance optimizations."""

    def __init__(self):
        """Initialize schema validator."""
        self._compiled_schemas: Dict[str, Any] = {}
        self._jsonschema_available = False

        # Try to import jsonschema
        try:
            import jsonschema
            from jsonschema import Draft7Validator, Draft202012Validator

            self._jsonschema = jsonschema
            self._Draft7Validator = Draft7Validator
            self._Draft202012Validator = Draft202012Validator
            self._jsonschema_available = True
        except ImportError:
            pass

    def validate(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against JSON Schema.

        Args:
            data: Data to validate
            schema: JSON Schema

        Returns:
            Validation result with issues and warnings
        """
        if not self._jsonschema_available:
            return {
                "valid": True,
                "issues": [],
                "warnings": [
                    "JSON Schema validation not available. "
                    "Install jsonschema package: pip install jsonschema"
                ],
            }

        try:
            # Validate the schema itself first
            schema_validation = self._validate_schema(schema)
            if not schema_validation["valid"]:
                return {
                    "valid": False,
                    "issues": [f"Invalid schema: {', '.join(schema_validation['issues'])}"],
                    "warnings": [],
                }

            # Get or create validator
            validator = self._get_validator(schema)

            # Validate data
            errors = list(validator.iter_errors(data))

            if not errors:
                return {"valid": True, "issues": [], "warnings": []}

            # Format errors
            issues = []
            for error in errors:
                formatted_error = self._format_error(error)
                issues.append(formatted_error)

            return {"valid": False, "issues": issues, "warnings": []}

        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Schema validation error: {str(e)}"],
                "warnings": [],
            }

    def _validate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the schema itself is valid JSON Schema.

        Args:
            schema: JSON Schema to validate

        Returns:
            Validation result
        """
        try:
            # Detect schema version
            schema_version = schema.get("$schema", "")

            if "draft-07" in schema_version or not schema_version:
                # Default to Draft 7
                self._jsonschema.Draft7Validator.check_schema(schema)
            elif "2020-12" in schema_version:
                self._jsonschema.Draft202012Validator.check_schema(schema)
            else:
                # Try Draft 7 as fallback
                self._jsonschema.Draft7Validator.check_schema(schema)

            return {"valid": True, "issues": []}

        except self._jsonschema.SchemaError as e:
            return {"valid": False, "issues": [f"Schema validation error: {str(e)}"]}
        except Exception as e:
            return {"valid": False, "issues": [f"Schema validation error: {str(e)}"]}

    def _get_validator(self, schema: Dict[str, Any]) -> Any:
        """
        Get or create a compiled validator for the schema.

        Args:
            schema: JSON Schema

        Returns:
            Compiled validator
        """
        # Create a cache key from schema
        schema_key = json.dumps(schema, sort_keys=True)

        if schema_key in self._compiled_schemas:
            return self._compiled_schemas[schema_key]

        # Detect schema version and create appropriate validator
        schema_version = schema.get("$schema", "")

        if "2020-12" in schema_version:
            validator = self._Draft202012Validator(schema)
        else:
            # Default to Draft 7
            validator = self._Draft7Validator(schema)

        # Cache the compiled validator
        self._compiled_schemas[schema_key] = validator

        return validator

    def _format_error(self, error: Any) -> str:
        """
        Format a JSON Schema validation error into a human-readable message.

        Args:
            error: ValidationError from jsonschema

        Returns:
            Formatted error message
        """
        try:
            # Get the path to the error
            path_parts = []
            for part in error.absolute_path:
                if isinstance(part, int):
                    path_parts.append(f"[{part}]")
                else:
                    if path_parts:
                        path_parts.append(f".{part}")
                    else:
                        path_parts.append(str(part))

            path_str = "".join(path_parts) if path_parts else "root"

            # Format the error message
            message = error.message

            # Add context for specific error types
            if error.validator == "required":
                missing_props = error.validator_value
                if isinstance(missing_props, list):
                    missing_str = ", ".join(f"'{prop}'" for prop in missing_props)
                    message = f"Missing required properties: {missing_str}"
            elif error.validator == "type":
                expected_type = error.validator_value
                actual_value = error.instance
                actual_type = type(actual_value).__name__
                message = f"Expected type '{expected_type}', got '{actual_type}'"
            elif error.validator == "enum":
                allowed_values = error.validator_value
                message = f"Value must be one of: {allowed_values}"
            elif error.validator == "pattern":
                pattern = error.validator_value
                message = f"Value does not match pattern: {pattern}"
            elif error.validator == "minLength":
                min_length = error.validator_value
                actual_length = len(error.instance) if error.instance else 0
                message = f"String too short (minimum {min_length}, got {actual_length})"
            elif error.validator == "maxLength":
                max_length = error.validator_value
                actual_length = len(error.instance) if error.instance else 0
                message = f"String too long (maximum {max_length}, got {actual_length})"

            # Combine path and message
            if path_str == "root":
                return message
            else:
                return f"At '{path_str}': {message}"

        except Exception:
            # Fallback to basic error message
            return str(error.message)

    def clear_cache(self) -> None:
        """Clear the compiled schema cache."""
        self._compiled_schemas.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "compiled_schemas": len(self._compiled_schemas),
            "jsonschema_available": self._jsonschema_available,
        }

    def is_available(self) -> bool:
        """Check if JSON Schema validation is available."""
        return self._jsonschema_available
