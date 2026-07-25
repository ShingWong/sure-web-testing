"""src/tools.py — Tool registry and build_registry factory for MCP server."""
from __future__ import annotations

import base64
import os
import re
from collections.abc import Callable
from typing import Any


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
    reg = ToolRegistry()
    b = browser_manager

    reg.register("launch", "Launch a browser session", {
        "headless": "bool (optional, default true)",
        "viewport": "dict (optional, default 1920x1080)",
        "record_video": "bool (optional, default false)",
    }, lambda p: b.launch(headless=p.get("headless", True), viewport=p.get("viewport"),
                         record_video=p.get("record_video", False)))
    reg.register("close", "Close the browser session", {}, lambda p: b.close())
    reg.register("get_info", "Get current page info (URL, title, load state)", {}, lambda p: b.get_info())

    reg.register("goto", "Navigate to a URL", {"url": "str", "wait_until": "str (optional)"},
                 lambda p: b.goto(p["url"], p.get("wait_until", "networkidle")))
    reg.register("reload", "Reload current page", {}, lambda p: b.reload())
    reg.register("go_back", "Go back in history", {}, lambda p: b.go_back())
    reg.register("go_forward", "Go forward in history", {}, lambda p: b.go_forward())

    reg.register("get_dom", "Get page DOM content", {"selector": "str (optional, for filtered DOM)"},
                 lambda p: b.get_dom(selector=p.get("selector")))
    reg.register("query_elements", "Query elements matching a selector",
                 {"selector": "str"}, lambda p: b.query_elements(p["selector"]))
    reg.register("get_text", "Get text content of an element",
                 {"selector": "str"}, lambda p: b.get_text(p["selector"]))
    reg.register("get_attribute", "Get attribute of an element",
                 {"selector": "str", "attr": "str"}, lambda p: b.get_attribute(p["selector"], p["attr"]))

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

    reg.register("screenshot", "Take a screenshot with optional element highlight",
                 {"path": "str (optional)", "full_page": "bool (optional)", "highlight": "str (optional)", "highlight_color": "str (optional)"},
                 lambda p: b.screenshot(path=p.get("path"), full_page=p.get("full_page", False),
                                        highlight=p.get("highlight"), highlight_color=p.get("highlight_color")))
    reg.register("highlight_element", "Highlight an element on the page",
                 {"selector": "str", "color": "str (optional)"},
                 lambda p: b.highlight_element(p["selector"], p.get("color", "#ff8800")))
    reg.register("clear_highlights", "Clear all element highlights", {}, lambda p: b.clear_highlights())

    reg.register("start_video", "Start video recording of the browser session",
                 {"path": "str (optional)"}, lambda p: b.start_video_recording(p.get("path")))
    reg.register("stop_video", "Stop video recording and return video path",
                 {}, lambda p: b.stop_video_recording())

    reg.register("get_console_logs", "Get collected console log messages", {}, lambda p: b.get_console_logs())
    reg.register("get_network_requests", "Get collected network requests",
                 {}, lambda p: b.get_network_requests())
    reg.register("clear_console_logs", "Clear collected console logs", {}, lambda p: b.clear_console_logs())
    reg.register("clear_network_requests", "Clear collected network requests",
                 {}, lambda p: b.clear_network_requests())

    reg.register("save_state", "Save browser state (cookies, localStorage)",
                 {"name": "str"}, lambda p: b.save_state(p["name"]))
    reg.register("load_state", "Load previously saved browser state",
                 {"name": "str"}, lambda p: b.load_state(p["name"]))
    reg.register("list_states", "List saved browser states",
                 {}, lambda p: b.list_states())

    # ── Vision tools ──────────────────────────────────────────────

    def _analyze_image_bytes(image_data: bytes, prompt: str, provider_name: str | None) -> dict:
        from src.vision import DEFAULT_ANALYSIS_PROMPT, get_provider

        try:
            provider = get_provider(provider_name)
            result = provider.analyze(image_data, prompt or DEFAULT_ANALYSIS_PROMPT)
            return {"status": "ok", "data": result.to_dict()}
        except ImportError as e:
            missing = "google-genai" if "google" in str(e) else "openai"
            return {
                "status": "error",
                "error": f"Missing dependency: pip install agentic-web-testing[{missing}-vision]. Also set VISION_API_KEY env var.",
            }
        except Exception as e:
            err_msg = str(e)
            err_msg = re.sub(r'(sk-[a-zA-Z0-9]{10,}|AIza[0-9A-Za-z_-]{35}|eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{10,})', '[API KEY REDACTED]', err_msg)
            return {"status": "error", "error": err_msg}

    def handle_analyze_screenshot(params: dict) -> dict:
        ss = b.screenshot()
        if ss.get("status") != "ok":
            return {"status": "error", "error": ss.get("error", "Screenshot failed")}
        image_bytes = base64.b64decode(ss["data"]["data"])
        return _analyze_image_bytes(
            image_bytes,
            params.get("prompt", ""),
            params.get("provider"),
        )

    def handle_analyze_image(params: dict) -> dict:
        path = params.get("path", "")
        if not path or not os.path.isfile(path):
            return {"status": "error", "error": f"File not found: {path}"}
        # Security: validate the path resolves to screenshots directory
        real = os.path.realpath(path)
        allowed = os.path.realpath(os.environ.get("ALLOWED_SCREENSHOT_DIR", "/tmp"))
        if not real.startswith(allowed):
            return {"status": "error", "error": "Access denied: file must be in allowed screenshot directory"}
        with open(path, "rb") as f:
            image_bytes = f.read()
        # Validate file is actually an image via magic bytes
        if not image_bytes.startswith(b'\x89PNG\r\n\x1a\n') and not image_bytes.startswith(b'\xff\xd8'):
            return {"status": "error", "error": "Not a valid image file (PNG or JPEG expected)"}
        return _analyze_image_bytes(
            image_bytes,
            params.get("prompt", ""),
            params.get("provider"),
        )

    reg.register(
        "analyze_screenshot",
        "Take screenshot + analyze with vision AI. Providers: google (gemini-2.5-flash-lite, free tier), "
        "openai (gpt-4o), openrouter (qwen/qwen3.6-plus ~$0.05/1K, glm-4v-plus ~$0.08/1K, or any model). "
        "Set VISION_PROVIDER, VISION_API_KEY, VISION_MODEL env vars. "
        "Deps: pip install agentic-web-testing[google-vision|openai-vision|openrouter-vision]",
        {
            "prompt": "str (optional, defaults to form verification prompt)",
            "provider": "str (optional, overrides VISION_PROVIDER env var)",
        },
        handle_analyze_screenshot,
    )
    reg.register(
        "analyze_image",
        "Analyze an existing image file with vision AI. Supports same providers as analyze_screenshot.",
        {
            "path": "str (path to image file)",
            "prompt": "str (optional, defaults to form verification prompt)",
            "provider": "str (optional, overrides VISION_PROVIDER env var)",
        },
        handle_analyze_image,
    )

    return reg
