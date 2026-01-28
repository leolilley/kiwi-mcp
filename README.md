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
load     Inspect things (full content for reading)
execute  Run things (agent follows structured steps)
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

Add to your MCP client (Claude Desktop, Cursor, Amp, Windsurf, Gemini - anything that speaks MCP):

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

## Level 1: The Four Tools

This is where everyone starts. Learn the primitives.

### Directives

A directive is a prompt you write once and reuse forever. Version-controlled. Signed. Validated.

```xml
<directive name="code_review" version="1.0.0">
  <metadata>
    <description>Review code for security issues</description>
  </metadata>

  <inputs>
    <input name="file_path" type="string" required="true">File to review</input>
  </inputs>

  <process>
    <step name="read">
      <action>Read the file at {{file_path}}</action>
    </step>
    <step name="analyze">
      <action>Check for: SQL injection, XSS, hardcoded secrets</action>
    </step>
  </process>
</directive>
```

The agent reads this. The agent follows it. Every time. No drift. No hallucination.

### Tools

Executable scripts with cryptographic guarantees.

```python
"""
__name__ = "scraper"
__version__ = "1.0.0"
__executor__ = "subprocess"
"""

def scrape(url: str) -> dict:
    ...
```

Sign it once. If the file changes, execution fails. If the chain changes, execution fails. Total integrity.

### Load vs Execute

**load** returns full content for inspection. The agent reads, understands, decides.

**execute** is when context gets lean. The agent follows structured steps. The directive *is* the control flow - not a blob dumped into context.

### The Registry: Solve Once, Solve Everywhere

Here's the thing about prompts: everyone's solving the same problems.

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

Someone figures out the perfect prompt for extracting structured data from PDFs. They publish it. You pull it. No 3-hour prompt engineering session. One command.

The registry isn't a nice-to-have. Individual prompt crafting doesn't scale. A community library of battle-tested, cryptographically signed prompts? That scales.

---

## Level 2: Threads Inside The MCP

Everything above works with any external harness - Claude, Cursor, whatever. The MCP just serves tools.

Now it gets interesting. What if the MCP *is* the harness?

### Spawning Agent Threads

The MCP can spawn its own LLM threads. Not "call an API." Actually create a new agent with its own context, its own conversation, its own execution.

```xml
<directive name="research_topic" version="1.0.0">
  <metadata>
    <permissions>
      <execute resource="spawn" action="thread" />
    </permissions>
  </metadata>

  <process>
    <step name="spawn_researcher">
      <action>
        Spawn a child thread running the "deep_research" directive.
        Wait for completion. Collect results.
      </action>
    </step>
  </process>
</directive>
```

The parent directive spawns a child agent. The child runs independently. When it finishes, results flow back.

### Why This Matters

External harnesses have no control once the agent starts running. You hope it follows instructions. You pray it doesn't go rogue.

**Inside the MCP, you have 100% control.**

The MCP controls what gets spawned, what permissions it has, how long it runs, how much it spends. The agent can't escape. It can't escalate. It operates within bounds you define.

### Permissions

Now permissions make sense. They're not for the external harness - they're for threads spawned *inside* the MCP.

```xml
<permissions>
  <read resource="filesystem" path="src/**" />
  <execute resource="tool" id="linter" />
  <execute resource="spawn" action="thread" />
</permissions>
```

A child thread can only do what the parent explicitly grants. And children can spawn grandchildren - each level attenuates further.

Parent has: `[fs.read, fs.write, spawn.thread]`  
Child declares: `[fs.write, tool.bash]`  
Child gets: `[fs.write]`

Intersection only. No escalation. Ever.

### Limits

Resource caps that actually work.

```xml
<limits>
  <tokens>50000</tokens>
  <turns>10</turns>
  <spawns>5</spawns>
  <spend currency="USD">0.50</spend>
</limits>
```

When a child hits its limit, it stops. Parent keeps going. No runaway costs. No infinite recursion.

### Hooks

Checkpoints where you can intervene.

