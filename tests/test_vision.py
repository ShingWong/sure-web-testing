"""tests/test_vision.py — Unit tests for the vision analysis module."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from src.vision import (
    GoogleVisionProvider,
    OpenAIVisionProvider,
    OpenRouterVisionProvider,
    VisionResult,
    get_provider,
)


class TestVisionProvider:
    def test_get_provider_google_default(self):
        """Default provider is Google when VISION_PROVIDER is unset."""
        with patch.dict(os.environ, {}, clear=True):
            provider = get_provider()
            assert isinstance(provider, GoogleVisionProvider)

    def test_get_provider_openai(self):
        with patch.dict(os.environ, {"VISION_PROVIDER": "openai"}, clear=True):
            provider = get_provider()
            assert isinstance(provider, OpenAIVisionProvider)

    def test_get_provider_explicit_name(self):
        provider = get_provider("google")
        assert isinstance(provider, GoogleVisionProvider)

    def test_get_provider_invalid(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown vision provider"):
            get_provider("nonexistent")

    def test_google_provider_uses_env_api_key(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"}, clear=True):
            p = GoogleVisionProvider()
            assert p.api_key == "test-key-123"
            assert p.model == "gemini-2.5-flash-lite"

    def test_google_provider_respects_vision_model(self):
        with patch.dict(os.environ, {"VISION_MODEL": "gemini-3-flash-preview"}, clear=True):
            p = GoogleVisionProvider()
            assert p.model == "gemini-3-flash-preview"

    def test_openai_provider_uses_env_api_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-123"}, clear=True):
            p = OpenAIVisionProvider()
            assert p.api_key == "sk-test-123"
            assert p.model == "gpt-4o"

    def test_openrouter_provider_defaults(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-test-key"}, clear=True):
            p = OpenRouterVisionProvider()
            assert p.api_key == "or-test-key"
            assert p.model == "qwen/qwen3.6-plus"
            assert "openrouter" in p.base_url

    def test_openrouter_provider_falls_back_to_vision_api_key(self):
        with patch.dict(os.environ, {"VISION_API_KEY": "shared-key"}, clear=True):
            p = OpenRouterVisionProvider()
            assert p.api_key == "shared-key"

    def test_get_provider_openrouter(self):
        with patch.dict(os.environ, {"VISION_PROVIDER": "openrouter"}, clear=True):
            provider = get_provider()
            assert isinstance(provider, OpenRouterVisionProvider)

    def test_vision_result_to_dict(self):
        r = VisionResult(provider="google", model="gemini-2.5-flash-lite", analysis="Form looks good.")
        d = r.to_dict()
        assert d["provider"] == "google"
        assert d["model"] == "gemini-2.5-flash-lite"
        assert d["analysis"] == "Form looks good."

    def test_analyze_image_tool_no_file(self):
        from src.browser import BrowserManager
        from src.tools import build_registry

        b = BrowserManager()
        reg = build_registry(b)
        result = reg.call_tool("analyze_image", {"path": "/nonexistent/image.png"})
        assert result.get("status") == "error"
        assert "not found" in result.get("error", "")

    def test_analyze_image_tool_no_api_key(self, tmp_path: Path):
        from src.browser import BrowserManager
        from src.tools import build_registry

        img = tmp_path / "test.png"
        img.write_bytes(b"fake-png-data")

        b = BrowserManager()
        with patch.dict(os.environ, {}, clear=True):
            reg = build_registry(b)
            result = reg.call_tool("analyze_image", {"path": str(img)})
            # Without API key, it'll try to import and fail with missing dep
            assert result.get("status") == "error"
