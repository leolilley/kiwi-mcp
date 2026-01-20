"""
Comprehensive tests for ValidationManager and all validators.

Tests filename matching, metadata validation, and validation pipeline
for directives, scripts, and knowledge entries.
"""

import pytest
from pathlib import Path

from kiwi_mcp.utils.validators import (
    BaseValidator,
    DirectiveValidator,
    ScriptValidator,
    KnowledgeValidator,
    ValidationManager,
)


class TestDirectiveValidator:
    """Test DirectiveValidator methods."""

    @pytest.fixture
    def validator(self):
        """Create DirectiveValidator instance."""
        return DirectiveValidator()

    @pytest.fixture
    def sample_directive_data(self):
        """Sample directive parsed data."""
        return {
            "name": "test_directive",
            "version": "1.0.0",
            "description": "Test directive",
            "permissions": [
                {"tag": "allow", "attrs": {"type": "read", "scope": "all"}}
            ],
            "model": {
                "tier": "reasoning",
                "fallback": "fast",
                "parallel": "false",
            },
        }

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_success(self, validator, tmp_path, sample_directive_data):
        """Should pass when filename matches directive name."""
        file_path = tmp_path / "test_directive.md"

        result = validator.validate_filename_match(file_path, sample_directive_data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_mismatch(self, validator, tmp_path, sample_directive_data):
        """Should fail when filename doesn't match directive name."""
        file_path = tmp_path / "wrong_name.md"

        result = validator.validate_filename_match(file_path, sample_directive_data)

        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert "mismatch" in result["issues"][0].lower()
        assert "error_details" in result

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_missing_name(self, validator, tmp_path):
        """Should fail when directive name is missing."""
        file_path = tmp_path / "test_directive.md"
        parsed_data = {"version": "1.0.0"}  # Missing name

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is False
        assert "name not found" in result["issues"][0].lower()

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_success(self, validator, sample_directive_data):
        """Should pass when metadata is valid."""
        # Add valid content with proper closing tag
        data = sample_directive_data.copy()
        data["content"] = """# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <permissions>
      <allow type="read" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
</directive>
```
"""
        result = validator.validate_metadata(data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_missing_closing_tag(self, validator, sample_directive_data):
        """Should fail when XML doesn't end with </directive> tag."""
        # Content with XML that doesn't end with </directive>
        data = sample_directive_data.copy()
        data["content"] = """# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <permissions>
      <allow type="read" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
</directive>
<!-- extra content after closing tag -->
```
"""
        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("must end with </directive>" in issue for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_closing_tag_with_whitespace(self, validator, sample_directive_data):
        """Should pass when XML ends with </directive> even with trailing whitespace."""
        # Content with XML ending with </directive> but with whitespace
        data = sample_directive_data.copy()
        data["content"] = """# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <permissions>
      <allow type="read" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
</directive>   
```
"""
        result = validator.validate_metadata(data)

        # Should pass - whitespace is stripped before checking
        assert result["valid"] is True

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_no_xml_content(self, validator, sample_directive_data):
        """Should fail when content doesn't contain valid XML."""
        # Content without XML directive
        data = sample_directive_data.copy()
        data["content"] = """# Test Directive

Just markdown, no XML here.
"""
        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("could not extract" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_content_after_code_block(self, validator, sample_directive_data):
        """Should fail when there's XML-like content after the closing code block."""
        # Content with valid XML but extra content after closing ```
        data = sample_directive_data.copy()
        data["content"] = """# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <permissions>
      <allow type="read" />
    </permissions>
    <model tier="reasoning" />
  </metadata>
</directive>
```</content>
<parameter name="filePath">/some/path</parameter>
"""
        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("unexpected content after code block" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_missing_permissions(self, validator, sample_directive_data):
        """Should fail when permissions are missing."""
        data = sample_directive_data.copy()
        data["permissions"] = []

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("permission" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_invalid_permission_format(self, validator, sample_directive_data):
        """Should fail when permission format is invalid."""
        data = sample_directive_data.copy()
        data["permissions"] = ["not a dict"]

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("invalid permission format" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_permission_missing_tag(self, validator, sample_directive_data):
        """Should fail when permission missing tag field."""
        data = sample_directive_data.copy()
        data["permissions"] = [{"attrs": {"type": "read"}}]  # Missing tag

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("tag" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_permission_missing_attrs(self, validator, sample_directive_data):
        """Should fail when permission missing attrs."""
        data = sample_directive_data.copy()
        data["permissions"] = [{"tag": "allow"}]  # Missing attrs

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("attribute" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_missing_model(self, validator, sample_directive_data):
        """Should fail when model is missing."""
        data = sample_directive_data.copy()
        data.pop("model", None)
        data.pop("model_class", None)

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("model" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_missing_tier(self, validator, sample_directive_data):
        """Should fail when model tier is missing."""
        data = sample_directive_data.copy()
        data["model"] = {"fallback": "fast"}  # Missing tier

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("tier" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_empty_tier(self, validator, sample_directive_data):
        """Should fail when model tier is empty."""
        data = sample_directive_data.copy()
        data["model"] = {"tier": ""}  # Empty tier

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("tier" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_invalid_parallel(self, validator, sample_directive_data):
        """Should fail when model parallel is invalid."""
        data = sample_directive_data.copy()
        data["model"] = {"tier": "reasoning", "parallel": "maybe"}  # Invalid

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("parallel" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_valid_parallel(self, validator, sample_directive_data):
        """Should pass when model parallel is valid."""
        data = sample_directive_data.copy()
        data["model"] = {"tier": "reasoning", "parallel": "true"}

        result = validator.validate_metadata(data)

        assert result["valid"] is True

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_invalid_fallback(self, validator, sample_directive_data):
        """Should fail when model fallback is invalid (non-string or whitespace-only)."""
        data = sample_directive_data.copy()
        data["model"] = {"tier": "reasoning", "fallback": "   "}  # Whitespace only

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("fallback" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_empty_string_fallback_allowed(self, validator, sample_directive_data):
        """Should allow empty string fallback (treated as omitted)."""
        data = sample_directive_data.copy()
        data["model"] = {"tier": "reasoning", "fallback": ""}  # Empty string is allowed

        result = validator.validate_metadata(data)

        # Empty string is falsy, so it's treated as omitted - should be valid
        assert result["valid"] is True

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_invalid_id(self, validator, sample_directive_data):
        """Should fail when model id is invalid (non-string or whitespace-only)."""
        data = sample_directive_data.copy()
        data["model"] = {"tier": "reasoning", "id": "   "}  # Whitespace only

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("id" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_model_empty_string_id_allowed(self, validator, sample_directive_data):
        """Should allow empty string id (treated as omitted)."""
        data = sample_directive_data.copy()
        data["model"] = {"tier": "reasoning", "id": ""}  # Empty string is allowed

        result = validator.validate_metadata(data)

        # Empty string is falsy, so it's treated as omitted - should be valid
        assert result["valid"] is True

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_legacy_warning(self, validator, sample_directive_data):
        """Should include warning for legacy model_class."""
        data = sample_directive_data.copy()
        data["model_class"] = data.pop("model")
        data["legacy_warning"] = {"message": "Legacy tag detected"}

        result = validator.validate_metadata(data)

        # Should still be valid but have warning
        assert result["valid"] is True
        assert len(result["warnings"]) > 0

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_combines_filename_and_metadata(self, validator, tmp_path, sample_directive_data):
        """Should combine filename and metadata validation results."""
        file_path = tmp_path / "test_directive.md"

        result = validator.validate(file_path, sample_directive_data)

        assert result["valid"] is True
        assert "issues" in result
        assert "warnings" in result

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_aggregates_all_issues(self, validator, tmp_path):
        """Should aggregate all validation issues."""
        file_path = tmp_path / "wrong_name.md"
        data = {
            "name": "test_directive",
            "permissions": [],
            "model": None,
        }

        result = validator.validate(file_path, data)

        assert result["valid"] is False
        assert len(result["issues"]) >= 2  # Filename mismatch + missing permissions + missing model


class TestScriptValidator:
    """Test ScriptValidator methods."""

    @pytest.fixture
    def validator(self):
        """Create ScriptValidator instance."""
        return ScriptValidator()

    @pytest.fixture
    def sample_script_data(self):
        """Sample script parsed data."""
        return {
            "name": "test_script",
            "description": "Test script",
            "category": "utility",
            "dependencies": [],
        }

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_success(self, validator, tmp_path, sample_script_data):
        """Should pass when filename matches script name."""
        file_path = tmp_path / "test_script.py"

        result = validator.validate_filename_match(file_path, sample_script_data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_mismatch(self, validator, tmp_path, sample_script_data):
        """Should fail when filename doesn't match script name."""
        file_path = tmp_path / "wrong_name.py"

        result = validator.validate_filename_match(file_path, sample_script_data)

        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert "mismatch" in result["issues"][0].lower()

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_missing_name(self, validator, tmp_path):
        """Should fail when script name is missing."""
        file_path = tmp_path / "test_script.py"
        parsed_data = {"description": "Test"}  # Missing name

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is False
        assert "name not found" in result["issues"][0].lower()

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_success(self, validator, sample_script_data):
        """Should pass when metadata is valid."""
        result = validator.validate_metadata(sample_script_data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_missing_name(self, validator):
        """Should fail when script name is missing."""
        data = {"description": "Test"}

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("name" in issue.lower() for issue in result["issues"])


class TestKnowledgeValidator:
    """Test KnowledgeValidator methods."""

    @pytest.fixture
    def validator(self):
        """Create KnowledgeValidator instance."""
        return KnowledgeValidator()

    @pytest.fixture
    def sample_knowledge_data(self):
        """Sample knowledge parsed data."""
        return {
            "zettel_id": "001-test",
            "title": "Test Entry",
            "content": "Test content",
            "entry_type": "learning",
            "category": "test",
            "tags": [],
        }

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_success(self, validator, tmp_path, sample_knowledge_data):
        """Should pass when filename matches zettel_id."""
        file_path = tmp_path / "001-test.md"

        result = validator.validate_filename_match(file_path, sample_knowledge_data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_mismatch(self, validator, tmp_path, sample_knowledge_data):
        """Should fail when filename doesn't match zettel_id."""
        file_path = tmp_path / "wrong_id.md"

        result = validator.validate_filename_match(file_path, sample_knowledge_data)

        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert "mismatch" in result["issues"][0].lower()

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_filename_match_missing_zettel_id(self, validator, tmp_path):
        """Should fail when zettel_id is missing."""
        file_path = tmp_path / "001-test.md"
        parsed_data = {}  # Missing zettel_id

        result = validator.validate_filename_match(file_path, parsed_data)

        assert result["valid"] is False
        assert "zettel" in result["issues"][0].lower() and "not found" in result["issues"][0].lower()

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_success(self, validator, sample_knowledge_data):
        """Should pass when metadata is valid."""
        result = validator.validate_metadata(sample_knowledge_data)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_missing_zettel_id(self, validator):
        """Should fail when zettel_id is missing."""
        data = {
            "title": "Test Entry",
            "content": "Test content",
        }  # Missing zettel_id

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("zettel" in issue.lower() and "required" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_missing_title(self, validator, sample_knowledge_data):
        """Should fail when title is missing."""
        data = sample_knowledge_data.copy()
        data.pop("title")

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("title" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_metadata_missing_content(self, validator, sample_knowledge_data):
        """Should fail when content is missing."""
        data = sample_knowledge_data.copy()
        data.pop("content")

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("content" in issue.lower() for issue in result["issues"])


class TestValidationManager:
    """Test ValidationManager class methods."""

    @pytest.mark.unit
    @pytest.mark.validation
    def test_get_validator_for_directive(self):
        """Should return DirectiveValidator for directive type."""
        validator = ValidationManager.get_validator("directive")

        assert isinstance(validator, DirectiveValidator)

    @pytest.mark.unit
    @pytest.mark.validation
    def test_get_validator_for_script(self):
        """Should return ScriptValidator for script type."""
        validator = ValidationManager.get_validator("script")

        assert isinstance(validator, ScriptValidator)

    @pytest.mark.unit
    @pytest.mark.validation
    def test_get_validator_for_knowledge(self):
        """Should return KnowledgeValidator for knowledge type."""
        validator = ValidationManager.get_validator("knowledge")

        assert isinstance(validator, KnowledgeValidator)

    @pytest.mark.unit
    @pytest.mark.validation
    def test_get_validator_invalid_type(self):
        """Should raise ValueError for unknown item type."""
        with pytest.raises(ValueError, match="Unknown item_type"):
            ValidationManager.get_validator("invalid")

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_directive(self, sample_directive_file):
        """Should validate directive using appropriate validator."""
        from kiwi_mcp.utils.parsers import parse_directive_file

        parsed_data = parse_directive_file(sample_directive_file)
        result = ValidationManager.validate("directive", sample_directive_file, parsed_data)

        assert "valid" in result
        assert "issues" in result
        assert "warnings" in result

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_script(self, sample_script_file):
        """Should validate script using appropriate validator."""
        from kiwi_mcp.utils.parsers import parse_script_metadata

        parsed_data = parse_script_metadata(sample_script_file)
        result = ValidationManager.validate("script", sample_script_file, parsed_data)

        assert "valid" in result
        assert "issues" in result
        assert "warnings" in result

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_knowledge(self, sample_knowledge_file):
        """Should validate knowledge using appropriate validator."""
        from kiwi_mcp.utils.parsers import parse_knowledge_entry

        parsed_data = parse_knowledge_entry(sample_knowledge_file)
        result = ValidationManager.validate("knowledge", sample_knowledge_file, parsed_data)

        assert "valid" in result
        assert "issues" in result
        assert "warnings" in result


class TestValidationEdgeCases:
    """Test edge cases and error handling in validators."""

    @pytest.mark.unit
    @pytest.mark.validation
    def test_directive_validator_with_none_permissions(self, tmp_path):
        """Should handle None permissions gracefully."""
        validator = DirectiveValidator()
        file_path = tmp_path / "test.md"
        data = {"name": "test", "permissions": None, "model": {"tier": "reasoning"}}

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("permission" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_directive_validator_with_empty_string_tier(self, tmp_path):
        """Should fail validation for empty string tier."""
        validator = DirectiveValidator()
        file_path = tmp_path / "test.md"
        data = {"name": "test", "permissions": [{"tag": "allow", "attrs": {"type": "read"}}], "model": {"tier": "   "}}  # Whitespace only

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("tier" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_script_validator_with_empty_name(self, tmp_path):
        """Should fail validation for empty script name."""
        validator = ScriptValidator()
        file_path = tmp_path / "test.py"
        data = {"name": ""}

        result = validator.validate_metadata(data)

        assert result["valid"] is False

    @pytest.mark.unit
    @pytest.mark.validation
    def test_knowledge_validator_with_empty_content(self, tmp_path):
        """Should fail validation for empty knowledge content."""
        validator = KnowledgeValidator()
        file_path = tmp_path / "001-test.md"
        data = {"zettel_id": "001-test", "title": "Test", "content": ""}

        result = validator.validate_metadata(data)

        assert result["valid"] is False
        assert any("content" in issue.lower() for issue in result["issues"])

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validation_manager_with_invalid_file_path(self):
        """Should handle invalid file path gracefully."""
        from pathlib import Path

        invalid_path = Path("/nonexistent/path/file.md")
        data = {"name": "test"}

        # Should not raise exception, just validate based on data
        result = ValidationManager.validate("directive", invalid_path, data)

        assert "valid" in result
