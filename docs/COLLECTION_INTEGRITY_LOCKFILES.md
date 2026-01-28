# Collection Integrity, Signing & Lockfiles

**Date:** 2026-01-28  
**Version:** 0.2.0  
**Purpose:** Security, integrity, and reproducibility for bundled collections

---

## Executive Summary

Collections integrate **three security layers**:

1. **Individual Item Hashing** - Each tool/directive/knowledge has integrity hash
2. **Collection Signing** - The entire collection manifest is cryptographically signed
3. **Lockfiles** - Pin exact versions + hashes for reproducible installs

Together these ensure:
- **Tamper Detection**: Any modification detected
- **Reproducibility**: Exact same bits installed every time
- **Trust**: Verified collections from known sources
- **Traceability**: Complete audit trail of what was installed

---

## Part 1: Individual Item Integrity (Per Content)

### Each Item Has a Hash

Every directive, tool, and knowledge entry in a collection is individually signed with a hash:

```
Tool: parser.py
├── Content Hash (SHA256): abc123...def456
├── Manifest Hash: 789xyz...uvw...
└── Location Path: tools/parser.py
    ├── Included in hash (prevents relocation)
    └── Any move = hash mismatch = requires re-signing

Directive: process-data.md
├── XML Content Hash: abc999...
├── Metadata Hash: xyz888...
├── Location Path: directives/process-data.md
└── Signature: kiwi-mcp:validated:2026-01-28:abc999...

Knowledge: batch-patterns.md
├── Content Hash: def777...
├── Metadata Hash: ghi666...
├── Category: patterns
├── Location Path: knowledge/patterns/batch-patterns.md
└── Signature: kiwi-mcp:validated:2026-01-28:def777...
```

### Signature Format (Embedded in Files)

**All items embedded with validation signature:**

```markdown
<!-- kiwi-mcp:validated:2026-01-28T10:30:00Z:96440106d21b93926bd00feca333b138871a2ec959f2fe5a444d86bf0e5c58e0 -->
```

**Structure:**
```
kiwi-mcp:validated:TIMESTAMP:HASH
├── TIMESTAMP = ISO 8601 (when signed)
├── HASH = SHA256 of canonical content
└── Detects any modification since signing
```

### Hash Computation Includes

**For Tools:**
```json
{
  "tool_id": "parser",
  "version": "1.0.0",
  "manifest": {...manifest metadata...},
  "files": [
    {"path": "tools/parser.py", "sha256": "..."}
  ],
  "location_path": "tools/parser.py"
}
```

**For Directives:**
```json
{
  "directive_name": "process-csv",
  "version": "1.0.0",
  "xml_hash": "...",
  "location_path": "directives/process-csv.md"
}
```

**For Knowledge:**
```json
{
  "zettel_id": "20260128-batch-patterns",
  "version": "1.0.0",
  "content_hash": "...",
  "metadata": {"category": "patterns", "entry_type": "pattern"},
  "location_path": "knowledge/patterns/batch-patterns.md"
}
```

### Verification Flow During Install

```
User: lilux install github://user/collection

1. Download collection
2. For each item in collection:
   a) Read signature from file
   b) Compute current hash
   c) Compare: signature_hash == current_hash?
   d) If NO → Reject (item modified or moved)
   e) If YES → Install item

3. If any item fails verification:
   "ERROR: Item 'tools/parser.py' signature invalid"
   "Reason: Content modified since signing"
   "Solution: Ask collection author to re-sign"
```

---

## Part 2: Collection Manifest Signing

### Collection Manifest (collection.toml)

The manifest lists all content + their hashes:

