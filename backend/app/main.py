"""LicenseLight FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.check import router as check_router
from app.api.v1.fonts import router as fonts_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    import os

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield
    # Shutdown: nothing special needed


app = FastAPI(
    title="LicenseLight API",
    description="Copyright compliance co-pilot for designers and indie developers",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(check_router, prefix="/api/v1")
app.include_router(fonts_router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "LicenseLight"}
