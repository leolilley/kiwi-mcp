"""
Kernel Validators - Primitive validation only.

This is the KERNEL version - contains only primitive validation.
Content validation moves to RYE OS layer.
"""

import subprocess
import urllib.parse
from pathlib import Path
from typing import Optional


class ValidationResult:
    """Result from a validation operation."""

    def __init__(self, valid: bool, error: Optional[str] = None):
        self.valid = valid
        self.error = error


class BashValidator:
    """Validate subprocess commands (dumb - no content knowledge)."""

    @staticmethod
    def validate_command(command: str) -> ValidationResult:
        """Basic command validation - no content interpretation."""
        if not command or not command.strip():
            return ValidationResult(False, "Empty command")
        return ValidationResult(True)

    async def validate(self, script_path: Path) -> ValidationResult:
        """Validate a bash script for syntax and structure."""
        try:
            # Check shebang exists
            content = script_path.read_text()
            if not content.startswith("#!"):
                return ValidationResult(valid=False, error="Missing shebang")

            # Syntax check with bash -n
            result = subprocess.run(
                ["bash", "-n", str(script_path)], capture_output=True, text=True
            )
            if result.returncode != 0:
                return ValidationResult(valid=False, error=result.stderr)

            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, error=str(e))


class APIValidator:
    """Validate HTTP requests (dumb - no content knowledge)."""

    @staticmethod
    def validate_request(url: str, method: str) -> ValidationResult:
        """Basic request validation - no content interpretation."""
        if not url or not url.strip():
            return ValidationResult(False, "Empty URL")
        return ValidationResult(True)

    async def validate(self, manifest) -> ValidationResult:
        """Validate an API tool manifest configuration."""
        config = manifest.executor_config

        # Check required fields
        if "endpoint" not in config:
            return ValidationResult(valid=False, error="Missing endpoint")

        # Validate URL format
        if not self._is_valid_url(config["endpoint"]):
            return ValidationResult(valid=False, error="Invalid endpoint URL")

        # Check auth config if present
        if "auth" in config:
            if config["auth"]["type"] not in ["bearer", "api_key", "basic"]:
                return ValidationResult(valid=False, error="Unknown auth type")

        return ValidationResult(valid=True)

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


# REMOVED: ValidationManager - moved to RYE
# REMOVED: compare_versions - moved to RYE
# REMOVED: BaseValidator - moved to RYE
# REMOVED: DirectiveValidator - moved to RYE
# REMOVED: ToolValidator - moved to RYE
# REMOVED: KnowledgeValidator - moved to RYE
# REMOVED: All complex validation logic - intelligence moves to RYE
