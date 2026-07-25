# Agentic Web Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent, step-by-step interactive browser testing tool with MCP server and CLI

**Architecture:** Single Python process running an MCP-over-stdio JSON-RPC 2.0 server, manages a persistent Playwright browser session in-memory. Tools called step-by-step — browser stays alive between calls. Interactive CLI as alternative entrypoint. Mirrors sure-state's MCP pattern.

**Tech Stack:** Python 3.11+, Playwright (Python), pytest, ruff, mypy

## Global Constraints

- Zero external runtime dependencies beyond `playwright` (all other packages dev-only)
- Custom MCP-over-stdio protocol (no MCP SDK) matching sure-state's JSON-RPC 2.0 pattern
- All tools return standardized `{ "status": "ok" | "error", "data": {...}, "error": "..." }` shape
- Highlighting style must match IMS_tutorial: `rgba(255,180,0,0.20)` background, `3px solid #ff8800` border, orange box-shadow glow
- Python 3.11+ with strict type hints throughout
- Playwright chromium headless by default, headed optional

---
### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: (none — first task)
- Produces: Python project skeleton with build config, test config, lint config

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "agentic-web-testing"
version = "0.1.0"
description = "Persistent, step-by-step interactive browser testing with MCP server and CLI"
license = { text = "MIT" }
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.50",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.5",
    "mypy>=1.10",
]

[project.scripts]
awt = "src.cli:main"
awt-server = "src.server:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.mypy]
strict = true
python_version = "3.11"
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
*.pyo
dist/
*.egg-info/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.env
playwright-report/
test-results/
```

- [ ] **Step 3: Create src/__init__.py**

```python
```

- [ ] **Step 4: Create tests/__init__.py**

```python
```

- [ ] **Step 5: Install playwright browsers and verify**

```bash
pip install -e ".[dev]"
playwright install chromium
pytest --version
ruff --version
mypy --version
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: project scaffolding with pyproject.toml, lint, and test config"
```

---
### Task 2: Protocol — JSON-RPC 2.0 Message Types

**Files:**
- Create: `src/protocol.py`

**Interfaces:**
- Consumes: (none — types only)
- Produces: `JSONRPCRequest`, `JSONRPCResponse`, `JSONRPCError` dataclasses; `read_message()` and `write_message()` for stdin/stdout transport

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_protocol.py"""
import json
import io
from src.protocol import JSONRPCRequest, JSONRPCResponse, JSONRPCError, read_message, write_message


def test_read_request():
    data = '{"jsonrpc":"2.0","id":1,"method":"goto","params":{"url":"http://example.com"}}\n'
    stream = io.StringIO(data)
    msg = read_message(stream)
    assert msg == JSONRPCRequest(jsonrpc="2.0", id=1, method="goto", params={"url": "http://example.com"})


def test_read_notification():
    data = '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
    stream = io.StringIO(data)
    msg = read_message(stream)
    assert msg == JSONRPCRequest(jsonrpc="2.0", id=None, method="notifications/initialized", params=None)


def test_write_response():
    stream = io.StringIO()
    msg = JSONRPCResponse(jsonrpc="2.0", id=1, result={"status": "ok", "data": {"url": "http://example.com"}})
    write_message(stream, msg)
    output = stream.getvalue()
    parsed = json.loads(output)
    assert parsed["id"] == 1
    assert parsed["result"]["status"] == "ok"


def test_write_error():
    stream = io.StringIO()
    err = JSONRPCError(jsonrpc="2.0", id=1, code=-32601, message="Method not found")
    write_message(stream, err)
    output = stream.getvalue()
    parsed = json.loads(output)
    assert parsed["error"]["code"] == -32601


def test_read_tool_list_response():
    data = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "goto", "description": "Navigate to URL"}]}}) + "\n"
    stream = io.StringIO(data)
    msg = read_message(stream)
    assert msg.result["tools"][0]["name"] == "goto"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.protocol'`

- [ ] **Step 3: Write minimal implementation**

```python
"""src/protocol.py — JSON-RPC 2.0 message types and stdin/stdout transport."""

from dataclasses import dataclass, field, asdict
from typing import Any
import json


@dataclass
class JSONRPCRequest:
    jsonrpc: str = "2.0"
    id: int | None = None
    method: str = ""
    params: dict[str, Any] | None = None


@dataclass
class JSONRPCResponse:
    jsonrpc: str = "2.0"
    id: int | None = None
    result: dict[str, Any] | None = None


@dataclass
class JSONRPCError:
    jsonrpc: str = "2.0"
    id: int | None = None
    code: int = 0
    message: str = ""
    data: Any = None


def read_message(stream) -> JSONRPCRequest | JSONRPCResponse | JSONRPCError:
    line = stream.readline()
    if not line:
        raise EOFError("Connection closed")
    raw = json.loads(line)
    if "method" in raw:
        return JSONRPCRequest(
            jsonrpc=raw.get("jsonrpc", "2.0"),
            id=raw.get("id"),
            method=raw["method"],
            params=raw.get("params"),
        )
    if "error" in raw:
        return JSONRPCError(
            jsonrpc=raw.get("jsonrpc", "2.0"),
            id=raw.get("id"),
            code=raw["error"]["code"],
            message=raw["error"]["message"],
            data=raw["error"].get("data"),
        )
    return JSONRPCResponse(
        jsonrpc=raw.get("jsonrpc", "2.0"),
        id=raw.get("id"),
        result=raw.get("result"),
    )


def write_message(stream, msg: JSONRPCRequest | JSONRPCResponse | JSONRPCError) -> None:
    d = asdict(msg)
    d = {k: v for k, v in d.items() if v is not None}
    if isinstance(msg, JSONRPCError):
        d = {"jsonrpc": d["jsonrpc"], "id": d.get("id"), "error": {"code": d["code"], "message": d["message"]}}
        if "data" in d and d["data"] is not None:
            d["error"]["data"] = d.pop("data")
    stream.write(json.dumps(d) + "\n")
    stream.flush()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/protocol.py tests/test_protocol.py && git commit -m "feat: JSON-RPC 2.0 protocol types and transport"
```

