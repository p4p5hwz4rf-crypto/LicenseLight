"""
Pexels license parser.

Pexels images are free for commercial use. No attribution required.
License: https://www.pexels.com/license/
"""

from app.services.license_parsers.base import BaseParser


def parse_pexels(url: str) -> dict:
    """Parse Pexels image page for license information."""
    parser = PexelsParser()
    return parser.parse(url)


class PexelsParser(BaseParser):
    domain = "pexels.com"

    def parse(self, url: str) -> dict:
        # Pexels has a consistent, well-known license
        # All photos on Pexels can be used for free commercially
        html = self.fetch_page(url)

        if html and "pexels" not in html.lower():
            return {
                "license_type": "unknown",
                "commercial_use": None,
                "requires_attribution": None,
                "summary": "无法确认该页面是否为 Pexels 图片页。",
            }

        return {
            "license_type": "free_commercial",
            "commercial_use": True,
            "requires_attribution": False,
            "summary": "Pexels 图片可免费用于商业和非商业用途，无需署名。",
        }
