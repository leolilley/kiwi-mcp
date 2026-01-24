#!/usr/bin/env python3
"""Test full execution pipeline with local chain resolution."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from kiwi_mcp.handlers.tool.handler import ToolHandler


async def test_tool_execution():
    """Test executing hello_node tool locally without registry."""
    print("\n🧪 Testing Tool Execution via ToolHandler")
    print("=" * 60)
    
    # Initialize handler with project path
    handler = ToolHandler(str(project_root))
    
    # Disable chain validation for this test (runtimes don't have child_schemas yet)
    handler.primitive_executor.validate_chain = False
    
    try:
        # Execute hello_node
        print("\n1. Executing 'hello_node' with params...")
        print("   Params: {'name': 'Kiwi', 'excited': True}")
        
        result = await handler.execute(
            action='run',
            tool_name='hello_node',
            parameters={'name': 'Kiwi', 'excited': True}
        )
        
        print(f"\n   Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"   Output: {result.get('data', {}).get('stdout', '')}")
            print(f"   Duration: {result.get('metadata', {}).get('duration_ms', 0)}ms")
            print(f"   Chain Length: {result.get('metadata', {}).get('chain_length', 0)}")
            print(f"   Integrity Verified: {result.get('metadata', {}).get('integrity_verified', False)}")
            print(f"   Chain Validated: {result.get('metadata', {}).get('chain_validated', False)}")
            
            # Verify output
            stdout = result.get('data', {}).get('stdout', '')
            if 'Hello, Kiwi!!!' in stdout:
                print("\n✓ Tool execution successful!")
                print("✓ Output matches expected result")
                return True
            else:
                print(f"\n✗ Unexpected output: {stdout}")
                return False
        else:
            print(f"   Error: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n✗ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        await handler.primitive_executor.close()


async def test_simple_execution():
    """Test simple hello_world.py execution."""
    print("\n2. Executing 'hello_world' (Python)...")
    
    handler = ToolHandler(str(project_root))
    
    # Disable chain validation
    handler.primitive_executor.validate_chain = False
    
    try:
        result = await handler.execute(
            action='run',
            tool_name='hello_world',
            parameters={'name': 'LocalChain'}
        )
        
        print(f"   Status: {result['status']}")
        
        if result['status'] == 'success':
            stdout = result.get('data', {}).get('stdout', '')
            print(f"   Output: {stdout}")
            
            if 'Hello, LocalChain' in stdout:
                print("✓ Python tool execution successful!")
                return True
            else:
                print(f"✗ Unexpected output")
                return False
        else:
            print(f"   Error: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"✗ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await handler.primitive_executor.close()


async def main():
    """Run all tests."""
    print("\n🚀 Full Execution Pipeline Test")
    print("=" * 60)
    print("Testing local chain resolution + execution")
    print("(No registry required!)")
    print("=" * 60)
    
    test1 = await test_tool_execution()
    test2 = await test_simple_execution()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✓ All execution tests passed!")
        print("\n🎉 Local chain resolution is fully functional!")
        print("   - Tools can be executed without registry")
        print("   - No network dependency for local development")
        print("   - Chains resolved from filesystem")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