---
### Task 3: Browser Manager — Persistent Playwright Session

**Files:**
- Create: `src/browser.py`

**Interfaces:**
- Consumes: (none — standalone module)
- Produces: `BrowserManager` class with:
  - `launch(headless: bool, viewport: dict) -> dict` — starts browser, context, page
  - `close() -> dict` — closes everything
  - `get_page()` — returns active Playwright page
  - `goto(url: str) -> dict` — navigate
  - `reload() -> dict`
  - `go_back() -> dict`
  - `go_forward() -> dict`
  - `get_info() -> dict` — url, title, load_state
  - `screenshot(path: str | None, full_page: bool, highlight: str | None, highlight_color: str) -> dict`
  - `get_dom(selector: str | None) -> dict`
  - `query_elements(selector: str) -> list[dict]`
  - `click(selector: str) -> dict`
  - `fill(selector: str, text: str) -> dict`
  - `press(selector: str, key: str) -> dict`
  - `evaluate(script: str) -> Any`
  - `get_console_logs() -> list[dict]`
  - `get_network_requests() -> list[dict]`
  - `clear_console_logs()`, `clear_network_requests()`
  - `save_state(name: str)`, `load_state(name: str)`, `list_states()`

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_browser.py"""
import pytest
from src.browser import BrowserManager


def test_launch_and_close():
    mgr = BrowserManager()
    result = mgr.launch(headless=True)
    assert result["status"] == "ok"
    assert "session_id" in result["data"]
    result = mgr.close()
    assert result["status"] == "ok"


def test_goto():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    result = mgr.goto("about:blank")
    assert result["status"] == "ok"
    assert "about:blank" in result["data"]["url"]
    mgr.close()


def test_get_info():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("about:blank")
    info = mgr.get_info()
    assert info["status"] == "ok"
    assert "title" in info["data"]
    mgr.close()


def test_screenshot():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("about:blank")
    result = mgr.screenshot()
    assert result["status"] == "ok"
    assert len(result["data"]["data"]) > 0  # base64 data
    mgr.close()


def test_get_dom():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("data:text/html,<h1>Hello</h1>")
    dom = mgr.get_dom()
    assert "Hello" in dom["data"]["html"]
    dom = mgr.get_dom("h1")
    assert "Hello" in dom["data"]["html"]
    mgr.close()


def test_click_and_fill():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("data:text/html,<input id='a'><button id='b'>Go</button>")
    r = mgr.fill("#a", "hello")
    assert r["status"] == "ok"
    r = mgr.click("#b")
    assert r["status"] == "ok"
    mgr.close()


def test_console_logs():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.evaluate("console.log('test message')")
    logs = mgr.get_console_logs()
    assert len(logs["data"]) > 0
    assert "test message" in logs["data"][0]["text"]
    mgr.close()


def test_no_session_error():
    mgr = BrowserManager()
    result = mgr.goto("about:blank")
    assert result["status"] == "error"
    assert "session" in result["error"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.browser'`

- [ ] **Step 3: Write minimal implementation**

```python
"""src/browser.py — Manages a persistent Playwright browser session."""
import base64
import os
import time
from typing import Any
from uuid import uuid4

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}


class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._session_id: str | None = None
        self._console_logs: list[dict] = []
        self._network_requests: list[dict] = []
        self._recording = False
        self._video_path: str | None = None
        self._states: dict[str, str] = {}  # name -> path

    def _ensure_session(self):
        if not self._browser or not self._page:
            raise RuntimeError("No active session. Call launch() first.")

    def launch(self, headless: bool = True, viewport: dict | None = None) -> dict:
        try:
            self._playwright = sync_playwright().__enter__()
            self._browser = self._playwright.chromium.launch(headless=headless)
            self._context = self._browser.new_context(
                viewport=viewport or DEFAULT_VIEWPORT,
                record_video_dir=os.path.abspath("./recordings") if self._recording else None,
            )
            self._page = self._context.new_page()
            self._session_id = str(uuid4())

            self._page.on("console", lambda msg: self._console_logs.append({
                "level": msg.type,
                "text": msg.text,
                "source": msg.location.url if hasattr(msg, "location") else "",
                "timestamp": time.time(),
            }))

            self._page.on("request", lambda req: self._network_requests.append({
                "url": req.url,
                "method": req.method,
                "type": req.resource_type,
                "timestamp": time.time(),
            }))

            self._page.on("response", lambda res: self._network_requests.append({
                "url": res.url,
                "method": res.request.method,
                "status": res.status,
                "type": res.request.resource_type,
                "timestamp": time.time(),
            }))

            return {"status": "ok", "data": {"session_id": self._session_id}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def close(self) -> dict:
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.__exit__(None, None, None)
            self._browser = None
            self._context = None
            self._page = None
            self._session_id = None
            self._console_logs = []
            self._network_requests = []
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def goto(self, url: str, wait_until: str = "networkidle") -> dict:
        try:
            self._ensure_session()
            self._page.goto(url, wait_until=wait_until)
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e), "data": {"url": self._page.url if self._page else "", "title": self._page.title() if self._page else ""}}

    def reload(self) -> dict:
        try:
            self._ensure_session()
            self._page.reload()
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def go_back(self) -> dict:
        try:
            self._ensure_session()
            self._page.go_back()
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def go_forward(self) -> dict:
        try:
            self._ensure_session()
            self._page.go_forward()
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_info(self) -> dict:
        try:
            self._ensure_session()
            return {"status": "ok", "data": {
                "url": self._page.url,
                "title": self._page.title(),
                "load_state": "loaded",
            }}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_dom(self, selector: str | None = None) -> dict:
        try:
            self._ensure_session()
            if selector:
                els = self._page.locator(selector)
                if els.count() == 0:
                    return {"status": "ok", "data": {"html": ""}}
                html = els.first.inner_html()
            else:
                html = self._page.content()
            return {"status": "ok", "data": {"html": html}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def query_elements(self, selector: str) -> dict:
        try:
            self._ensure_session()
            els = self._page.locator(selector)
            count = els.count()
            results = []
            for i in range(min(count, 50)):
                el = els.nth(i)
                try:
                    visible = el.is_visible()
                except Exception:
                    visible = False
                try:
                    box = el.bounding_box()
                    rect = {"x": round(box["x"]), "y": round(box["y"]), "w": round(box["width"]), "h": round(box["height"])} if box else None
                except Exception:
                    rect = None
                results.append({
                    "tag": el.evaluate("el => el.tagName.toLowerCase()", timeout=1000) if count > 0 else "",
                    "text": el.text_content(timeout=1000) or "",
                    "visible": visible,
                    "rect": rect,
                })
            return {"status": "ok", "data": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def click(self, selector: str, timeout: int = 10000) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            self._page.locator(selector).first.click()
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def fill(self, selector: str, text: str, timeout: int = 10000) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            self._page.locator(selector).first.fill(text)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def press(self, selector: str, key: str) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.press(key)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def select_option(self, selector: str, value: str) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.select_option(value)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def hover(self, selector: str) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.hover()
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def evaluate(self, script: str) -> dict:
        try:
            self._ensure_session()
            result = self._page.evaluate(script)
            return {"status": "ok", "data": {"result": result}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def screenshot(self, path: str | None = None, full_page: bool = False,
                   highlight: str | None = None, highlight_color: str | None = None) -> dict:
        try:
            self._ensure_session()
            if highlight:
                self._highlight_element(highlight, highlight_color or "#ff8800")
            import tempfile
            path = path or os.path.join(tempfile.gettempdir(), f"awt_{uuid4().hex}.png")
            self._page.screenshot(path=path, full_page=full_page)
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            if highlight:
                self._clear_highlights()
            return {"status": "ok", "data": {"path": path, "data": data}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _highlight_element(self, selector: str, color: str = "#ff8800"):
        self._clear_highlights()
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        js = f"""(() => {{
            const el = document.querySelector('{selector.replace("'", "\\'")}');
            if (!el) return;
            const r = el.getBoundingClientRect();
            let f = document.getElementById('awt-highlight');
            if (!f) {{
                f = document.createElement('div');
                f.id = 'awt-highlight';
                document.body.appendChild(f);
            }}
            f.style.cssText = 'position:fixed;left:{r.x}px;top:{r.y}px;width:{r.width}px;height:{r.height}px;' +
                'background:rgba({r},{g},{b},0.20);border:3px solid {color};z-index:999999;' +
                'pointer-events:none;border-radius:3px;box-shadow:0 0 12px rgba({r},{g},{b},0.6)';
        }})()"""
        self._page.evaluate(js)

    def _clear_highlights(self):
        self._page.evaluate("(()=>{let o=document.getElementById('awt-highlight');if(o)o.remove();})()")

    def highlight_element(self, selector: str, color: str = "#ff8800") -> dict:
        try:
            self._ensure_session()
            self._highlight_element(selector, color)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clear_highlights(self) -> dict:
        try:
            self._ensure_session()
            self._clear_highlights()
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_text(self, selector: str) -> dict:
        try:
            self._ensure_session()
            text = self._page.locator(selector).first.text_content(timeout=5000) or ""
            return {"status": "ok", "data": {"text": text.strip()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_attribute(self, selector: str, attr: str) -> dict:
        try:
            self._ensure_session()
            val = self._page.locator(selector).first.get_attribute(attr, timeout=5000)
            return {"status": "ok", "data": {"value": val}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def wait_for(self, selector: str | None = None, timeout: int = 10000) -> dict:
        try:
            self._ensure_session()
            if selector:
                self._page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            else:
                self._page.wait_for_load_state("networkidle", timeout=timeout)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_console_logs(self) -> dict:
        return {"status": "ok", "data": list(self._console_logs)}

    def get_network_requests(self) -> dict:
        return {"status": "ok", "data": list(self._network_requests)}

    def clear_console_logs(self) -> dict:
        self._console_logs = []
        return {"status": "ok", "data": {"ok": True}}

    def clear_network_requests(self) -> dict:
        self._network_requests = []
        return {"status": "ok", "data": {"ok": True}}

    def save_state(self, name: str) -> dict:
        try:
            self._ensure_session()
            state_path = f"/tmp/awt_state_{name}.json"
            self._context.storage_state(path=state_path)
            self._states[name] = state_path
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def load_state(self, name: str) -> dict:
        try:
            self._ensure_session()
            if name not in self._states:
                return {"status": "error", "error": f"State '{name}' not found"}
            self._context.add_cookies(self._states[name])
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_states(self) -> dict:
        return {"status": "ok", "data": [{"name": k} for k in self._states]}

    def get_page(self) -> Page:
        self._ensure_session()
        return self._page
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/browser.py tests/test_browser.py && git commit -m "feat: BrowserManager with persistent Playwright session"
```

---
### Task 4: Tools Registry

**Files:**
- Create: `src/tools.py`

**Interfaces:**
- Consumes: `BrowserManager` from `src/browser.py`
- Produces: `ToolRegistry` class with `register()`, `list_tools()`, `call_tool(name, params) -> dict`

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_tools.py"""
from src.tools import ToolRegistry


