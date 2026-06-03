"""
MedFlow Imaging — ImagingStudy ORM Model

Represents a collection of dental images grouped by session/visit.
Examples: "Full Mouth Series 2026-06-01", "Panoramic Pre-Treatment"
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, Text, Index
from sqlalchemy.orm import relationship
import enum

from app.models.database import Base


class StudyType(str, enum.Enum):
    """Classification of the imaging study."""
    PERIAPICAL = "PERIAPICAL"
    BITEWING = "BITEWING"
    PANORAMIC = "PANORAMIC"
    CBCT = "CBCT"
    PHOTO = "PHOTO"
    INTRAORAL = "INTRAORAL"
    CLINICAL = "CLINICAL"


class StudyStatus(str, enum.Enum):
    """Lifecycle status of the study."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class ImagingStudy(Base):
    __tablename__ = "imaging_studies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practice_id = Column(String(36), nullable=False, index=True)
    patient_id = Column(String(36), nullable=False, index=True)
    provider_id = Column(String(36), nullable=False)
    appointment_id = Column(String(36), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    study_type = Column(Enum(StudyType), nullable=False)
    status = Column(Enum(StudyStatus), nullable=False, default=StudyStatus.ACTIVE)
    study_date = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: a study contains many files
    files = relationship("ImagingFile", back_populates="study", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_study_patient_practice", "patient_id", "practice_id"),
    )

    def __repr__(self):
        return f"<ImagingStudy id={self.id} title='{self.title}' type={self.study_type}>"
