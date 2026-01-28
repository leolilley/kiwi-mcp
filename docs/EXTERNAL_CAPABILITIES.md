# External Capabilities

**Date:** 2026-01-28  
**Status:** Planning  
**Purpose:** Document how Kiwi MCP agents interact with the outside world

---

## Overview

Kiwi MCP agents aren't limited to local files - they can reach out and interact with:
- **Web browsing** - Navigate, scrape, interact with websites
- **HTTP APIs** - Call any REST/GraphQL endpoint
- **External MCPs** - Leverage other MCP servers (Supabase, etc.)
- **App automation** - Control desktop/mobile apps
- **Messaging platforms** - Discord, Slack, Telegram, WhatsApp
- **Cloud services** - AWS, GCP, databases, storage

---

## 1. Web Browsing & Automation

### Current Capabilities

Agents can browse the web through:

**Built-in Tools (via host agent like Amp):**
- `web_search` - Search the web
- `read_web_page` - Fetch and parse URL content

**Custom Tools (in `.ai/tools/`):**
```python
# .ai/tools/browser_control.py
"""
Browser automation using Playwright/Selenium.

Features:
- Navigate to URLs
- Click elements, fill forms
- Take screenshots
- Extract data
- Handle authentication
"""

async def browse(url: str, actions: list[dict]) -> dict:
    """Execute browser actions on a page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        
        results = []
        for action in actions:
            if action["type"] == "click":
                await page.click(action["selector"])
            elif action["type"] == "fill":
                await page.fill(action["selector"], action["value"])
            elif action["type"] == "screenshot":
                await page.screenshot(path=action["path"])
            elif action["type"] == "extract":
                results.append(await page.query_selector(action["selector"]).text_content())
        
        return {"results": results}
```

### Use Cases

| Use Case | Implementation |
|----------|----------------|
| **Web scraping** | Fetch page → parse HTML → extract data |
| **Form automation** | Navigate → fill fields → submit |
| **Screenshot capture** | Load page → render → save image |
| **Content monitoring** | Periodic fetch → diff → alert on change |
| **Authentication flows** | Login → capture session → reuse |

### Directives for Web Browsing

```xml
<directive name="web_research">
  <process>
    <step name="search">
      Use web_search to find relevant pages
    </step>
    <step name="read_pages">
      Use read_web_page on top results (parallel)
    </step>
    <step name="extract">
      Parse and extract relevant information
    </step>
    <step name="synthesize">
      Combine findings into summary
    </step>
  </process>
</directive>
```

---

## 2. HTTP API Integration

### Pattern: API Client Tools

```python
# .ai/tools/api_client.py
"""
Generic HTTP API client for any REST/GraphQL endpoint.
"""

import httpx

async def call_api(
    method: str,
    url: str,
    headers: dict = None,
    body: dict = None,
    auth: dict = None
) -> dict:
    """Make HTTP request to any API."""
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=body,
            auth=(auth["user"], auth["pass"]) if auth else None
        )
        return {
            "status": response.status_code,
            "body": response.json() if response.headers.get("content-type") == "application/json" else response.text
        }
```

### Common API Integrations

| Service | Tool | Capabilities |
|---------|------|--------------|
| **OpenAI** | `llm_client.py` | Chat completions, embeddings |
| **GitHub** | `github_client.py` | Repos, issues, PRs, actions |
| **Slack** | `slack_client.py` | Messages, channels, users |
| **Discord** | `discord_client.py` | Messages, guilds, roles |
| **Stripe** | `stripe_client.py` | Payments, subscriptions |
| **Twilio** | `twilio_client.py` | SMS, voice, WhatsApp |
| **SendGrid** | `email_client.py` | Email sending |
| **Google Maps** | `maps_scraper.py` | Location data, leads |

### Credential Management

See: [AGENT_CREDENTIAL_SECURITY.md](new%20auth/AGENT_CREDENTIAL_SECURITY.md)

```yaml
# .ai/config/credentials.yaml (encrypted)
apis:
  openai:
    api_key: ${OPENAI_API_KEY}
  github:
    token: ${GITHUB_TOKEN}
  slack:
    bot_token: ${SLACK_BOT_TOKEN}
```

