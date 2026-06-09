"""Async database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import get_settings

settings = get_settings()

# Async engine — for FastAPI endpoints
if "sqlite" in settings.DATABASE_URL:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
    # Sync engine — for background tasks (SQLite needs separate connection)
    sync_db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
    sync_engine = create_engine(
        sync_db_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    sync_engine = create_engine(sync_db_url, echo=settings.DEBUG)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

SyncSession = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:  # type: ignore
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
