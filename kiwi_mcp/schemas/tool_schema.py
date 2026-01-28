"""
Schema-driven extraction and validation engine.

Architecture:
1. BOOTSTRAP - Loads extractor tools (reads EXTENSIONS, PARSER, EXTRACTION_RULES)
2. PARSERS - Minimal preprocessors (text with dynamic loading from .ai/parsers/)
3. PRIMITIVES - Generic extraction functions (filename, regex, regex_all, path, category_path)
4. VALIDATION - Validates tools and extractors

Extractors define WHAT to extract and HOW via schema rules.
The engine provides only generic primitives.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============================================================================
# PARSERS - Minimal preprocessors for different file types
# =============================================================================


def _parse_text(content: str) -> Dict[str, Any]:
    """Raw text - no preprocessing."""
    return {"content": content}


# Dynamic parser loading
_loaded_parsers: Dict[str, Any] = {}


def _load_parser(name: str, project_path: Optional[Path] = None):
    """Load a parser from .ai/parsers/ directories."""
    from kiwi_mcp.utils.resolvers import get_user_space

    search_paths = [
        project_path / ".ai" / "parsers" if project_path else None,
        Path.cwd() / ".ai" / "parsers",
        get_user_space() / "parsers",
    ]

    for p in filter(None, search_paths):
        f = p / f"{name}.py"
        if f.exists():
            code = f.read_text()
            ns = {"__builtins__": __builtins__}
            exec(code, ns)
            if "parse" in ns:
                _loaded_parsers[name] = ns["parse"]
                return


def get_parser(name: str, project_path: Optional[Path] = None):
    """Get parser by name, loading from RYE if needed."""
    # Check builtin first
    if name == "text":
        return _parse_text

    # Check loaded parsers
    if name not in _loaded_parsers:
        _load_parser(name, project_path)

    # Return loaded parser or fallback to text
    return _loaded_parsers.get(name, _parse_text)


# Keep only text parser as builtin
BUILTIN_PARSERS = {
    "text": _parse_text,
}

# Legacy alias for compatibility
PARSERS = BUILTIN_PARSERS


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


def _extract_regex_all(rule: Dict, parsed: Dict, file_path: Path) -> Optional[List[str]]:
    """Extract all values matching regex pattern."""
    content = parsed.get("content", "")
    pattern = rule.get("pattern")
    if not pattern:
        return None

    flags = re.MULTILINE if rule.get("multiline") else 0
    matches = re.findall(pattern, content, flags)
    if matches:
        return [m.strip() if isinstance(m, str) else m for m in matches]
    return None


def _extract_category_from_path(rule: Dict, parsed: Dict, file_path: Path) -> Optional[str]:
    """Extract category from file path (parent directory name)."""
    return file_path.parent.name if file_path.parent.name else None


PRIMITIVES = {
    "filename": _extract_filename,
    "regex": _extract_regex,
    "regex_all": _extract_regex_all,
    "path": _extract_path,
    "category_path": _extract_category_from_path,
}


# =============================================================================
# BOOTSTRAP - Loads extractor tools
# =============================================================================


class Bootstrap:
    """Load extractor tools by reading their module variables."""

    @staticmethod
    def load_extractor(file_path: Path, item_type: str = "tool") -> Optional[Dict[str, Any]]:
        """
        Load an extractor tool's EXTENSIONS, PARSER, SIGNATURE_FORMAT, EXTRACTION_RULES,
        VALIDATION_SCHEMA, and SEARCH_FIELDS.
        Uses exec() to properly handle multi-line dict definitions.
        """
        try:
            content = file_path.read_text()
            
            # Execute the file to get module-level variables
            namespace: Dict[str, Any] = {}
            exec(content, namespace)
            
            extensions = namespace.get("EXTENSIONS")
            parser = namespace.get("PARSER", "text")
            signature_format = namespace.get("SIGNATURE_FORMAT")
            rules = namespace.get("EXTRACTION_RULES")
            validation_schema = namespace.get("VALIDATION_SCHEMA")
            search_fields = namespace.get("SEARCH_FIELDS")

            if extensions and rules:
                return {
                    "extensions": extensions,
                    "parser": parser,
                    "signature_format": signature_format or {"prefix": "#", "after_shebang": True},
                    "rules": rules,
                    "validation_schema": validation_schema,
                    "search_fields": search_fields,
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
        # Since we have dynamic parser loading, we just validate it's a string
        if not isinstance(parser, str):
            issues.append(f"PARSER must be a string, got {type(parser).__name__}")

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
                if rule_type == "regex_all" and "pattern" not in rule:
                    issues.append(f"Rule '{field_name}' (regex_all) requires 'pattern'")
                if rule_type == "path" and "key" not in rule:
                    issues.append(f"Rule '{field_name}' (path) requires 'key'")

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
        "requires": {"required": False, "type": "list_of_strings"},
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
        self._extractors: Dict[tuple, Dict] = {}  # (item_type, ext) -> {parser, rules}
        self._loaded_types: set = set()  # Track which item_types have been loaded

    def _load_extractors(self, item_type: str = "tool", project_path: Optional[Path] = None):
        """Load extractor tools for a specific item type."""
        if item_type in self._loaded_types:
            return

        search_paths = []
        if project_path:
            search_paths.append(project_path / ".ai" / "extractors" / item_type)
        search_paths.append(Path.cwd() / ".ai" / "extractors" / item_type)

        from kiwi_mcp.utils.resolvers import get_user_space

        search_paths.append(get_user_space() / "extractors" / item_type)

        for extractors_dir in search_paths:
            if extractors_dir.exists():
                for file_path in extractors_dir.glob("*.py"):
                    if file_path.name.startswith("_"):
                        continue

                    extractor_data = Bootstrap.load_extractor(file_path, item_type)
                    if extractor_data:
                        validation = ExtractorValidator.validate(extractor_data)
                        if validation["valid"]:
                            for ext in extractor_data["extensions"]:
                                self._extractors[(item_type, ext.lower())] = {
                                    "parser": extractor_data["parser"],
                                    "rules": extractor_data["rules"],
                                    "validation_schema": extractor_data.get("validation_schema"),
                                    "search_fields": extractor_data.get("search_fields"),
                                }

        self._loaded_types.add(item_type)

    def extract(
        self, file_path: Path, item_type: str = "tool", project_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Extract metadata using dynamically loaded rules."""
        self._load_extractors(item_type, project_path)

        ext = file_path.suffix.lower()
        extractor = self._extractors.get((item_type, ext))

        if not extractor:
            raise ValueError(
                f"No extractor found for extension '{ext}'. "
                f"Available: {list(self._extractors.keys())}"
            )

        content = file_path.read_text()

        # Use the extractor's parser with dynamic loading
        parser_name = extractor["parser"]
        parser_func = get_parser(parser_name, project_path)
        parsed = parser_func(content)

        # Apply extraction rules
        result = {}
        for field, rule in extractor["rules"].items():
            primitive = PRIMITIVES.get(rule["type"])
            if primitive:
                result[field] = primitive(rule, parsed, file_path)
            else:
                result[field] = None

        # Add path-derived category for validation
        result["_path_category"] = _extract_category_from_path(
            {"base_folder": f"{item_type}s" if item_type != "knowledge" else "knowledge"},
            parsed,
            file_path
        )
        result["_file_path"] = file_path
        result["_item_type"] = item_type

        return result

    def get_supported_extensions(
        self, item_type: str = "tool", project_path: Optional[Path] = None
    ) -> List[str]:
        """Get list of supported file extensions."""
        self._load_extractors(item_type, project_path)
        return [ext for (itype, ext) in self._extractors.keys() if itype == item_type]

    def get_validation_schema(
        self, file_path: Path, item_type: str = "tool", project_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """Get validation schema for a file type."""
        self._load_extractors(item_type, project_path)
        ext = file_path.suffix.lower()
        extractor = self._extractors.get((item_type, ext))
        if extractor:
            return extractor.get("validation_schema")
        return None

    def get_search_fields(
        self, file_path: Path, item_type: str = "tool", project_path: Optional[Path] = None
    ) -> Dict[str, float]:
        """
        Get search fields with weights for a file type.
        
        Returns explicit SEARCH_FIELDS from extractor, or derives defaults
        from EXTRACTION_RULES and VALIDATION_SCHEMA.
        """
        self._load_extractors(item_type, project_path)
        ext = file_path.suffix.lower()
        extractor = self._extractors.get((item_type, ext))
        
        if not extractor:
            return {}
        
        # Use explicit SEARCH_FIELDS if defined
        explicit_fields = extractor.get("search_fields")
        if explicit_fields:
            # Normalize: accept both float and {"weight": float} forms
            return {
                k: (v if isinstance(v, (int, float)) else v.get("weight", 1.0))
                for k, v in explicit_fields.items()
            }
        
        # Derive defaults from schema
        return self._derive_search_fields(extractor)

    def _derive_search_fields(self, extractor: Dict) -> Dict[str, float]:
        """
        Derive search fields from EXTRACTION_RULES and VALIDATION_SCHEMA.
        
        Uses type information to exclude structural fields and applies
        default weights based on field names.
        """
        # Default weights by field name (kernel-owned)
        DEFAULT_WEIGHTS = {
            "name": 5.0,
            "title": 5.0,
            "description": 2.0,
            "summary": 2.0,
            "category": 1.5,
            "tags": 1.5,
            "entry_type": 1.5,
            "content": 1.0,
            "body": 1.0,
        }
        
        # Types to exclude from search
        EXCLUDE_TYPES = {"object", "array", "semver", "number", "boolean"}
        
        # Fields to exclude by name (structural/metadata)
        EXCLUDE_NAMES = {
            "version", "author", "model", "permissions", "cost",
            "created_at", "updated_at", "id", "backlinks", "attachments",
            "source_url", "source_type", "inputs", "outputs", "process",
            "config", "config_schema", "env_config", "mutates_state",
            "extensions", "extraction_rules", "validation", "executor_id",
            "tool_type",
        }
        
        rules = extractor.get("rules", {})
        validation = extractor.get("validation_schema", {})
        field_schemas = validation.get("fields", {}) if validation else {}
        
        result = {}
        for field_name in rules.keys():
            # Skip internal/excluded fields
            if field_name.startswith("_") or field_name in EXCLUDE_NAMES:
                continue
            
            # Check validation type if available
            field_schema = field_schemas.get(field_name, {})
            field_type = field_schema.get("type", "string")
            if field_type in EXCLUDE_TYPES:
                continue
            
            # Apply weight from defaults or fallback
            weight = DEFAULT_WEIGHTS.get(field_name, 1.0)
            result[field_name] = weight
        
        return result


# =============================================================================
# SCHEMA VALIDATOR
# =============================================================================


class SchemaValidator:
    """Validates extracted tool data."""

    def __init__(self, schema: Optional[Dict[str, Any]] = None):
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
                if field_type:
                    type_error = self._validate_type(value, field_type, field_name)
                    if type_error:
                        issues.append(type_error)

        # Validate category matches path
        metadata_category = data.get("category")
        path_category = data.get("_path_category")
        if metadata_category and path_category is not None and metadata_category != path_category:
            issues.append(
                f"Category mismatch: metadata declares '{metadata_category}' "
                f"but file is at '{path_category or '(root)'}'"
            )

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
        elif expected_type == "list_of_strings":
            if not isinstance(value, list):
                return f"Field '{field_name}' must be a list"
            for item in value:
                if not isinstance(item, str):
                    return (
                        f"Field '{field_name}' must contain only strings, got {type(item).__name__}"
                    )
                if "." not in item:
                    return f"Field '{field_name}' capability '{item}' must follow resource.action format (e.g., fs.read)"
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


def extract_tool_metadata(
    file_path: Path, item_type: str = "tool", project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Extract tool metadata using schema-driven extraction."""
    return _get_extractor().extract(file_path, item_type, project_path)


def validate_tool_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate tool metadata against schema."""
    return _get_validator().validate(data)


def validate_extractor(file_path: Path) -> Dict[str, Any]:
    """Validate an extractor tool's structure."""
    extractor_data = Bootstrap.load_extractor(file_path)
    if not extractor_data:
        return {
            "valid": False,
            "issues": ["Failed to load extractor (missing EXTENSIONS or EXTRACTION_RULES)"],
        }
    return ExtractorValidator.validate(extractor_data)


def extract_and_validate(
    file_path: Path, item_type: str = "tool", project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Extract and validate in one call."""
    extractor = _get_extractor()
    data = extractor.extract(file_path, item_type, project_path)
    schema = extractor.get_validation_schema(file_path, item_type, project_path)
    validator = SchemaValidator(schema) if schema else _get_validator()
    validation = validator.validate(data)
    return {
        "data": data,
        "valid": validation["valid"],
        "issues": validation["issues"],
        "warnings": validation["warnings"],
    }


def search_items(
    item_type: str,
    query: str,
    search_paths: List[Path],
    project_path: Optional[Path] = None,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search for items using schema-driven BM25 ranking.
    
    Architecture:
    1. Extract metadata from files using SchemaExtractor
    2. Get search fields from extractor's SEARCH_FIELDS or derive defaults
    3. Index documents into KeywordSearchEngine with weighted fields
    4. Search and return ranked results
    
    Args:
        item_type: "directive", "tool", or "knowledge"
        query: Search query string
        search_paths: List of directories to search
        project_path: Project root for extractor resolution
        filters: Optional filters (category, entry_type, tags, etc.)
        limit: Maximum results to return
    
    Returns:
        List of matching items with scores
    """
    from kiwi_mcp.utils.search.keyword import KeywordSearchEngine
    
    filters = filters or {}
    extractor = _get_extractor()
    engine = KeywordSearchEngine()
    
    # Phase 1: Extract and index all matching files
    indexed_data: Dict[str, Dict[str, Any]] = {}  # item_id -> extracted data
    
    for search_dir in search_paths:
        if not search_dir.exists():
            continue
            
        extensions = extractor.get_supported_extensions(item_type, project_path)
        for ext in extensions:
            for file_path in search_dir.rglob(f"*{ext}"):
                try:
                    data = extractor.extract(file_path, item_type, project_path)
                    
                    # Apply filters early to avoid indexing filtered items
                    if not _matches_filters(data, filters):
                        continue
                    
                    # Get search fields for this file type
                    search_fields = extractor.get_search_fields(file_path, item_type, project_path)
                    
                    # Build indexable fields from extracted data
                    fields = _build_search_fields(data, search_fields)
                    
                    # Generate unique item ID
                    item_id = str(file_path)
                    
                    # Index the document with schema-driven field weights
                    engine.index_document(
                        item_id=item_id,
                        item_type=item_type,
                        fields=fields,
                        path=file_path,
                        metadata=data,
                        field_weights=search_fields,
                    )
                    
                    # Store for result building
                    indexed_data[item_id] = data
                    
                except Exception:
                    continue
    
    # Phase 2: Search if query provided, else return all indexed items
    if query:
        search_results = engine.search(query, item_type=item_type, limit=limit, min_score=0.0)
        return [
            {
                **{k: v for k, v in indexed_data[r.item_id].items() if not k.startswith("_")},
                "score": r.score,
                "path": str(r.path),
            }
            for r in search_results
            if r.item_id in indexed_data
        ]
    else:
        # No query: return all items with score 1.0
        return [
            {
                **{k: v for k, v in data.items() if not k.startswith("_")},
                "score": 1.0,
                "path": item_id,
            }
            for item_id, data in list(indexed_data.items())[:limit]
        ]


def _build_search_fields(data: Dict[str, Any], search_fields: Dict[str, float]) -> Dict[str, str]:
    """
    Build indexable text fields from extracted data using schema-driven field selection.
    
    Args:
        data: Extracted metadata
        search_fields: Field names with weights from extractor
    
    Returns:
        Dictionary of field_name -> text content for indexing
    """
    result = {}
    for field_name in search_fields.keys():
        value = data.get(field_name)
        if value is None:
            result[field_name] = ""
        elif isinstance(value, str):
            result[field_name] = value
        elif isinstance(value, list):
            result[field_name] = " ".join(str(v) for v in value if v)
        else:
            result[field_name] = str(value)
    return result


def _matches_filters(data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Check if data matches all filters."""
    for key, value in filters.items():
        if value is None:
            continue
        data_value = data.get(key)
        if isinstance(value, list):
            if data_value not in value:
                return False
        elif data_value != value:
            return False
    return True
