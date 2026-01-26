"""
Content Parsing Utilities

Parses markdown files for directives, scripts, and knowledge entries.
"""

import re
import ast
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging
from kiwi_mcp.utils.xml_error_helper import format_error_with_context

logger = logging.getLogger(__name__)

# Mapping of module names to their corresponding PyPI package names
MODULE_TO_PACKAGE = {
    "git": "GitPython",
    "bs4": "beautifulsoup4",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "openai": "openai",
    "anthropic": "anthropic",
    "supabase": "supabase",
    "googleapiclient": "google-api-python-client",
    "google_auth_oauthlib": "google-auth-oauthlib",
    "requests": "requests",
    "selenium": "selenium",
}

# Mapping of package names to their corresponding import module names
PACKAGE_TO_MODULE = {v: k for k, v in MODULE_TO_PACKAGE.items()}


def parse_directive_file(file_path: Path) -> Dict[str, Any]:
    """
    Parse a directive markdown file.

    Extracts XML directive from markdown code block, validates required structure,
    and parses it into a dict with a flat permissions list.

    Returns:
        {
            "name": str,
            "version": str,
            "description": str,
            "content": str,      # Raw markdown
            "parsed": dict,      # Parsed XML structure
            "permissions": list  # [{"tag": str, "attrs": dict}, ...]
        }
    """
    content = file_path.read_text()

    # Extract XML from markdown
    xml_content = _extract_xml_from_markdown(content)
    if not xml_content:
        raise ValueError(f"No XML directive found in directive file: {file_path}")

    # Parse XML and validate required <permissions> section
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        # Use enhanced error formatting with context and suggestions
        enhanced_error = format_error_with_context(
            str(e),
            xml_content,
            str(file_path)
        )
        raise ValueError(enhanced_error)

    # Look for <permissions> inside <metadata> (required location)
    metadata_elem = root.find("metadata")
    if metadata_elem is None:
        raise ValueError(f"Directive XML is missing required <metadata> section: {file_path}")

    permissions_elem = metadata_elem.find("permissions")
    if permissions_elem is None:
        raise ValueError(
            f"Directive XML is missing required <permissions> section inside <metadata>: {file_path}"
        )

    permissions: List[Dict[str, Any]] = []
    for child in permissions_elem:
        # Skip comments or non-element nodes
        if not isinstance(child.tag, str):
            continue
        permissions.append({"tag": child.tag, "attrs": dict(child.attrib) if child.attrib else {}})

    model_elem = metadata_elem.find("model")

    if model_elem is not None:
        model_data = {
            "tier": model_elem.get("tier"),
            "fallback": model_elem.get("fallback"),
            "parallel": model_elem.get("parallel"),
            "id": model_elem.get("id"),
            "reasoning": model_elem.text.strip() if model_elem.text else None,
        }
    else:
        model_data = None

    # Extract relationships from metadata (if present)
    relationships_data = {}
    relationships_elem = metadata_elem.find("relationships")
    if relationships_elem is not None:
        for rel_type in ["requires", "suggests", "extends", "related"]:
            elements = relationships_elem.findall(rel_type)
            if elements:
                relationships_data[rel_type] = [
                    elem.get("directive") or elem.text.strip() if elem.text else None
                    for elem in elements
                ]

    # Convert full XML to nested dict
    parsed = _element_to_dict(root)

    # Expand CDATA placeholders in action elements (after parsing)
    parsed = _expand_placeholders_in_dict(parsed)

    # Extract metadata
    attrs = parsed.get("_attrs", {})
    metadata = parsed.get("metadata", {})

    # Get directive name from XML (REQUIRED - no fallback)
    if "name" not in attrs or not attrs.get("name"):
        raise ValueError(
            f"Directive XML is missing required 'name' attribute in {file_path}\n"
            f"\n"
            f"PROBLEM:\n"
            f"  The <directive> tag must have a 'name' attribute\n"
            f'  Example: <directive name="my_directive" version="1.0.0">\n'
            f"\n"
            f"SOLUTION:\n"
            f"  1. Edit {file_path}\n"
            f'  2. Add name attribute to directive tag: <directive name="{file_path.stem}" ...>\n'
            f"  3. Ensure filename matches: {file_path.name} should match the name attribute"
        )

    directive_name = attrs["name"]

    # Validate filename matches directive name
    expected_filename = f"{directive_name}.md"
    actual_filename = file_path.name

    if actual_filename != expected_filename:
        raise ValueError(
            f"Filename and directive name mismatch in {file_path}\n"
            f"\n"
            f"PROBLEM:\n"
            f"  Expected filename: {expected_filename}\n"
            f"  Actual filename: {actual_filename}\n"
            f"  XML directive name: {directive_name}\n"
            f"\n"
            f"SOLUTION (choose one):\n"
            f"  Option 1 - Rename file to match XML:\n"
            f"    mv '{file_path}' '{file_path.parent / expected_filename}'\n"
            f"\n"
            f"  Option 2 - Update XML to match filename:\n"
            f"    1. Edit {file_path}\n"
            f'    2. Change XML: <directive name="{file_path.stem}" ...>\n'
            f"    3. Run: mcp__kiwi_mcp__execute(item_type='directive', action='sign', item_id='{file_path.stem}')\n"
            f"\n"
            f"  Option 3 - Use edit_directive directive:\n"
            f"    Run directive edit_directive with directive_name='{file_path.stem}'\n"
            f"    Update XML name attribute to '{file_path.stem}' or rename file to '{expected_filename}'"
        )

    # Extract category from metadata (if present)
    category_from_xml = None
    category_elem = metadata_elem.find("category")
    if category_elem is not None and category_elem.text:
        category_from_xml = category_elem.text.strip()

    # Extract category from file path (supports nested categories)
    from kiwi_mcp.utils.paths import extract_category_path
    
    # Determine location (project or user) by checking path
    # This is a best-effort guess - handlers should pass location explicitly
    location = "project" if ".ai" in str(file_path) else "user"
    project_path = None
    if location == "project":
        # Try to find project root by looking for .ai parent
        path_parts = file_path.parts
        if ".ai" in path_parts:
            ai_index = path_parts.index(".ai")
            project_path = Path(*path_parts[:ai_index])
    
    category_from_path = extract_category_path(file_path, "directive", location, project_path)

    # Validate category consistency
    if category_from_xml and category_from_path:
        if category_from_xml != category_from_path:
            raise ValueError(
                f"Category mismatch in {file_path}\n"
                f"\n"
                f"PROBLEM:\n"
                f"  XML category: '{category_from_xml}'\n"
                f"  Path category: '{category_from_path}'\n"
                f"\n"
                f"SOLUTION (choose one):\n"
                f"  Option 1 - Update XML to match path:\n"
                f"    1. Edit {file_path}\n"
                f"    2. Change XML: <category>{category_from_path}</category>\n"
                f"    3. Run: mcp__kiwi_mcp__execute(item_type='directive', action='sign', item_id='{directive_name}')\n"
                f"\n"
                f"  Option 2 - Move file to match XML:\n"
                f"    # Build path from category: {category_from_xml}\n"
                f"    # Example: mv '{file_path}' '<project>/.ai/directives/{category_from_xml.replace('/', '/')}/{file_path.name}'\n"
                f"\n"
                f"  Option 3 - Use edit_directive directive:\n"
                f"    Run directive edit_directive with directive_name='{directive_name}'\n"
                f"    Fix mismatch (update XML or move file)"
            )
    
    # Use path category if XML category missing, otherwise use XML (validated above)
    category = category_from_path if not category_from_xml else category_from_xml

    result = {
        "name": directive_name,  # Use validated name (required, no fallback)
        "version": attrs.get("version"),  # None if missing - validator will catch it
        "description": _get_text_content(metadata.get("description", "")),
        "content": content,
        "parsed": parsed,
        "permissions": permissions,
        "model": model_data,
        "relationships": relationships_data if relationships_data else None,
        "category": category,
    }

    return result


