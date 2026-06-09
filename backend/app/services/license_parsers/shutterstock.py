"""
Shutterstock license parser.

Shutterstock is a paid stock image service:
- Standard License: Commercial use allowed, some restrictions
- Enhanced License: Extended commercial rights
- Editorial Use Only: Cannot be used commercially

Reference: https://www.shutterstock.com/license
"""

import re
import logging

from app.services.license_parsers.base import BaseParser

logger = logging.getLogger(__name__)


def parse_shutterstock(url: str) -> dict:
    """Parse Shutterstock page for license information."""
    parser = ShutterstockParser()
    return parser.parse(url)


class ShutterstockParser(BaseParser):
    domain = "shutterstock.com"

    def parse(self, url: str) -> dict:
        html = self.fetch_page(url)

        if not html:
            return {
                "license_type": "paid",
                "commercial_use": False,
                "requires_attribution": None,
                "summary": "Shutterstock 为付费图库，商业使用需购买对应授权（标准授权或增强授权）。",
            }

        soup = self.parse_html(html)
        text = soup.get_text()

        # Check for "Editorial Use Only"
        editorial_patterns = [
            r"editorial use only",
            r"editorial only",
            r"not for commercial use",
        ]

        is_editorial = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in editorial_patterns
        )

        if is_editorial:
            return {
                "license_type": "editorial_only",
                "commercial_use": False,
                "requires_attribution": None,
                "summary": "该图片仅供编辑用途（Editorial Use Only），禁止商业使用。请勿用于广告、营销或产品推广。",
            }

        # Check for license type indicators
        if re.search(r"enhanced license", text, re.IGNORECASE):
            return {
                "license_type": "paid",
                "commercial_use": True,
                "requires_attribution": False,
                "summary": "Shutterstock 增强授权支持广泛商业使用。请确认您持有有效的增强授权。",
            }

        # Default: standard paid
        return {
            "license_type": "paid",
            "commercial_use": False,
            "requires_attribution": None,
            "summary": "Shutterstock 为付费图库，商业使用需购买标准授权或增强授权。未经授权使用存在法律风险。",
        }
