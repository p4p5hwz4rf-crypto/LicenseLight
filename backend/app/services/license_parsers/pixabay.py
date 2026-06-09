"""
Pixabay license parser.

Pixabay images are free for commercial use under the Pixabay Content License.
No attribution required for most content.
Some content may be under different licenses (sponsored images from Shutterstock).
"""

import logging
import re

from app.services.license_parsers.base import BaseParser

logger = logging.getLogger(__name__)


def parse_pixabay(url: str) -> dict:
    """Parse Pixabay image page for license information."""
    parser = PixabayParser()
    return parser.parse(url)


class PixabayParser(BaseParser):
    domain = "pixabay.com"

    def parse(self, url: str) -> dict:
        html = self.fetch_page(url)

        if not html:
            return {
                "license_type": "free_commercial",
                "commercial_use": True,
                "requires_attribution": False,
                "summary": "Pixabay 图片通常可免费商用，无需署名（无法访问页面确认）。",
            }

        soup = self.parse_html(html)
        text = soup.get_text().lower()

        # Check for Shutterstock sponsored content
        if "sponsored" in text and "shutterstock" in text:
            return {
                "license_type": "paid",
                "commercial_use": False,
                "requires_attribution": None,
                "summary": "该图片为 Shutterstock 赞助内容，非免费使用。商业使用需购买 Shutterstock 授权。",
            }

        # Check for "free for commercial use" indicators
        free_patterns = [
            r"free for commercial use",
            r"no attribution required",
            r"pixabay (content )?license",
        ]

        for pattern in free_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "license_type": "free_commercial",
                    "commercial_use": True,
                    "requires_attribution": False,
                    "summary": "Pixabay 图片可在 Pixabay Content License 下免费商用，无需署名。",
                }

        # Default: assume Pixabay license applies
        return {
            "license_type": "free_commercial",
            "commercial_use": True,
            "requires_attribution": False,
            "summary": "Pixabay 图片可免费商用（需确认非 Shutterstock 赞助内容）。",
        }
