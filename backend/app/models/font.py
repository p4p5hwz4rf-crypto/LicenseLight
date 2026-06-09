"""Font license database models."""

from typing import Optional, List

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Font(Base):
    __tablename__ = "fonts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    foundry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    license_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # 'free_commercial', 'free_personal', 'paid', 'open_source'
    commercial_use: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    requires_attribution: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    embedding_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    web_font_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    price_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    official_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    aliases: Mapped[List["FontAlias"]] = relationship(
        "FontAlias", back_populates="font", cascade="all, delete-orphan"
    )


class FontAlias(Base):
    __tablename__ = "font_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    font_id: Mapped[int] = mapped_column(Integer, ForeignKey("fonts.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    font: Mapped["Font"] = relationship("Font", back_populates="aliases")