---

## 3. External MCP Integration

### Using Other MCPs

Kiwi can call tools from other MCP servers:

```xml
<directive name="database_migration">
  <process>
    <step name="apply_migration">
      <tool_call>
        <mcp>supabase</mcp>
        <tool>apply_migration</tool>
        <params>
          <project_id>abc123</project_id>
          <query>CREATE TABLE users (...)</query>
        </params>
      </tool_call>
    </step>
  </process>
</directive>
```

### Available External MCPs

| MCP | Capabilities |
|-----|--------------|
| **Supabase** | Database, auth, storage, edge functions |
| **Filesystem** | Read/write files (sandboxed) |
| **Git** | Commits, branches, diffs |
| **Docker** | Container management |
| **Kubernetes** | Cluster operations |
| **AWS** | Cloud services |

### MCP Discovery

```python
# List available MCPs
available_mcps = await mcp_discovery.list_servers()

# Get MCP capabilities
supabase_tools = await mcp_discovery.get_tools("supabase")
```

---

## 4. App Automation

### Desktop Automation

```python
# .ai/tools/desktop_control.py
"""
Desktop automation using pyautogui or similar.
"""

import pyautogui

def click_at(x: int, y: int) -> None:
    """Click at screen coordinates."""
    pyautogui.click(x, y)

def type_text(text: str) -> None:
    """Type text via keyboard."""
    pyautogui.typewrite(text)

def screenshot() -> str:
    """Capture screen and save."""
    path = "/tmp/screenshot.png"
    pyautogui.screenshot(path)
    return path

def find_and_click(image_path: str) -> bool:
    """Find image on screen and click it."""
    location = pyautogui.locateOnScreen(image_path)
    if location:
        pyautogui.click(location)
        return True
    return False
```

### Mobile Automation

```python
# .ai/tools/mobile_control.py
"""
Mobile automation using Appium.
"""

from appium import webdriver

async def mobile_action(
    device_id: str,
    app_package: str,
    actions: list[dict]
) -> dict:
    """Execute actions on mobile device."""
    driver = webdriver.Remote(
        command_executor='http://localhost:4723/wd/hub',
        desired_capabilities={
            'platformName': 'Android',
            'deviceName': device_id,
            'appPackage': app_package
        }
    )
    
    results = []
    for action in actions:
        if action["type"] == "tap":
            driver.find_element_by_id(action["id"]).click()
        elif action["type"] == "input":
            driver.find_element_by_id(action["id"]).send_keys(action["text"])
        # ... more actions
    
    driver.quit()
    return {"results": results}
```

---

## 5. Messaging Platforms

### Pattern: Channel Tools

Each messaging platform gets a channel tool:

```
.ai/tools/
├── channel_discord.py
├── channel_slack.py
├── channel_telegram.py
├── channel_whatsapp.py
└── channel_email.py
```

### Discord Integration

```python
# .ai/tools/channel_discord.py

import discord

class DiscordChannel:
    def __init__(self, bot_token: str):
        self.client = discord.Client()
        self.token = bot_token
    
    async def send_message(self, channel_id: int, content: str) -> dict:
        """Send message to Discord channel."""
        channel = self.client.get_channel(channel_id)
        message = await channel.send(content)
        return {"message_id": message.id}
    
    async def listen(self, callback: callable) -> None:
        """Listen for incoming messages."""
        @self.client.event
        async def on_message(message):
            if message.author != self.client.user:
                await callback(message)
        
        await self.client.start(self.token)
```

### Multi-Channel Routing

```xml
<directive name="multi_channel_handler">
  <inputs>
    <input name="message" />
    <input name="channel_type" />  <!-- discord, slack, telegram -->
    <input name="channel_id" />
  </inputs>
  <process>
    <step name="process">
      Process message with LLM
    </step>
    <step name="respond">
      Route response to correct channel tool based on channel_type
    </step>
  </process>
</directive>
```

---

## 6. Cloud Services

### AWS Integration

