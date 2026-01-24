#!/usr/bin/env python3
"""Test local chain resolution without registry."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from kiwi_mcp.primitives.local_chain_resolver import LocalChainResolver


async def test_local_chain_resolution():
    """Test that we can resolve hello_node chain locally."""
    print("Testing local chain resolution...")
    print("=" * 60)
    
    resolver = LocalChainResolver(project_root)
    
    try:
        # Test resolving hello_node
        print("\n1. Resolving 'hello_node' chain...")
        chain = await resolver.resolve_chain('hello_node')
        
        print(f"✓ Resolved chain with {len(chain)} steps:\n")
        
        for i, link in enumerate(chain, 1):
            tool_id = link["tool_id"]
            tool_type = link["tool_type"]
            executor_id = link.get("executor_id", "None")
            file_path = link.get("file_path", "N/A")
            
            print(f"  {i}. {tool_id}")
            print(f"     - Type: {tool_type}")
            print(f"     - Executor: {executor_id}")
            print(f"     - Path: {file_path}")
            print()
        
        # Verify chain structure
        assert len(chain) == 3, f"Expected 3 steps, got {len(chain)}"
        assert chain[0]['tool_id'] == 'hello_node', "First should be hello_node"
        assert chain[0]['tool_type'] == 'javascript', "Should be javascript type"
        assert chain[1]['tool_id'] == 'node_runtime', "Second should be node_runtime"
        assert chain[1]['tool_type'] == 'runtime', "Should be runtime type"
        assert chain[2]['tool_id'] == 'subprocess', "Third should be subprocess"
        assert chain[2]['tool_type'] == 'primitive', "Should be primitive type"
        assert chain[2]['executor_id'] is None, "Primitive should have no executor"
        
        print("✓ Chain structure validated!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_nonexistent_tool():
    """Test error handling for nonexistent tools."""
    print("\n2. Testing error handling for nonexistent tool...")
    
    resolver = LocalChainResolver(project_root)
    
    try:
        chain = await resolver.resolve_chain('nonexistent_tool')
        print(f"✗ Should have raised ToolNotFoundError, got: {chain}")
        return False
    except Exception as e:
        error_msg = str(e)
        if "not found locally" in error_msg:
            print(f"✓ Correctly raised error: {error_msg}")
            return True
        else:
            print(f"✗ Unexpected error: {e}")
            return False


async def main():
    """Run all tests."""
    print("\n🧪 Local Chain Resolution Tests")
    print("=" * 60)
    
    test1 = await test_local_chain_resolution()
    test2 = await test_nonexistent_tool()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
