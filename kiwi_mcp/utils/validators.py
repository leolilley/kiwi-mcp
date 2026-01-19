"""
Unified Validation Pipeline

Provides consistent validation across directives, scripts, and knowledge entries.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseValidator(ABC):
    """Base validator for item-type-specific validation."""

    @abstractmethod
    def validate_filename_match(self, file_path: Path, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that filename matches item identifier."""

    @abstractmethod
    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate item-specific metadata."""

    def validate(self, file_path: Path, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all validations.
        
        Returns:
            {"valid": bool, "issues": List[str], "warnings": List[str]}
        """
        all_issues = []
        all_warnings = []

        # Validate filename match
        filename_result = self.validate_filename_match(file_path, parsed_data)
        if not filename_result.get("valid", True):
            all_issues.extend(filename_result.get("issues", []))
        if filename_result.get("warnings"):
            all_warnings.extend(filename_result.get("warnings", []))

        # Validate metadata
        metadata_result = self.validate_metadata(parsed_data)
        if not metadata_result.get("valid", True):
            all_issues.extend(metadata_result.get("issues", []))
        if metadata_result.get("warnings"):
            all_warnings.extend(metadata_result.get("warnings", []))

        return {
            "valid": len(all_issues) == 0,
            "issues": all_issues,
            "warnings": all_warnings,
        }


class DirectiveValidator(BaseValidator):
    """Validator for directives."""

    def validate_filename_match(self, file_path: Path, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate filename matches directive name."""
        directive_name = parsed_data.get("name")
        if not directive_name:
            return {
                "valid": False,
                "issues": ["Directive name not found in parsed data"],
            }

        expected_filename = f"{directive_name}.md"
        actual_filename = file_path.name

        if actual_filename != expected_filename:
            return {
                "valid": False,
                "issues": [
                    f"Filename mismatch: expected '{expected_filename}', got '{actual_filename}'"
                ],
                "error_details": {
                    "expected": expected_filename,
                    "actual": actual_filename,
                    "directive_name": directive_name,
                    "path": str(file_path),
                },
            }

        return {"valid": True, "issues": []}

    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate directive metadata (permissions and model)."""
        issues = []
        warnings = []

        # Validate permissions
        permissions = parsed_data.get("permissions", [])
        if not permissions:
            issues.append("No permissions defined in directive")
        else:
            for perm in permissions:
                if not isinstance(perm, dict):
                    issues.append(f"Invalid permission format: {perm}")
                    continue

                if "tag" not in perm:
                    issues.append("Permission missing 'tag' field")
                if not perm.get("attrs"):
                    issues.append(f"Permission '{perm.get('tag', 'unknown')}' missing attributes")

        # Validate model
        model_data = parsed_data.get("model") or parsed_data.get("model_class")
        if model_data is None:
            issues.append(
                "No <model> or <model_class> tag found in directive metadata. "
                "Add a <model> tag with required 'tier' attribute inside <metadata>."
            )
        else:
            # Check tier
            tier = model_data.get("tier")
            if tier is None or tier == "":
                issues.append(
                    "Model tag exists but is missing required 'tier' attribute. "
                    "Example: <model tier=\"reasoning\">...</model>"
                )
            elif not isinstance(tier, str) or not tier.strip():
                issues.append(f"Model 'tier' attribute must be a non-empty string, got: {repr(tier)}")

            # Check fallback
            fallback = model_data.get("fallback")
            if fallback and (not isinstance(fallback, str) or not fallback.strip()):
                issues.append("model fallback must be a non-empty string or omitted")

            # Check parallel
            parallel = model_data.get("parallel")
            if parallel and parallel not in ["true", "false"]:
                issues.append(f"model parallel '{parallel}' not valid. Must be 'true' or 'false'")

            # Check id
            model_id = model_data.get("id")
            if model_id and (not isinstance(model_id, str) or not model_id.strip()):
                issues.append("model id must be a non-empty string or omitted")

        # Check for legacy model_class warning
        if parsed_data.get("legacy_warning"):
            warnings.append(parsed_data["legacy_warning"].get("message", "Legacy model_class tag detected"))

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }


class ScriptValidator(BaseValidator):
    """Validator for scripts."""

    def validate_filename_match(self, file_path: Path, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate filename matches script name."""
        script_name = parsed_data.get("name")
        if not script_name:
            return {
                "valid": False,
                "issues": ["Script name not found in parsed data"],
            }

        expected_filename = f"{script_name}.py"
        actual_filename = file_path.name

        if actual_filename != expected_filename:
            return {
                "valid": False,
                "issues": [
                    f"Filename mismatch: expected '{expected_filename}', got '{actual_filename}'"
                ],
                "error_details": {
                    "expected": expected_filename,
                    "actual": actual_filename,
                    "script_name": script_name,
                    "path": str(file_path),
                },
            }

        return {"valid": True, "issues": []}

    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate script metadata."""
        issues = []
        warnings = []

        # Scripts have minimal required metadata - just name
        # Could add validation for dependencies, etc. in the future
        name = parsed_data.get("name")
        if not name:
            issues.append("Script name is required")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }


class KnowledgeValidator(BaseValidator):
    """Validator for knowledge entries."""

    def validate_filename_match(self, file_path: Path, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate filename matches zettel_id."""
        zettel_id = parsed_data.get("zettel_id")
        if not zettel_id:
            return {
                "valid": False,
                "issues": ["Zettel ID not found in parsed data"],
            }

        expected_filename = f"{zettel_id}.md"
        actual_filename = file_path.name

        if actual_filename != expected_filename:
            return {
                "valid": False,
                "issues": [
                    f"Filename mismatch: expected '{expected_filename}', got '{actual_filename}'"
                ],
                "error_details": {
                    "expected": expected_filename,
                    "actual": actual_filename,
                    "zettel_id": zettel_id,
                    "path": str(file_path),
                },
            }

        return {"valid": True, "issues": []}

    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate knowledge entry metadata."""
        issues = []
        warnings = []

        # Required fields
        zettel_id = parsed_data.get("zettel_id")
        if not zettel_id:
            issues.append("Zettel ID is required")

        title = parsed_data.get("title")
        if not title:
            issues.append("Title is required")

        content = parsed_data.get("content")
        if not content:
            issues.append("Content is required")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }


class ValidationManager:
    """Unified validation interface."""

    VALIDATORS = {
        "directive": DirectiveValidator(),
        "script": ScriptValidator(),
        "knowledge": KnowledgeValidator(),
    }

    @classmethod
    def get_validator(cls, item_type: str) -> BaseValidator:
        """Get validator for item type."""
        validator = cls.VALIDATORS.get(item_type)
        if not validator:
            raise ValueError(f"Unknown item_type: {item_type}. Supported: {list(cls.VALIDATORS.keys())}")
        return validator

    @classmethod
    def validate(cls, item_type: str, file_path: Path, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate item using appropriate validator.
        
        Returns:
            {"valid": bool, "issues": List[str], "warnings": List[str]}
        """
        validator = cls.get_validator(item_type)
        return validator.validate(file_path, parsed_data)
