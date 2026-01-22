# MCP 2.0 & 2.5 Design: Intent-Based Tool Calling

**Date:** 2026-01-22  
**Status:** Approved  
**Author:** Kiwi Team  
**Phases:** 12 (Weeks 25-27) & 13 (Weeks 28-30)

---

## Executive Summary

As Kiwi MCP scales to millions of directives and tools, traditional tool calling breaks down:
- Agents can't hold all tool schemas in context
- Syntax hallucinations increase with tool count
- Every agent must "know" every tool

**MCP 2.0** solves this by abstracting tool calling from syntax to intent. Agents express _what_ they want (`[TOOL: search for email scripts]`), and a specialized model (FunctionGemma) resolves to actual tool calls.

**MCP 2.5** adds predictive pre-fetching: while agents generate responses, we predict likely tool intents and pre-fetch search results, enabling shortcuts that reduce latency by 30%+.

---

## Part 1: The Problem

### Current Tool Calling Model

```
Agent Context (limited to ~200K tokens)
├── System prompt (AGENTS.md)
├── Tool schemas (4 meta-tools × ~500 tokens each)
├── Conversation history
└── Working space for reasoning
```

With 4 meta-tools, this works fine. But as we add:
- MCP routing (Phase 4) → External MCP schemas
- Tool manifests (Phase 1-2) → Python/Bash/API tool schemas
- Directive executor (Phase 6) → Subagent tool injection

...the schema overhead explodes.

### The Scale Problem

| Scale | Tool Schemas | Context Overhead | Problem |
|-------|--------------|------------------|---------|
| Current | 4 meta-tools | ~2K tokens | ✅ Works |
| Phase 4 | +50 MCP tools | ~27K tokens | ⚠️ Tight |
| Phase 6 | +100 local tools | ~52K tokens | 🔴 Critical |
| Future | 1M+ registry | Impossible | 💀 Broken |

### Symptoms at Scale

1. **Context crowding**: Less room for actual reasoning
2. **Syntax hallucinations**: Agents invent tool args
3. **Inconsistent behavior**: Different models handle schemas differently
4. **Slow iteration**: Adding tools requires prompt updates everywhere

---

## Part 2: MCP 2.0 - Intent Abstraction

### The Core Insight

Instead of:
```
Agent: <tool_call name="mcp__kiwi_mcp__execute">
         <item_type>script</item_type>
         <action>run</action>
         <item_id>google_maps_scraper</item_id>
         <parameters>{"query": "tech companies", "limit": 50}</parameters>
       </tool_call>
```

We allow:
```
Agent: To find leads, I need [TOOL: run the google maps scraper for tech companies, limit 50]
```

The harness intercepts this intent and resolves it to the actual tool call.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MCP 2.0 Architecture                            │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Front-End Agent (Any LLM)                   │  │
│  │  • Minimal tool knowledge (4 meta-tools)                       │  │
│  │  • Expresses intents in natural language                       │  │
│  │  • Output: "I need [TOOL: description of what I want]"         │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                  │                                   │
│                                  ▼                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Intent Parser                               │  │
│  │  • Regex: \[TOOL:\s*(.+?)\]                                   │  │
│  │  • Extracts: intent string + surrounding context               │  │
│  │  • Passes to resolver with conversation history                │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                  │                                   │
│                                  ▼                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Schema Discovery (RAG)                      │  │
│  │  • Query vector store (Phase 5) for relevant schemas           │  │
│  │  • Filter by item_type, permissions, availability              │  │
│  │  • Return top-K candidates (~10)                               │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                  │                                   │
│                                  ▼                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    FunctionGemma (Tool Resolver)               │  │
│  │  • Specialized small LLM (Gemma 2B/7B fine-tuned)              │  │
│  │  • Input: intent + context + candidate schemas                 │  │
│  │  • Output: validated tool call XML                             │  │
│  │  • Optimized for structured output, not reasoning              │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                  │                                   │
│                                  ▼                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Tool Executor (Existing)                    │  │
│  │  • Receives validated tool call                                │  │
│  │  • Routes through Kiwi proxy (audit, permissions)              │  │
│  │  • Returns result to agent                                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Intent Syntax

