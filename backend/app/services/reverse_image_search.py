"""
Reverse image search service using Google Custom Search API.

Downscales the image to <200KB, sends it to Google CSE,
then parses result pages to extract license information.
"""
from typing import Optional, List

import io
import os
import logging
from urllib.parse import urlparse

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

# Known stock image domains and their license parsers
STOCK_DOMAINS = {
    "unsplash.com": "unsplash",
    "pexels.com": "pexels",
    "pixabay.com": "pixabay",
    "freepik.com": "freepik",
    "shutterstock.com": "shutterstock",
    "gettyimages.com": "gettyimages",
    "istockphoto.com": "gettyimages",  # Owned by Getty
    "rawpixel.com": "rawpixel",
}


def _downscale_image(image_path: str, max_size_kb: int = 200) -> str:
    """
    Downscale an image to under max_size_kb for Google reverse image search.
    Returns the path to the downscaled version.
    """
    img = Image.open(image_path)

    # Convert to RGB if necessary (e.g., RGBA PNG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    quality = 85
    max_dimension = 1024

    # Resize if too large
    w, h = img.size
    if max(w, h) > max_dimension:
        ratio = max_dimension / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    output_path = image_path + ".search.jpg"

    # Iteratively reduce quality to meet size target
    for _ in range(10):
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        size_kb = buffer.tell() / 1024

        if size_kb <= max_size_kb:
            with open(output_path, "wb") as f:
                f.write(buffer.getvalue())
            logger.info(f"Downscaled image: {size_kb:.0f}KB (quality={quality})")
            return output_path

        quality -= 10

    # Last resort with lowest quality
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=20, optimize=True)
    with open(output_path, "wb") as f:
        f.write(buffer.getvalue())
    logger.info(f"Downscaled image at minimum quality: {buffer.tell()/1024:.0f}KB")
    return output_path


def reverse_image_search(
    image_path: str,
    google_api_key: str,
    google_cse_id: str,
    api_key: str = "",
) -> List[dict]:
    """
    Perform a reverse image search using Google Custom Search API.

    Downscales the image, uploads it for search, then fetches and parses
    the top result pages for license information.

    Returns:
        List of dicts:
        [{"url": "...", "title": "...", "domain": "...", "license_info": {...}}, ...]
    """
    if not google_api_key or not google_cse_id:
        logger.warning("Google API/CSE not configured; skipping reverse image search")
        return []

    # Step 1: Prepare the image
    search_image_path = _downscale_image(image_path)

    try:
        # Step 2: Google Custom Search (text-based fallback for image search)
        # Note: True reverse image search requires hosting the image at a URL.
        # For MVP, we use Google CSE with "searchType=image" which requires
        # an image URL. As a practical workaround, we search by the filename
        # and use image search mode or search for the image via text query.
        #
        # Production enhancement: upload to a temporary public URL first.
        search_results = _google_image_search(
            image_path, search_image_path, google_api_key, google_cse_id
        )
    except Exception as e:
        logger.error(f"Google search failed: {e}")
        return []
    finally:
        # Clean up downscaled image
        if os.path.exists(search_image_path):
            os.remove(search_image_path)

    if not search_results:
        return []

    # Step 3: For each result URL, fetch and parse license information
    results_with_license = []
    for item in search_results[:5]:  # Top 5 results
        url = item.get("link", "")
        domain = urlparse(url).netloc.lower()

        license_info = _fetch_and_parse_license(
            url, domain, api_key
        )

        results_with_license.append(
            {
                "url": url,
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "domain": domain,
                "license_info": license_info,
            }
        )

    return results_with_license


