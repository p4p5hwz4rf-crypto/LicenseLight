"""
Unified AI client — supports Claude, OpenAI, DeepSeek, Gemini, and Kimi.

Supports both server-side (.env) and per-request (BYOK) API keys.
Per-request keys take precedence over server config.

Provider capabilities:
  - Claude:  vision + text (best font detection)
  - OpenAI:  vision + text (GPT-4o / GPT-4o-mini)
  - DeepSeek: text only (cheapest, best Chinese summaries)
  - Gemini:  vision + text (free tier available)
  - Kimi:    vision + text (Moonshot, cheap, excellent Chinese)

Usage:
  from app.services.ai_client import call_ai_with_image, call_ai_text, is_ai_available
"""

import base64
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _get_config():
    from app.core.config import get_settings
    return get_settings()


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _media_type(image_path: str) -> str:
    ext = image_path.lower().rsplit(".", 1)[-1]
    return {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "webp": "image/webp", "gif": "image/gif",
    }.get(ext, "image/png")


def _parse_json_response(text: str) -> dict:
    """Extract JSON from an AI response (handles markdown fences)."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"Could not parse JSON from AI response: {text[:200]}")


# ── Claude ────────────────────────────────────────────────────────────────────

def _claude_vision(api_key: str, image_path: str, prompt: str,
                   model: str = "", max_tokens: int = 4096,
                   temperature: float = 0.3) -> str:
    from anthropic import Anthropic
    cfg = _get_config()
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model or cfg.CLAUDE_MODEL,
        max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64", "media_type": _media_type(image_path),
                "data": _encode_image(image_path)}},
            {"type": "text", "text": prompt},
        ]}],
    )
    return msg.content[0].text


def _claude_text(api_key: str, prompt: str, model: str = "",
                 max_tokens: int = 4096, temperature: float = 0.3) -> str:
    from anthropic import Anthropic
    cfg = _get_config()
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model or cfg.CLAUDE_MODEL,
        max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _openai_vision(api_key: str, image_path: str, prompt: str,
                   model: str = "", max_tokens: int = 4096,
                   temperature: float = 0.3) -> str:
    from openai import OpenAI
    cfg = _get_config()
    client = OpenAI(api_key=api_key, base_url=os.environ.get("OPENAI_BASE_URL"), timeout=30.0, max_retries=1)
    resp = client.chat.completions.create(
        model=model or cfg.OPENAI_MODEL,
        max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {
                "url": f"data:{_media_type(image_path)};base64,{_encode_image(image_path)}",
                "detail": "high"}},
            {"type": "text", "text": prompt},
        ]}],
    )
    return resp.choices[0].message.content or ""


def _openai_text(api_key: str, prompt: str, model: str = "",
                 max_tokens: int = 4096, temperature: float = 0.3) -> str:
    from openai import OpenAI
    cfg = _get_config()
    client = OpenAI(api_key=api_key, base_url=os.environ.get("OPENAI_BASE_URL"), timeout=30.0, max_retries=1)
    resp = client.chat.completions.create(
        model=model or cfg.OPENAI_TEXT_MODEL,
        max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# ── DeepSeek ──────────────────────────────────────────────────────────────────

def _deepseek_vision(api_key: str, image_path: str, prompt: str,
                     model: str = "", max_tokens: int = 4096,
                     temperature: float = 0.3) -> str:
    """DeepSeek doesn't support vision — always raises to trigger fallback."""
    raise NotImplementedError("DeepSeek does not support image/vision analysis")


def _deepseek_text(api_key: str, prompt: str, model: str = "",
                   max_tokens: int = 4096, temperature: float = 0.3) -> str:
    from openai import OpenAI
    cfg = _get_config()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com", timeout=30.0, max_retries=1)
    resp = client.chat.completions.create(
        model=model or cfg.DEEPSEEK_MODEL,
        max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# ── Gemini ────────────────────────────────────────────────────────────────────

def _gemini_vision(api_key: str, image_path: str, prompt: str,
                   model: str = "", max_tokens: int = 4096,
                   temperature: float = 0.3) -> str:
    import google.generativeai as genai
    import PIL.Image
    cfg = _get_config()
    genai.configure(api_key=api_key)
    img = PIL.Image.open(image_path)
    gen_model = genai.GenerativeModel(model or cfg.GEMINI_MODEL)
    resp = gen_model.generate_content(
        [prompt, img],
        generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
    )
    return resp.text or ""


def _gemini_text(api_key: str, prompt: str, model: str = "",
                 max_tokens: int = 4096, temperature: float = 0.3) -> str:
    import google.generativeai as genai
    cfg = _get_config()
    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(model or cfg.GEMINI_MODEL)
    resp = gen_model.generate_content(
        prompt,
        generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
    )
    return resp.text or ""


# ── Kimi / Moonshot ───────────────────────────────────────────────────────────

def _kimi_vision(api_key: str, image_path: str, prompt: str,
                 model: str = "", max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
    from openai import OpenAI
    cfg = _get_config()
    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1", timeout=30.0, max_retries=1)
    resp = client.chat.completions.create(
        model=model or cfg.KIMI_VISION_MODEL,
        max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {
                "url": f"data:{_media_type(image_path)};base64,{_encode_image(image_path)}",
                "detail": "high"}},
            {"type": "text", "text": prompt},
        ]}],
    )
    return resp.choices[0].message.content or ""


