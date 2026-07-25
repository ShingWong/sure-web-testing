"""tests/test_protocol.py"""
import io
import json

from src.protocol import JSONRPCError, JSONRPCRequest, JSONRPCResponse, read_message, write_message


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
