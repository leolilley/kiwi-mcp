"""
Chain Validator - Parent→Child validation for tool execution chains.

Each tool can define schemas for what children it accepts via
`validation.child_schemas` in its manifest. This validator checks
each adjacent pair (parent, child) in the execution chain.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ChainValidationResult:
    """Result of chain validation."""
    
    valid: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_pairs: int = 0
    
    def add_issue(self, issue: str) -> None:
        self.issues.append(issue)
        self.valid = False
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)


class ChainValidator:
    """Validates parent→child relationships in execution chains."""
    
    def __init__(self, schema_validator=None):
        """
        Initialize chain validator.
        
        Args:
            schema_validator: Optional SchemaValidator instance.
                            If not provided, will lazy-load.
        """
        self._schema_validator = schema_validator
    
    def _get_schema_validator(self):
        """Lazy-load schema validator."""
        if self._schema_validator is None:
            try:
                from kiwi_mcp.utils.schema_validator import SchemaValidator
                self._schema_validator = SchemaValidator()
            except ImportError:
                logger.warning("SchemaValidator not available")
                return None
        return self._schema_validator
    
    def validate_chain(self, chain: List[Dict[str, Any]]) -> ChainValidationResult:
        """
        Validate each adjacent pair (parent, child) in the chain.
        
        The chain is ordered: [leaf_script, runtime, ..., primitive]
        So we validate: runtime validates leaf_script, etc.
        
        Args:
            chain: List of tool dicts from leaf to primitive
            
        Returns:
            ChainValidationResult with validation status
        """
        result = ChainValidationResult(valid=True)
        
        if len(chain) < 2:
            # Single tool or empty chain - nothing to validate
            return result
        
        # Iterate pairs: (child, parent)
        for i in range(len(chain) - 1):
            child = chain[i]
            parent = chain[i + 1]
            
            pair_result = self._validate_pair(parent, child)
            
            if not pair_result.get("valid", True):
                for issue in pair_result.get("issues", []):
                    result.add_issue(
                        f"[{parent.get('tool_id')}→{child.get('tool_id')}] {issue}"
                    )
            
            for warning in pair_result.get("warnings", []):
                result.add_warning(
                    f"[{parent.get('tool_id')}→{child.get('tool_id')}] {warning}"
                )
            
            result.validated_pairs += 1
        
        return result
    
    def _validate_pair(
        self, 
        parent: Dict[str, Any], 
        child: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that parent accepts child according to its schema.
        
        Args:
            parent: Parent tool dict (the executor)
            child: Child tool dict (the one being executed)
            
        Returns:
            Dict with valid, issues, warnings
        """
        parent_manifest = parent.get("manifest", {})
        validation_config = parent_manifest.get("validation", {})
        child_schemas = validation_config.get("child_schemas", [])
        
        # Primitives don't need to validate children (they're the bottom)
        if parent.get("tool_type") == "primitive":
            return {"valid": True, "issues": [], "warnings": []}
        
        if not child_schemas:
            return {
                "valid": False,
                "issues": [
                    f"Parent '{parent.get('tool_id')}' must define child_schemas to validate children"
                ],
                "warnings": []
            }
        
        # Find matching schema for child
        child_type = child.get("tool_type")
        
        for schema_def in child_schemas:
            match_criteria = schema_def.get("match", {})
            
            if self._matches(child, match_criteria):
                # Found matching schema - validate child against it
                schema = schema_def.get("schema")
                if not schema:
                    return {
                        "valid": True,
                        "issues": [],
                        "warnings": ["Schema definition has no schema body"]
                    }
                
                return self._validate_against_schema(child, schema)
        
        # No matching schema found
        return {
            "valid": False,
            "issues": [
                f"No schema matches child type '{child_type}'. "
                f"Available matches: {[s.get('match', {}) for s in child_schemas]}"
            ],
            "warnings": []
        }
    
    def _matches(self, child: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """
        Check if child matches the match criteria.
        
        Args:
            child: Child tool dict
            criteria: Match criteria dict (e.g., {"tool_type": "script"})
            
        Returns:
            True if all criteria match
        """
        for key, value in criteria.items():
            child_value = child.get(key)
            
            # Handle nested matching (e.g., manifest.language)
            if "." in key:
                parts = key.split(".")
                child_value = child
                for part in parts:
                    if isinstance(child_value, dict):
                        child_value = child_value.get(part)
                    else:
                        child_value = None
                        break
            
            if child_value != value:
                return False
        
        return True
    
    def _validate_against_schema(
        self, 
        child: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate child against JSON Schema.
        
        Args:
            child: Child tool dict to validate
            schema: JSON Schema to validate against
            
        Returns:
            Validation result dict
        """
        validator = self._get_schema_validator()
        
        if not validator or not validator.is_available():
            return {
                "valid": True,
                "issues": [],
                "warnings": ["jsonschema not available - validation skipped"]
            }
        
        return validator.validate(child, schema)


def get_child_schema_template(tool_type: str) -> Dict[str, Any]:
    """
    Get a template child schema for common tool types.
    
    Useful for building parent validation configs.
    
    Args:
        tool_type: Type of child tool
        
    Returns:
        Template schema dict
    """
    templates = {
        "script": {
            "match": {"tool_type": "script"},
            "schema": {
                "type": "object",
                "properties": {
                    "tool_id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                    "tool_type": {"const": "script"},
                    "manifest": {
                        "type": "object",
                        "properties": {
                            "entrypoint": {"type": "string"}
                        },
                        "required": ["entrypoint"]
                    }
                },
                "required": ["tool_id", "tool_type", "manifest"]
            }
        },
        "runtime": {
            "match": {"tool_type": "runtime"},
            "schema": {
                "type": "object",
                "properties": {
                    "tool_id": {"type": "string"},
                    "tool_type": {"const": "runtime"},
                    "manifest": {
                        "type": "object",
                        "properties": {
                            "config": {"type": "object"}
                        }
                    }
                },
                "required": ["tool_id", "tool_type"]
            }
        }
    }
    
    return templates.get(tool_type, {"match": {"tool_type": tool_type}, "schema": {}})
