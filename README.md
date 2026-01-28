# Kiwi MCP

**Programmable AI agents through structured prompts.**

While everyone else is building chatbots, you'll be building systems.

---

## The Problem

Your AI assistant is only as good as its context window. Feed it garbage, get garbage back. Feed it the same instructions 47 different ways across 47 different sessions, get 47 inconsistent results.

The industry's solution? More parameters. Bigger models. Longer context windows.

Our solution? **Structure.**

---

## What This Is

Kiwi MCP is a Model Context Protocol server that gives your AI agent access to:

- **Directives** - Reusable workflow instructions that tell the agent exactly how to accomplish tasks
- **Tools** - Executable scripts with cryptographic signatures and chain validation
- **Knowledge** - Structured information the agent can reference

Four tools. That's it.

```
search   Find things
load     Get things
execute  Run things
sign     Validate things
```

The magic isn't in the tools. It's in what you put in them.

---

## Directives: Prompts That Don't Suck

A directive is a prompt you write once and reuse forever. It's version-controlled, signed, and validated before execution.

```xml
<directive name="code_review" version="1.0.0">
  <metadata>
    <description>Review code for security and performance issues</description>
    <category>engineering</category>
    <model tier="reasoning">Deep analysis required</model>
  </metadata>

  <inputs>
    <input name="file_path" type="string" required="true">File to review</input>
  </inputs>

  <process>
    <step name="read">
      <action>Read the file at {{file_path}}</action>
    </step>
    <step name="analyze">
      <action>Check for: SQL injection, XSS, hardcoded secrets, N+1 queries</action>
    </step>
    <step name="report">
      <action>Return findings with line numbers and severity</action>
    </step>
  </process>
</directive>
```

The agent reads this. The agent follows it. Every time. No drift. No hallucination. No "I interpreted your request as..."

---

## Safety Harness

Every directive can declare:

**Permissions** - What resources it can access
```xml
<permissions>
  <read resource="filesystem" path="src/**" />
  <execute resource="tool" id="linter" />
</permissions>
```

**Limits** - How much it can spend
```xml
<limits>
  <tokens>50000</tokens>
  <turns>10</turns>
  <spend currency="USD">0.50</spend>
</limits>
```

**Hooks** - What happens at checkpoints
```xml
<hooks>
  <hook>
    <when>cost.spend > limits.spend * 0.8</when>
    <directive>budget_warning</directive>
  </hook>
</hooks>
```

Child threads inherit attenuated permissions. No escalation. Ever.

---

## Tools: Scripts With Teeth

Tools are executable code. Python, Bash, whatever. But they're not just files sitting in a folder.

Every tool has:

- **Metadata** extracted from docstrings and decorators
- **Cryptographic signature** computed on content hash
- **Lockfile** pinning the exact execution chain
- **Chain validation** ensuring dependencies haven't been tampered with

```python
"""
Lead scraper for Google Maps.

__name__ = "google_maps_scraper"
__version__ = "2.1.0"
__executor__ = "subprocess"
__category__ = "scraping"
__requires__ = ["fs.read", "process.exec"]
"""

def scrape(query: str, location: str) -> list:
    ...
```

Sign it once. Execute it anywhere. If someone modifies the file, execution fails. If the chain changes, execution fails. If no lockfile exists, execution fails.

```
sign(item_type="tool", item_id="google_maps_scraper", project_path="/project")
```

This generates the lockfile automatically. No extra steps.

---

## Knowledge: Your Agent's Memory

Zettelkasten-style entries that your agent can search and reference.

```markdown
---
id: email-deliverability-001
title: Email Deliverability Best Practices  
entry_type: reference
tags: [email, deliverability, smtp]
---

SPF, DKIM, and DMARC are table stakes. Here's what actually matters...
```

Keyword search with BM25 scoring. Optional vector embeddings if you want semantic search. Zero external dependencies for basic usage.

---

## Installation

```bash
git clone https://github.com/your-org/kiwi-mcp
cd kiwi-mcp
pip install -e ".[dev]"
```

Requirements: Python 3.11+

---

## Usage

### With Claude Desktop / Cursor / Any MCP Client

Add to your MCP config:

```json
{
  "mcpServers": {
    "kiwi": {
      "command": "python",
      "args": ["-m", "kiwi_mcp.server"],
      "env": {
        "KIWI_PROJECT_PATH": "/path/to/your/project"
      }
    }
  }
}
```

### The Four Tools

**search** - Find directives, tools, or knowledge

```json
{
  "item_type": "directive",
  "query": "code review security",
  "project_path": "/project"
}
```

**load** - Inspect or copy items between locations

```json
{
  "item_type": "tool",
  "item_id": "linter",
  "source": "user",
  "destination": "project",
  "project_path": "/project"
}
```

**execute** - Run a directive or tool

```json
{
  "item_type": "directive",
  "item_id": "code_review",
  "parameters": {"file_path": "src/auth.py"},
  "project_path": "/project"
}
```

**sign** - Validate and sign an item

```json
{
  "item_type": "tool",
  "item_id": "scraper",
  "project_path": "/project"
}
```

---

## Project Structure

```
.ai/
├── directives/        # Your workflow instructions
│   ├── engineering/
│   └── research/
├── tools/             # Your executable scripts
│   ├── scraping/
│   └── analysis/
├── knowledge/         # Your structured information
├── lockfiles/         # Auto-generated chain locks
└── extractors/        # Custom metadata parsers
```

User-level fallback at `~/.ai/` for global items.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  MCP Server                       │
├────────────┬────────────┬────────────┬───────────┤
│   search   │    load    │  execute   │   sign    │
└─────┬──────┴─────┬──────┴─────┬──────┴─────┬─────┘
      │            │            │            │
      └────────────┴────────────┴────────────┘
                       │
              TypeHandlerRegistry
      ┌────────────────┼────────────────┐
      │                │                │
  Directive        Tool           Knowledge
  Handler         Handler          Handler
      │                │                │
      └────────────────┴────────────────┘
                       │
              ┌────────┴────────┐
              │                 │
          Local FS          Registry
         (.ai/)           (Supabase)
```

**Primitives layer**: Integrity verification, chain validation, lockfile enforcement

**Runtime layer**: Auth tokens, environment resolution, subprocess execution

**Safety layer**: Capability tokens, permission attenuation, limit tracking

---

## The Philosophy

Most AI tooling treats the model like a black box you throw text at and hope for the best.

We treat it like a computer that executes programs.

Directives are programs. Tools are functions. Knowledge is memory. The agent is the runtime.

You wouldn't write production code without types, tests, or version control. Why would you write production prompts that way?

---

## What's Next

- Thread spawning with isolated capability tokens
- Multi-agent orchestration through hook chains  
- Registry for sharing validated directives and tools
- Visual directive editor

---

## License

MIT

---

*"The best interface is no interface."*

*The second best interface is four functions that do exactly what they say.*
