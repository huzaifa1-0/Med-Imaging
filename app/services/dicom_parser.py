"""
MedFlow Imaging — DICOM Parser Service

Extracts metadata and pixel data from DICOM (.dcm) files using pydicom.
This powers:
  - Automatic metadata population on upload (patient name, modality, study date)
  - Pixel array extraction for AI inference and image processing
  - Optimal window/level calculation for X-ray contrast display
"""

import pydicom
from pydicom.errors import InvalidDicomError
import numpy as np
from io import BytesIO
from typing import Optional


class DicomParser:
    """Parses DICOM files to extract clinical metadata and pixel arrays."""

    @staticmethod
    def extract_metadata(file_bytes: bytes) -> dict:
        """
        Parse a DICOM file and return a dictionary of useful clinical metadata.

        Args:
            file_bytes: Raw bytes of the .dcm file

        Returns:
            Dictionary with extracted DICOM header fields
        """
        try:
            ds = pydicom.dcmread(BytesIO(file_bytes))
        except InvalidDicomError:
            return {"error": "File is not a valid DICOM file"}

        return {
            "patient_name": str(getattr(ds, "PatientName", "") or ""),
            "patient_id": str(getattr(ds, "PatientID", "") or ""),
            "modality": str(getattr(ds, "Modality", "") or ""),
            "study_date": str(getattr(ds, "StudyDate", "") or ""),
            "study_description": str(getattr(ds, "StudyDescription", "") or ""),
            "series_description": str(getattr(ds, "SeriesDescription", "") or ""),
            "institution_name": str(getattr(ds, "InstitutionName", "") or ""),
            "manufacturer": str(getattr(ds, "Manufacturer", "") or ""),
            "rows": int(getattr(ds, "Rows", 0)),
            "columns": int(getattr(ds, "Columns", 0)),
            "bits_allocated": int(getattr(ds, "BitsAllocated", 0)),
            "bits_stored": int(getattr(ds, "BitsStored", 0)),
            "photometric_interpretation": str(
                getattr(ds, "PhotometricInterpretation", "") or ""
            ),
            "pixel_spacing": [
                float(x) for x in getattr(ds, "PixelSpacing", [0, 0])
            ],
        }

    @staticmethod
    def get_pixel_array(file_bytes: bytes) -> Optional[np.ndarray]:
        """
        Extract the pixel data from a DICOM file as a normalized 8-bit NumPy array.

        Returns:
            np.ndarray of shape (rows, columns) with uint8 values [0-255],
            or None if pixel data cannot be extracted.
        """
        try:
            ds = pydicom.dcmread(BytesIO(file_bytes))
            pixels = ds.pixel_array.astype(np.float64)

            # Apply Rescale Slope/Intercept if present (common in CT/X-ray)
            slope = float(getattr(ds, "RescaleSlope", 1))
            intercept = float(getattr(ds, "RescaleIntercept", 0))
            pixels = pixels * slope + intercept

            # Normalize to 0-255 range
            p_min, p_max = pixels.min(), pixels.max()
            if p_max > p_min:
                pixels = ((pixels - p_min) / (p_max - p_min) * 255.0)
            else:
                pixels = np.zeros_like(pixels)

            return pixels.astype(np.uint8)

        except Exception as e:
            print(f"DICOM pixel extraction failed: {e}")
            return None

    @staticmethod
    def get_dimensions(file_bytes: bytes) -> dict:
        """
        Quick extraction of just width/height from DICOM headers.

        Returns:
            {"width": int, "height": int}
        """
        try:
            ds = pydicom.dcmread(BytesIO(file_bytes), stop_before_pixels=True)
            return {
                "width": int(getattr(ds, "Columns", 0)),
                "height": int(getattr(ds, "Rows", 0)),
            }
        except Exception:
            return {"width": 0, "height": 0}

    @staticmethod
    def calculate_window_level(file_bytes: bytes) -> dict:
        """
        Determine optimal Window Center and Window Width for display.

        First checks DICOM headers for preset values.
        Falls back to histogram-based auto-calculation.

        Returns:
            {"window_center": float, "window_width": float}
        """
        try:
            ds = pydicom.dcmread(BytesIO(file_bytes))

            # Use DICOM-stored values if available
            wc = getattr(ds, "WindowCenter", None)
            ww = getattr(ds, "WindowWidth", None)
            if wc is not None and ww is not None:
                # Handle multi-value window center/width
                if isinstance(wc, pydicom.multival.MultiValue):
                    wc = float(wc[0])
                if isinstance(ww, pydicom.multival.MultiValue):
                    ww = float(ww[0])
                return {"window_center": float(wc), "window_width": float(ww)}

            # Auto-calculate from pixel histogram
            pixels = ds.pixel_array.astype(np.float64)
            slope = float(getattr(ds, "RescaleSlope", 1))
            intercept = float(getattr(ds, "RescaleIntercept", 0))
            pixels = pixels * slope + intercept

            p5, p95 = np.percentile(pixels, [5, 95])
            center = (p5 + p95) / 2.0
            width = p95 - p5

            return {"window_center": round(center, 2), "window_width": round(width, 2)}

        except Exception as e:
            return {"window_center": 128.0, "window_width": 256.0}


# Singleton instance
dicom_parser = DicomParser()
