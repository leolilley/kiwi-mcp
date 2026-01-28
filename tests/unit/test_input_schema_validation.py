"""
Tests for directive input schema and knowledge frontmatter schema validation.

These tests verify the Phase 3 validation schema features:
1. Directive input_schema extraction and validation
2. Knowledge frontmatter_schema extraction and validation
3. Auto-generation of schemas from input specifications
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestDirectiveInputSchemaValidation:
    """Tests for directive input schema validation."""

    def test_build_input_schema_from_spec_basic(self):
        """Test building a schema from basic input specifications."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        
        handler = Mock(spec=DirectiveHandler)
        handler._build_input_schema_from_spec = DirectiveHandler._build_input_schema_from_spec
        
        inputs_spec = [
            {"name": "topic", "type": "string", "required": True, "description": "Topic to research"},
            {"name": "depth", "type": "string", "required": False, "description": "Search depth"},
        ]
        
        schema = handler._build_input_schema_from_spec(handler, inputs_spec)
        
        assert schema["type"] == "object"
        assert "topic" in schema["properties"]
        assert "depth" in schema["properties"]
        assert schema["properties"]["topic"]["type"] == "string"
        assert schema["required"] == ["topic"]

    def test_build_input_schema_from_spec_type_mapping(self):
        """Test that directive types map correctly to JSON Schema types."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        
        handler = Mock(spec=DirectiveHandler)
        handler._build_input_schema_from_spec = DirectiveHandler._build_input_schema_from_spec
        
        inputs_spec = [
            {"name": "str_field", "type": "string", "required": False},
            {"name": "num_field", "type": "number", "required": False},
            {"name": "int_field", "type": "integer", "required": False},
            {"name": "bool_field", "type": "boolean", "required": False},
            {"name": "arr_field", "type": "array", "required": False},
            {"name": "obj_field", "type": "object", "required": False},
        ]
        
        schema = handler._build_input_schema_from_spec(handler, inputs_spec)
        
        assert schema["properties"]["str_field"]["type"] == "string"
        assert schema["properties"]["num_field"]["type"] == "number"
        assert schema["properties"]["int_field"]["type"] == "integer"
        assert schema["properties"]["bool_field"]["type"] == "boolean"
        assert schema["properties"]["arr_field"]["type"] == "array"
        assert schema["properties"]["obj_field"]["type"] == "object"

    def test_build_input_schema_from_spec_empty(self):
        """Test building schema from empty input spec."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        
        handler = Mock(spec=DirectiveHandler)
        handler._build_input_schema_from_spec = DirectiveHandler._build_input_schema_from_spec
        
        schema = handler._build_input_schema_from_spec(handler, [])
        
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert "required" not in schema

    def test_build_input_schema_from_spec_all_required(self):
        """Test that all required fields are captured."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        
        handler = Mock(spec=DirectiveHandler)
        handler._build_input_schema_from_spec = DirectiveHandler._build_input_schema_from_spec
        
        inputs_spec = [
            {"name": "a", "type": "string", "required": True},
            {"name": "b", "type": "string", "required": True},
            {"name": "c", "type": "string", "required": False},
        ]
        
        schema = handler._build_input_schema_from_spec(handler, inputs_spec)
        
        assert set(schema["required"]) == {"a", "b"}

    def test_validate_inputs_with_schema_valid(self):
        """Test validation with valid inputs."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        from kiwi_mcp.utils.schema_validator import SchemaValidator
        
        handler = Mock(spec=DirectiveHandler)
        handler._schema_validator = SchemaValidator()
        handler._validate_inputs_with_schema = DirectiveHandler._validate_inputs_with_schema
        
        schema = {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "minLength": 3},
            },
            "required": ["topic"],
        }
        
        params = {"topic": "AI research"}
        
        result = handler._validate_inputs_with_schema(handler, params, schema)
        
        assert result["valid"] is True
        assert result["issues"] == []

    def test_validate_inputs_with_schema_invalid_missing_required(self):
        """Test validation fails for missing required field."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        from kiwi_mcp.utils.schema_validator import SchemaValidator
        
        handler = Mock(spec=DirectiveHandler)
        handler._schema_validator = SchemaValidator()
        handler._validate_inputs_with_schema = DirectiveHandler._validate_inputs_with_schema
        
        schema = {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
            },
            "required": ["topic"],
        }
        
        params = {"other": "value"}  # Missing 'topic'
        
        result = handler._validate_inputs_with_schema(handler, params, schema)
        
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_inputs_with_schema_invalid_type(self):
        """Test validation fails for wrong type."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        from kiwi_mcp.utils.schema_validator import SchemaValidator
        
        handler = Mock(spec=DirectiveHandler)
        handler._schema_validator = SchemaValidator()
        handler._validate_inputs_with_schema = DirectiveHandler._validate_inputs_with_schema
        
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
        }
        
        params = {"count": "not an integer"}
        
        result = handler._validate_inputs_with_schema(handler, params, schema)
        
        assert result["valid"] is False

    def test_extract_input_schema_from_element(self):
        """Test extracting input schema from parsed XML."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        
        handler = Mock(spec=DirectiveHandler)
        handler.logger = Mock()
        handler._extract_input_schema = DirectiveHandler._extract_input_schema
        
        # Simulate parsed XML with schema element
        parsed = {
            "inputs": {
                "input": [{"_attrs": {"name": "topic"}}],
                "schema": {"_text": '{"type": "object", "properties": {"topic": {"minLength": 5}}}'}
            }
        }
        
        schema = handler._extract_input_schema(handler, parsed)
        
        assert schema is not None
        assert schema["type"] == "object"
        assert "topic" in schema["properties"]
        assert schema["properties"]["topic"]["minLength"] == 5

    def test_extract_input_schema_none_when_missing(self):
        """Test that None is returned when no schema is defined."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler
        
        handler = Mock(spec=DirectiveHandler)
        handler.logger = Mock()
        handler._extract_input_schema = DirectiveHandler._extract_input_schema
        
        parsed = {
            "inputs": {
                "input": [{"_attrs": {"name": "topic"}}]
            }
        }
        
        schema = handler._extract_input_schema(handler, parsed)
        
        assert schema is None


