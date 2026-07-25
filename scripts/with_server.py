#!/usr/bin/env python3
"""Manage MCP server lifecycle: start, stop, restart, status.

Usage:
    python scripts/with_server.py start
    python scripts/with_server.py stop
    python scripts/with_server.py restart
    python scripts/with_server.py status
"""
import argparse
import os
import signal
import subprocess
import sys
import time


PID_FILE = "/tmp/awt-server.pid"
LOG_FILE = "/tmp/awt-server.log"


def start():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if os.path.exists(f"/proc/{pid}"):
            print(f"Server already running (PID {pid})")
            return
    with open(LOG_FILE, "w") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.server"],
            stdout=log, stderr=log,
        )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    time.sleep(0.5)
    if proc.poll() is None:
        print(f"Server started (PID {proc.pid})")
    else:
        print("Server failed to start")
        sys.exit(1)


def stop():
    if not os.path.exists(PID_FILE):
        print("No PID file found")
        return
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        os.unlink(PID_FILE)
        print(f"Server stopped (PID {pid})")
    except ProcessLookupError:
        os.unlink(PID_FILE)
        print("Server not running")


def status():
    if not os.path.exists(PID_FILE):
        print("Server not running")
        return
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    if os.path.exists(f"/proc/{pid}"):
        print(f"Server running (PID {pid})")
    else:
        print("PID file exists but process not found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agentic Web Testing server lifecycle")
    parser.add_argument("command", choices=["start", "stop", "restart", "status"])
    args = parser.parse_args()

    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "restart":
        stop()
        time.sleep(1)
        start()
    elif args.command == "status":
        status()
