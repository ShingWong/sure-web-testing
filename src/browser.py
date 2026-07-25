"""src/browser.py — Manages a persistent Playwright browser session."""
import base64
import json
import os
import tempfile
import time
from uuid import uuid4

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}


class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._session_id: str | None = None
        self._console_logs: list[dict] = []
        self._network_requests: list[dict] = []
        self._recording: bool = False
        self._video_path: str | None = None
        self._states: dict[str, str] = {}

    def _ensure_session(self):
        if not self._browser or not self._page:
            raise RuntimeError("No active session. Call launch() first.")

    def launch(self, headless: bool = True, viewport: dict | None = None,
               record_video: bool = False) -> dict:
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=headless)
            self._recording = record_video
            self._context = self._browser.new_context(
                viewport=viewport or DEFAULT_VIEWPORT,
                record_video_dir=os.path.abspath("./recordings") if self._recording else None,
            )
            self._page = self._context.new_page()
            self._session_id = str(uuid4())

            self._page.on("console", lambda msg: self._console_logs.append({
                "level": msg.type,
                "text": msg.text,
                "source": msg.location.get("url", "") if isinstance(msg.location, dict) else str(msg.location) if hasattr(msg, "location") else "",
                "timestamp": time.time(),
            }))

            self._page.on("request", lambda req: self._network_requests.append({
                "url": req.url,
                "method": req.method,
                "type": req.resource_type,
                "timestamp": time.time(),
            }))

            self._page.on("response", lambda res: self._network_requests.append({
                "url": res.url,
                "method": res.request.method,
                "status": res.status,
                "type": res.request.resource_type,
                "timestamp": time.time(),
            }))

            return {"status": "ok", "data": {"session_id": self._session_id}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def close(self) -> dict:
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            self._browser = None
            self._context = None
            self._page = None
            self._session_id = None
            self._console_logs = []
            self._network_requests = []
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def start_video_recording(self, path: str | None = None) -> dict:
        try:
            self._ensure_session()
            self._recording = True
            self._video_path = path
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def stop_video_recording(self) -> dict:
        try:
            self._ensure_session()
            video = self._page.video
            if video:
                video_path = video.path()
                return {"status": "ok", "data": {"video_path": video_path}}
            return {"status": "error", "error": "No video recording in progress"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def goto(self, url: str, wait_until: str = "networkidle") -> dict:
        try:
            self._ensure_session()
            self._page.goto(url, wait_until=wait_until)
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e), "data": {"url": self._page.url if self._page else "", "title": self._page.title() if self._page else ""}}

    def reload(self) -> dict:
        try:
            self._ensure_session()
            self._page.reload()
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def go_back(self) -> dict:
        try:
            self._ensure_session()
            self._page.go_back()
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def go_forward(self) -> dict:
        try:
            self._ensure_session()
            self._page.go_forward()
            return {"status": "ok", "data": {"url": self._page.url, "title": self._page.title()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_info(self) -> dict:
        try:
            self._ensure_session()
            return {"status": "ok", "data": {
                "url": self._page.url,
                "title": self._page.title(),
                "load_state": "loaded",
            }}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_dom(self, selector: str | None = None) -> dict:
        try:
            self._ensure_session()
            if selector:
                els = self._page.locator(selector)
                if els.count() == 0:
                    return {"status": "ok", "data": {"html": ""}}
                html = els.first.inner_html()
            else:
                html = self._page.content()
            return {"status": "ok", "data": {"html": html}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def query_elements(self, selector: str) -> dict:
        try:
            self._ensure_session()
            els = self._page.locator(selector)
            count = els.count()
            results = []
            for i in range(min(count, 50)):
                el = els.nth(i)
                try:
                    visible = el.is_visible()
                except Exception:
                    visible = False
                try:
                    box = el.bounding_box()
                    rect = {"x": round(box["x"]), "y": round(box["y"]), "w": round(box["width"]), "h": round(box["height"])} if box else None
                except Exception:
                    rect = None
                results.append({
                    "tag": el.evaluate("el => el.tagName.toLowerCase()", timeout=1000) if count > 0 else "",
                    "text": el.text_content(timeout=1000) or "",
                    "visible": visible,
                    "rect": rect,
                })
            return {"status": "ok", "data": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def click(self, selector: str, timeout: int = 10000) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            self._page.locator(selector).first.click()
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def fill(self, selector: str, text: str, timeout: int = 10000) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            self._page.locator(selector).first.fill(text)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def press(self, selector: str, key: str) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.press(key)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def select_option(self, selector: str, value: str) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.select_option(value)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def hover(self, selector: str) -> dict:
        try:
            self._ensure_session()
            self._page.locator(selector).first.hover()
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def evaluate(self, script: str) -> dict:
        try:
            self._ensure_session()
            result = self._page.evaluate(script)
            return {"status": "ok", "data": {"result": result}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def screenshot(self, path: str | None = None, full_page: bool = False,
                   highlight: str | None = None, highlight_color: str | None = None) -> dict:
        try:
            self._ensure_session()
            if highlight:
                self._highlight_element(highlight, highlight_color or "#ff8800")
            path = path or os.path.join(tempfile.gettempdir(), f"awt_{uuid4().hex}.png")
            self._page.screenshot(path=path, full_page=full_page)
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            if highlight:
                self._clear_highlights()
            return {"status": "ok", "data": {"path": path, "data": data}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _highlight_element(self, selector: str, color: str = "#ff8800"):
        self._clear_highlights()
        r_ch, g_ch, b_ch = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        escaped = selector.replace("'", "\\'")
        js = f"""(() => {{
            const el = document.querySelector('{escaped}');
            if (!el) return;
            const rect = el.getBoundingClientRect();
            let f = document.getElementById('awt-highlight');
            if (!f) {{
                f = document.createElement('div');
                f.id = 'awt-highlight';
                document.body.appendChild(f);
            }}
            f.style.cssText = 'position:fixed;left:' + rect.x + 'px;top:' + rect.y + 'px;' +
                'width:' + rect.width + 'px;height:' + rect.height + 'px;' +
                'background:rgba({r_ch},{g_ch},{b_ch},0.20);' +
                'border:3px solid {color};z-index:999999;' +
                'pointer-events:none;border-radius:3px;' +
                'box-shadow:0 0 12px rgba({r_ch},{g_ch},{b_ch},0.6)';
        }})()"""
        self._page.evaluate(js)

    def _clear_highlights(self):
        self._page.evaluate("(()=>{let o=document.getElementById('awt-highlight');if(o)o.remove();})()")

    def highlight_element(self, selector: str, color: str = "#ff8800") -> dict:
        try:
            self._ensure_session()
            self._highlight_element(selector, color)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clear_highlights(self) -> dict:
        try:
            self._ensure_session()
            self._clear_highlights()
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_text(self, selector: str) -> dict:
        try:
            self._ensure_session()
            text = self._page.locator(selector).first.text_content(timeout=5000) or ""
            return {"status": "ok", "data": {"text": text.strip()}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_attribute(self, selector: str, attr: str) -> dict:
        try:
            self._ensure_session()
            val = self._page.locator(selector).first.get_attribute(attr, timeout=5000)
            return {"status": "ok", "data": {"value": val}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def wait_for(self, selector: str | None = None, timeout: int = 10000) -> dict:
        try:
            self._ensure_session()
            if selector:
                self._page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            else:
                self._page.wait_for_load_state("networkidle", timeout=timeout)
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_console_logs(self) -> dict:
        return {"status": "ok", "data": list(self._console_logs)}

    def get_network_requests(self) -> dict:
        return {"status": "ok", "data": list(self._network_requests)}

    def clear_console_logs(self) -> dict:
        self._console_logs = []
        return {"status": "ok", "data": {"ok": True}}

    def clear_network_requests(self) -> dict:
        self._network_requests = []
        return {"status": "ok", "data": {"ok": True}}

    def save_state(self, name: str) -> dict:
        try:
            self._ensure_session()
            state_path = os.path.join(tempfile.gettempdir(), f"awt_state_{name}.json")
            self._context.storage_state(path=state_path)
            self._states[name] = state_path
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def load_state(self, name: str) -> dict:
        try:
            self._ensure_session()
            if name not in self._states:
                return {"status": "error", "error": f"State '{name}' not found"}
            state_path = self._states[name]
            with open(state_path) as f:
                state = json.load(f)
            if "cookies" in state:
                self._context.add_cookies(state["cookies"])
            return {"status": "ok", "data": {"ok": True}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_states(self) -> dict:
        return {"status": "ok", "data": [{"name": k} for k in self._states]}

    def get_page(self) -> Page:
        self._ensure_session()
        return self._page
