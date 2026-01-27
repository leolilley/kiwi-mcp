"""
Tests for tool chain error handling with full context.

Tests:
- ToolChainError construction and formatting
- FailedToolContext with config paths and validation errors
- Error wrapping at execution layer
- Serialization to dict for LLM consumption
"""

import pytest
from kiwi_mcp.primitives.errors import (
    ToolChainError,
    FailedToolContext,
    ValidationError,
    ConfigValidationError,
)


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_validation_error_basic(self):
        """Create a basic validation error."""
        err = ValidationError(field="config.model", error="required")
        assert err.field == "config.model"
        assert err.error == "required"
        assert err.value is None

    def test_validation_error_with_value(self):
        """Create validation error with a value."""
        err = ValidationError(
            field="config.max_tokens", error="must be >= 1", value=0
        )
        assert err.field == "config.max_tokens"
        assert err.error == "must be >= 1"
        assert err.value == 0


class TestFailedToolContext:
    """Tests for FailedToolContext dataclass."""

    def test_failed_tool_context_minimal(self):
        """Create context with just required fields."""
        ctx = FailedToolContext(
            tool_id="anthropic_messages", config_path=".ai/tools/llm/anthropic_messages.yaml"
        )
        assert ctx.tool_id == "anthropic_messages"
        assert ctx.config_path == ".ai/tools/llm/anthropic_messages.yaml"
        assert ctx.validation_errors == []
        assert ctx.metadata == {}

    def test_failed_tool_context_with_errors(self):
        """Create context with validation errors."""
        errors = [
            ValidationError(field="config.model", error="required"),
            ValidationError(field="config.max_tokens", error="must be >= 1", value=0),
        ]
        ctx = FailedToolContext(
            tool_id="anthropic_messages",
            config_path=".ai/tools/llm/anthropic_messages.yaml",
            validation_errors=errors,
        )
        assert len(ctx.validation_errors) == 2
        assert ctx.validation_errors[0].field == "config.model"

    def test_failed_tool_context_with_metadata(self):
        """Create context with additional metadata."""
        ctx = FailedToolContext(
            tool_id="http_client",
            config_path=".ai/tools/http_client.yaml",
            metadata={
                "attempted_at": "2024-01-27T10:00:00Z",
                "request_id": "abc123",
            },
        )
        assert ctx.metadata["attempted_at"] == "2024-01-27T10:00:00Z"
        assert ctx.metadata["request_id"] == "abc123"


