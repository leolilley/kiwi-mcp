#!/usr/bin/env python3
"""
Simple test of RYE handlers
"""

from pathlib import Path
import sys

# Add rye/rye to Python path
sys.path.insert(0, str(Path(__file__).parent / "rye" / "rye"))

# Now import handlers
import handlers.directive.handler as dh_module
import handlers.tool.handler as th_module
import handlers.knowledge.handler as kh_module


def test_imports():
    """Test that handlers can be imported."""
    print("Testing RYE handler imports...")

    # Test directive handler
    d_handler = dh_module.DirectiveHandler("/tmp")
    print(f"✅ Directive handler: {type(d_handler)}")

    # Test tool handler
    t_handler = th_module.ToolHandler("/tmp")
    print(f"✅ Tool handler: {type(t_handler)}")

    # Test knowledge handler
    k_handler = kh_module.KnowledgeHandler("/tmp")
    print(f"✅ Knowledge handler: {type(k_handler)}")

    print("\n🎉 All RYE handlers imported successfully!")


if __name__ == "__main__":
    test_imports()