```python
# .ai/tools/aws_client.py

import boto3

async def s3_upload(bucket: str, key: str, data: bytes) -> str:
    """Upload to S3."""
    s3 = boto3.client('s3')
    s3.put_object(Bucket=bucket, Key=key, Body=data)
    return f"s3://{bucket}/{key}"

async def lambda_invoke(function_name: str, payload: dict) -> dict:
    """Invoke Lambda function."""
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
        FunctionName=function_name,
        Payload=json.dumps(payload)
    )
    return json.loads(response['Payload'].read())

async def sqs_send(queue_url: str, message: dict) -> str:
    """Send message to SQS queue."""
    sqs = boto3.client('sqs')
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )
    return response['MessageId']
```

### Database Connections

```python
# .ai/tools/database_client.py

import asyncpg
import motor.motor_asyncio

async def postgres_query(dsn: str, query: str, params: list = None) -> list:
    """Execute PostgreSQL query."""
    conn = await asyncpg.connect(dsn)
    rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
    await conn.close()
    return [dict(row) for row in rows]

async def mongodb_query(uri: str, db: str, collection: str, query: dict) -> list:
    """Execute MongoDB query."""
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    coll = client[db][collection]
    cursor = coll.find(query)
    return await cursor.to_list(length=100)
```

---

## 7. Security Considerations

### Permission Model

External capabilities require explicit permissions:

```xml
<permissions>
  <!-- Web access -->
  <execute resource="http" action="GET" domains="*.wikipedia.org" />
  <execute resource="http" action="*" domains="api.openai.com" />
  
  <!-- Browser automation -->
  <execute resource="browser" action="navigate" />
  <execute resource="browser" action="screenshot" />
  
  <!-- External MCPs -->
  <execute resource="mcp:supabase" action="*" />
  
  <!-- Messaging -->
  <execute resource="channel:discord" action="send" />
  <execute resource="channel:slack" action="*" />
</permissions>
```

### Rate Limiting

```yaml
# .ai/config/rate_limits.yaml
external:
  http_requests:
    per_minute: 60
    per_hour: 1000
  browser_sessions:
    concurrent: 3
  api_calls:
    openai: 100/minute
    github: 5000/hour
```

### Audit Logging

All external interactions logged:

```json
{
  "timestamp": "2026-01-28T10:30:00Z",
  "agent_id": "agent_001",
  "action": "http_request",
  "target": "https://api.github.com/repos/owner/repo",
  "method": "GET",
  "status": 200,
  "duration_ms": 150
}
```

---

## 8. Demo Ideas

### Wiki Race (Game 4.5)

Uses HTTP calls recursively - each agent fetches a Wikipedia page, picks a link, spawns next agent.

### Web Monitoring

```
Agent spawns → fetches page → extracts content → compares to last version
            → if changed: alert via Slack
            → spawns delayed check (recursive)
```

### API Orchestration

```
User: "Get my GitHub issues and post summary to Slack"

Agent:
  → call_api(GET, github.com/repos/me/repo/issues)
  → process issues with LLM
  → call_api(POST, slack.com/messages, summary)
```

### Multi-Platform Bot

```
Discord message arrives
  → channel_discord receives
  → directive processes with LLM
  → if needs data: call external APIs
  → channel_discord sends response
  → optionally: cross-post to Slack
```

---

## Implementation Status

| Capability | Status | Notes |
|------------|--------|-------|
| web_search | ✅ Via host | Built into Amp |
| read_web_page | ✅ Via host | Built into Amp |
| HTTP client | 🔧 Tool needed | Create api_client.py |
| Browser automation | 🔧 Tool needed | Playwright wrapper |
| Discord | 🔧 Tool needed | channel_discord.py |
| Slack | 🔧 Tool needed | channel_slack.py |
| External MCPs | ✅ Works | Supabase, etc. via host |
| Database clients | 🔧 Tool needed | postgres/mongo wrappers |
| AWS services | 🔧 Tool needed | boto3 wrapper |

---

## Next Steps

1. **Create core HTTP client tool** - Generic API caller
2. **Create browser automation tool** - Playwright wrapper
3. **Create channel tools** - Discord, Slack, Telegram
4. **Document credential management** - Secure API key handling
5. **Add demo directives** - Web scraping, API orchestration examples

---

_Last Updated: 2026-01-28_
