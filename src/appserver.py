"""src/appserver.py — session-lived application server lifecycle.

Ports `webapp-testing`'s with_server.py readiness pattern into the MCP
session: start the app under test, wait until its port accepts connections,
keep stdout/stderr in a log file (no PIPE deadlock), stop on request — and
stop everything when the MCP server exits (atexit wired in server.main).

Servers run in their own process group (`start_new_session=True`) so stop
can reap the whole tree — `sh -c "npm run dev"` would otherwise orphan its
node children.
"""
from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import tempfile
import time

_TAIL_BYTES = 16_384


class ServerManager:
    """Named child processes started by the start_server tool."""

    def __init__(self) -> None:
        self._servers: dict[str, dict] = {}
        self._counter = 0

    # ── public API (tool handlers return its dicts directly) ─────────

    def start(self, command: str, port: int | None = None, cwd: str | None = None,
              timeout: int = 30, name: str | None = None) -> dict:
        if not name:
            self._counter += 1
            name = f"server-{self._counter}"
        existing = self._servers.get(name)
        if existing and existing["proc"].poll() is None:
            return {"status": "error",
                    "error": f"'{name}' is already running (pid {existing['proc'].pid}); stop it first"}

        safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        fd, log_path = tempfile.mkstemp(prefix=f"swt-server-{safe}-", suffix=".log")
        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=fd,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                # Log capture is the point of the log file — without this,
                # python children block-buffer stdout to a file and their
                # output (e.g. http.server's "Serving HTTP" banner) doesn't
                # appear until the process exits. Harmless for other runtimes.
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except Exception as e:
            os.close(fd)
            try:
                os.unlink(log_path)
            except OSError:
                pass
            return {"status": "error", "error": f"failed to start: {e}"}
        finally:
            os.close(fd)

        entry = {"proc": proc, "command": command, "port": port, "log": log_path,
                 "started": time.time()}
        self._servers[name] = entry

        # No port → can't poll readiness; brief grace period so an instant
        # crash (bad cwd, missing binary) still surfaces as an error here.
        if port is None:
            time.sleep(0.3)
            rc = proc.poll()
            if rc is not None:
                self._servers.pop(name, None)
                return {"status": "error",
                        "error": f"'{name}' exited rc={rc} immediately; log tail:\n{self._tail(log_path)}"}
            return {"status": "ok",
                    "data": {"name": name, "pid": proc.pid, "ready": None,
                             "note": "no port given — readiness not checked", "log": log_path}}

        deadline = time.time() + timeout
        while time.time() < deadline:
            rc = proc.poll()
            if rc is not None:
                self._servers.pop(name, None)
                return {"status": "error",
                        "error": f"'{name}' exited rc={rc} during startup; log tail:\n{self._tail(log_path)}"}
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    return {"status": "ok",
                            "data": {"name": name, "pid": proc.pid, "port": port,
                                     "ready": True, "log": log_path}}
            except OSError:
                time.sleep(0.3)

        # Readiness timeout: kill the half-started server so retries are clean,
        # and hand back the log tail — that's where the real cause lives.
        self._terminate(entry)
        self._servers.pop(name, None)
        return {"status": "error",
                "error": (f"'{name}' did not accept connections on port {port} within "
                          f"{timeout}s — stopped. Log tail:\n{self._tail(log_path)}")}

    def stop(self, name: str | None = None) -> dict:
        if name is None:
            return self.stop_all()
        entry = self._servers.pop(name, None)
        if entry is None:
            known = ", ".join(self._servers) or "(none)"
            return {"status": "error", "error": f"no server named '{name}'; known: {known}"}
        rc = self._terminate(entry)
        return {"status": "ok", "data": {"name": name, "returncode": rc}}

    def stop_all(self) -> dict:
        stopped = []
        for name in list(self._servers):
            entry = self._servers.pop(name)
            stopped.append({"name": name, "returncode": self._terminate(entry)})
        return {"status": "ok", "data": {"stopped": stopped}}

    def list_servers(self) -> dict:
        rows = []
        for name, entry in self._servers.items():
            rc = entry["proc"].poll()
            rows.append({
                "name": name,
                "command": entry["command"],
                "pid": entry["proc"].pid,
                "port": entry["port"],
                "running": rc is None,
                "returncode": rc,
                "uptime_s": round(time.time() - entry["started"]),
                "log": entry["log"],
            })
        return {"status": "ok", "data": {"servers": rows}}

    def logs(self, name: str, tail: int = 50) -> dict:
        entry = self._servers.get(name)
        if entry is None:
            known = ", ".join(self._servers) or "(none)"
            return {"status": "error", "error": f"no server named '{name}'; known: {known}"}
        lines = self._tail(entry["log"], lines=tail).splitlines()
        return {"status": "ok",
                "data": {"name": name, "log": entry["log"], "lines": lines}}

    # ── internals ────────────────────────────────────────────────────

    @staticmethod
    def _tail(path: str, lines: int = 40) -> str:
        try:
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - _TAIL_BYTES))
                chunk = f.read().decode("utf-8", errors="replace")
        except OSError:
            return "(no log)"
        return "\n".join(chunk.splitlines()[-lines:])

    @staticmethod
    def _terminate(entry: dict) -> int | None:
        """SIGTERM the process group, escalate to SIGKILL after 5s."""
        proc = entry["proc"]
        if proc.poll() is not None:
            return proc.returncode
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            return proc.poll()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)
        return proc.returncode