def _kimi_text(api_key: str, prompt: str, model: str = "",
               max_tokens: int = 4096, temperature: float = 0.3) -> str:
    from openai import OpenAI
    cfg = _get_config()
    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1", timeout=30.0, max_retries=1)
    resp = client.chat.completions.create(
        model=model or cfg.KIMI_MODEL,
        max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# ── Router ────────────────────────────────────────────────────────────────────

PROVIDERS = {
    "claude":  {"vision": _claude_vision,  "text": _claude_text},
    "openai":  {"vision": _openai_vision,  "text": _openai_text},
    "deepseek":{"vision": _deepseek_vision,"text": _deepseek_text},
    "gemini":  {"vision": _gemini_vision,  "text": _gemini_text},
    "kimi":    {"vision": _kimi_vision,    "text": _kimi_text},
}


def _env_api_key(provider: str = "") -> str:
    """Get the configured API key from .env for a provider."""
    cfg = _get_config()
    key_map = {
        "claude": cfg.CLAUDE_API_KEY,
        "openai": cfg.OPENAI_API_KEY,
        "deepseek": cfg.DEEPSEEK_API_KEY,
        "gemini": cfg.GEMINI_API_KEY,
        "kimi": cfg.KIMI_API_KEY,
    }
    return key_map.get(provider, "")


# ── Public API ────────────────────────────────────────────────────────────────


def is_ai_available(api_key: str = "", provider: str = "") -> bool:
    """Check if any AI provider is available (BYOK key or .env key)."""
    if api_key:
        return True
    cfg = _get_config()
    return bool(_env_api_key(provider or cfg.AI_PROVIDER))


def supports_vision(provider: str = "") -> bool:
    """Check if the given provider supports image/vision analysis."""
    cfg = _get_config()
    p = provider or cfg.AI_PROVIDER
    return p in ("claude", "openai", "gemini", "kimi")


def call_ai_with_image(
    api_key: str,
    image_path: str,
    prompt: str,
    provider: str = "",
    model: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Send an image + text prompt to the configured AI provider.

    Args:
        api_key: User-provided API key (BYOK). If empty, falls back to .env config.
        provider: Override the AI provider. If empty, uses .env AI_PROVIDER.
    """
    cfg = _get_config()
    effective_provider = provider or cfg.AI_PROVIDER
    effective_api_key = api_key or _env_api_key(effective_provider)

    if effective_provider not in PROVIDERS:
        raise ValueError(
            f"Unknown AI provider: {effective_provider}. "
            f"Choose: claude, openai, deepseek, gemini, kimi"
        )

    try:
        return PROVIDERS[effective_provider]["vision"](
            api_key=effective_api_key, image_path=image_path, prompt=prompt,
            model=model, max_tokens=max_tokens, temperature=temperature,
        )
    except NotImplementedError:
        logger.info(
            f"{effective_provider} does not support vision; "
            f"use Claude/OpenAI/Gemini/Kimi for font detection"
        )
        raise
    except ImportError as e:
        pkg = {
            "claude": "anthropic", "openai": "openai", "deepseek": "openai",
            "gemini": "google-generativeai", "kimi": "openai",
        }.get(effective_provider, "unknown")
        logger.error(f"Missing package for {effective_provider}: {e}. pip install {pkg}")
        raise
    except Exception as e:
        logger.error(f"{effective_provider} vision call failed: {e}")
        raise


def call_ai_text(
    api_key: str,
    prompt: str,
    provider: str = "",
    model: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Send a text-only prompt to the configured AI provider.

    Args:
        api_key: User-provided API key (BYOK). If empty, falls back to .env config.
        provider: Override the AI provider. If empty, uses .env AI_PROVIDER.
    """
    cfg = _get_config()
    effective_provider = provider or cfg.AI_PROVIDER
    effective_api_key = api_key or _env_api_key(effective_provider)

    if effective_provider not in PROVIDERS:
        raise ValueError(
            f"Unknown AI provider: {effective_provider}. "
            f"Choose: claude, openai, deepseek, gemini, kimi"
        )

    try:
        return PROVIDERS[effective_provider]["text"](
            api_key=effective_api_key, prompt=prompt, model=model,
            max_tokens=max_tokens, temperature=temperature,
        )
    except ImportError as e:
        pkg = {
            "claude": "anthropic", "openai": "openai", "deepseek": "openai",
            "gemini": "google-generativeai", "kimi": "openai",
        }.get(effective_provider, "unknown")
        logger.error(f"Missing package for {effective_provider}: {e}. pip install {pkg}")
        raise
    except Exception as e:
        logger.error(f"{effective_provider} text call failed: {e}")
        raise


def call_ai_json(
    api_key: str,
    prompt: str,
    provider: str = "",
    model: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.1,
) -> dict:
    """Call the AI with a text prompt and parse the response as JSON."""
    response = call_ai_text(
        api_key=api_key, prompt=prompt, provider=provider,
        model=model, max_tokens=max_tokens, temperature=temperature,
    )
    return _parse_json_response(response)
