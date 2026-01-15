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

logger = logging.getLogger(__name__)

# Mapping of module names to their corresponding PyPI package names
MODULE_TO_PACKAGE = {
    'git': 'GitPython',
    'bs4': 'beautifulsoup4',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'sklearn': 'scikit-learn',
    'cv2': 'opencv-python',
    'PIL': 'Pillow',
    'openai': 'openai',
    'anthropic': 'anthropic',
    'supabase': 'supabase',
    'googleapiclient': 'google-api-python-client',
    'google_auth_oauthlib': 'google-auth-oauthlib',
    'requests': 'requests',
    'selenium': 'selenium',
}

# Mapping of package names to their corresponding import module names
PACKAGE_TO_MODULE = {v: k for k, v in MODULE_TO_PACKAGE.items()}


def parse_directive_file(file_path: Path) -> Dict[str, Any]:
    """
    Parse a directive markdown file.
    
    Extracts XML directive from markdown code block and parses to dict.
    
    Returns:
        {
            "name": str,
            "version": str,
            "description": str,
            "content": str,  # Raw markdown
            "parsed": dict  # Parsed XML structure
        }
    """
    content = file_path.read_text()
    
    # Extract XML from markdown
    xml_content = _extract_xml_from_markdown(content)
    if not xml_content:
        return {
            "name": file_path.stem,
            "version": "0.0.0",
            "description": "",
            "content": content,
            "parsed": {}
        }
    
    # Parse XML to dict
    parsed = _parse_xml_to_dict(xml_content)
    
    # Extract metadata
    attrs = parsed.get("_attrs", {})
    metadata = parsed.get("metadata", {})
    
    return {
        "name": attrs.get("name", file_path.stem),
        "version": attrs.get("version", "0.0.0"),
        "description": _get_text_content(metadata.get("description", "")),
        "content": content,
        "parsed": parsed
    }


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
    metadata = {
        "name": file_path.stem,
        "description": "",
        "category": "utility",
        "dependencies": [],
        "required_env_vars": [],
        "input_schema": {},
        "tech_stack": []
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
                lines = docstring.strip().split('\n')
                description_lines = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith(('Usage:', 'Args:', 'Dependencies:')):
                        break
                    description_lines.append(line)
                if description_lines:
                    metadata["description"] = ' '.join(description_lines).strip()
        
        # Extract imports and dependencies
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split('.')[0])
        
        # Convert imports to dependencies (filter out stdlib and internal modules)
        stdlib_modules = {
            'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'typing',
            'argparse', 'logging', 'collections', 'itertools', 'functools',
            'contextlib', 'io', 'shlex', 'subprocess', 'importlib', 'hashlib',
            're', 'math', 'random', 'string', 'urllib', 'http', 'email',
            'concurrent', 'threading', 'multiprocessing', 'asyncio', 'queue'
        }
        # Internal kiwi-mcp modules (not pip packages)
        internal_modules = {'lib'}
        
        skip_modules = stdlib_modules | internal_modules
        external_deps = [imp for imp in set(imports) if imp not in skip_modules]
        metadata["dependencies"] = [
            {"name": MODULE_TO_PACKAGE.get(dep, dep), "version": None} 
            for dep in external_deps
        ]
        metadata["tech_stack"] = list(set([MODULE_TO_PACKAGE.get(dep, dep) for dep in external_deps]))
        
        # Extract required env vars (look for os.getenv, os.environ patterns)
        env_vars = set()
        for node in ast.walk(tree):
            # Look for os.getenv() calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'getenv' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
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
    
    # Parse YAML frontmatter
    frontmatter = _extract_yaml_frontmatter(content)
    
    # Extract content (after frontmatter)
    content_start = content.find("---", 3) + 3 if content.startswith("---") else 0
    entry_content = content[content_start:].strip()
    
    return {
        "zettel_id": frontmatter.get("zettel_id", file_path.stem),
        "title": frontmatter.get("title", file_path.stem),
        "content": entry_content,
        "entry_type": frontmatter.get("entry_type", "learning"),
        "category": frontmatter.get("category", ""),
        "tags": frontmatter.get("tags", [])
    }


def _extract_xml_from_markdown(content: str) -> Optional[str]:
    """Extract XML directive from markdown."""
    start_pattern = r'<directive[^>]*>'
    start_match = re.search(start_pattern, content)
    if not start_match:
        return None
    
    start_idx = start_match.start()
    end_tag = '</directive>'
    end_idx = content.rfind(end_tag)
    if end_idx == -1 or end_idx < start_idx:
        return None
    
    return content[start_idx:end_idx + len(end_tag)].strip()


def _parse_xml_to_dict(xml_content: str) -> Dict[str, Any]:
    """Parse XML string to dictionary."""
    try:
        root = ET.fromstring(xml_content)
        return _element_to_dict(root)
    except ET.ParseError as e:
        logger.warning(f"XML parse error: {e}")
        return {}


def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
    """Convert XML element to dict."""
    result = {}
    
    if element.text and element.text.strip():
        result['_text'] = element.text.strip()
    
    if element.attrib:
        result['_attrs'] = dict(element.attrib)
    
    for child in element:
        tag = child.tag
        child_dict = _element_to_dict(child)
        
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_dict)
        else:
            result[tag] = child_dict
    
    if len(result) == 1 and '_text' in result:
        return result['_text']
    
    return result


def _get_text_content(value: Any) -> str:
    """Extract text content from parsed XML value."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get('_text', '')
    return ''


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
    
    # Simple YAML parser (only supports basic key: value)
    result = {}
    for line in yaml_content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    
    return result
