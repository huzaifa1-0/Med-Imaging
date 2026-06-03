"""
MedFlow Imaging — Image Processor Service

Handles all non-AI image operations:
  - Thumbnail generation (200x200 JPEG) for gallery views
  - Standard image dimension extraction
  - DICOM-to-PNG/JPEG conversion for preview purposes

Phase 2 will add: CLAHE enhancement, denoising, edge sharpening.
"""

import io
from typing import Optional, Tuple

from PIL import Image
import numpy as np

from app.services.dicom_parser import dicom_parser


class ImageProcessor:
    """Processes dental images for storage, display, and preview."""

    THUMBNAIL_SIZE = (200, 200)
    THUMBNAIL_QUALITY = 80
    THUMBNAIL_BG = (249, 250, 251)  # Light gray background for letterboxing

    def generate_thumbnail(self, file_bytes: bytes, is_dicom: bool = False) -> Optional[bytes]:
        """
        Create a 200x200 JPEG thumbnail from an image file.

        For DICOM files, first extracts pixel data via pydicom,
        then converts to PIL Image before resizing.

        Args:
            file_bytes: Raw file bytes
            is_dicom: Whether the source file is a DICOM file

        Returns:
            JPEG bytes of the thumbnail, or None on failure
        """
        try:
            if is_dicom:
                pixel_array = dicom_parser.get_pixel_array(file_bytes)
                if pixel_array is None:
                    return None
                img = Image.fromarray(pixel_array, mode="L")  # Grayscale
            else:
                img = Image.open(io.BytesIO(file_bytes))

            # Convert to RGB if necessary (thumbnails are always JPEG)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            # Resize with letterboxing to maintain aspect ratio
            img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Create background canvas and paste centered
            canvas = Image.new("RGB", self.THUMBNAIL_SIZE, self.THUMBNAIL_BG)
            offset_x = (self.THUMBNAIL_SIZE[0] - img.width) // 2
            offset_y = (self.THUMBNAIL_SIZE[1] - img.height) // 2
            canvas.paste(img, (offset_x, offset_y))

            # Encode to JPEG bytes
            buffer = io.BytesIO()
            canvas.save(buffer, format="JPEG", quality=self.THUMBNAIL_QUALITY)
            return buffer.getvalue()

        except Exception as e:
            print(f"Thumbnail generation failed: {e}")
            return None

    def get_image_dimensions(
        self, file_bytes: bytes, is_dicom: bool = False
    ) -> Tuple[int, int]:
        """
        Extract width and height from an image file.

        Returns:
            Tuple of (width, height)
        """
        try:
            if is_dicom:
                dims = dicom_parser.get_dimensions(file_bytes)
                return dims["width"], dims["height"]
            else:
                img = Image.open(io.BytesIO(file_bytes))
                return img.width, img.height
        except Exception:
            return 0, 0

    def dicom_to_png(self, file_bytes: bytes) -> Optional[bytes]:
        """
        Convert a DICOM file to PNG bytes for browser preview.

        Returns:
            PNG bytes, or None on failure
        """
        try:
            pixel_array = dicom_parser.get_pixel_array(file_bytes)
            if pixel_array is None:
                return None

            img = Image.fromarray(pixel_array, mode="L")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()

        except Exception as e:
            print(f"DICOM to PNG conversion failed: {e}")
            return None


# Singleton instance
image_processor = ImageProcessor()