def test_register_and_list():
    reg = ToolRegistry()
    def my_tool(params: dict) -> dict:
        return {"status": "ok", "data": {"result": params.get("x", 0) * 2}}
    reg.register("double", "Multiply by 2", {"x": "int"}, my_tool)
    tools = reg.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "double"

def test_call_tool():
    reg = ToolRegistry()
    def my_tool(params: dict) -> dict:
        return {"status": "ok", "data": {"result": params["x"] * 2}}
    reg.register("double", "Multiply by 2", {"x": "int"}, my_tool)
    result = reg.call_tool("double", {"x": 5})
    assert result["status"] == "ok"
    assert result["data"]["result"] == 10

def test_call_unknown_tool():
    reg = ToolRegistry()
    result = reg.call_tool("nonexistent", {})
    assert result["status"] == "error"

def test_call_with_error():
    reg = ToolRegistry()
    def broken(params):
        raise ValueError("oops")
    reg.register("broken", "Broken tool", {}, broken)
    result = reg.call_tool("broken", {})
    assert result["status"] == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""src/tools.py — Tool registry for MCP server."""
from typing import Callable, Any


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, params: dict[str, str], handler: Callable[[dict], dict]) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "params": params,
            "handler": handler,
        }

    def list_tools(self) -> list[dict]:
        return [
            {"name": t["name"], "description": t["description"], "params": t["params"]}
            for t in self._tools.values()
        ]

    def call_tool(self, name: str, params: dict[str, Any]) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {"status": "error", "error": f"Unknown tool: {name}"}
        try:
            return tool["handler"](params)
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: all tests PASS

- [ ] **Step 5: Build tool map from BrowserManager methods**

Create the actual tool registry that wraps BrowserManager for use in the MCP server. Update `src/tools.py` to include a `build_registry()` factory:

```python
"""src/tools.py — Tool registry for MCP server."""
from typing import Callable, Any


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, params: dict[str, str], handler: Callable[[dict], dict]) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "params": params,
            "handler": handler,
        }

    def list_tools(self) -> list[dict]:
        return [
            {"name": t["name"], "description": t["description"], "params": t["params"]}
            for t in self._tools.values()
        ]

    def call_tool(self, name: str, params: dict[str, Any]) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {"status": "error", "error": f"Unknown tool: {name}"}
        try:
            return tool["handler"](params)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_handler(self, name: str) -> Callable | None:
        tool = self._tools.get(name)
        return tool["handler"] if tool else None


def build_registry(browser_manager) -> ToolRegistry:
    """Build the full tool registry wrapping a BrowserManager instance."""
    reg = ToolRegistry()
    b = browser_manager

    # Session lifecycle
    reg.register("launch", "Launch a browser session", {
        "headless": "bool (optional, default true)",
        "viewport": "dict (optional, default 1920x1080)",
    }, lambda p: b.launch(headless=p.get("headless", True), viewport=p.get("viewport")))
    reg.register("close", "Close the browser session", {}, lambda p: b.close())
    reg.register("get_info", "Get current page info (URL, title, load state)", {}, lambda p: b.get_info())

    # Navigation
    reg.register("goto", "Navigate to a URL", {"url": "str", "wait_until": "str (optional)"},
                 lambda p: b.goto(p["url"], p.get("wait_until", "networkidle")))
    reg.register("reload", "Reload current page", {}, lambda p: b.reload())
    reg.register("go_back", "Go back in history", {}, lambda p: b.go_back())
    reg.register("go_forward", "Go forward in history", {}, lambda p: b.go_forward())

    # DOM inspection
    reg.register("get_dom", "Get page DOM content", {"selector": "str (optional, for filtered DOM)"},
                 lambda p: b.get_dom(selector=p.get("selector")))
    reg.register("query_elements", "Query elements matching a selector",
                 {"selector": "str"}, lambda p: b.query_elements(p["selector"]))
    reg.register("get_text", "Get text content of an element",
                 {"selector": "str"}, lambda p: b.get_text(p["selector"]))
    reg.register("get_attribute", "Get attribute of an element",
                 {"selector": "str", "attr": "str"}, lambda p: b.get_attribute(p["selector"], p["attr"]))

    # Interaction
    reg.register("click", "Click an element", {"selector": "str", "timeout": "int (optional, default 10000)"},
                 lambda p: b.click(p["selector"], p.get("timeout", 10000)))
    reg.register("fill", "Fill an input field", {"selector": "str", "text": "str"},
                 lambda p: b.fill(p["selector"], p["text"]))
    reg.register("press", "Press a key on an element", {"selector": "str", "key": "str"},
                 lambda p: b.press(p["selector"], p["key"]))
    reg.register("select_option", "Select an option in a dropdown",
                 {"selector": "str", "value": "str"}, lambda p: b.select_option(p["selector"], p["value"]))
    reg.register("hover", "Hover over an element",
                 {"selector": "str"}, lambda p: b.hover(p["selector"]))
    reg.register("evaluate", "Execute JavaScript in page context",
                 {"script": "str"}, lambda p: b.evaluate(p["script"]))
    reg.register("wait_for", "Wait for element or load state",
                 {"selector": "str (optional)", "timeout": "int (optional, default 10000)"},
                 lambda p: b.wait_for(selector=p.get("selector"), timeout=p.get("timeout", 10000)))

    # Visual capture
    reg.register("screenshot", "Take a screenshot with optional element highlight",
                 {"path": "str (optional)", "full_page": "bool (optional)", "highlight": "str (optional)", "highlight_color": "str (optional)"},
                 lambda p: b.screenshot(path=p.get("path"), full_page=p.get("full_page", False),
                                        highlight=p.get("highlight"), highlight_color=p.get("highlight_color")))
    reg.register("highlight_element", "Highlight an element on the page",
                 {"selector": "str", "color": "str (optional)"},
                 lambda p: b.highlight_element(p["selector"], p.get("color", "#ff8800")))
    reg.register("clear_highlights", "Clear all element highlights", {}, lambda p: b.clear_highlights())

    # Console & network
    reg.register("get_console_logs", "Get collected console log messages", {}, lambda p: b.get_console_logs())
    reg.register("get_network_requests", "Get collected network requests",
                 {}, lambda p: b.get_network_requests())
    reg.register("clear_console_logs", "Clear collected console logs", {}, lambda p: b.clear_console_logs())
    reg.register("clear_network_requests", "Clear collected network requests",
                 {}, lambda p: b.clear_network_requests())

    # State persistence
    reg.register("save_state", "Save browser state (cookies, localStorage)",
                 {"name": "str"}, lambda p: b.save_state(p["name"]))
    reg.register("load_state", "Load previously saved browser state",
                 {"name": "str"}, lambda p: b.load_state(p["name"]))
    reg.register("list_states", "List saved browser states",
                 {}, lambda p: b.list_states())

    return reg
```

- [ ] **Step 6: Run tests again**

Run: `pytest tests/test_tools.py -v`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/tools.py tests/test_tools.py && git commit -m "feat: ToolRegistry and build_registry with all browser tools"
```

---
### Task 5: MCP Server

**Files:**
- Create: `src/server.py`

**Interfaces:**
- Consumes: `ToolRegistry` from `src/tools.py`, `BrowserManager` from `src/browser.py`, `read_message`/`write_message` from `src/protocol.py`
- Produces: `MCPServer` class that handles stdin/stdout JSON-RPC 2.0 protocol

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_server.py"""
import io
import json
from src.server import MCPServer
from src.tools import ToolRegistry


