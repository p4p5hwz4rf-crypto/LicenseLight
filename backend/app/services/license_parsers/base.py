"""Base class for domain-specific license parsers."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Common user-agent to avoid being blocked
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class BaseParser(ABC):
    """Abstract base for stock image license parsers."""

    domain: str = ""

    def fetch_page(self, url: str, timeout: int = 15) -> Optional[str]:
        """
        Fetch a webpage and return its HTML text.

        Args:
            url: The URL to fetch.
            timeout: Request timeout in seconds.

        Returns:
            HTML string or None on failure.
        """
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers={"User-Agent": USER_AGENT})
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML with BeautifulSoup using lxml parser."""
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    def parse(self, url: str) -> dict:
        """
        Parse license information from a webpage URL.

        Returns:
            dict with keys: license_type, commercial_use, requires_attribution, summary
        """
        ...
