"""
OCR service for extracting text and bounding boxes from images.

Uses PaddleOCR for Chinese + English text extraction.
Falls back to Claude for low-confidence regions.
"""
from typing import Optional, List

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded PaddleOCR instance
_ocr_instance = None


def _get_ocr():
    """Lazy-load PaddleOCR to avoid import overhead at module load."""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR

            _ocr_instance = PaddleOCR(
                use_angle_cls=True,
                lang="ch",  # Chinese + English
                use_gpu=False,
                show_log=False,
            )
        except ImportError:
            logger.error(
                "PaddleOCR not installed. Install with: pip install paddleocr"
            )
            raise
    return _ocr_instance


def extract_text_from_image(
    image_path: str,
    confidence_threshold: float = 0.7,
) -> List[dict]:
    """
    Extract all text strings and their bounding boxes from an image.

    Args:
        image_path: Path to the image file.
        confidence_threshold: Minimum confidence for OCR results.

    Returns:
        List of dicts with keys:
            - text: extracted string
            - confidence: OCR confidence score (0-1)
            - bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] (four corners)
    """
    ocr = _get_ocr()

    try:
        raw_results = ocr.ocr(image_path, cls=True)
    except Exception as e:
        logger.error(f"PaddleOCR failed on {image_path}: {e}")
        return _fallback_ocr(image_path)

    if not raw_results or not raw_results[0]:
        logger.info(f"No text detected in {image_path}")
        return []

    results = []
    for line in raw_results[0]:
        bbox_points, (text, confidence) = line

        results.append(
            {
                "text": text,
                "confidence": round(float(confidence), 4),
                "bbox": [[int(p[0]), int(p[1])] for p in bbox_points],
            }
        )

    # Filter low-confidence results
    high_conf = [r for r in results if r["confidence"] >= confidence_threshold]
    low_conf = [r for r in results if r["confidence"] < confidence_threshold]

    logger.info(
        f"OCR: {len(high_conf)} high-confidence, {len(low_conf)} low-confidence regions"
    )

    return results


def _fallback_ocr(image_path: str) -> List[dict]:
    """
    Fallback: Use Claude for OCR when PaddleOCR is unavailable.
    This is a simplified fallback - in production, you'd crop regions
    and send them to Claude individually.
    """
    from app.core.config import get_settings
    from app.services.claude_client import call_claude_with_image

    settings = get_settings()

    if not settings.CLAUDE_API_KEY:
        logger.warning("No Claude API key configured; skipping fallback OCR")
        return []

    prompt = """Analyze this image and extract ALL visible text.

For each piece of text found, output a JSON object with:
- "text": the exact text string
- "bbox": estimated bounding box as [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] in pixels

Return a JSON array of these objects. Output ONLY the JSON array, no other text."""

    try:
        text = call_claude_with_image(
            api_key=settings.CLAUDE_API_KEY,
            image_path=image_path,
            prompt=prompt,
        )
        import json

        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            results = json.loads(text[start:end])
            for r in results:
                r.setdefault("confidence", 0.5)
            return results
        return []
    except Exception as e:
        logger.error(f"Claude fallback OCR failed: {e}")
        return []
