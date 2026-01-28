"""
Unified Validation Pipeline

Provides consistent validation across directives, scripts, and knowledge entries.
"""

import re
import subprocess
import urllib.parse
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from packaging import version

from kiwi_mcp.utils.logger import get_logger

logger = get_logger("validators")


class BaseValidator(ABC):
    """Base validator for item-type-specific validation."""

    @abstractmethod
    def validate_filename_match(
        self, file_path: Path, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
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

        filename_result = self.validate_filename_match(file_path, parsed_data)
        if not filename_result.get("valid", True):
            all_issues.extend(filename_result.get("issues", []))
        if filename_result.get("warnings"):
            all_warnings.extend(filename_result.get("warnings", []))

        metadata_result = self.validate_metadata(parsed_data)
        if not metadata_result.get("valid", True):
            all_issues.extend(metadata_result.get("issues", []))
        if metadata_result.get("warnings"):
            all_warnings.extend(metadata_result.get("warnings", []))

        if all_issues:
            logger.warning(f"Validation failed for {file_path}: {all_issues}")

        return {
            "valid": len(all_issues) == 0,
            "issues": all_issues,
            "warnings": all_warnings,
        }


class DirectiveValidator(BaseValidator):
    """Validator for directives."""

    def validate_filename_match(
        self, file_path: Path, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate filename matches directive name and name format."""
        issues = []
        directive_name = parsed_data.get("name")

        if not directive_name:
            return {
                "valid": False,
                "issues": ["Directive name not found in parsed data"],
            }

        # Validate name format (must be snake_case, can start with number for ordering)
        if not re.match(r"^[a-z0-9][a-z0-9_]*$", directive_name):
            issues.append(
                f"Invalid directive name '{directive_name}'. Must be snake_case "
                "(lowercase letters, numbers, underscores)"
            )

        expected_filename = f"{directive_name}.md"
        actual_filename = file_path.name

        if actual_filename != expected_filename:
            issues.append(
                f"Filename mismatch: expected '{expected_filename}', got '{actual_filename}'"
            )

        if issues:
            return {
                "valid": False,
                "issues": issues,
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

        # Validate XML structure: closing directive tag must be at the end
        # Use 'raw' field (full file content) not 'content' (which is just the process XML)
        content = parsed_data.get("raw", "") or parsed_data.get("content", "")
        if content:
            xml_content = self._extract_xml_from_content(content)
            if xml_content:
                # Strip whitespace and check that XML ends with </directive>
                xml_stripped = xml_content.strip()
                if not xml_stripped.endswith("</directive>"):
                    issues.append(
                        "Directive XML must end with </directive> tag. "
                        "The closing </directive> tag must be the last element in the XML block."
                    )
                else:
                    # Check that there's no content after </directive> in the original content
                    # Find the position of the extracted XML in the original content
                    start_match = re.search(r"<directive[^>]*>", content)
                    if start_match:
                        start_idx = start_match.start()
                        end_tag = "</directive>"
                        end_idx = content.rfind(end_tag)
                        if end_idx != -1:
                            # Check if there's any non-whitespace content after </directive> before the code block ends
                            after_closing = content[end_idx + len(end_tag) :]
                            # Find the end of the XML code block (```)
                            code_block_end = after_closing.find("```")
                            if code_block_end != -1:
                                # Check content between </directive> and closing ```
                                content_before_close = after_closing[:code_block_end].strip()
                                if content_before_close:
                                    issues.append(
                                        "Directive XML must end with </directive> tag with no content after it. "
                                        f"Found content after closing tag (before code block end): {repr(content_before_close[:50])}"
                                    )

                                # Also check for content after the closing ``` that looks like it shouldn't be there
                                # (e.g., XML-like tags or other structured content)
                                after_code_block = after_closing[code_block_end + 3 :].strip()
                                # Look for XML-like tags or other suspicious content
                                if after_code_block:
                                    # Check if it looks like XML tags or structured content
                                    xml_like_pattern = r"<[^>]+>"
                                    if re.search(xml_like_pattern, after_code_block):
                                        issues.append(
                                            "Directive XML code block should end immediately after closing ```. "
                                            f"Found unexpected content after code block: {repr(after_code_block[:100])}"
                                        )
            else:
                has_directive_tag = "<directive" in content
                has_closing_tag = "</directive>" in content
                if not has_directive_tag:
                    issues.append("Missing <directive> opening tag in content")
                elif not has_closing_tag:
                    issues.append("Missing </directive> closing tag in content")
                else:
                    issues.append("Could not extract XML: <directive> and </directive> tags found but extraction failed")

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
            # Check tier - must be one of the valid values
            tier = model_data.get("tier")
            valid_tiers = ["fast", "balanced", "general", "reasoning", "expert", "orchestrator"]
            if tier is None or tier == "":
                issues.append(
                    "Model tag exists but is missing required 'tier' attribute. "
                    'Example: <model tier="reasoning">...</model>'
                )
            elif not isinstance(tier, str) or not tier.strip():
                issues.append(
                    f"Model 'tier' attribute must be a non-empty string, got: {repr(tier)}"
                )
            elif tier not in valid_tiers:
                issues.append(f"Invalid model tier '{tier}'. Must be one of: {valid_tiers}")

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

        # Validate version (REQUIRED) - must be semver format
        directive_version = parsed_data.get("version")
        if not directive_version or directive_version == "0.0.0":
            issues.append(
                "Directive is missing required 'version' attribute. "
                'Add version attribute to <directive> tag: <directive name="..." version="1.0.0">'
            )
        elif not re.match(r"^\d+\.\d+\.\d+$", str(directive_version)):
            issues.append(
                f"Invalid version format '{directive_version}'. Must be semver (e.g., 1.0.0, 2.1.3)"
            )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def _extract_xml_from_content(self, content: str) -> Optional[str]:
        """Extract XML directive from markdown content."""
        start_match = re.search(r"<directive[^>]*>", content)
        if not start_match:
            return None

        start_idx = start_match.start()
        end_tag = "</directive>"
        end_idx = content.rfind(end_tag)
        if end_idx == -1 or end_idx < start_idx:
            return None

        return content[start_idx : end_idx + len(end_tag)].strip()


class ToolValidator(BaseValidator):
    """Validator for unified tools - validates manifest structure at definition time.

    This is Layer 1 validation: checking that tool manifests are well-formed.
    It does NOT use database calls or async operations.

    Runtime parameter validation (Layer 2) happens in PrimitiveExecutor using
    the tool's config_schema - that's where "everything else is data" applies.
    """

    def validate_filename_match(
        self, file_path: Path, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate that filename matches tool identifier."""
        issues = []

        tool_id = parsed_data.get("tool_id") or parsed_data.get("name")
        if not tool_id:
            return {
                "valid": False,
                "issues": ["Tool ID not found in parsed data"],
            }

        # Check filename matches tool_id (with appropriate extension)
        expected_extensions = {".py", ".sh", ".yaml", ".yml"}
        actual_extension = file_path.suffix.lower()

        if actual_extension not in expected_extensions:
            issues.append(
                f"Unsupported file extension '{actual_extension}'. "
                f"Expected one of: {', '.join(sorted(expected_extensions))}"
            )

        expected_stem = tool_id
        actual_stem = file_path.stem

        if actual_stem != expected_stem:
            issues.append(
                f"Filename mismatch: expected '{expected_stem}{actual_extension}', "
                f"got '{file_path.name}'"
            )

        if issues:
            return {
                "valid": False,
                "issues": issues,
                "error_details": {
                    "expected": f"{expected_stem}{actual_extension}",
                    "actual": file_path.name,
                    "tool_id": tool_id,
                    "path": str(file_path),
                },
            }

        return {"valid": True, "issues": []}

    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool manifest metadata - definition-time checks only."""
        issues = []
        warnings = []

        # Required fields for all tools
        tool_id = parsed_data.get("tool_id") or parsed_data.get("name")
        if not tool_id:
            issues.append("Tool ID (tool_id or name) is required")

        tool_type = parsed_data.get("tool_type")
        if not tool_type:
            issues.append("Tool type (tool_type) is required")
        elif not isinstance(tool_type, str) or not tool_type.strip():
            issues.append("Tool type (tool_type) must be a non-empty string")

        # Version validation
        version = parsed_data.get("version")
        if not version or version == "0.0.0":
            issues.append(
                'Tool is missing required version. Add at module level: __version__ = "1.0.0"'
            )
        elif not re.match(r"^\d+\.\d+\.\d+", str(version)):
            issues.append(f"Invalid version format '{version}'. Must be semver (e.g., 1.0.0)")

        # executor_id required for non-primitives
        # Only primitives can have NULL executor_id (they are the bottom of the chain)
        if tool_type and tool_type != "primitive":
            executor_id = parsed_data.get("executor_id") or parsed_data.get("executor")
            if not executor_id:
                issues.append(
                    f"Tool type '{tool_type}' requires executor_id field. "
                    "Non-primitive tools must reference another tool in the executor chain."
                )

        # Validate requires field (optional list of capability strings)
        requires = parsed_data.get("requires")
        if requires is not None:
            if not isinstance(requires, list):
                issues.append(
                    f"'requires' field must be a list of capability strings, got {type(requires).__name__}"
                )
            else:
                for cap in requires:
                    if not isinstance(cap, str):
                        issues.append(
                            f"Capability in 'requires' must be a string, got {type(cap).__name__}"
                        )
                    elif not self._validate_capability_format(cap):
                        issues.append(
                            f"Invalid capability format '{cap}'. "
                            "Must be <resource>.<action> (e.g., 'fs.read', 'tool.bash')"
                        )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def _validate_capability_format(self, capability: str) -> bool:
        """Validate capability matches pattern <resource>.<action>."""
        if not capability or "." not in capability:
            return False
        parts = capability.split(".", 1)
        if len(parts) != 2:
            return False
        resource, action = parts
        # Both resource and action must be non-empty and contain only valid chars
        if not resource or not action:
            return False
        # Allow alphanumeric, underscore, hyphen
        valid_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        return bool(valid_pattern.match(resource) and valid_pattern.match(action))


class KnowledgeValidator(BaseValidator):
    """Validator for knowledge entries."""

    def validate_filename_match(
        self, file_path: Path, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate filename matches id."""
        id = parsed_data.get("id")
        if not id:
            return {
                "valid": False,
                "issues": ["ID not found in parsed data"],
            }

        expected_filename = f"{id}.md"
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
                    "id": id,
                    "path": str(file_path),
                },
            }

        return {"valid": True, "issues": []}

    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate knowledge entry metadata."""
        issues = []
        warnings = []

        # Required fields
        id = parsed_data.get("id")
        if not id:
            issues.append("ID is required")

        title = parsed_data.get("title")
        if not title:
            issues.append("Title is required")

        content = parsed_data.get("content")
        if not content:
            issues.append("Content is required")

        # Version is required (enables version-warning when running)
        entry_version = parsed_data.get("version")
        if not entry_version or entry_version == "0.0.0":
            issues.append(
                "Knowledge entry is missing required 'version' in YAML frontmatter. "
                'Add to frontmatter: version: "1.0.0"'
            )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two semantic version strings using packaging library.

    Assumes versions are valid strings (missing versions are caught by validator).

    Args:
        version1: First version string
        version2: Second version string

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2

    Raises:
        ValueError: If version strings are invalid (packaging will raise)
    """
    v1 = version.parse(version1)
    v2 = version.parse(version2)
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    return 0


