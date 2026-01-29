"""
Tests for validation utilities including BashValidator and APIValidator
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from lilux.utils.validators import BashValidator, APIValidator, ValidationResult


class TestBashValidator:
    """Test suite for BashValidator."""

    @pytest.fixture
    def bash_validator(self):
        """Create a BashValidator instance."""
        return BashValidator()

    @pytest.mark.asyncio
    async def test_validate_valid_script(self, bash_validator):
        """Test validation of a valid bash script."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\necho 'Hello World'")
            script_path = Path(f.name)

        try:
            result = await bash_validator.validate(script_path)
            assert result.valid is True
            assert result.error is None
        finally:
            script_path.unlink()

    @pytest.mark.asyncio
    async def test_validate_missing_shebang(self, bash_validator):
        """Test validation fails when shebang is missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("echo 'Hello World'")  # No shebang
            script_path = Path(f.name)

        try:
            result = await bash_validator.validate(script_path)
            assert result.valid is False
            assert "Missing shebang" in result.error
        finally:
            script_path.unlink()

    @pytest.mark.asyncio
    async def test_validate_syntax_error(self, bash_validator):
        """Test validation fails with syntax errors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\nif [ true ; then\n# Missing fi")  # Syntax error
            script_path = Path(f.name)

        try:
            result = await bash_validator.validate(script_path)
            assert result.valid is False
            assert result.error is not None
        finally:
            script_path.unlink()


class TestAPIValidator:
    """Test suite for APIValidator."""

    @pytest.fixture
    def api_validator(self):
        """Create an APIValidator instance."""
        return APIValidator()

    @pytest.fixture
    def mock_manifest(self):
        """Create a mock manifest."""
        manifest = Mock()
        manifest.executor_config = {}
        return manifest

    @pytest.mark.asyncio
    async def test_validate_valid_config(self, api_validator, mock_manifest):
        """Test validation of a valid API configuration."""
        mock_manifest.executor_config = {"endpoint": "https://api.example.com/test"}

        result = await api_validator.validate(mock_manifest)
        assert result.valid is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_missing_endpoint(self, api_validator, mock_manifest):
        """Test validation fails when endpoint is missing."""
        mock_manifest.executor_config = {}

        result = await api_validator.validate(mock_manifest)
        assert result.valid is False
        assert "Missing endpoint" in result.error

    @pytest.mark.asyncio
    async def test_validate_invalid_url(self, api_validator, mock_manifest):
        """Test validation fails with invalid URL."""
        mock_manifest.executor_config = {"endpoint": "not-a-url"}

        result = await api_validator.validate(mock_manifest)
        assert result.valid is False
        assert "Invalid endpoint URL" in result.error

    @pytest.mark.asyncio
    async def test_validate_valid_auth_bearer(self, api_validator, mock_manifest):
        """Test validation with valid bearer auth."""
        mock_manifest.executor_config = {
            "endpoint": "https://api.example.com/test",
            "auth": {"type": "bearer", "token_param": "token"},
        }

        result = await api_validator.validate(mock_manifest)
        assert result.valid is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_valid_auth_api_key(self, api_validator, mock_manifest):
        """Test validation with valid API key auth."""
        mock_manifest.executor_config = {
            "endpoint": "https://api.example.com/test",
            "auth": {"type": "api_key", "key_param": "key", "header": "X-API-Key"},
        }

        result = await api_validator.validate(mock_manifest)
        assert result.valid is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_invalid_auth_type(self, api_validator, mock_manifest):
        """Test validation fails with invalid auth type."""
        mock_manifest.executor_config = {
            "endpoint": "https://api.example.com/test",
            "auth": {"type": "invalid_auth_type"},
        }

        result = await api_validator.validate(mock_manifest)
        assert result.valid is False
        assert "Unknown auth type" in result.error

    def test_is_valid_url_valid_https(self, api_validator):
        """Test URL validation with valid HTTPS URL."""
        assert api_validator._is_valid_url("https://api.example.com/test") is True

    def test_is_valid_url_valid_http(self, api_validator):
        """Test URL validation with valid HTTP URL."""
        assert api_validator._is_valid_url("http://api.example.com/test") is True

    def test_is_valid_url_invalid(self, api_validator):
        """Test URL validation with invalid URLs."""
        assert api_validator._is_valid_url("not-a-url") is False
        assert (
            api_validator._is_valid_url("ftp://example.com") is True
        )  # Valid URL, different scheme
        assert api_validator._is_valid_url("") is False
        assert api_validator._is_valid_url("http://") is False


class TestValidationResult:
    """Test suite for ValidationResult."""

    def test_validation_result_success(self):
        """Test creating a successful validation result."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.error is None

    def test_validation_result_failure(self):
        """Test creating a failed validation result."""
        result = ValidationResult(valid=False, error="Test error")
        assert result.valid is False
        assert result.error == "Test error"
