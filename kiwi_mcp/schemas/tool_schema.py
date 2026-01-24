"""
Schema-driven extraction and validation engine.

Architecture:
1. BOOTSTRAP - Loads extractor tools (reads EXTENSIONS, PARSER, EXTRACTION_RULES)
2. PARSERS - Minimal preprocessors (text, yaml, python_ast)
3. PRIMITIVES - Generic extraction functions (filename, regex, path, ast_var, ast_docstring)
4. VALIDATION - Validates tools and extractors

Extractors define WHAT to extract and HOW via schema rules.
The engine provides only generic primitives.
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


# =============================================================================
# PARSERS - Minimal preprocessors for different file types
# =============================================================================

def _parse_text(content: str) -> Dict[str, Any]:
    """Raw text - no preprocessing."""
    return {"content": content}


def _parse_yaml(content: str) -> Dict[str, Any]:
    """Parse YAML content."""
    try:
        return {"data": yaml.safe_load(content) or {}, "content": content}
    except Exception:
        return {"data": {}, "content": content}


def _parse_python_ast(content: str) -> Dict[str, Any]:
    """Parse Python AST."""
    try:
        return {"ast": ast.parse(content), "content": content}
    except SyntaxError:
        return {"ast": None, "content": content}


PARSERS = {
    "text": _parse_text,
    "yaml": _parse_yaml,
    "python_ast": _parse_python_ast,
}


# =============================================================================
# PRIMITIVES - Generic extraction functions
# =============================================================================

def _extract_filename(rule: Dict, parsed: Dict, file_path: Path) -> Optional[str]:
    """Extract name from filename stem."""
    return file_path.stem


def _extract_regex(rule: Dict, parsed: Dict, file_path: Path) -> Optional[str]:
    """Extract value using regex pattern."""
    content = parsed.get("content", "")
    pattern = rule.get("pattern")
    if not pattern:
        return None
    
    flags = re.MULTILINE if rule.get("multiline") else 0
    match = re.search(pattern, content, flags)
    if match:
        group = rule.get("group", 1)
        try:
            result = match.group(group)
            return result.strip() if result else None
        except IndexError:
            return match.group(0).strip() if match.group(0) else None
    return None


def _extract_path(rule: Dict, parsed: Dict, file_path: Path) -> Optional[Any]:
    """Extract value from parsed dict by key path."""
    data = parsed.get("data", {})
    if not isinstance(data, dict):
        return None
    
    key = rule.get("key", "")
    keys = key.split(".") if "." in key else [key]
    
    current = data
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            # Try fallback
            fallback = rule.get("fallback")
            if fallback and isinstance(data, dict):
                return data.get(fallback)
            return None
    return current


def _extract_ast_var(rule: Dict, parsed: Dict, file_path: Path) -> Optional[Any]:
    """Extract module-level variable from Python AST."""
    tree = parsed.get("ast")
    if not tree:
        return None
    
    var_name = rule.get("name")
    if not var_name:
        return None
    
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == var_name:
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    if isinstance(node.value, ast.Constant):
                        return node.value.value
                    return None
    return None


def _extract_ast_docstring(rule: Dict, parsed: Dict, file_path: Path) -> Optional[str]:
    """Extract module docstring from Python AST."""
    tree = parsed.get("ast")
    if not tree or not tree.body:
        return None
    
    first = tree.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        if isinstance(first.value.value, str):
            docstring = first.value.value.strip()
            # Extract first paragraph only
            lines = docstring.split("\n")
            desc_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    break
                desc_lines.append(line)
            return " ".join(desc_lines) if desc_lines else docstring
    return None


PRIMITIVES = {
    "filename": _extract_filename,
    "regex": _extract_regex,
    "path": _extract_path,
    "ast_var": _extract_ast_var,
    "ast_docstring": _extract_ast_docstring,
}


# =============================================================================
# BOOTSTRAP - Loads extractor tools
# =============================================================================

class Bootstrap:
    """Load extractor tools by reading their module variables."""

    @staticmethod
    def load_extractor(file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load an extractor tool's EXTENSIONS, PARSER, SIGNATURE_FORMAT, and EXTRACTION_RULES.
        """
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            extensions = None
            parser = "text"  # Default parser
            signature_format = None
            rules = None
            
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        if target.id == "EXTENSIONS":
                            try:
                                extensions = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
                        elif target.id == "PARSER":
                            try:
                                parser = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
                        elif target.id == "SIGNATURE_FORMAT":
                            try:
                                signature_format = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
                        elif target.id == "EXTRACTION_RULES":
                            try:
                                rules = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
            
            if extensions and rules:
                return {
                    "extensions": extensions,
                    "parser": parser,
                    "signature_format": signature_format or {"prefix": "#", "after_shebang": True},
                    "rules": rules,
                    "path": file_path,
                }
            return None
            
        except Exception:
            return None


