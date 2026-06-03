"""
MedFlow Imaging — FastAPI Application Entry Point

This is the main server file. Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Features:
  - CORS middleware for frontend dev servers
  - Auto-creates database tables on startup
  - Health check endpoint at /health
  - All imaging routes mounted at /api/v1/imaging
  - Auto-generated Swagger docs at /docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.router import api_router
from app.models.database import Base, engine


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""

    app = FastAPI(
        title="MedFlow Imaging Microservice",
        description=(
            "Dental imaging microservice handling DICOM/image upload, S3 storage, "
            "thumbnail generation, metadata extraction, and AI diagnostics. "
            "Designed as a standalone Python service consumed by the MedFlow Node.js backend."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Startup Event ─────────────────────────────────────────────────────
    @app.on_event("startup")
    def on_startup():
        """Create all database tables if they don't exist yet."""
        # Import models so SQLAlchemy registers them with Base.metadata
        from app.models.imaging_study import ImagingStudy  # noqa: F401
        from app.models.imaging_file import ImagingFile  # noqa: F401

        Base.metadata.create_all(bind=engine)
        print("✅ Database tables verified / created")
        print(f"✅ MedFlow Imaging Service running in {settings.APP_ENV} mode")
        print(f"✅ S3 Bucket: {settings.AWS_S3_BUCKET}")
        print(f"✅ Swagger docs: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")

    # ── Routes ────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1/imaging")

    # ── Health Check ──────────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    def health_check():
        """Service health check endpoint."""
        return {
            "status": "healthy",
            "service": "medflow-imaging",
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        }

    return app


# Create the app instance — uvicorn points to this
app = create_app()
