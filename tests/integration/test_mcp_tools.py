"""
Integration tests for MCP base tools (mcp_stdio, mcp_http).

Tests tool chain resolution, JSON-RPC protocol handling, and config structure.
"""

import pytest
from pathlib import Path
from kiwi_mcp.primitives.executor import ChainResolver


class TestMcpTools:
    """Test MCP base tool configurations and execution."""

    @pytest.fixture
    def project_path(self):
        """Get the actual project path."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def resolver(self, project_path):
        """ChainResolver instance."""
        return ChainResolver(project_path)

    @pytest.mark.asyncio
    async def test_mcp_stdio_chain_resolution(self, resolver):
        """Test that mcp_stdio resolves to subprocess primitive."""
        chain = await resolver.resolve("mcp_stdio")
        
        assert len(chain) == 2
        assert chain[0]["tool_id"] == "mcp_stdio"
        assert chain[0]["tool_type"] == "http"
        assert chain[0]["executor_id"] == "subprocess"
        
        assert chain[1]["tool_id"] == "subprocess"
        assert chain[1]["tool_type"] == "primitive"

    @pytest.mark.asyncio
    async def test_mcp_http_chain_resolution(self, resolver):
        """Test that mcp_http resolves to http_client primitive."""
        chain = await resolver.resolve("mcp_http")
        
        assert len(chain) == 2
        assert chain[0]["tool_id"] == "mcp_http"
        assert chain[0]["tool_type"] == "http"
        assert chain[0]["executor_id"] == "http_client"
        
        assert chain[1]["tool_id"] == "http_client"
        assert chain[1]["tool_type"] == "primitive"

    @pytest.mark.asyncio
    async def test_mcp_stdio_config_structure(self, project_path):
        """Test mcp_stdio config has correct structure."""
        import yaml
        
        tool_file = project_path / ".ai" / "tools" / "mcp" / "mcp_stdio.yaml"
        
        with open(tool_file) as f:
            config = yaml.safe_load(f)
        
        # Verify structure
        assert config["tool_id"] == "mcp_stdio"
        assert config["tool_type"] == "http"
        assert config["executor_id"] == "subprocess"
        assert config.get("category") == "mcp"
        
        # Verify config
        assert "config" in config
        assert config["config"].get("input_format") == "jsonrpc"
        assert config["config"].get("output_format") == "jsonrpc"
        
        # Verify parameters
        param_names = [p.get("name") for p in config.get("parameters", [])]
        assert "command" in param_names
        assert "method" in param_names
        assert "params" in param_names

    @pytest.mark.asyncio
    async def test_mcp_http_config_structure(self, project_path):
        """Test mcp_http config has correct structure."""
        import yaml
        
        tool_file = project_path / ".ai" / "tools" / "mcp" / "mcp_http.yaml"
        
        with open(tool_file) as f:
            config = yaml.safe_load(f)
        
        # Verify structure
        assert config["tool_id"] == "mcp_http"
        assert config["tool_type"] == "http"
        assert config["executor_id"] == "http_client"
        assert config.get("category") == "mcp"
        
        # Verify config
        assert "config" in config
        assert config["config"].get("method") == "POST"
        assert "headers" in config["config"]
        assert config["config"]["headers"].get("Content-Type") == "application/json"
        
        # Verify body templating
        body = config["config"].get("body", {})
        assert body.get("jsonrpc") == "2.0"
        assert body.get("id") == "{request_id}"
        assert body.get("method") == "{rpc_method}"
        assert body.get("params") == "{rpc_params}"
        
        # Verify parameters
        param_names = [p.get("name") for p in config.get("parameters", [])]
        assert "url" in param_names
        assert "rpc_method" in param_names
        assert "rpc_params" in param_names

    @pytest.mark.asyncio
    async def test_mcp_stdio_parameters(self, project_path):
        """Test mcp_stdio has all required parameters."""
        import yaml
        
        tool_file = project_path / ".ai" / "tools" / "mcp" / "mcp_stdio.yaml"
        
        with open(tool_file) as f:
            config = yaml.safe_load(f)
        
        parameters = config.get("parameters", [])
        
        # Check required parameters
        command_param = next((p for p in parameters if p.get("name") == "command"), None)
        assert command_param is not None
        assert command_param.get("required") is True
        
        method_param = next((p for p in parameters if p.get("name") == "method"), None)
        assert method_param is not None
        assert method_param.get("required") is True
        
        params_param = next((p for p in parameters if p.get("name") == "params"), None)
        assert params_param is not None
        assert params_param.get("required") is True

    @pytest.mark.asyncio
    async def test_mcp_http_parameters(self, project_path):
        """Test mcp_http has all required parameters."""
        import yaml
        
        tool_file = project_path / ".ai" / "tools" / "mcp" / "mcp_http.yaml"
        
        with open(tool_file) as f:
            config = yaml.safe_load(f)
        
        parameters = config.get("parameters", [])
        
        # Check required parameters
        url_param = next((p for p in parameters if p.get("name") == "url"), None)
        assert url_param is not None
        assert url_param.get("required") is True
        
        rpc_method_param = next((p for p in parameters if p.get("name") == "rpc_method"), None)
        assert rpc_method_param is not None
        assert rpc_method_param.get("required") is True
        
        rpc_params_param = next((p for p in parameters if p.get("name") == "rpc_params"), None)
        assert rpc_params_param is not None
        assert rpc_params_param.get("required") is True

    @pytest.mark.asyncio
    async def test_mcp_http_body_templating(self, project_path):
        """Test that mcp_http body uses parameter templating."""
        import yaml
        
        tool_file = project_path / ".ai" / "tools" / "mcp" / "mcp_http.yaml"
        
        with open(tool_file) as f:
            config = yaml.safe_load(f)
        
        body = config["config"].get("body", {})
        
        # Verify placeholders
        assert "{request_id}" in str(body.get("id", ""))
        assert "{rpc_method}" in str(body.get("method", ""))
        assert "{rpc_params}" in str(body.get("params", ""))

    @pytest.mark.asyncio
    async def test_yaml_configs_are_valid(self, project_path):
        """Test that all YAML configs are valid and parse correctly."""
        import yaml
        
        mcp_dir = project_path / ".ai" / "tools" / "mcp"
        
        for yaml_file in [mcp_dir / "mcp_stdio.yaml", mcp_dir / "mcp_http.yaml"]:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                assert "tool_id" in config
                assert "tool_type" in config
                assert config["tool_type"] == "http"
                assert "executor_id" in config
                assert "config" in config
                assert "parameters" in config

    @pytest.mark.asyncio
    async def test_mcp_tools_have_signatures(self, project_path):
        """Test that MCP tools have validation signatures."""
        mcp_dir = project_path / ".ai" / "tools" / "mcp"
        
        for yaml_file in [mcp_dir / "mcp_stdio.yaml", mcp_dir / "mcp_http.yaml"]:
            content = yaml_file.read_text()
            assert "kiwi-mcp:validated:" in content, f"{yaml_file.name} missing signature"
