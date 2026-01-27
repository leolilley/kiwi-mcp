# Clawdbot Kiwi MCP Implementation Examples

This document provides concrete code examples for implementing clawdbot-like functionality using Kiwi MCP.

## Example 1: Telegram Channel Tool

### Tool: `channel_telegram.py`

```python
"""Telegram channel integration tool for Kiwi MCP."""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json
from grammY import Bot, Context
from grammY.types import Message

logger = logging.getLogger("channel_telegram")


class TelegramChannelTool:
    """Tool for Telegram channel operations."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with config."""
        self.config_path = config_path or Path.home() / ".kiwi" / "telegram_config.json"
        self.bot: Optional[Bot] = None
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load Telegram configuration."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = json.load(f)
        else:
            raise ValueError(f"Telegram config not found at {self.config_path}")
    
    async def connect(self) -> Dict[str, Any]:
        """Connect to Telegram and start listening."""
        bot_token = self.config.get("botToken")
        if not bot_token:
            raise ValueError("botToken required in config")
        
        self.bot = Bot(bot_token)
        
        # Set up message handler
        @self.bot.on.message()
        async def handle_message(ctx: Context):
            message_data = {
                "channel": "telegram",
                "chat_id": str(ctx.chat.id),
                "user_id": str(ctx.from_user.id),
                "username": ctx.from_user.username,
                "text": ctx.message.text,
                "timestamp": ctx.message.date.isoformat(),
            }
            
            # Emit event via MCP (would need event system)
            # For now, return message data
            return message_data
        
        # Start bot
        await self.bot.start()
        
        return {
            "status": "connected",
            "bot_username": (await self.bot.get_me()).username,
        }
    
    async def send_message(
        self,
        chat_id: str,
        message: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message to a Telegram chat."""
        if not self.bot:
            await self.connect()
        
        try:
            sent = await self.bot.api.send_message(
                chat_id=int(chat_id),
                text=message,
                reply_to_message_id=int(reply_to) if reply_to else None,
            )
            
            return {
                "status": "sent",
                "message_id": str(sent.message_id),
                "chat_id": chat_id,
            }
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """Get information about a chat."""
        if not self.bot:
            await self.connect()
        
        try:
            chat = await self.bot.api.get_chat(chat_id=int(chat_id))
            return {
                "chat_id": str(chat.id),
                "type": chat.type,
                "title": getattr(chat, "title", None),
                "username": getattr(chat, "username", None),
            }
        except Exception as e:
            logger.error(f"Failed to get chat info: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
```

### Tool Manifest: `.ai/tools/channel_telegram.md`

```markdown
---
tool_name: channel_telegram
version: 1.0.0
description: Telegram channel integration for sending and receiving messages
category: channel
author: kiwi-mcp
language: python
---

# Telegram Channel Tool

## Purpose
Handles Telegram bot integration for sending and receiving messages.

## Parameters

### connect()
Connects to Telegram and starts listening for messages.

**Returns:**
- `status`: Connection status
- `bot_username`: Bot username

### send_message(chat_id: str, message: str, reply_to: Optional[str] = None)
Sends a message to a Telegram chat.

**Parameters:**
- `chat_id`: Telegram chat ID
- `message`: Message text to send
- `reply_to`: Optional message ID to reply to

**Returns:**
- `status`: "sent" or "error"
- `message_id`: ID of sent message
- `error`: Error message if failed

### get_chat_info(chat_id: str)
Gets information about a Telegram chat.

**Parameters:**
- `chat_id`: Telegram chat ID

**Returns:**
- Chat information including type, title, username

## Configuration
Requires `~/.kiwi/telegram_config.json`:
```json
{
  "botToken": "YOUR_BOT_TOKEN"
}
```

## Dependencies
- grammY
```

## Example 2: Message Handling Directive

### Directive: `.ai/directives/handle_inbound_message.xml`

