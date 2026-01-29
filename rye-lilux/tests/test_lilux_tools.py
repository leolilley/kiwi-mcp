"""
Smoke tests for Lilux kernel tools.
"""

import pytest
from pathlib import Path


class TestLiluxImports:
    """Test that lilux modules can be imported."""

    def test_import_lilux(self):
        import lilux
        assert lilux is not None

    def test_import_search_tool(self):
        from lilux.tools import search
        assert search is not None

    def test_import_load_tool(self):
        from lilux.tools import load
        assert load is not None

    def test_import_execute_tool(self):
        from lilux.tools import execute
        assert execute is not None

    def test_import_sign_tool(self):
        from lilux.tools import sign
        assert sign is not None

    def test_import_help_tool(self):
        from lilux.tools import help
        assert help is not None


class TestLiluxServer:
    """Test lilux server setup."""

    def test_server_module_exists(self):
        from lilux import server
        assert server is not None


class TestRyeContent:
    """Test RYE content bundle structure."""

    def test_rye_ai_tools_core_exist(self):
        rye_tools = Path(__file__).parent.parent / "rye" / ".ai" / "tools" / "core"
        assert rye_tools.exists()
        
        # Check for core tools
        assert (rye_tools / "system.py").exists()
        assert (rye_tools / "telemetry_lib.py").exists()
        assert (rye_tools / "rag.py").exists()

    def test_rye_ai_tools_threads_exist(self):
        threads = Path(__file__).parent.parent / "rye" / ".ai" / "tools" / "threads"
        assert threads.exists()
        assert (threads / "safety_harness.py").exists()
        assert (threads / "thread_directive.py").exists()
        assert (threads / "spawn_thread.py").exists()

    def test_rye_ai_tools_llm_exist(self):
        llm = Path(__file__).parent.parent / "rye" / ".ai" / "tools" / "llm"
        assert llm.exists()
        assert (llm / "anthropic_messages.yaml").exists()
        assert (llm / "openai_chat.yaml").exists()
        assert (llm / "pricing.yaml").exists()

    def test_rye_ai_tools_mcp_exist(self):
        mcp = Path(__file__).parent.parent / "rye" / ".ai" / "tools" / "mcp"
        assert mcp.exists()
        assert (mcp / "mcp_discover.py").exists()
        assert (mcp / "mcp_call.py").exists()

    def test_rye_ai_tools_capabilities_exist(self):
        caps = Path(__file__).parent.parent / "rye" / ".ai" / "tools" / "capabilities"
        assert caps.exists()
        assert (caps / "fs.py").exists()
        assert (caps / "net.py").exists()
        assert (caps / "process.py").exists()

    def test_rye_ai_directives_core_exist(self):
        directives = Path(__file__).parent.parent / "rye" / ".ai" / "directives" / "core"
        assert directives.exists()
        assert (directives / "init.md").exists()
        assert (directives / "bootstrap.md").exists()
        assert (directives / "search_directives.md").exists()

    def test_rye_ai_knowledge_structure_exists(self):
        knowledge = Path(__file__).parent.parent / "rye" / ".ai" / "knowledge"
        assert knowledge.exists()
        assert (knowledge / "lilux").exists()
        assert (knowledge / "rye").exists()
        assert (knowledge / "concepts").exists()
        assert (knowledge / "patterns").exists()
        assert (knowledge / "procedures").exists()
