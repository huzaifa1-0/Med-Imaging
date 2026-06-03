"""
MedFlow Imaging — API Router Aggregator

Combines all route modules under a single prefix.
Import this in main.py to mount all endpoints at once.
"""

from fastapi import APIRouter

from app.api.studies import router as studies_router
from app.api.files import router as files_router

api_router = APIRouter()

# Mount sub-routers
api_router.include_router(studies_router)
api_router.include_router(files_router)
