"""tests/test_tools.py"""
from src.browser import BrowserManager
from src.tools import ToolRegistry, build_registry


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


def test_build_registry_has_all_tools():
    b = BrowserManager()
    reg = build_registry(b)
    tools = reg.list_tools()
    names = [t["name"] for t in tools]
    assert "launch" in names
    assert "goto" in names
    assert "get_dom" in names
    assert "click" in names
    assert "fill" in names
    assert "screenshot" in names
    assert "get_console_logs" in names
    assert "save_state" in names
    assert len(names) >= 25  # sanity check
