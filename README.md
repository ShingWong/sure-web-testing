# sure-web-testing

**Persistent, step-by-step interactive browser testing** with MCP server, CLI, and provider-agnostic vision analysis. Launch a browser once, then navigate, inspect, interact, and analyze — the browser stays alive between calls. Swap vision providers (Google, OpenAI, OpenRouter) with a single env var.

```bash
# Start the MCP server
awt-server

# Or use the interactive CLI
awt
```

### Why sure-web-testing?

| Problem | How sure-web-testing solves it |
|---------|------------------------------|
| **One-shot scripts lose state** | Persistent browser session — launch once, step through a workflow, inspect state between every action. |
| **No MCP-native browser tooling** | Full stdin/stdout JSON-RPC 2.0 MCP server. Any MCP-aware agent (OpenCode, Claude Code, Cursor) can drive the browser directly. |
| **Vision provider lock-in** | Swap from Gemini to GPT-4o to Qwen by changing `VISION_PROVIDER`. No code changes, no lock-in. |
| **Hard-to-debug test failures** | DOM inspection, console log capture, network request logging, highlighted screenshots — all available between steps. |
| **No video recording** | Built-in `start_video` / `stop_video` — record browser sessions for demo or replay. |

### How it compares

| | sure-web-testing | Playwright CLI | Selenium | Cypress |
|---|---|---|---|---|
| Persistent session | ✅ Step-by-step | ❌ Script-only | ❌ Script-only | ❌ Per-test |
| MCP server | ✅ Built-in | ❌ | ❌ | ❌ |
| Vision analysis | ✅ Provider-agnostic | ❌ | ❌ | ❌ |
| Video recording | ✅ Built-in | ❌ | ❌ | ✅ |
| Console/Network capture | ✅ Per-step | ❌ | ❌ | ✅ |
| Interactive CLI | ✅ REPL | ❌ | ❌ | ❌ |
| Install size | ~40 MB (Playwright) | ~40 MB | ~200 MB | ~150 MB |
| Framework lock-in | Zero — Python + MCP | Tight — JS only | Tight — Java/C# | Tight — JS/TS |

## Installation

```bash
pip install sure-web-testing
playwright install chromium
```

Vision extras (install the providers you need):

```bash
pip install "sure-web-testing[google-vision]"     # Gemini (free tier)
pip install "sure-web-testing[openai-vision]"      # GPT-4o
pip install "sure-web-testing[openrouter-vision]"  # Qwen, GLM, any OpenRouter model
pip install "sure-web-testing[all-vision]"         # All providers
```

## Provider Setup

**MCP Server** — no API keys needed for browser control:

```bash
awt-server
```

**Vision analysis** — set provider and API key:

```bash
export VISION_PROVIDER=google                  # or openai, openrouter
export GOOGLE_API_KEY=AIza...                  # or OPENAI_API_KEY, OPENROUTER_API_KEY
```

Full config options in [`docs/vision-config.md`](docs/vision-config.md).

## Architecture

```
Agent/CLI
  │
  ▼  stdin/stdout JSON-RPC 2.0
  │
┌──────────────────────────────────────────────┐
│  MCP Server                                  │
│  ┌──────────────┐   ┌───────────────────┐   │
│  │  ToolRegistry │   │  Vision Analyzer  │   │
│  │  (30+ tools)  │   │  Google / OpenAI  │   │
│  └──────┬───────┘   │  OpenRouter       │   │
│         │           └────────┬──────────┘   │
│  ┌──────▼────────────────────▼──────┐       │
│  │       BrowserManager             │       │
│  │       (Playwright)               │       │
│  └──────────────┬───────────────────┘       │
└─────────────────┼────────────────────────────┘
                  │
                  ▼
            Chromium Browser
```

## Tool Reference

### Session Lifecycle

| Tool | Purpose |
|------|---------|
| `launch` | Start browser session (headless, viewport, video) |
| `close` | Close browser and cleanup |
| `get_info` | Current URL, title, load state |

### Navigation

| Tool | Purpose |
|------|---------|
| `goto` | Navigate to URL |
| `reload` | Reload current page |
| `go_back` / `go_forward` | History navigation |

### DOM Inspection

| Tool | Purpose |
|------|---------|
| `get_dom` | Full page HTML or filtered by selector |
| `query_elements` | List matching elements with tag, text, rect |
| `get_text` / `get_attribute` | Element content |

### Interaction

| Tool | Purpose |
|------|---------|
| `click` | Click element |
| `fill` | Fill input field |
| `press` | Press key |
| `select_option` | Select dropdown value |
| `hover` | Hover over element |
| `evaluate` | Execute JavaScript (sandboxed) |
| `wait_for` | Wait for element or load state |

### Visual Capture

