# Phase 1 Complete: Kernel Minimization Summary

## Changes Made to `/home/leo/projects/kiwi-mcp/kiwi_mcp/schemas/tool_schema.py`

### 1. Removed Imports
- Removed `import ast` (no longer needed)
- Removed `import yaml` (no longer needed)

### 2. Updated Parsers Section
- **BUILTIN_PARSERS**: Now only contains `"text": _parse_text` (removed yaml and python_ast)
- **Dynamic Loading**: Enhanced `_load_parser()` and `get_parser()` functions to load parsers from `.ai/parsers/` directories
- **Caching**: Added `_loaded_parsers` dict to cache dynamically loaded parsers

### 3. Updated Primitives
**Removed primitives:**
- `ast_var` - extracted module-level variables from Python AST
- `ast_docstring` - extracted module docstrings from Python AST

**Added primitives:**
- `regex_all` - extracts all regex matches (not just the first one)
- `category_path` - extracts category from parent directory name

**Final PRIMITIVES dict:**
```python
PRIMITIVES = {
    "filename": _extract_filename,
    "regex": _extract_regex,
    "regex_all": _extract_regex_all,
    "path": _extract_path,
    "category_path": _extract_category_from_path,
}
```

### 4. Bootstrap Class Updates
- Replaced AST-based module parsing with regex-based parsing to avoid `ast` dependency
- Still able to extract EXTENSIONS, PARSER, SIGNATURE_FORMAT, and EXTRACTION_RULES variables

### 5. Validator Updates
- `ExtractorValidator`: Updated to use dynamic parser validation (no longer checks against static PARSERS dict)
- Added validation for `regex_all` primitive requiring "pattern" parameter
- Removed validation for removed AST primitives

### 6. SchemaExtractor Updates
- Updated to use `get_parser(parser_name, project_path)` instead of accessing PARSERS dict directly
- This enables dynamic loading of parsers from `.ai/parsers/` directories

### 7. Fixed Type Issues
- Fixed Optional type annotations in `SchemaValidator.__init__`
- Added null checks in `_validate_type` method
- All LSP errors resolved

## Verification
✅ File compiles without syntax errors
✅ All imports work correctly
✅ BUILTIN_PARSERS contains only "text" parser
✅ PRIMITIVES contains the 5 required primitives
✅ Dynamic parser loading works with fallback to text parser
✅ All LSP errors resolved

## Kernel Successfully Minimized
The kernel has been stripped to the absolute minimum while maintaining:
- Core text parsing capability
- Dynamic extensibility through `.ai/parsers/` directory
- Essential extraction primitives (filename, regex, regex_all, path, category_path)
- Full validation and bootstrap functionality

Ready for Phase 2: RYE Parser Implementation.