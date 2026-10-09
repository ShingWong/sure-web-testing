"""src/server.py — MCP server handling stdin/stdout JSON-RPC 2.0 protocol.

MCP conformance (OpenCode v2 negotiates properly; v1 tolerated shortcuts):
- initialize echoes a real date-string protocolVersion from the versions we
  speak — "0.1" is not an MCP version and a v2 client rejects the handshake.
- tools/list exposes JSON-Schema `inputSchema`, not the internal params map.
- ping is a required method; unknown methods still return -32601.
- tools/call sets isError when the tool reports a failure.
"""
import json
import sys
import traceback
from typing import Any

from src.protocol import JSONRPCError, JSONRPCRequest, JSONRPCResponse, read_message, write_message
from src.tools import ToolRegistry

# MCP protocol revisions this server speaks, oldest first. The handshake
# echoes the client's requested version when we support it (the spec's
# negotiation), else our newest.
MCP_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")

_TYPE_MAP = {
    "bool": "boolean", "int": "integer", "float": "number",
    "str": "string", "dict": "object", "list": "array",
}


def _input_schema(params: dict[str, str]) -> dict[str, Any]:
    """Internal params map -> MCP JSON Schema (fields marked optional are
    not required; the leading type token picks the JSON type)."""
    props: dict[str, Any] = {}
    required: list[str] = []
    for field, desc in params.items():
        text = str(desc)
        jtype = _TYPE_MAP.get(text.split(" ")[0].strip().lower(), "string")
        props[field] = {"type": jtype, "description": text}
        if "optional" not in text.lower():
            required.append(field)
    return {"type": "object", "properties": props, "required": required}


class MCPServer:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def handle_one(self, stdin, stdout) -> None:
        try:
            msg = read_message(stdin)
        except EOFError:
            raise  # let run()'s outer handler exit the loop
        except Exception as e:
            err = JSONRPCError(id=None, code=-32700, message="Parse error", data=str(e))
            write_message(stdout, err)
            return

        if isinstance(msg, JSONRPCError):
            write_message(stdout, msg)
            return

        req = msg
        assert isinstance(req, JSONRPCRequest), f"Expected JSONRPCRequest, got {type(req)}"

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
        except ValueError as e:
            err = JSONRPCError(id=req.id, code=-32601, message="Method not found", data=str(e))
            write_message(stdout, err)
        except Exception as e:
            err = JSONRPCError(id=req.id, code=-32603, message="Internal error", data=str(e))
            write_message(stdout, err)

    def _handle_method(self, method: str, params: dict[str, Any]) -> dict:
        if method == "initialize":
            asked = params.get("protocolVersion")
            version = asked if asked in MCP_PROTOCOL_VERSIONS else MCP_PROTOCOL_VERSIONS[-1]
            return {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "sure-web-testing", "version": "0.1.0"},
            }
        elif method == "ping":
            return {}
        elif method == "tools/list":
            tools = []
            for t in self._registry.list_tools():
                tools.append({
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": _input_schema(t.get("params", {})),
                    # v1-era clients read `params` directly for argument
                    # hints. Kept alongside inputSchema: extra keys are
                    # allowed and spec-compliant clients ignore them.
                    "params": t.get("params", {}),
                })
            return {"tools": tools}
        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self._registry.call_tool(name, arguments)
            content = []
            if "data" in result:
                data = result["data"]
                text = json.dumps(data) if not isinstance(data, str) else data
                content.append({"type": "text", "text": text})
            if "error" in result:
                content.append({"type": "text", "text": result["error"]})
            out: dict[str, Any] = {"content": content}
            if "error" in result:
                out["isError"] = True
            return out
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