Agents express tool needs with a simple bracket syntax:

```
[TOOL: <natural language description of what you need>]
```

**Examples:**
```
[TOOL: search for directives about email campaigns]
[TOOL: run the deploy_staging script with environment=production]
[TOOL: load the knowledge entry about API rate limiting]
[TOOL: create a new script called lead_enricher that uses Apollo API]
```

**Why this syntax:**
- Easy to detect with regex: `\[TOOL:\s*(.+?)\]`
- Natural to write (agents don't need to learn it)
- Unambiguous (won't conflict with code or markdown)
- Nestable if needed: `[TOOL: run [TOOL: search for latest deploy script]]`

---

## Detailed Implementation

### 1. Intent Parser

```python
# kiwi_mcp/intent/parser.py

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Intent:
    """Parsed tool intent from agent output."""
    raw_text: str           # The full [TOOL: ...] match
    intent_text: str        # Just the description inside
    position: tuple[int, int]  # Start/end position in output
    context_before: str     # 500 chars before intent
    context_after: str      # 500 chars after intent


class IntentParser:
    """Parses tool intents from agent output."""
    
    # Match [TOOL: anything until closing bracket]
    # Non-greedy to handle multiple intents
    INTENT_PATTERN = re.compile(r'\[TOOL:\s*(.+?)\]', re.IGNORECASE | re.DOTALL)
    
    # Context window around intent
    CONTEXT_CHARS = 500
    
    def parse(self, agent_output: str) -> list[Intent]:
        """Extract all tool intents from agent output.
        
        Returns list of Intent objects in order of appearance.
        """
        intents = []
        
        for match in self.INTENT_PATTERN.finditer(agent_output):
            start, end = match.span()
            
            intent = Intent(
                raw_text=match.group(0),
                intent_text=match.group(1).strip(),
                position=(start, end),
                context_before=agent_output[max(0, start - self.CONTEXT_CHARS):start],
                context_after=agent_output[end:end + self.CONTEXT_CHARS]
            )
            intents.append(intent)
        
        return intents
    
    def has_intent(self, agent_output: str) -> bool:
        """Quick check if output contains any intents."""
        return bool(self.INTENT_PATTERN.search(agent_output))
    
    def replace_intent(self, agent_output: str, intent: Intent, replacement: str) -> str:
        """Replace an intent with resolved result."""
        return (
            agent_output[:intent.position[0]] +
            replacement +
            agent_output[intent.position[1]:]
        )
```

### 2. Schema Discovery via RAG

```python
# kiwi_mcp/intent/discovery.py

from ..storage.vector import VectorStore, SearchResult


class SchemaDiscovery:
    """Discovers relevant tool schemas for intent resolution."""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
    
    async def find_schemas(
        self,
        intent: Intent,
        limit: int = 10,
        include_types: list[str] = ["directive", "script", "mcp_tool"]
    ) -> list[ToolSchema]:
        """Find tool schemas relevant to the intent.
        
        Uses RAG (Phase 5) to semantically search for matching tools.
        """
        # Combine intent with context for better matching
        search_query = f"{intent.intent_text}\n\nContext: {intent.context_before[-200:]}"
        
        # Search vector store
        results = await self.vector_store.search(
            query=search_query,
            limit=limit * 2,  # Fetch more, filter down
            item_type=None  # Search all types initially
        )
        
        # Convert to ToolSchema objects
        schemas = []
        for result in results:
            if result.item_type in include_types:
                schema = self._result_to_schema(result)
                schemas.append(schema)
        
        # Rank by relevance and return top K
        return self._rank_schemas(schemas, intent)[:limit]
    
    def _result_to_schema(self, result: SearchResult) -> ToolSchema:
        """Convert search result to tool schema."""
        return ToolSchema(
            tool_id=result.item_id,
            tool_type=result.item_type,
            description=result.metadata.get("description", ""),
            parameters=result.metadata.get("parameters", []),
            examples=result.metadata.get("examples", []),
            score=result.score
        )
    
    def _rank_schemas(self, schemas: list[ToolSchema], intent: Intent) -> list[ToolSchema]:
        """Rank schemas by intent relevance."""
        # Already ranked by vector similarity, but can add boosting:
        # - Boost exact name matches
        # - Boost recently used tools
        # - Boost higher-rated tools
        for schema in schemas:
            if schema.tool_id.lower() in intent.intent_text.lower():
                schema.score += 0.1  # Name match boost
        
        return sorted(schemas, key=lambda s: s.score, reverse=True)
```

### 3. FunctionGemma Tool Resolver

```python
# kiwi_mcp/intent/resolver.py

from dataclasses import dataclass
from typing import Optional
import json


@dataclass
class ToolCall:
    """Resolved tool call from intent."""
    tool_type: str          # meta-tool: search | load | execute | help
    item_type: Optional[str]  # directive | script | knowledge | mcp
    action: Optional[str]    # run | create | update | delete | publish
    item_id: Optional[str]
    parameters: dict
    confidence: float       # 0.0 to 1.0


class ToolResolver:
    """Resolves natural language intents to structured tool calls.
    
    Uses a specialized small LLM (FunctionGemma) optimized for
    structured output generation.
    """
    
    def __init__(
        self,
        model_name: str = "google/gemma-2-2b-it",
        vector_store: Optional[VectorStore] = None
    ):
        self.model_name = model_name
        self.discovery = SchemaDiscovery(vector_store) if vector_store else None
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            # Lazy load model
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype="auto",
                device_map="auto"
            )
        return self._model
    
    async def resolve(
        self,
        intent: Intent,
        context: list[dict],  # Conversation history
        prefetched_schemas: Optional[list[ToolSchema]] = None
    ) -> ToolCall:
        """Resolve intent to tool call.
        
        Args:
            intent: Parsed intent from agent output
            context: Recent conversation messages
            prefetched_schemas: Schemas from MCP 2.5 pre-fetching (optional)
        
        Returns:
            ToolCall with structured parameters
        """
        # Get relevant schemas (use prefetched if available)
        if prefetched_schemas:
            schemas = prefetched_schemas
        elif self.discovery:
            schemas = await self.discovery.find_schemas(intent)
        else:
            schemas = []
        
        # Build resolver prompt
        prompt = self._build_prompt(intent, context, schemas)
        
        # Generate tool call
        response = await self._generate(prompt)
        
        # Parse and validate
        tool_call = self._parse_response(response)
        
        return tool_call
    
    def _build_prompt(
        self,
        intent: Intent,
        context: list[dict],
        schemas: list[ToolSchema]
    ) -> str:
        """Build prompt for FunctionGemma."""
        
        # Format context
        context_str = "\n".join([
            f"{msg['role']}: {msg['content'][:200]}"
            for msg in context[-5:]  # Last 5 messages
        ])
        
        # Format schemas
        schema_str = "\n\n".join([
            f"Tool: {s.tool_id}\nType: {s.tool_type}\nDescription: {s.description}\n"
            f"Parameters: {json.dumps(s.parameters)}"
            for s in schemas[:5]  # Top 5 schemas
        ])
        
        return f"""You are a function call generator. Your job is to convert natural language tool intents into precise, structured tool calls.

## Available Tools

{schema_str}

## Kiwi MCP Meta-Tools

All tools are accessed via these 4 meta-tools:
1. search(item_type, query, source) - Find items
2. load(item_type, item_id, source) - Get item details
3. execute(item_type, action, item_id, parameters) - Run actions
4. help(topic) - Get guidance

## Conversation Context

{context_str}

## Intent to Resolve

{intent.intent_text}

## Task

Output ONLY a valid tool call in this XML format:

<tool_call>
  <meta_tool>execute</meta_tool>
  <item_type>script</item_type>
  <action>run</action>
  <item_id>google_maps_scraper</item_id>
  <parameters>{{"query": "tech companies", "limit": 50}}</parameters>
  <confidence>0.95</confidence>
</tool_call>

If you cannot resolve the intent, output:
<tool_call>
  <error>Unable to resolve: reason</error>
  <confidence>0.0</confidence>
</tool_call>

Now generate the tool call:"""
    
    async def _generate(self, prompt: str) -> str:
        """Generate response from FunctionGemma."""
        import asyncio
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def _sync_generate():
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,  # Low temperature for deterministic output
                do_sample=False
            )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        response = await loop.run_in_executor(None, _sync_generate)
        
        # Extract just the generated part (after prompt)
        return response[len(prompt):].strip()
    
    def _parse_response(self, response: str) -> ToolCall:
        """Parse FunctionGemma response into ToolCall."""
        import xml.etree.ElementTree as ET
        
        try:
            # Find XML in response
            xml_match = re.search(r'<tool_call>.*?</tool_call>', response, re.DOTALL)
            if not xml_match:
                raise ValueError("No tool_call XML found in response")
            
            root = ET.fromstring(xml_match.group(0))
            
            # Check for error
            error = root.find('error')
            if error is not None:
                return ToolCall(
                    tool_type="error",
                    item_type=None,
                    action=None,
                    item_id=None,
                    parameters={"error": error.text},
                    confidence=0.0
                )
            
            # Parse successful resolution
            meta_tool = root.findtext('meta_tool', 'execute')
            
            return ToolCall(
                tool_type=meta_tool,
                item_type=root.findtext('item_type'),
                action=root.findtext('action'),
                item_id=root.findtext('item_id'),
                parameters=json.loads(root.findtext('parameters', '{}')),
                confidence=float(root.findtext('confidence', '0.5'))
            )
            
        except Exception as e:
            logging.error(f"Failed to parse tool call: {e}\nResponse: {response}")
            return ToolCall(
                tool_type="error",
                item_type=None,
                action=None,
                item_id=None,
                parameters={"error": f"Parse error: {str(e)}"},
                confidence=0.0
            )
```

### 4. Updated Agent Prompt

Add to AGENTS.md:

```markdown
## Tool Calling (MCP 2.0)

You have access to Kiwi MCP with 4 meta-tools. Rather than remembering exact syntax,
express your tool needs naturally using intent brackets:

```
[TOOL: description of what you need]
```

### Examples

**Searching:**
- `[TOOL: search for directives about email campaigns]`
- `[TOOL: find scripts that scrape Google Maps]`
- `[TOOL: look up knowledge about rate limiting]`

**Executing:**
- `[TOOL: run the google_maps_scraper with query='tech companies']`
- `[TOOL: execute deploy_staging for production environment]`
- `[TOOL: create a new directive for user onboarding]`

**Loading:**
- `[TOOL: load the bootstrap directive to see its steps]`
- `[TOOL: get the code for lead_enricher script]`

The system will resolve your intent to the correct tool call. You don't need
to worry about exact parameter names or syntax—just describe what you need.

### Direct Calls (Fallback)

You can still use direct tool calls if you know the exact syntax:

```xml
<tool_call name="mcp__kiwi_mcp__execute">
  <item_type>script</item_type>
  <action>run</action>
  <item_id>my_script</item_id>
</tool_call>
```
```

---

## Part 3: MCP 2.5 - Predictive Pre-Fetching

### The Insight

While the front-end agent is generating its response (which takes 1-5 seconds), we can:
1. **Predict** what tool intents it might express
2. **Pre-fetch** search results for those predictions
3. **Shortcut** resolution when predictions match

This reduces the intent→execution latency by eliminating the search step for 60%+ of tool calls.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MCP 2.5 Architecture                            │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Front-End Agent (Generating...)                   │  │
│  │  "To handle the campaign, I need to first..."                 │  │
│  │                                                                │  │
│  │           ▼ (streaming tokens)                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │ Token Buffer: "To handle the campaign, I need to fir"  │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                  │                                   │
│                    (parallel snapshot every 100 tokens)              │
│                                  │                                   │
│          ┌───────────────────────┴───────────────────────┐          │
│          │                                               │          │
│          ▼                                               ▼          │
│  ┌───────────────────────┐                 ┌────────────────────┐   │
│  │    Intent Predictor   │                 │  Agent Completes   │   │
│  │  (BERT/small LLM)     │                 │                    │   │
│  │                       │                 │  "[TOOL: search    │   │
│  │  Predictions:         │                 │   for email        │   │
│  │  1. search scripts    │                 │   scripts]"        │   │
│  │     email (0.85)      │                 │                    │   │
│  │  2. load directive    │                 │                    │   │
│  │     campaign (0.6)    │                 │                    │   │
│  └───────────┬───────────┘                 └──────────┬─────────┘   │
│              │                                        │             │
│              ▼                                        │             │
│  ┌───────────────────────┐                            │             │
│  │   Pre-Fetch Cache     │                            │             │
│  │                       │                            │             │
│  │   Runs search for     │◄───────────────────────────┘             │
│  │   predicted intents   │        (actual intent arrives)           │
│  │                       │                                          │
│  │   Cache:              │                                          │
│  │   - "search email" →  │                                          │
│  │     [script1, ...]    │                                          │
│  └───────────┬───────────┘                                          │
│              │                                                       │
│              ▼                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Intent Resolution (MCP 2.0)                       │  │
│  │                                                                │  │
│  │  IF actual ≈ predicted (semantic similarity > 0.8):           │  │
│  │    → Use cached schemas → Skip search → Fast resolve           │  │
│  │  ELSE:                                                         │  │
│  │    → Normal resolution with fresh search                       │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Intent Predictor

```python
# kiwi_mcp/intent/predictor.py

from sentence_transformers import SentenceTransformer
import numpy as np
from dataclasses import dataclass


@dataclass
class Prediction:
    """Predicted tool intent."""
    intent_text: str
    confidence: float
    embedding: list[float]


class IntentPredictor:
    """Predicts likely tool intents from conversation context.
    
    Uses a fine-tuned embedding model trained on historical
    conversation → intent mappings from audit logs.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.intent_templates = self._load_intent_templates()
    
    def _load_intent_templates(self) -> list[dict]:
        """Load common intent patterns from training data.
        
        These are learned from audit logs: what intents typically
        follow what conversation patterns.
        """
        # Example templates - would be loaded from training
        return [
            {
                "triggers": ["campaign", "email", "outreach"],
                "likely_intents": [
                    "search for email campaign directives",
                    "search for email scripts",
                    "load email templates"
                ]
            },
            {
                "triggers": ["deploy", "staging", "production", "release"],
                "likely_intents": [
                    "run deploy_staging script",
                    "execute deployment directive",
                    "search for deployment scripts"
                ]
            },
            {
                "triggers": ["scrape", "leads", "companies", "maps"],
                "likely_intents": [
                    "run google_maps_scraper",
                    "search for scraping scripts",
                    "execute lead enrichment"
                ]
            },
            # ... many more learned from usage
        ]
    
    async def predict(
        self,
        partial_output: str,
        conversation: list[dict],
        top_k: int = 3
    ) -> list[Prediction]:
        """Predict likely tool intents from current context.
        
        Args:
            partial_output: Agent's response so far
            conversation: Recent conversation history
            top_k: Number of predictions to return
        
        Returns:
            List of Predictions sorted by confidence
        """
        # Combine context for prediction
        context = self._build_context(partial_output, conversation)
        
        # Embed context
        context_embedding = self.model.encode(context)
        
        # Find matching intent templates
        predictions = []
        
        for template in self.intent_templates:
            # Check if any trigger words match
            trigger_match = any(
                trigger in context.lower()
                for trigger in template["triggers"]
            )
            
            if trigger_match:
                for intent_text in template["likely_intents"]:
                    # Compute similarity
                    intent_embedding = self.model.encode(intent_text)
                    similarity = np.dot(context_embedding, intent_embedding) / (
                        np.linalg.norm(context_embedding) * np.linalg.norm(intent_embedding)
                    )
                    
                    predictions.append(Prediction(
                        intent_text=intent_text,
                        confidence=float(similarity),
                        embedding=intent_embedding.tolist()
                    ))
        
        # Sort by confidence and return top K
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions[:top_k]
    
    def _build_context(self, partial: str, conversation: list[dict]) -> str:
        """Build context string for prediction."""
        parts = []
        
        # Add recent conversation
        for msg in conversation[-3:]:
            parts.append(f"{msg['role']}: {msg['content'][:200]}")
        
        # Add current partial output
        parts.append(f"assistant (generating): {partial[-500:]}")
        
        return "\n".join(parts)
```

### Pre-Fetch Cache

```python
# kiwi_mcp/intent/prefetch.py

import asyncio
import time
from dataclasses import dataclass
from typing import Optional
import hashlib


@dataclass
class CacheEntry:
    """Cached pre-fetch result."""
    prediction: Prediction
    schemas: list[ToolSchema]
    fetched_at: float
    expires_at: float
    
    def is_valid(self) -> bool:
        return time.time() < self.expires_at


class PreFetchCache:
    """Cache for pre-fetched search results."""
    
    def __init__(
        self,
        ttl_seconds: float = 10.0,
        max_entries: int = 50
    ):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
    
    def _hash_intent(self, intent_text: str) -> str:
        """Hash intent for cache key."""
        return hashlib.md5(intent_text.lower().encode()).hexdigest()[:16]
    
    async def store(self, prediction: Prediction, schemas: list[ToolSchema]):
        """Store pre-fetched schemas for a prediction."""
        async with self._lock:
            # Evict old entries if needed
            if len(self.cache) >= self.max_entries:
                self._evict_oldest()
            
            key = self._hash_intent(prediction.intent_text)
            self.cache[key] = CacheEntry(
                prediction=prediction,
                schemas=schemas,
                fetched_at=time.time(),
                expires_at=time.time() + self.ttl
            )
    
    async def match(
        self,
        actual_intent: str,
        threshold: float = 0.8
    ) -> Optional[list[ToolSchema]]:
        """Find cached schemas matching actual intent.
        
        Uses semantic similarity to match even if wording differs.
        """
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        actual_embedding = model.encode(actual_intent)
        
        best_match = None
        best_score = threshold
        
        async with self._lock:
            for key, entry in list(self.cache.items()):
                if not entry.is_valid():
                    del self.cache[key]
                    continue
                
                # Compute similarity with cached prediction
                similarity = np.dot(actual_embedding, entry.prediction.embedding) / (
                    np.linalg.norm(actual_embedding) * np.linalg.norm(entry.prediction.embedding)
                )
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = entry.schemas
        
        return best_match
    
    def _evict_oldest(self):
        """Evict oldest cache entries."""
        if not self.cache:
            return
        
        # Sort by fetched_at and remove oldest 20%
        sorted_keys = sorted(
            self.cache.keys(),
            key=lambda k: self.cache[k].fetched_at
        )
        
        for key in sorted_keys[:len(sorted_keys) // 5]:
            del self.cache[key]


class PreFetchDispatcher:
    """Dispatches pre-fetch searches based on predictions."""
    
    def __init__(
        self,
        discovery: SchemaDiscovery,
        cache: PreFetchCache
    ):
        self.discovery = discovery
        self.cache = cache
        self._pending: dict[str, asyncio.Task] = {}
    
    async def dispatch(self, predictions: list[Prediction]):
        """Dispatch pre-fetch searches for predictions.
        
        Runs searches in parallel for top predictions.
        """
        tasks = []
        
        for pred in predictions:
            # Only dispatch if confidence is high enough
            if pred.confidence < 0.6:
                continue
            
            # Don't re-fetch if already cached or pending
            key = hashlib.md5(pred.intent_text.encode()).hexdigest()[:16]
            if key in self._pending:
                continue
            
            task = asyncio.create_task(self._fetch_and_cache(pred))
            self._pending[key] = task
            tasks.append(task)
        
        # Don't wait for completion - fire and forget
        # Results will be in cache when needed
    
    async def _fetch_and_cache(self, prediction: Prediction):
        """Fetch schemas and cache them."""
        key = hashlib.md5(prediction.intent_text.encode()).hexdigest()[:16]
        
        try:
            # Create a mock Intent for discovery
            mock_intent = Intent(
                raw_text=f"[TOOL: {prediction.intent_text}]",
                intent_text=prediction.intent_text,
                position=(0, 0),
                context_before="",
                context_after=""
            )
            
            schemas = await self.discovery.find_schemas(mock_intent)
            await self.cache.store(prediction, schemas)
            
        finally:
            if key in self._pending:
                del self._pending[key]
```

### MCP 2.5 Harness Integration

```python
# kiwi_mcp/intent/pipeline.py

import asyncio
from typing import AsyncIterator


class MCP25Harness:
    """Harness that combines MCP 2.0 intent resolution with 2.5 pre-fetching."""
    
    def __init__(
        self,
        parser: IntentParser,
        resolver: ToolResolver,
        predictor: IntentPredictor,
        cache: PreFetchCache,
        dispatcher: PreFetchDispatcher
    ):
        self.parser = parser
        self.resolver = resolver
        self.predictor = predictor
        self.cache = cache
        self.dispatcher = dispatcher
        
        # Track metrics
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def process_stream(
        self,
        token_stream: AsyncIterator[str],
        conversation: list[dict]
    ) -> AsyncIterator[str]:
        """Process agent output stream with prediction and pre-fetching.
        
        Yields tokens while running predictions in parallel.
        When intents are detected, resolves them (using cache if available).
        """
        buffer = ""
        token_count = 0
        prediction_task: Optional[asyncio.Task] = None
        
        async for token in token_stream:
            buffer += token
            token_count += 1
            
            # Snapshot for prediction every 100 tokens
            if token_count % 100 == 0 and prediction_task is None:
                prediction_task = asyncio.create_task(
                    self._predict_and_prefetch(buffer, conversation)
                )
            
            # Check for complete intent
            if self.parser.has_intent(buffer):
                intents = self.parser.parse(buffer)
                
                for intent in intents:
                    # Resolve intent
                    resolved = await self._resolve_with_cache(intent, conversation)
                    
                    # Replace intent in buffer with resolution marker
                    buffer = self.parser.replace_intent(
                        buffer,
                        intent,
                        f"<resolved>{resolved.tool_type}:{resolved.item_id}</resolved>"
                    )
                    
                    yield f"\n[Resolved: {resolved.tool_type} {resolved.item_id}]\n"
            
            yield token
        
        # Clean up
        if prediction_task and not prediction_task.done():
            prediction_task.cancel()
    
    async def _predict_and_prefetch(
        self,
        buffer: str,
        conversation: list[dict]
    ):
        """Predict intents and dispatch pre-fetches."""
        predictions = await self.predictor.predict(buffer, conversation)
        await self.dispatcher.dispatch(predictions)
    
    async def _resolve_with_cache(
        self,
        intent: Intent,
        conversation: list[dict]
    ) -> ToolCall:
        """Resolve intent, using cache if available."""
        # Try cache first
        cached_schemas = await self.cache.match(intent.intent_text)
        
        if cached_schemas:
            self.cache_hits += 1
            # Use cached schemas for faster resolution
            return await self.resolver.resolve(
                intent,
                conversation,
                prefetched_schemas=cached_schemas
            )
        else:
            self.cache_misses += 1
            # Normal resolution
            return await self.resolver.resolve(intent, conversation)
    
    def get_metrics(self) -> dict:
        """Get cache performance metrics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "latency_reduction_estimate": hit_rate * 0.4  # ~40% latency from search
        }
```

---

## Training the Predictor

### Data Source: Audit Logs

From Phase 3 (Kiwi Proxy), we have audit logs of all tool calls:

```json
{
  "timestamp": "2026-01-22T10:30:00Z",
  "session_id": "sess_abc123",
  "conversation_context": "To handle the email campaign, I need to first...",
  "intent_expressed": "[TOOL: search for email campaign directives]",
  "tool_called": "execute(directive, search, ...)",
  "result": "success"
}
```

### Training Pipeline

```python
# kiwi_mcp/training/predictor_training.py

def prepare_training_data(audit_logs: list[dict]) -> Dataset:
    """Convert audit logs to training data.
    
    Format: (context_before_intent, intent_text)
    """
    examples = []
    
    for log in audit_logs:
        if log["result"] == "success":
            examples.append({
                "context": log["conversation_context"],
                "intent": log["intent_expressed"],
                "tool": log["tool_called"]
            })
    
    return Dataset.from_list(examples)


def fine_tune_predictor(dataset: Dataset):
    """Fine-tune predictor model on intent patterns."""
    from sentence_transformers import SentenceTransformer, losses
    
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Create training pairs: (context, intent)
    train_examples = [
        InputExample(texts=[ex["context"], ex["intent"]])
        for ex in dataset
    ]
    
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
    train_loss = losses.MultipleNegativesRankingLoss(model)
    
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=3,
        warmup_steps=100
    )
    
    model.save("models/intent_predictor")
```

---

## Performance Analysis

### Latency Breakdown

**Without MCP 2.0/2.5:**
```
Agent generates response: 2000ms
Parse output, extract tool: 10ms
Execute tool call: 500ms
Return to agent: 10ms
Total: 2520ms
```

**With MCP 2.0 (no pre-fetch):**
```
Agent generates response: 2000ms
Parse intent: 5ms
RAG schema search: 200ms
FunctionGemma resolve: 150ms
Execute tool call: 500ms
Return to agent: 10ms
Total: 2865ms (+345ms overhead)
```

**With MCP 2.5 (cache hit):**
```
Agent generates response: 2000ms (prediction runs parallel)
Parse intent: 5ms
Cache lookup: 5ms (hit!)
FunctionGemma resolve: 150ms (with cached schemas)
Execute tool call: 500ms
Return to agent: 10ms
Total: 2670ms (+150ms overhead, 195ms saved)
```

**With 60% hit rate:**
```
Average overhead: 0.6 * 150ms + 0.4 * 345ms = 228ms
Net benefit over no abstraction: Scales to 1M+ tools
```

---

## Success Metrics

### Phase 12 (MCP 2.0)

- [ ] Intent syntax `[TOOL: ...]` parsed correctly (100% accuracy)
- [ ] FunctionGemma resolves intents to valid tool calls (95%+ accuracy)
- [ ] RAG integration provides relevant schemas (top-5 contains correct 90%+)
- [ ] Fallback to direct calls works seamlessly
- [ ] Resolution latency < 500ms (excluding model load)

### Phase 13 (MCP 2.5)

- [ ] Predictions generated during agent streaming (no blocking)
- [ ] Pre-fetch cache hit rate > 60%
- [ ] End-to-end latency reduced by 30%+ for cache hits
- [ ] Predictor improves from audit logs (monthly fine-tuning)
- [ ] Graceful fallback on cache miss (no user-visible errors)

---

## Open Questions & Recommendations

### 1. FunctionGemma hosting: Local or API?

**Recommendation: Local for privacy, API for scale.**

- **Development**: Local Gemma 2B, ~2GB VRAM
- **Production (small)**: Local Gemma 7B, ~14GB VRAM  
- **Production (large)**: API to Gemini/Claude for cost efficiency
- Make configurable via `KIWI_RESOLVER_MODEL` env var

### 2. What if intent is ambiguous?

**Recommendation: Confidence threshold with clarification.**

```python
if tool_call.confidence < 0.7:
    return AmbiguousIntent(
        tool_call=tool_call,
        alternatives=[alt1, alt2, alt3],
        message="Did you mean one of these?"
    )
```

### 3. How to handle multi-intent responses?

**Recommendation: Sequential resolution with dependency detection.**

```python
intents = parser.parse(output)  # May find multiple

# Check for dependencies
if "[TOOL: search..." in output and "[TOOL: run {result}" in output:
    # Second intent depends on first - resolve sequentially
    pass
else:
    # Independent - resolve in parallel
    await asyncio.gather(*[resolve(i) for i in intents])
```

### 4. Can agents learn to skip intents for common patterns?

**Recommendation: Yes, via directive caching.**

If an agent frequently resolves `[TOOL: search for X]` → `execute Y`, 
store this mapping in knowledge and suggest direct calls:

```
Hint: For email campaigns, you can directly use:
execute(item_type="directive", action="run", item_id="outbound_campaign")
```

---

## Related Documents

- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Phases 12-13
- [RAG_VECTOR_SEARCH_DESIGN.md](./RAG_VECTOR_SEARCH_DESIGN.md) - Phase 5 prerequisite
- [DIRECTIVE_RUNTIME_ARCHITECTURE.md](./DIRECTIVE_RUNTIME_ARCHITECTURE.md) - Executor spawning
- [AGENT_ARCHITECTURE_COMPARISON.md](./AGENT_ARCHITECTURE_COMPARISON.md) - Why this matters