def test_initialize():
    reg = ToolRegistry()
    reg.register("ping", "Ping test", {}, lambda p: {"status": "ok", "data": {"pong": True}})
    server = MCPServer(reg)

    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    output = stdout.getvalue()
    parsed = json.loads(output)
    assert parsed["id"] == 1
    assert parsed["result"]["protocolVersion"] == "0.1"


def test_tools_list():
    reg = ToolRegistry()
    reg.register("ping", "Ping test", {"x": "str"}, lambda p: {"status": "ok", "data": {"pong": True}})
    server = MCPServer(reg)

    stdin = io.StringIO('{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n')
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    output = stdout.getvalue()
    parsed = json.loads(output)
    assert parsed["id"] == 2
    assert len(parsed["result"]["tools"]) == 1
    assert parsed["result"]["tools"][0]["name"] == "ping"


def test_tools_call():
    reg = ToolRegistry()
    reg.register("echo", "Echo input", {"msg": "str"}, lambda p: {"status": "ok", "data": {"echo": p["msg"]}})
    server = MCPServer(reg)

    stdin = io.StringIO(json.dumps({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"msg":"hello"}}}) + "\n")
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    output = stdout.getvalue()
    parsed = json.loads(output)
    assert parsed["id"] == 3
    assert parsed["result"]["content"][0]["text"] == "hello"


