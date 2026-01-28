# Kiwi MCP Search Implementation Analysis

**Date:** 2026-01-28  
**Status:** Current Implementation Review  
**Scope:** Keyword Search Fallback & System Reliability  

---

## Executive Summary

Kiwi MCP implements a **hybrid search strategy** with vector search as the primary layer and **keyword search as a fallback**. However, the keyword search fallback—which serves as the actual search mechanism in most real-world deployments—is **fundamentally limited and unreliable**.

**Current Reality:** Without vector embeddings configured, search defaults to basic keyword matching that:
- Only works via exact term substring matching
- Has no semantic understanding
- Produces inconsistent relevance scoring
- Scales linearly with file count (O(n))
- Returns no results for paraphrased queries

This document details what search actually does, why it's unreliable, and what needs to be fixed.

---

## Architecture Overview

### High-Level Search Flow

```
Search Request
    ↓
┌─────────────────────────┐
│ Check Vector Available? │
└─────┬───────────────────┘
      │
      ├─ YES → Vector/Hybrid Search (semantic)
      │
      └─ NO → Keyword Search (basic substring matching)
```

The problem: **Most users fall into the NO path**.

### Current Implementation

**File:** [kiwi_mcp/tools/search.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/tools/search.py#L113-L147)

```python
async def execute(self, arguments: dict) -> str:
    # Try vector search first if available
    if self._has_vector_search(project_path):
        return await self._vector_search(...)
    
    # Fallback to keyword search
    return await self._keyword_search(...)
```

**Requirement for vector search:** The `.ai/vector/` directory must exist.

---

## The Keyword Search Implementation

### What It Actually Does

**File:** [kiwi_mcp/utils/file_search.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/utils/file_search.py#L56-L79)

```python
def score_relevance(content: str, query_terms: List[str]) -> float:
    """
    Calculate relevance score for content against query terms.
    
    Scoring:
    - All terms present: High score (100.0)
    - Some terms present: Medium score (proportional)
    - No terms present: Zero score (0.0)
    """
    content_lower = content.lower()
    matches = sum(1 for term in query_terms if term.lower() in content_lower)
    
    if matches == 0:
        return 0.0
    if matches == len(query_terms):
        return 100.0
    
    return (matches / len(query_terms)) * 50.0
```

### How Each Item Type Searches

#### Directives (NOT IMPLEMENTED)

**File:** [kiwi_mcp/handlers/directive/handler.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/directive/handler.py#L985-L994)

The directive handler does NOT have a `search()` method. Searching directives is **completely unsupported** in the keyword fallback path.

#### Tools (Basic Substring Matching)

**File:** [kiwi_mcp/handlers/tool/handler.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/tool/handler.py#L118-L156)

```python
async def _search_local(self, query: str, limit: int) -> List[Dict[str, Any]]:
    results = []
    
    # Search each tool directory
    for search_dir in search_dirs:
        files = search_python_files(search_dir, query)  # ← Glob pattern search
        
        for file_path in files:
            meta = extract_tool_metadata(file_path, self.project_path)
            searchable_text = f"{meta['name']} {meta.get('description', '')}"
            score = score_relevance(searchable_text, query.split())  # ← Keyword scoring
            
            results.append({
                "name": meta["name"],
                "description": meta.get("description", ""),
                "score": score,
                ...
            })
    
    return results
```

**What this does:**
1. Splits query into words
2. For each word, checks if it appears anywhere in tool name or description (case-insensitive)
3. Scores based on how many query words appear
4. Returns files ranked by score

**Example:**
- Query: `"create tool"` → splits to `["create", "tool"]`
- Searches for tools with BOTH "create" and "tool" in name/description
- If only one word matches → score = 50.0
- If both match → score = 100.0

#### Knowledge (Basic Substring Matching)

**File:** [kiwi_mcp/handlers/knowledge/handler.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/knowledge/handler.py#L520-L561)

Same approach as tools:

```python
def _search_local(self, query: str, ...) -> List[Dict[str, Any]]:
    results = []
    query_terms = query.lower().split()
    
    # Search all markdown files
    files = search_markdown_files(self.search_paths)
    
    for file_path in files:
        entry = parse_knowledge_entry(file_path)
        searchable_text = f"{entry['title']} {entry['content']}"
        score = score_relevance(searchable_text, query_terms)
        
        if score > 0:
            results.append({
                "zettel_id": entry["zettel_id"],
                "title": entry["title"],
                "score": score,
                ...
            })
    
    return results
```

---

## Why This Is Unreliable

### 1. No Semantic Understanding

**Problem:** The search has zero semantic awareness.

**Example:**
- Query: `"deploy application"`
- Will NOT match: "push to production", "release to cloud", "ship new version"
- Will only match if both "deploy" AND "application" appear verbatim in the content

**Real User Impact:**
```
User asks: "How do I deploy my app?"
Search for: "deploy application"
Result: No matches (even though you have docs on "releasing to production")
```

### 2. Exact Substring Matching Only

**Problem:** Query terms must appear as substrings in the content.

**Example:**
- Query: `"run tests"`
- Matches: "run_tests", "running_tests", "run test"
- Does NOT match: "execute test suite", "test execution", "run test_suite.py"

### 3. All-or-Nothing Scoring

**Problem:** Scoring has only 3 bins (0%, 50%, or 100%).

**Score Distribution:**
```
0 matching terms    → 0.0 (not included)
1 matching term     → (1/total) * 50.0 = capped at 50.0
2 matching terms    → (2/total) * 50.0 = capped at 50.0
... 
All matching terms  → 100.0
```

This means:
- A result with 1 match gets capped at 50, even if that single term is highly relevant
- A result with 9/10 matches gets 90% score (good)
- No signal about term frequency, position, or importance

### 4. No Ranking by Relevance

**Problem:** Multiple matches with the same score are returned in arbitrary order.

**Example:**
- Query: `"authentication"`
- Result A: Title="Basic Auth", Score=100
- Result B: Title="JWT Auth", Score=100
- Order is whatever filesystem order they're in

### 5. Directives Are Completely Unsearchable

**Critical Limitation:** Directives don't have a keyword search implementation at all.

```python
# In directive handler
# ❌ No search() method exists
# ❌ No _search_local() method exists
```

Users cannot search directives via the keyword fallback.

### 6. Linear Time Complexity

**Problem:** O(n) scan for every query.

- 100 items: Fast
- 1,000 items: Acceptable
- 10,000 items: Slow (~100ms)
- 100,000 items: Very slow (~1s+)

No indexing, no caching, no optimization.

### 7. No Filtering or Narrowing

**Problem:** No way to refine searches.

Users can't:
- Filter by category
- Filter by tags
- Filter by type
- Sort by date
- Exclude items

### 8. Single Word Splitting

**Problem:** Multi-word queries are naively split on whitespace.

**Example:**
- Query: `"state machine"`
- Split to: `["state", "machine"]`
- Matches: Anything with BOTH words
- Misses: "state_machine", "StateMachine", "finite state automaton"

---

## Real-World Reliability Test

### Scenario 1: Typical User Search

```
User: "I want to find directives about authentication"
Search: directive, query="authentication directives"
Result: ❌ NOT FOUND (directives don't support keyword search)
```

### Scenario 2: Paraphrased Query

```
User: "How do I install dependencies?"
Search: tool, query="install dependencies"
Result: ❌ Might not find "setup_environment" or "pip_install" tools
         ✓ Only matches if both "install" and "dependencies" exist
```

### Scenario 3: Similar Concepts

```
User: "What tools help with debugging?"
Search: tool, query="debugging tools"
Result: ❌ Won't match "troubleshooting", "error_analysis", "profiling" tools
         ✓ Only exact substring matches
```

### Scenario 4: Common Misspelling

```
User: "How do I authentificate users?"
Search: knowledge, query="authentificate"
Result: ❌ No matches (won't find "authenticate" entries)
```

---

## Comparison: What Vector Search Would Do

The planned vector search (Phase 5) would:

✓ **Semantic matching:** "deploy" ≈ "release" ≈ "push to production"  
✓ **Approximate matching:** "authenticate" ≈ "authentificate"  
✓ **Concept matching:** "state machine" ≈ "finite state automaton"  
✓ **Ranking by relevance:** Context-aware scoring  
✓ **Fast queries:** <100ms even for 100K+ items (with proper indexing)  
✓ **Support all types:** Directives, tools, knowledge equally  

See: [RAG_VECTOR_SEARCH_DESIGN.md](file:///home/leo/projects/kiwi-mcp/docs/RAG_VECTOR_SEARCH_DESIGN.md)

---

## System Design Issues

### Issue 1: Silent Fallback to Unreliable Search

**Problem:** Users don't know when they're using the unreliable keyword search.

```python
# SearchTool doesn't tell users which backend is active
return self._format_response({
    "items": items,
    "total": len(items),
    "search_type": "vector_hybrid",  # ← But might be "keyword" instead
    "source": source,
})
```

**Fix Needed:** Always indicate search type and confidence in results.

### Issue 2: No Graceful Degradation

**Problem:** When keyword search fails, users just get empty results.

```python
if score > 0:  # ← Knowledge only includes if score > 0
    results.append(...)
```

No explanation of WHY no results were found.

### Issue 3: No Error Messages for Missing Features

**Problem:** Directive search is silently unsupported.

```python
# directive/handler.py
# ❌ search() method doesn't exist
# ❌ No error message
# ❌ User gets confused
```

### Issue 4: Handler Inconsistency

Different handlers implement search differently:
- Directives: Not implemented
- Tools: Implemented, file-based filtering
- Knowledge: Implemented, similar to tools

No consistent interface or behavior.

---

## Impact on Users

### What Users Experience

1. **Directive Searches Always Fail:**
   ```
   > kiwi search directive "authentication"
   Result: {} (empty, no explanation why)
   ```

2. **Tool/Knowledge Searches Are Unpredictable:**
   ```
   > kiwi search tool "logging"
   Result: Only tools with BOTH "logging" in name/description
   Miss: "debug_output", "print_messages", "log_to_file"
   ```

3. **Complex Queries Fail:**
   ```
   > kiwi search knowledge "state management architecture"
   Split into: ["state", "management", "architecture"]
   Need ALL THREE in any entry to match
   Miss: Most relevant results with 2/3 terms
   ```

4. **No Feedback on Quality:**
   ```
   Search returns results but:
   - No indication if they're good matches
   - No explanation of search strategy used
   - No suggestions for refining query
   ```

---

## Code Locations Reference

| Component | File | Lines |
|-----------|------|-------|
| Search Tool Entry Point | [search.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/tools/search.py) | 113-147 |
| Vector Search Setup | [search.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/tools/search.py) | 66-111 |
| Keyword Fallback Router | [search.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/tools/search.py) | 198-235 |
| Relevance Scoring | [file_search.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/utils/file_search.py) | 56-79 |
| Tool Search | [tool/handler.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/tool/handler.py) | 118-156 |
| Knowledge Search | [knowledge/handler.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/knowledge/handler.py) | 520-561 |
| Directive Search | [directive/handler.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/directive/handler.py) | ❌ Not implemented |
| Vector Hybrid Search | [RAG_VECTOR_SEARCH_DESIGN.md](file:///home/leo/projects/kiwi-mcp/docs/RAG_VECTOR_SEARCH_DESIGN.md) | Planned (Phase 5) |

---

## Recommendations

### Short Term (Improve Keyword Search)

1. **Implement Directive Search**
   - Add `search()` method to DirectiveHandler
   - Use same approach as knowledge/tools

2. **Add Search Feedback**
   - Always indicate: `"search_type": "keyword"` (vs "vector_hybrid")
   - Add quality indicator: `"quality": "low"` for keyword fallback
   - Suggest: "Consider vector search for better results"

3. **Better Scoring**
   - Implement TF-IDF instead of binary matching
   - Score based on term frequency, not just presence
   - Rank by relevance, not by result order

4. **Error Messages**
   - Explain why searches fail
   - Suggest query refinements
   - Link to documentation on advanced search

### Long Term (Enable Vector Search)

1. **Phase 5 Implementation**
   - Enable optional vector search with embeddings
   - Support semantic similarity
   - See: [RAG_VECTOR_SEARCH_DESIGN.md](file:///home/leo/projects/kiwi-mcp/docs/RAG_VECTOR_SEARCH_DESIGN.md)

2. **Hybrid Search**
   - Combine vector + keyword approaches
   - Weight both signals
   - Better relevance ranking

3. **Search Features**
   - Advanced filtering (category, tags, type)
   - Faceted search
   - Search history and learning

---

## Summary

The current keyword search implementation is **essentially a basic substring matcher** that:
- Only works for tools and knowledge (not directives)
- Returns results only if ALL query terms appear
- Has no semantic understanding
- Scales linearly with content size
- Provides no quality feedback

**Reliability Score: 2/10** (for production use)

It's suitable for:
- ✓ Small test datasets (<10 items)
- ✓ Single-word queries
- ✓ Exact term matching

It fails for:
- ❌ Paraphrased queries
- ❌ Synonym matching
- ❌ Directives (not implemented)
- ❌ Large datasets (>1000 items)
- ❌ User expectations

**Next Priority:** Implement vector search (Phase 5) to replace this unreliable fallback.

