# Intent Directive: Natural Language to Kiwi-MCP Tool Calls

**Date:** 2026-01-28  
**Status:** Planning  
**Author:** Kiwi Team

---

## Executive Summary

The `intent_directive` is a specialized directive that takes plain English user input and outputs a structured kiwi-mcp tool call command. This enables a simple HTTP server wrapper around the MCP that can route chat/tool intent requests into MCP tool calls, providing full access to registry intelligence and actions through a single exposed tool call.

**Key Insight:** By leveraging our threading architecture, one single exposure tool call (`intent_directive`) gives any client full access to the entire registry intelligence and actions.

---

## Problem Statement

### Current State

- Kiwi MCP exposes 4 unified tools: `search`, `load`, `execute`, `help`
- Clients must know the exact tool syntax and parameters
- Direct tool calls require understanding of:
  - Item types (directive, tool, knowledge)
  - Actions (run, sign, etc.)
  - Parameter structures
  - Project paths

### Desired State

- HTTP server wrapper around MCP
- Single endpoint: `/intent` that accepts plain English
- Returns structured tool call command
- Enables natural language access to entire registry

### Use Case

```
User (via HTTP): "I want to search for directives about email campaigns"
     ↓
HTTP Server: POST /intent { "query": "I want to search for directives about email campaigns" }
     ↓
MCP Tool Call: execute(item_type="directive", action="run", item_id="intent_directive", parameters={"user_input": "..."})
     ↓
intent_directive: Analyzes intent, searches registry, returns tool call
     ↓
HTTP Server: Returns { "tool_call": { "tool": "search", "arguments": {...} } }
     ↓
HTTP Server: Executes the tool call via MCP
     ↓
User: Gets results
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HTTP Server (Wrapper)                             │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  POST /intent                                                   │ │
│  │  { "query": "plain english user request" }                     │ │
│  └───────────────────────┬───────────────────────────────────────┘ │
│                          │                                          │
│                          ▼                                          │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  MCP Tool Call: execute(intent_directive, ...)               │ │
│  └───────────────────────┬───────────────────────────────────────┘ │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Kiwi MCP Server                                  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  intent_directive (Directive)                                   │ │
│  │  • Takes: user_input (plain English)                           │ │
│  │  • Uses: search tool to find relevant items                    │ │
│  │  • Uses: knowledge base for intent patterns                     │ │
│  │  • Outputs: structured tool call JSON                          │ │
│  └───────────────────────┬───────────────────────────────────────┘ │
│                          │                                          │
│                          ▼                                          │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Tool Call Output:                                             │ │
│  │  {                                                              │ │
│  │    "tool": "search",                                           │ │
│  │    "arguments": {                                              │ │
│  │      "item_type": "directive",                                 │ │
│  │      "query": "email campaigns",                               │ │
│  │      "source": "local",                                        │ │
│  │      "project_path": "/path/to/project"                        │ │
│  │    }                                                            │ │
│  │  }                                                              │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HTTP Server (Wrapper)                             │
│                                                                      │
│  • Receives tool call from intent_directive                         │
│  • Executes tool call via MCP                                        │
│  • Returns results to user                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Intent Directive Design

### Directive Structure

```xml
<directive name="intent_directive" version="1.0.0">
  <metadata>
    <description>Converts plain English user requests into structured kiwi-mcp tool calls</description>
    <category>core</category>
    <author>kiwi-mcp</author>
    <model tier="reasoning" fallback="general">
      Requires reasoning to understand user intent and map to correct tool calls
    </model>
    <permissions>
      <read resource="filesystem" path="**/*" />
      <execute resource="kiwi-mcp" action="search" />
      <execute resource="kiwi-mcp" action="load" />
      <execute resource="kiwi-mcp" action="execute" />
      <read resource="knowledge" path="**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="user_input" type="string" required="true">
      Plain English description of what the user wants to do
    </input>
    <input name="project_path" type="string" required="true">
      Absolute path to project root (where .ai/ folder lives)
    </input>
    <input name="context" type="object" required="false">
      Additional context about the request (conversation history, user preferences, etc.)
    </input>
    <input name="agent_config" type="object" required="false">
      Agent configuration defining identity, context, permissions, and cost limits.
      If not provided, uses default neutral agent configuration.
      Structure:
      {
        "identity": {
          "name": "Agent name",
          "spoken_style": "description of communication style",
          "personality": "agent personality description",
          "tone": "tone of voice"
        },
        "context": {
          "domain_knowledge": ["list of domain facts"],
          "constraints": ["list of hard constraints"],
          "guidelines": ["list of preferred approaches"]
        },
        "permissions": {
          "filesystem": {"read": [...], "write": [...], "forbidden": [...]},
          "kiwi-mcp": {"search": {...}, "load": {...}, "execute": {...}},
          "network": {"allowed_endpoints": [...]}
        },
        "cost_limits": {
          "daily_budget_usd": 10.00,
          "per_request_max_usd": 1.00,
          "total_budget_usd": 500.00
        }
      }
    </input>
  </inputs>

  <process>
    <step name="apply_agent_config">
      <description>Apply agent configuration to set context, permissions, and constraints</description>
      <action>
        1. Load agent_config if provided, otherwise use default neutral config
        2. Inject domain knowledge into reasoning context
        3. Apply constraints and guidelines to intent parsing
        4. Check cost limits and budget availability
        5. Validate permissions for requested operations
      </action>
    </step>

    <step name="parse_intent">
      <description>Analyze user input to understand intent, influenced by agent context</description>
      <action>
        1. Extract key verbs: search, find, load, run, execute, create, delete, etc.
        2. Identify item types mentioned: directive, tool, knowledge, script
        3. Extract parameters: query terms, item names, action details
        4. Determine target tool: search, load, execute, help
        5. Apply agent's domain knowledge to refine intent understanding
        6. Check against agent's constraints and guidelines
      </action>
    </step>

    <step name="search_registry">
      <description>Search registry for relevant items if item names are mentioned</description>
      <action>
        If user mentions specific item names:
        1. Search for matching directives, tools, or knowledge entries
        2. Use search results to refine tool call parameters
        3. If exact match found, use item_id directly
      </action>
      <tool_call>
        <mcp>kiwi-mcp</mcp>
        <tool>search</tool>
        <params>
          <item_type>inferred from user_input</item_type>
          <query>extracted keywords from user_input</query>
          <source>local</source>
          <project_path>project_path</project_path>
        </params>
      </tool_call>
    </step>

    <step name="validate_permissions_and_cost">
      <description>Check permissions and cost limits before building tool call</description>
      <action>
        1. Verify requested operations are allowed by agent permissions
        2. Check if tool call would exceed per-request cost limit
        3. Verify daily budget has sufficient remaining funds
        4. Check total budget availability
        5. If any check fails, return error with suggestions for alternative approaches
      </action>
    </step>

    <step name="build_tool_call">
      <description>Construct structured tool call JSON with agent context</description>
      <action>
        1. Map intent to one of 4 meta-tools: search, load, execute, help
        2. Build arguments object with required parameters
        3. Include project_path in all tool calls
        4. Apply agent's spoken style to response formatting
        5. Include agent identity in response metadata
        6. Format as JSON for easy execution
      </action>
    </step>

    <step name="validate_output">
      <description>Validate the generated tool call structure</description>
      <action>
        1. Check that tool name is one of: search, load, execute, help
        2. Verify required parameters are present
        3. Ensure project_path is included
        4. Validate item_type if present (must be directive, tool, or knowledge)
        5. Validate action if present (must be run, sign, etc.)
      </action>
    </step>
  </process>

  <outputs>
    <success>
      Returns JSON object with tool call structure:
      {
        "tool": "search|load|execute|help",
        "arguments": {
          "item_type": "directive|tool|knowledge",
          "action": "run|sign|...",
          "item_id": "...",
          "query": "...",
          "parameters": {...},
          "project_path": "..."
        },
        "confidence": 0.0-1.0,
        "reasoning": "explanation of how intent was mapped",
        "agent_identity": {
          "name": "Agent name from config",
          "spoken_style": "Style applied to response"
        },
        "response_style": "How the agent would phrase the response",
        "cost_estimate": {
          "usd": 0.05,
          "tokens_estimate": 1000
        },
        "permissions_checked": true
      }
    </success>
  </outputs>
