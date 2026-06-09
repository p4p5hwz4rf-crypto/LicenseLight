"""Image upload and analysis status endpoints."""

import os
import uuid
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.schemas.analysis import (
    AnalysisUploadResponse,
    AnalysisStatusResponse,
    AnalysisReport,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/check", tags=["check"])
settings = get_settings()


def _ensure_upload_dir() -> str:
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


async def _run_analysis(job_id: str, image_path: str):
    """
    Run the analysis synchronously (no Celery needed for local dev).
    Updates the AnalysisJob with results or error.
    """
    from app.core.database import async_session_factory
    from app.services.ocr import extract_text_from_image
    from app.services.font_detection import detect_fonts_in_regions
    from app.services.reverse_image_search import reverse_image_search
    from app.services.traffic_light import classify_font_risk, classify_source_risk
    from app.services.report_generator import generate_report

    async with async_session_factory() as db:
        stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            return

        try:
            job.status = AnalysisStatus.PROCESSING
            await db.commit()

            # Step 1: OCR
            logger.info(f"[{job_id}] OCR extraction...")
            ocr_results = extract_text_from_image(image_path)

            # Step 2: Font Detection
            font_results = []
            if settings.CLAUDE_API_KEY:
                logger.info(f"[{job_id}] Font detection via Claude...")
                font_results = detect_fonts_in_regions(
                    image_path, ocr_results, settings.CLAUDE_API_KEY
                )
            else:
                font_results = [
                    {"text": r["text"], "font_name": "Unknown", "confidence": 0.0,
                     "serif": None, "weight": "regular", "style": "normal", "bbox": r["bbox"]}
                    for r in ocr_results
                ]

            # Step 3: Reverse Image Search
            search_results = []
            if settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID:
                logger.info(f"[{job_id}] Reverse image search...")
                search_results = reverse_image_search(
                    image_path, settings.GOOGLE_API_KEY, settings.GOOGLE_CSE_ID, settings.CLAUDE_API_KEY
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
                claude_api_key=settings.CLAUDE_API_KEY,
            )

            job.status = AnalysisStatus.COMPLETED
            job.report = report
            job.completed_at = datetime.utcnow()
            await db.commit()
            logger.info(f"[{job_id}] Analysis completed")

        except Exception as exc:
            logger.exception(f"[{job_id}] Analysis failed: {exc}")
            job.status = AnalysisStatus.FAILED
            job.error_message = str(exc)
            await db.commit()


@router.post("/image", response_model=AnalysisUploadResponse, status_code=202)
async def upload_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Upload an image for copyright compliance analysis."""
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

    # Run analysis in background (no Celery needed)
    background_tasks.add_task(_run_analysis, job.id, file_path)

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
