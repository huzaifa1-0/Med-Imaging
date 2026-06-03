"""
MedFlow Imaging — Study Pydantic Schemas

Request and response validation models for the /studies endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class StudyTypeEnum(str, Enum):
    PERIAPICAL = "PERIAPICAL"
    BITEWING = "BITEWING"
    PANORAMIC = "PANORAMIC"
    CBCT = "CBCT"
    PHOTO = "PHOTO"
    INTRAORAL = "INTRAORAL"
    CLINICAL = "CLINICAL"


class StudyStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


# ── Request Schemas ───────────────────────────────────────────────────────────

class StudyCreateRequest(BaseModel):
    """POST /studies — create a new imaging study."""
    practice_id: str = Field(..., description="Tenant practice identifier")
    patient_id: str = Field(..., description="Patient this study belongs to")
    provider_id: str = Field(..., description="Provider creating the study")
    appointment_id: Optional[str] = Field(None, description="Optional linked appointment")
    title: str = Field(..., min_length=1, max_length=255, description="Study title")
    description: Optional[str] = Field(None, description="Optional notes about the study")
    study_type: StudyTypeEnum = Field(..., description="Type of imaging study")


class StudyUpdateRequest(BaseModel):
    """PATCH /studies/{id} — update study metadata."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[StudyStatusEnum] = None


# ── Response Schemas ──────────────────────────────────────────────────────────

class FileInStudyResponse(BaseModel):
    """Nested file summary inside a study response."""
    id: str
    file_name: str
    file_type: str
    image_category: str
    tooth_number: Optional[int] = None
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


class StudyResponse(BaseModel):
    """Single study response (used for create, update, get-by-id)."""
    id: str
    practice_id: str
    patient_id: str
    provider_id: str
    appointment_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    study_type: str
    status: str
    study_date: datetime
    created_at: datetime
    updated_at: datetime
    files: List[FileInStudyResponse] = []

    class Config:
        from_attributes = True


class StudyListResponse(BaseModel):
    """Response wrapper for listing studies."""
    count: int
    studies: List[StudyResponse]
