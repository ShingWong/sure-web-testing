---
name: agentic-web-testing
description: Use when testing web applications interactively with step-by-step browser access via MCP server. Use for debugging UI issues, verifying login flows, inspecting DOM/console/network incrementally, recording demo videos, or taking highlighted screenshots. Use instead of one-shot Playwright scripts when you need to inspect state between steps.
---

# Agentic Web Testing

## Overview

Step-by-step interactive browser testing via MCP server. Launch a persistent Playwright browser session, then navigate, inspect, interact, and debug one step at a time — the browser stays alive between calls.

## Quick Start

```bash
# Start the MCP server
python -m src.server

# Or use the interactive CLI
python -m src.cli
```

## Architecture

```
Agent/CLI ↔ stdin/stdout JSON-RPC 2.0 ↔ MCP Server ↔ Playwright ↔ Chromium
```

## Tool Reference

### Session Lifecycle
| Tool | Purpose |
|------|---------|
| `launch` | Start browser session |
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
| `evaluate` | Execute JavaScript |
| `wait_for` | Wait for element or load state |

### Visual Capture
| Tool | Purpose |
|------|---------|
| `screenshot` | Screenshot with optional element highlight |
| `highlight_element` | Orange highlight over element |
| `start_video` / `stop_video` | Record browser session video |

### Console & Network
| Tool | Purpose |
|------|---------|
| `get_console_logs` | Browser console messages |
| `get_network_requests` | Network request log |

### Vision Analysis (Provider-Agnostic)
| Tool | Purpose |
|------|---------|
| `analyze_screenshot` | Take screenshot + analyze with vision AI in one call |
| `analyze_image` | Analyze an existing image file with vision AI |

Configure via environment variables:
- `VISION_PROVIDER` — `"google"` (default), `"openai"`, or `"openrouter"`
- `VISION_API_KEY` — API key for the chosen provider (or provider-specific: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`)
- `VISION_MODEL` — Model override (default: provider-specific)
- `VISION_BASE_URL` — Base URL override (for OpenAI-compatible providers only)

Providers and their defaults:

| Provider | Default Model | API Key Env Var | Base URL |
|----------|--------------|----------------|----------|
| `google` | `gemini-2.5-flash-lite` | `GOOGLE_API_KEY` | — |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` | `https://api.openai.com/v1` |
| `openrouter` | `qwen/qwen3.6-plus` | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` |

All OpenAI-compatible providers (`openai`, `openrouter`) use the same base class, so you can add any OpenAI-compatible API by setting `VISION_BASE_URL`. For example, to use a local vLLM server: `VISION_PROVIDER=openai VISION_BASE_URL=http://localhost:8000/v1`

### Configuration Examples

**Cheapest — Qwen via OpenRouter (~$0.05/1K images):**
```bash
export VISION_PROVIDER=openrouter
export VISION_MODEL=qwen/qwen3.6-plus
export OPENROUTER_API_KEY=sk-or-v1-...
pip install "agentic-web-testing[openrouter-vision]"
```

**GLM via OpenRouter (~$0.08/1K images):**
```bash
export VISION_PROVIDER=openrouter
export VISION_MODEL=glm-4v-plus
export OPENROUTER_API_KEY=sk-or-v1-...
```

**Gemini Flash (free tier):**
```bash
export VISION_PROVIDER=google
export VISION_MODEL=gemini-2.5-flash-lite
export GOOGLE_API_KEY=AIza...
pip install "agentic-web-testing[google-vision]"
```

**GPT-4o (best accuracy):**
```bash
export VISION_PROVIDER=openai
export VISION_MODEL=gpt-4o
export OPENAI_API_KEY=sk-proj-...
pip install "agentic-web-testing[openai-vision]"
```

**Any OpenAI-compatible endpoint (vLLM, Ollama, Together, Groq, etc.):**
```bash
export VISION_PROVIDER=openai
export VISION_BASE_URL=http://localhost:8000/v1
export VISION_API_KEY=not-needed
```

Install: `pip install "agentic-web-testing[all-vision]"` to enable all providers.

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

## Development

```bash
pip install -e ".[dev]"
playwright install chromium
pytest
ruff check src/ tests/
mypy src/
```
