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
