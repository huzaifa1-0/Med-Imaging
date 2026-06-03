"""
MedFlow Imaging — ImagingFile ORM Model

Represents a single dental image file (DICOM, JPEG, PNG, TIFF)
stored in AWS S3 and linked to a study, patient, and optionally a tooth number.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, DateTime, Enum, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
import enum

from app.models.database import Base


class ImageFileType(str, enum.Enum):
    """Supported image file formats."""
    DICOM = "DICOM"
    JPEG = "JPEG"
    PNG = "PNG"
    TIFF = "TIFF"


class ImageCategory(str, enum.Enum):
    """Clinical category of the image."""
    XRAY = "XRAY"
    PHOTO = "PHOTO"
    SCAN = "SCAN"
    DOCUMENT = "DOCUMENT"


class ImagingFile(Base):
    __tablename__ = "imaging_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    study_id = Column(String(36), ForeignKey("imaging_studies.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(String(36), nullable=False, index=True)

    # File metadata
    file_name = Column(String(255), nullable=False)
    file_type = Column(Enum(ImageFileType), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # S3 storage pointers
    s3_key = Column(String(512), nullable=False, unique=True)
    s3_bucket = Column(String(255), nullable=False)
    thumbnail_key = Column(String(512), nullable=True)

    # Clinical context
    tooth_number = Column(Integer, nullable=True)  # Universal 1-32 or FDI 11-48
    image_category = Column(Enum(ImageCategory), nullable=False, default=ImageCategory.XRAY)
    notes = Column(Text, nullable=True)
    captured_at = Column(DateTime, nullable=True)

    # DICOM-specific extracted metadata (stored as nullable fields)
    dicom_patient_name = Column(String(255), nullable=True)
    dicom_modality = Column(String(50), nullable=True)
    dicom_study_date = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to study
    study = relationship("ImagingStudy", back_populates="files")

    __table_args__ = (
        Index("ix_file_study", "study_id"),
        Index("ix_file_tooth", "patient_id", "tooth_number"),
    )

    def __repr__(self):
        return f"<ImagingFile id={self.id} name='{self.file_name}' tooth={self.tooth_number}>"
