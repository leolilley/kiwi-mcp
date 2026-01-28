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
load     Inspect things (read-only, for context)
execute  Run things (directives become instructions, tools become actions)
sign     Validate things
```

---

## Install

```bash
# pipx (recommended)
pipx install kiwi-mcp

# or curl
curl -sSL https://raw.githubusercontent.com/kiwi-mcp/kiwi-mcp/main/install.sh | bash

# or from source
git clone https://github.com/kiwi-mcp/kiwi-mcp && cd kiwi-mcp && pip install -e .
```

Add to your MCP client (Claude Desktop, Cursor, etc):

```json
{
  "mcpServers": {
    "kiwi": {
      "command": "kiwi-mcp",
      "args": ["serve"]
    }
  }
}
```

---

## Context Discipline

Here's what most people get wrong: they dump everything into the context window and pray.

Kiwi separates **inspection** from **execution**.

**load** (same source and destination, or no destination) returns the full content for inspection. The agent reads the directive, understands what it does, sees the inputs it needs.

```json
{
  "name": "email_outreach",
  "version": "2.1.0", 
  "description": "Cold email campaign with follow-up sequences",
  "inputs": [
    {"name": "prospect_list", "type": "string", "required": true},
    {"name": "template_id", "type": "string", "required": true}
  ],
  "process": { ... },
  "content": "..."
}
```

**execute** is when context gets lean. The agent isn't carrying around a massive prompt blob. It's following structured steps. Each step tells it exactly what to do. The directive *is* the control flow.

Same for knowledge. Load to read it. Execute to act on it. Your context window stays surgical because the agent operates on instructions, not raw dumps.

---

## Directives: Prompts That Don't Suck

A directive is a prompt you write once and reuse forever. Version-controlled. Signed. Validated before execution.

```xml
<directive name="code_review" version="1.0.0">
  <metadata>
    <description>Review code for security and performance issues</description>
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

## Tools: Scripts With Teeth

Tools are executable code with cryptographic guarantees.

```python
"""
__name__ = "google_maps_scraper"
__version__ = "2.1.0"
__executor__ = "subprocess"
__requires__ = ["fs.read", "process.exec"]
"""

def scrape(query: str, location: str) -> list:
    ...
```

Sign it:
```
sign(item_type="tool", item_id="google_maps_scraper", project_path="/project")
```

This computes a content hash, generates a lockfile pinning the execution chain, and writes the signature. If someone modifies the file, execution fails. If the chain changes, execution fails. If no lockfile exists, execution fails.

One command. Total integrity.

---

## The Registry: Solve Once, Solve Everywhere

Here's the thing about prompts: everyone's solving the same problems.

How do I get an agent to review code properly? How do I make it scrape without hallucinating selectors? How do I get consistent JSON output?

You solve it. You sign it. You publish it.

```
sign(item_type="directive", item_id="code_review", project_path="/project")
execute(item_type="directive", action="publish", item_id="code_review", version="1.0.0")
```

Now everyone can pull your solution:

```
search(item_type="directive", query="code review security", source="registry")
load(item_type="directive", item_id="code_review", source="registry", destination="project")
```

The directive lands in your `.ai/directives/` folder. Fully validated. Ready to customize or run as-is.

**This is the unlock.** Someone figures out the perfect prompt for extracting structured data from PDFs. They publish it. Now you have it. You didn't spend 3 hours prompt engineering. You ran one command.

Tools work the same way. Someone builds a scraper that actually works. They sign it, publish it, you pull it. Their lockfile becomes your lockfile. Their integrity guarantees become yours.

The registry isn't a nice-to-have. It's the entire point. Individual prompt crafting doesn't scale. A community library of battle-tested, cryptographically signed, version-controlled prompts? That scales.

---

## Safety Harness

Every directive can declare what it's allowed to do.

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

No surprises. No runaway costs. No "oops it deleted my database."

---

## Now It Gets Interesting

Everything above is table stakes. Here's where your brain starts melting.

---

### Spawn Agents Inside The MCP

Not "call an API." Not "send a webhook." Actually spawn a new agent thread with its own context, its own permissions, its own limits - running in parallel, reporting back when done.

