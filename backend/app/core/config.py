"""Application configuration loaded from environment variables."""

from typing import List
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the LicenseLight application."""

    # Application
    APP_NAME: str = "LicenseLight"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Database — use SQLite for local dev, PostgreSQL for production
    DATABASE_URL: str = "sqlite+aiosqlite:///./licenselight.db"

    # Redis / Celery — optional, not needed for local dev
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # AI Provider — choose one: "claude", "openai", "deepseek", "gemini", "kimi"
    # Claude / OpenAI / Gemini support both vision (font detection) and text (summary)
    # DeepSeek supports text only (summary) — vision will fall back to basic analysis
    AI_PROVIDER: str = "claude"

    # Anthropic Claude
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"

    # OpenAI (GPT-4o for vision, GPT-4o-mini for text)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"           # Vision model
    OPENAI_TEXT_MODEL: str = "gpt-4o-mini"  # Cheaper for text-only tasks

    # DeepSeek (text-only, very cheap, excellent Chinese)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Kimi / Moonshot (OpenAI-compatible, great Chinese + vision)
    KIMI_API_KEY: str = ""
    KIMI_MODEL: str = "moonshot-v1-8k"
    KIMI_VISION_MODEL: str = "moonshot-v1-8k-vision"

    # Google Custom Search
    GOOGLE_API_KEY: str = ""
    GOOGLE_CSE_ID: str = ""

    # OCR
    OCR_ENGINE: str = "paddleocr"  # "paddleocr" or "tesseract"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