```xml
<directive name="handle_inbound_message" version="1.0.0">
  <metadata>
    <description>Orchestrates handling of inbound messages from any channel</description>
    <category>message</category>
    <author>kiwi-mcp</author>
    <model tier="orchestrator" fallback="general">
      Multi-step message handling with session management and routing
    </model>
    <permissions>
      <read resource="session" path="**/*" />
      <execute resource="channel" action="send" />
      <execute resource="llm" action="chat" />
    </permissions>
  </metadata>

  <context>
    <tech_stack>any</tech_stack>
  </context>

  <inputs>
    <input name="channel" type="string" required="true">
      Channel name (telegram, whatsapp, slack, etc.)
    </input>
    <input name="message_data" type="object" required="true">
      Message data from channel tool
    </input>
    <input name="project_path" type="string" required="true">
      Project path for session management
    </input>
  </inputs>

  <process>
    <step name="validate_message">
      <description>Validate incoming message data</description>
      <action>
        1. Check message_data has required fields (chat_id, user_id, text)
        2. Validate channel is supported
        3. Check allowlist if configured
      </action>
      <tool_call>
        <tool>validate_message</tool>
        <params>
          <channel>${channel}</channel>
          <message_data>${message_data}</message_data>
        </params>
      </tool_call>
    </step>

    <step name="get_or_create_session">
      <description>Get or create session for this chat</description>
      <action>
        1. Generate session_id from channel + chat_id
        2. Check if session exists
        3. Create new session if needed
        4. Load session context
      </action>
      <tool_call>
        <tool>session_manager</tool>
        <action>get_or_create</action>
        <params>
          <session_id>${channel}:${message_data.chat_id}</session_id>
          <project_path>${project_path}</project_path>
        </params>
      </tool_call>
    </step>

    <step name="check_pairing">
      <description>Check if sender is paired/approved</description>
      <action>
        1. Load pairing configuration from knowledge
        2. Check if user_id is in allowlist
        3. If not paired and dmPolicy="pairing", send pairing code
        4. If not paired and dmPolicy="open", proceed
      </action>
      <tool_call>
        <tool>pairing_check</tool>
        <params>
          <channel>${channel}</channel>
          <user_id>${message_data.user_id}</user_id>
          <chat_id>${message_data.chat_id}</chat_id>
          <project_path>${project_path}</project_path>
        </params>
      </tool_call>
    </step>

    <step name="process_with_agent">
      <description>Process message with AI agent</description>
      <action>
        1. Load agent personality from knowledge
        2. Build context from session history
        3. Call LLM with message and context
        4. Stream response if needed
      </action>
      <tool_call>
        <tool>llm_chat</tool>
        <params>
          <session_id>${session_id}</session_id>
          <message>${message_data.text}</message>
          <context>${session_context}</context>
          <project_path>${project_path}</project_path>
        </params>
      </tool_call>
    </step>

    <step name="send_response">
      <description>Send response back to channel</description>
      <action>
        1. Format response for channel
        2. Send via channel tool
        3. Update session with response
      </action>
      <tool_call>
        <tool>channel_${channel}</tool>
        <action>send_message</action>
        <params>
          <chat_id>${message_data.chat_id}</chat_id>
          <message>${agent_response}</message>
          <reply_to>${message_data.message_id}</reply_to>
        </params>
      </tool_call>
    </step>

    <step name="update_session">
      <description>Update session with new messages</description>
      <action>
        1. Add user message to session
        2. Add agent response to session
        3. Apply compaction if needed
        4. Save session state
      </action>
      <tool_call>
        <tool>session_manager</tool>
        <action>update</action>
        <params>
          <session_id>${session_id}</session_id>
          <messages>
            <user_message>${message_data.text}</user_message>
            <agent_response>${agent_response}</agent_response>
          </messages>
          <project_path>${project_path}</project_path>
        </params>
      </tool_call>
    </step>
  </process>

  <outputs>
    <success>
      Message processed and response sent
    </success>
    <error>
      Error details with context
    </error>
  </outputs>
</directive>
```

## Example 3: Session Manager Tool

### Tool: `session_manager.py`

