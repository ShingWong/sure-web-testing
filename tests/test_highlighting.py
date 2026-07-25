"""tests/test_highlighting.py"""
from src.highlighting import HIGHLIGHT_STYLE


def test_style_constants():
    assert "rgba(255,180,0,0.20)" in HIGHLIGHT_STYLE["background"]
    assert "#ff8800" in HIGHLIGHT_STYLE["border"]
