"""
Tests for JSON-RPC protocol handler tool.
"""

import pytest
import json
import sys
from pathlib import Path

# Load tool from .ai/tools/protocol/
tool_path = Path(__file__).parent.parent.parent / ".ai" / "tools" / "protocol"
sys.path.insert(0, str(tool_path))

from jsonrpc_handler import (
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcBuilder,
    JsonRpcParser,
    JsonRpcErrorCodes,
)


class TestJsonRpcRequest:
    """Test JSON-RPC request building."""

    def test_basic_request(self):
        """Test basic request creation."""
        request = JsonRpcRequest(method="test/method", params={"key": "value"})
        
        assert request.method == "test/method"
        assert request.params == {"key": "value"}
        assert request.id is not None
        
        request_dict = request.to_dict()
        assert request_dict["jsonrpc"] == "2.0"
        assert request_dict["method"] == "test/method"
        assert request_dict["params"] == {"key": "value"}
        assert "id" in request_dict

    def test_request_with_custom_id(self):
        """Test request with custom ID."""
        request = JsonRpcRequest(method="test/method", params={}, id="custom-123")
        
        assert request.id == "custom-123"
        assert request.to_dict()["id"] == "custom-123"

    def test_request_to_json(self):
        """Test request JSON serialization."""
        request = JsonRpcRequest(method="test/method", params={"key": "value"})
        json_str = request.to_json()
        
        parsed = json.loads(json_str)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "test/method"
        assert parsed["params"] == {"key": "value"}

    def test_request_from_dict(self):
        """Test creating request from dict."""
        data = {
            "jsonrpc": "2.0",
            "method": "test/method",
            "params": {"key": "value"},
            "id": "test-id",
        }
        request = JsonRpcRequest.from_dict(data)
        
        assert request.method == "test/method"
        assert request.params == {"key": "value"}
        assert request.id == "test-id"


class TestJsonRpcResponse:
    """Test JSON-RPC response parsing."""

    def test_success_response(self):
        """Test success response."""
        response = JsonRpcResponse.success(result={"data": "test"}, request_id="123")
        
        assert response.is_success
        assert not response.is_error
        assert response.result == {"data": "test"}
        assert response.id == "123"
        
        response_dict = response.to_dict()
        assert response_dict["jsonrpc"] == "2.0"
        assert response_dict["result"] == {"data": "test"}
        assert response_dict["id"] == "123"
        assert "error" not in response_dict

    def test_error_response(self):
        """Test error response."""
        response = JsonRpcResponse.error_response(
            code=-32601,
            message="Method not found",
            request_id="123",
        )
        
        assert response.is_error
        assert not response.is_success
        assert response.error["code"] == -32601
        assert response.error["message"] == "Method not found"
        assert response.id == "123"
        
        response_dict = response.to_dict()
        assert response_dict["jsonrpc"] == "2.0"
        assert response_dict["error"]["code"] == -32601
        assert response_dict["id"] == "123"
        assert "result" not in response_dict

    def test_error_response_with_data(self):
        """Test error response with additional data."""
        response = JsonRpcResponse.error_response(
            code=-32602,
            message="Invalid params",
            data={"param": "value"},
            request_id="123",
        )
        
        assert response.error["data"] == {"param": "value"}

    def test_response_from_dict_success(self):
        """Test parsing success response from dict."""
        data = {
            "jsonrpc": "2.0",
            "result": {"data": "test"},
            "id": "123",
        }
        response = JsonRpcResponse.from_dict(data)
        
        assert response.is_success
        assert response.result == {"data": "test"}
        assert response.id == "123"

    def test_response_from_dict_error(self):
        """Test parsing error response from dict."""
        data = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": "123",
        }
        response = JsonRpcResponse.from_dict(data)
        
        assert response.is_error
        assert response.error["code"] == -32601
        assert response.id == "123"

    def test_response_from_json(self):
        """Test parsing response from JSON string."""
        json_str = '{"jsonrpc": "2.0", "result": {"data": "test"}, "id": "123"}'
        response = JsonRpcResponse.from_json(json_str)
        
        assert response.is_success
        assert response.result == {"data": "test"}


