"""Image upload and analysis status endpoints."""

import os
import uuid
import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db, SyncSession
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.schemas.analysis import (
    AnalysisUploadResponse,
    AnalysisStatusResponse,
    AnalysisReport,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/check", tags=["check"])
settings = get_settings()
_executor = ThreadPoolExecutor(max_workers=2)


def _can_use_ai_vision(api_key: str = "", ai_provider: str = "") -> bool:
    """Check if the configured AI provider supports vision analysis."""
    from app.services.ai_client import is_ai_available, supports_vision
    if api_key:
        return supports_vision(ai_provider)
    return is_ai_available() and supports_vision()


def _basic_font_detection(image_path: str, ocr_results: List[dict]) -> List[dict]:
    """
    Basic font detection without Claude API.
    Groups OCR text regions and attempts to detect font properties from the image.
    Returns deduplicated font results with text samples.
    """
    from PIL import Image, ImageFilter, ImageStat
    import math

    results = []

    try:
        img = Image.open(image_path).convert("L")  # Grayscale for analysis
    except Exception:
        # Can't open image — return one deduplicated Unknown entry
        return _deduplicate_ocr_texts(ocr_results, font_name="Unknown", confidence=0.0)

    # Try to detect if text is serif or sans-serif by edge analysis
    # This is a heuristic: serif fonts have more small horizontal edges
    try:
        edges = img.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)
        edge_intensity = sum(stat.mean) / len(stat.mean)
    except Exception:
        edge_intensity = 50.0

    # Use OCR text regions to estimate font properties
    # Group texts by approximate vertical position (same line/region)
    text_groups = {}
    for r in ocr_results:
        bbox = r.get("bbox", [[0, 0]])
        y_mid = sum(p[1] for p in bbox) / len(bbox) if bbox else 0
        # Group by vertical band (every 50px)
        band = int(y_mid / 50) * 50
        if band not in text_groups:
            text_groups[band] = []
        text_groups[band].append(r)

    # For each group, analyze text characteristics
    for band, texts in sorted(text_groups.items()):
        if not texts:
            continue

        # Calculate average text height for this group
        heights = []
        for t in texts:
            bbox = t.get("bbox", [])
            if len(bbox) >= 4:
                h = max(p[1] for p in bbox) - min(p[1] for p in bbox)
                heights.append(h)
        avg_height = sum(heights) / len(heights) if heights else 20

        # Heuristic weight detection based on stroke width estimation
        if avg_height > 60:
            weight = "bold"
        elif avg_height > 40:
            weight = "semibold"
        else:
            weight = "regular"

        # Heuristic serif detection from edge pattern
        serif = edge_intensity > 60

        # Collect individual text samples (not joined)
        text_samples = [t["text"] for t in texts if t.get("text", "").strip()]
        # Store first text as primary label, rest as context
        primary_text = text_samples[0] if text_samples else ""

        results.append({
            "text": primary_text,
            "font_name": "Unknown",
            "confidence": 0.15,
            "serif": serif,
            "weight": weight,
            "style": "normal",
            "bbox": texts[0].get("bbox", [[0, 0], [0, 0], [0, 0], [0, 0]]),
            "_all_texts": text_samples,  # Keep all texts for dedup later
        })

    logger.info(
        f"Basic font detection: {len(results)} groups from {len(ocr_results)} OCR regions "
        f"(serif={any(r.get('serif') for r in results)}, edge_intensity={edge_intensity:.1f})"
    )

    return results if results else _deduplicate_ocr_texts(ocr_results, font_name="Unknown", confidence=0.0)


def _deduplicate_ocr_texts(
    ocr_results: List[dict],
    font_name: str = "Unknown",
    confidence: float = 0.0,
) -> List[dict]:
    """Deduplicate OCR results into a single entry when all fonts are the same."""
    texts = [r["text"] for r in ocr_results if r.get("text", "").strip()]
    if not texts:
        return [{
            "text": "[No text detected]",
            "font_name": font_name,
            "confidence": confidence,
            "serif": None,
            "weight": "regular",
            "style": "normal",
            "bbox": [[0, 0], [0, 0], [0, 0], [0, 0]],
        }]

    # Deduplicate texts while preserving order
    seen = set()
    unique_texts = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            unique_texts.append(t)

    combined = " | ".join(unique_texts[:10])
    if len(unique_texts) > 10:
        combined += f" ... (+{len(unique_texts) - 10} more)"

    return [{
        "text": combined,
        "font_name": font_name,
        "confidence": confidence,
        "serif": None,
        "weight": "regular",
        "style": "normal",
        "bbox": [[0, 0], [0, 0], [0, 0], [0, 0]],
    }]


