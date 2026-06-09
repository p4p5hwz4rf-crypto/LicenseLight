"""
Traffic light risk classification for fonts and image sources.

Maps license information to a simple three-color system:
  - GREEN:  Free for commercial use, no attribution or attribution easily doable
  - YELLOW: Paid license required, or attribution required, or unknown but low-risk
  - RED:    Explicitly prohibited for commercial use, known risky sources
"""

from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


def classify_font_risk(
    font_results: List[dict],
    db_session,
) -> List[dict]:
    """
    Classify each detected font into Green / Yellow / Red risk levels.

    Looks up each detected font in the local license database.
    If no match found, uses Claude's confidence and heuristics.

    Args:
        font_results: Output from font_detection service.
        db_session: SQLAlchemy sync session for DB lookups.

    Returns:
        List of font risk assessments:
        [{"name": "...", "risk": "red", "explanation": "...", "alternatives": [...]}, ...]
    """
    from sqlalchemy import select, or_
    from app.models.font import Font, FontAlias

    classified = []

    for fr in font_results:
        font_name = fr.get("font_name", "Unknown")
        text_sample = fr.get("text", "")

        # Look up in database
        db_match = _lookup_font_in_db(font_name, db_session)

        risk = "yellow"
        explanation = ""
        alternatives = []

        if db_match:
            # Font found in our licensed database
            risk, explanation, alternatives = _assess_known_font(db_match)
        else:
            # Font not in database
            risk, explanation = _assess_unknown_font(font_name, fr)

        classified.append(
            {
                "name": font_name,
                "text_sample": text_sample,
                "risk": risk,
                "explanation": explanation,
                "alternatives": alternatives,
                "db_match": db_match,
            }
        )

    return classified


def _lookup_font_in_db(font_name: str, db_session) -> Optional[dict]:
    """Look up a font by name or alias in the local database."""
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
        .limit(5)
    )

    result = db_session.execute(stmt)
    fonts = result.unique().scalars().all()

    if not fonts:
        return None

    # Return best match (first result)
    font = fonts[0]
    return {
        "id": font.id,
        "name": font.name,
        "foundry": font.foundry,
        "license_type": font.license_type,
        "commercial_use": font.commercial_use,
        "requires_attribution": font.requires_attribution,
        "embedding_allowed": font.embedding_allowed,
        "web_font_allowed": font.web_font_allowed,
        "price_info": font.price_info,
        "official_url": font.official_url,
    }


def _assess_known_font(db_match: dict) -> Tuple[str, str, List[str]]:
    """Assess risk for a font found in our database."""
    license_type = db_match.get("license_type", "")
    commercial_use = db_match.get("commercial_use")
    requires_attribution = db_match.get("requires_attribution")
    font_name = db_match.get("name", "")
    price_info = db_match.get("price_info", "")

    # GREEN: Free for commercial use, no attribution required
    if license_type in ("free_commercial", "open_source") and commercial_use is True:
        if not requires_attribution:
            return (
                "green",
                f"{font_name} 是免费可商用的开源字体，无需署名即可用于商业项目。",
                [],
            )
        else:
            return (
                "green",
                f"{font_name} 可免费商用，但需要标注出处/署名。请确保在使用时附上适当的版权声明。",
                [],
            )

    # GREEN with attribution
    if license_type == "free_commercial" and requires_attribution:
        return (
            "green",
            f"{font_name} 免费可商用，需署名。记得在项目中添加版权声明。",
            [],
        )

    # YELLOW: Paid license or personal use only
    if license_type in ("paid", "free_personal"):
        explanation = (
            f"{font_name} 商业使用需购买授权。"
            if license_type == "paid"
            else f"{font_name} 仅供个人使用，商业用途需另行购买授权。"
        )
        if price_info:
            explanation += f" 价格参考：{price_info}"
        # Suggest free alternatives
        alternatives = _get_free_alternatives(font_name)
        return ("yellow", explanation, alternatives)

    # RED: Explicitly prohibited
    if commercial_use is False:
        explanation = f"{font_name} 明确禁止商业使用。请立即停止使用并替换为免费商用字体。"
        alternatives = _get_free_alternatives(font_name)
        return ("red", explanation, alternatives)

    # Default: unknown/uncertain
    return (
        "yellow",
        f"{font_name} 的授权状态不明确，建议在使用前确认商业使用条款。",
        _get_free_alternatives(font_name),
    )


