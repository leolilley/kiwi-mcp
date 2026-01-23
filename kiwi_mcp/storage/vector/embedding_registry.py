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
    """Load and resolve vector configuration with user/project hierarchy."""

    # Default paths
    if user_config_path is None:
        user_config_path = str(Path.home() / ".ai" / "config" / "vector.yaml")
    if project_config_path is None:
        project_config_path = ".ai/config/vector.yaml"

    # Load user config (mandatory)
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

    # Validate mandatory fields
    embedding_url = resolved.get("embedding", {}).get("url", "")
    storage_url = resolved.get("storage", {}).get("url", "")

    if not embedding_url:
        raise ValueError(
            "Embedding URL is mandatory. Set EMBEDDING_URL environment variable "
            "or configure embedding.url in ~/.ai/config/vector.yaml"
        )

    if not storage_url:
        raise ValueError(
            "Vector storage URL is mandatory. Set VECTOR_DB_URL environment variable "
            "or configure storage.url in ~/.ai/config/vector.yaml"
        )

    return VectorConfig(
        embedding_url=embedding_url,
        embedding_key=resolved.get("embedding", {}).get("key", ""),
        embedding_model=resolved.get("embedding", {}).get("model", "default"),
        storage_type=resolved.get("storage", {}).get("type", "simple"),
        storage_url=storage_url,
        storage_key=resolved.get("storage", {}).get("key", ""),
        request_format=resolved.get("embedding", {}).get("request_format", "openai"),
        auth_header=resolved.get("embedding", {}).get("auth_header", "Authorization"),
        auth_format=resolved.get("embedding", {}).get("auth_format", "Bearer {key}"),
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
