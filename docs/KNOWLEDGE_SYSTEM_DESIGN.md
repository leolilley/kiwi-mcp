# Knowledge System Design

**Date:** 2026-01-25  
**Status:** Draft  
**Author:** Kiwi Team  
**Phase:** Future (after Phase 8)

---

## Executive Summary

This document describes the RAG-based knowledge system for Kiwi MCP. The knowledge system provides:

1. **Local vector stores** for semantic search (user/project separated)
2. **Registry synchronization** for pulling knowledge from remote
3. **Help tool integration** for agent guidance via RAG queries
4. **Versioned knowledge entries** that sync like directives and tools

---

## The Problem

### Current State

The `help` tool currently provides:
- Simple keyword-based topic lookup
- Static guidance text
- Signal handling (stuck, escalate, checkpoint)

This doesn't scale:
- Limited to pre-defined topics
- Can't answer arbitrary questions about the system
- No semantic understanding of queries

### Desired State

The `help` tool uses RAG to answer any question about:
- How Kiwi MCP works
- Available directives and their usage
- Tool capabilities and parameters
- Best practices and patterns
- Troubleshooting common issues

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE SYSTEM ARCHITECTURE                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Remote Registry (Supabase)                          │ │
│  │                                                                          │ │
│  │  knowledge entries (versioned, published)                                │ │
│  │  embeddings pre-computed on publish                                      │ │
│  └───────────────────────────────────┬────────────────────────────────────┘ │
│                                      │ sync/pull                             │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Local Knowledge Stores                              │ │
│  │                                                                          │ │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────────┐  │ │
│  │  │  User Space (~/.ai/)        │  │  Project Space (.ai/)           │  │ │
│  │  │                             │  │                                  │  │ │
│  │  │  knowledge/                 │  │  knowledge/                      │  │ │
│  │  │    *.md (entries)           │  │    *.md (entries)                │  │ │
│  │  │  vectors/                   │  │  vectors/                        │  │ │
│  │  │    knowledge.db (sqlite+vec)│  │    knowledge.db (sqlite+vec)     │  │ │
│  │  └─────────────────────────────┘  └─────────────────────────────────┘  │ │
│  │                                                                          │ │
│  └───────────────────────────────────┬────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     help(action="guidance") RAG Query                   │ │
│  │                                                                          │ │
│  │  1. Embed query with local model                                         │ │
│  │  2. Search user space vectors                                            │ │
│  │  3. Search project space vectors                                         │ │
│  │  4. Combine and rank results                                             │ │
│  │  5. Return relevant knowledge chunks                                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Entry Format

### Current Format (Markdown with Frontmatter)

```yaml
---
zettel_id: directive-creation-pattern
title: Directive Creation Pattern
entry_type: pattern
version: "1.0.0"
author: kiwi-mcp
tags:
  - directives
  - patterns
  - core
references:
  - create_directive
  - anneal_directive
---

# Directive Creation Pattern

CRITICAL: Directives MUST be created through the `create_directive` directive.

## Why?

1. Validation: XML syntax and required fields are verified
2. Signing: Cryptographic signature prevents tampering
3. Registration: New directive becomes discoverable via search

## Never Do This

```python
# WRONG - creates unsigned, unvalidated directive
create_file(".ai/directives/foo.md", content)
```

## Always Do This

```
run directive create_directive with inputs:
  name: foo
  description: ...
  category: ...
```
```

### Extended Format (with Embeddings Metadata)

```yaml
---
zettel_id: directive-creation-pattern
title: Directive Creation Pattern
entry_type: pattern
version: "1.0.0"
author: kiwi-mcp
tags:
  - directives
  - patterns
  - core
references:
  - create_directive
  - anneal_directive

# Embedding metadata (computed on publish/sync)
embedding:
  model: "text-embedding-3-small"
  dimensions: 1536
  chunks: 3
  last_computed: "2026-01-25T10:00:00Z"
---
```

---

## Vector Store Implementation

### Technology Choice: sqlite-vec

Using `sqlite-vec` for local vector storage:
- No external dependencies (embeds in SQLite)
- Fast local queries
- Portable (single file per store)
- Works offline

### Schema

```sql
-- knowledge_vectors.sql
CREATE TABLE knowledge_entries (
    zettel_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    version TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,  -- JSON array
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE knowledge_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zettel_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB NOT NULL,  -- sqlite-vec format
    FOREIGN KEY (zettel_id) REFERENCES knowledge_entries(zettel_id)
);

-- Vector index for similarity search
CREATE VIRTUAL TABLE knowledge_embeddings USING vec0(
    embedding float[1536]  -- OpenAI text-embedding-3-small dimensions
);
```

### Chunking Strategy

Knowledge entries are chunked for embedding:

1. **Split by headers** - Each `##` section becomes a chunk
2. **Max chunk size** - 512 tokens (with overlap)
3. **Preserve context** - Include entry title and zettel_id in each chunk

