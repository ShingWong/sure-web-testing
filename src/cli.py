"""src/cli.py — Interactive REPL CLI for step-by-step browser testing."""
import shlex

from src.browser import BrowserManager


def format_result(result: dict) -> str:
    if result.get("status") == "error":
        return f"Error: {result.get('error', 'unknown error')}"
    data = result.get("data")
    if data is None:
        return "OK (no data)"
    if isinstance(data, list):
        lines = [f"  [{i}] {d}" for i, d in enumerate(data)]
        return f"OK — {len(data)} items:\n" + "\n".join(lines)
    if isinstance(data, dict):
        if "html" in data:
            html = data["html"]
            return f"DOM ({len(html)} chars)\n{html[:2000]}"
        if "data" in data and isinstance(data["data"], str) and len(data["data"]) > 100:
            return f"Screenshot captured ({len(data['data'])} bytes base64)"
        parts = [f"  {k}: {v}" for k, v in data.items() if v is not None]
        if len(parts) <= 3:
            return "OK — " + ", ".join(parts)
        return "OK\n" + "\n".join(parts)
    return f"OK — {data}"


def main():
    mgr = BrowserManager()
    print("Agentic Web Testing CLI")
    print("Type 'help' for commands, 'quit' to exit.")

    commands = {
        "launch": lambda args: mgr.launch(headless="--headed" not in args),
        "close": lambda args: mgr.close(),
        "goto": lambda args: mgr.goto(args[0]) if args else {"status": "error", "error": "Usage: goto <url>"},
        "screenshot": lambda args: mgr.screenshot(),
        "dom": lambda args: mgr.get_dom(),
        "click": lambda args: mgr.click(args[0]) if args else {"status": "error", "error": "Usage: click <selector>"},
        "fill": lambda args: mgr.fill(args[0], " ".join(args[1:])) if len(args) >= 2 else {"status": "error", "error": "Usage: fill <selector> <text>"},
        "info": lambda args: mgr.get_info(),
        "console": lambda args: mgr.get_console_logs(),
        "network": lambda args: mgr.get_network_requests(),
        "evaluate": lambda args: mgr.evaluate(" ".join(args)) if args else {"status": "error", "error": "Usage: evaluate <js>"},
        "highlight": lambda args: mgr.highlight_element(args[0]) if args else {"status": "error", "error": "Usage: highlight <selector>"},
        "clear": lambda args: mgr.clear_highlights(),
        "help": lambda args: print("Commands: launch, close, goto, screenshot, dom, click, fill, info,\n  console, network, evaluate, highlight, clear, help, quit"),
    }

    while True:
        try:
            line = input("awt> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line == "quit":
            break

        parts = shlex.split(line)
        cmd = parts[0]
        args = parts[1:]

        handler = commands.get(cmd)
        if not handler:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")
            continue

        try:
            result = handler(args)
            if result:
                print(format_result(result))
        except Exception as e:
            print(f"Error: {e}")

    mgr.close()
    print("Goodbye.")


if __name__ == "__main__":
    main()