| Tool | Purpose |
|------|---------|
| `screenshot` | Screenshot with optional element highlight |
| `highlight_element` | Orange highlight over element |
| `clear_highlights` | Remove all highlights |
| `start_video` / `stop_video` | Record browser session video |

### Console & Network

| Tool | Purpose |
|------|---------|
| `get_console_logs` | Browser console messages |
| `get_network_requests` | Network request log |

### Vision Analysis

| Tool | Purpose |
|------|---------|
| `analyze_screenshot` | Take screenshot + analyze with vision AI in one call |
| `analyze_image` | Analyze an existing image file with vision AI |

Vision is provider-agnostic. Configure with `VISION_PROVIDER`:

| Provider | Default Model | Cost/1K images | Env Var |
|----------|--------------|----------------|---------|
| `google` | `gemini-2.5-flash-lite` | Free tier | `GOOGLE_API_KEY` |
| `openai` | `gpt-4o` | ~$2.50 | `OPENAI_API_KEY` |
| `openrouter` | `qwen/qwen3.6-plus` | ~$0.05 | `OPENROUTER_API_KEY` |

## Typical Workflow

```
launch(headless=false)
goto("http://localhost:6080")
fill("input[name=email]", "user@example.com")
fill("input[name=password]", "mypassword")
click("button[type=submit]")
wait_for("text=Dashboard")
screenshot(highlight="h1")
get_console_logs()
close()
```

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `VISION_PROVIDER` | `google` | Vision AI provider |
| `VISION_API_KEY` | — | API key (falls back to provider-specific var) |
| `VISION_MODEL` | provider default | Model override |
| `VISION_BASE_URL` | — | Base URL override (for OpenAI-compatible providers) |
| `GOOGLE_API_KEY` | — | Google AI API key |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |

## MCP Integration

AI coding assistants (OpenCode, Claude Code, Cursor) can connect to the MCP server:

```json
{
  "mcpServers": {
    "sure-web-testing": {
      "command": "awt-server"
    }
  }
}
```

Once connected, agents can launch a browser, navigate, inspect, and interact step-by-step — the browser stays alive between tool calls.

### OpenCode Workflow Example

Configure in `opencode.json`:

```json
{
  "mcpServers": {
    "sure-web-testing": {
      "command": "awt-server"
    }
  }
}
```

Then prompt OpenCode with a step-by-step browser task:

```
Using sure-web-testing, debug the login flow at http://localhost:3000.
Start recording video, then step through each action — inspect state
between every step.

1. Launch a headed browser with video recording enabled
2. Go to http://localhost:3000/login
3. Get the DOM and verify the form elements exist
4. Highlight the email input and take a screenshot to confirm selector
5. Fill in email "test@example.com"
6. Fill in password "wrong"
7. Click the submit button
8. Wait for the error message to appear
9. Highlight the error element and screenshot it
10. Get console logs to check for JS errors
11. Get network requests to verify the API call and its response
12. Stop the video and save the recording
13. Close the browser
```

OpenCode executes each step via the MCP tools, pausing between every action so you can inspect DOM, console, network, and screenshots before proceeding. This multi-step debugging loop — act, inspect, decide, act — is the core workflow.

### What OpenCode should know

| File | What it tells the agent |
|------|------------------------|
| `src/browser.py` | `BrowserManager` class — session lifecycle, navigation, DOM, interaction, console/network capture, video recording, element highlighting |
| `src/tools.py` | `ToolRegistry` + `build_registry` — all 30+ MCP tools with signatures |
| `src/vision.py` | `VisionProvider` hierarchy — Google, OpenAI, OpenRouter vision analysis |
| `src/server.py` | `MCPServer` — JSON-RPC 2.0 protocol over stdin/stdout |
| `src/cli.py` | Interactive REPL CLI |
| `docs/vision-config.md` | Vision provider configuration and model pricing |

### Example: AI-driven multi-step debugging workflow

1. Read `src/tools.py` → understand available browser tools
2. Read `src/browser.py` → understand session model (launch once, step sequentially)
3. Call `launch` with `record_video=true` → start browser with video capture
4. Call `goto` → navigate to target page
5. Call `query_elements` or `get_dom` → verify page structure
6. Call `highlight_element` + `screenshot` → visually confirm target components
7. Call `fill`, `click`, `select_option` → interact with page
8. Call `get_console_logs` → check for JS errors after each interaction
9. Call `get_network_requests` → verify API calls and responses
10. Call `screenshot` with `highlight` → capture visual evidence at key states
11. Call `analyze_screenshot` → let vision AI inspect the page visually
12. Call `stop_video` → save full session recording
13. Call `close` → cleanup

## Development

```bash
git clone git@github.com:ShingWong/sure-web-testing.git
cd sure-web-testing
pip install -e ".[dev]"
playwright install chromium
pytest                              # 41 tests
ruff check src/ tests/
mypy src/
```