```xml
<directive name="research_competitors" version="1.0.0">
  <metadata>
    <permissions>
      <execute resource="spawn" action="thread" />
    </permissions>
    <limits>
      <spawns>5</spawns>
      <spend currency="USD">2.00</spend>
    </limits>
  </metadata>

  <process>
    <step name="parallel_research">
      <action>
        For each competitor, spawn a child thread running the "deep_research" 
        directive. Each thread gets attenuated permissions - only what the 
        parent explicitly grants. Collect results when all complete.
      </action>
    </step>
  </process>
</directive>
```

Parent spawns 5 research agents. Each runs independently. Each has capped spend. Each can only access what parent grants. Results flow back when done.

**Orchestration through prompts.** No code. No infrastructure. Just XML.

---

### Permission Attenuation

Child threads can never escalate privileges.

Parent has: `[fs.read, fs.write, spawn.thread]`
Child declares it needs: `[fs.write, tool.bash]`
Child gets: `[fs.write]`

Intersection only. The child can't invent permissions the parent doesn't have. Delegation chains are cryptographically signed. You can trace exactly who granted what to whom.

---

### Recursive Orchestration

A directive can spawn children that spawn children. Each level attenuates further. Budget flows down and is tracked at every level.

```
research_competitors (budget: $2.00)
├── deep_research: CompanyA (budget: $0.40)
│   ├── scrape_website (budget: $0.10)
│   └── analyze_pricing (budget: $0.10)
├── deep_research: CompanyB (budget: $0.40)
│   ├── scrape_website (budget: $0.10)
│   └── analyze_pricing (budget: $0.10)
└── ... (3 more)
```

When a child hits its limit, it stops. Parent keeps going. No runaway recursion. No surprise bills.

---

### Hooks Are Just Directives

When a hook fires, it runs a directive. That directive can do anything - including spawning more agents, running tools, or firing its own hooks.

```xml
<hook>
  <when>event.name == "error" && event.code == "rate_limited"</when>
  <directive>backoff_retry</directive>
  <inputs>
    <wait_seconds>{{event.detail.retry_after}}</wait_seconds>
  </inputs>
</hook>
```

Self-healing systems. Defined in XML. Executed by agents.

---

## One Endpoint To Rule Them All

Here's where it gets stupid simple.

Wrap the MCP in an HTTP server. One endpoint. Plain text in.

```
POST /intent
Content-Type: text/plain

Find all Python files that import requests and check if they handle timeouts
```

The server runs a `tool_intent` directive that:
1. Parses your natural language request
2. Determines which tools/directives to invoke
3. Executes the plan
4. Returns structured results

Plain English command. Full system intelligence. One controlled interface.

No prompt engineering. No JSON gymnastics. No "act as a senior developer who..."

**The directive is the system prompt. The MCP is the API. The agent is the backend.**

---

## Project Structure

```
.ai/
├── directives/        # Workflow instructions
├── tools/             # Executable scripts  
├── knowledge/         # Structured information
├── lockfiles/         # Auto-generated chain locks
└── extractors/        # Custom metadata parsers

~/.ai/                 # User-level fallback for global items
```

---

## The Philosophy

Most AI tooling treats the model like a black box you throw text at and hope for the best.

We treat it like a computer that executes programs.

Directives are programs. Tools are functions. Knowledge is memory. The agent is the runtime.

You wouldn't write production code without types, tests, or version control. Why would you write production prompts that way?

---

## What You Can Build

- **Research pipelines** that spawn 20 agents to analyze different sources in parallel
- **Code review systems** that check security, performance, and style simultaneously  
- **Sales automation** that personalizes outreach based on scraped prospect data
- **Content factories** that research, outline, draft, edit, and publish autonomously
- **Data pipelines** that extract, transform, validate, and load without human intervention

The limit isn't the model. The limit is your imagination and your directive library.

---

## What's Next

- Visual directive editor
- Real-time execution streaming
- Cross-model orchestration (spawn Claude for analysis, GPT for generation)
- Marketplace for validated directive packages

---

## License

MIT

---

*"The best interface is no interface."*

*The second best is four tools and a library of prompts that actually work.*
