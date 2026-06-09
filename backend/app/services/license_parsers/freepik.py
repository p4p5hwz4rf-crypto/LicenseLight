"""
Freepik license parser.

Freepik has multiple license tiers:
- Free: Requires attribution (must credit Freepik)
- Premium: No attribution required, commercial use allowed

Reference: https://www.freepik.com/legal#nav-freepik-license
"""

import re
import logging

from app.services.license_parsers.base import BaseParser

logger = logging.getLogger(__name__)


def parse_freepik(url: str) -> dict:
    """Parse Freepik page for license information."""
    parser = FreepikParser()
    return parser.parse(url)


class FreepikParser(BaseParser):
    domain = "freepik.com"

    def parse(self, url: str) -> dict:
        html = self.fetch_page(url)

        if not html:
            return {
                "license_type": "free_personal",
                "commercial_use": False,
                "requires_attribution": True,
                "summary": "Freepik 免费资源需署名（注明 Designed by Freepik），商业用途需 Premium 订阅。",
            }

        soup = self.parse_html(html)
        text = soup.get_text()

        # Check for Premium indicators
        premium_indicators = [
            r"premium",
            r"unlimited downloads",
            r"no attribution",
            r"premium license",
        ]

        is_premium = any(
            re.search(indicator, text, re.IGNORECASE)
            for indicator in premium_indicators
        )

        # Check for free/attribution indicators
        free_indicators = [
            r"free.*attribution",
            r"attribution.*required",
            r"must.*credit",
            r"designed by freepik",
        ]

        requires_attribution = any(
            re.search(indicator, text, re.IGNORECASE)
            for indicator in free_indicators
        )

        if is_premium and not requires_attribution:
            return {
                "license_type": "paid",
                "commercial_use": True,
                "requires_attribution": False,
                "summary": "Freepik Premium 资源可商用且无需署名。请确认您持有有效的 Premium 订阅。",
            }

        # Default: free tier with attribution
        return {
            "license_type": "free_personal",
            "commercial_use": False,
            "requires_attribution": True,
            "summary": "Freepik 免费资源使用时需署名（注明 Designed by Freepik）。商业项目建议升级 Premium 或使用 Unsplash 等免署名图库。",
        }