```python
"""Session management tool for Kiwi MCP."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

logger = logging.getLogger("session_manager")


class SessionManagerTool:
    """Tool for managing agent sessions."""
    
    def __init__(self, project_path: Path):
        """Initialize with project path."""
        self.project_path = Path(project_path)
        self.sessions_dir = self.project_path / ".ai" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def _session_path(self, session_id: str) -> Path:
        """Get path to session file."""
        # Sanitize session_id for filename
        safe_id = hashlib.md5(session_id.encode()).hexdigest()
        return self.sessions_dir / f"{safe_id}.json"
    
    def get_or_create(
        self,
        session_id: str,
        channel: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get existing session or create new one."""
        session_path = self._session_path(session_id)
        
        if session_path.exists():
            with open(session_path) as f:
                session = json.load(f)
            logger.info(f"Loaded existing session: {session_id}")
            return session
        
        # Create new session
        session = {
            "session_id": session_id,
            "channel": channel,
            "chat_id": chat_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "messages": [],
            "context": {},
            "metadata": {},
        }
        
        self._save_session(session)
        logger.info(f"Created new session: {session_id}")
        return session
    
    def update(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update session with new messages."""
        session_path = self._session_path(session_id)
        
        if not session_path.exists():
            raise ValueError(f"Session not found: {session_id}")
        
        with open(session_path) as f:
            session = json.load(f)
        
        # Add new messages
        session["messages"].extend(messages)
        
        # Update context if provided
        if context:
            session["context"].update(context)
        
        # Update timestamp
        session["updated_at"] = datetime.utcnow().isoformat()
        
        self._save_session(session)
        return session
    
    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get session message history."""
        session_path = self._session_path(session_id)
        
        if not session_path.exists():
            return []
        
        with open(session_path) as f:
            session = json.load(f)
        
        messages = session.get("messages", [])
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def compact(
        self,
        session_id: str,
        strategy: str = "summary",
    ) -> Dict[str, Any]:
        """Compact session history."""
        session_path = self._session_path(session_id)
        
        if not session_path.exists():
            raise ValueError(f"Session not found: {session_id}")
        
        with open(session_path) as f:
            session = json.load(f)
        
        messages = session.get("messages", [])
        
        if strategy == "summary":
            # Keep last N messages, summarize rest
            keep_count = 10
            if len(messages) > keep_count:
                # Summarize old messages (would call LLM)
                old_messages = messages[:-keep_count]
                # For now, just truncate
                session["messages"] = messages[-keep_count:]
                session["context"]["summary"] = f"Summarized {len(old_messages)} messages"
        
        session["updated_at"] = datetime.utcnow().isoformat()
        self._save_session(session)
        
        return session
    
    def _save_session(self, session: Dict[str, Any]):
        """Save session to disk."""
        session_path = self._session_path(session["session_id"])
        with open(session_path, "w") as f:
            json.dump(session, f, indent=2)
    
    def list_sessions(
        self,
        channel: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by channel."""
        sessions = []
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file) as f:
                    session = json.load(f)
                
                if channel and session.get("channel") != channel:
                    continue
                
                sessions.append({
                    "session_id": session["session_id"],
                    "channel": session.get("channel"),
                    "chat_id": session.get("chat_id"),
                    "message_count": len(session.get("messages", [])),
                    "updated_at": session.get("updated_at"),
                })
            except Exception as e:
                logger.error(f"Error reading session {session_file}: {e}")
        
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return sessions[:limit]
```

## Example 4: LLM Chat Tool

### Tool: `llm_chat.py`

```python
"""LLM chat tool for Kiwi MCP."""

import logging
from typing import Dict, Any, Optional, List, AsyncIterator
from pathlib import Path
import json

logger = logging.getLogger("llm_chat")


class LLMChatTool:
    """Tool for interacting with LLM APIs."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with config."""
        self.config_path = config_path or Path.home() / ".kiwi" / "llm_config.json"
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load LLM configuration."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = json.load(f)
        else:
            # Default config
            self.config = {
                "provider": "anthropic",
                "model": "claude-opus-4-5",
                "api_key": None,  # Should come from env
            }
    
    async def chat(
        self,
        message: str,
        context: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Send message to LLM and get response."""
        provider = self.config.get("provider", "anthropic")
        model = self.config.get("model", "claude-opus-4-5")
        
        # Build messages from context
        messages = []
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": message})
        
        if provider == "anthropic":
            return await self._chat_anthropic(messages, model, stream)
        elif provider == "openai":
            return await self._chat_openai(messages, model, stream)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def _chat_anthropic(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool,
    ) -> Dict[str, Any]:
        """Chat with Anthropic API."""
        import anthropic
        
        api_key = self.config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Convert messages format
        system_message = None
        chat_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content")
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        if stream:
            # Streaming response
            response_text = ""
            async with client.messages.stream(
                model=model,
                max_tokens=4096,
                system=system_message,
                messages=chat_messages,
            ) as stream:
                async for text in stream.text_stream:
                    response_text += text
                    yield {"type": "chunk", "content": text}
            
            yield {
                "type": "complete",
                "content": response_text,
            }
        else:
            # Non-streaming response
            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_message,
                messages=chat_messages,
            )
            
            return {
                "status": "success",
                "content": response.content[0].text,
                "model": model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }
    
    async def _chat_openai(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool,
    ) -> Dict[str, Any]:
        """Chat with OpenAI API."""
        from openai import AsyncOpenAI
        
        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY required")
        
        client = AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
        )
        
        if stream:
            response_text = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_text += content
                    yield {"type": "chunk", "content": content}
            
            yield {
                "type": "complete",
                "content": response_text,
            }
        else:
            return {
                "status": "success",
                "content": response.choices[0].message.content,
                "model": model,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                },
            }
```

