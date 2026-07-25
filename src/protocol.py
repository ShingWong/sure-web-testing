"""src/protocol.py — JSON-RPC 2.0 message types and stdin/stdout transport."""

import json
from dataclasses import asdict, dataclass
from typing import Any


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