```xml
<hooks>
  <hook>
    <when>cost.spend > limits.spend * 0.8</when>
    <directive>budget_warning</directive>
  </hook>
  <hook>
    <when>event.name == "error"</when>
    <directive>error_handler</directive>
  </hook>
</hooks>
```

When a hook fires, it runs a directive. That directive can do anything - spawn more agents, run tools, fire its own hooks. Self-healing systems defined in XML.

---

## Level 3: Orchestration

Now you're cooking.

### Parallel Execution

Spawn 5 research agents simultaneously. Each investigates a different competitor. Results merge when all complete.

```
research_competitors (budget: $2.00)
├── deep_research: CompanyA (budget: $0.40)
├── deep_research: CompanyB (budget: $0.40)
├── deep_research: CompanyC (budget: $0.40)
├── deep_research: CompanyD (budget: $0.40)
└── deep_research: CompanyE (budget: $0.40)
```

### Recursive Delegation

A directive spawns children that spawn grandchildren. Budget flows down. Permissions attenuate at every level. The tree can go as deep as you want - each node is sandboxed.

### Tight Context

Parent spawns a child with a focused task. Child completes with minimal context. Results flow back as structured data. Parent's context stays clean.

This is how you build complex systems without context explosion.

---

## Level 4: Autonomous Systems

Multi-agent collaboration. State branching for exploration. Self-evolving directive libraries. Emergent specialization.

This is where you stop building tools and start building organisms.

We're not documenting this level yet. You'll figure it out.

---

## One Endpoint To Rule Them All

Wrap the MCP in HTTP. One endpoint. Plain text in.

```
POST /intent
Content-Type: text/plain

Find all Python files that import requests and check if they handle timeouts
```

A `tool_intent` directive parses your request, determines the plan, executes it, returns results.

Plain English in. Structured results out. No prompt engineering. No JSON gymnastics.

**The directive is the system prompt. The MCP is the API. The agent is the backend.**

Anyone who can make an HTTP request gets 100% of the system's intelligence through one controlled interface.

---

## The Universal Agent File

Forget "You are a helpful assistant." Forget "Act as a senior developer." Forget role-playing prompts entirely.

Drop one file in your project: `AGENTS.md`

```markdown
## COMMAND DISPATCH TABLE

| User Says            | Run Directive      | With Inputs              |
| -------------------- | ------------------ | ------------------------ |
| `create tool X`      | `create_tool`      | `tool_name=X`            |
| `create directive X` | `create_directive` | `directive_name=X`       |
| `search tools X`     | `search_tools`     | `query=X, source=local`  |
| `run X`              | `run_directive`    | `directive_name=X`       |
| `bootstrap X`        | `bootstrap`        | `project_type=X`         |
| `research X`         | `research_topic`   | `topic=X`                |
| `debug X`            | `debug_issue`      | `issue_description=X`    |
```

The agent reads this. Now it knows: when a user says "create tool scraper", execute `create_tool` with `tool_name=scraper`.

No ambiguity. No interpretation. No "I think you meant..."

**This is the system prompt.** Not a paragraph of vibes. A dispatch table that maps intent to action.

The file also contains a full directive that teaches the agent the Kiwi workflow:

1. Understand the task
2. Search for existing directives that match
3. Load and execute if found
4. If not found, search tools and knowledge, orchestrate manually
5. Store learnings for next time

One file. Universal behavior. Works with Claude, Cursor, Amp, Gemini - any agent that reads project files gets the same capabilities.

Compare this to:

```
You are a helpful AI assistant specializing in code review. 
When asked to review code, you should look for security issues,
performance problems, and style violations. Be thorough but concise.
If you're unsure about something, ask for clarification.
```

That's a prayer. AGENTS.md is a program.

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

- Research pipelines that spawn 20 agents to analyze sources in parallel
- Code review systems that check security, performance, and style simultaneously  
- Sales automation that personalizes outreach based on scraped prospect data
- Content factories that research, outline, draft, edit, and publish autonomously
- Data pipelines that extract, transform, validate, and load without intervention

The limit isn't the model. The limit is your directive library.

---

## License

MIT

---

*"The best interface is no interface."*

*The second best is four tools and a library of prompts that actually work.*