```python
def chunk_knowledge_entry(entry: KnowledgeEntry) -> List[KnowledgeChunk]:
    """Chunk a knowledge entry for embedding."""
    chunks = []
    
    # Split by ## headers
    sections = re.split(r'\n(?=## )', entry.content)
    
    for i, section in enumerate(sections):
        # Add context prefix
        chunk_content = f"[{entry.zettel_id}] {entry.title}\n\n{section}"
        
        # Check token count
        if count_tokens(chunk_content) > 512:
            # Sub-chunk if too large
            sub_chunks = split_by_tokens(chunk_content, max_tokens=512, overlap=50)
            for j, sub in enumerate(sub_chunks):
                chunks.append(KnowledgeChunk(
                    zettel_id=entry.zettel_id,
                    chunk_index=i * 100 + j,  # Allow sub-indexing
                    content=sub
                ))
        else:
            chunks.append(KnowledgeChunk(
                zettel_id=entry.zettel_id,
                chunk_index=i,
                content=chunk_content
            ))
    
    return chunks
```

---

## Embedding Generation

### Local vs Remote Embedding

**Option 1: Local embedding (preferred)**
- Use `sentence-transformers` or similar
- No API calls needed
- Works offline
- Slightly lower quality than OpenAI

**Option 2: Remote embedding (fallback)**
- Use OpenAI `text-embedding-3-small`
- Higher quality
- Requires API key and network

### Configuration

```yaml
# .ai/config/knowledge.yaml
embedding:
  provider: local  # or "openai"
  model: "all-MiniLM-L6-v2"  # for local
  # model: "text-embedding-3-small"  # for openai
  dimensions: 384  # MiniLM is 384, OpenAI is 1536
  batch_size: 32
```

### Embedding on Sync

When knowledge is synced from registry:

```python
async def sync_knowledge_to_local(
    zettel_id: str,
    source: str = "registry"
) -> None:
    """Sync knowledge entry and update vector store."""
    
    # 1. Fetch entry from registry
    entry = await registry.get_knowledge(zettel_id)
    
    # 2. Save to local filesystem
    path = f".ai/knowledge/{entry.zettel_id}.md"
    write_knowledge_file(path, entry)
    
    # 3. Chunk the content
    chunks = chunk_knowledge_entry(entry)
    
    # 4. Generate embeddings
    embeddings = await embedding_model.embed_batch([c.content for c in chunks])
    
    # 5. Store in vector database
    await vector_store.upsert_chunks(chunks, embeddings)
```

---

## Help Tool Integration

### Enhanced Help Tool

```python
async def help(
    action: str = "guidance",
    topic: Optional[str] = None,
    query: Optional[str] = None,
    reason: Optional[str] = None,
    **kwargs
) -> dict:
    """
    Help tool with RAG-based guidance.
    
    Actions:
    - guidance: Answer questions about the system (uses RAG)
    - stuck: Signal that agent is stuck
    - escalate: Request human decision
    - checkpoint: Save state before risky action
    """
    
    if action == "guidance":
        return await _rag_guidance(query or topic)
    elif action == "stuck":
        return await _signal_stuck(reason, kwargs)
    elif action == "escalate":
        return await _signal_escalate(reason, kwargs)
    elif action == "checkpoint":
        return await _request_checkpoint(reason, kwargs)
```

### RAG Guidance Implementation

```python
async def _rag_guidance(query: str) -> dict:
    """Answer question using RAG over knowledge base."""
    
    # 1. Embed the query
    query_embedding = await embedding_model.embed(query)
    
    # 2. Search both user and project knowledge stores
    user_results = await user_vector_store.search(
        query_embedding,
        limit=5,
        min_score=0.7
    )
    project_results = await project_vector_store.search(
        query_embedding,
        limit=5,
        min_score=0.7
    )
    
    # 3. Combine and deduplicate
    all_results = merge_and_rank(user_results, project_results)
    
    # 4. Format response
    if not all_results:
        return {
            "found": False,
            "message": "No relevant knowledge found for your query.",
            "suggestion": "Try searching for directives or tools instead."
        }
    
    return {
        "found": True,
        "chunks": [
            {
                "zettel_id": r.zettel_id,
                "content": r.content,
                "score": r.score,
                "source": r.source  # "user" or "project"
            }
            for r in all_results[:3]  # Top 3 results
        ],
        "suggestion": "Review the above knowledge entries for guidance."
    }
```

---

## User Space Initialization

### First-Time Setup

When user initializes Kiwi (runs `kiwi init` or first use):

