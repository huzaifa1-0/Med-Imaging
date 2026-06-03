"""
MedFlow Imaging — File Pydantic Schemas

Request and response validation models for the /files endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class ImageCategoryEnum(str, Enum):
    XRAY = "XRAY"
    PHOTO = "PHOTO"
    SCAN = "SCAN"
    DOCUMENT = "DOCUMENT"


# ── Request Schemas ───────────────────────────────────────────────────────────

class FileUpdateRequest(BaseModel):
    """PATCH /files/{id} — update file metadata."""
    tooth_number: Optional[int] = Field(None, ge=1, le=48, description="Tooth number (Universal 1-32 or FDI 11-48)")
    notes: Optional[str] = None
    image_category: Optional[ImageCategoryEnum] = None


# ── Response Schemas ──────────────────────────────────────────────────────────

class FileResponse(BaseModel):
    """Full file record response."""
    id: str
    study_id: str
    patient_id: str
    file_name: str
    file_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    s3_key: str
    tooth_number: Optional[int] = None
    image_category: str
    notes: Optional[str] = None
    dicom_patient_name: Optional[str] = None
    dicom_modality: Optional[str] = None
    dicom_study_date: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PresignedUrlResponse(BaseModel):
    """Response with time-limited S3 download URLs."""
    file_id: str
    original_url: str
    thumbnail_url: Optional[str] = None
    expires_in_seconds: int = 3600


class ToothFilesResponse(BaseModel):
    """Files grouped by tooth number."""
    patient_id: str
    teeth: Dict[int, List[FileResponse]]
