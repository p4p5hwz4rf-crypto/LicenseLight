"""
Getty Images license parser.

Getty Images is a premium stock image service known for aggressive
copyright enforcement. Images require paid licenses.
- Royalty-Free (RF): Commercial use allowed with license
- Rights-Managed (RM): Specific usage terms
- Editorial Use Only: Not for commercial use

WARNING: Getty Images actively pursues unauthorized use cases.
"""

import re
import logging

from app.services.license_parsers.base import BaseParser

logger = logging.getLogger(__name__)


def parse_gettyimages(url: str) -> dict:
    """Parse Getty Images (or iStock) page for license information."""
    parser = GettyImagesParser()
    return parser.parse(url)


class GettyImagesParser(BaseParser):
    domain = "gettyimages.com"

    def parse(self, url: str) -> dict:
        html = self.fetch_page(url)

        if not html:
            return {
                "license_type": "paid",
                "commercial_use": False,
                "requires_attribution": None,
                "summary": "⚠️ Getty Images 为付费图库，对未经授权使用维权力度极强。商业使用必须购买授权，建议立即替换为免费图库资源。",
            }

        soup = self.parse_html(html)
        text = soup.get_text()

        # Check for editorial use
        editorial_patterns = [
            r"editorial use only",
            r"editorial only",
            r"not released",
            r"not model released",
        ]

        is_editorial = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in editorial_patterns
        )

        # Check for royalty-free
        is_rf = bool(re.search(r"royalty.?free", text, re.IGNORECASE))
        # Check for rights-managed
        is_rm = bool(re.search(r"rights.?managed", text, re.IGNORECASE))
        # Check for iStock
        is_istock = "istockphoto" in url.lower() or "istock" in text.lower()

        if is_editorial:
            return {
                "license_type": "editorial_only",
                "commercial_use": False,
                "requires_attribution": None,
                "summary": "⚠️ 该 Getty Images 图片仅供编辑用途，严禁商业使用。Getty 对侵权行为的维权力度非常强，建议立即移除。",
            }

        if is_rf:
            return {
                "license_type": "paid",
                "commercial_use": True,
                "requires_attribution": False,
                "summary": "Getty Images Royalty-Free 授权支持商业使用，但需购买相应许可。请确保您持有有效授权。",
            }

        if is_rm:
            return {
                "license_type": "paid",
                "commercial_use": False,
                "requires_attribution": None,
                "summary": "Getty Images Rights-Managed 授权需根据具体用途购买。未经授权的使用可能面临高额索赔。",
            }

        # Generic Getty/iStock result
        source = "iStock" if is_istock else "Getty Images"
        return {
            "license_type": "paid",
            "commercial_use": False,
            "requires_attribution": None,
            "summary": f"{source} 为付费图库，所有商业使用均需购买相应授权。{source} 对未经授权使用有严格的维权机制，建议确认授权状态或替换为免费商用资源。",
        }
