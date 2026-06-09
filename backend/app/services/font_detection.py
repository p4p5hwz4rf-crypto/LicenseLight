"""
Font detection service using Claude vision.

For each text region found by OCR, Claude analyzes the typeface
characteristics and attempts to identify the exact font.
"""

from typing import Optional, List
import json
import logging

logger = logging.getLogger(__name__)

FONT_DETECTION_PROMPT = """You are a font identification expert. Analyze this image region and identify ALL fonts used in the visible text.

For each distinct font, describe:
1. Typeface characteristics (serif/sans-serif, weight, style, width)
2. Your best guess at the exact font name (e.g., "方正黑体", "Arial", "思源宋体")
3. Confidence level (0-1)

CRITICAL: For Chinese text, pay special attention to:
- 方正 (FounderType) fonts: 方正黑体, 方正宋体, 方正楷体, 方正仿宋, etc.
- 汉仪 (Hanyi) fonts: 汉仪旗黑, 汉仪楷体, etc.
- 华康 (Dynacomware) fonts
- 思源 (Source Han) fonts: 思源黑体, 思源宋体
- 站酷 fonts: 站酷快乐体, 站酷文艺体, etc.
- 阿里巴巴普惠体 (Alibaba PuHuiTi)
- 造字工房 fonts: 造字工房悦黑, etc.

Output a JSON array:
[{"font_name": "...", "serif": true/false, "weight": "...", "style": "...", "confidence": 0.0-1.0}]

Output ONLY the JSON array, no other text."""


def detect_fonts_in_regions(
    image_path: str,
    ocr_results: List[dict],
    api_key: str,
    ai_provider: str = "",
    model: str = "",
) -> List[dict]:
    """
    Identify fonts used in each text region of the image.

    Sends the full image to the AI for font identification.
    Cross-references OCR results for context.

    Returns:
        List of dicts:
        [{"text": "...", "font_name": "...", "confidence": 0.9, "serif": false, ...}, ...]
    """
    from app.services.ai_client import is_ai_available
    ai_ok = is_ai_available(api_key=api_key)
    logger.info(f"Font detection: ai_available={ai_ok}, api_key={'SET' if api_key else 'EMPTY'}, provider='{ai_provider or '(default)'}'")
    if not ai_ok:
        logger.warning("No AI provider configured; skipping font detection")
        return _build_empty_results(ocr_results)

    from app.services.ai_client import call_ai_with_image

    try:
        logger.info(f"Font detection: calling AI vision (provider={ai_provider or '(default)'})...")
        response = call_ai_with_image(
            api_key=api_key,
            image_path=image_path,
            prompt=FONT_DETECTION_PROMPT,
            provider=ai_provider,
            model=model,
            max_tokens=4096,
            temperature=0.2,
        )
    except Exception as e:
        logger.exception(f"AI font detection FAILED (provider={ai_provider or '(default)'}): {e}")
        return _build_empty_results(ocr_results)

    # Parse Claude's JSON response
    try:
        text = response.strip()
        logger.info(f"AI font detection raw response ({len(text)} chars): {text[:300]}...")
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            detected_fonts = json.loads(text[start:end])
        else:
            detected_fonts = []
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse font detection JSON: {response[:200]}")
        return _build_empty_results(ocr_results)

    # Map detected fonts to OCR text regions
    results = []
    if detected_fonts and ocr_results:
        # Associate each OCR region with the best-matching detected font
        # Simple strategy: assign the first detected font to all regions
        # (Claude analyzes the whole image, so fonts are global)
        for i, ocr in enumerate(ocr_results):
            font_idx = min(i, len(detected_fonts) - 1)
            font_info = detected_fonts[font_idx]
            results.append(
                {
                    "text": ocr["text"],
                    "font_name": font_info.get("font_name", "Unknown"),
                    "confidence": font_info.get("confidence", 0.5),
                    "serif": font_info.get("serif", None),
                    "weight": font_info.get("weight", "regular"),
                    "style": font_info.get("style", "normal"),
                    "bbox": ocr["bbox"],
                }
            )
    elif detected_fonts:
        for font_info in detected_fonts:
            results.append(
                {
                    "text": "",
                    "font_name": font_info.get("font_name", "Unknown"),
                    "confidence": font_info.get("confidence", 0.5),
                    "serif": font_info.get("serif", None),
                    "weight": font_info.get("weight", "regular"),
                    "style": font_info.get("style", "normal"),
                    "bbox": [],
                }
            )

    return results


def _build_empty_results(ocr_results: List[dict]) -> List[dict]:
    """Build empty font results when detection is unavailable."""
    return [
        {
            "text": r["text"],
            "font_name": "Unknown",
            "confidence": 0.0,
            "serif": None,
            "weight": "regular",
            "style": "normal",
            "bbox": r["bbox"],
        }
        for r in ocr_results
    ]


async def match_font_to_db(
    font_name: str,
    db_session,
) -> List[dict]:
    """
    Match a font name guessed by Claude against our font license database.

    Uses SQLAlchemy async session for fuzzy matching.
    Returns matching font records with license details.
    """
    from sqlalchemy import select, or_
    from sqlalchemy.orm import selectinload
    from app.models.font import Font, FontAlias

    stmt = (
        select(Font)
        .options(selectinload(Font.aliases))
        .where(
            or_(
                Font.name.ilike(f"%{font_name}%"),
                Font.aliases.any(FontAlias.alias.ilike(f"%{font_name}%")),
            )
        )
        .limit(10)
    )

    result = await db_session.execute(stmt)
    fonts = result.unique().scalars().all()

    return [
        {
            "id": f.id,
            "name": f.name,
            "foundry": f.foundry,
            "license_type": f.license_type,
            "commercial_use": f.commercial_use,
            "requires_attribution": f.requires_attribution,
            "price_info": f.price_info,
            "official_url": f.official_url,
        }
        for f in fonts
    ]