def _ensure_upload_dir() -> str:
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _run_analysis_sync(
    job_id: str, image_path: str,
    api_key: str = "", ai_provider: str = "",
):
    """
    Run the full analysis pipeline synchronously in a background thread.
    Uses sync SQLAlchemy session to avoid async/sync mixing issues.
    api_key + ai_provider: user-provided BYOK credentials (never stored).
    """
    from app.services.ocr import extract_text_from_image
    from app.services.font_detection import detect_fonts_in_regions
    from app.services.reverse_image_search import reverse_image_search
    from app.services.traffic_light import classify_font_risk, classify_source_risk
    from app.services.report_generator import generate_report

    # Diagnostic: log what we received
    key_preview = f"{api_key[:8]}..." if len(api_key) > 8 else (api_key[:3] + "..." if api_key else "")
    logger.info(
        f"[{job_id}] BYOK: api_key={'SET:'+key_preview if api_key else 'EMPTY'}, "
        f"ai_provider='{ai_provider or '(default)'}', "
        f"can_ai={_can_use_ai_vision(api_key, ai_provider)}"
    )

    db = SyncSession()
    try:
        job = db.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        ).scalar_one_or_none()

        if not job:
            return

        job.status = AnalysisStatus.PROCESSING
        db.commit()

        # Step 1: OCR
        logger.info(f"[{job_id}] OCR extraction...")
        ocr_results = extract_text_from_image(image_path)

        # Step 2: Font Detection (skip if no AI provider configured)
        font_results = []
        can_ai = _can_use_ai_vision(api_key, ai_provider)
        logger.info(f"[{job_id}] Font detection: can_ai={can_ai}, ocr_regions={len(ocr_results)}")
        if can_ai:
            logger.info(f"[{job_id}] Calling AI font detection (provider={ai_provider or '(default)'})...")
            try:
                font_results = detect_fonts_in_regions(
                    image_path, ocr_results,
                    api_key or settings.CLAUDE_API_KEY,
                    ai_provider=ai_provider,
                )
                font_names = set(r.get("font_name", "") for r in font_results)
                logger.info(f"[{job_id}] AI font detection done: {len(font_results)} fonts, names={font_names}")
            except Exception as e:
                logger.error(f"[{job_id}] AI font detection FAILED: {e}")
                font_results = _basic_font_detection(image_path, ocr_results)
        elif ocr_results:
            # No AI — try basic font property detection from image
            logger.info(f"[{job_id}] Using basic (non-AI) font detection")
            font_results = _basic_font_detection(image_path, ocr_results)

        # Step 3: Reverse Image Search (skip if no Google API key)
        search_results = []
        if settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID:
            logger.info(f"[{job_id}] Reverse image search...")
            search_results = reverse_image_search(
                image_path, settings.GOOGLE_API_KEY,
                settings.GOOGLE_CSE_ID, api_key or settings.CLAUDE_API_KEY
            )

        # Step 4: License Classification
        logger.info(f"[{job_id}] License classification...")
        font_risks = classify_font_risk(font_results, db)
        source_risk = classify_source_risk(search_results)

        # Step 5: Generate Report
        logger.info(f"[{job_id}] Generating report...")
        report = generate_report(
            font_risks=font_risks,
            source_risk=source_risk,
            api_key=api_key or settings.CLAUDE_API_KEY,
            ai_provider=ai_provider,
        )

        job.status = AnalysisStatus.COMPLETED
        job.report = report
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"[{job_id}] Analysis completed successfully")

    except Exception as exc:
        logger.exception(f"[{job_id}] Analysis failed: {exc}")
        try:
            job.status = AnalysisStatus.FAILED
            job.error_message = str(exc)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def _run_analysis(
    job_id: str, image_path: str,
    api_key: str = "", ai_provider: str = "",
):
    """Wrapper that runs the sync analysis in a thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor, _run_analysis_sync,
        job_id, image_path, api_key, ai_provider,
    )


@router.post("/image", response_model=AnalysisUploadResponse, status_code=202)
async def upload_image(
    file: UploadFile = File(...),
    api_key: str = Form(""),
    ai_provider: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Upload an image for copyright compliance analysis.

    Optional api_key + ai_provider allow users to bring their own AI key.
    Keys are never stored server-side — only used for this analysis.
    """
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}",
        )

    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    upload_dir = _ensure_upload_dir()
    ext = os.path.splitext(file.filename or "image.png")[1]
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    job = AnalysisJob(
        id=str(uuid.uuid4()),
        status=AnalysisStatus.PENDING,
        original_filename=file.filename,
        image_path=file_path,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Run analysis in background thread pool
    asyncio.create_task(_run_analysis(job.id, file_path, api_key, ai_provider))

    return AnalysisUploadResponse(
        task_id=job.id,
        status="pending",
        message="Image uploaded. Analysis started.",
    )


@router.get("/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Poll for the status and result of an analysis job."""
    stmt = select(AnalysisJob).where(AnalysisJob.id == task_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    report = None
    if job.status == AnalysisStatus.COMPLETED and job.report:
        report = AnalysisReport(**job.report)

    return AnalysisStatusResponse(
        task_id=job.id,
        status=job.status.value,
        error_message=job.error_message,
        result=report,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
