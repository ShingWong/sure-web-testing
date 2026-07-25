# Agentic Web Testing — Design Spec

## Problem

Current webapp testing is oneshot: each test run starts a fresh Playwright script, performs actions, and exits. There's no persistent session — agents must restart the browser for every interaction, cannot inspect intermediate state, and cannot iterate step-by-step. Debugging requires re-running the entire script.

## Goal

Build a persistent, interactive browser testing tool that gives agents live access to the DOM, console, network, and page state — step by step — without restarting.

## Users

1. **Agents (OpenCode)** — call MCP tools to navigate, inspect, and interact with web apps
2. **Humans** — interactive CLI for manual debugging

## Use Cases

- **persona-bot-v2**: Test login flow, persona CRUD, chat UI, admin dashboard — step by step
- **IMS_tutorial**: Navigate Zabbix UI, take highlighted screenshots, record demo videos
- **General**: Debug failing tests interactively, inspect DOM state, verify network requests

## Architecture

```
Agent (OpenCode) ↔ stdin/stdout JSON-RPC 2.0 ↔ MCP Server ↔ Playwright ↔ Chromium
```

Single Python process. MCP server manages a persistent Playwright browser session in-memory. Tools are called step-by-step — the browser stays alive between calls. Mirrors sure-state's `createMcpServer` pattern.

### MCP Protocol

JSON-RPC 2.0 over stdin/stdout, newline-delimited:
- Methods: `initialize`, `tools/list`, `tools/call`, `notifications/initialized`
- Responses: `{"jsonrpc":"2.0", "id": N, "result": {...}}` or `{"jsonrpc":"2.0", "id": N, "error": {...}}`
- Same protocol as sure-state's `createMcpServer`

### Standardized Response Shape

All tools return:
```json
{
  "status": "ok" | "error",
  "data": { /* tool-specific payload */ },
  "error": "message if failed"
}
```

## Tools

### Session Lifecycle
| Tool | Input | Output |
|------|-------|--------|
| `launch` | `headless?`, `viewport?` | `{ session_id }` |
| `close` | — | `{ ok: true }` |
| `get_info` | — | `{ url, title, load_state }` |

### Navigation
| Tool | Input | Output |
|------|-------|--------|
| `goto` | `url`, `wait_until?` | `{ url, title }` |
| `reload` | — | `{ url, title }` |
| `go_back` | — | `{ url, title }` |
| `go_forward` | — | `{ url, title }` |

### DOM Inspection (live access)
| Tool | Input | Output |
|------|-------|--------|
| `get_dom` | `selector?` | `{ html }` — full or filtered DOM text |
| `query_elements` | `selector` | `[{ tag, text, attributes, visible, rect }]` |
| `get_text` | `selector` | `{ text }` |
| `get_attribute` | `selector`, `attr` | `{ value }` |
| `get_property` | `selector`, `prop` | `{ value }` |

### Interaction
| Tool | Input | Output |
|------|-------|--------|
| `click` | `selector`, `timeout?` | `{ ok: true }` |
| `fill` | `selector`, `text` | `{ ok: true }` |
| `press` | `selector`, `key` | `{ ok: true }` |
| `select_option` | `selector`, `value` | `{ ok: true }` |
| `hover` | `selector` | `{ ok: true }` |
| `check` / `uncheck` | `selector` | `{ ok: true }` |
| `evaluate` | `script` | `{ result }` — arbitrary JS result |
| `wait_for` | `selector?`, `timeout?` | `{ ok: true }` — wait for selector or load state |

### Visual Capture (for IMS_tutorial)
| Tool | Input | Output |
|------|-------|--------|
| `screenshot` | `path?`, `full_page?`, `highlight?`, `highlight_color?` | `{ path, data (base64) }` |
| `start_video` | `path?` | `{ ok: true }` |
| `stop_video` | — | `{ path }` |
| `highlight_element` | `selector`, `color?` | `{ rect }` |
| `clear_highlights` | — | `{ ok: true }` |

### Console & Network (live feeds)
| Tool | Input | Output |
|------|-------|--------|
| `get_console_logs` | — | `[{ level, text, source, timestamp }]` |
| `get_network_requests` | — | `[{ url, method, status, timing, type }]` |
| `clear_console_logs` | — | `{ ok: true }` |
| `clear_network_requests` | — | `{ ok: true }` |

### State Persistence
| Tool | Input | Output |
|------|-------|--------|
| `save_state` | `name` | `{ ok: true }` |
| `load_state` | `name` | `{ ok: true }` |
| `list_states` | — | `[{ name }]` |

## Highlighting Style (matches IMS_tutorial)

Orange semi-transparent overlay:
```
background: rgba(255, 180, 0, 0.20)
border: 3px solid #ff8800
border-radius: 3px
box-shadow: 0 0 12px rgba(255, 150, 0, 0.6)
pointer-events: none
z-index: 999999
```

Injected via `page.evaluate()` — same pattern as IMS_tutorial's `highlight()` function.

## Browser Session Lifecycle

1. `launch()` → creates Playwright browser + context + page
2. Tools operate on the active page
3. `close()` → destroys everything
4. Multiple `launch`/`close` cycles supported in same process

### Edge Cases
- `goto()` times out → return error with current URL/page info
- Browser crash → auto-detect and report, needs re-launch
- No browser launched → return specific error "no active session"
- Stale elements → auto-wait and retry (Playwright handles this)
- Dialogs → auto-accept by default, configurable
- Multiple tabs → operate on current page, allow tab switching

## Project Structure

```
agentic-web-testing/
├── src/
│   ├── __init__.py
│   ├── server.py           # MCP server (stdin/stdout JSON-RPC 2.0)
│   ├── browser.py          # BrowserManager — persistent Playwright session
│   ├── tools.py            # Tool definitions and registry
│   ├── cli.py              # Interactive REPL CLI
│   ├── highlighting.py     # Element highlight injection
│   └── protocol.py         # JSON-RPC 2.0 message types
├── tests/
│   ├── test_browser.py
│   ├── test_server.py
│   └── test_tools.py
├── scripts/
│   ├── with_server.py      # Server lifecycle management
│   └── security_check.py   # Pre-publish checks
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-07-24-agentic-web-testing-design.md
├── pyproject.toml
├── SKILL.md                # OpenCode skill for agentic-web-testing
├── README.md
└── .gitignore
```

## Build & Test

```bash
# Tests
pytest                    # unit + integration
pytest --headed           # headed browser tests (optional)

# Quality
ruff check src/ tests/    # linting
mypy src/                 # type checking
```

## Implementation Order

1. **Core** — `protocol.py`, `browser.py` (BrowserManager), `tools.py` (ToolRegistry)
2. **MCP Server** — `server.py` with stdin/stdout JSON-RPC 2.0
3. **Highlighting** — `highlighting.py` with IMS_tutorial-compatible styling
4. **Video capture** — Playwright video recording support
5. **CLI** — `cli.py` interactive REPL
6. **Tests** — unit + integration tests
7. **Scripts** — `with_server.py`, `security_check.py`
8. **SKILL.md** — OpenCode skill teaching agents how to use the tool
9. **Git setup** + GitHub private repo
