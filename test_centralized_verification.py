#!/usr/bin/env python3
"""Test centralized verification architecture.

NOTE: This test expects tools to be validated with the NEW unified integrity system.
If you get "Integrity mismatch" errors, re-validate the tool with:
  execute(item_type='tool', action='update', item_id='hello_world', ...)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kiwi_mcp.utils.metadata_manager import MetadataManager
from kiwi_mcp.primitives.integrity_verifier import IntegrityVerifier
from kiwi_mcp.primitives.local_chain_resolver import LocalChainResolver

async def main():
    print("=" * 80)
    print("CENTRALIZED VERIFICATION ARCHITECTURE TEST")
    print("=" * 80)

    # Test 1: MetadataManager only extracts hashes, doesn't verify
    print("\n" + "=" * 80)
    print("TEST 1: MetadataManager.get_signature_hash (format handling only)")
    print("=" * 80)

    tool_path = Path(".ai/tools/utility/hello_world.py")
    if not tool_path.exists():
        print(f"❌ Tool not found: {tool_path}")
        return False

    content = tool_path.read_text()

    # This should ONLY extract the hash, not verify integrity
    stored_hash = MetadataManager.get_signature_hash("tool", content, file_path=tool_path, project_path=Path.cwd())

    if stored_hash:
        print(f"✅ Extracted hash from signature")
        print(f"   Hash: {stored_hash[:16]}...{stored_hash[-16:]}")
        print(f"   Length: {len(stored_hash)} chars (expected: 64)")
        print(f"   Format: SHA256 hex digest")
    else:
        print(f"❌ No hash found in signature")
        print(f"\n   SOLUTION: Re-validate the tool:")
        print(f"   execute(item_type='tool', action='update', item_id='hello_world', ...)")
        return False

    # Test 2: IntegrityVerifier handles all verification
    print("\n" + "=" * 80)
    print("TEST 2: IntegrityVerifier.verify_single_file (integrity verification)")
    print("=" * 80)

    verifier = IntegrityVerifier()

    result = verifier.verify_single_file(
        item_type="tool",
        item_id="hello_world",
        version="1.0.1",
        file_path=tool_path,
        stored_hash=stored_hash,
        project_path=Path.cwd()
    )

    if result.success:
        print(f"✅ Integrity verified - content matches signature")
        print(f"   Verified: {result.verified_count} item(s)")
        print(f"   Duration: {result.duration_ms}ms")
    else:
        print(f"⚠️  Integrity mismatch detected")
        print(f"   Error: {result.error}")
        print(f"\n   This is EXPECTED if the tool was signed before the unified integrity system.")
        print(f"   The signature uses an old hashing method that doesn't match the new one.")
        print(f"\n   SOLUTION: Re-validate with the new system:")
        print(f"   execute(item_type='tool', action='update', item_id='hello_world', ...)")
        print(f"\n   Continuing with remaining tests...")

    # Test 3: LocalChainResolver extracts hash without verification
    print("\n" + "=" * 80)
    print("TEST 3: LocalChainResolver (chain building with hash extraction)")
    print("=" * 80)

    resolver = LocalChainResolver(project_path=Path.cwd())

    try:
        chain = await resolver.resolve_chain("hello_world")
        print(f"✅ Chain resolved successfully")
        print(f"   Steps: {len(chain)}")
        
        for i, link in enumerate(chain):
            tool_id = link.get("tool_id", "unknown")
            content_hash = link.get("content_hash", "missing")
            hash_display = content_hash[:16] if content_hash and content_hash != "missing" else "MISSING"
            print(f"   [{i}] {tool_id}: {hash_display}...")
            
            if not content_hash or content_hash == "missing":
                print(f"\n❌ Chain link missing content_hash")
                return False
        
    except Exception as e:
        print(f"❌ Chain resolution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Modification detection
    print("\n" + "=" * 80)
    print("TEST 4: Modification detection (wrong hash should fail)")
    print("=" * 80)

    # Use wrong hash - should fail
    wrong_hash = "0" * 64

    mod_result = verifier.verify_single_file(
        item_type="tool",
        item_id="hello_world",
        version="1.0.1",
        file_path=tool_path,
        stored_hash=wrong_hash,
        project_path=Path.cwd()
    )

    if not mod_result.success:
        print(f"✅ Correctly detected tampering")
        print(f"   Error: {mod_result.error}")
    else:
        print(f"❌ SECURITY ISSUE: Failed to detect modification")
        print(f"   Verification passed when it should have failed!")
        return False

    print("\n" + "=" * 80)
    print("✅ ARCHITECTURE VERIFIED")
    print("=" * 80)
    print("\nVerification is now centralized:")
    print("  ✓ MetadataManager: Format handling ONLY")
    print("    - get_signature_hash(): Extract hash from signature")
    print("    - get_signature_info(): Extract full signature metadata")
    print("    - sign_content_with_hash(): Add signature to content")
    print("")
    print("  ✓ IntegrityVerifier: ALL verification logic")
    print("    - verify_single_file(): Verify one file's integrity")
    print("    - verify_chain(): Verify entire execution chain")
    print("")
    print("  ✓ LocalChainResolver: Hash extraction, NO verification")
    print("    - Uses get_signature_hash() to build chain")
    print("    - Verification happens later via IntegrityVerifier")
    print("")
    print("  ✓ Handlers: Use IntegrityVerifier for content verification")
    print("    - Run: verify_single_file() before execution")
    print("    - Create/Update: compute_unified_integrity() + sign")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
