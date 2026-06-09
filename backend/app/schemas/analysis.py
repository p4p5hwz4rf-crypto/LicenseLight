from typing import List
"""Pydantic schemas for analysis API request/response validation."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AnalysisUploadResponse(BaseModel):
    """Returned immediately after file upload."""
    task_id: str
    status: str = "pending"
    message: str = "Image uploaded successfully. Analysis started."


class FontResult(BaseModel):
    """Single font license analysis result."""
    name: str
    risk: str  # "green", "yellow", "red"
    explanation: str
    alternatives: List[str] = Field(default_factory=list)
    detected_text: List[str] = Field(default_factory=list)


class ImageSourceResult(BaseModel):
    """Image source license analysis result."""
    source_url: str = ""
    risk: str  # "green", "yellow", "red"
    explanation: str
    alternatives: List[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    """Complete analysis report."""
    overall_risk: str  # "green", "yellow", "red"
    fonts: List[FontResult] = Field(default_factory=list)
    image_source: Optional[ImageSourceResult] = None
    summary: str = ""


class AnalysisStatusResponse(BaseModel):
    """Polling response for task status."""
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    error_message: Optional[str] = None
    result: Optional[AnalysisReport] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
