"""
RYE Tool Handler - Intelligence layer for tool parsing and validation.

Migrated from Lilux to RYE to maintain clean microkernel separation.
Contains ALL tool intelligence moved from Lilux kernel.
"""

import ast
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from lilux.utils.logger import get_logger
except ImportError:
    # Fallback for testing without Lilux
    import logging

    def get_logger(name):
        return logging.getLogger(name)


class ToolHandler:
    """Intelligent handler for tool content parsing and validation."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.logger = get_logger("rye_tool_handler")

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse tool metadata and extract executor config.

        Args:
            file_path: Path to tool file

        Returns:
            Parsed tool data structure
        """
        try:
            content = file_path.read_text()
            return self._parse_tool_metadata(content)
        except Exception as e:
            self.logger.error(f"Failed to parse tool {file_path}: {e}")
            raise

    def validate(self, parsed: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """
        Validate tool structure and executor chain.

        Args:
            parsed: Parsed tool data
            file_path: Path to tool file

        Returns:
            Validation result with issues if any
        """
        issues = []
        warnings = []

        # Validate required fields
        required_fields = ["name", "description", "version"]
        for field in required_fields:
            if not parsed.get(field):
                issues.append(f"Missing required field: {field}")

        # Validate version format
        version = parsed.get("version", "")
        if version and not re.match(r"^\d+\.\d+\.\d+$", version):
            issues.append(f"Invalid version format: {version}. Expected: X.Y.Z")

        # Validate tool type
        tool_type = parsed.get("tool_type")
        if tool_type and tool_type not in ["subprocess", "http_client", "chain", "custom"]:
            warnings.append(f"Unknown tool type: {tool_type}")

        # Validate executor config
        executor = parsed.get("executor", {})
        if executor:
            if "type" not in executor:
                issues.append("Executor missing 'type' field")

            # Validate subprocess executor
            if executor.get("type") == "subprocess":
                if "command" not in executor:
                    issues.append("Subprocess executor missing 'command' field")

            # Validate HTTP executor
            elif executor.get("type") == "http_client":
                if "url" not in executor:
                    issues.append("HTTP executor missing 'url' field")
                if "method" not in executor:
                    issues.append("HTTP executor missing 'method' field")

            # Validate chain executor
            elif executor.get("type") == "chain":
                if "chain" not in executor:
                    issues.append("Chain executor missing 'chain' field")

        # Validate input schema
        input_schema = parsed.get("input_schema")
        if input_schema and not isinstance(input_schema, dict):
            issues.append("input_schema must be a JSON Schema dictionary")

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def compute_integrity(self, parsed: Dict[str, Any], content: str) -> str:
        """
        Compute canonical integrity hash for a tool.

        Args:
            parsed: Parsed tool data
            content: Raw file content

        Returns:
            SHA256 hex digest (64 characters)
        """
        # Extract Python code without signature
        code_content = self._extract_content_for_hash(content)

        # Build canonical content for hashing
        metadata = {
            "name": parsed.get("name", ""),
            "version": parsed.get("version", "0.0.0"),
            "description": parsed.get("description", ""),
            "tool_type": parsed.get("tool_type", ""),
        }

        # Create canonical representation
        canonical_parts = [
            f"name:{metadata['name']}",
            f"version:{metadata['version']}",
            f"description:{metadata['description']}",
            f"tool_type:{metadata['tool_type']}",
            f"code:{code_content}",
        ]

        canonical_content = "|".join(canonical_parts)
        return hashlib.sha256(canonical_content.encode()).hexdigest()

    def get_executor_type(self, parsed: Dict[str, Any]) -> str:
        """
        Determine which Lilux primitive to use.

        Args:
            parsed: Parsed tool data

        Returns:
            Executor type string
        """
        executor = parsed.get("executor", {})
        return executor.get("type", "subprocess")

    def extract_signature(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract signature from content.

        Args:
            content: File content with potential signature

        Returns:
            Signature data if found, None otherwise
        """
        # Look for signature comment at end of file
        signature_pattern = r"##\s*Signature:\s*kiwi-mcp:validated:([^:]+):([^:]+):([^\s]+)"
        match = re.search(signature_pattern, content)

        if match:
            return {
                "hash": match.group(1),
                "signature": match.group(2),
                "item_id": match.group(3),
                "format": "kiwi-mcp",
            }

        return None

    def add_signature(self, content: str, hash: str) -> str:
        """
        Add signature to content.

        Args:
            content: Original content
            hash: Computed hash to sign

        Returns:
            Content with signature added
        """
        # Remove existing signature
        content = self._remove_existing_signature(content)

        # Add new signature
        signature = f"\n\n## Signature: kiwi-mcp:validated:{hash}:SIGNATURE:{self._extract_item_id(content)}"
        return content + signature

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from tool content.

        Args:
            content: Raw file content

        Returns:
            Dict with extracted metadata
        """
        parsed = self._parse_tool_metadata(content)

        metadata = {
            "name": parsed.get("name", ""),
            "description": parsed.get("description", ""),
            "version": parsed.get("version", "0.0.0"),
            "tool_type": parsed.get("tool_type", "subprocess"),
            "category": parsed.get("category", ""),
            "author": parsed.get("author", ""),
            "executor": parsed.get("executor", {}),
            "input_schema": parsed.get("input_schema", {}),
            "output_schema": parsed.get("output_schema", {}),
            "requires_auth": parsed.get("requires_auth", False),
            "mutates_state": parsed.get("mutates_state", False),
        }

        return metadata

    def _parse_tool_metadata(self, content: str) -> Dict[str, Any]:
        """
        Parse tool metadata from Python file.

        Args:
            content: Python file content

        Returns:
            Parsed tool metadata structure
        """
        # Remove existing signature
        content = self._remove_existing_signature(content)

        # Parse Python AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")

        result = {}

        # Extract module-level variables
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        if var_name.startswith("__") and var_name.endswith("__"):
                            # Skip special variables like __name__
                            continue

                        # Extract value
                        if isinstance(node.value, ast.Str):  # Python < 3.8
                            result[var_name] = node.value.s
                        elif isinstance(node.value, ast.Constant):
                            result[var_name] = node.value.value
                        elif isinstance(node.value, ast.Dict):
                            result[var_name] = self._extract_dict_value(node.value)
                        elif isinstance(node.value, ast.Dict):
                            result[var_name] = self._extract_dict_value(node.value)

        # Extract docstring
        if (
            tree.body and isinstance(tree.body[0], ast.Expr) and hasattr(tree.body[0].value, "s")
        ):  # Python < 3.8
            result["description"] = tree.body[0].value.s
        elif (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and hasattr(tree.body[0].value, "value")
        ):  # Python >= 3.8
            result["description"] = tree.body[0].value.value

        # Extract metadata from comments or special variables
        # Look for TOOL_METADATA block
        metadata_match = re.search(r"TOOL_METADATA\s*=\s*{([^}]+)}", content, re.DOTALL)
        if metadata_match:
            try:
                # Safe eval of the metadata dict
                metadata_str = "{" + metadata_match.group(1) + "}"
                metadata_dict = eval(metadata_str)  # No security issue - controlled content
                result.update(metadata_dict)
            except:
                pass  # Fall back to AST parsing

        # Default values
        if "tool_type" not in result:
            result["tool_type"] = "subprocess"

        if "version" not in result:
            result["version"] = "0.0.0"

        return result

    def _extract_dict_value(self, dict_node: ast.Dict) -> Dict[str, Any]:
        """Extract value from AST dict node."""
        result = {}

        for key, value in zip(dict_node.keys, dict_node.values):
            if hasattr(key, "s"):  # Python < 3.8
                key_str = key.s
            elif hasattr(key, "value"):  # Python >= 3.8
                key_str = key.value
            else:
                continue

            if hasattr(value, "s"):  # Python < 3.8
                result[key_str] = value.s
            elif hasattr(value, "value"):  # Python >= 3.8
                result[key_str] = value.value
            elif isinstance(value, ast.Dict):
                result[key_str] = self._extract_dict_value(value)

        return result

    def _extract_content_for_hash(self, content: str) -> str:
        """
        Extract Python code for hashing (without signature).

        Args:
            content: Full file content

        Returns:
            Python code without signature
        """
        # Remove signature
        content = self._remove_existing_signature(content)

        # Remove comments for consistent hashing
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            lines.append(line)

        return "\n".join(lines)

    def _remove_existing_signature(self, content: str) -> str:
        """Remove existing signature from content."""
        signature_pattern = r"\n\n##\s*Signature:\s*kiwi-mcp:validated:.*?$"
        return re.sub(signature_pattern, "", content, flags=re.MULTILINE)

    def _extract_item_id(self, content: str) -> str:
        """Extract item ID from tool content."""
        try:
            parsed = self._parse_tool_metadata(content)
            return parsed.get("name", "")
        except:
            return ""
