"""src/server.py — MCP server handling stdin/stdout JSON-RPC 2.0 protocol."""
import json
import sys
import traceback
from typing import Any

from src.protocol import JSONRPCError, JSONRPCRequest, JSONRPCResponse, read_message, write_message
from src.tools import ToolRegistry


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
                data = result["data"]
                text = json.dumps(data) if not isinstance(data, str) else data
                content.append({"type": "text", "text": text})
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