class TestJsonRpcBuilder:
    """Test JSON-RPC request builder."""

    def test_build_request(self):
        """Test building request directly."""
        request = JsonRpcBuilder.build_request(
            method="test/method",
            params={"key": "value"},
            request_id="custom-id",
        )
        
        assert request.method == "test/method"
        assert request.params == {"key": "value"}
        assert request.id == "custom-id"

    def test_build_from_template_simple(self):
        """Test building request from simple template."""
        template = {
            "method": "test/method",
            "params": {"key": "value"},
        }
        params = {}
        
        request = JsonRpcBuilder.build_from_template(template, params)
        
        assert request.method == "test/method"
        assert request.params == {"key": "value"}

    def test_build_from_template_with_placeholders(self):
        """Test building request with parameter placeholders."""
        template = {
            "method": "{rpc_method}",
            "params": {
                "tool_name": "{tool_name}",
                "arguments": "{arguments}",
            },
        }
        params = {
            "rpc_method": "tools/call",
            "tool_name": "test_tool",
            "arguments": {"key": "value"},
        }
        
        request = JsonRpcBuilder.build_from_template(template, params)
        
        assert request.method == "tools/call"
        assert request.params["tool_name"] == "test_tool"
        assert request.params["arguments"] == {"key": "value"}

    def test_build_from_template_nested(self):
        """Test building request with nested parameter substitution."""
        template = {
            "method": "tools/call",
            "params": {
                "name": "{tool_name}",
                "arguments": {
                    "param1": "{param1}",
                    "param2": "{param2}",
                },
            },
        }
        params = {
            "tool_name": "test_tool",
            "param1": "value1",
            "param2": "value2",
        }
        
        request = JsonRpcBuilder.build_from_template(template, params)
        
        assert request.params["name"] == "test_tool"
        assert request.params["arguments"]["param1"] == "value1"
        assert request.params["arguments"]["param2"] == "value2"

    def test_build_from_template_type_preservation(self):
        """Test that single placeholder preserves type."""
        template = {
            "method": "tools/call",
            "params": {
                "count": "{count}",  # Should preserve int type
                "enabled": "{enabled}",  # Should preserve bool type
            },
        }
        params = {
            "count": 42,
            "enabled": True,
        }
        
        request = JsonRpcBuilder.build_from_template(template, params)
        
        assert isinstance(request.params["count"], int)
        assert request.params["count"] == 42
        assert isinstance(request.params["enabled"], bool)
        assert request.params["enabled"] is True

    def test_build_from_template_missing_param(self):
        """Test error handling for missing parameters."""
        template = {
            "method": "test/method",
            "params": {"key": "{missing_param}"},
        }
        params = {}
        
        with pytest.raises(ValueError, match="Missing parameter"):
            JsonRpcBuilder.build_from_template(template, params)


class TestJsonRpcParser:
    """Test JSON-RPC response parser."""

    def test_parse_success_response(self):
        """Test parsing success response."""
        json_str = '{"jsonrpc": "2.0", "result": {"data": "test"}, "id": "123"}'
        response = JsonRpcParser.parse_response(json_str)
        
        assert response.is_success
        assert response.result == {"data": "test"}
        assert response.id == "123"

    def test_parse_error_response(self):
        """Test parsing error response."""
        json_str = '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "123"}'
        response = JsonRpcParser.parse_response(json_str)
        
        assert response.is_error
        assert response.error["code"] == -32601
        assert response.id == "123"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        json_str = '{"invalid": json}'
        response = JsonRpcParser.parse_response(json_str)
        
        assert response.is_error
        assert response.error["code"] == -32700  # Parse error
        assert "Parse error" in response.error["message"]

    def test_parse_batch_responses(self):
        """Test parsing batch responses."""
        json_str = json.dumps([
            {"jsonrpc": "2.0", "result": {"data": "test1"}, "id": "1"},
            {"jsonrpc": "2.0", "result": {"data": "test2"}, "id": "2"},
        ])
        responses = JsonRpcParser.parse_batch_responses(json_str)
        
        assert len(responses) == 2
        assert responses[0].result == {"data": "test1"}
        assert responses[1].result == {"data": "test2"}

    def test_parse_single_response_as_batch(self):
        """Test parsing single response as batch."""
        json_str = '{"jsonrpc": "2.0", "result": {"data": "test"}, "id": "123"}'
        responses = JsonRpcParser.parse_batch_responses(json_str)
        
        assert len(responses) == 1
        assert responses[0].result == {"data": "test"}

    def test_validate_success_response(self):
        """Test validating valid success response."""
        response = JsonRpcResponse.success(result={"data": "test"}, request_id="123")
        is_valid, error = JsonRpcParser.validate_response(response)
        
        assert is_valid
        assert error is None

    def test_validate_error_response(self):
        """Test validating valid error response."""
        response = JsonRpcResponse.error_response(
            code=-32601,
            message="Method not found",
            request_id="123",
        )
        is_valid, error = JsonRpcParser.validate_response(response)
        
        assert is_valid
        assert error is None

    def test_validate_missing_id(self):
        """Test validation fails for missing ID."""
        response = JsonRpcResponse(result={"data": "test"}, id=None)
        is_valid, error = JsonRpcParser.validate_response(response)
        
        assert not is_valid
        assert "missing 'id'" in error.lower()

    def test_validate_missing_result_and_error(self):
        """Test validation fails when both result and error are missing."""
        response = JsonRpcResponse(result=None, error=None, id="123")
        is_valid, error = JsonRpcParser.validate_response(response)
        
        assert not is_valid
        assert "result" in error.lower() or "error" in error.lower()

    def test_validate_invalid_error(self):
        """Test validation fails for invalid error structure."""
        response = JsonRpcResponse(error={"message": "test"}, id="123")  # Missing code
        is_valid, error = JsonRpcParser.validate_response(response)
        
        assert not is_valid
        assert "code" in error.lower() or "message" in error.lower()


class TestJsonRpcErrorCodes:
    """Test JSON-RPC error codes."""

    def test_error_codes_exist(self):
        """Test that standard error codes are defined."""
        assert JsonRpcErrorCodes.PARSE_ERROR == -32700
        assert JsonRpcErrorCodes.INVALID_REQUEST == -32600
        assert JsonRpcErrorCodes.METHOD_NOT_FOUND == -32601
        assert JsonRpcErrorCodes.INVALID_PARAMS == -32602
        assert JsonRpcErrorCodes.INTERNAL_ERROR == -32603
        assert JsonRpcErrorCodes.SERVER_ERROR_START == -32000
        assert JsonRpcErrorCodes.SERVER_ERROR_END == -32099