def test_unknown_method():
    reg = ToolRegistry()
    server = MCPServer(reg)
    stdin = io.StringIO('{"jsonrpc":"2.0","id":4,"method":"unknown","params":{}}\n')
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    output = stdout.getvalue()
    parsed = json.loads(output)
    assert "error" in parsed
    assert parsed["error"]["code"] == -32601


def test_notification_no_response():
    reg = ToolRegistry()
    server = MCPServer(reg)
    stdin = io.StringIO('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    assert stdout.getvalue() == ""


def test_malformed_json():
    reg = ToolRegistry()
    server = MCPServer(reg)
    stdin = io.StringIO("not json\n")
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    output = stdout.getvalue()
    parsed = json.loads(output)
    assert "error" in parsed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""src/server.py — MCP server handling stdin/stdout JSON-RPC 2.0 protocol."""
import json
import sys
import traceback
from typing import Any

from src.protocol import read_message, write_message, JSONRPCRequest, JSONRPCResponse, JSONRPCError
from src.tools import ToolRegistry


class MCPServer:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def handle_one(self, stdin, stdout) -> None:
        try:
            msg = read_message(stdin)
        except EOFError:
            return
        except Exception as e:
            err = JSONRPCError(id=None, code=-32700, message="Parse error", data=str(e))
            write_message(stdout, err)
            return

        if isinstance(msg, JSONRPCError):
            write_message(stdout, msg)
            return

        req = msg

        # Notifications (no id) — no response
        if req.id is None:
            return

        try:
            result = self._handle_method(req.method, req.params or {})
            if "error" in result and result["status"] == "error":
                resp = JSONRPCResponse(id=req.id, result=result)
            else:
                resp = JSONRPCResponse(id=req.id, result=result)
            write_message(stdout, resp)
        except Exception as e:
            err = JSONRPCError(id=req.id, code=-32603, message="Internal error", data=str(e))
            write_message(stdout, err)

    def _handle_method(self, method: str, params: dict[str, Any]) -> dict:
        if method == "initialize":
            return {
                "protocolVersion": "0.1",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agentic-web-testing", "version": "0.1.0"},
            }
        elif method == "tools/list":
            return {"tools": self._registry.list_tools()}
        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self._registry.call_tool(name, arguments)
            content = []
            if "data" in result:
                content.append({"type": "text", "text": json.dumps(result["data"])})
            if "error" in result:
                content.append({"type": "text", "text": result["error"]})
            return {"content": content}
        else:
            raise ValueError(f"Unknown method: {method}")

    def run(self, stdin=sys.stdin, stdout=sys.stdout) -> None:
        while True:
            try:
                self.handle_one(stdin, stdout)
            except EOFError:
                break
            except Exception:
                traceback.print_exc()
                break


def main():
    from src.browser import BrowserManager
    from src.tools import build_registry

    browser = BrowserManager()
    registry = build_registry(browser)
    server = MCPServer(registry)
    server.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_server.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/server.py tests/test_server.py && git commit -m "feat: MCP server with stdin/stdout JSON-RPC 2.0 protocol"
```

---
### Task 6: Interactive CLI

**Files:**
- Create: `src/cli.py`

**Interfaces:**
- Consumes: `BrowserManager` from `src/browser.py`
- Produces: Interactive REPL where users type tool commands and see formatted results

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_cli.py"""
from src.browser import BrowserManager
from src.cli import format_result


def test_format_ok():
    result = format_result({"status": "ok", "data": {"url": "http://example.com", "title": "Example"}})
    assert "ok" in result.lower()
    assert "http://example.com" in result


def test_format_error():
    result = format_result({"status": "error", "error": "Something went wrong"})
    assert "error" in result.lower()
    assert "Something went wrong" in result


def test_format_list():
    result = format_result({"status": "ok", "data": [{"name": "foo"}, {"name": "bar"}]})
    assert "foo" in result
    assert "bar" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""src/cli.py — Interactive REPL CLI for step-by-step browser testing."""
import shlex
import sys
from src.browser import BrowserManager


def format_result(result: dict) -> str:
    if result.get("status") == "error":
        return f"❌ Error: {result.get('error', 'unknown error')}"
    data = result.get("data")
    if data is None:
        return "✓ OK (no data)"
    if isinstance(data, list):
        lines = [f"  [{i}] {d}" for i, d in enumerate(data)]
        return f"✓ {len(data)} items:\n" + "\n".join(lines)
    if isinstance(data, dict):
        if "html" in data:
            html = data["html"]
            return f"✓ DOM ({len(html)} chars)\n{html[:2000]}"
        if "data" in data and isinstance(data["data"], str) and len(data["data"]) > 100:
            return f"✓ Screenshot captured ({len(data['data'])} bytes base64)"
        parts = [f"  {k}: {v}" for k, v in data.items() if v is not None]
        return "✓ " + ", ".join(parts) if len(parts) <= 3 else "✓\n" + "\n".join(parts)
    return f"✓ {data}"


def main():
    mgr = BrowserManager()
    print("Agentic Web Testing CLI")
    print("Type 'help' for commands, 'quit' to exit.")
    print()

    commands = {
        "launch": lambda args: mgr.launch(headless="--headed" not in args),
        "close": lambda args: mgr.close(),
        "goto": lambda args: mgr.goto(args[0]) if args else {"status": "error", "error": "Usage: goto <url>"},
        "screenshot": lambda args: mgr.screenshot(),
        "dom": lambda args: mgr.get_dom(),
        "click": lambda args: mgr.click(args[0]) if args else {"status": "error", "error": "Usage: click <selector>"},
        "fill": lambda args: mgr.fill(args[0], " ".join(args[1:])) if len(args) >= 2 else {"status": "error", "error": "Usage: fill <selector> <text>"},
        "info": lambda args: mgr.get_info(),
        "console": lambda args: mgr.get_console_logs(),
        "network": lambda args: mgr.get_network_requests(),
        "evaluate": lambda args: mgr.evaluate(" ".join(args)) if args else {"status": "error", "error": "Usage: evaluate <js>"},
        "highlight": lambda args: mgr.highlight_element(args[0]) if args else {"status": "error", "error": "Usage: highlight <selector>"},
        "clear": lambda args: mgr.clear_highlights(),
        "help": lambda args: print("Commands: launch, close, goto, screenshot, dom, click, fill, info,\n  console, network, evaluate, highlight, clear, help, quit"),
    }

    while True:
        try:
            line = input("awt> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line == "quit":
            break

        parts = shlex.split(line)
        cmd = parts[0]
        args = parts[1:]

        handler = commands.get(cmd)
        if not handler:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")
            continue

        try:
            result = handler(args)
            if result:
                print(format_result(result))
        except Exception as e:
            print(f"Error: {e}")

    mgr.close()
    print("Goodbye.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/cli.py tests/test_cli.py && git commit -m "feat: interactive CLI REPL for step-by-step browser testing"
```

---
### Task 7: Highlighting Module

**Files:**
- Create: `src/highlighting.py`

**Interfaces:**
- Consumes: Playwright `Page` object
- Produces: `HighlightManager` class with `highlight(selector, color)`, `clear()`, style matching IMS_tutorial

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_highlighting.py"""
from src.highlighting import HighlightManager, HIGHLIGHT_STYLE


def test_style_constants():
    assert "rgba(255,180,0,0.20)" in HIGHLIGHT_STYLE["background"]
    assert "#ff8800" in HIGHLIGHT_STYLE["border"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_highlighting.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""src/highlighting.py — Element highlight injection matching IMS_tutorial style."""

HIGHLIGHT_STYLE = {
    "background": "rgba(255,180,0,0.20)",
    "border": "3px solid #ff8800",
    "border_radius": "3px",
    "box_shadow": "0 0 12px rgba(255,150,0,0.6)",
    "z_index": "999999",
    "pointer_events": "none",
}


class HighlightManager:
    def __init__(self, page):
        self._page = page
        self._element_id = "awt-highlight"

    def highlight(self, selector: str, color: str = "#ff8800") -> dict:
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        js = f"""(() => {{
            const el = document.querySelector('{selector.replace("'", "\\'")}');
            if (!el) return false;
            const r = el.getBoundingClientRect();
            let f = document.getElementById('{self._element_id}');
            if (!f) {{
                f = document.createElement('div');
                f.id = '{self._element_id}';
                document.body.appendChild(f);
            }}
            f.style.cssText = 'position:fixed;left:' + r.x + 'px;top:' + r.y + 'px;' +
                'width:' + r.width + 'px;height:' + r.height + 'px;' +
                'background:rgba({r},{g},{b},0.20);' +
                'border:3px solid {color};z-index:999999;' +
                'pointer-events:none;border-radius:3px;' +
                'box-shadow:0 0 12px rgba({r},{g},{b},0.6)';
            return true;
        }})()"""
        found = self._page.evaluate(js)
        return {"status": "ok" if found else "error", "data": {"found": found}}

    def clear(self) -> dict:
        self._page.evaluate(f"(()=>{{let o=document.getElementById('{self._element_id}');if(o)o.remove();}})()")
        return {"status": "ok", "data": {"ok": True}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_highlighting.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/highlighting.py tests/test_highlighting.py && git commit -m "feat: HighlightManager matching IMS_tutorial style"
```

---
### Task 8: Video Capture Support

**Files:**
- Modify: `src/browser.py` — add video recording methods

**Interfaces:**
- Consumes: Playwright video recording API
- Produces: `start_video_recording(path?)` and `stop_video_recording()` methods on BrowserManager

- [ ] **Step 1: Add tests**

```python
# Add to tests/test_browser.py

def test_video_recording():
    mgr = BrowserManager()
    mgr.launch(headless=True, record_video=True)
    mgr.goto("about:blank")
    mgr.evaluate("document.body.innerHTML = '<h1>Test</h1>'")
    result = mgr.stop_video_recording()
    assert result["status"] == "ok"
    assert result["data"]["video_path"] is not None
    mgr.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser.py::test_video_recording -v`
Expected: FAIL

- [ ] **Step 3: Add video methods to BrowserManager**

Add to `src/browser.py`:

```python
    def start_video_recording(self, path: str | None = None) -> dict:
        try:
            self._ensure_session()
            self._recording = True
            self._video_path = path
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def stop_video_recording(self) -> dict:
        try:
            self._ensure_session()
            video = self._page.video
            if video:
                video_path = video.path()
                return {"status": "ok", "data": {"video_path": video_path}}
            return {"status": "error", "error": "No video recording in progress"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

Also modify `launch()` to accept `record_video` parameter that sets up video dir.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser.py::test_video_recording -v`
Expected: PASS

- [ ] **Step 5: Register video tools in build_registry**

Add to `src/tools.py` in `build_registry()`:

```python
    reg.register("start_video", "Start video recording of the browser session",
                 {"path": "str (optional)"}, lambda p: b.start_video_recording(p.get("path")))
    reg.register("stop_video", "Stop video recording and return video path",
                 {}, lambda p: b.stop_video_recording())
```

- [ ] **Step 6: Commit**

```bash
git add src/browser.py src/tools.py && git commit -m "feat: video recording support"
```

---
### Task 9: Scripts — Server Lifecycle and Security Check

**Files:**
- Create: `scripts/with_server.py`
- Create: `scripts/security_check.py`

- [ ] **Step 1: Create with_server.py (server lifecycle management)**

```python
#!/usr/bin/env python3
"""Manage MCP server lifecycle: start, stop, restart, status.

Usage:
    python scripts/with_server.py --help
"""
import argparse
import os
import signal
import subprocess
import sys
import time


PID_FILE = "/tmp/awt-server.pid"
LOG_FILE = "/tmp/awt-server.log"


def start():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if os.path.exists(f"/proc/{pid}"):
            print(f"Server already running (PID {pid})")
            return
    with open(LOG_FILE, "w") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.server"],
            stdout=log, stderr=log,
        )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    time.sleep(0.5)
    if proc.poll() is None:
        print(f"Server started (PID {proc.pid})")
    else:
        print("Server failed to start")
        sys.exit(1)


def stop():
    if not os.path.exists(PID_FILE):
        print("No PID file found")
        return
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        os.unlink(PID_FILE)
        print(f"Server stopped (PID {pid})")
    except ProcessLookupError:
        os.unlink(PID_FILE)
        print("Server not running")


def status():
    if not os.path.exists(PID_FILE):
        print("Server not running")
        return
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    if os.path.exists(f"/proc/{pid}"):
        print(f"Server running (PID {pid})")
    else:
        print("PID file exists but process not found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agentic Web Testing server lifecycle")
    parser.add_argument("command", choices=["start", "stop", "restart", "status"])
    args = parser.parse_args()

    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "restart":
        stop()
        time.sleep(1)
        start()
    elif args.command == "status":
        status()
```

- [ ] **Step 2: Create security_check.py (pre-publish checks)**

```python
#!/usr/bin/env python3
"""Pre-publish security checks. Modeled after sure-state's security-check.ts."""
import os
import subprocess
import sys


def check_no_secrets():
    """Check for common secret patterns in source files."""
    patterns = [
        (r"password\s*=\s*['\"].+['\"]", "Hardcoded password"),
        (r"api_key\s*=\s*['\"].+['\"]", "Hardcoded API key"),
        (r"secret\s*=\s*['\"].+['\"]", "Hardcoded secret"),
        (r"token\s*=\s*['\"].+['\"]", "Hardcoded token"),
    ]
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    issues = []
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                for i, line in enumerate(f, 1):
                    for pat, desc in patterns:
                        import re
                        if re.search(pat, line):
                            issues.append(f"  {fpath}:{i} — {desc}")
    if issues:
        print("⚠ Security issues found:")
        for issue in issues:
            print(issue)
        return False
    print("✓ No security issues found")
    return True


def check_dependencies():
    """Check for known-vulnerable dependencies."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=columns"],
        capture_output=True, text=True,
    )
    print("Dependencies:")
    print(result.stdout)
    return True


if __name__ == "__main__":
    ok = True
    ok &= check_no_secrets()
    ok &= check_dependencies()
    sys.exit(0 if ok else 1)
```

- [ ] **Step 3: Commit**

```bash
git add scripts/ && git commit -m "chore: server lifecycle and security check scripts"
```

---
### Task 10: SKILL.md for OpenCode

**Files:**
- Create: `SKILL.md` (at project root, for OpenCode skill system)

**Interfaces:**
- Consumes: (none — documentation only)
- Produces: OpenCode skill file teaching agents how to use the tool

- [ ] **Step 1: Create SKILL.md**

```markdown
---
name: agentic-web-testing
description: Use when testing web applications interactively with step-by-step browser access via MCP server. Use for debugging UI issues, verifying login flows, inspecting DOM/console/network incrementally, recording demo videos, or taking highlighted screenshots. Use instead of one-shot Playwright scripts when you need to inspect state between steps.
---

# Agentic Web Testing

## Overview

Step-by-step interactive browser testing via MCP server. Launch a persistent Playwright browser session, then navigate, inspect, interact, and debug one step at a time — the browser stays alive between calls.

## When to Use

- Testing web apps interactively (login flows, forms, navigation)
- Debugging UI issues (DOM state, console errors, network requests)
- Recording demo videos of browser workflows
- Taking screenshots with element highlighting
- Any task that currently uses a one-shot Playwright script

## Quick Start

```bash
# Start the MCP server (for agent use)
python -m src.server

# Or use the interactive CLI (for human use)
python -m src.cli
```

## Architecture

```
Agent/CLI ↔ stdin/stdout JSON-RPC 2.0 ↔ MCP Server ↔ Playwright ↔ Chromium
```

The server manages a persistent browser session. Each tool call operates on the same page. Call `launch()` once, interact step-by-step, then `close()` when done.

## Tool Reference

### Session Lifecycle
| Tool | Purpose |
|------|---------|
| `launch` | Start browser session (headless by default) |
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
| `click` | Click element (waits for visible) |
| `fill` | Fill input field |
| `press` | Press key |
| `select_option` | Select dropdown value |
| `evaluate` | Run JavaScript in page context |
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
| `clear_console_logs` / `clear_network_requests` | Reset logs |

### State
| Tool | Purpose |
|------|---------|
| `save_state` / `load_state` | Persist/restore cookies + storage |
| `list_states` | Saved states |

## Typical Workflow

```
1. launch(headless=false)      → open visible browser
2. goto("http://localhost:6080") → navigate to app
3. fill("input[name=email]", "user@example.com")
4. fill("input[name=password]", "mypassword")
5. click("button[type=submit]")
6. wait_for("text=Dashboard")
7. screenshot(highlight="h1")  → verify logged in
8. get_console_logs()          → check for errors
9. evaluate("localStorage.getItem('token')")  → check auth state
10. close()
```

## Common Patterns

### Debugging Auth
```
goto("http://app/login")
fill("input[name=email]", email)
fill("input[name=password]", password)
click("button[type=submit]")
wait_for("a[href='/dashboard']")
screenshot(highlight="a[href='/dashboard']")
get_console_logs()
evaluate("localStorage.getItem('token')")
```

### Finding Selectors
```
goto(url)
wait_for()
query_elements("button")      → list all buttons
query_elements("a")           → list all links
get_dom("form")               → get form HTML
```

### Recording a Demo
```
launch(headless=false)
start_video()
goto(url)
click("...")
fill("...")
screenshot(highlight="...")
...
stop_video()                  → returns mp4 path
close()
```

## Example: Testing Zabbix (from IMS_tutorial)

```
launch()
goto("http://zabbix:8088/index.php")
fill("[name=name]", "Admin")
fill("[name=password]", "zabbix")
click("button[type=submit]")
wait_for("a[href*=action=host.view]")
goto("http://zabbix:8088/zabbix.php?action=host.view")
screenshot(highlight="button.js-create-host")
click("button.js-create-host")
fill("[name=host]", "kvm10")
screenshot(highlight="[name=host]", highlight_color="#ff8800")
```

## Development

```bash
# Install
pip install -e ".[dev]"
playwright install chromium

# Test
pytest

# Lint
ruff check src/ tests/
mypy src/
```

## Related

- **webapp-testing** — legacy one-shot Playwright scripts (use agentic-web-testing for new work)
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md && git commit -m "docs: SKILL.md for OpenCode agentic-web-testing skill"
```

---
### Task 11: GitHub Private Repository Setup

**Files:**
- (none — git/gh operations)

- [ ] **Step 1: Create GitHub private repo and push**

```bash
gh repo create agentic-web-testing --private --description "Persistent, step-by-step interactive browser testing with MCP server and CLI" --push --remote origin
git branch -m main
git push -u origin main
```

- [ ] **Step 2: Verify**

```bash
gh repo view ShingWong/agentic-web-testing --json visibility,url
```

---

## Self-Review Checklist

- [ ] Spec coverage: All tools from the design doc are implemented (launch, close, goto, etc.)
- [ ] Placeholder scan: No "TBD", "TODO", or incomplete sections
- [ ] Type consistency: BrowserManager methods match tool registry signatures
- [ ] Test coverage: protocol, browser, tools, server, CLI, highlighting all have tests
