"""
MedFlow Imaging — Files API Routes

Endpoints for uploading, retrieving, updating, and deleting imaging files.
Handles multipart file uploads, S3 storage, thumbnail generation, and DICOM parsing.
"""

import os
import uuid
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db
from app.models.imaging_study import ImagingStudy
from app.models.imaging_file import ImagingFile, ImageFileType, ImageCategory
from app.schemas.file import (
    FileResponse,
    FileUpdateRequest,
    PresignedUrlResponse,
    ToothFilesResponse,
)
from app.services.storage import storage_service
from app.services.dicom_parser import dicom_parser
from app.services.image_processor import image_processor

router = APIRouter(prefix="/files", tags=["Files"])

# Allowed upload extensions
ALLOWED_EXTENSIONS = {".dcm", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}


def _get_file_type(filename: str, content_type: str) -> ImageFileType:
    """Determine ImageFileType from filename extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".dcm" or content_type == "application/dicom":
        return ImageFileType.DICOM
    elif ext == ".png":
        return ImageFileType.PNG
    elif ext in (".tiff", ".tif"):
        return ImageFileType.TIFF
    return ImageFileType.JPEG


@router.post("/upload", response_model=FileResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(..., description="The image file (DICOM, JPEG, PNG, TIFF)"),
    study_id: str = Form(..., description="ID of the parent study"),
    patient_id: str = Form(..., description="Patient ID"),
    practice_id: str = Form(..., description="Practice ID for tenant isolation"),
    tooth_number: Optional[int] = Form(None, description="Tooth number (1-48)"),
    image_category: str = Form("XRAY", description="Image category: XRAY, PHOTO, SCAN, DOCUMENT"),
    db: Session = Depends(get_db),
):
    """
    Upload a dental image file.

    Pipeline:
      1. Validate file extension and study ownership
      2. Read file bytes into memory
      3. Detect file type and extract DICOM metadata if applicable
      4. Upload original to S3
      5. Generate and upload 200x200 thumbnail
      6. Extract image dimensions
      7. Save metadata record to database
    """

    # 1. Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 2. Verify the study exists and belongs to this practice
    study = (
        db.query(ImagingStudy)
        .filter(ImagingStudy.id == study_id, ImagingStudy.practice_id == practice_id)
        .first()
    )
    if not study:
        raise HTTPException(status_code=403, detail="Study not found or access denied")

    # 3. Read file bytes
    file_bytes = await file.read()
    file_id = str(uuid.uuid4())
    file_type = _get_file_type(file.filename, file.content_type)
    is_dicom = file_type == ImageFileType.DICOM

    # 4. Extract DICOM metadata if applicable
    dicom_meta = {}
    if is_dicom:
        dicom_meta = dicom_parser.extract_metadata(file_bytes)

    # 5. Upload original to S3
    s3_key = storage_service.build_s3_key(
        practice_id, patient_id, study_id, file_id, ext
    )
    storage_service.upload_file(file_bytes, s3_key, file.content_type or "application/octet-stream")

    # 6. Generate and upload thumbnail
    thumbnail_key = None
    thumb_bytes = image_processor.generate_thumbnail(file_bytes, is_dicom=is_dicom)
    if thumb_bytes:
        thumbnail_key = storage_service.build_s3_key(
            practice_id, patient_id, study_id, file_id, ext, is_thumbnail=True
        )
        storage_service.upload_file(thumb_bytes, thumbnail_key, "image/jpeg")

    # 7. Extract dimensions
    width, height = image_processor.get_image_dimensions(file_bytes, is_dicom=is_dicom)

    # 8. Save to database
    db_file = ImagingFile(
        id=file_id,
        study_id=study_id,
        patient_id=patient_id,
        file_name=file.filename,
        file_type=file_type,
        file_size=len(file_bytes),
        width=width or None,
        height=height or None,
        s3_key=s3_key,
        s3_bucket=storage_service.bucket,
        thumbnail_key=thumbnail_key,
        tooth_number=tooth_number,
        image_category=image_category,
        dicom_patient_name=dicom_meta.get("patient_name") or None,
        dicom_modality=dicom_meta.get("modality") or None,
        dicom_study_date=dicom_meta.get("study_date") or None,
    )

    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return FileResponse.model_validate(db_file)


@router.get("/{file_id}/url", response_model=PresignedUrlResponse)
def get_file_url(
    file_id: str,
    practice_id: str = Query(..., description="Practice ID for tenant check"),
    db: Session = Depends(get_db),
):
    """Generate 1-hour pre-signed S3 URLs for the original file and thumbnail."""

    db_file = db.query(ImagingFile).filter(ImagingFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Tenant check via parent study
    study = (
        db.query(ImagingStudy)
        .filter(ImagingStudy.id == db_file.study_id, ImagingStudy.practice_id == practice_id)
        .first()
    )
    if not study:
        raise HTTPException(status_code=403, detail="Access denied")

    original_url = storage_service.get_presigned_url(db_file.s3_key)
    thumbnail_url = None
    if db_file.thumbnail_key:
        thumbnail_url = storage_service.get_presigned_url(db_file.thumbnail_key)

    return PresignedUrlResponse(
        file_id=file_id,
        original_url=original_url,
        thumbnail_url=thumbnail_url,
    )


@router.get("/by-tooth/{patient_id}", response_model=ToothFilesResponse)
def get_files_by_tooth(
    patient_id: str,
    practice_id: str = Query(..., description="Practice ID for tenant check"),
    db: Session = Depends(get_db),
):
    """Retrieve all images for a patient grouped by tooth number."""

    files = (
        db.query(ImagingFile)
        .join(ImagingStudy, ImagingFile.study_id == ImagingStudy.id)
        .filter(
            ImagingFile.patient_id == patient_id,
            ImagingStudy.practice_id == practice_id,
            ImagingFile.tooth_number.isnot(None),
        )
        .all()
    )

    grouped = defaultdict(list)
    for f in files:
        grouped[f.tooth_number].append(FileResponse.model_validate(f))

    return ToothFilesResponse(patient_id=patient_id, teeth=dict(grouped))


@router.patch("/{file_id}", response_model=FileResponse)
def update_file_metadata(
    file_id: str,
    payload: FileUpdateRequest,
    practice_id: str = Query(..., description="Practice ID for tenant check"),
    db: Session = Depends(get_db),
):
    """Update a file's tooth number, notes, or image category."""

    db_file = db.query(ImagingFile).filter(ImagingFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Tenant check
    study = (
        db.query(ImagingStudy)
        .filter(ImagingStudy.id == db_file.study_id, ImagingStudy.practice_id == practice_id)
        .first()
    )
    if not study:
        raise HTTPException(status_code=403, detail="Access denied")

    if payload.tooth_number is not None:
        db_file.tooth_number = payload.tooth_number
    if payload.notes is not None:
        db_file.notes = payload.notes
    if payload.image_category is not None:
        db_file.image_category = payload.image_category.value

    db.commit()
    db.refresh(db_file)

    return FileResponse.model_validate(db_file)


@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    practice_id: str = Query(..., description="Practice ID for tenant check"),
    db: Session = Depends(get_db),
):
    """Delete a file record and remove corresponding S3 objects."""

    db_file = db.query(ImagingFile).filter(ImagingFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Tenant check
    study = (
        db.query(ImagingStudy)
        .filter(ImagingStudy.id == db_file.study_id, ImagingStudy.practice_id == practice_id)
        .first()
    )
    if not study:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete from S3
    keys_to_delete = [db_file.s3_key]
    if db_file.thumbnail_key:
        keys_to_delete.append(db_file.thumbnail_key)
    storage_service.delete_multiple(keys_to_delete)

    # Delete from database
    db.delete(db_file)
    db.commit()

    return {"success": True, "message": "File deleted successfully"}