class ValidationResult:
    """Result from a validation operation."""

    def __init__(self, valid: bool, error: Optional[str] = None):
        self.valid = valid
        self.error = error


class BashValidator:
    """Validator for bash scripts in tool manifests."""

    async def validate(self, script_path: Path) -> ValidationResult:
        """Validate a bash script for syntax and structure."""
        try:
            # Check shebang exists
            content = script_path.read_text()
            if not content.startswith("#!"):
                return ValidationResult(valid=False, error="Missing shebang")

            # Syntax check with bash -n
            result = subprocess.run(
                ["bash", "-n", str(script_path)], capture_output=True, text=True
            )
            if result.returncode != 0:
                return ValidationResult(valid=False, error=result.stderr)

            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, error=str(e))


class APIValidator:
    """Validator for API tool manifests."""

    async def validate(self, manifest) -> ValidationResult:
        """Validate an API tool manifest configuration."""
        config = manifest.executor_config

        # Check required fields
        if "endpoint" not in config:
            return ValidationResult(valid=False, error="Missing endpoint")

        # Validate URL format
        if not self._is_valid_url(config["endpoint"]):
            return ValidationResult(valid=False, error="Invalid endpoint URL")

        # Check auth config if present
        if "auth" in config:
            if config["auth"]["type"] not in ["bearer", "api_key", "basic"]:
                return ValidationResult(valid=False, error="Unknown auth type")

        return ValidationResult(valid=True)

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


