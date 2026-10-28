import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.dataset import (
    DatasetResponse,
    DatasetListResponse,
    DatasetUpdate,
    DatasetScanResult,
    PaginatedImagesResponse,
)
from backend.app.domain.models import ImageRecord
from backend.app.services.dataset_service import DatasetService

router = APIRouter()


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List all datasets across all projects."""
    items, total = DatasetService.list_all_datasets(db, skip=skip, limit=limit)
    return DatasetListResponse(
        items=[DatasetResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Get dataset details by ID."""
    dataset = DatasetService.get_dataset_by_id(db, dataset_id)
    return DatasetResponse.model_validate(dataset)


@router.patch("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: str,
    dataset_in: DatasetUpdate,
    db: Session = Depends(get_db),
):
    """Update dataset name or description."""
    dataset = DatasetService.update_dataset(db, dataset_id, dataset_in)
    return DatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Delete a dataset and its indexed image records."""
    DatasetService.delete_dataset(db, dataset_id)
    return None


@router.post("/{dataset_id}/scan", response_model=DatasetScanResult)
def scan_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Trigger recursive image folder scan for the dataset."""
    result = DatasetService.scan_dataset(db, dataset_id)
    return DatasetScanResult(**result)


@router.get("/{dataset_id}/images", response_model=PaginatedImagesResponse)
def get_dataset_images(
    dataset_id: str,
    is_valid: Optional[bool] = Query(None, description="Filter valid or corrupted images"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get paginated image records for a dataset."""
    return DatasetService.get_dataset_images(
        db, dataset_id, is_valid=is_valid, page=page, page_size=page_size
    )


@router.get("/{dataset_id}/images/{image_id}/file")
def get_image_file(dataset_id: str, image_id: str, db: Session = Depends(get_db)):
    """
    Safely stream an image file directly from the filesystem.
    Validates that the file path is strictly within the dataset's root path.
    """
    dataset = DatasetService.get_dataset_by_id(db, dataset_id)
    image = db.query(ImageRecord).filter(
        ImageRecord.id == image_id, ImageRecord.dataset_id == dataset_id
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image record not found.",
        )

    file_path = Path(image.absolute_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical image file is missing or was moved.",
        )

    # Security check: Ensure file path is strictly inside dataset.root_path
    dataset_root = Path(dataset.root_path).resolve()
    try:
        file_path.resolve().relative_to(dataset_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: File is outside the dataset root directory.",
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
    )