```toml
[metadata]
name = "data-tools"
version = "1.0.0"
description = "Data processing collection"
author = "team@example.com"
license = "MIT"
source = "https://github.com/example/data-tools"

# Manifest signature
[manifest]
signed = true
timestamp = "2026-01-28T10:30:00Z"
hash = "manifest_abc123..."
signer = "team@example.com"

[content]
# Each item with its hash
[content.directives]
"process-csv.md" = {hash = "abc123...", version = "1.0.0"}
"validate.md" = {hash = "def456...", version = "1.0.0"}

[content.tools]
"parser.py" = {hash = "ghi789...", version = "1.0.0"}
"validator.py" = {hash = "jkl012...", version = "1.0.0"}

[content.knowledge]
"patterns/batch.md" = {hash = "mno345...", version = "1.0.0"}

[dependencies]
core = {version = ">=0.1.0", hash = "core_hash_..."}
```

### Collection Signature File

Separate `.collection.sig` file alongside `collection.toml`:

```
collection.toml.sig
├── Signature: RSA/ECDSA of manifest
├── Public Key Fingerprint: ABC123...
├── Signer Identity: team@example.com
├── Timestamp: 2026-01-28T10:30:00Z
└── All items' hashes included in signature
```

### Manifest Verification

```python
# During install
def verify_collection_manifest(collection_path: Path) -> bool:
    """Verify collection manifest integrity"""
    
    # 1. Load manifest
    manifest = load_toml(collection_path / "collection.toml")
    
    # 2. Load signature
    sig = load_signature(collection_path / "collection.toml.sig")
    
    # 3. Compute manifest hash
    manifest_content = (collection_path / "collection.toml").read_text()
    computed_manifest_hash = sha256(manifest_content).hexdigest()
    
    # 4. Verify signature
    if not verify_signature(manifest, sig):
        raise SignatureError("Collection manifest signature invalid")
    
    # 5. Verify each item's hash
    for item_type, items in manifest["content"].items():
        for item_name, item_meta in items.items():
            item_path = collection_path / get_item_path(item_type, item_name)
            item_content = item_path.read_text()
            
            # Extract stored hash from item's embedded signature
            stored_hash = extract_signature_hash(item_content)
            
            # Compute current hash
            computed_hash = compute_unified_integrity(
                item_type=item_type,
                item_id=item_name,
                content=item_content,
                location_path=str(item_path.relative_to(collection_path))
            )
            
            # Compare
            if stored_hash != computed_hash:
                raise IntegrityError(f"Item {item_name} integrity failed")
    
    return True
```

---

## Part 3: Lockfiles (Reproducibility)

### Lockfile Purpose

A **lockfile** pins exact versions and hashes for reproducible installs:

```
~/.local/share/lilux/collections/my-workspace.lock
├── Collection pinning
├── Dependency resolution
├── Hash verification
└── Reproducible reinstalls
```

### Lockfile Format

```yaml
# Collection lockfile
version: "1"
generated: "2026-01-28T10:30:00Z"
lilux_version: ">=0.1.0"

# Root collection
root:
  name: "my-workspace"
  source: "github://user/my-workspace"
  version: "1.0.0"
  hash: "collection_root_hash_..."
  installed_at: "~/.local/share/lilux/collections/user-my-workspace"

# Resolved dependencies (tree)
dependencies:
  - name: "rye-core"
    source: "rye://core"
    version: "0.1.0"
    hash: "rye_core_hash_..."
    installed_at: "~/.local/share/lilux/collections/rye-core"
    
  - name: "ml-utils"
    source: "github://user/ml-utils"
    version: "1.0.0"
    hash: "ml_utils_hash_..."
    installed_at: "~/.local/share/lilux/collections/github-user-ml-utils"
    dependencies:
      - "rye-core"  # Transitive dependency

# Content inventory (for verification)
content:
  directives:
    - name: "process-csv"
      path: "directives/process-csv.md"
      version: "1.0.0"
      hash: "abc123..."
      source: "user-my-workspace"
      
    - name: "validate"
      path: "directives/validate.md"
      version: "1.0.0"
      hash: "def456..."
      source: "user-my-workspace"
  
  tools:
    - name: "parser"
      path: "tools/parser.py"
      version: "1.0.0"
      hash: "ghi789..."
      source: "user-my-workspace"
  
  knowledge:
    - name: "batch-patterns"
      path: "knowledge/patterns/batch.md"
      version: "1.0.0"
      hash: "mno345..."
      source: "user-my-workspace"

# Verification status
verification:
  status: "verified"
  timestamp: "2026-01-28T10:30:00Z"
  all_signatures_valid: true
  all_hashes_match: true
```