```python
async def initialize_user_space():
    """Set up user space with core knowledge."""
    
    user_ai_path = Path.home() / ".ai"
    
    # 1. Create directory structure
    (user_ai_path / "knowledge").mkdir(parents=True, exist_ok=True)
    (user_ai_path / "vectors").mkdir(parents=True, exist_ok=True)
    
    # 2. Initialize vector store
    vector_store = VectorStore(user_ai_path / "vectors" / "knowledge.db")
    await vector_store.initialize()
    
    # 3. Sync core knowledge from registry
    core_knowledge = [
        "kiwi-overview",
        "directive-creation-pattern",
        "tool-creation-pattern",
        "permission-system",
        "mcp-integration",
        "troubleshooting-guide",
    ]
    
    for zettel_id in core_knowledge:
        await sync_knowledge_to_local(
            zettel_id,
            source="registry",
            destination="user"
        )
    
    print(f"✓ User space initialized with {len(core_knowledge)} knowledge entries")
```

---

## Synchronization

### Knowledge Sync Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  sync_knowledge Command                                                      │
│                                                                              │
│  1. List all knowledge in local (user + project)                             │
│  2. Check registry for updates (version comparison)                          │
│  3. For each outdated entry:                                                 │
│     a. Download new version                                                  │
│     b. Re-chunk content                                                      │
│     c. Re-embed chunks                                                       │
│     d. Update vector store                                                   │
│  4. For new entries:                                                         │
│     a. Download and save                                                     │
│     b. Chunk and embed                                                       │
│     c. Insert into vector store                                              │
│  5. Report sync results                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Incremental Updates

When a knowledge entry is modified:

```python
async def update_knowledge_vectors(zettel_id: str) -> None:
    """Update vectors for a single knowledge entry."""
    
    # 1. Load the entry
    entry = load_knowledge_entry(zettel_id)
    
    # 2. Delete old chunks from vector store
    await vector_store.delete_by_zettel_id(zettel_id)
    
    # 3. Re-chunk and embed
    chunks = chunk_knowledge_entry(entry)
    embeddings = await embedding_model.embed_batch([c.content for c in chunks])
    
    # 4. Insert new chunks
    await vector_store.insert_chunks(chunks, embeddings)
```

---

## Query Patterns

### Search Both Stores

```python
async def search_knowledge(
    query: str,
    sources: List[str] = ["user", "project"],
    limit: int = 10,
    min_score: float = 0.6
) -> List[KnowledgeResult]:
    """Search knowledge across user and project stores."""
    
    # Embed query
    query_embedding = await embedding_model.embed(query)
    
    results = []
    
    if "user" in sources:
        user_results = await user_vector_store.search(
            query_embedding, limit=limit, min_score=min_score
        )
        for r in user_results:
            r.source = "user"
        results.extend(user_results)
    
    if "project" in sources:
        project_results = await project_vector_store.search(
            query_embedding, limit=limit, min_score=min_score
        )
        for r in project_results:
            r.source = "project"
        results.extend(project_results)
    
    # Sort by score, dedupe by zettel_id
    results.sort(key=lambda r: r.score, reverse=True)
    seen = set()
    deduped = []
    for r in results:
        if r.zettel_id not in seen:
            seen.add(r.zettel_id)
            deduped.append(r)
    
    return deduped[:limit]
```

---

## Implementation Phases

### Phase 1: Local Vector Store (2-3 days)

1. Set up sqlite-vec integration
2. Implement chunking strategy
3. Local embedding with sentence-transformers
4. Basic vector store CRUD operations

**Files:**
- `kiwi_mcp/knowledge/vector_store.py` (new)
- `kiwi_mcp/knowledge/chunker.py` (new)
- `kiwi_mcp/knowledge/embedder.py` (new)
- `tests/knowledge/test_vector_store.py` (new)

### Phase 2: User Space Initialization (1-2 days)

1. `kiwi init` command for user space setup
2. Core knowledge sync from registry
3. Vector store initialization

**Files:**
- `kiwi_mcp/cli/init.py` (new)
- `kiwi_mcp/knowledge/setup.py` (new)

### Phase 3: Help Tool RAG Integration (2 days)

1. Extend help tool with `_rag_guidance`
2. Multi-store search
3. Result formatting

**Files:**
- `kiwi_mcp/tools/help.py` (extend)
- `tests/tools/test_help_rag.py` (new)

### Phase 4: Sync Integration (1-2 days)

1. Knowledge sync directive update
2. Incremental vector updates
3. Registry integration for versioned knowledge

**Files:**
- `.ai/directives/core/sync_knowledge.md` (update)
- `kiwi_mcp/knowledge/sync.py` (new)

---

## Success Metrics

- [ ] Local vector store working with sqlite-vec
- [ ] Knowledge entries chunked and embedded on sync
- [ ] `help(action="guidance", query="how do I create a directive?")` returns relevant content
- [ ] User and project knowledge stores queried separately and together
- [ ] Sync updates vectors correctly for modified entries
- [ ] Works fully offline after initial sync

---

## Related Documents

- `THREAD_AND_STREAMING_ARCHITECTURE.md` - Thread and streaming design
- `RUNTIME_PERMISSION_DESIGN.md` - Permission enforcement
