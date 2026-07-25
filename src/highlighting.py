"""src/highlighting.py — Element highlight injection matching IMS_tutorial style."""

HIGHLIGHT_STYLE = {
    "background": "rgba(255,180,0,0.20)",
    "border": "3px solid #ff8800",
    "border_radius": "3px",
    "box_shadow": "0 0 12px rgba(255,150,0,0.6)",
    "z_index": "999999",
    "pointer_events": "none",
}


class HighlightManager:
    def __init__(self, page):
        self._page = page
        self._element_id = "awt-highlight"

    def highlight(self, selector: str, color: str = "#ff8800") -> dict:
        r_ch, g_ch, b_ch = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        js = f"""(() => {{
            const el = document.querySelector('{selector.replace("'", "\\'")}');
            if (!el) return false;
            const box = el.getBoundingClientRect();
            let f = document.getElementById('{self._element_id}');
            if (!f) {{
                f = document.createElement('div');
                f.id = '{self._element_id}';
                document.body.appendChild(f);
            }}
            f.style.cssText = 'position:fixed;left:' + box.x + 'px;top:' + box.y + 'px;' +
                'width:' + box.width + 'px;height:' + box.height + 'px;' +
                'background:rgba({r_ch},{g_ch},{b_ch},0.20);' +
                'border:3px solid {color};z-index:999999;' +
                'pointer-events:none;border-radius:3px;' +
                'box-shadow:0 0 12px rgba({r_ch},{g_ch},{b_ch},0.6)';
            return true;
        }})()"""
        found = self._page.evaluate(js)
        return {"status": "ok" if found else "error", "data": {"found": found}}

    def clear(self) -> dict:
        self._page.evaluate(f"(()=>{{let o=document.getElementById('{self._element_id}');if(o)o.remove();}})()")
        return {"status": "ok", "data": {"ok": True}}
