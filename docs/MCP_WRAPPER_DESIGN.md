# MCP Wrapper Design

**Date:** 2026-01-25  
**Status:** Draft  
**Author:** Kiwi Team  
**Phase:** Future (after core implementation)

---

## Executive Summary

This document defines how to build **wrappers around Kiwi MCP** that enable external applications (Discord bots, Slack apps, web APIs, CLI tools) to leverage the full Kiwi ecosystem.

**Core Principle:** Users don't know MCP params. Every request goes through an **intent directive** that spawns a thread to construct the correct MCP calls, giving users full natural-language access to the kernel.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WRAPPER PATTERN                                  │
│                                                                          │
│  WRONG (what we're NOT doing):                                           │
│  External Request → Wrapper → MCP (search/load/execute/help) → Response │
│  (User must know exact params - they won't!)                             │
│                                                                          │
│  CORRECT (what we ARE doing):                                            │
│  External Request → Wrapper → Intent Thread → MCP calls → Response      │
│                                                                          │
│  User: "deploy to staging"                                               │
│  Wrapper: spawns intent_handler thread with that message                 │
│  Thread: LLM figures out → execute(directive, run, deploy_staging, ...) │
│  Result: streamed or sync response back to user                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Problem

### Direct MCP Access is Too Low-Level

The 4 Kiwi meta-tools (search, load, execute, help) are powerful but raw. **Users will never know the exact params.** They'll say:

- "deploy to staging" (not `execute(directive, run, deploy_staging, ...)`)
- "what scripts do I have for scraping?" (not `search(tool, scraper, local)`)
- "help me set up email campaigns" (not `help(action=guidance, topic=email)`)

Exposing the 4 meta-tools directly forces the wrapper to do all the intent parsing - **which is exactly what an LLM is good at**.

### The Solution: Intent Threading

Every incoming request spawns a thread running an **intent handler directive**. The LLM inside that thread:

1. Understands the natural language request
2. Figures out which MCP calls to make (search, load, execute, help)
3. Executes them with correct params
4. Formats the response for the platform

The wrapper's job is simple: **spawn threads and relay responses**.

### What a Wrapper Provides

The wrapper sits between the external interface and the MCP, handling:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WRAPPER RESPONSIBILITIES                         │
│                                                                          │
│  1. Thread Spawning & Management                                         │
│     Spawn intent_handler thread for each request                         │
│     Continue existing threads for conversations                          │
│     Terminate/archive threads                                            │
│                                                                          │
│  2. Response Relay (Streaming & Sync)                                    │
│     Stream SSE tokens back to platform                                   │
│     Buffer for sync responses                                            │
│     Handle platform-specific formatting                                  │
│                                                                          │
│  3. Access Control                                                       │
│     Map users to Kiwi permissions                                        │
│     Inject user context into thread                                      │
│     Enforce rate limits                                                  │
│                                                                          │
│  4. Platform Adaptation                                                  │
│     Character limits (Discord 2000, Slack 40000)                         │
│     Attachments/embeds                                                   │
│     Typing indicators                                                    │
│                                                                          │
│  5. State Persistence                                                    │
│     Track active threads                                                 │
│     Handle reconnections                                                 │
│     Persist across restarts                                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INTENT-BASED WRAPPER ARCHITECTURE                         │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     External Interface (Discord, Slack, HTTP)          │ │
│  │                                                                          │ │
│  │  User: "@bot deploy to staging"                                         │ │
│  │         │                                                               │ │
│  │         ▼                                                               │ │
│  └───────────────────────────────────┬────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Wrapper (Thin Layer)                                │ │
│  │                                                                          │ │
│  │  1. Check: new thread or continue existing?                             │ │
│  │  2. Spawn/continue thread with intent_handler directive                 │ │
│  │  3. Relay response (streaming or sync)                                  │ │
│  │  4. Handle platform-specific formatting                                 │ │
│  │                                                                          │ │
│  │  The wrapper does NOT parse intent or call MCP directly.                │ │
│  │  That's the thread's job.                                               │ │
│  └───────────────────────────────────┬────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Intent Handler Thread (LLM)                         │ │
│  │                                                                          │ │
│  │  Directive: intent_handler (or platform-specific variant)               │ │
│  │                                                                          │ │
│  │  The LLM inside the thread:                                             │ │
│  │  • Understands natural language ("deploy to staging")                   │ │
│  │  • Constructs correct MCP calls (search, load, execute, help)           │ │
│  │  • Executes multi-step workflows                                        │ │
│  │  • Formats response appropriately                                       │ │
│  │                                                                          │ │
│  └───────────────────────────────────┬────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Kiwi MCP (Universal Kernel)                         │ │
│  │                                                                          │ │
│  │  search() │ load() │ execute() │ help()                                 │ │
│  │                                                                          │ │
│  │  The LLM in the thread calls these with correct params.                 │ │
│  │  Users never need to know the param structure.                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## The Intent Handler Directive

### Core Concept

The `intent_handler` directive is the **universal entry point** for all external requests. It's what turns natural language into MCP calls:

```xml
<directive name="intent_handler" version="1.0.0">
  <metadata>
    <description>Handle natural language requests via Kiwi MCP</description>
    <category>core</category>
    <author>kiwi</author>

    <permissions>
      <!-- Intent handler needs full access to figure out what to do -->
      <read resource="filesystem" path="**/*" />
      <execute resource="kiwi-mcp" action="*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="request" type="string" required="true">
      The natural language request from the user
    </input>
    <input name="user_context" type="object" required="false">
      Platform-specific user context (user_id, permissions, channel, etc.)
    </input>
    <input name="platform" type="string" default="generic">
      Target platform for response formatting (discord, slack, http, cli)
    </input>
    <input name="project_path" type="string" required="false">
      If scoped to a project, the path to use
    </input>
  </inputs>

  <process>
    <step name="get_system_context">
      <description>Query system information for context-aware responses</description>
      <action><![CDATA[
Query system information using the system item type:

# Get runtime info (platform, architecture)
mcp__kiwi_mcp__execute(
  item_type="system",
  action="run",
  item_id="runtime"
)
→ { platform: "linux", arch: "x86_64", ... }

# Get MCP capabilities
mcp__kiwi_mcp__execute(
  item_type="system",
  action="run",
  item_id="mcp"
)
→ { kiwi_version: "0.1.0", item_types: [...], ... }

Use this info to:
- Format paths correctly for the platform
- Understand available capabilities
- Adapt responses to the environment
      ]]></action>
    </step>

    <step name="understand_intent">
      <description>Parse the user's natural language request</description>
      <action><![CDATA[
Analyze the request to determine:
1. What does the user want to accomplish?
2. Is this a search, a command, a question, or a multi-step task?
3. What MCP calls will be needed?

Categories:
- SEARCH: "what tools do I have?", "find directives about..."
- EXECUTE: "deploy to staging", "run the scraper", "create a new..."
- HELP: "how do I...", "what's the best way to...", "explain..."
- SYSTEM: "what platform am I on?", "where is my userspace?"
- CONVERSATIONAL: "continue from where we left off", follow-up questions

Do NOT ask the user for clarification unless truly ambiguous.
Make reasonable assumptions based on context.
      ]]></action>
    </step>

    <step name="execute_mcp_calls">
      <description>Make the appropriate MCP calls</description>
      <action><![CDATA[
Based on intent, call the appropriate Kiwi tools:

For SEARCH:
  mcp__kiwi_mcp__search(
    item_type="...",  # directive, tool, knowledge, system
    query="...",
    source="all",
    project_path="{project_path}"
  )

For EXECUTE:
  # First, find the right directive/tool
  mcp__kiwi_mcp__search(item_type="directive", query="...")

  # Then execute it
  mcp__kiwi_mcp__execute(
    item_type="directive",
    action="run",
    item_id="...",
    parameters={...},
    project_path="{project_path}"
  )

For SYSTEM:
  mcp__kiwi_mcp__execute(
    item_type="system",
    action="run",
    item_id="paths"  # or "runtime", "shell", "mcp"
  )

For HELP:
  mcp__kiwi_mcp__help(
    topic="...",  # overview, search, load, execute, system
  )

For multi-step tasks, chain these calls appropriately.
      ]]></action>
    </step>

    <step name="format_response">
      <description>Format response for the target platform</description>
      <action><![CDATA[
Format the response based on {platform}:

DISCORD:
- Max 2000 chars per message
- Use code blocks for code/logs
- Use embeds for structured data
- Split long responses into multiple messages

SLACK:
- Max 40000 chars
- Use mrkdwn formatting
- Use blocks for structured data

HTTP:
- Return JSON with { success, data, error }
- Include metadata (tokens_used, duration_ms)

CLI:
- Plain text with ANSI colors
- Structured output if --json flag
      ]]></action>
    </step>
  </process>

  <outputs>
    <success>
      Response formatted for {platform}, ready to relay to user
    </success>
  </outputs>
</directive>
```

### Platform-Specific Variants

For complex platforms, create specialized variants:

```
intent_handler          # Generic (default)
intent_handler_discord  # Discord-specific behaviors
intent_handler_slack    # Slack-specific behaviors
intent_handler_api      # HTTP API with JSON responses
```

---

## Response Mechanisms: Streaming vs Synchronous

### The Two Modes

The wrapper must handle **two distinct response patterns**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESPONSE MODES                                       │
│                                                                              │
│  STREAMING (Real-time)                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  User sends message                                                     │ │
│  │       ▼                                                                 │ │
│  │  Wrapper spawns thread (stream=true)                                    │ │
│  │       ▼                                                                 │ │
│  │  Thread returns SSE stream                                              │ │
│  │       ▼                                                                 │ │
│  │  Wrapper relays tokens as they arrive                                   │ │
│  │       ▼                                                                 │ │
│  │  Platform shows typing/updates in real-time                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Use for: Long responses, multi-step tasks, interactive conversations       │
│                                                                              │
│  SYNCHRONOUS (Buffered)                                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  User sends message                                                     │ │
│  │       ▼                                                                 │ │
│  │  Wrapper spawns thread (stream=false)                                   │ │
│  │       ▼                                                                 │ │
│  │  Thread completes, returns full response                                │ │
│  │       ▼                                                                 │ │
│  │  Wrapper sends complete message                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Use for: Quick commands, API responses, webhooks                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Streaming Implementation

```python
# kiwi_wrapper/streaming.py

from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional
import httpx

@dataclass
class StreamToken:
    """A single token from the stream."""
    type: str  # "text", "tool_start", "tool_result", "done", "error"
    content: str
    metadata: Optional[dict] = None

class StreamingResponseHandler:
    """
    Handles streaming responses from MCP thread execution.

    Connects to the thread's SSE stream and relays tokens to the platform.
    """

    def __init__(
        self,
        mcp_url: str,
        on_token: Callable[[StreamToken], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
    ):
        self.mcp_url = mcp_url
        self.on_token = on_token
        self.on_complete = on_complete
        self.on_error = on_error
        self.buffer = ""

    async def stream_thread(
        self,
        thread_id: str,
        message: str,
    ) -> None:
        """Stream response from a thread."""

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.mcp_url}/threads/{thread_id}/message",
                json={"message": message, "stream": True},
                timeout=None,  # Streaming has no timeout
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        event_data = json.loads(line[6:])
                        token = self._parse_event(event_data)

                        if token.type == "text":
                            self.buffer += token.content
                            await self.on_token(token)

                        elif token.type == "done":
                            await self.on_complete(self.buffer)
                            break

                        elif token.type == "error":
                            await self.on_error(token.content)
                            break

    def _parse_event(self, event: dict) -> StreamToken:
        """Parse SSE event into StreamToken."""
        event_type = event.get("type")

        if event_type == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                return StreamToken(
                    type="text",
                    content=delta.get("text", "")
                )

        elif event_type == "message_stop":
            return StreamToken(type="done", content="")

        elif event_type == "error":
            return StreamToken(
                type="error",
                content=event.get("error", "Unknown error")
            )

        return StreamToken(type="unknown", content="")


class SyncResponseHandler:
    """
    Handles synchronous (buffered) responses from MCP thread execution.

    Waits for full response before returning.
    """

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    async def send_and_wait(
        self,
        thread_id: str,
        message: str,
        timeout: float = 60.0,
    ) -> dict:
        """Send message and wait for complete response."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_url}/threads/{thread_id}/message",
                json={"message": message, "stream": False},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
```

### Platform-Specific Streaming

Different platforms handle streaming differently:

```python
# kiwi_wrapper/platforms/discord.py

class DiscordStreamHandler:
    """Handle streaming for Discord."""

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.current_message: Optional[discord.Message] = None
        self.buffer = ""
        self.last_update = 0
        self.update_interval = 0.5  # Update every 500ms

    async def on_token(self, token: StreamToken) -> None:
        """Handle incoming token."""
        self.buffer += token.content

        # Throttle updates to avoid rate limits
        now = time.time()
        if now - self.last_update > self.update_interval:
            await self._update_message()
            self.last_update = now

    async def on_complete(self, full_response: str) -> None:
        """Handle stream completion."""
        # Final update with complete response
        await self._update_message(final=True)

    async def _update_message(self, final: bool = False) -> None:
        """Update or create the Discord message."""
        content = self.buffer[:2000]  # Discord limit

        if len(self.buffer) > 2000 and final:
            # Split into multiple messages
            await self._send_chunked(self.buffer)
        elif self.current_message:
            await self.current_message.edit(content=content)
        else:
            self.current_message = await self.channel.send(content)

    async def _send_chunked(self, content: str) -> None:
        """Send long content as multiple messages."""
        chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
        for i, chunk in enumerate(chunks):
            if i == 0 and self.current_message:
                await self.current_message.edit(content=chunk)
            else:
                await self.channel.send(chunk)


# kiwi_wrapper/platforms/http.py

class HTTPStreamHandler:
    """Handle streaming for HTTP API (SSE passthrough)."""

    async def stream_response(
        self,
        thread_id: str,
        message: str,
    ) -> AsyncIterator[str]:
        """Yield SSE events to client."""

        async with StreamingResponseHandler(
            mcp_url=self.mcp_url,
            on_token=lambda t: None,  # We yield directly
            on_complete=lambda r: None,
            on_error=lambda e: None,
        ) as handler:
            async for event in handler.raw_events(thread_id, message):
                yield f"data: {json.dumps(event)}\n\n"
```

---

## Conversation Modes

### The Core Question

When a user sends a message, should it:

1. **Single-shot** - New thread per request, forget context after
2. **Persistent thread** - Continue an ongoing conversation
3. **Scoped thread** - Conversation within a specific context (project, channel)

**Key insight:** Even single-shot mode spawns a thread (running `intent_handler`). The difference is whether that thread persists for follow-up messages.

### Mode 1: Single-Shot (New Thread Each Time)

Best for: Quick commands, webhooks, stateless API calls

```
User: "@bot what directives do I have?"
Bot:  [spawns new intent_handler thread]
      [LLM in thread calls: mcp.search(directive, ...)]
      [thread terminates after response]
      "You have 12 directives: deploy_staging, create_api, ..."
```

Implementation:

```python
async def handle_single_shot(
    message: str,
    user_id: str,
    platform: str,
    stream: bool = True,
) -> AsyncIterator[str] | str:
    """Spawn new thread for each request."""

    # Generate unique thread ID (will be discarded after)
    thread_id = f"oneshot_{user_id}_{int(time.time())}"

    # Spawn thread running intent_handler
    if stream:
        async for chunk in spawn_intent_thread_streaming(
            thread_id=thread_id,
            message=message,
            user_context={"user_id": user_id},
            platform=platform,
        ):
            yield chunk
    else:
        result = await spawn_intent_thread_sync(
            thread_id=thread_id,
            message=message,
            user_context={"user_id": user_id},
            platform=platform,
        )
        return result

    # Thread is not stored - dies after response


async def spawn_intent_thread_streaming(
    thread_id: str,
    message: str,
    user_context: dict,
    platform: str,
    project_path: str = None,
) -> AsyncIterator[str]:
    """Spawn thread and stream response."""

    # Execute intent_handler directive in a new thread
    result = await mcp.execute(
        item_type="directive",
        action="run",
        item_id="intent_handler",
        parameters={
            "location": "thread",
            "thread_id": thread_id,
            "inputs": {
                "request": message,
                "user_context": user_context,
                "platform": platform,
                "project_path": project_path,
            },
            "stream": True,  # Request streaming response
        }
    )

    # Relay SSE stream
    async for event in result.stream:
        yield event
```

### Mode 2: Persistent Thread (Stateful Conversation)

Best for: Complex tasks, multi-turn assistance, ongoing projects

```
User: "@bot help me deploy to staging"
Bot:  [spawns thread: conv_user123_1706198400]
      "I'll help you deploy. First, which service?"

User: "the auth service"
Bot:  [continues SAME thread]
      "Got it. Checking staging environment..."

User: "wait, what's the current status first?"
Bot:  [thread has full context, pivots naturally]
      "Let me check... Auth service is at v2.3.1 on staging."
```

Implementation:

```python
async def handle_persistent_thread(
    message: str,
    user_id: str,
    channel_id: str,
    stream: bool = True,
) -> AsyncIterator[str] | str:
    """Continue or create a persistent thread."""

    # Thread key: user + channel
    thread_key = f"persistent:{user_id}:{channel_id}"
    existing = await thread_store.get(thread_key)

    if existing and not is_expired(existing):
        # Continue existing thread - send message to running thread
        thread_id = existing.thread_id

        if stream:
            async for chunk in continue_thread_streaming(thread_id, message):
                yield chunk
        else:
            return await continue_thread_sync(thread_id, message)
    else:
        # Spawn new persistent thread
        thread_id = f"conv_{user_id}_{int(time.time())}"

        # Store reference before spawning
        await thread_store.set(thread_key, ThreadRef(
            thread_id=thread_id,
            created_at=time.time(),
            expires_at=time.time() + 3600,  # 1 hour timeout
        ))

        if stream:
            async for chunk in spawn_intent_thread_streaming(
                thread_id=thread_id,
                message=message,
                user_context={"user_id": user_id},
                platform="discord",
            ):
                yield chunk
        else:
            return await spawn_intent_thread_sync(
                thread_id=thread_id,
                message=message,
                user_context={"user_id": user_id},
                platform="discord",
            )


async def continue_thread_streaming(
    thread_id: str,
    message: str,
) -> AsyncIterator[str]:
    """Send message to existing thread and stream response."""

    # The thread is already running - just send a message
    result = await mcp.execute(
        item_type="thread",
        action="message",
        item_id=thread_id,
        parameters={
            "message": message,
            "stream": True,
        }
    )

    async for event in result.stream:
        yield event
```

### Mode 3: Scoped Thread (Project-Aware)

Best for: Project-specific work, channel-to-codebase linking

```
Channel: #project-alpha

User: "@bot create a new API endpoint for user profiles"
Bot:  [spawns thread with project_path=/code/project-alpha]
      [LLM loads project .ai/, understands FastAPI context]
      "I see project-alpha uses FastAPI. Creating endpoint..."

---

Channel: #project-beta

User: "@bot create a new API endpoint for user profiles"
Bot:  [spawns thread with project_path=/code/project-beta]
      [LLM loads different .ai/, understands Express context]
      "Project-beta uses Express. Creating endpoint..."
```

Implementation:

```python
async def handle_scoped_thread(
    message: str,
    user_id: str,
    channel_id: str,
    channel_projects: ChannelProjectMap,
    stream: bool = True,
) -> AsyncIterator[str] | str:
    """Handle thread scoped to a project."""

    # Get project for this channel
    project_path = channel_projects.get(channel_id)
    if not project_path:
        yield "⚠️ Channel not linked to a project. Use `/link <path>`"
        return

    # Thread key: channel (not user - shared project context)
    thread_key = f"scoped:{channel_id}"
    existing = await thread_store.get(thread_key)

    if existing and not is_expired(existing):
        thread_id = existing.thread_id

        if stream:
            async for chunk in continue_thread_streaming(thread_id, message):
                yield chunk
        else:
            return await continue_thread_sync(thread_id, message)
    else:
        # Spawn new scoped thread with project context
        thread_id = f"scoped_{channel_id}_{int(time.time())}"

        await thread_store.set(thread_key, ThreadRef(
            thread_id=thread_id,
            created_at=time.time(),
            expires_at=time.time() + 3600,
            project_path=project_path,
        ))

        if stream:
            async for chunk in spawn_intent_thread_streaming(
                thread_id=thread_id,
                message=message,
                user_context={"user_id": user_id},
                platform="discord",
                project_path=project_path,  # Injected into intent_handler
            ):
                yield chunk
```

---

## Content Control

### The Compaction Problem

LLM conversations accumulate context. A long Discord conversation might:

1. **Exceed token limits** - Thread dies from context overflow
2. **Drift off-topic** - Original intent lost in noise
3. **Slow down** - Larger context = slower responses
4. **Cost more** - More tokens = higher costs

### Compaction Strategies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COMPACTION STRATEGIES                           │
│                                                                         │
│  1. Sliding Window                                                      │
│     Keep last N messages, drop older ones                               │
│     Simple but loses important early context                            │
│                                                                         │
│  2. Summarization                                                       │
│     Periodically summarize older messages into a condensed block        │
│     Preserves key information, reduces token count                      │
│                                                                         │
│  3. Key Facts Extraction                                                │
│     Extract and maintain a "facts" section                              │
│     "User wants to deploy auth service to staging"                      │
│     "Current version: v2.3.1"                                           │
│                                                                         │
│  4. Hierarchical Memory                                                 │
│     Short-term: Last 5 messages (full)                                  │
│     Medium-term: Summarized older messages                              │
│     Long-term: Key facts and decisions                                  │
│                                                                         │
│  5. Topic-Based Pruning                                                 │
│     Keep messages relevant to current topic                             │
│     Archive off-topic tangents                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Implementation: Hierarchical Memory

```python
@dataclass
class ThreadMemory:
    """Hierarchical memory for long conversations."""

    # Short-term: Recent full messages
    recent_messages: List[dict]  # Last 5 messages

    # Medium-term: Summarized history
    history_summary: str  # Summary of older conversation

    # Long-term: Extracted facts
    key_facts: List[str]  # "User is deploying auth service"
    decisions_made: List[str]  # "Decided to use blue-green deployment"

    # Metadata
    total_messages: int
    last_compacted_at: float

    def to_context(self) -> str:
        """Build context string for LLM."""
        return f"""## Conversation Context

### Key Facts
{self._format_facts()}

### History Summary
{self.history_summary}

### Recent Messages
{self._format_recent()}
"""

    async def compact(self, summarizer: Callable) -> None:
        """Compact memory when it gets too large."""
        if len(self.recent_messages) > 10:
            # Summarize older messages
            to_summarize = self.recent_messages[:-5]
            summary = await summarizer(to_summarize)

            # Update medium-term memory
            if self.history_summary:
                self.history_summary = await summarizer([
                    {"role": "system", "content": self.history_summary},
                    {"role": "system", "content": summary}
                ])
            else:
                self.history_summary = summary

            # Keep only recent
            self.recent_messages = self.recent_messages[-5:]
            self.last_compacted_at = time.time()
```

### Compaction via Directive

The wrapper can use a Kiwi directive to handle compaction:

```xml
<directive name="compact_thread" version="1.0.0">
  <metadata>
    <description>Compact a thread's memory to reduce context size</description>
    <category>core</category>
  </metadata>

  <process>
    <step name="extract_facts">
      <description>Extract key facts from conversation</description>
      <action><![CDATA[
Analyze the conversation and extract:
1. User's primary goal
2. Decisions made
3. Key information gathered
4. Current status/next steps

Format as bullet points.
      ]]></action>
    </step>

    <step name="summarize_history">
      <description>Summarize older messages</description>
      <action><![CDATA[
Create a 2-3 sentence summary of the conversation so far.
Focus on: what was discussed, what was accomplished.
      ]]></action>
    </step>

    <step name="rebuild_context">
      <description>Rebuild compact context</description>
      <action><![CDATA[
Combine:
1. Key facts (bullets)
2. History summary (paragraph)
3. Last 5 messages (full)

This becomes the new thread context.
      ]]></action>
    </step>
  </process>
</directive>
```

---

## Remote Codebase Access

### The Scenario

A Discord bot might manage a codebase hosted somewhere else:

- Bot runs on Server A
- Codebase is on Server B
- User interacts via Discord

### Architecture Options

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REMOTE CODEBASE OPTIONS                          │
│                                                                          │
│  Option 1: Codebase-Local MCP                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Server B (Codebase)                                                 │ │
│  │  ├── Kiwi MCP (running)                                              │ │
│  │  ├── .ai/ (project)                                                  │ │
│  │  └── code/                                                           │ │
│  │                                                                       │ │
│  │  Server A (Bot)                                                       │ │
│  │  └── Wrapper → HTTP → MCP on Server B                                │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Option 2: Bot-Local MCP with Remote Mounting                            │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Server A (Bot + MCP)                                                │ │
│  │  ├── Kiwi MCP (running)                                              │ │
│  │  ├── ~/.ai/ (user)                                                   │ │
│  │  └── Remote mount → Server B:/code/                                  │ │
│  │                                                                       │ │
│  │  Server B (Codebase)                                                  │ │
│  │  └── code/ (mounted via NFS/SSHFS/etc)                               │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Option 3: Git-Based Sync                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Server A (Bot + MCP)                                                │ │
│  │  ├── Kiwi MCP                                                        │ │
│  │  └── Local clone of repo                                             │ │
│  │                                                                       │ │
│  │  Changes: Commit/push to git → Webhook → Pull on Server B            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

`Ah this is where tool intent comes into play`

---

### Recommended: Option 1 (Codebase-Local MCP)

The cleanest architecture is running the MCP where the code is:

```python
# wrapper/remote_mcp.py

class RemoteMCPClient:
    """Client for remote Kiwi MCP over HTTP."""

    def __init__(self, mcp_url: str, api_key: str):
        self.mcp_url = mcp_url
        self.api_key = api_key
        self.http = httpx.AsyncClient()

    async def search(self, item_type: str, query: str, **kwargs) -> dict:
        """Search remote MCP."""
        return await self._call("search", {
            "item_type": item_type,
            "query": query,
            **kwargs
        })

    async def load(self, item_type: str, item_id: str, **kwargs) -> dict:
        """Load from remote MCP."""
        return await self._call("load", {
            "item_type": item_type,
            "item_id": item_id,
            **kwargs
        })

    async def execute(self, item_type: str, action: str, item_id: str, **kwargs) -> dict:
        """Execute on remote MCP."""
        return await self._call("execute", {
            "item_type": item_type,
            "action": action,
            "item_id": item_id,
            **kwargs
        })

    async def help(self, action: str, **kwargs) -> dict:
        """Get help from remote MCP."""
        return await self._call("help", {
            "action": action,
            **kwargs
        })

    async def _call(self, tool: str, params: dict) -> dict:
        """Make HTTP call to remote MCP."""
        response = await self.http.post(
            f"{self.mcp_url}/tools/{tool}",
            json=params,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        response.raise_for_status()
        return response.json()
```

---

## Discord Bot Example

### Complete Discord Wrapper

```python
# discord_wrapper/bot.py

import discord
from discord import app_commands
from kiwi_wrapper import KiwiWrapper, ConversationMode

class KiwiBot(discord.Client):
    """Discord bot wrapping Kiwi MCP."""

    def __init__(self, mcp_url: str, mcp_key: str):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        # Initialize wrapper
        self.kiwi = KiwiWrapper(
            mcp_url=mcp_url,
            mcp_key=mcp_key,
            default_mode=ConversationMode.SCOPED,
        )

        # Thread store (Redis or similar)
        self.thread_store = ThreadStore()

        # Channel-to-project mapping
        self.channel_projects = ChannelProjectMap()

    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        if message.author.bot:
            return

        # Check if mentioned or in DM
        if not self._should_respond(message):
            return

        # Extract clean message
        content = self._clean_message(message.content)

        # Determine conversation mode
        mode = self._get_mode(message)

        # Process through wrapper
        try:
            async with message.channel.typing():
                response = await self._process_message(
                    content=content,
                    user_id=str(message.author.id),
                    channel_id=str(message.channel.id),
                    mode=mode,
                )

            # Send response (handle Discord limits)
            await self._send_response(message.channel, response)

        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

    async def _process_message(
        self,
        content: str,
        user_id: str,
        channel_id: str,
        mode: ConversationMode,
    ) -> str:
        """Process message through Kiwi wrapper."""

        if mode == ConversationMode.SINGLE_SHOT:
            return await self.kiwi.single_shot(content, user_id)

        elif mode == ConversationMode.PERSISTENT:
            thread_key = f"persistent:{user_id}:{channel_id}"
            return await self.kiwi.persistent_thread(
                content, user_id, thread_key, self.thread_store
            )

        elif mode == ConversationMode.SCOPED:
            project_path = self.channel_projects.get(channel_id)
            if not project_path:
                return "⚠️ Channel not linked to a project. Use `/link <path>`"

            thread_key = f"scoped:{channel_id}"
            return await self.kiwi.scoped_thread(
                content, user_id, thread_key, project_path, self.thread_store
            )

    async def _send_response(self, channel, response: str):
        """Send response, handling Discord's 2000 char limit."""
        if len(response) <= 2000:
            await channel.send(response)
        else:
            # Split into chunks
            chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
            for chunk in chunks:
                await channel.send(chunk)

    def _should_respond(self, message: discord.Message) -> bool:
        """Check if bot should respond to this message."""
        # DMs always respond
        if isinstance(message.channel, discord.DMChannel):
            return True

        # Check if mentioned
        if self.user in message.mentions:
            return True

        # Check for command prefix
        if message.content.startswith("!kiwi"):
            return True

        return False

    def _clean_message(self, content: str) -> str:
        """Remove bot mention and prefix from message."""
        # Remove mention
        content = content.replace(f"<@{self.user.id}>", "").strip()
        # Remove prefix
        if content.startswith("!kiwi"):
            content = content[5:].strip()
        return content

    def _get_mode(self, message: discord.Message) -> ConversationMode:
        """Determine conversation mode based on context."""
        # DMs are persistent
        if isinstance(message.channel, discord.DMChannel):
            return ConversationMode.PERSISTENT

        # Linked channels are scoped
        if self.channel_projects.get(str(message.channel.id)):
            return ConversationMode.SCOPED

        # Default to single-shot
        return ConversationMode.SINGLE_SHOT


# Slash commands
class KiwiCommands(app_commands.Group):
    """Slash commands for Kiwi bot."""

    @app_commands.command(name="link")
    async def link_channel(self, interaction: discord.Interaction, project_path: str):
        """Link this channel to a project."""
        # Validate project path exists on MCP
        result = await interaction.client.kiwi.mcp.execute(
            item_type="tool",
            action="run",
            item_id="validate_project",
            parameters={"path": project_path}
        )

        if not result.get("valid"):
            await interaction.response.send_message(
                f"❌ Invalid project path: {project_path}",
                ephemeral=True
            )
            return

        # Store mapping
        interaction.client.channel_projects.set(
            str(interaction.channel.id),
            project_path
        )

        await interaction.response.send_message(
            f"✅ Channel linked to project: `{project_path}`"
        )

    @app_commands.command(name="unlink")
    async def unlink_channel(self, interaction: discord.Interaction):
        """Unlink this channel from its project."""
        interaction.client.channel_projects.delete(str(interaction.channel.id))
        await interaction.response.send_message("✅ Channel unlinked from project")

    @app_commands.command(name="status")
    async def status(self, interaction: discord.Interaction):
        """Show current channel status."""
        channel_id = str(interaction.channel.id)
        project = interaction.client.channel_projects.get(channel_id)

        if project:
            await interaction.response.send_message(
                f"📁 Linked to: `{project}`\n"
                f"🤖 Mode: Scoped conversations"
            )
        else:
            await interaction.response.send_message(
                f"📁 Not linked to any project\n"
                f"🤖 Mode: Single-shot commands"
            )

    @app_commands.command(name="new")
    async def new_conversation(self, interaction: discord.Interaction):
        """Start a new conversation (clear context)."""
        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel.id)

        # Clear existing thread
        thread_key = f"persistent:{user_id}:{channel_id}"
        await interaction.client.thread_store.delete(thread_key)

        await interaction.response.send_message("🔄 Started new conversation")

    @app_commands.command(name="run")
    async def run_directive(
        self,
        interaction: discord.Interaction,
        directive: str,
        inputs: str = None
    ):
        """Run a specific directive."""
        await interaction.response.defer()

        params = {}
        if inputs:
            try:
                params = json.loads(inputs)
            except json.JSONDecodeError:
                await interaction.followup.send("❌ Invalid JSON for inputs")
                return

        result = await interaction.client.kiwi.mcp.execute(
            item_type="directive",
            action="run",
            item_id=directive,
            parameters=params
        )

        response = format_directive_result(result)
        await interaction.followup.send(response)
```

---

## Wrapper Core Implementation

### KiwiWrapper Class

```python
# kiwi_wrapper/wrapper.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable

class ConversationMode(Enum):
    SINGLE_SHOT = "single_shot"
    PERSISTENT = "persistent"
    SCOPED = "scoped"

@dataclass
class ThreadRef:
    """Reference to an active thread."""
    thread_id: str
    created_at: float
    expires_at: float
    project_path: Optional[str] = None
    memory: Optional["ThreadMemory"] = None

class KiwiWrapper:
    """
    Wrapper around Kiwi MCP for external applications.

    CORE PRINCIPLE: The wrapper does NOT parse intent or construct MCP calls.
    Instead, it spawns threads running the intent_handler directive, which
    uses an LLM to understand the request and make correct MCP calls.

    The wrapper's job is simple:
    - Spawn/continue threads
    - Relay responses (streaming or sync)
    - Handle platform-specific formatting
    """

    def __init__(
        self,
        mcp_url: str,
        mcp_key: str,
        default_mode: ConversationMode = ConversationMode.SINGLE_SHOT,
        default_platform: str = "generic",
        thread_timeout: int = 3600,
    ):
        self.mcp = RemoteMCPClient(mcp_url, mcp_key)
        self.default_mode = default_mode
        self.default_platform = default_platform
        self.thread_timeout = thread_timeout

    # -------------------------------------------------------------------------
    # Main Entry Points (All spawn/continue threads with intent_handler)
    # -------------------------------------------------------------------------

    async def single_shot(
        self,
        message: str,
        user_id: str,
        platform: str = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
        """
        Handle single-shot request.

        Spawns a NEW thread running intent_handler for each request.
        Thread is discarded after response.
        """
        platform = platform or self.default_platform
        thread_id = f"oneshot_{user_id}_{int(time.time())}"

        if stream:
            async for chunk in self._spawn_intent_thread_streaming(
                thread_id=thread_id,
                message=message,
                user_context={"user_id": user_id},
                platform=platform,
            ):
                yield chunk
        else:
            return await self._spawn_intent_thread_sync(
                thread_id=thread_id,
                message=message,
                user_context={"user_id": user_id},
                platform=platform,
            )

    async def persistent_thread(
        self,
        message: str,
        user_id: str,
        thread_key: str,
        thread_store: "ThreadStore",
        platform: str = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
        """
        Handle message in persistent thread.

        Continues existing thread if available, otherwise spawns new one.
        Thread persists for follow-up messages.
        """
        platform = platform or self.default_platform
        thread_ref = await thread_store.get(thread_key)

        if thread_ref and not self._is_expired(thread_ref):
            # Continue existing thread
            if stream:
                async for chunk in self._continue_thread_streaming(
                    thread_ref.thread_id, message
                ):
                    yield chunk
            else:
                return await self._continue_thread_sync(
                    thread_ref.thread_id, message
                )
        else:
            # Spawn new thread
            thread_id = f"conv_{user_id}_{int(time.time())}"

            # Store reference first
            await thread_store.set(thread_key, ThreadRef(
                thread_id=thread_id,
                created_at=time.time(),
                expires_at=time.time() + self.thread_timeout,
            ))

            if stream:
                async for chunk in self._spawn_intent_thread_streaming(
                    thread_id=thread_id,
                    message=message,
                    user_context={"user_id": user_id},
                    platform=platform,
                ):
                    yield chunk
            else:
                return await self._spawn_intent_thread_sync(
                    thread_id=thread_id,
                    message=message,
                    user_context={"user_id": user_id},
                    platform=platform,
                )

    async def scoped_thread(
        self,
        message: str,
        user_id: str,
        thread_key: str,
        project_path: str,
        thread_store: "ThreadStore",
        platform: str = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
        """
        Handle message in project-scoped thread.

        Like persistent_thread, but includes project_path in context.
        The intent_handler uses this to scope MCP calls to the project.
        """
        platform = platform or self.default_platform
        thread_ref = await thread_store.get(thread_key)

        if thread_ref and not self._is_expired(thread_ref):
            if stream:
                async for chunk in self._continue_thread_streaming(
                    thread_ref.thread_id, message
                ):
                    yield chunk
            else:
                return await self._continue_thread_sync(
                    thread_ref.thread_id, message
                )
        else:
            thread_id = f"scoped_{thread_key}_{int(time.time())}"

            await thread_store.set(thread_key, ThreadRef(
                thread_id=thread_id,
                created_at=time.time(),
                expires_at=time.time() + self.thread_timeout,
                project_path=project_path,
            ))

            if stream:
                async for chunk in self._spawn_intent_thread_streaming(
                    thread_id=thread_id,
                    message=message,
                    user_context={"user_id": user_id},
                    platform=platform,
                    project_path=project_path,  # Key difference!
                ):
                    yield chunk
            else:
                return await self._spawn_intent_thread_sync(
                    thread_id=thread_id,
                    message=message,
                    user_context={"user_id": user_id},
                    platform=platform,
                    project_path=project_path,
                )

    # -------------------------------------------------------------------------
    # Thread Spawning/Continuing (Internal)
    # -------------------------------------------------------------------------

    async def _spawn_intent_thread_streaming(
        self,
        thread_id: str,
        message: str,
        user_context: dict,
        platform: str,
        project_path: str = None,
    ) -> AsyncIterator[str]:
        """
        Spawn a new thread running intent_handler and stream response.

        The LLM in the thread understands the natural language request
        and makes the appropriate MCP calls.
        """
        result = await self.mcp.execute(
            item_type="directive",
            action="run",
            item_id="intent_handler",
            parameters={
                "location": "thread",
                "thread_id": thread_id,
                "inputs": {
                    "request": message,
                    "user_context": user_context,
                    "platform": platform,
                    "project_path": project_path,
                },
                "stream": True,
            }
        )

        async for event in result.stream:
            yield event

    async def _spawn_intent_thread_sync(
        self,
        thread_id: str,
        message: str,
        user_context: dict,
        platform: str,
        project_path: str = None,
    ) -> str:
        """Spawn thread and wait for complete response."""
        result = await self.mcp.execute(
            item_type="directive",
            action="run",
            item_id="intent_handler",
            parameters={
                "location": "thread",
                "thread_id": thread_id,
                "inputs": {
                    "request": message,
                    "user_context": user_context,
                    "platform": platform,
                    "project_path": project_path,
                },
                "stream": False,
            }
        )
        return result.get("response", "")

    async def _continue_thread_streaming(
        self,
        thread_id: str,
        message: str,
    ) -> AsyncIterator[str]:
        """Send message to existing thread and stream response."""
        result = await self.mcp.execute(
            item_type="thread",
            action="message",
            item_id=thread_id,
            parameters={
                "message": message,
                "stream": True,
            }
        )

        async for event in result.stream:
            yield event

    async def _continue_thread_sync(
        self,
        thread_id: str,
        message: str,
    ) -> str:
        """Send message to existing thread and wait for response."""
        result = await self.mcp.execute(
            item_type="thread",
            action="message",
            item_id=thread_id,
            parameters={
                "message": message,
                "stream": False,
            }
        )
        return result.get("response", "")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _is_expired(self, thread_ref: ThreadRef) -> bool:
        """Check if thread has expired."""
        return time.time() > thread_ref.expires_at
```

---

## Access Control

### The Access Model with Intent Threading

With intent threading, access control works differently:

1. **The wrapper controls who can spawn threads** (not who can call specific MCP tools)
2. **The intent_handler directive enforces what the user can do** (via Kiwi permissions)
3. **User context is passed to the thread** (user_id, roles, rate limits)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ACCESS CONTROL FLOW                                  │
│                                                                              │
│  User: "@bot deploy to staging"                                              │
│          │                                                                   │
│          ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Wrapper Access Controller                                               │ │
│  │                                                                          │ │
│  │  1. Check: Is user allowed to spawn threads?                             │ │
│  │  2. Check: Rate limit not exceeded?                                      │ │
│  │  3. Build: user_context = { user_id, roles, permissions }                │ │
│  │  4. Pass: user_context into intent_handler                               │ │
│  └────────────────────────────────┬────────────────────────────────────────┘ │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Intent Handler Thread (with user_context)                               │ │
│  │                                                                          │ │
│  │  1. LLM understands request: "deploy to staging"                         │ │
│  │  2. LLM calls: mcp.search(directive, deploy)                             │ │
│  │  3. LLM calls: mcp.execute(directive, run, deploy_staging, ...)          │ │
│  │  4. Kiwi MCP checks: user_context.roles allows this directive?           │ │
│  │     → If no: returns permission denied error                             │ │
│  │     → If yes: executes directive                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### User Permission Mapping

```python
# kiwi_wrapper/access.py

@dataclass
class WrapperUser:
    """User in the wrapper context."""
    external_id: str  # Discord user ID, etc.
    kiwi_user_id: Optional[str]  # Linked Kiwi user
    roles: List[str]  # ["admin", "developer", "viewer"]
    rate_limit: RateLimit

class AccessController:
    """
    Control access at the wrapper level.

    NOTE: This does NOT control what MCP calls are allowed.
    That's handled by Kiwi's permission system inside the thread.

    This controls:
    - Who can spawn threads
    - Rate limiting
    - User context passed to threads
    """

    def __init__(self, user_store: "UserStore"):
        self.user_store = user_store

    async def check_access(
        self,
        external_id: str,
    ) -> tuple[bool, Optional[WrapperUser], Optional[str]]:
        """
        Check if user can spawn a thread.

        Returns: (allowed, user_context, error_message)
        """
        user = await self.user_store.get(external_id)

        if not user:
            # Unknown user - create default
            user = WrapperUser(
                external_id=external_id,
                kiwi_user_id=None,
                roles=["viewer"],  # Default role
                rate_limit=RateLimit(requests_per_minute=10),
            )
            await self.user_store.set(external_id, user)

        # Check rate limit
        if not user.rate_limit.check():
            return False, None, "Rate limit exceeded. Try again in a minute."

        return True, user, None

    def build_user_context(self, user: WrapperUser) -> dict:
        """
        Build user context to pass to intent_handler.

        This context is used by Kiwi MCP to enforce permissions.
        """
        return {
            "user_id": user.external_id,
            "kiwi_user_id": user.kiwi_user_id,
            "roles": user.roles,
            # Kiwi uses these roles to check directive permissions
        }


@dataclass
class RateLimit:
    """Simple rate limiter."""
    requests_per_minute: int
    _requests: List[float] = field(default_factory=list)

    def check(self) -> bool:
        """Check if request is allowed."""
        now = time.time()
        # Remove old requests
        self._requests = [r for r in self._requests if now - r < 60]

        if len(self._requests) >= self.requests_per_minute:
            return False

        self._requests.append(now)
        return True
```

---

## Implementation Phases

### Phase 1: Intent Handler Directive (1-2 days)

1. Create `intent_handler` directive in registry
2. Test with various natural language requests
3. Ensure correct MCP call construction

**Files:**

- Registry: `directives/core/intent_handler.md`
- Tests: `tests/integration/test_intent_handler.py`

### Phase 2: Core Wrapper with Streaming (2-3 days)

1. Implement `RemoteMCPClient` with streaming support
2. Implement `KiwiWrapper` with three modes (single-shot, persistent, scoped)
3. Implement `StreamingResponseHandler` and `SyncResponseHandler`
4. Thread store abstraction (Redis/SQLite backends)

**Files:**

- `kiwi_wrapper/mcp_client.py` (new)
- `kiwi_wrapper/wrapper.py` (new)
- `kiwi_wrapper/streaming.py` (new)
- `kiwi_wrapper/stores/redis.py` (new)
- `kiwi_wrapper/stores/sqlite.py` (new)

### Phase 3: Discord Bot with Streaming (2-3 days)

1. Discord.py integration with streaming updates
2. Slash commands (/link, /unlink, /status, /new)
3. Channel-project linking
4. Platform-specific stream handling (throttled message updates)

**Files:**

- `discord_wrapper/bot.py` (new)
- `discord_wrapper/commands.py` (new)
- `discord_wrapper/stream_handler.py` (new)

### Phase 4: Access Control (1 day)

1. User registration and role mapping
2. Rate limiting at wrapper level
3. User context injection into threads

**Files:**

- `kiwi_wrapper/access.py` (new)

### Phase 5: HTTP API Wrapper (1-2 days)

1. FastAPI wrapper for HTTP clients
2. SSE passthrough for streaming
3. Sync endpoint for webhooks

**Files:**

- `http_wrapper/app.py` (new)
- `http_wrapper/routes.py` (new)

---

## Success Metrics

- [ ] `intent_handler` correctly interprets natural language → MCP calls
- [ ] `intent_handler` queries system info for context-aware responses
- [ ] Single-shot spawns thread, gets response, discards thread
- [ ] Persistent threads maintain context across messages
- [ ] Scoped threads inject project_path correctly
- [ ] Streaming responses update Discord messages in real-time
- [ ] Sync responses work for webhooks/quick commands
- [ ] Rate limiting prevents abuse
- [ ] User context flows through to Kiwi for permission checks
- [ ] Remote codebase access works via HTTP wrapper

---

## Related Documents

- `THREAD_AND_STREAMING_ARCHITECTURE.md` - Thread and harness design
- `INIT_PROCESS_DESIGN.md` - MCP initialization and system item type
- `KNOWLEDGE_SYSTEM_DESIGN.md` - RAG-based help system
- `MCP_2_INTENT_DESIGN.md` - Future intent abstraction (FunctionGemma)