class ValidationManager:
    """Unified validation interface.

    Two-Layer Validation Architecture:
    - Layer 1 (Definition-time): Validators in this class check manifest structure
    - Layer 2 (Runtime): PrimitiveExecutor validates params against config_schema

    This separation keeps definition validation simple and synchronous while
    allowing runtime validation to be data-driven per tool.
    """

    VALIDATORS = {
        "directive": DirectiveValidator(),
        "tool": ToolValidator(),  # Simple, no DB dependency - Layer 1 validation
        "knowledge": KnowledgeValidator(),
    }

    @classmethod
    def get_validator(cls, item_type: str) -> BaseValidator:
        """Get validator for item type."""
        # Map tool subtypes to tool validator
        tool_types = {"primitive", "runtime", "mcp_server", "mcp_tool", "api"}
        if item_type in tool_types:
            item_type = "tool"

        validator = cls.VALIDATORS.get(item_type)
        if not validator:
            raise ValueError(
                f"Unknown item_type: {item_type}. Supported: {list(cls.VALIDATORS.keys())}"
            )
        return validator

    @classmethod
    def validate(
        cls, item_type: str, file_path: Path, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate item using appropriate validator.

        Returns:
            {"valid": bool, "issues": List[str], "warnings": List[str]}
        """
        validator = cls.get_validator(item_type)
        return validator.validate(file_path, parsed_data)

    @classmethod
    async def validate_and_embed(
        cls,
        item_type: str,
        file_path: Path,
        parsed_data: Dict[str, Any],
        vector_store: Optional[Any] = None,
        item_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate and optionally embed content to vector store.

        This is the validation gate - only valid content gets embedded.

        Args:
            item_type: Type of item (directive, tool, knowledge)
            file_path: Path to the item file
            parsed_data: Parsed item data
            vector_store: Optional vector store for embedding
            item_id: Optional item ID for embedding

        Returns:
            Validation result with optional embedding status
        """
        # First validate
        result = cls.validate(item_type, file_path, parsed_data)

        # If valid and vector store provided, embed
        if result["valid"] and vector_store and item_id:
            try:
                content = cls._extract_searchable(item_type, file_path, parsed_data)
                metadata = {
                    "name": parsed_data.get("name") or parsed_data.get("title", ""),
                    "description": parsed_data.get("description", "")[:200],
                }

                success = await vector_store.embed_and_store(
                    item_id=item_id, item_type=item_type, content=content, metadata=metadata
                )
                result["embedded"] = success
            except Exception as e:
                result["embedding_error"] = str(e)

        return result

    @classmethod
    def _extract_searchable(cls, item_type: str, file_path: Path, parsed_data: Dict) -> str:
        """Extract searchable content based on item type.

        Args:
            item_type: Type of item
            file_path: Path to file
            parsed_data: Parsed item data

        Returns:
            Searchable text content
        """
        if item_type == "directive":
            parts = [
                f"Directive: {parsed_data.get('name', '')}",
                f"Description: {parsed_data.get('description', '')}",
            ]
            for step in parsed_data.get("steps", []):
                parts.append(f"Step: {step.get('description', '')}")
            return "\n".join(parts)

        elif item_type == "tool":
            parts = [f"Tool: {parsed_data.get('name', '')}"]
            # Extract docstrings from Python code
            try:
                import ast

                tree = ast.parse(file_path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        docstring = ast.get_docstring(node)
                        if docstring:
                            parts.append(docstring)
            except:
                pass
            return "\n".join(parts)

        elif item_type == "knowledge":
            return f"{parsed_data.get('title', '')}\n{file_path.read_text()}"

        return file_path.read_text()