def _assess_unknown_font(font_name: str, font_result: dict) -> Tuple[str, str]:
    """Assess risk for a font NOT found in our database."""
    confidence = font_result.get("confidence", 0)

    # Known risky foundries
    risky_keywords = ["方正", "汉仪", "华康", "造字工房", "getty", "蒙纳"]
    safe_keywords = ["思源", "阿里巴巴普惠", "站酷", "google", "adobe", "noto", "roboto", "open sans"]

    name_lower = font_name.lower()

    # Check for known risky patterns
    for kw in risky_keywords:
        if kw.lower() in name_lower:
            return (
                "red",
                f"检测到 {font_name}（置信度 {confidence:.0%}）。该字体厂商通常要求商业授权，未经授权使用存在侵权风险。建议替换为免费商用字体。",
            )

    # Check for known safe patterns
    for kw in safe_keywords:
        if kw.lower() in name_lower:
            return (
                "green",
                f"检测到 {font_name}（置信度 {confidence:.0%}）。该字体为已知的免费商用字体，可安全使用。",
            )

    # Unknown font
    return (
        "yellow",
        f"无法在字体库中匹配到 {font_name}（置信度 {confidence:.0%}）。建议手动确认该字体的商业使用授权条款。",
    )


def _get_free_alternatives(font_name: str) -> List[str]:
    """Suggest free commercial-use alternatives based on font type."""
    name_lower = font_name.lower()

    if any(kw in name_lower for kw in ["黑", "hei", "sans", "gothic"]):
        return ["思源黑体 (Source Han Sans)", "阿里巴巴普惠体", "Noto Sans SC"]
    elif any(kw in name_lower for kw in ["宋", "song", "serif", "明"]):
        return ["思源宋体 (Source Han Serif)", "Noto Serif SC"]
    elif any(kw in name_lower for kw in ["楷", "kai"]):
        return ["全字库楷体", "TW-MOE-Standard-Kai"]
    elif any(kw in name_lower for kw in ["圆", "rounded"]):
        return ["站酷快乐体", "点点像素体"]
    else:
        return ["思源黑体 (Source Han Sans)", "阿里巴巴普惠体", "Noto Sans SC"]


def classify_source_risk(search_results: List[dict]) -> Optional[dict]:
    """
    Classify the risk level of the image source.

    Args:
        search_results: Output from reverse_image_search service.

    Returns:
        Image source risk assessment or None if no results.
    """
    if not search_results:
        return None

    # Find the best match (highest relevance)
    best = search_results[0]
    license_info = best.get("license_info", {})
    domain = best.get("domain", "")

    license_type = license_info.get("license_type", "unknown")
    commercial_use = license_info.get("commercial_use")
    requires_attribution = license_info.get("requires_attribution")
    summary = license_info.get("summary", "")

    # Free stock sites → GREEN
    free_stock_domains = ["unsplash.com", "pexels.com", "pixabay.com"]
    if any(d in domain for d in free_stock_domains):
        return {
            "source_url": best.get("url", ""),
            "risk": "green",
            "explanation": f"图片来源 {domain} 为知名免费图库，可免费商用，无需署名。",
            "alternatives": [],
        }

    # Freepik → YELLOW (free with attribution)
    if "freepik.com" in domain:
        return {
            "source_url": best.get("url", ""),
            "risk": "yellow",
            "explanation": "Freepik 资源免费使用需署名。若未署名或需要更高权限，需购买 Premium 订阅。",
            "alternatives": ["https://unsplash.com", "https://pexels.com"],
        }

    # Paid stock → YELLOW or RED
    paid_stock = ["shutterstock.com", "gettyimages.com", "istockphoto.com", "adobe.com/stock"]
    if any(d in domain for d in paid_stock):
        risk = "red" if "getty" in domain else "yellow"
        return {
            "source_url": best.get("url", ""),
            "risk": risk,
            "explanation": f"图片来源 {domain} 为付费图库。{'Getty Images 对未经授权使用的维权力度很强，建议立即替换。' if 'getty' in domain else '商业使用需购买相应授权。'}",
            "alternatives": ["https://unsplash.com", "https://pexels.com", "https://pixabay.com"],
        }

    # Use license info from parsing
    if license_type == "free_commercial":
        risk = "green"
    elif license_type == "free_personal":
        risk = "yellow"
    elif license_type in ("editorial_only", "paid"):
        risk = "red" if license_type == "editorial_only" else "yellow"
    elif commercial_use is False:
        risk = "red"
    elif commercial_use is True:
        risk = "green" if not requires_attribution else "yellow"
    else:
        risk = "yellow"

    return {
        "source_url": best.get("url", ""),
        "risk": risk,
        "explanation": summary
        or f"图片来源 {domain}，授权状态不明确。建议在使用前确认许可条款。",
        "alternatives": (
            ["https://unsplash.com", "https://pexels.com"]
            if risk != "green"
            else []
        ),
    }