class TestKnowledgeFrontmatterSchemaValidation:
    """Tests for knowledge frontmatter schema validation."""

    def test_build_base_frontmatter_schema(self):
        """Test building base frontmatter schema."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
        
        handler = Mock(spec=KnowledgeHandler)
        handler._build_base_frontmatter_schema = KnowledgeHandler._build_base_frontmatter_schema
        
        schema = handler._build_base_frontmatter_schema(handler)
        
        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "title" in schema["properties"]
        assert "entry_type" in schema["properties"]
        assert set(schema["required"]) == {"id", "title"}

    def test_build_base_frontmatter_schema_entry_type_string(self):
        """Test that entry_type is a flexible string field (no enum constraint)."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
        
        handler = Mock(spec=KnowledgeHandler)
        handler._build_base_frontmatter_schema = KnowledgeHandler._build_base_frontmatter_schema
        
        schema = handler._build_base_frontmatter_schema(handler)
        
        entry_type_schema = schema["properties"]["entry_type"]
        assert entry_type_schema["type"] == "string"
        # No enum constraint - entry_type is flexible
        assert "enum" not in entry_type_schema

    def test_validate_frontmatter_with_schema_valid(self):
        """Test validation with valid frontmatter."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
        from kiwi_mcp.utils.schema_validator import SchemaValidator
        
        # Use a SimpleNamespace as a mock that can have methods bound
        class MockHandler:
            def __init__(self):
                self._schema_validator = SchemaValidator()
            
            _build_base_frontmatter_schema = KnowledgeHandler._build_base_frontmatter_schema
            _validate_frontmatter_with_schema = KnowledgeHandler._validate_frontmatter_with_schema
        
        handler = MockHandler()
        
        entry_data = {
            "id": "20260124-test",
            "title": "Test Entry",
            "entry_type": "pattern",
            "content": "Some content",
        }
        
        result = handler._validate_frontmatter_with_schema(entry_data, None)
        
        assert result["valid"] is True

    def test_validate_frontmatter_with_schema_missing_title(self):
        """Test validation fails for missing required title."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
        from kiwi_mcp.utils.schema_validator import SchemaValidator
        
        class MockHandler:
            def __init__(self):
                self._schema_validator = SchemaValidator()
            
            _build_base_frontmatter_schema = KnowledgeHandler._build_base_frontmatter_schema
            _validate_frontmatter_with_schema = KnowledgeHandler._validate_frontmatter_with_schema
        
        handler = MockHandler()
        
        entry_data = {
            "id": "20260124-test",
            # Missing "title"
            "entry_type": "pattern",
            "content": "Some content",
        }
        
        result = handler._validate_frontmatter_with_schema(entry_data, None)
        
        assert result["valid"] is False
        assert any("title" in issue for issue in result["issues"])

    def test_validate_frontmatter_with_custom_schema(self):
        """Test validation with custom schema merged."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
        from kiwi_mcp.utils.schema_validator import SchemaValidator
        
        class MockHandler:
            def __init__(self):
                self._schema_validator = SchemaValidator()
            
            _build_base_frontmatter_schema = KnowledgeHandler._build_base_frontmatter_schema
            _validate_frontmatter_with_schema = KnowledgeHandler._validate_frontmatter_with_schema
        
        handler = MockHandler()
        
        entry_data = {
            "id": "20260124-test",
            "title": "Test Entry",
            "custom_field": "ab",  # Too short
            "content": "Some content",
        }
        
        custom_schema = {
            "properties": {
                "custom_field": {"type": "string", "minLength": 5}
            },
            "required": ["custom_field"]
        }
        
        result = handler._validate_frontmatter_with_schema(entry_data, custom_schema)
        
        assert result["valid"] is False

    def test_extract_frontmatter_schema(self):
        """Test extracting schema from entry data."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
        
        handler = Mock(spec=KnowledgeHandler)
        handler._extract_frontmatter_schema = KnowledgeHandler._extract_frontmatter_schema
        
        entry_data = {
            "id": "test",
            "title": "Test",
            "schema": {
                "properties": {
                    "custom": {"type": "string"}
                }
            }
        }
        
        schema = handler._extract_frontmatter_schema(handler, entry_data)
        
        assert schema is not None
        assert "custom" in schema["properties"]

    def test_extract_frontmatter_schema_none_when_missing(self):
        """Test None returned when no schema in entry."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler
        
        handler = Mock(spec=KnowledgeHandler)
        handler._extract_frontmatter_schema = KnowledgeHandler._extract_frontmatter_schema
        
        entry_data = {
            "id": "test",
            "title": "Test",
        }
        
        schema = handler._extract_frontmatter_schema(handler, entry_data)
        
        assert schema is None