### Lockfile Usage

**Create lockfile:**
```bash
$ cd my-project
$ lilux lock --collection my-workspace
Creating lockfile: my-project/lilux.lock

✓ Resolved dependencies (3 collections, 12 items)
✓ Verified all signatures
✓ Computed content hashes
✓ Locked to lilux.lock

Next: lilux install --lock lilux.lock
```

**Reproduce exact install:**
```bash
$ lilux install --lock lilux.lock

Installing from lockfile: lilux.lock
├── Fetching rye-core@0.1.0 (hash: rye_core_hash_...)
├── Verifying signature
├── Installing 5 items
├── Fetching user-ml-utils@1.0.0 (hash: ml_utils_hash_...)
├── Verifying signature
├── Installing 3 items
└── ✓ All items verified and installed

Content identical to: 2026-01-28T10:30:00Z
```

### Lockfile Guarantees

```
lilux.lock
├── Same versions installed ✓
├── Same hashes computed ✓
├── Same files bit-for-bit identical ✓
└── Same behavior guaranteed ✓
```

**Reproducibility benefits:**
- CI/CD pipelines deterministic
- Team consistency (everyone same content)
- Regression testing (known good state)
- Rollback (previous lock file)

---

## Part 4: Signature Chain

### Hierarchy

```
Collection.toml
├── Signed by: Collection author
├── Contains: Manifest hash + all item hashes
└── Verifies: Entire collection integrity

├── Item 1 (tool.py)
│   ├── Signed by: Item author (often same)
│   ├── Embedded signature: kiwi-mcp:validated:...HASH
│   └── Verifies: This specific item

├── Item 2 (directive.md)
│   └── Same pattern

└── Item 3 (knowledge.md)
    └── Same pattern

Verification Flow:
1. Verify Collection.toml.sig (top level)
2. Verify each item's embedded signature (item level)
3. If both pass → Entire collection trusted
4. If either fails → Collection rejected
```

### Signature Verification Levels

**Level 1: Item-Only (Fast)**
```python
# Just verify individual items
for item_path in collection_items:
    verify_embedded_signature(item_path)
# Fast, works offline, no network
```

**Level 2: Collection (Trusted Source)**
```python
# Verify collection manifest
verify_collection_signature(collection_path / "collection.toml.sig")
# Ensures all items listed + hashes match
```

**Level 3: Trust Chain (Strict)**
```python
# Verify collection author
verify_author_key_in_keyring(collection.author)
# Only install from trusted authors
```

---

## Part 5: Signing Collections (Author Workflow)

### Step 1: Organize Collection

```bash
mkdir data-tools
cd data-tools

mkdir directives tools knowledge
# Create content...
```

### Step 2: Create Manifest

```bash
$ cat > collection.toml << 'EOF'
[metadata]
name = "data-tools"
version = "1.0.0"
author = "me@example.com"

[content]
directives = [
    "directives/process.md",
]
tools = [
    "tools/parser.py",
]
knowledge = [
    "knowledge/batch.md",
]
EOF
```

### Step 3: Sign Individual Items

```bash
# Sign each item
$ lilux sign item directives/process.md
✓ Signed: kiwi-mcp:validated:2026-01-28T10:30:00Z:abc123...

$ lilux sign item tools/parser.py
✓ Signed: kiwi-mcp:validated:2026-01-28T10:30:00Z:def456...

$ lilux sign item knowledge/batch.md
✓ Signed: kiwi-mcp:validated:2026-01-28T10:30:00Z:ghi789...
```

### Step 4: Sign Collection Manifest

