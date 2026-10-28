import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from backend.app.domain.models import (
    Project,
    Dataset,
    ImageRecord,
    ProjectLabel,
    ImageAnnotation,
    ClassificationAnnotation,
    ObjectAnnotation,
)
from backend.app.schemas.annotation import (
    AnnotationStatus,
    BoundingBoxCreate,
    BoundingBoxResponse,
    ImageAnnotationSaveRequest,
    ImageAnnotationResponse,
    DatasetAnnotationSummary,
    AnnotatedImageItem,
    PaginatedAnnotatedImages,
)
from backend.app.schemas.label import LabelResponse
from backend.app.services.dataset_service import DatasetService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnnotationService:
    """Service handling business rules for Image Annotations, Object Detection, and Classification."""

    @classmethod
    def get_or_create_annotation(cls, db: Session, image_id: str) -> ImageAnnotationResponse:
        """Fetch existing image annotation or build default unannotated response."""
        image = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image with ID '{image_id}' not found.",
            )

        dataset = db.query(Dataset).filter(Dataset.id == image.dataset_id).first()
        project = db.query(Project).filter(Project.id == dataset.project_id).first()

        annotation = (
            db.query(ImageAnnotation)
            .filter(ImageAnnotation.image_id == image_id)
            .first()
        )

        if not annotation:
            # Create a default UNANNOTATED record
            annotation = ImageAnnotation(
                dataset_id=dataset.id,
                image_id=image.id,
                task_type=project.task_type,
                status=AnnotationStatus.UNANNOTATED.value,
                is_negative=False,
            )
            db.add(annotation)
            db.commit()
            db.refresh(annotation)

        return cls._build_response(annotation)

    @classmethod
    def save_annotation(
        cls,
        db: Session,
        image_id: str,
        req: ImageAnnotationSaveRequest,
    ) -> ImageAnnotationResponse:
        """Save classification or object-detection annotations with full validation."""
        image = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image with ID '{image_id}' not found.",
            )

        dataset = db.query(Dataset).filter(Dataset.id == image.dataset_id).first()
        project = db.query(Project).filter(Project.id == dataset.project_id).first()

        # Find or create ImageAnnotation record
        annotation = (
            db.query(ImageAnnotation)
            .filter(ImageAnnotation.image_id == image_id)
            .first()
        )
        if not annotation:
            annotation = ImageAnnotation(
                dataset_id=dataset.id,
                image_id=image.id,
                task_type=req.task_type.value,
            )
            db.add(annotation)
            db.flush()

        annotation.is_negative = req.is_negative
        annotation.notes = req.notes
        annotation.updated_at = utc_now()

        computed_status = AnnotationStatus.UNANNOTATED

        # Clear existing children for fresh transactional assignment
        db.query(ClassificationAnnotation).filter(
            ClassificationAnnotation.image_annotation_id == annotation.id
        ).delete()
        db.query(ObjectAnnotation).filter(
            ObjectAnnotation.image_annotation_id == annotation.id
        ).delete()

        # 1. Classification Workflow
        if "Classification" in req.task_type.value:
            if req.label_ids:
                # Validate labels belong to project
                valid_labels = (
                    db.query(ProjectLabel)
                    .filter(
                        ProjectLabel.project_id == project.id,
                        ProjectLabel.id.in_(req.label_ids),
                    )
                    .all()
                )
                if len(valid_labels) != len(req.label_ids):
                    computed_status = AnnotationStatus.INVALID
                elif not project.is_multi_label and len(req.label_ids) > 1:
                    # Single-label mode violation
                    computed_status = AnnotationStatus.INVALID
                else:
                    computed_status = AnnotationStatus.ANNOTATED

                for lbl in valid_labels:
                    cls_ann = ClassificationAnnotation(
                        image_annotation_id=annotation.id,
                        label_id=lbl.id,
                    )
                    db.add(cls_ann)
            else:
                if req.is_negative:
                    computed_status = AnnotationStatus.ANNOTATED
                else:
                    computed_status = AnnotationStatus.UNANNOTATED

        # 2. Object Detection Workflow
        elif "Detection" in req.task_type.value or "Object" in req.task_type.value:
            if req.objects:
                has_invalid_box = False
                for box in req.objects:
                    # Validate label existence
                    lbl = (
                        db.query(ProjectLabel)
                        .filter(
                            ProjectLabel.id == box.label_id,
                            ProjectLabel.project_id == project.id,
                        )
                        .first()
                    )
                    if not lbl:
                        has_invalid_box = True
                        continue

                    # Clamp coordinates to [0, 1]
                    x_min = max(0.0, min(1.0, float(box.x_min)))
                    y_min = max(0.0, min(1.0, float(box.y_min)))
                    x_max = max(0.0, min(1.0, float(box.x_max)))
                    y_max = max(0.0, min(1.0, float(box.y_max)))

                    # Ensure coordinates order and non-zero area
                    if x_min >= x_max or y_min >= y_max:
                        has_invalid_box = True
                        continue
                    area = (x_max - x_min) * (y_max - y_min)
                    if area < 0.00001:
                        has_invalid_box = True
                        continue

                    obj_ann = ObjectAnnotation(
                        image_annotation_id=annotation.id,
                        label_id=lbl.id,
                        x_min=round(x_min, 6),
                        y_min=round(y_min, 6),
                        x_max=round(x_max, 6),
                        y_max=round(y_max, 6),
                        confidence=box.confidence,
                    )
                    db.add(obj_ann)

                if has_invalid_box:
                    computed_status = AnnotationStatus.INVALID
                else:
                    computed_status = AnnotationStatus.ANNOTATED
            else:
                if req.is_negative:
                    computed_status = AnnotationStatus.ANNOTATED
                else:
                    computed_status = AnnotationStatus.UNANNOTATED
        else:
            computed_status = AnnotationStatus.ANNOTATED

        # Respect explicit review status if requested by user
        if req.status == AnnotationStatus.NEEDS_REVIEW:
            computed_status = AnnotationStatus.NEEDS_REVIEW
        elif req.status == AnnotationStatus.INVALID:
            computed_status = AnnotationStatus.INVALID

        annotation.status = computed_status.value
        db.commit()
        db.refresh(annotation)

        # Update dataset.annotation_count
        cls._update_dataset_annotation_count(db, dataset.id)

        return cls._build_response(annotation)

    @classmethod
    def mark_negative(cls, db: Session, image_id: str, is_negative: bool) -> ImageAnnotationResponse:
        """Explicitly confirm an image as containing no target objects."""
        image = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        dataset = db.query(Dataset).filter(Dataset.id == image.dataset_id).first()
        annotation = (
            db.query(ImageAnnotation)
            .filter(ImageAnnotation.image_id == image_id)
            .first()
        )
        if not annotation:
            project = db.query(Project).filter(Project.id == dataset.project_id).first()
            annotation = ImageAnnotation(
                dataset_id=dataset.id,
                image_id=image.id,
                task_type=project.task_type,
            )
            db.add(annotation)
            db.flush()

        annotation.is_negative = is_negative
        if is_negative:
            # If negative, clear any object annotations
            db.query(ObjectAnnotation).filter(
                ObjectAnnotation.image_annotation_id == annotation.id
            ).delete()
            annotation.status = AnnotationStatus.ANNOTATED.value
        else:
            # Recheck status
            has_objs = db.query(ObjectAnnotation).filter(
                ObjectAnnotation.image_annotation_id == annotation.id
            ).count() > 0
            annotation.status = AnnotationStatus.ANNOTATED.value if has_objs else AnnotationStatus.UNANNOTATED.value

        annotation.updated_at = utc_now()
        db.commit()
        db.refresh(annotation)

        cls._update_dataset_annotation_count(db, dataset.id)
        return cls._build_response(annotation)

    @classmethod
    def mark_review(cls, db: Session, image_id: str, needs_review: bool) -> ImageAnnotationResponse:
        """Mark or unmark an image for review."""
        annotation = (
            db.query(ImageAnnotation)
            .filter(ImageAnnotation.image_id == image_id)
            .first()
        )
        if not annotation:
            # Create annotation first
            cls.get_or_create_annotation(db, image_id)
            annotation = (
                db.query(ImageAnnotation)
                .filter(ImageAnnotation.image_id == image_id)
                .first()
            )

        if needs_review:
            annotation.status = AnnotationStatus.NEEDS_REVIEW.value
        else:
            # Recompute valid vs unannotated
            has_objs = db.query(ObjectAnnotation).filter(
                ObjectAnnotation.image_annotation_id == annotation.id
            ).count() > 0
            has_cls = db.query(ClassificationAnnotation).filter(
                ClassificationAnnotation.image_annotation_id == annotation.id
            ).count() > 0
            if has_objs or has_cls or annotation.is_negative:
                annotation.status = AnnotationStatus.ANNOTATED.value
            else:
                annotation.status = AnnotationStatus.UNANNOTATED.value

        annotation.updated_at = utc_now()
        db.commit()
        db.refresh(annotation)

        cls._update_dataset_annotation_count(db, annotation.dataset_id)
        return cls._build_response(annotation)

    @classmethod
    def get_dataset_annotation_summary(cls, db: Session, dataset_id: str) -> DatasetAnnotationSummary:
        dataset = DatasetService.get_dataset_by_id(db, dataset_id)

        total_images = db.query(ImageRecord).filter(ImageRecord.dataset_id == dataset_id).count()

        # Query counts grouped by status
        annotations = (
            db.query(ImageAnnotation)
            .filter(ImageAnnotation.dataset_id == dataset_id)
            .all()
        )

        annotated_count = 0
        needs_review_count = 0
        invalid_count = 0

        for a in annotations:
            if a.status == AnnotationStatus.ANNOTATED.value:
                annotated_count += 1
            elif a.status == AnnotationStatus.NEEDS_REVIEW.value:
                needs_review_count += 1
            elif a.status == AnnotationStatus.INVALID.value:
                invalid_count += 1

        unannotated_count = max(0, total_images - annotated_count - needs_review_count - invalid_count)

        completion_pct = 0.0
        if total_images > 0:
            completion_pct = round(((annotated_count + needs_review_count) / total_images) * 100, 1)

        # Class distribution
        class_dist: Dict[str, int] = {}
        # 1. From object annotations
        obj_counts = (
            db.query(ProjectLabel.name, func.count(ObjectAnnotation.id))
            .join(ObjectAnnotation, ProjectLabel.id == ObjectAnnotation.label_id)
            .join(ImageAnnotation, ObjectAnnotation.image_annotation_id == ImageAnnotation.id)
            .filter(ImageAnnotation.dataset_id == dataset_id)
            .group_by(ProjectLabel.name)
            .all()
        )
        for name, count in obj_counts:
            class_dist[name] = class_dist.get(name, 0) + count

        # 2. From classification annotations
        cls_counts = (
            db.query(ProjectLabel.name, func.count(ClassificationAnnotation.id))
            .join(ClassificationAnnotation, ProjectLabel.id == ClassificationAnnotation.label_id)
            .join(ImageAnnotation, ClassificationAnnotation.image_annotation_id == ImageAnnotation.id)
            .filter(ImageAnnotation.dataset_id == dataset_id)
            .group_by(ProjectLabel.name)
            .all()
        )
        for name, count in cls_counts:
            class_dist[name] = class_dist.get(name, 0) + count

        return DatasetAnnotationSummary(
            dataset_id=dataset_id,
            total_images=total_images,
            annotated_images=annotated_count,
            unannotated_images=unannotated_count,
            needs_review_images=needs_review_count,
            invalid_images=invalid_count,
            completion_percentage=completion_pct,
            class_distribution=class_dist,
        )

    @classmethod
    def list_annotated_images(
        cls,
        db: Session,
        dataset_id: str,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedAnnotatedImages:
        DatasetService.get_dataset_by_id(db, dataset_id)

        query = (
            db.query(ImageRecord, ImageAnnotation)
            .outerjoin(ImageAnnotation, ImageRecord.id == ImageAnnotation.image_id)
            .filter(ImageRecord.dataset_id == dataset_id)
        )

        if search and search.strip():
            query = query.filter(ImageRecord.relative_path.ilike(f"%{search.strip()}%"))

        # Filtering by status
        if status_filter and status_filter.upper() != "ALL":
            filter_val = status_filter.upper()
            if filter_val == "UNANNOTATED":
                query = query.filter(
                    (ImageAnnotation.id == None) | (ImageAnnotation.status == "UNANNOTATED")
                )
            else:
                query = query.filter(ImageAnnotation.status == filter_val)

        total = query.count()
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size

        records = query.order_by(ImageRecord.relative_path.asc()).offset(offset).limit(page_size).all()

        items: List[AnnotatedImageItem] = []
        for img, ann in records:
            assigned_labels = []
            ann_count = 0
            is_negative = False
            ann_status = AnnotationStatus.UNANNOTATED
            updated_at = None
            notes = None

            if ann:
                ann_status = AnnotationStatus(ann.status)
                is_negative = ann.is_negative
                updated_at = ann.updated_at
                notes = ann.notes

                # Collect label names
                for ca in ann.classification_labels:
                    if ca.label:
                        assigned_labels.append(ca.label.name)
                        ann_count += 1
                for oa in ann.objects:
                    if oa.label and oa.label.name not in assigned_labels:
                        assigned_labels.append(oa.label.name)
                    ann_count += 1

            items.append(
                AnnotatedImageItem(
                    id=img.id,
                    dataset_id=dataset_id,
                    relative_path=img.relative_path,
                    file_size_bytes=img.file_size_bytes,
                    width=img.width,
                    height=img.height,
                    is_valid=img.is_valid,
                    status=ann_status,
                    is_negative=is_negative,
                    annotation_count=ann_count,
                    assigned_labels=assigned_labels,
                    notes=notes,
                    updated_at=updated_at,
                )
            )

        return PaginatedAnnotatedImages(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    def _update_dataset_annotation_count(cls, db: Session, dataset_id: str) -> None:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return

        completed_count = (
            db.query(ImageAnnotation)
            .filter(
                ImageAnnotation.dataset_id == dataset_id,
                ImageAnnotation.status.in_(["ANNOTATED", "NEEDS_REVIEW"]),
            )
            .count()
        )
        dataset.annotation_count = completed_count
        db.commit()

    @classmethod
    def _build_response(cls, annotation: ImageAnnotation) -> ImageAnnotationResponse:
        labels_resp: List[LabelResponse] = []
        label_ids: List[str] = []
        for ca in annotation.classification_labels:
            if ca.label:
                labels_resp.append(LabelResponse.model_validate(ca.label))
                label_ids.append(ca.label.id)

        objects_resp: List[BoundingBoxResponse] = []
        for oa in annotation.objects:
            if oa.label:
                objects_resp.append(
                    BoundingBoxResponse(
                        id=oa.id,
                        label_id=oa.label_id,
                        label_name=oa.label.name,
                        label_color=oa.label.color,
                        x_min=oa.x_min,
                        y_min=oa.y_min,
                        x_max=oa.x_max,
                        y_max=oa.y_max,
                        confidence=oa.confidence,
                    )
                )

        return ImageAnnotationResponse(
            id=annotation.id,
            dataset_id=annotation.dataset_id,
            image_id=annotation.image_id,
            task_type=annotation.task_type,
            status=AnnotationStatus(annotation.status),
            is_negative=annotation.is_negative,
            label_ids=label_ids,
            labels=labels_resp,
            objects=objects_resp,
            notes=annotation.notes,
            created_at=annotation.created_at,
            updated_at=annotation.updated_at,
        )