class TestToolChainError:
    """Tests for ToolChainError."""

    def test_tool_chain_error_basic(self):
        """Create a basic ToolChainError."""
        failed_ctx = FailedToolContext(
            tool_id="anthropic_messages",
            config_path=".ai/tools/llm/anthropic_messages.yaml",
        )
        error = ToolChainError(
            code="CONFIG_VALIDATION_ERROR",
            message="Missing required field 'model'",
            chain=["anthropic_thread", "anthropic_messages", "http_client"],
            failed_at=failed_ctx,
        )

        assert error.code == "CONFIG_VALIDATION_ERROR"
        assert error.message == "Missing required field 'model'"
        assert error.chain == ["anthropic_thread", "anthropic_messages", "http_client"]
        assert error.failed_at.tool_id == "anthropic_messages"
        assert error.cause is None

    def test_tool_chain_error_with_cause(self):
        """Create ToolChainError with underlying cause."""
        cause = ValueError("Invalid value")
        failed_ctx = FailedToolContext(
            tool_id="http_client", config_path=".ai/tools/http_client.yaml"
        )
        error = ToolChainError(
            code="EXECUTION_FAILED",
            message="HTTP request failed",
            chain=["anthropic_messages", "http_client"],
            failed_at=failed_ctx,
            cause=cause,
        )

        assert error.cause == cause
        assert isinstance(error.cause, ValueError)

    def test_tool_chain_error_formatting(self):
        """Test formatted error message."""
        errors = [
            ValidationError(field="config.model", error="required"),
        ]
        failed_ctx = FailedToolContext(
            tool_id="anthropic_messages",
            config_path=".ai/tools/llm/anthropic_messages.yaml",
            validation_errors=errors,
        )
        error = ToolChainError(
            code="CONFIG_VALIDATION_ERROR",
            message="Configuration validation failed",
            chain=["root", "anthropic_messages", "http_client"],
            failed_at=failed_ctx,
        )

        formatted = str(error)
        assert "[CONFIG_VALIDATION_ERROR]" in formatted
        assert "anthropic_messages" in formatted
        assert ".ai/tools/llm/anthropic_messages.yaml" in formatted
        assert "config.model" in formatted
        assert "required" in formatted

    def test_tool_chain_error_formatting_with_cause(self):
        """Test formatted error with underlying cause."""
        cause = ValueError("connection timeout")
        failed_ctx = FailedToolContext(
            tool_id="http_client", config_path=".ai/tools/http_client.yaml"
        )
        error = ToolChainError(
            code="EXECUTION_FAILED",
            message="Tool execution failed",
            chain=["root", "http_client"],
            failed_at=failed_ctx,
            cause=cause,
        )

        formatted = str(error)
        assert "ValueError" in formatted
        assert "connection timeout" in formatted

    def test_tool_chain_error_to_dict(self):
        """Test serialization to dict."""
        errors = [
            ValidationError(field="config.model", error="required"),
            ValidationError(field="config.max_tokens", error="must be >= 1", value=0),
        ]
        failed_ctx = FailedToolContext(
            tool_id="anthropic_messages",
            config_path=".ai/tools/llm/anthropic_messages.yaml",
            validation_errors=errors,
        )
        error = ToolChainError(
            code="CONFIG_VALIDATION_ERROR",
            message="Configuration validation failed",
            chain=["anthropic_thread", "anthropic_messages", "http_client"],
            failed_at=failed_ctx,
        )

        error_dict = error.to_dict()

        # Verify structure
        assert error_dict["code"] == "CONFIG_VALIDATION_ERROR"
        assert error_dict["message"] == "Configuration validation failed"
        assert error_dict["chain"] == [
            "anthropic_thread",
            "anthropic_messages",
            "http_client",
        ]

        # Verify failed_at
        assert error_dict["failed_at"]["tool_id"] == "anthropic_messages"
        assert (
            error_dict["failed_at"]["config_path"]
            == ".ai/tools/llm/anthropic_messages.yaml"
        )

        # Verify validation_errors
        assert len(error_dict["failed_at"]["validation_errors"]) == 2
        assert error_dict["failed_at"]["validation_errors"][0]["field"] == "config.model"
        assert error_dict["failed_at"]["validation_errors"][0]["error"] == "required"
        assert error_dict["failed_at"]["validation_errors"][1]["field"] == "config.max_tokens"
        assert error_dict["failed_at"]["validation_errors"][1]["value"] == 0

    def test_tool_chain_error_to_dict_with_cause(self):
        """Test dict serialization with cause."""
        cause = RuntimeError("Database connection failed")
        failed_ctx = FailedToolContext(
            tool_id="http_client", config_path=".ai/tools/http_client.yaml"
        )
        error = ToolChainError(
            code="EXECUTION_FAILED",
            message="HTTP request failed",
            chain=["root", "http_client"],
            failed_at=failed_ctx,
            cause=cause,
        )

        error_dict = error.to_dict()

        # Verify cause
        assert error_dict["cause"] is not None
        assert "Database connection failed" in error_dict["cause"]["message"]

    def test_tool_chain_error_to_dict_llm_actionable(self):
        """Test that dict format is LLM-actionable."""
        errors = [
            ValidationError(field="config.model", error="required"),
        ]
        failed_ctx = FailedToolContext(
            tool_id="anthropic_messages",
            config_path=".ai/tools/llm/anthropic_messages.yaml",
            validation_errors=errors,
        )
        error = ToolChainError(
            code="CONFIG_VALIDATION_ERROR",
            message="Configuration validation failed",
            chain=["anthropic_thread", "anthropic_messages", "http_client"],
            failed_at=failed_ctx,
        )

        error_dict = error.to_dict()

        # An LLM should be able to:
        # 1. Identify the error code
        assert "code" in error_dict

        # 2. Understand what failed and where
        assert "chain" in error_dict  # tool execution path
        assert "failed_at" in error_dict  # where it failed

        # 3. Know how to fix it
        assert "failed_at" in error_dict
        assert "config_path" in error_dict["failed_at"]
        assert "validation_errors" in error_dict["failed_at"]

        # 4. Understand the underlying cause if present
        assert "cause" in error_dict

    def test_tool_chain_error_is_exception(self):
        """ToolChainError should be an Exception."""
        failed_ctx = FailedToolContext(
            tool_id="http_client", config_path=".ai/tools/http_client.yaml"
        )
        error = ToolChainError(
            code="EXECUTION_FAILED",
            message="Execution failed",
            chain=["root", "http_client"],
            failed_at=failed_ctx,
        )

        assert isinstance(error, Exception)

    def test_tool_chain_error_can_be_raised(self):
        """ToolChainError should be raisable."""
        failed_ctx = FailedToolContext(
            tool_id="http_client", config_path=".ai/tools/http_client.yaml"
        )
        error = ToolChainError(
            code="EXECUTION_FAILED",
            message="Execution failed",
            chain=["root", "http_client"],
            failed_at=failed_ctx,
        )

        with pytest.raises(ToolChainError) as exc_info:
            raise error

        assert exc_info.value.code == "EXECUTION_FAILED"


