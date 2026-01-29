"""Vector configuration management with user/project resolution."""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from ..storage.vector.embedding_registry import VectorConfig, load_vector_config


class VectorConfigManager:
    """Manages vector configuration at user and project levels."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.user_config_path = Path.home() / ".ai" / "config" / "vector.yaml"
        self.project_config_path = self.project_path / ".ai" / "config" / "vector.yaml"

    def load_config(self) -> VectorConfig:
        """Load resolved vector configuration."""
        return load_vector_config(str(self.user_config_path), str(self.project_config_path))

    def ensure_user_config(self) -> bool:
        """Ensure user-level configuration exists."""
        if self.user_config_path.exists():
            return True

        # Create default user config
        self.user_config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "embedding": {
                "url": "${EMBEDDING_URL:https://api.openai.com/v1/embeddings}",
                "key": "${EMBEDDING_API_KEY}",
                "model": "${EMBEDDING_MODEL:text-embedding-3-small}",
                "request_format": "${EMBEDDING_FORMAT:openai}",
            },
            "storage": {
                "type": "simple",
                "url": "${VECTOR_DB_URL}",  # User must set this
                "key": "${VECTOR_DB_KEY:}",
            },
        }

        with open(self.user_config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

        return False  # Was created, not pre-existing

    def create_project_config(
        self,
        embedding_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        storage_url: Optional[str] = None,
    ) -> None:
        """Create project-specific configuration overrides."""
        self.project_config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {}

        if embedding_url or embedding_model:
            config["embedding"] = {}
            if embedding_url:
                config["embedding"]["url"] = embedding_url
            if embedding_model:
                config["embedding"]["model"] = embedding_model

        if storage_url:
            config["storage"] = {"url": storage_url}

        with open(self.project_config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration and return status."""
        try:
            config = self.load_config()

            # Test embedding service
            from ..storage.vector.api_embeddings import EmbeddingService

            embedding_service = EmbeddingService(config)
            embedding_info = embedding_service.get_info()

            return {
                "valid": True,
                "config": config,
                "embedding_info": embedding_info,
                "user_config_exists": self.user_config_path.exists(),
                "project_config_exists": self.project_config_path.exists(),
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "user_config_exists": self.user_config_path.exists(),
                "project_config_exists": self.project_config_path.exists(),
            }
