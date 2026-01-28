"""
Content Parsing Utilities

Thin wrappers for parsing markdown files using SchemaExtractor.
"""

import re
import ast
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging
from kiwi_mcp.schemas.tool_schema import SchemaExtractor

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

# Schema extractor singleton
_extractor = None


def _get_extractor() -> SchemaExtractor:
    """Get or create singleton extractor."""
    global _extractor
    if _extractor is None:
        _extractor = SchemaExtractor()
    return _extractor


def parse_directive_file(file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Parse directive file using extractor."""
    return _get_extractor().extract(file_path, "directive", project_path)


def parse_knowledge_file(file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Parse knowledge file using extractor."""
    return _get_extractor().extract(file_path, "knowledge", project_path)


def parse_knowledge_entry(file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Parse knowledge file using extractor. Backward compatibility alias."""
    return parse_knowledge_file(file_path, project_path)


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
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            metadata["version"] = node.value.value
                    elif target.id == "__tool_type__":
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            metadata["tool_type"] = node.value.value
                    elif target.id == "__executor_id__":
                        if isinstance(node.value, ast.Constant):
                            metadata["executor_id"] = node.value.value  # Can be None or string
                    elif target.id == "__category__":
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
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


def _extract_docstring(content: str) -> Optional[str]:
    """Extract module docstring from Python code."""
    match = re.search(r'^\s*"""(.+?)"""', content, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^\s*'''(.+?)'''", content, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None