class TestConfigValidationError:
    """Tests for ConfigValidationError."""

    def test_config_validation_error_basic(self):
        """Create a basic ConfigValidationError."""
        errors = [
            ValidationError(field="config.model", error="required"),
        ]
        error = ConfigValidationError(tool_id="anthropic_messages", errors=errors)

        assert error.tool_id == "anthropic_messages"
        assert len(error.errors) == 1
        assert error.errors[0].field == "config.model"

    def test_config_validation_error_formatting(self):
        """Test formatted message."""
        errors = [
            ValidationError(field="config.model", error="required"),
            ValidationError(field="config.max_tokens", error="must be >= 1"),
        ]
        error = ConfigValidationError(tool_id="anthropic_messages", errors=errors)

        formatted = str(error)
        assert "anthropic_messages" in formatted
        assert "config.model" in formatted
        assert "config.max_tokens" in formatted

    def test_config_validation_error_is_exception(self):
        """ConfigValidationError should be an Exception."""
        errors = [ValidationError(field="config.model", error="required")]
        error = ConfigValidationError(tool_id="test", errors=errors)

        assert isinstance(error, Exception)


class TestErrorContextIntegration:
    """Integration tests for error context."""

    def test_complete_error_context_flow(self):
        """Test complete error context from validation to serialization."""
        # Simulate a validation failure
        validation_errors = [
            ValidationError(field="config.api_key", error="required"),
            ValidationError(field="config.timeout", error="must be > 0", value=-1),
        ]

        # Create failed tool context
        failed_ctx = FailedToolContext(
            tool_id="anthropic_messages",
            config_path=".ai/tools/llm/anthropic_messages.yaml",
            validation_errors=validation_errors,
            metadata={"validation_time_ms": 45},
        )

        # Create tool chain error
        error = ToolChainError(
            code="CONFIG_VALIDATION_ERROR",
            message="Anthropic messages configuration is invalid",
            chain=["user_directive", "anthropic_thread", "anthropic_messages", "http_client"],
            failed_at=failed_ctx,
        )

        # Serialize to dict
        error_dict = error.to_dict()

        # Verify all information is present
        assert error_dict["code"] == "CONFIG_VALIDATION_ERROR"
        assert error_dict["chain"] == [
            "user_directive",
            "anthropic_thread",
            "anthropic_messages",
            "http_client",
        ]
        assert error_dict["failed_at"]["tool_id"] == "anthropic_messages"
        assert len(error_dict["failed_at"]["validation_errors"]) == 2

        # Verify it's JSON-serializable (for API responses)
        import json

        json_str = json.dumps(error_dict)
        assert "anthropic_messages" in json_str
        assert "config.api_key" in json_str

    def test_multiple_errors_in_chain(self):
        """Test handling multiple errors across chain."""
        # First error in chain
        error1_ctx = FailedToolContext(
            tool_id="anthropic_thread",
            config_path=".ai/tools/llm/anthropic_thread.yaml",
            validation_errors=[
                ValidationError(field="config.model", error="required"),
            ],
        )

        error1 = ToolChainError(
            code="CONFIG_VALIDATION_ERROR",
            message="Anthropic thread config invalid",
            chain=["root", "anthropic_thread", "anthropic_messages", "http_client"],
            failed_at=error1_ctx,
        )

        # Second error later in chain
        error2_ctx = FailedToolContext(
            tool_id="anthropic_messages",
            config_path=".ai/tools/llm/anthropic_messages.yaml",
            validation_errors=[
                ValidationError(field="config.api_key", error="required"),
            ],
        )

        error2 = ToolChainError(
            code="CONFIG_VALIDATION_ERROR",
            message="Anthropic messages config invalid",
            chain=["root", "anthropic_thread", "anthropic_messages", "http_client"],
            failed_at=error2_ctx,
        )

        # Both should have full chain context
        assert len(error1.chain) == 4
        assert len(error2.chain) == 4
        assert error1.failed_at.tool_id != error2.failed_at.tool_id
