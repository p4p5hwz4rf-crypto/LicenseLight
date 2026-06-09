"""
Claude API client wrapper for LicenseLight.

Provides reusable functions for calling Claude 3.5 Sonnet
with image analysis and text generation capabilities.
"""

import base64
import json
import logging
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)


def _encode_image_to_base64(image_path: str) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_media_type(image_path: str) -> str:
    """Determine the MIME type from file extension."""
    ext = image_path.lower().rsplit(".", 1)[-1]
    mapping = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    return mapping.get(ext, "image/png")


def call_claude_with_image(
    api_key: str,
    image_path: str,
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Send an image + text prompt to Claude and return the text response.

    Args:
        api_key: Anthropic API key.
        image_path: Path to the image file.
        prompt: Text prompt for Claude.
        model: Claude model ID.
        max_tokens: Max tokens in response.
        temperature: Response randomness.

    Returns:
        Claude's text response.
    """
    client = Anthropic(api_key=api_key)
    media_type = _get_image_media_type(image_path)
    base64_image = _encode_image_to_base64(image_path)

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    return message.content[0].text


def call_claude_text(
    api_key: str,
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Send a text-only prompt to Claude and return the response.

    Args:
        api_key: Anthropic API key.
        prompt: Text prompt for Claude.
        model: Claude model ID.
        max_tokens: Max tokens in response.
        temperature: Response randomness.

    Returns:
        Claude's text response.
    """
    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def call_claude_json(
    api_key: str,
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    temperature: float = 0.1,
) -> dict:
    """
    Call Claude with a text prompt and parse the response as JSON.

    Args:
        api_key: Anthropic API key.
        prompt: Text prompt (should instruct Claude to output JSON).
        model: Claude model ID.
        max_tokens: Max tokens.
        temperature: Low for structured output.

    Returns:
        Parsed JSON dict.
    """
    response = call_claude_text(
        api_key=api_key,
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    # Try to extract JSON from response (handle markdown code blocks)
    text = response.strip()
    if text.startswith("```"):
        # Remove code fence
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Claude returned non-JSON response. Attempting extraction...")
        # Try to find JSON between braces
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise ValueError(f"Could not parse Claude response as JSON: {text[:200]}")
