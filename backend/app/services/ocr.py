"""
OCR service for extracting text and bounding boxes from images.

Engine priority:
  1. PaddleOCR  — best Chinese + English accuracy (requires paddleocr package)
  2. Tesseract  — free, offline, good Chinese + English (requires tesseract binary)
  3. Claude     — cloud AI OCR (requires CLAUDE_API_KEY)
  4. Basic      — Pillow fallback that returns image dimensions
"""

import os
import subprocess
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

_ocr_instance = None
_ocr_available = True
_tesseract_checked = False
_tesseract_available = False
_tesseract_path = None


def _find_tesseract() -> Optional[str]:
    """Find the tesseract binary on the system."""
    global _tesseract_checked, _tesseract_available, _tesseract_path
    if _tesseract_checked:
        return _tesseract_path if _tesseract_available else None

    _tesseract_checked = True

    # Common install locations on Windows
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]

    for path in candidates:
        if os.path.exists(path):
            _tesseract_available = True
            _tesseract_path = path
            logger.info(f"Tesseract found at: {path}")
            return path

    # Try PATH lookup
    try:
        result = subprocess.run(
            ["where", "tesseract"],
            capture_output=True, text=True, timeout=5,
            shell=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip().split("\n")[0].strip()
            _tesseract_available = True
            _tesseract_path = path
            logger.info(f"Tesseract found via PATH: {path}")
            return path
    except Exception:
        pass

    logger.warning("Tesseract not found on this system")
    return None


def _get_ocr():
    """Lazy-load PaddleOCR. Returns None if not installed."""
    global _ocr_instance, _ocr_available
    if not _ocr_available:
        return None
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_instance = PaddleOCR(
                use_angle_cls=True,
                lang="ch",
                use_gpu=False,
                show_log=False,
            )
            logger.info("PaddleOCR loaded successfully")
        except ImportError:
            logger.warning("PaddleOCR not installed")
            _ocr_available = False
            return None
    return _ocr_instance


def extract_text_from_image(
    image_path: str,
    confidence_threshold: float = 0.7,
) -> List[dict]:
    """
    Extract all text strings and their bounding boxes from an image.

    Tries engines in order: PaddleOCR → Tesseract → Claude → Basic.
    Returns list of {text, confidence, bbox} dicts.
    """
    ocr = _get_ocr()

    if ocr is not None:
        try:
            raw_results = ocr.ocr(image_path, cls=True)
            if raw_results and raw_results[0]:
                results = []
                for line in raw_results[0]:
                    bbox_points, (text, confidence) = line
                    results.append({
                        "text": text,
                        "confidence": round(float(confidence), 4),
                        "bbox": [[int(p[0]), int(p[1])] for p in bbox_points],
                    })
                high_conf = [r for r in results if r["confidence"] >= confidence_threshold]
                low_conf = [r for r in results if r["confidence"] < confidence_threshold]
                logger.info(f"PaddleOCR: {len(high_conf)} high-conf, {len(low_conf)} low-conf regions")
                return results
            logger.info("PaddleOCR returned empty results, trying Tesseract...")
        except Exception as e:
            logger.error(f"PaddleOCR failed on {image_path}: {e}")

    # Try Tesseract
    tesseract_path = _find_tesseract()
    if tesseract_path:
        results = _tesseract_ocr(image_path, tesseract_path, confidence_threshold)
        if results:
            return results

    # Try Claude
    results = _claude_ocr(image_path)
    if results:
        return results

    # Last resort
    return _basic_ocr(image_path)


def _get_tessdata_dir(tesseract_path: str) -> str:
    """Find the best tessdata directory, checking multiple locations."""
    import os

    # Check user's home tessdata first (writable, can have extra langs)
    user_tessdata = os.path.expanduser("~/tessdata")
    if os.path.isdir(user_tessdata) and os.listdir(user_tessdata):
        return user_tessdata

    # Default location next to tesseract binary
    default_dir = os.path.join(os.path.dirname(tesseract_path), "tessdata")
    if os.path.isdir(default_dir):
        return default_dir

    return default_dir


def _tesseract_ocr(
    image_path: str,
    tesseract_path: str,
    confidence_threshold: float = 0.7,
) -> List[dict]:
    """
    Run Tesseract OCR on the image and return structured results.
    Uses chi_sim+eng for Chinese + English recognition.
    """
    import os
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = tesseract_path

    tessdata_dir = _get_tessdata_dir(tesseract_path)
    os.environ.setdefault("TESSDATA_PREFIX", os.path.dirname(tessdata_dir))

    # Check available languages
    available_langs = []
    if os.path.isdir(tessdata_dir):
        available_langs = [
            f.replace(".traineddata", "")
            for f in os.listdir(tessdata_dir)
            if f.endswith(".traineddata")
        ]

    # Use chi_sim+eng if Chinese data available, else just eng
    if "chi_sim" in available_langs:
        lang = "chi_sim+eng"
    elif "chi_tra" in available_langs:
        lang = "chi_tra+eng"
    else:
        lang = "eng"
        logger.info("Chinese language data not installed; using English only")

    logger.info(f"Tesseract OCR: using language '{lang}', available: {available_langs}")

    try:
        img = Image.open(image_path)
    except Exception as e:
        logger.error(f"Cannot open image {image_path}: {e}")
        return []

    try:
        # Get detailed results including bounding boxes and confidence
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
        return []

    results = []
    n_boxes = len(data["text"])
    for i in range(n_boxes):
        text = (data["text"][i] or "").strip()
        conf = int(data["conf"][i]) if data["conf"][i] != "-1" else 0

        if not text or conf < 20:  # Tesseract confidence is 0-100
            continue

        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

        results.append({
            "text": text,
            "confidence": round(conf / 100.0, 4),
            "bbox": bbox,
        })

    # Also try page-level text as fallback for regions without boxes
    if not results:
        try:
            page_text = pytesseract.image_to_string(img, lang=lang).strip()
            if page_text:
                w, h = img.size
                for line in page_text.split("\n"):
                    line = line.strip()
                    if line:
                        results.append({
                            "text": line,
                            "confidence": 0.6,
                            "bbox": [[0, 0], [w, 0], [w, h], [0, h]],
                        })
        except Exception:
            pass

    logger.info(f"Tesseract OCR: extracted {len(results)} text regions")
    return results


def _claude_ocr(image_path: str) -> List[dict]:
    """Use AI vision for OCR when local engines are unavailable."""
    from app.services.ai_client import call_ai_with_image, is_ai_available

    if not is_ai_available():
        logger.info("No AI provider configured; skipping AI OCR")
        return []

    prompt = """Analyze this image and extract ALL visible text.

For each piece of text found, output a JSON array:
[{"text": "...", "confidence": 0.0-1.0}]

Output ONLY the JSON array, no other text."""

    try:
        text = call_ai_with_image(
            api_key="",  # using env config
            image_path=image_path,
            prompt=prompt,
        )
        import json
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            results = json.loads(text[start:end])
            for r in results:
                r.setdefault("confidence", 0.5)
                r.setdefault("bbox", [[0, 0], [0, 0], [0, 0], [0, 0]])
            logger.info(f"Claude OCR: extracted {len(results)} text regions")
            return results
        return []
    except Exception as e:
        logger.error(f"Claude OCR failed: {e}")
        return []


def _basic_ocr(image_path: str) -> List[dict]:
    """
    Last-resort fallback: use Pillow to get image info.
    Only used when no OCR engine is available at all.
    """
    try:
        from PIL import Image
        img = Image.open(image_path)
        w, h = img.size
        logger.info(f"Basic OCR: image {w}x{h}, no OCR engine available")
        return [{
            "text": f"[Image: {w}x{h} — no OCR engine available]",
            "confidence": 0.0,
            "bbox": [[0, 0], [w, 0], [w, h], [0, h]],
        }]
    except Exception:
        return [{
            "text": "[No OCR available]",
            "confidence": 0.0,
            "bbox": [[0, 0], [0, 0], [0, 0], [0, 0]],
        }]