def parse_script_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from Python script using AST parsing.

    Extracts:
    - Description from docstring
    - Dependencies from imports (auto-detected)
    - Required env vars from os.getenv/os.environ usage
    - Input parameters from argparse or function signatures
    - Tech stack from imports

    Returns:
        {
            "name": str,
            "description": str,
            "category": str,
            "dependencies": list[dict],  # [{"name": "requests", "version": None}, ...]
            "required_env_vars": list[str],
            "input_schema": dict,
            "tech_stack": list[str]
        }
    """
    # Extract category from file path (supports nested categories)
    from kiwi_mcp.utils.paths import extract_category_path
    
    # Determine location (project or user) by checking path
    location = "project" if ".ai" in str(file_path) else "user"
    project_path = None
    if location == "project":
        # Try to find project root by looking for .ai parent
        path_parts = file_path.parts
        if ".ai" in path_parts:
            ai_index = path_parts.index(".ai")
            project_path = Path(*path_parts[:ai_index])
    
    category_from_path = extract_category_path(file_path, "tool", location, project_path)
    
    metadata = {
        "name": file_path.stem,
        "description": "",
        "category": category_from_path or "utility",
        "dependencies": [],
        "required_env_vars": [],
        "input_schema": {},
        "tech_stack": [],
        "version": None,
        "tool_type": None,
        "executor_id": None,
        "config_schema": None,
    }

    try:
        content = file_path.read_text()

        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fallback to basic docstring extraction
            docstring = _extract_docstring(content)
            metadata["description"] = docstring or ""
            return metadata

        # Extract docstring (module-level)
        if tree.body and isinstance(tree.body[0], ast.Expr):
            docstring_value = tree.body[0].value
            if isinstance(docstring_value, ast.Constant) and isinstance(docstring_value.value, str):
                docstring = docstring_value.value
                # Extract description (first paragraph)
                lines = docstring.strip().split("\n")
                description_lines = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith(("Usage:", "Args:", "Dependencies:")):
                        break
                    description_lines.append(line)
                if description_lines:
                    metadata["description"] = " ".join(description_lines).strip()

        # Extract module-level constants: __version__, __tool_type__, __executor_id__, __category__, CONFIG_SCHEMA
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    if target.id == "__version__":
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            metadata["version"] = node.value.value
                    elif target.id == "__tool_type__":
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            metadata["tool_type"] = node.value.value
                    elif target.id == "__executor_id__":
                        if isinstance(node.value, ast.Constant):
                            metadata["executor_id"] = node.value.value  # Can be None or string
                    elif target.id == "__category__":
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            # Use explicit category over path-derived
                            metadata["category"] = node.value.value
                    elif target.id == "CONFIG_SCHEMA":
                        try:
                            metadata["config_schema"] = ast.literal_eval(node.value)
                        except Exception:
                            pass

        # Extract imports and dependencies
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

        # Convert imports to dependencies (filter out stdlib and internal modules)
        stdlib_modules = {
            "os",
            "sys",
            "json",
            "time",
            "datetime",
            "pathlib",
            "typing",
            "argparse",
            "logging",
            "collections",
            "itertools",
            "functools",
            "contextlib",
            "io",
            "shlex",
            "subprocess",
            "importlib",
            "hashlib",
            "re",
            "math",
            "random",
            "string",
            "urllib",
            "http",
            "email",
            "concurrent",
            "threading",
            "multiprocessing",
            "asyncio",
            "queue",
        }
        # Internal kiwi-mcp modules (not pip packages)
        internal_modules = {"lib"}

        skip_modules = stdlib_modules | internal_modules
        external_deps = [imp for imp in set(imports) if imp not in skip_modules]
        metadata["dependencies"] = [
            {"name": MODULE_TO_PACKAGE.get(dep, dep), "version": None} for dep in external_deps
        ]
        metadata["tech_stack"] = list(
            set([MODULE_TO_PACKAGE.get(dep, dep) for dep in external_deps])
        )

        # Extract required env vars (look for os.getenv, os.environ patterns)
        env_vars = set()
        for node in ast.walk(tree):
            # Look for os.getenv() calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if (
                        node.func.attr == "getenv"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"
                    ):
                        if (
                            node.args
                            and isinstance(node.args[0], ast.Constant)
                            and isinstance(node.args[0].value, str)
                        ):
                            env_vars.add(node.args[0].value)

        metadata["required_env_vars"] = sorted(list(env_vars))

    except Exception as e:
        logger.warning(f"Failed to extract metadata from {file_path}: {e}")

    return metadata


def parse_knowledge_entry(file_path: Path) -> Dict[str, Any]:
    """
    Parse a knowledge entry markdown file with YAML frontmatter.

    Returns:
        {
            "zettel_id": str,
            "title": str,
            "content": str,
            "entry_type": str,
            "category": str,
            "tags": list
        }
    """
    content = file_path.read_text()

    # Skip signature line at top if present (HTML comment format)
    content_without_sig = re.sub(r"^<!-- kiwi-mcp:validated:[^>]+-->\n", "", content)

    # Parse YAML frontmatter
    frontmatter = _extract_yaml_frontmatter(content_without_sig)

    # Extract content (after frontmatter)
    content_start = content_without_sig.find("---", 3) + 3 if content_without_sig.startswith("---") else 0
    entry_content = content_without_sig[content_start:].strip()

    # Get zettel_id from frontmatter (fallback to filename stem if not present)
    zettel_id = frontmatter.get("zettel_id", file_path.stem)

    # Validate filename matches zettel_id
    expected_filename = f"{zettel_id}.md"
    actual_filename = file_path.name

    if actual_filename != expected_filename:
        raise ValueError(
            f"Filename and zettel_id mismatch in {file_path}\n"
            f"\n"
            f"PROBLEM:\n"
            f"  Expected filename: {expected_filename}\n"
            f"  Actual filename: {actual_filename}\n"
            f"  Frontmatter zettel_id: {zettel_id}\n"
            f"\n"
            f"SOLUTION (choose one):\n"
            f"  Option 1 - Rename file to match frontmatter:\n"
            f"    mv '{file_path}' '{file_path.parent / expected_filename}'\n"
            f"\n"
            f"  Option 2 - Update frontmatter to match filename:\n"
            f"    1. Edit {file_path}\n"
            f"    2. Change frontmatter: zettel_id: {file_path.stem}\n"
            f"    3. Run: mcp__kiwi_mcp__execute(item_type='knowledge', action='sign', item_id='{file_path.stem}')\n"
            f"\n"
            f"  Option 3 - Use edit_knowledge directive:\n"
            f"    Run directive edit_knowledge with zettel_id='{file_path.stem}'\n"
            f"    Update frontmatter zettel_id to '{file_path.stem}' or rename file to '{expected_filename}'"
        )

    # Extract category from frontmatter
    category_from_frontmatter = frontmatter.get("category", "")
    
    # Extract category from file path (supports nested categories)
    from kiwi_mcp.utils.paths import extract_category_path
    
    # Determine location (project or user) by checking path
    location = "project" if ".ai" in str(file_path) else "user"
    project_path = None
    if location == "project":
        # Try to find project root by looking for .ai parent
        path_parts = file_path.parts
        if ".ai" in path_parts:
            ai_index = path_parts.index(".ai")
            project_path = Path(*path_parts[:ai_index])
    
    category_from_path = extract_category_path(file_path, "knowledge", location, project_path)

    # Validate category consistency
    if category_from_frontmatter and category_from_path:
        if category_from_frontmatter != category_from_path:
            raise ValueError(
                f"Category mismatch in {file_path}\n"
                f"\n"
                f"PROBLEM:\n"
                f"  Frontmatter category: '{category_from_frontmatter}'\n"
                f"  Path category: '{category_from_path}'\n"
                f"\n"
                f"SOLUTION (choose one):\n"
                f"  Option 1 - Update frontmatter to match path:\n"
                f"    1. Edit {file_path}\n"
                f"    2. Change frontmatter: category: {category_from_path}\n"
                f"    3. Run: mcp__kiwi_mcp__execute(item_type='knowledge', action='sign', item_id='{zettel_id}')\n"
                f"\n"
                f"  Option 2 - Move file to match frontmatter:\n"
                f"    # Build path from category: {category_from_frontmatter}\n"
                f"    # Example: mv '{file_path}' '<project>/.ai/knowledge/{category_from_frontmatter.replace('/', '/')}/{file_path.name}'\n"
                f"\n"
                f"  Option 3 - Use edit_knowledge directive:\n"
                f"    Run directive edit_knowledge with zettel_id='{zettel_id}'\n"
                f"    Fix mismatch (update frontmatter or move file)"
            )
    
    # Use path category if frontmatter category missing, otherwise use frontmatter (validated above)
    category = category_from_path if not category_from_frontmatter else category_from_frontmatter

    return {
        "zettel_id": zettel_id,
        "title": frontmatter.get("title", file_path.stem),
        "content": entry_content,
        "entry_type": frontmatter.get("entry_type", "learning"),
        "category": category,
        "tags": frontmatter.get("tags", []),
        "version": frontmatter.get("version"),  # None if missing; validator requires it
    }


def _extract_xml_from_markdown(content: str) -> Optional[str]:
    """Extract XML directive from markdown."""
    start_pattern = r"<directive[^>]*>"
    start_match = re.search(start_pattern, content)
    if not start_match:
        return None

    start_idx = start_match.start()
    end_tag = "</directive>"
    end_idx = content.rfind(end_tag)
    if end_idx == -1 or end_idx < start_idx:
        return None

    return content[start_idx : end_idx + len(end_tag)].strip()


def _parse_xml_to_dict(xml_content: str) -> Dict[str, Any]:
    """Parse XML string to dictionary."""
    try:
        root = ET.fromstring(xml_content)
        return _element_to_dict(root)
    except ET.ParseError as e:
        logger.warning(f"XML parse error: {e}")
        return {}


def _expand_cdata_placeholders(text: str) -> str:
    """
    Replace CDATA placeholders with actual CDATA markers.

    These placeholders allow showing CDATA examples in CDATA content,
    working around the XML limitation that CDATA sections cannot be nested.
    """
    text = text.replace("{CDATA_OPEN}", "<![CDATA[")
    text = text.replace("{CDATA_CLOSE}", "]]>")
    return text


def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
    """Convert XML element to dict."""
    result = {}

    if element.text and element.text.strip():
        result["_text"] = element.text.strip()

    if element.attrib:
        result["_attrs"] = dict(element.attrib)

    for child in element:
        tag = child.tag
        child_dict = _element_to_dict(child)

        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_dict)
        else:
            result[tag] = child_dict

    if len(result) == 1 and "_text" in result:
        return result["_text"]

    return result


def _expand_placeholders_in_dict(data: Any) -> Any:
    """
    Recursively expand CDATA placeholders in action elements.

    This is applied AFTER XML parsing to expand {CDATA_OPEN} and {CDATA_CLOSE}
    placeholders in action element text content.
    """
    if isinstance(data, str):
        return _expand_cdata_placeholders(data)
    elif isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Expand placeholders in action element text content
            if key == "action" and isinstance(value, (str, dict)):
                if isinstance(value, str):
                    result[key] = _expand_cdata_placeholders(value)
                elif isinstance(value, dict) and "_text" in value:
                    result[key] = value.copy()
                    result[key]["_text"] = _expand_cdata_placeholders(value["_text"])
                else:
                    result[key] = _expand_placeholders_in_dict(value)
            else:
                result[key] = _expand_placeholders_in_dict(value)
        return result
    elif isinstance(data, list):
        return [_expand_placeholders_in_dict(item) for item in data]
    else:
        return data


def _get_text_content(value: Any) -> str:
    """Extract text content from parsed XML value."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("_text", "")
    return ""


def _extract_docstring(content: str) -> Optional[str]:
    """Extract module docstring from Python code."""
    match = re.search(r'^\s*"""(.+?)"""', content, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^\s*'''(.+?)'''", content, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _extract_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown."""
    if not content.startswith("---"):
        return {}

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}

    yaml_content = content[3:end_idx].strip()

    # Use proper YAML parsing to handle arrays, quoted strings, etc.
    try:
        import yaml
        result = yaml.safe_load(yaml_content) or {}
        return result
    except Exception:
        # Fallback to simple parser if YAML parsing fails
        result = {}
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result
