"""src/tools.py — Tool registry and build_registry factory for MCP server."""
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

    return reg