</directive>
```

---

## Agent Customization: Traditional Agent Approaches

The `intent_directive` can be configured to create traditional agent approaches with distinct identities, contexts, permissions, and cost controls. Instead of building separate specialized agents, you configure one frontend directive with different parameters to create different agent personalities and capabilities.

### Core Concept

**One Directive, Many Agents**: The `intent_directive` acts as a configurable frontend that can be instantiated with different configurations to create different agent behaviors. All agents share the same underlying MCP infrastructure but have different:

- **Identity**: Spoken style, personality, tone
- **Context**: Domain knowledge, constraints, guidelines
- **Permissions**: What resources they can access
- **Cost Limits**: Budget controls and spending caps

### Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Agent Configuration Layer                         │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Coder Agent     │  │  Researcher Agent │  │  Deployer Agent   │ │
│  │  Config:          │  │  Config:          │  │  Config:          │ │
│  │  - Identity:      │  │  - Identity:      │  │  - Identity:      │ │
│  │    "Technical,    │  │    "Analytical,   │  │    "Precise,       │ │
│  │     concise"      │  │     thorough"     │  │     safety-first"  │ │
│  │  - Context:        │  │  - Context:        │  │  - Context:        │ │
│  │    Code patterns, │  │    Research        │  │    Deployment      │ │
│  │    best practices │  │    methodologies   │  │    procedures      │ │
│  │  - Permissions:   │  │  - Permissions:   │  │  - Permissions:   │ │
│  │    filesystem,    │  │    knowledge,      │  │    registry,      │ │
│  │    git, code      │  │    web search      │  │    infrastructure │ │
│  │  - Cost: $5/day   │  │  - Cost: $10/day  │  │  - Cost: $20/day  │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │
│           │                     │                     │            │
│           └─────────────────────┼─────────────────────┘            │
│                                 │                                   │
│                                 ▼                                   │
│                    ┌────────────────────────┐                      │
│                    │  intent_directive      │                      │
│                    │  (Configurable)        │                      │
│                    └───────────┬────────────┘                      │
└─────────────────────────────────┼──────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Unified Kiwi MCP Infrastructure                  │
│                                                                      │
│  • search, load, execute, help tools                                │
│  • Registry with directives, tools, knowledge                      │
│  • Threading architecture                                           │
│  • Permission enforcement                                           │
│  • Cost tracking                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Configuration Structure

The `intent_directive` accepts an `agent_config` parameter that defines the agent's behavior:

```json
{
  "user_input": "create a new Python script for data processing",
  "project_path": "/home/user/project",
  "agent_config": {
    "identity": {
      "name": "Coder Agent",
      "spoken_style": "technical, concise, code-first",
      "personality": "Efficient problem solver who prefers code over explanation",
      "tone": "professional, direct"
    },
    "context": {
      "domain_knowledge": [
        "Python best practices",
        "Code structure patterns",
        "Testing methodologies"
      ],
      "constraints": [
        "Always include error handling",
        "Follow PEP 8 style guide",
        "Write docstrings for all functions"
      ],
      "guidelines": [
        "Prefer async/await for I/O operations",
        "Use type hints",
        "Keep functions under 50 lines"
      ]
    },
    "permissions": {
      "filesystem": {
        "read": ["**/*.py", "**/*.md", "**/*.yaml"],
        "write": [".ai/tools/**", "src/**"]
      },
      "kiwi-mcp": {
        "search": ["directive", "tool", "knowledge"],
        "load": ["directive", "tool"],
        "execute": ["tool"]
      },
      "network": {
        "allowed_endpoints": ["api.github.com", "pypi.org"]
      }
    },
    "cost_limits": {
      "daily_budget_usd": 5.00,
      "per_request_max_usd": 0.50,
      "total_budget_usd": 100.00,
      "terminate_on_exceed": true
    }
  }
}
```

### Identity Configuration

The `identity` section defines how the agent speaks and behaves:

```json
{
  "identity": {
    "name": "Researcher Agent",
    "spoken_style": "analytical, thorough, detail-oriented",
    "personality": "Curious investigator who explores all angles before concluding",
    "tone": "academic, inquisitive",
    "response_format": "structured with citations",
    "greeting": "Hello! I'm here to help you research and analyze. What would you like to explore?",
    "signature_phrases": [
      "Let me investigate this further...",
      "Based on my research...",
      "I found several relevant sources..."
    ]
}
```

**Example Agent Identities:**

| Agent Type | Spoken Style | Personality | Use Case |
|------------|--------------|------------|----------|
| **Coder Agent** | Technical, concise | Code-first problem solver | Software development |
| **Researcher Agent** | Analytical, thorough | Detail-oriented investigator | Research and analysis |
| **Deployer Agent** | Precise, safety-first | Risk-averse executor | Production deployments |
| **Helper Agent** | Friendly, patient | Supportive guide | User assistance |
| **Analyst Agent** | Data-driven, objective | Number-focused evaluator | Data analysis |

### Context Injection

The `context` section hard-injects domain knowledge, constraints, and guidelines into the agent's reasoning:

```json
{
  "context": {
    "domain_knowledge": [
      "Email marketing best practices",
      "Campaign optimization strategies",
      "A/B testing methodologies"
    ],
    "constraints": [
      "Never send emails without user consent",
      "Always include unsubscribe links",
      "Respect rate limits"
    ],
    "guidelines": [
      "Prefer segmentation over broadcast",
      "Test subject lines before sending",
      "Monitor open rates and adjust"
    ],
    "examples": [
      {
        "scenario": "User wants to create email campaign",
        "approach": "Search for email campaign directive, load it, execute with user parameters"
      }
    ],
    "forbidden_actions": [
      "Deleting production data",
      "Modifying core directives",
      "Accessing user personal information"
    ]
}
```

**Context Types:**

1. **Domain Knowledge**: Facts, patterns, best practices specific to the agent's domain
2. **Constraints**: Hard limits that cannot be violated
3. **Guidelines**: Preferred approaches and recommendations
4. **Examples**: Common scenarios and how to handle them
5. **Forbidden Actions**: Explicitly disallowed operations

### Permission Hardening

The `permissions` section restricts what the agent can access:

```json
{
  "permissions": {
    "filesystem": {
      "read": [".ai/**", "src/**", "docs/**"],
      "write": [".ai/tools/**", "src/**"],
      "execute": ["src/**/*.py"],
      "forbidden": ["**/secrets/**", "**/.env", "**/credentials/**"]
    },
    "kiwi-mcp": {
      "search": {
        "item_types": ["directive", "tool"],
        "forbidden_queries": ["delete", "remove", "destroy"]
      },
      "load": {
        "item_types": ["directive", "tool"],
        "sources": ["local", "registry"]
      },
      "execute": {
        "actions": ["run"],
        "forbidden_actions": ["delete", "sign"]
      }
    },
    "network": {
      "allowed_endpoints": [
        "api.github.com",
        "pypi.org",
        "docs.python.org"
      ],
      "forbidden_endpoints": ["*"]
    },
    "registry": {
      "read": true,
      "write": false,
      "publish": false
    }
}
```

**Permission Enforcement:**

- Permissions are checked **before** tool execution
- Violations return structured errors with suggestions
- All permission checks are logged for audit
- Permissions can be updated dynamically (with proper authorization)

### Cost Control

The `cost_limits` section enforces budget constraints:

```json
{
  "cost_limits": {
    "daily_budget_usd": 10.00,
    "per_request_max_usd": 1.00,
    "total_budget_usd": 500.00,
    "terminate_on_exceed": true,
    "warn_at_percent": 80,
    "tracking": {
      "model_calls": true,
      "tool_executions": true,
      "api_requests": true
    },
    "throttling": {
      "max_requests_per_minute": 60,
      "max_requests_per_hour": 1000
    }
}
```

**Cost Tracking:**

- Tracks all model API calls (tokens × cost per token)
- Tracks tool execution costs (compute time, API calls)
- Enforces limits at multiple levels (per-request, daily, total)
- Provides warnings before limits are reached
- Can terminate or throttle when limits exceeded

### Example: Creating a Specialized Agent

**Scenario**: Create a "Security Auditor Agent" that reviews code for security issues.

```json
{
  "agent_config": {
    "identity": {
      "name": "Security Auditor",
      "spoken_style": "cautious, detail-oriented, security-focused",
      "personality": "Paranoid security expert who finds vulnerabilities others miss",
      "tone": "serious, warning-focused"
    },
    "context": {
      "domain_knowledge": [
        "OWASP Top 10 vulnerabilities",
        "Common security anti-patterns",
        "Secure coding practices",
        "Cryptography best practices"
      ],
      "constraints": [
        "Never suggest disabling security features",
        "Always recommend least privilege",
        "Flag any hardcoded credentials"
      ],
      "guidelines": [
        "Check for SQL injection risks",
        "Verify input validation",
        "Review authentication mechanisms",
        "Audit authorization checks"
      ]
    },
    "permissions": {
      "filesystem": {
        "read": ["**/*.py", "**/*.js", "**/*.ts", "**/*.yaml", "**/*.json"],
        "write": [],
        "execute": []
      },
      "kiwi-mcp": {
        "search": {
          "item_types": ["tool", "knowledge"],
          "queries": ["security", "vulnerability", "audit"]
        },
        "load": {
          "item_types": ["tool", "knowledge"]
        },
        "execute": {
          "actions": ["run"],
          "item_types": ["tool"]
        }
      },
      "network": {
        "allowed_endpoints": ["api.github.com/security"]
      }
    },
    "cost_limits": {
      "daily_budget_usd": 15.00,
      "per_request_max_usd": 2.00,
      "total_budget_usd": 300.00
    }
  }
}
```

**Usage:**

```python
# HTTP request to create security audit
POST /intent
{
  "query": "Review my authentication code for security issues",
  "project_path": "/home/user/project",
  "agent_config": { /* security auditor config above */ }
}
```

The agent will:
1. Use security-focused language and tone
2. Apply security domain knowledge
3. Only access code files (no write permissions)
4. Stay within budget limits
5. Return security-focused analysis

### Agent Instantiation Patterns

#### Pattern 1: Pre-configured Agent Directives

Create specialized directive files that wrap `intent_directive` with hardcoded configs:

```xml
<!-- .ai/directives/agents/coder_agent.md -->
<directive name="coder_agent" version="1.0.0">
  <metadata>
    <description>Coder agent with technical focus and code permissions</description>
  </metadata>
  <process>
    <step name="call_intent_directive">
      <action>
        Call intent_directive with hardcoded coder_agent config
      </action>
      <tool_call>
        <mcp>kiwi-mcp</mcp>
        <tool>execute</tool>
        <params>
          <item_type>directive</item_type>
          <action>run</action>
          <item_id>intent_directive</item_id>
          <parameters>
            <user_input>user_input</user_input>
            <project_path>project_path</project_path>
            <agent_config>
              <!-- Hardcoded coder agent config -->
            </agent_config>
          </parameters>
        </params>
      </tool_call>
    </step>
  </process>
</directive>
```

#### Pattern 2: Dynamic Agent Selection

HTTP server selects agent config based on route or header:

```python
@app.post("/agent/{agent_name}/intent")
async def handle_agent_intent(agent_name: str, request: IntentRequest):
    # Load agent config from registry
    agent_config = await load_agent_config(agent_name)
    
    # Call intent_directive with agent config
    result = await mcp.tools["execute"].execute({
        "item_type": "directive",
        "action": "run",
        "item_id": "intent_directive",
        "parameters": {
            "user_input": request.query,
            "project_path": request.project_path,
            "agent_config": agent_config
        }
    })
    # ... rest of execution
```

#### Pattern 3: User-Defined Agents

Users can define their own agent configs and store them:

```python
POST /agent/create
{
  "name": "my_custom_agent",
  "config": {
    "identity": { /* user-defined */ },
    "context": { /* user-defined */ },
    "permissions": { /* user-defined */ },
    "cost_limits": { /* user-defined */ }
  }
}

# Later use it
POST /agent/my_custom_agent/intent
{
  "query": "help me with my task"
}
```

### Benefits of This Approach

1. **Unified Infrastructure**: All agents use the same MCP tools and registry
2. **Easy Customization**: Change agent behavior by updating config, not code
3. **Permission Safety**: Hard-enforced permissions prevent unauthorized access
4. **Cost Control**: Budget limits prevent runaway spending
5. **Consistency**: All agents follow the same execution model
6. **Scalability**: Add new agents by creating configs, not new code
7. **Auditability**: All agent actions are logged with their config context

### Comparison: Traditional vs Kiwi Approach

| Aspect | Traditional Approach | Kiwi Approach |
|--------|---------------------|---------------|
| **Agent Creation** | Write custom code for each agent | Configure one directive |
| **Infrastructure** | Separate systems per agent | Shared MCP infrastructure |
| **Permissions** | Implemented per agent | Centralized, configurable |
| **Cost Control** | Custom tracking per agent | Unified cost tracking |
| **Scaling** | Add code for each agent | Add config for each agent |
| **Consistency** | Varies by implementation | Uniform execution model |

---

## Implementation Plan

### Phase 1: Intent Directive Creation

1. **Create directive file**: `.ai/directives/core/intent_directive.md`

   - Define XML structure with inputs, process steps
   - Include intent parsing logic
   - Add registry search integration
   - Output structured tool call JSON

2. **Intent Parsing Logic**

   - Pattern matching for common verbs: search, find, load, run, execute, create, delete
   - Item type detection: directive, tool, knowledge, script
   - Parameter extraction: query terms, item names, action details
   - Confidence scoring based on clarity of intent

3. **Registry Integration**
   - Use search tool to find items when names are mentioned
   - Use knowledge base for intent pattern matching
   - Cache common intent patterns for faster resolution

### Phase 2: HTTP Server Wrapper

1. **Simple HTTP Server** (FastAPI or Flask)

   ```python
   # kiwi_mcp/api/http_server.py

   from fastapi import FastAPI, HTTPException
   from pydantic import BaseModel
   import asyncio
   from kiwi_mcp.server import KiwiMCP

   app = FastAPI()
   mcp = KiwiMCP()

   class IntentRequest(BaseModel):
       query: str
       project_path: str
       context: dict = None

   @app.post("/intent")
   async def handle_intent(request: IntentRequest):
       # Call intent_directive via MCP
       result = await mcp.tools["execute"].execute({
           "item_type": "directive",
           "action": "run",
           "item_id": "intent_directive",
           "parameters": {
               "user_input": request.query,
               "project_path": request.project_path,
               "context": request.context or {}
           },
           "project_path": request.project_path
       })

       # Parse directive output to get tool call
       tool_call = parse_directive_output(result)

       # Execute the tool call
       execution_result = await mcp.tools[tool_call["tool"]].execute(
           tool_call["arguments"]
       )

       return {
           "tool_call": tool_call,
           "result": execution_result
       }
   ```

2. **Tool Call Execution**
   - Parse directive output JSON
   - Execute tool call via MCP
   - Return results to client
   - Handle errors gracefully

### Phase 3: Threading Integration

1. **Leverage Threading Architecture**

   - Intent directive runs in its own thread context
   - Can spawn sub-threads for complex intent resolution
   - Thread registry tracks intent resolution patterns
   - Enables learning from usage patterns

2. **Pattern Learning**
   - Store successful intent → tool call mappings
   - Build knowledge base of common patterns
   - Improve intent resolution over time
   - Cache frequent mappings

---

## Intent Patterns

### Search Patterns

| User Input                      | Tool Call                                  |
| ------------------------------- | ------------------------------------------ |
| "search for directives about X" | `search(item_type="directive", query="X")` |
| "find tools that do Y"          | `search(item_type="tool", query="Y")`      |
| "look up knowledge on Z"        | `search(item_type="knowledge", query="Z")` |
| "show me scripts for W"         | `search(item_type="tool", query="W")`      |

### Load Patterns

| User Input          | Tool Call                                  |
| ------------------- | ------------------------------------------ |
| "load directive X"  | `load(item_type="directive", item_id="X")` |
| "get tool Y"        | `load(item_type="tool", item_id="Y")`      |
| "fetch knowledge Z" | `load(item_type="knowledge", item_id="Z")` |

### Execute Patterns

| User Input                        | Tool Call                                                                        |
| --------------------------------- | -------------------------------------------------------------------------------- |
| "run directive X"                 | `execute(item_type="directive", action="run", item_id="X")`                      |
| "execute tool Y with params Z"    | `execute(item_type="tool", action="run", item_id="Y", parameters=Z)`             |
| "create a new directive called X" | `execute(item_type="directive", action="create", item_id="X", parameters={...})` |

### Help Patterns

| User Input         | Tool Call         |
| ------------------ | ----------------- |
| "help with X"      | `help(topic="X")` |
| "how do I Y"       | `help(topic="Y")` |
| "show usage for Z" | `help(topic="Z")` |

---

## Example Flows

### Example 1: Simple Search

**User Request:**

```
"I want to find directives about email campaigns"
```

**Intent Directive Processing:**

1. Parse: verb="find", item_type="directive", query="email campaigns"
2. Search registry (optional): Look for exact matches
3. Build tool call:
   ```json
   {
     "tool": "search",
     "arguments": {
       "item_type": "directive",
       "query": "email campaigns",
       "source": "local",
       "project_path": "/home/user/project"
     }
   }
   ```

**HTTP Server Execution:**

- Calls `mcp.tools["search"].execute(arguments)`
- Returns search results to user

### Example 2: Execute with Parameters

**User Request:**

```
"Run the google_maps_scraper tool with query='tech companies' and limit=50"
```

**Intent Directive Processing:**

1. Parse: verb="run", item_type="tool", item_id="google_maps_scraper", parameters={"query": "tech companies", "limit": 50}
2. Search registry: Verify tool exists
3. Build tool call:
   ```json
   {
     "tool": "execute",
     "arguments": {
       "item_type": "tool",
       "action": "run",
       "item_id": "google_maps_scraper",
       "parameters": {
         "query": "tech companies",
         "limit": 50
       },
       "project_path": "/home/user/project"
     }
   }
   ```

**HTTP Server Execution:**

- Calls `mcp.tools["execute"].execute(arguments)`
- Tool executes and returns results

### Example 3: Ambiguous Intent

**User Request:**

```
"I need something to scrape leads from Google Maps"
```

**Intent Directive Processing:**

1. Parse: verb="need", intent="scrape leads from Google Maps", item_type=unknown
2. Search registry: Look for tools matching "scrape", "leads", "google maps"
3. Find: `google_maps_scraper` tool
4. Build tool call:
   ```json
   {
     "tool": "search",
     "arguments": {
       "item_type": "tool",
       "query": "scrape leads google maps",
       "source": "local",
       "project_path": "/home/user/project"
     },
     "confidence": 0.85,
     "reasoning": "Found potential match: google_maps_scraper. Suggesting search to let user choose."
   }
   ```

### Example 4: Agent-Specific Behavior

**Same User Request, Different Agents:**

**User Request:**
```
"Create a script to process user data"
```

**Coder Agent Response:**
```json
{
  "tool": "execute",
  "arguments": {
    "item_type": "tool",
    "action": "create",
    "item_id": "user_data_processor",
    "parameters": {
      "language": "python",
      "structure": "async/await pattern",
      "include_tests": true
    },
    "project_path": "/home/user/project"
  },
  "agent_identity": "Coder Agent",
  "response_style": "Technical, code-first approach with async patterns"
}
```

**Researcher Agent Response:**
```json
{
  "tool": "search",
  "arguments": {
    "item_type": "knowledge",
    "query": "user data processing best practices privacy regulations",
    "source": "local",
    "project_path": "/home/user/project"
  },
  "agent_identity": "Researcher Agent",
  "response_style": "Analytical approach - researching best practices before creating",
  "reasoning": "Before creating a script, I should research data processing best practices and privacy regulations to ensure compliance."
}
```

**Security Auditor Agent Response:**
```json
{
  "tool": "search",
  "arguments": {
    "item_type": "knowledge",
    "query": "user data security encryption PII handling",
    "source": "local",
    "project_path": "/home/user/project"
  },
  "agent_identity": "Security Auditor",
  "response_style": "Security-focused - ensuring data protection before processing",
  "reasoning": "User data processing requires security review. Checking for encryption requirements, PII handling guidelines, and compliance standards before proceeding."
}
```

**Key Differences:**
- **Coder Agent**: Jumps straight to implementation with technical patterns
- **Researcher Agent**: Researches best practices first
- **Security Auditor**: Focuses on security and compliance before action

---

## Benefits

1. **Single Entry Point**: One HTTP endpoint exposes entire MCP functionality
2. **Natural Language Access**: Users don't need to know tool syntax
3. **Registry Intelligence**: Leverages search and knowledge base
4. **Threading Power**: Can spawn sub-threads for complex resolution
5. **Learning**: Patterns improve over time through usage
6. **Extensibility**: Easy to add new intent patterns
7. **Agent Customization**: Create traditional agent approaches with identity, context, permissions, and cost controls through configuration
8. **Unified Infrastructure**: All agents share the same MCP tools and registry, reducing complexity
9. **Permission Safety**: Hard-enforced permissions prevent unauthorized access
10. **Cost Control**: Budget limits prevent runaway spending across all agents

---

## Technical Considerations

### Performance

- Intent directive should be fast (< 500ms for simple intents)
- Cache common intent patterns
- Use vector search for item matching
- Parallel search when multiple items mentioned

### Error Handling

- Return structured errors with suggestions
- Handle ambiguous intents gracefully
- Provide fallback options
- Log intent resolution for learning

### Security

- Validate project_path
- Check permissions before executing tool calls
- Sanitize user input
- Audit all intent resolutions

### Testing

- Unit tests for intent parsing
- Integration tests for HTTP server
- End-to-end tests for common flows
- Performance tests for latency

---

## Future Enhancements

1. **Multi-turn Conversations**: Track context across requests
2. **Intent Learning**: ML model trained on successful resolutions
3. **Confidence Thresholds**: Ask for clarification when confidence low
4. **Batch Processing**: Handle multiple intents in one request
5. **Streaming Responses**: Stream tool execution results
6. **WebSocket Support**: Real-time intent resolution

---

## Related Documents

- [THREAD_AND_STREAMING_ARCHITECTURE.md](../THREAD_AND_STREAMING_ARCHITECTURE.md) - Threading architecture
- [MCP_2_INTENT_DESIGN.md](../MCP_2_INTENT_DESIGN.md) - More complex intent system (future)
- [UNIFIED_TOOLS_ARCHITECTURE.md](../UNIFIED_TOOLS_ARCHITECTURE.md) - Tool architecture
- [SEARCH_USAGE.md](../SEARCH_USAGE.md) - Search tool usage

---

## Implementation Checklist

### Core Intent Directive
- [ ] Create `intent_directive.md` directive file
- [ ] Implement intent parsing logic
- [ ] Add registry search integration
- [ ] Build tool call generation
- [ ] Add agent_config parameter support
- [ ] Implement permission checking
- [ ] Implement cost limit validation
- [ ] Add agent identity injection

### HTTP Server Wrapper
- [ ] Create HTTP server wrapper
- [ ] Add `/intent` endpoint
- [ ] Add `/agent/{name}/intent` endpoint for agent-specific requests
- [ ] Add tool call execution
- [ ] Add error handling
- [ ] Document API endpoints

### Agent Configuration System
- [ ] Design agent config schema
- [ ] Implement config loading from registry
- [ ] Create default agent configs (coder, researcher, deployer, etc.)
- [ ] Add config validation
- [ ] Implement config storage/retrieval
- [ ] Create agent config management endpoints

### Integration & Testing
- [ ] Integrate with threading architecture
- [ ] Add cost tracking integration
- [ ] Add permission enforcement integration
- [ ] Write unit tests for intent parsing
- [ ] Write unit tests for agent config application
- [ ] Write integration tests for HTTP server
- [ ] Write end-to-end tests for agent workflows
- [ ] Performance tests for latency
- [ ] Create example clients (different agent types)