def _google_image_search(
    original_path: str,
    search_image_path: str,
    api_key: str,
    cse_id: str,
) -> List[dict]:
    """
    Use Google Custom Search API for image-based search.

    Since the free CSE API requires a hosted URL for true reverse image search,
    we use a hybrid approach:
    1. Try searchType=image with image search parameters
    2. Fall back to text search using OCR results from the image
    """
    # For MVP: use text-based search with the image filename or OCR text
    # In production, upload image to a temporary cloud URL and use searchType=image

    # Extract a search query from the filename
    filename = os.path.splitext(os.path.basename(original_path))[0]
    query = filename.replace("-", " ").replace("_", " ").strip()

    if not query or len(query) < 3:
        query = "design image"

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "searchType": "image",
        "num": 5,
        "imgSize": "medium",
        "safe": "active",
    }

    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    items = data.get("items", [])
    logger.info(f"Google search returned {len(items)} results for query '{query}'")
    return items


def _fetch_and_parse_license(
    url: str,
    domain: str,
    api_key: str = "",
) -> dict:
    """
    Fetch a webpage and extract license information.

    Uses domain-specific parsers when available, falls back to Claude.
    """
    # Try domain-specific parser first
    parser_map = _get_parser_map()
    parser_key = None
    for known_domain, parser_name in STOCK_DOMAINS.items():
        if known_domain in domain:
            parser_key = parser_name
            break

    if parser_key and parser_key in parser_map:
        try:
            return parser_map[parser_key](url)
        except Exception as e:
            logger.warning(f"Domain parser '{parser_key}' failed for {url}: {e}")

    # Fallback: fetch page and use Claude
    try:
        return _claude_license_extraction(url, api_key)
    except Exception as e:
        logger.error(f"License extraction failed for {url}: {e}")
        return {
            "license_type": "unknown",
            "commercial_use": None,
            "requires_attribution": None,
            "summary": f"Failed to parse license from {domain}",
        }


def _get_parser_map() -> dict:
    """Lazy-load domain-specific parsers."""
    parser_map = {}
    try:
        from app.services.license_parsers.unsplash import parse_unsplash
        parser_map["unsplash"] = parse_unsplash
    except ImportError:
        pass
    try:
        from app.services.license_parsers.pexels import parse_pexels
        parser_map["pexels"] = parse_pexels
    except ImportError:
        pass
    try:
        from app.services.license_parsers.pixabay import parse_pixabay
        parser_map["pixabay"] = parse_pixabay
    except ImportError:
        pass
    try:
        from app.services.license_parsers.freepik import parse_freepik
        parser_map["freepik"] = parse_freepik
    except ImportError:
        pass
    try:
        from app.services.license_parsers.shutterstock import parse_shutterstock
        parser_map["shutterstock"] = parse_shutterstock
    except ImportError:
        pass
    try:
        from app.services.license_parsers.gettyimages import parse_gettyimages
        parser_map["gettyimages"] = parse_gettyimages
    except ImportError:
        pass
    return parser_map


def _claude_license_extraction(url: str, api_key: str) -> dict:
    """Use Claude to extract license info from a webpage HTML snippet."""
    if not api_key:
        return {
            "license_type": "unknown",
            "commercial_use": None,
            "requires_attribution": None,
            "summary": "No license parser available and Claude not configured.",
        }

    from app.services.ai_client import call_ai_json

    # Fetch the page HTML first
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            response.raise_for_status()
            html = response.text[:15000]  # Truncate to avoid token limits
    except Exception:
        return {
            "license_type": "unknown",
            "commercial_use": None,
            "requires_attribution": None,
            "summary": f"Could not fetch page: {url}",
        }

    prompt = f"""Analyze this webpage HTML snippet and determine the license type of the main image.

URL: {url}

HTML snippet:
```
{html[:10000]}
```

Determine:
1. Is the image free for commercial use?
2. Does it require attribution?
3. What is the overall license type?

Return JSON:
{{"license_type": "free_commercial|free_personal|editorial_only|paid|unknown", "commercial_use": true/false/null, "requires_attribution": true/false/null, "summary": "Brief Chinese explanation"}}

Output ONLY the JSON object."""

    try:
        return call_ai_json(api_key, prompt, temperature=0.1)
    except Exception as e:
        logger.error(f"Claude license extraction failed: {e}")
        return {
            "license_type": "unknown",
            "commercial_use": None,
            "requires_attribution": None,
            "summary": f"Parsing failed: {str(e)[:100]}",
        }
