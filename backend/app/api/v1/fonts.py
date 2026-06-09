"""Font license search API endpoint."""

from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.font import Font, FontAlias
from app.schemas.font import FontOut, FontSearchResult

router = APIRouter(prefix="/fonts", tags=["fonts"])


@router.get("/search", response_model=List[FontSearchResult])
async def search_fonts(
    q: str = Query(..., min_length=1, description="Font name to search"),
    db: AsyncSession = Depends(get_db),
):
    """
    Fuzzy search fonts by name or alias.
    Returns matching fonts with license details.
    """
    # Direct name match first (ILIKE)
    stmt = (
        select(Font)
        .options(selectinload(Font.aliases))
        .where(
            or_(
                Font.name.ilike(f"%{q}%"),
                Font.aliases.any(FontAlias.alias.ilike(f"%{q}%")),
            )
        )
        .limit(20)
    )

    result = await db.execute(stmt)
    fonts = result.unique().scalars().all()

    if not fonts:
        return []

    results = []
    for font in fonts:
        # Determine match type and score
        match_type = "fuzzy"
        score = 0.5

        if font.name.lower() == q.lower():
            match_type = "name"
            score = 1.0
        elif any(a.alias.lower() == q.lower() for a in font.aliases):
            match_type = "alias"
            score = 0.9
        elif q.lower() in font.name.lower():
            match_type = "fuzzy"
            score = 0.7

        results.append(
            FontSearchResult(
                font=FontOut.model_validate(font),
                match_type=match_type,
                score=score,
            )
        )

    # Sort by score descending
    results.sort(key=lambda x: x.score, reverse=True)
    return results