# =============================================================================
# EXTRACTOR VALIDATION
# =============================================================================

class ExtractorValidator:
    """Validates extractor tools have correct structure."""

    @staticmethod
    def validate(extractor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an extractor's structure."""
        issues = []
        
        extensions = extractor_data.get("extensions")
        parser = extractor_data.get("parser", "text")
        rules = extractor_data.get("rules")
        
        # Validate EXTENSIONS
        if not extensions:
            issues.append("EXTENSIONS is required")
        elif not isinstance(extensions, list):
            issues.append("EXTENSIONS must be a list")
        else:
            for ext in extensions:
                if not isinstance(ext, str):
                    issues.append(f"Extension must be string, got {type(ext).__name__}")
                elif not ext.startswith("."):
                    issues.append(f"Extension must start with '.', got '{ext}'")
        
        # Validate PARSER
        if parser not in PARSERS:
            issues.append(f"Unknown PARSER '{parser}'. Valid: {list(PARSERS.keys())}")
        
        # Validate EXTRACTION_RULES
        if not rules:
            issues.append("EXTRACTION_RULES is required")
        elif not isinstance(rules, dict):
            issues.append("EXTRACTION_RULES must be a dict")
        else:
            for field_name, rule in rules.items():
                if not isinstance(rule, dict):
                    issues.append(f"Rule for '{field_name}' must be a dict")
                    continue
                
                rule_type = rule.get("type")
                if not rule_type:
                    issues.append(f"Rule for '{field_name}' missing 'type'")
                elif rule_type not in PRIMITIVES:
                    issues.append(
                        f"Rule '{field_name}' has unknown type '{rule_type}'. "
                        f"Valid types: {list(PRIMITIVES.keys())}"
                    )
                
                # Type-specific validation
                if rule_type == "regex" and "pattern" not in rule:
                    issues.append(f"Rule '{field_name}' (regex) requires 'pattern'")
                if rule_type == "path" and "key" not in rule:
                    issues.append(f"Rule '{field_name}' (path) requires 'key'")
                if rule_type == "ast_var" and "name" not in rule:
                    issues.append(f"Rule '{field_name}' (ast_var) requires 'name'")
        
        return {"valid": len(issues) == 0, "issues": issues}


# =============================================================================
# TOOL VALIDATION SCHEMA
# =============================================================================

VALIDATION_SCHEMA = {
    "fields": {
        "name": {"required": True, "type": "string"},
        "version": {"required": True, "type": "semver"},
        "tool_type": {"required": True, "type": "string"},
        "executor_id": {
            "required": False,
            "required_unless": {"tool_type": ["primitive", "extractor"]},
        },
        "category": {"required": False, "type": "string"},
        "description": {"required": False, "type": "string"},
        "config_schema": {"required": False, "type": "object"},
        "config": {"required": False, "type": "object"},
        "mutates_state": {"required": False, "type": "boolean", "default": False},
    },
}


# =============================================================================
# SCHEMA EXTRACTOR - Dynamic extraction using loaded rules
# =============================================================================

class SchemaExtractor:
    """
    Extraction engine that loads rules from extractor tools.
    
    Uses Bootstrap to load extractors, then PRIMITIVES for extraction.
    """

    def __init__(self):
        self._extractors: Dict[str, Dict] = {}  # ext -> {parser, rules}
        self._extractors_loaded = False

    def _load_extractors(self, project_path: Optional[Path] = None):
        """Load extractor tools using bootstrap."""
        if self._extractors_loaded:
            return
        
        search_paths = []
        if project_path:
            search_paths.append(project_path / ".ai" / "tools" / "extractors")
        search_paths.append(Path.cwd() / ".ai" / "tools" / "extractors")
        
        from kiwi_mcp.utils.resolvers import get_user_space
        search_paths.append(get_user_space() / "tools" / "extractors")
        
        for extractors_dir in search_paths:
            if extractors_dir.exists():
                for file_path in extractors_dir.glob("*.py"):
                    if file_path.name.startswith("_"):
                        continue
                    
                    extractor_data = Bootstrap.load_extractor(file_path)
                    if extractor_data:
                        # Validate extractor
                        validation = ExtractorValidator.validate(extractor_data)
                        if validation["valid"]:
                            for ext in extractor_data["extensions"]:
                                self._extractors[ext.lower()] = {
                                    "parser": extractor_data["parser"],
                                    "rules": extractor_data["rules"],
                                }
        
        self._extractors_loaded = True

    def extract(self, file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
        """Extract metadata using dynamically loaded rules."""
        self._load_extractors(project_path)
        
        ext = file_path.suffix.lower()
        extractor = self._extractors.get(ext)
        
        if not extractor:
            raise ValueError(
                f"No extractor found for extension '{ext}'. "
                f"Available: {list(self._extractors.keys())}"
            )
        
        content = file_path.read_text()
        
        # Use the extractor's parser
        parser_name = extractor["parser"]
        parser_func = PARSERS.get(parser_name, _parse_text)
        parsed = parser_func(content)
        
        # Apply extraction rules
        result = {}
        for field, rule in extractor["rules"].items():
            primitive = PRIMITIVES.get(rule["type"])
            if primitive:
                result[field] = primitive(rule, parsed, file_path)
            else:
                result[field] = None
        
        return result

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        self._load_extractors()
        return list(self._extractors.keys())


# =============================================================================
# SCHEMA VALIDATOR
# =============================================================================

class SchemaValidator:
    """Validates extracted tool data."""

    def __init__(self, schema: Dict[str, Any] = None):
        self.schema = schema or VALIDATION_SCHEMA

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted data against schema."""
        issues = []
        warnings = []
        fields = self.schema["fields"]
        
        for field_name, field_schema in fields.items():
            value = data.get(field_name)
            
            if field_schema.get("required"):
                if value is None or value == "":
                    issues.append(f"Missing required field: {field_name}")
                    continue
            
            required_unless = field_schema.get("required_unless")
            if required_unless and value is None:
                condition_met = False
                for cond_field, cond_value in required_unless.items():
                    actual_value = data.get(cond_field)
                    if isinstance(cond_value, list):
                        if actual_value in cond_value:
                            condition_met = True
                            break
                    else:
                        if actual_value == cond_value:
                            condition_met = True
                            break
                if not condition_met:
                    cond_field = list(required_unless.keys())[0]
                    cond_value = list(required_unless.values())[0]
                    if isinstance(cond_value, list):
                        cond_str = " or ".join(cond_value)
                    else:
                        cond_str = str(cond_value)
                    issues.append(
                        f"Field '{field_name}' is required unless {cond_field} is {cond_str}"
                    )
            
            if value is not None:
                field_type = field_schema.get("type")
                type_error = self._validate_type(value, field_type, field_name)
                if type_error:
                    issues.append(type_error)
        
        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def _validate_type(self, value: Any, expected_type: str, field_name: str) -> Optional[str]:
        """Validate value matches expected type."""
        if expected_type == "string":
            if not isinstance(value, str):
                return f"Field '{field_name}' must be a string"
        elif expected_type == "semver":
            if not isinstance(value, str):
                return f"Field '{field_name}' must be a semver string"
            if not re.match(r"^\d+\.\d+\.\d+", value):
                return f"Field '{field_name}' must be semver format (e.g., 1.0.0)"
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                return f"Field '{field_name}' must be a boolean"
        elif expected_type == "object":
            if not isinstance(value, dict):
                return f"Field '{field_name}' must be an object/dict"
        return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_extractor = None
_validator = None


def _get_extractor() -> SchemaExtractor:
    global _extractor
    if _extractor is None:
        _extractor = SchemaExtractor()
    return _extractor


def _get_validator() -> SchemaValidator:
    global _validator
    if _validator is None:
        _validator = SchemaValidator()
    return _validator


def extract_tool_metadata(file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Extract tool metadata using schema-driven extraction."""
    return _get_extractor().extract(file_path, project_path)


def validate_tool_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate tool metadata against schema."""
    return _get_validator().validate(data)


def validate_extractor(file_path: Path) -> Dict[str, Any]:
    """Validate an extractor tool's structure."""
    extractor_data = Bootstrap.load_extractor(file_path)
    if not extractor_data:
        return {"valid": False, "issues": ["Failed to load extractor (missing EXTENSIONS or EXTRACTION_RULES)"]}
    return ExtractorValidator.validate(extractor_data)


def extract_and_validate(file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Extract and validate in one call."""
    data = extract_tool_metadata(file_path, project_path)
    validation = validate_tool_metadata(data)
    return {
        "data": data,
        "valid": validation["valid"],
        "issues": validation["issues"],
        "warnings": validation["warnings"],
    }
