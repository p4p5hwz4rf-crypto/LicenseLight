"""Pydantic schemas for font-related API responses."""

from pydantic import BaseModel
from typing import Optional, List


class FontAliasOut(BaseModel):
    id: int
    alias: str

    model_config = {"from_attributes": True}


class FontOut(BaseModel):
    """Public font license information."""
    id: int
    name: str
    foundry: Optional[str] = None
    license_type: Optional[str] = None
    commercial_use: Optional[bool] = None
    requires_attribution: Optional[bool] = None
    embedding_allowed: Optional[bool] = None
    web_font_allowed: Optional[bool] = None
    price_info: Optional[str] = None
    official_url: Optional[str] = None
    notes: Optional[str] = None
    aliases: List[FontAliasOut] = []

    model_config = {"from_attributes": True}


class FontSearchResult(BaseModel):
    """Search result with match score."""
    font: FontOut
    match_type: str = "name"  # "name", "alias", "fuzzy"
    score: float = 1.0
