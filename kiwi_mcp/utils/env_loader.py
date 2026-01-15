"""
Environment Variable Loader for Kiwi MCP

Loads environment variables from .env files in a hierarchical manner:
1. Userspace (.ai/.env) - base defaults
2. Project space (.ai/.env) - project-specific overrides

This follows the principle of least surprise:
- Userspace provides sensible defaults for all projects
- Project space can override specific values
- Runtime environment takes precedence over both
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from kiwi_mcp.utils.logger import get_logger
from kiwi_mcp.utils.resolvers import get_user_space

logger = get_logger("env_loader")


def parse_env_file(filepath: Path) -> Dict[str, str]:
    """
    Parse a .env file into a dict of key-value pairs.
    
    Supports:
    - Basic KEY=value
    - KEY="quoted value"
    - KEY='single quoted'
    - # comments
    - Empty lines
    - Inline comments after values
    
    Args:
        filepath: Path to .env file
        
    Returns:
        Dict of environment variables
    """
    if not filepath.exists():
        return {}
    
    env_vars = {}
    
    try:
        content = filepath.read_text(encoding='utf-8')
        
        for line_num, line in enumerate(content.splitlines(), 1):
            # Skip empty lines and comments
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=value
            if '=' not in line:
                continue
            
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            
            # Validate key name
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                logger.warning(f"{filepath}:{line_num} - Invalid key: {key}")
                continue
            
            # Strip quotes and handle inline comments
            if value.startswith('"') and '"' in value[1:]:
                # Double quoted - find closing quote
                end_quote = value.index('"', 1)
                value = value[1:end_quote]
            elif value.startswith("'") and "'" in value[1:]:
                # Single quoted - find closing quote
                end_quote = value.index("'", 1)
                value = value[1:end_quote]
            else:
                # Unquoted - strip inline comments
                if ' #' in value:
                    value = value[:value.index(' #')].strip()
            
            env_vars[key] = value
            
    except Exception as e:
        logger.warning(f"Error parsing {filepath}: {e}")
    
    return env_vars


def load_env_hierarchy(
    project_path: Optional[Path] = None,
    include_runtime: bool = True
) -> Tuple[Dict[str, str], List[str]]:
    """
    Load environment variables from .env files in order of precedence.
    
    Loading order (later overrides earlier):
    1. Userspace: ~/.ai/.env
    2. Project space: <project>/.ai/.env
    3. Runtime environment (os.environ) if include_runtime=True
    
    Args:
        project_path: Optional project path for project-level .env
        include_runtime: Whether to include os.environ (default True)
        
    Returns:
        Tuple of (merged_env_dict, list_of_loaded_files)
    """
    user_space = get_user_space()
    merged = {}
    loaded_files = []
    
    # 1. Userspace .env (base defaults)
    userspace_env = user_space / ".env"
    if userspace_env.exists():
        user_vars = parse_env_file(userspace_env)
        merged.update(user_vars)
        loaded_files.append(str(userspace_env))
        logger.info(f"Loaded {len(user_vars)} vars from {userspace_env}")
    
    # 2. Project space .env (project overrides)
    if project_path:
        project_env = Path(project_path) / ".ai" / ".env"
        if project_env.exists():
            project_vars = parse_env_file(project_env)
            merged.update(project_vars)
            loaded_files.append(str(project_env))
            logger.info(f"Loaded {len(project_vars)} vars from {project_env}")
    
    # 3. Runtime environment (highest precedence)
    if include_runtime:
        merged.update(dict(os.environ))
    
    return merged, loaded_files


def build_script_env(
    project_path: Optional[Path] = None,
    search_paths: Optional[List[Path]] = None,
    extra_vars: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Build complete environment for script execution.
    
    Combines:
    - .env files (userspace + project)
    - Current os.environ
    - PYTHONPATH from search_paths
    - Any extra_vars passed in
    
    Args:
        project_path: Optional project path
        search_paths: Paths to add to PYTHONPATH
        extra_vars: Additional env vars to set
        
    Returns:
        Complete environment dict for subprocess execution
    """
    # Load from .env hierarchy
    env, loaded_files = load_env_hierarchy(project_path, include_runtime=True)
    
    # Build PYTHONPATH from search paths
    if search_paths:
        pythonpath_parts = [str(p.absolute()) for p in search_paths if p.exists()]
        if env.get("PYTHONPATH"):
            pythonpath_parts.append(env["PYTHONPATH"])
        if pythonpath_parts:
            env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    
    # Add extra vars
    if extra_vars:
        env.update(extra_vars)
    
    # Add metadata about loaded files (useful for debugging)
    if loaded_files:
        env["_KIWI_ENV_FILES"] = os.pathsep.join(loaded_files)
    
    return env


def get_required_vars(required: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Optional[str]]:
    """
    Check which required environment variables are set.
    
    Args:
        required: List of required env var names
        env: Environment dict to check (defaults to os.environ)
        
    Returns:
        Dict mapping var names to values (None if missing)
    """
    if env is None:
        env = dict(os.environ)
    
    return {var: env.get(var) for var in required}


def validate_required_vars(required: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[bool, List[str]]:
    """
    Validate that all required environment variables are set.
    
    Args:
        required: List of required env var names
        env: Environment dict to check
        
    Returns:
        Tuple of (all_present: bool, missing_vars: list)
    """
    result = get_required_vars(required, env)
    missing = [k for k, v in result.items() if v is None]
    return len(missing) == 0, missing


def create_env_template(
    filepath: Path,
    vars_with_descriptions: Dict[str, str],
    overwrite: bool = False
) -> bool:
    """
    Create a .env template file with variable placeholders and descriptions.
    
    Args:
        filepath: Path to create .env file
        vars_with_descriptions: Dict mapping VAR_NAME to description
        overwrite: Whether to overwrite existing file
        
    Returns:
        True if file was created
    """
    if filepath.exists() and not overwrite:
        logger.info(f"{filepath} already exists, not overwriting")
        return False
    
    lines = [
        "# Kiwi MCP Environment Variables",
        "# This file is loaded automatically when running scripts.",
        "#",
        "# Hierarchy (later overrides earlier):",
        "#   1. ~/.ai/.env (userspace defaults)",
        "#   2. .ai/.env (project overrides)",
        "#   3. Runtime environment (e.g. from MCP settings)",
        "",
    ]
    
    for var_name, description in vars_with_descriptions.items():
        lines.append(f"# {description}")
        lines.append(f"{var_name}=")
        lines.append("")
    
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text('\n'.join(lines), encoding='utf-8')
        logger.info(f"Created env template at {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to create {filepath}: {e}")
        return False
