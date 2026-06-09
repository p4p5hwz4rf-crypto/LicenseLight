"""
Unsplash license parser.

Unsplash images are free for commercial and non-commercial use.
No attribution required, but appreciated.
License: https://unsplash.com/license
"""

import logging
import re

from app.services.license_parsers.base import BaseParser

logger = logging.getLogger(__name__)


def parse_unsplash(url: str) -> dict:
    """
    Parse Unsplash image page for license information.

    Unsplash License:
    - Free for commercial use: YES
    - Attribution required: NO (but appreciated)
    - License type: free_commercial

    Args:
        url: Unsplash photo URL.

    Returns:
        Standardized license info dict.
    """
    parser = UnsplashParser()
    return parser.parse(url)


class UnsplashParser(BaseParser):
    domain = "unsplash.com"

    def parse(self, url: str) -> dict:
        html = self.fetch_page(url)

        # Even if fetch fails, Unsplash license terms are well-known
        if html:
            soup = self.parse_html(html)

            # Check for any license badges or text
            license_text = soup.get_text().lower()

            # Unsplash images are always free commercial use
            # Just verify it's actually an Unsplash page
            if "unsplash" not in license_text:
                return self._unknown_result()

        # Unsplash has a consistent, well-known license
        return {
            "license_type": "free_commercial",
            "commercial_use": True,
            "requires_attribution": False,
            "summary": "Unsplash 图片可免费用于商业和非商业用途，无需署名（但建议署名以支持摄影师）。",
        }

    def _unknown_result(self) -> dict:
        return {
            "license_type": "unknown",
            "commercial_use": None,
            "requires_attribution": None,
            "summary": "无法确认该页面是否为 Unsplash 图片页。",
        }