## Example 5: Knowledge Entry for Agent Personality

### Knowledge: `.ai/knowledge/agent_personality.md`

```markdown
---
zettel_id: agent_personality
title: Personal AI Assistant Personality
entry_type: pattern
category: agent
references:
  - agent_behavior_guidelines
extends:
  - base_assistant_pattern
---

# Personal AI Assistant Personality

## Core Principles

1. **Helpful but not intrusive**: Assist when asked, don't be pushy
2. **Context-aware**: Remember conversation history and user preferences
3. **Honest about limitations**: Admit when you don't know something
4. **Respectful of privacy**: Don't share user data without permission

## Communication Style

- **Tone**: Friendly, professional, concise
- **Format**: Use markdown for structure, code blocks for code
- **Emojis**: Use sparingly, only when appropriate
- **Length**: Keep responses focused, break long responses into sections

## System Prompt Template

```
You are a personal AI assistant running on the user's device.

Your capabilities:
- Answer questions and provide information
- Help with tasks and workflows
- Execute tools and scripts when needed
- Remember context across conversations

Your constraints:
- You run locally and respect user privacy
- You have access to tools but require user approval for sensitive operations
- You maintain session context but can forget old information if needed

Current session: ${session_id}
Channel: ${channel}
User: ${user_id}
```

## Behavior Patterns

### Message Handling
- Always acknowledge receipt of messages
- Process requests in order
- Stream long responses when possible
- Provide status updates for long-running tasks

### Error Handling
- Explain errors clearly
- Suggest solutions when possible
- Don't expose internal implementation details
- Log errors for debugging

### Tool Execution
- Explain what tool you're about to use
- Show results clearly
- Handle tool failures gracefully
- Ask for confirmation for destructive operations
```

## Example 6: Channel Router Directive

### Directive: `.ai/directives/channel_router.xml`

```xml
<directive name="channel_router" version="1.0.0">
  <metadata>
    <description>Routes messages from different channels to appropriate handlers</description>
    <category>routing</category>
  </metadata>

  <inputs>
    <input name="channel" type="string" required="true" />
    <input name="message_data" type="object" required="true" />
    <input name="project_path" type="string" required="true" />
  </inputs>

  <process>
    <step name="identify_channel">
      <description>Identify channel type and load channel-specific config</description>
      <action>
        Load knowledge: channel_configs for ${channel}
        Validate message_data format for channel
      </action>
    </step>

    <step name="check_routing_rules">
      <description>Check if message should be routed to specific agent</description>
      <action>
        Load knowledge: routing_rules
        Match channel/peer/account to agent workspace
        If match found, set agent_workspace
      </action>
    </step>

    <step name="route_to_handler">
      <description>Route to message handler with appropriate workspace</description>
      <action>
        Execute directive: handle_inbound_message
        With project_path = agent_workspace or default
        Pass channel and message_data
      </action>
    </step>
  </process>
</directive>
```

## Usage Example

### Starting the System

```python
# 1. Start MCP server (exposes Kiwi MCP tools)
# This would be done via MCP server implementation

# 2. Connect Telegram channel
result = mcp_kiwi_mcp_execute(
    item_type="tool",
    action="run",
    item_id="channel_telegram",
    parameters={"action": "connect"},
    project_path="/path/to/project"
)

# 3. Set up message listener (would be event-driven in real implementation)
# When message arrives, execute directive:

result = mcp_kiwi_mcp_execute(
    item_type="directive",
    action="run",
    item_id="handle_inbound_message",
    parameters={
        "channel": "telegram",
        "message_data": {
            "chat_id": "123456789",
            "user_id": "987654321",
            "text": "Hello!",
        },
        "project_path": "/path/to/project",
    },
    project_path="/path/to/project"
)
```

## Key Differences from Clawdbot

1. **Modularity**: Each component (channel, session, LLM) is a separate tool
2. **Orchestration**: Workflow logic is in directives, not hardcoded
3. **Configuration**: Stored as knowledge entries, not JSON files
4. **Discovery**: Tools/directives/knowledge can be searched and loaded dynamically
5. **Sharing**: Components can be published to registry and shared

This approach provides the same functionality as clawdbot but with better composability, extensibility, and maintainability.
