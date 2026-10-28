from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.db.session import get_db
from backend.app.schemas.annotation import (
    ImageAnnotationSaveRequest,
    ImageAnnotationResponse,
    DatasetAnnotationSummary,
    PaginatedAnnotatedImages,
    ExportRequest,
    ExportResponse,
)
from backend.app.services.annotation_service import AnnotationService
from backend.app.services.export_service import ExportService

router = APIRouter()


class NegativeMarkRequest(BaseModel):
    is_negative: bool


class ReviewMarkRequest(BaseModel):
    needs_review: bool


@router.get("/datasets/{dataset_id}/annotation-summary", response_model=DatasetAnnotationSummary)
def get_dataset_annotation_summary(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieve annotation completion metrics, status breakdown, and class distribution."""
    return AnnotationService.get_dataset_annotation_summary(db, dataset_id)


@router.get("/datasets/{dataset_id}/annotated-images", response_model=PaginatedAnnotatedImages)
def list_annotated_images(
    dataset_id: str,
    status: Optional[str] = Query("ALL", description="Filter: ALL, UNANNOTATED, ANNOTATED, NEEDS_REVIEW, INVALID"),
    search: Optional[str] = Query(None, description="Search by image relative path"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve paginated image browser items with attached annotation metadata and statuses."""
    return AnnotationService.list_annotated_images(
        db,
        dataset_id=dataset_id,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/images/{image_id}/annotation", response_model=ImageAnnotationResponse)
def get_image_annotation(image_id: str, db: Session = Depends(get_db)):
    """Get annotation details for a specific image, or return default empty state."""
    return AnnotationService.get_or_create_annotation(db, image_id)


@router.put("/images/{image_id}/annotation", response_model=ImageAnnotationResponse)
def save_image_annotation(
    image_id: str,
    req: ImageAnnotationSaveRequest,
    db: Session = Depends(get_db),
):
    """Save or update classification labels or object detection bounding boxes."""
    return AnnotationService.save_annotation(db, image_id, req)


@router.post("/images/{image_id}/annotation/mark-negative", response_model=ImageAnnotationResponse)
def mark_image_negative(
    image_id: str,
    req: NegativeMarkRequest,
    db: Session = Depends(get_db),
):
    """Mark or unmark an image as confirmed negative (contains no target objects)."""
    return AnnotationService.mark_negative(db, image_id, req.is_negative)


@router.post("/images/{image_id}/annotation/mark-review", response_model=ImageAnnotationResponse)
def mark_image_review(
    image_id: str,
    req: ReviewMarkRequest,
    db: Session = Depends(get_db),
):
    """Flag or unflag an image annotation for peer review."""
    return AnnotationService.mark_review(db, image_id, req.needs_review)


@router.post("/datasets/{dataset_id}/export", response_model=ExportResponse)
def export_dataset_annotations(
    dataset_id: str,
    req: ExportRequest,
    db: Session = Depends(get_db),
):
    """Export dataset annotations into standard formats: YOLO, COCO, Pascal VOC, CSV, JSON."""
    return ExportService.export_dataset(db, dataset_id, req)