```bash
# Sign entire collection
$ lilux sign collection collection.toml

Generating manifest...
├── directives/process.md (hash: abc123...)
├── tools/parser.py (hash: def456...)
└── knowledge/batch.md (hash: ghi789...)

Creating collection.toml.sig...
├── Manifest hash: mno345...
├── Signer: me@example.com
├── Timestamp: 2026-01-28T10:30:00Z
└── ✓ Signed

Files to publish:
├── collection.toml
├── collection.toml.sig (NEW)
└── All items (with embedded signatures)
```

### Step 5: Publish

```bash
# Git commit
$ git add .
$ git commit -m "Release 1.0.0"
$ git tag v1.0.0
$ git push

# Now installable
$ lilux install github://me/data-tools@1.0.0
```

---

## Part 6: Installing with Verification

### Installation Flow

```
$ lilux install github://user/data-tools

Step 1: Fetch Collection
├── Clone/download from source
└── Hash collection.toml against known hash (if cached)

Step 2: Verify Collection Manifest
├── Load collection.toml.sig
├── Verify RSA/ECDSA signature
├── Check manifest hash = computed hash
└── Extract all item hashes from manifest

Step 3: Verify Individual Items
├── For each directive/tool/knowledge:
│   ├── Read embedded signature
│   ├── Extract hash from signature
│   ├── Compute current content hash
│   ├── Compare: signature_hash == computed_hash?
│   └── If mismatch: REJECT
└── All items verified → Continue

Step 4: Resolve Dependencies
├── Load [dependencies] from manifest
├── Recursively verify dependencies
└── Build dependency tree

Step 5: Create Lockfile (Optional)
├── Record all versions + hashes
├── Save to lilux.lock
└── Enable reproducible reinstalls

Step 6: Install Content
├── Copy items to user space
├── Update local registry metadata
└── Index for search

Step 7: Verification Report
✓ Collection: data-tools v1.0.0
✓ Signer: user@example.com
✓ All signatures valid
✓ Items installed:
  ├── 3 directives
  ├── 2 tools
  └── 1 knowledge entry
✓ Dependencies resolved: rye-core v0.1.0
✓ Lockfile created: lilux.lock
```

### Security Checks

```python
def install_collection_secure(collection_url: str) -> InstallResult:
    """Install with full security verification"""
    
    # 1. Fetch collection
    collection = fetch_collection(collection_url)
    
    # 2. Basic structure check
    if not collection.has_file("collection.toml"):
        raise ManifestError("Missing collection.toml")
    
    # 3. Verify manifest signature
    if not verify_collection_signature(collection):
        raise SignatureError("Collection manifest signature invalid")
    
    # 4. Verify each item
    manifest = load_manifest(collection)
    for item_type, items in manifest["content"].items():
        for item_name, item_meta in items.items():
            item_path = collection.get_item_path(item_type, item_name)
            
            # Verify embedded signature
            if not verify_item_signature(item_path, item_meta["hash"]):
                raise IntegrityError(f"Item {item_name} integrity check failed")
    
    # 5. Verify dependencies
    for dep in manifest.get("dependencies", []):
        install_collection_secure(dep["source"])  # Recursive
    
    # 6. Create lockfile
    lockfile = create_lockfile(collection, manifest)
    save_lockfile(lockfile)
    
    # 7. Install
    install_items(collection, manifest)
    
    return InstallResult(
        collection=collection_url,
        status="success",
        items_installed=count_items(manifest),
        lockfile_path=lockfile.path,
        signatures_verified=True
    )
```

---

## Part 7: Mismatch Handling

### Scenarios

**Scenario 1: Item Modified After Signing**

```
$ lilux install github://user/data-tools

ERROR: Item 'tools/parser.py' signature mismatch
├── Expected hash: abc123...
├── Computed hash: def456...
├── Reason: File modified or corrupted

Solution:
1. Ask collection author to re-sign
2. Or: Use local collection.py without verification
```

**Scenario 2: Item Moved**

