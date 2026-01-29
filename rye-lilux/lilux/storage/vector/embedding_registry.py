"""Vector configuration - no hardcoded providers, just URL + key + model."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
from pathlib import Path
import yaml


@dataclass
class VectorConfig:
    """Vector configuration - no hardcoded providers."""

    # Embedding configuration (user provides URL + key + model)
    embedding_url: str = ""  # MANDATORY - embedding service URL
    embedding_key: str = ""  # API key (empty string if not needed)
    embedding_model: str = "default"  # Model name (server-specific)

    # Storage configuration
    storage_type: str = "simple"  # simple, chromadb, remote
    storage_url: str = ""  # MANDATORY - where vectors are stored
    storage_key: str = ""  # Auth for vector storage (empty if not needed)

    # Request configuration
    request_format: str = "openai"  # openai, cohere, custom
    auth_header: str = "Authorization"  # Header name for API key
    auth_format: str = "Bearer {key}"  # How to format auth header

    # Metadata
    user_config_path: Optional[str] = None
    project_config_path: Optional[str] = None


def resolve_template(template: str) -> str:
    """Resolve ${VAR:default} template following MCP patterns."""
    if template.startswith("${") and template.endswith("}"):
        content = template[2:-1]  # Remove ${}
        if ":" in content:
            var_name, default_value = content.split(":", 1)
            return os.getenv(var_name, default_value)
        else:
            return os.getenv(content, "")
    return template


def load_vector_config(
    user_config_path: Optional[str] = None, project_config_path: Optional[str] = None
) -> VectorConfig:
    """Load vector config from environment (config file optional fallback)."""
    
    # Try environment variables first (primary method)
    embedding_url = os.getenv("EMBEDDING_URL")
    vector_db_url = os.getenv("VECTOR_DB_URL")
    
    # Fallback to config file if env vars missing
    if not embedding_url or not vector_db_url:
        # Default paths
        if user_config_path is None:
            user_config_path = str(Path.home() / ".ai" / "config" / "vector.yaml")
        if project_config_path is None:
            project_config_path = ".ai/config/vector.yaml"

        # Load user config (optional fallback)
        user_config = {}
        if Path(user_config_path).exists():
            with open(user_config_path) as f:
                user_config = yaml.safe_load(f) or {}

        # Load project config (optional)
        project_config = {}
        if Path(project_config_path).exists():
            with open(project_config_path) as f:
                project_config = yaml.safe_load(f) or {}

        # Merge configurations (project overrides user)
        merged = _merge_configs(user_config, project_config)

        # Resolve environment variables
        resolved = _resolve_config_env_vars(merged)

        # Get from config file if not in env
        if not embedding_url:
            embedding_url = resolved.get("embedding", {}).get("url", "")
        if not vector_db_url:
            vector_db_url = resolved.get("storage", {}).get("url", "")
        
        # Get other settings from config file
        embedding_key = resolved.get("embedding", {}).get("key", "")
        embedding_model = resolved.get("embedding", {}).get("model", "default")
        storage_type = resolved.get("storage", {}).get("type", "simple")
        storage_key = resolved.get("storage", {}).get("key", "")
        request_format = resolved.get("embedding", {}).get("request_format", "openai")
        auth_header = resolved.get("embedding", {}).get("auth_header", "Authorization")
        auth_format = resolved.get("embedding", {}).get("auth_format", "Bearer {key}")
    else:
        # Use env vars directly
        embedding_key = os.getenv("EMBEDDING_API_KEY", "")
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        storage_type = os.getenv("VECTOR_DB_TYPE", "simple")
        storage_key = os.getenv("VECTOR_DB_KEY", "")
        request_format = os.getenv("EMBEDDING_FORMAT", "openai")
        auth_header = os.getenv("EMBEDDING_AUTH_HEADER", "Authorization")
        auth_format = os.getenv("EMBEDDING_AUTH_FORMAT", "Bearer {key}")
        
        # Set config paths to None if using env vars only
        user_config_path = None
        project_config_path = None

    # Validate mandatory fields
    if not embedding_url:
        raise ValueError(
            "Embedding URL is mandatory. Set EMBEDDING_URL environment variable "
            "or configure embedding.url in ~/.ai/config/vector.yaml"
        )

    if not vector_db_url:
        raise ValueError(
            "Vector storage URL is mandatory. Set VECTOR_DB_URL environment variable "
            "or configure storage.url in ~/.ai/config/vector.yaml"
        )

    return VectorConfig(
        embedding_url=embedding_url,
        embedding_key=embedding_key,
        embedding_model=embedding_model,
        storage_type=storage_type,
        storage_url=vector_db_url,
        storage_key=storage_key,
        request_format=request_format,
        auth_header=auth_header,
        auth_format=auth_format,
        user_config_path=user_config_path,
        project_config_path=project_config_path,
    )


def _merge_configs(user_config: dict, project_config: dict) -> dict:
    """Merge user and project configs with project taking precedence."""
    merged = {}

    # Start with user config
    if "embedding" in user_config:
        merged["embedding"] = user_config["embedding"].copy()
    if "storage" in user_config:
        merged["storage"] = user_config["storage"].copy()

    # Override with project config
    if "embedding" in project_config:
        if "embedding" not in merged:
            merged["embedding"] = {}
        merged["embedding"].update(project_config["embedding"])
    if "storage" in project_config:
        if "storage" not in merged:
            merged["storage"] = {}
        merged["storage"].update(project_config["storage"])

    return merged


def _resolve_config_env_vars(config: dict) -> dict:
    """Resolve environment variables in config values."""
    resolved = {}

    for section_name, section in config.items():
        resolved[section_name] = {}
        for key, value in section.items():
            if isinstance(value, str):
                resolved[section_name][key] = resolve_template(value)
            else:
                resolved[section_name][key] = value

    return resolved
