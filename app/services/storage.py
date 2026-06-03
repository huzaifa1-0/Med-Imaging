"""
MedFlow Imaging — S3 Storage Service

Handles all interactions with AWS S3:
  - Upload original files and thumbnails
  - Generate time-limited pre-signed download URLs
  - Delete objects from S3

All file paths follow the HIPAA-compliant tenant-isolated structure:
  practices/{practice_id}/patients/{patient_id}/studies/{study_id}/{file_id}.ext
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional

from app.config import settings


class StorageService:
    """Manages all S3 operations for the imaging microservice."""

    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.bucket = settings.AWS_S3_BUCKET

    def build_s3_key(
        self,
        practice_id: str,
        patient_id: str,
        study_id: str,
        file_id: str,
        extension: str,
        is_thumbnail: bool = False,
    ) -> str:
        """
        Construct a deterministic, tenant-isolated S3 key.

        Example output:
          practices/abc/patients/xyz/studies/s1/file123.dcm
          practices/abc/patients/xyz/studies/s1/thumbs/file123.jpg
        """
        base = f"practices/{practice_id}/patients/{patient_id}/studies/{study_id}"
        if is_thumbnail:
            return f"{base}/thumbs/{file_id}.jpg"
        return f"{base}/{file_id}{extension}"

    def upload_file(
        self,
        file_bytes: bytes,
        s3_key: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """Upload raw bytes to S3. Returns True on success."""
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
                ServerSideEncryption="AES256",  # SSE-S3 encryption at rest
            )
            return True
        except ClientError as e:
            raise RuntimeError(f"S3 upload failed for key '{s3_key}': {e}")

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generate a temporary download URL for a private S3 object.

        Args:
            s3_key: The full S3 object key
            expires_in: Lifetime in seconds (default 3600 = 1 hour)

        Returns:
            A pre-signed HTTPS URL string
        """
        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate pre-signed URL for '{s3_key}': {e}")

    def delete_file(self, s3_key: str) -> bool:
        """Delete a single object from S3. Returns True on success."""
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            print(f"Warning: S3 delete failed for '{s3_key}': {e}")
            return False

    def delete_multiple(self, s3_keys: list[str]) -> None:
        """Bulk-delete multiple S3 objects (up to 1000 per call)."""
        if not s3_keys:
            return
        try:
            objects = [{"Key": key} for key in s3_keys]
            self.s3.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": objects, "Quiet": True},
            )
        except ClientError as e:
            print(f"Warning: S3 bulk delete failed: {e}")


# Singleton instance
storage_service = StorageService()
