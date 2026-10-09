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
    # The v1 answer was "0.1" — not an MCP protocol version; an opencode v2
    # client negotiates properly and rejects the handshake. With no version
    # requested the server offers its newest supported date-string version.
    assert parsed["result"]["protocolVersion"] == "2025-06-18"
    assert parsed["result"]["capabilities"]["tools"]["listChanged"] is False


def test_initialize_echoes_client_version():
    """A client asking for a version we speak gets it echoed back."""
    reg = ToolRegistry()
    server = MCPServer(reg)
    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":9,"method":"initialize",'
        '"params":{"protocolVersion":"2024-11-05"}}\n'
    )
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    parsed = json.loads(stdout.getvalue())
    assert parsed["result"]["protocolVersion"] == "2024-11-05"


def test_initialize_unknown_version_does_not_echo():
    """The old "0.1" (or any version we do not speak) must never come back —
    we answer with our newest supported version instead."""
    reg = ToolRegistry()
    server = MCPServer(reg)
    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":10,"method":"initialize",'
        '"params":{"protocolVersion":"0.1"}}\n'
    )
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    parsed = json.loads(stdout.getvalue())
    assert parsed["result"]["protocolVersion"] == "2025-06-18"


def test_ping():
    """ping is a required MCP method; unknown methods stay -32601."""
    reg = ToolRegistry()
    server = MCPServer(reg)
    stdin = io.StringIO('{"jsonrpc":"2.0","id":11,"method":"ping"}\n')
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    parsed = json.loads(stdout.getvalue())
    assert parsed["result"] == {}

    stdin = io.StringIO('{"jsonrpc":"2.0","id":12,"method":"resources/list"}\n')
    stdout = io.StringIO()
    server.handle_one(stdin, stdout)
    parsed = json.loads(stdout.getvalue())
    assert parsed["error"]["code"] == -32601


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
    reg.register("echo", "Echo input", {"msg": "str"}, lambda p: {"status": "ok", "data": p["msg"]})
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
