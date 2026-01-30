"""
RYE Directive Handler - Intelligence layer for directive parsing and validation.

Migrated from Lilux to RYE to maintain clean microkernel separation.
Contains ALL directive intelligence moved from Lilux kernel.
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import xml.etree.ElementTree as ET

try:
    from lilux.utils.logger import get_logger
except ImportError:
    # Fallback for testing without Lilux
    import logging

    def get_logger(name):
        return logging.getLogger(name)


class DirectiveHandler:
    """Intelligent handler for directive content parsing and validation."""

    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.logger = get_logger("rye_directive_handler")

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse directive XML and extract all data.

        Args:
            file_path: Path to directive file

        Returns:
            Parsed directive data structure
        """
        try:
            content = file_path.read_text()
            return self._parse_directive_xml(content)
        except Exception as e:
            self.logger.error(f"Failed to parse directive {file_path}: {e}")
            raise

    def validate(self, parsed: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """
        Validate directive structure and requirements.

        Args:
            parsed: Parsed directive data
            file_path: Path to directive file

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

        # Validate metadata structure
        metadata = parsed.get("metadata", {})
        if metadata:
            if "model" in metadata:
                model = metadata["model"]
                if isinstance(model, dict) and "tier" not in model:
                    issues.append("Model must have 'tier' attribute")

        # Validate inputs
        inputs = parsed.get("inputs", [])
        if inputs:
            for i, inp in enumerate(inputs):
                if not isinstance(inp, dict):
                    issues.append(f"Input {i} is not a dictionary")
                    continue

                if "name" not in inp:
                    issues.append(f"Input {i} missing 'name' field")
                if "type" not in inp:
                    issues.append(f"Input {i} missing 'type' field")
                if "description" not in inp:
                    warnings.append(f"Input {i} missing 'description' field")

        # Validate process steps
        process = parsed.get("process", {})
        steps = process.get("step", [])
        if steps:
            if isinstance(steps, dict):
                steps = [steps]

            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    issues.append(f"Process step {i} is not a dictionary")
                    continue

                attrs = step.get("_attrs", {})
                if "name" not in attrs:
                    issues.append(f"Process step {i} missing 'name' attribute")
                if "action" not in step and not any(
                    key in step for key in ["command", "http", "tool"]
                ):
                    issues.append(f"Process step {i} missing action")

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def compute_integrity(self, parsed: Dict[str, Any], content: str) -> str:
        """
        Compute canonical integrity hash for a directive.

        Args:
            parsed: Parsed directive data
            content: Raw file content

        Returns:
            SHA256 hex digest (64 characters)
        """
        # Extract XML content without signature
        xml_content = self._extract_content_for_hash(content)

        # Build canonical content for hashing
        metadata = {
            "name": parsed.get("name", ""),
            "version": parsed.get("version", "0.0.0"),
            "description": parsed.get("description", ""),
            "category": parsed.get("category", ""),
        }

        # Create canonical representation
        canonical_parts = [
            f"name:{metadata['name']}",
            f"version:{metadata['version']}",
            f"description:{metadata['description']}",
            f"category:{metadata['category']}",
            f"xml:{xml_content}",
        ]

        canonical_content = "|".join(canonical_parts)
        return hashlib.sha256(canonical_content.encode()).hexdigest()

    def extract_signature(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract signature from content.

        Args:
            content: File content with potential signature

        Returns:
            Signature data if found, None otherwise
        """
        # Look for signature comment at end of file
        signature_pattern = r"<!--\s*kiwi-mcp:validated:([^:]+):([^:]+):([^\s]+)\s*-->"
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
        signature = (
            f"\n<!-- kiwi-mcp:validated:{hash}:SIGNATURE:{self._extract_item_id(content)} -->"
        )
        return content + signature

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from directive content.

        Args:
            content: Raw file content

        Returns:
            Dict with extracted metadata
        """
        parsed = self._parse_directive_xml(content)

        metadata = {
            "name": parsed.get("name", ""),
            "description": parsed.get("description", ""),
            "category": parsed.get("category", ""),
            "version": parsed.get("version", "0.0.0"),
            "author": parsed.get("author", ""),
            "model": parsed.get("model", {}),
            "permissions": parsed.get("permissions", []),
            "inputs": parsed.get("inputs", []),
            "process": parsed.get("process", {}),
        }

        return metadata

    def _parse_directive_xml(self, content: str) -> Dict[str, Any]:
        """
        Parse directive XML content.

        Args:
            content: File content containing XML

        Returns:
            Parsed directive structure
        """
        # Extract XML block from markdown
        xml_match = re.search(r"```xml\s*(.*?)\s*```", content, re.DOTALL)
        if not xml_match:
            raise ValueError("No XML directive block found in content")

        xml_content = xml_match.group(1).strip()

        # Parse XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        if root.tag != "directive":
            raise ValueError(f"Expected <directive> root element, got <{root.tag}>")

        # Extract directive attributes
        result = {
            "name": root.get("name", ""),
            "version": root.get("version", "0.0.0"),
        }

        # Parse child elements
        for child in root:
            if child.tag == "metadata":
                result.update(self._parse_metadata(child))
            elif child.tag == "inputs":
                result["inputs"] = self._parse_inputs(child)
            elif child.tag == "process":
                result["process"] = self._parse_process(child)
            elif child.tag == "outputs":
                result["outputs"] = self._parse_outputs(child)

        return result

    def _parse_metadata(self, metadata_elem: ET.Element) -> Dict[str, Any]:
        """Parse metadata element."""
        metadata = {}

        for child in metadata_elem:
            if child.tag == "description":
                metadata["description"] = child.text or ""
            elif child.tag == "category":
                metadata["category"] = child.text or ""
            elif child.tag == "author":
                metadata["author"] = child.text or ""
            elif child.tag == "model":
                metadata["model"] = {
                    "tier": child.get("tier", "general"),
                    "fallback": child.get("fallback", "general"),
                    "parallel": child.get("parallel", "false").lower() == "true",
                    "text": child.text or "",
                }
            elif child.tag == "permissions":
                permissions = []
                for perm in child:
                    if perm.tag == "permission":
                        perm_text = perm.text or ""
                        resource = perm.get("resource", "")
                        permissions.append({"text": perm_text, "resource": resource})
                metadata["permissions"] = permissions

        return metadata

    def _parse_inputs(self, inputs_elem: ET.Element) -> List[Dict[str, Any]]:
        """Parse inputs element."""
        inputs = []

        for child in inputs_elem:
            if child.tag == "input":
                input_def = {
                    "name": child.get("name", ""),
                    "type": child.get("type", "string"),
                    "required": child.get("required", "false").lower() == "true",
                    "description": child.text or "",
                }
                inputs.append(input_def)

        return inputs

    def _parse_process(self, process_elem: ET.Element) -> Dict[str, Any]:
        """Parse process element."""
        process = {}

        for child in process_elem:
            if child.tag == "step":
                step_data = {
                    "_attrs": {
                        "name": child.get("name", ""),
                        "description": child.get("description", ""),
                    }
                }

                # Parse step content
                for step_child in child:
                    if step_child.tag == "action":
                        step_data["action"] = step_child.text or ""
                    elif step_child.tag == "description":
                        step_data["description"] = step_child.text or ""
                    elif step_child.tag in ["command", "http", "tool"]:
                        step_data[step_child.tag] = step_child.text or ""

                if "step" not in process:
                    process["step"] = []
                process["step"].append(step_data)

        return process

    def _parse_outputs(self, outputs_elem: ET.Element) -> Dict[str, Any]:
        """Parse outputs element."""
        outputs = {}

        for child in outputs_elem:
            if child.tag == "success":
                outputs["success"] = child.text or ""
            elif child.tag == "failure":
                outputs["failure"] = child.text or ""

        return outputs

    def _extract_content_for_hash(self, content: str) -> str:
        """
        Extract XML content for hashing (without signature).

        Args:
            content: Full file content

        Returns:
            XML content without signature
        """
        # Remove signature
        content = self._remove_existing_signature(content)

        # Extract XML block
        xml_match = re.search(r"```xml\s*(.*?)\s*```", content, re.DOTALL)
        if xml_match:
            return xml_match.group(1).strip()

        return ""

    def _remove_existing_signature(self, content: str) -> str:
        """Remove existing signature from content."""
        signature_pattern = r"\n<!--\s*kiwi-mcp:validated:.*?-->"
        return re.sub(signature_pattern, "", content, flags=re.DOTALL)

    def _extract_item_id(self, content: str) -> str:
        """Extract item ID from directive content."""
        try:
            parsed = self._parse_directive_xml(content)
            return parsed.get("name", "")
        except:
            return ""
