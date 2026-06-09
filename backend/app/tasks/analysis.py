"""
Celery task for the full image copyright compliance analysis pipeline.

Steps:
  1. OCR: Extract text from the image using PaddleOCR.
  2. Font Detection: Send text regions to Claude for font identification.
  3. Reverse Image Search: Downscale and search via Google Custom Search.
  4. License Rule Engine: Match fonts to DB, parse source licenses.
  5. Report Generation: Assemble structured JSON report.
"""

import os
import json
import base64
import logging
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.core.config import get_settings
from app.models.analysis import AnalysisStatus

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def analyze_image_task(self, job_id: str, image_path: str):
    """
    Full image copyright compliance analysis pipeline.

    Args:
        job_id: The AnalysisJob UUID.
        image_path: Path to the saved image file on disk.
    """
    from app.services.ocr import extract_text_from_image
    from app.services.font_detection import detect_fonts_in_regions
    from app.services.reverse_image_search import reverse_image_search
    from app.services.traffic_light import classify_font_risk, classify_source_risk
    from app.services.report_generator import generate_report

    settings = get_settings()

    # Import sync DB session for Celery task context
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models.analysis import AnalysisJob

    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    engine = create_engine(sync_url)

    with Session(engine) as db:
        job = db.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        ).scalar_one_or_none()

        if not job:
            logger.error(f"AnalysisJob {job_id} not found")
            return

        try:
            # Mark as processing
            job.status = AnalysisStatus.PROCESSING
            db.commit()

            # ── Step 1: OCR ──────────────────────────────────────────
            logger.info(f"[{job_id}] Step 1: OCR extraction...")
            ocr_results = extract_text_from_image(image_path)

            # ── Step 2: Font Detection ───────────────────────────────
            logger.info(f"[{job_id}] Step 2: Font detection via Claude...")
            font_results = detect_fonts_in_regions(
                image_path, ocr_results, settings.CLAUDE_API_KEY
            )

            # ── Step 3: Reverse Image Search ─────────────────────────
            logger.info(f"[{job_id}] Step 3: Reverse image search...")
            search_results = reverse_image_search(
                image_path,
                settings.GOOGLE_API_KEY,
                settings.GOOGLE_CSE_ID,
                settings.CLAUDE_API_KEY,
            )

            # ── Step 4: Traffic Light Classification ─────────────────
            logger.info(f"[{job_id}] Step 4: License classification...")
            font_risks = classify_font_risk(font_results, db)
            source_risk = classify_source_risk(search_results)

            # ── Step 5: Generate Report ──────────────────────────────
            logger.info(f"[{job_id}] Step 5: Generating report...")
            report = generate_report(
                font_risks=font_risks,
                source_risk=source_risk,
                api_key=settings.CLAUDE_API_KEY,
            )

            # Mark complete
            job.status = AnalysisStatus.COMPLETED
            job.report = report
            job.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"[{job_id}] Analysis completed successfully")

        except Exception as exc:
            logger.exception(f"[{job_id}] Analysis failed: {exc}")
            job.status = AnalysisStatus.FAILED
            job.error_message = str(exc)
            db.commit()

            # Retry once if it's a transient error
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc)