```
$ lilux install github://user/data-tools

ERROR: Item location invalid
├── Expected: tools/parser.py
├── Found: old-tools/parser.py
├── Reason: File path included in hash

Solution:
1. Move file back to original location
2. Re-sign if location intentionally changed
```

**Scenario 3: Dependency Version Conflict**

```
$ lilux install my-collection

ERROR: Dependency version mismatch
├── my-collection requires: ml-utils >= 1.0.0
├── Found in lockfile: ml-utils = 0.5.0
├── Reason: Lockfile from older install

Solution:
1. Update lockfile: lilux lock my-collection
2. Reinstall: lilux install --lock lilux.lock
```

---

## Part 8: Trust Model

### Who Signs What

```
Official Collections (RYE Core)
├── Signed by: Lilux Core Team
├── Key Fingerprint: ABC123...OFFICIAL
├── Trust Level: Maximum
└── Used for: Core directives, tools, knowledge

Community Collections (GitHub)
├── Signed by: Collection Author
├── Key Fingerprint: Varies per author
├── Trust Level: Depends on author verification
└── Used for: Domain-specific, specialized content

Local Collections (User Space)
├── Signed by: Local user
├── Key Fingerprint: User's key
├── Trust Level: User trusts themselves
└── Used for: Personal, experimental content
```

### Verification Levels

```yaml
# lilux config
security:
  # Level 1: Item-only (fast, no network)
  verify_items: true
  
  # Level 2: Collection manifest
  verify_manifest: true
  
  # Level 3: Author trust chain
  verify_author: false  # Optional
  
  # Trusted authors
  trusted_authors:
    - "core@lilux.dev"  # Core team
    - "me@example.com"  # Self
  
  # Untrusted collections (always prompt)
  untrusted_require_prompt: true
```

---

## Part 9: Implementation Checklist

### Phase 1: Foundation (0.2.0)
- [x] Individual item signing (directives, tools, knowledge)
- [x] Hash computation with location path
- [x] Embedded signature format
- [ ] Collection manifest (collection.toml)
- [ ] Manifest signing (collection.toml.sig)
- [ ] Manifest verification

### Phase 2: Security (0.3.0)
- [ ] Lockfile format and generation
- [ ] Lockfile-based installation
- [ ] Dependency resolution tracking
- [ ] RSA/ECDSA manifest signing
- [ ] Author key fingerprints
- [ ] Trust model configuration

### Phase 3: Advanced (0.4.0+)
- [ ] Key management UI
- [ ] Author verification workflow
- [ ] Signature chain validation
- [ ] Revocation support
- [ ] Audit logging

---

## Part 10: Summary

### Security Stack

```
Collection Installation
    ↓
1. Verify Collection Manifest
   └── RSA/ECDSA signature of manifest
       + all item hashes
    ↓
2. Verify Each Item
   └── Embedded signature in each file
       + recomputed hash match
    ↓
3. Resolve Dependencies
   └── Recursively verify each dep
    ↓
4. Create Lockfile
   └── Pin exact versions + hashes
    ↓
5. Install & Index
   └── Content verified and ready
```

### Key Guarantees

- **Tamper Detection**: Any modification detected immediately
- **Location Awareness**: Moving files = hash mismatch
- **Signature Chain**: Top-level + item-level verification
- **Reproducibility**: Lockfiles enable exact reinstalls
- **Traceability**: Complete audit trail (who signed, when)
- **Offline Verification**: Works without network access

---

## Related Docs

- [HASH_VALIDATION_SYSTEM.md](./HASH_VALIDATION_SYSTEM.md) - Detailed hash system
- [REGISTRY_BUNDLING_STRATEGY.md](./REGISTRY_BUNDLING_STRATEGY.md) - Collections & distribution
- [TOOL_CHAIN_VALIDATION_DESIGN.md](./TOOL_CHAIN_VALIDATION_DESIGN.md) - Chain validation

---

_Document Status: Design for Implementation_  
_Last Updated: 2026-01-28_  
_Next: Implement collection manifest signing + lockfile system_
