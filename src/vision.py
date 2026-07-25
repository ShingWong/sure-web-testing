"""src/vision.py — Provider-agnostic visual analysis for screenshots.

Configure via environment variables:
  VISION_PROVIDER  = "google" | "openai" | "openrouter" (default: "google")
  VISION_API_KEY   = API key for the chosen provider
  VISION_MODEL     = Model name override (default: provider-specific)
"""
from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from typing import ClassVar


class VisionResult:
    def __init__(self, provider: str, model: str, analysis: str):
        self.provider = provider
        self.model = model
        self.analysis = analysis

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "analysis": self.analysis,
        }


class VisionProvider(ABC):
    @abstractmethod
    def analyze(self, image_data: bytes, prompt: str) -> VisionResult:
        ...


class GoogleVisionProvider(VisionProvider):
    name: ClassVar[str] = "google"

    def __init__(self) -> None:
        self.api_key = os.environ.get("VISION_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        self.model = os.environ.get("VISION_MODEL") or "gemini-2.5-flash-lite"

    def analyze(self, image_data: bytes, prompt: str) -> VisionResult:
        from google import genai

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=[prompt, image_data],
        )
        return VisionResult(
            provider=self.name,
            model=self.model,
            analysis=response.text or "",
        )


class OpenAICompatibleProvider(VisionProvider):
    """Base for any OpenAI-compatible API (OpenAI, OpenRouter, Together, etc.)."""

    name: ClassVar[str] = "openai-compatible"
    _api_key_env: ClassVar[str] = ""
    _default_model: ClassVar[str] = ""
    _default_base_url: ClassVar[str] = ""

    def __init__(self) -> None:
        self.api_key = (
            os.environ.get("VISION_API_KEY")
            or os.environ.get(self._api_key_env, "")
        )
        self.model = os.environ.get("VISION_MODEL") or self._default_model
        self.base_url = os.environ.get("VISION_BASE_URL") or self._default_base_url

    def analyze(self, image_data: bytes, prompt: str) -> VisionResult:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        b64 = base64.b64encode(image_data).decode("utf-8")
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )
        return VisionResult(
            provider=self.name,
            model=self.model,
            analysis=response.choices[0].message.content or "",
        )


class OpenAIVisionProvider(OpenAICompatibleProvider):
    name: ClassVar[str] = "openai"
    _api_key_env: ClassVar[str] = "OPENAI_API_KEY"
    _default_model: ClassVar[str] = "gpt-4o"
    _default_base_url: ClassVar[str] = "https://api.openai.com/v1"


class OpenRouterVisionProvider(OpenAICompatibleProvider):
    name: ClassVar[str] = "openrouter"
    _api_key_env: ClassVar[str] = "OPENROUTER_API_KEY"
    _default_model: ClassVar[str] = "qwen/qwen3.6-plus"
    _default_base_url: ClassVar[str] = "https://openrouter.ai/api/v1"


_PROVIDERS: dict[str, type[VisionProvider]] = {
    "google": GoogleVisionProvider,
    "openai": OpenAIVisionProvider,
    "openrouter": OpenRouterVisionProvider,
}


def get_provider(name: str | None = None) -> VisionProvider:
    name = (name or os.environ.get("VISION_PROVIDER") or "google").lower()
    cls = _PROVIDERS.get(name)
    if not cls:
        available = ", ".join(_PROVIDERS)
        raise ValueError(f"Unknown vision provider '{name}'. Available: {available}")
    return cls()


DEFAULT_ANALYSIS_PROMPT = """Analyze this screenshot of a web form. Verify:
1. Is the form title visible?
2. Are all expected input fields present with labels?
3. Is help text visible for each field?
4. Is the submit button visible?
5. Are there any visual issues or errors displayed?

Return structured PASS/FAIL verdict for each check, plus overall verdict."""
