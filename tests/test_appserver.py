"""tests/test_appserver.py — ServerManager lifecycle."""
import os
import socket
import sys
import time

from src.appserver import ServerManager


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


class TestServerManager:
    def test_start_ready_stop(self):
        """Start → port accepts connections → stop kills it."""
        port = _free_port()
        sm = ServerManager()
        try:
            r = sm.start(f"{sys.executable} -m http.server {port} --bind 127.0.0.1",
                         port=port, timeout=15)
            assert r["status"] == "ok", r
            assert r["data"]["ready"] is True
            assert r["data"]["pid"] > 0

            listed = sm.list_servers()["data"]["servers"]
            assert len(listed) == 1
            assert listed[0]["running"] is True
            assert listed[0]["port"] == port

            stop = sm.stop(r["data"]["name"])
            assert stop["status"] == "ok"
            # Port must be released
            time.sleep(0.2)
            with socket.socket() as s:
                s.settimeout(0.5)
                assert s.connect_ex(("127.0.0.1", port)) != 0
        finally:
            sm.stop_all()

    def test_readiness_timeout_kills_and_returns_log(self):
        """A command that never opens the port → error + killed, no orphan."""
        port = _free_port()
        sm = ServerManager()
        r = sm.start(f"{sys.executable} -c 'import time; time.sleep(60)'",
                     port=port, timeout=2)
        assert r["status"] == "error"
        assert "did not accept connections" in r["error"]
        assert "Log tail" in r["error"]
        # entry cleaned up, process reaped
        assert sm.list_servers()["data"]["servers"] == []
        assert _wait(port, timeout=0.3) is False

    def test_crash_on_startup_surfaces_log(self):
        """Nonexistent command → immediate error with log, not a hung wait."""
        sm = ServerManager()
        r = sm.start("definitely-not-a-real-binary-xyz", timeout=5, name="crashy")
        assert r["status"] == "error"
        assert "crashy" in r["error"]
        assert sm.list_servers()["data"]["servers"] == []

    def test_no_port_grace_period(self):
        """port omitted → readiness unchecked, but instant crash still errors."""
        sm = ServerManager()
        ok = sm.start(f"{sys.executable} -c 'import time; time.sleep(30)'")
        assert ok["status"] == "ok"
        assert ok["data"]["ready"] is None

        bad = sm.start("definitely-not-a-real-binary-xyz", name="crash2")
        assert bad["status"] == "error"

        assert sm.stop_all()["data"]["stopped"]
        assert sm.list_servers()["data"]["servers"] == []

    def test_duplicate_name_rejected(self):
        sm = ServerManager()
        r = sm.start(f"{sys.executable} -c 'import time; time.sleep(30)'", name="dup")
        assert r["status"] == "ok"
        again = sm.start(f"{sys.executable} -c 'import time; time.sleep(30)'", name="dup")
        assert again["status"] == "error"
        assert "already running" in again["error"]
        sm.stop_all()

    def test_stop_unknown_name(self):
        sm = ServerManager()
        r = sm.stop("ghost")
        assert r["status"] == "error"
        assert "no server named" in r["error"]

    def test_logs_tailing(self):
        port = _free_port()
        sm = ServerManager()
        try:
            r = sm.start(f"{sys.executable} -m http.server {port} --bind 127.0.0.1",
                         port=port, timeout=15)
            assert r["status"] == "ok", r
            # http.server logs "Serving HTTP..." to stderr on start
            time.sleep(0.5)
            logs = sm.logs(r["data"]["name"], tail=10)
            assert logs["status"] == "ok"
            assert any("Serving HTTP" in ln for ln in logs["data"]["lines"]), logs
        finally:
            sm.stop_all()

    def test_stop_all_reaps_process_group(self):
        """Children of the shell must die with it (process-group kill)."""
        sm = ServerManager()
        r = sm.start(f"{sys.executable} -c 'import time; time.sleep(45)'", name="grp")
        assert r["status"] == "ok"
        pid = r["data"]["pid"]
        sm.stop_all()
        # Process must be gone (zombie reaped by wait() inside _terminate)
        gone = False
        for _ in range(20):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                gone = True
                break
            time.sleep(0.1)
        assert gone, f"pid {pid} still alive after stop_all"


class TestRegistryIntegration:
    def test_server_tools_registered_when_manager_passed(self):
        from src.browser import BrowserManager
        from src.tools import build_registry

        sm = ServerManager()
        reg = build_registry(BrowserManager(), sm)
        names = [t["name"] for t in reg.list_tools()]
        for expected in ("start_server", "stop_server", "list_servers", "server_logs"):
            assert expected in names

    def test_server_tools_absent_without_manager(self):
        """CLI/tests that pass only a browser keep the old 29-tool surface."""
        from src.browser import BrowserManager
        from src.tools import build_registry

        reg = build_registry(BrowserManager())
        names = [t["name"] for t in reg.list_tools()]
        assert "start_server" not in names

    def test_start_server_tool_call(self):
        from src.browser import BrowserManager
        from src.tools import build_registry

        sm = ServerManager()
        reg = build_registry(BrowserManager(), sm)
        port = _free_port()
        r = reg.call_tool("start_server", {
            "command": f"{sys.executable} -m http.server {port} --bind 127.0.0.1",
            "port": port, "timeout": 15,
        })
        assert r["status"] == "ok", r
        listed = reg.call_tool("list_servers", {})
        assert listed["data"]["servers"][0]["running"] is True
        stop = reg.call_tool("stop_server", {"name": r["data"]["name"]})
        assert stop["status"] == "ok"
