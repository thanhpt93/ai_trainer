import os
import time
from pathlib import Path
from typing import Generator, Tuple, List, Optional
from PIL import Image
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.core.config import settings
from backend.app.domain.models import Dataset, ImageRecord


class DatasetScanner:
    """Service to scan image directories safely and persist metadata."""

    @staticmethod
    def inspect_image(file_path: Path) -> Tuple[bool, Optional[int], Optional[int], Optional[int], Optional[str], Optional[str]]:
        """
        Inspect an image file using Pillow without loading full image pixels into memory.
        Returns (is_valid, width, height, channels, format, error_reason)
        """
        try:
            with Image.open(file_path) as img:
                # img.verify() checks header and file integrity
                width, height = img.size
                img_format = img.format
                mode = img.mode
                
                # Determine channels based on mode
                channels = len(mode) if mode else 3
                if mode in ("RGB", "YCbCr"):
                    channels = 3
                elif mode in ("RGBA", "CMYK"):
                    channels = 4
                elif mode in ("L", "1", "P"):
                    channels = 1

                return True, width, height, channels, img_format, None
        except Exception as exc:
            return False, None, None, None, None, str(exc)[:250]

    @classmethod
    def scan_directory(cls, db: Session, dataset: Dataset) -> dict:
        """
        Recursively scans the dataset's root path, inspecting images and persisting records.
        Does NOT load all images into memory simultaneously.
        """
        start_time = time.time()
        root_path = Path(dataset.root_path)

        # Clear previously scanned image records for this dataset to allow re-scans
        db.query(ImageRecord).filter(ImageRecord.dataset_id == dataset.id).delete()
        db.commit()

        total_scanned = 0
        valid_count = 0
        corrupted_count = 0
        unsupported_count = 0

        batch: List[ImageRecord] = []

        for root, dirs, files in os.walk(str(root_path), followlinks=False):
            # Sort files for deterministic scanning
            dirs.sort()
            files.sort()
            
            for file_name in files:
                total_scanned += 1
                full_path = Path(root) / file_name
                suffix = full_path.suffix.lower()

                if suffix not in settings.SUPPORTED_IMAGE_EXTENSIONS:
                    unsupported_count += 1
                    continue

                try:
                    rel_path = str(full_path.relative_to(root_path).as_posix())
                except ValueError:
                    rel_path = file_name

                file_size = 0
                try:
                    file_size = full_path.stat().st_size
                except OSError:
                    pass

                is_valid, width, height, channels, img_format, error_reason = cls.inspect_image(full_path)

                if is_valid:
                    valid_count += 1
                else:
                    corrupted_count += 1

                record = ImageRecord(
                    dataset_id=dataset.id,
                    relative_path=rel_path,
                    absolute_path=str(full_path),
                    file_size_bytes=file_size,
                    width=width,
                    height=height,
                    channels=channels,
                    format=img_format,
                    is_valid=is_valid,
                    error_reason=error_reason,
                )
                batch.append(record)

                if len(batch) >= settings.SCAN_BATCH_SIZE:
                    db.bulk_save_objects(batch)
                    db.commit()
                    batch.clear()

        # Save remaining batch
        if batch:
            db.bulk_save_objects(batch)
            db.commit()
            batch.clear()

        duration = time.time() - start_time

        # Update dataset stats
        dataset.image_count = valid_count + corrupted_count
        dataset.valid_image_count = valid_count
        dataset.corrupted_image_count = corrupted_count
        dataset.unsupported_file_count = unsupported_count
        dataset.last_scanned_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(dataset)

        return {
            "dataset_id": dataset.id,
            "scanned_files": total_scanned,
            "valid_images": valid_count,
            "corrupted_images": corrupted_count,
            "unsupported_files": unsupported_count,
            "duration_seconds": round(duration, 3),
            "message": f"Scan completed in {duration:.2f}s: {valid_count} valid images, {corrupted_count} corrupted, {unsupported_count} unsupported files.",
        }
