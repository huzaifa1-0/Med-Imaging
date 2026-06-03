"""
MedFlow Imaging — Studies API Routes

CRUD endpoints for managing imaging studies (collections of dental images).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.models.database import get_db
from app.models.imaging_study import ImagingStudy, StudyStatus, StudyType
from app.schemas.study import (
    StudyCreateRequest,
    StudyUpdateRequest,
    StudyResponse,
    StudyListResponse,
)

router = APIRouter(prefix="/studies", tags=["Studies"])


@router.get("", response_model=StudyListResponse)
def list_studies(
    patient_id: str = Query(..., description="Required patient ID"),
    practice_id: str = Query(..., description="Required practice ID for tenant isolation"),
    appointment_id: Optional[str] = Query(None),
    study_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all active imaging studies for a specific patient within a practice."""

    query = db.query(ImagingStudy).filter(
        ImagingStudy.patient_id == patient_id,
        ImagingStudy.practice_id == practice_id,
        ImagingStudy.status != StudyStatus.DELETED,
    )

    if appointment_id:
        query = query.filter(ImagingStudy.appointment_id == appointment_id)
    if study_type:
        query = query.filter(ImagingStudy.study_type == study_type)

    studies = query.order_by(ImagingStudy.study_date.desc()).all()

    return StudyListResponse(
        count=len(studies),
        studies=[StudyResponse.model_validate(s) for s in studies],
    )


@router.post("", response_model=StudyResponse, status_code=201)
def create_study(
    payload: StudyCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new imaging study for a patient."""

    study = ImagingStudy(
        practice_id=payload.practice_id,
        patient_id=payload.patient_id,
        provider_id=payload.provider_id,
        appointment_id=payload.appointment_id,
        title=payload.title,
        description=payload.description,
        study_type=payload.study_type.value,
    )

    db.add(study)
    db.commit()
    db.refresh(study)

    return StudyResponse.model_validate(study)


@router.get("/{study_id}", response_model=StudyResponse)
def get_study(
    study_id: str,
    practice_id: str = Query(..., description="Practice ID for tenant check"),
    db: Session = Depends(get_db),
):
    """Retrieve a single study with its files."""

    study = (
        db.query(ImagingStudy)
        .filter(
            ImagingStudy.id == study_id,
            ImagingStudy.practice_id == practice_id,
        )
        .first()
    )

    if not study:
        raise HTTPException(status_code=404, detail="Imaging study not found")

    return StudyResponse.model_validate(study)


@router.patch("/{study_id}", response_model=StudyResponse)
def update_study(
    study_id: str,
    payload: StudyUpdateRequest,
    practice_id: str = Query(..., description="Practice ID for tenant check"),
    db: Session = Depends(get_db),
):
    """Update an existing study's title, description, or status."""

    study = (
        db.query(ImagingStudy)
        .filter(
            ImagingStudy.id == study_id,
            ImagingStudy.practice_id == practice_id,
        )
        .first()
    )

    if not study:
        raise HTTPException(status_code=404, detail="Imaging study not found")

    if payload.title is not None:
        study.title = payload.title
    if payload.description is not None:
        study.description = payload.description
    if payload.status is not None:
        study.status = payload.status.value
    study.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(study)

    return StudyResponse.model_validate(study)


@router.delete("/{study_id}")
def delete_study(
    study_id: str,
    practice_id: str = Query(..., description="Practice ID for tenant check"),
    db: Session = Depends(get_db),
):
    """Soft-delete a study by setting status to DELETED."""

    study = (
        db.query(ImagingStudy)
        .filter(
            ImagingStudy.id == study_id,
            ImagingStudy.practice_id == practice_id,
        )
        .first()
    )

    if not study:
        raise HTTPException(status_code=404, detail="Imaging study not found")

    study.status = StudyStatus.DELETED
    study.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Study soft-deleted successfully"}
