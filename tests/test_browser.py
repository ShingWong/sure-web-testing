from src.browser import BrowserManager


def test_launch_and_close():
    mgr = BrowserManager()
    result = mgr.launch(headless=True)
    assert result["status"] == "ok"
    assert "session_id" in result["data"]
    result = mgr.close()
    assert result["status"] == "ok"


def test_goto():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    result = mgr.goto("about:blank")
    assert result["status"] == "ok"
    assert "about:blank" in result["data"]["url"]
    mgr.close()


def test_get_info():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("about:blank")
    info = mgr.get_info()
    assert info["status"] == "ok"
    assert "title" in info["data"]
    mgr.close()


def test_screenshot():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("about:blank")
    result = mgr.screenshot()
    assert result["status"] == "ok"
    assert len(result["data"]["data"]) > 0  # base64 data
    mgr.close()


def test_get_dom():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("data:text/html,<h1>Hello</h1>")
    dom = mgr.get_dom()
    assert "Hello" in dom["data"]["html"]
    dom = mgr.get_dom("h1")
    assert "Hello" in dom["data"]["html"]
    mgr.close()


def test_click_and_fill():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("data:text/html,<input id='a'><button id='b'>Go</button>")
    r = mgr.fill("#a", "hello")
    assert r["status"] == "ok"
    r = mgr.click("#b")
    assert r["status"] == "ok"
    mgr.close()


def test_console_logs():
    mgr = BrowserManager()
    mgr.launch(headless=True)
    mgr.goto("data:text/html,<script>console.log('test message')</script>")
    mgr.wait_for(timeout=1000)
    logs = mgr.get_console_logs()
    assert len(logs["data"]) > 0
    assert "test message" in logs["data"][0]["text"]
    mgr.close()


def test_no_session_error():
    mgr = BrowserManager()
    result = mgr.goto("about:blank")
    assert result["status"] == "error"
    assert "session" in result["error"].lower()
