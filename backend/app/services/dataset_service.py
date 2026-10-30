import math
from pathlib import Path
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.domain.models import (
    Project,
    Dataset,
    ImageRecord,
    ImageAnnotation,
    ClassificationAnnotation,
    ObjectAnnotation,
    TrainingJob,
    ModelArtifact,
)
from backend.app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetScanResult,
    PaginatedImagesResponse,
    ImageRecordResponse,
)
from backend.app.services.path_validator import PathValidator
from backend.app.services.dataset_scanner import DatasetScanner
from backend.app.services.project_service import ProjectService


class DatasetService:
    """Service handling business rules for Datasets and Image Records."""

    @classmethod
    def create_dataset(cls, db: Session, project_id: str, dataset_in: DatasetCreate) -> Dataset:
        # Verify parent project exists
        ProjectService.get_project_by_id(db, project_id)

        # Validate that the dataset source directory exists and is accessible
        resolved_path = PathValidator.validate_and_resolve_directory(
            dataset_in.root_path,
            must_exist=True,
            create_if_missing=False,
        )

        dataset = Dataset(
            project_id=project_id,
            name=dataset_in.name.strip(),
            description=dataset_in.description,
            root_path=str(resolved_path),
            format=dataset_in.format.value,
            is_linked=dataset_in.is_linked,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        if dataset_in.scan_immediately:
            DatasetScanner.scan_directory(db, dataset)
            db.refresh(dataset)

        return dataset

    @classmethod
    def get_datasets_by_project(
        cls,
        db: Session,
        project_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Dataset], int]:
        # Validate project exists
        ProjectService.get_project_by_id(db, project_id)

        query = db.query(Dataset).filter(Dataset.project_id == project_id)
        total = query.count()
        items = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @classmethod
    def get_all_datasets(
        cls,
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Dataset], int]:
        query = db.query(Dataset)
        total = query.count()
        items = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @classmethod
    def get_dataset_by_id(cls, db: Session, dataset_id: str) -> Dataset:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID '{dataset_id}' not found.",
            )
        return dataset

    @classmethod
    def update_dataset(cls, db: Session, dataset_id: str, dataset_in: DatasetUpdate) -> Dataset:
        dataset = cls.get_dataset_by_id(db, dataset_id)

        if dataset_in.name is not None:
            dataset.name = dataset_in.name.strip()
        if dataset_in.description is not None:
            dataset.description = dataset_in.description

        db.commit()
        db.refresh(dataset)
        return dataset

    @classmethod
    def delete_dataset(cls, db: Session, dataset_id: str) -> None:
        dataset = cls.get_dataset_by_id(db, dataset_id)

        # 1. Clean up child annotations and records cleanly
        image_ann_ids = [
            ia.id for ia in db.query(ImageAnnotation.id).filter(ImageAnnotation.dataset_id == dataset.id).all()
        ]
        if image_ann_ids:
            db.query(ClassificationAnnotation).filter(
                ClassificationAnnotation.image_annotation_id.in_(image_ann_ids)
            ).delete(synchronize_session=False)
            db.query(ObjectAnnotation).filter(
                ObjectAnnotation.image_annotation_id.in_(image_ann_ids)
            ).delete(synchronize_session=False)

        db.query(ImageAnnotation).filter(ImageAnnotation.dataset_id == dataset.id).delete(synchronize_session=False)
        db.query(ImageRecord).filter(ImageRecord.dataset_id == dataset.id).delete(synchronize_session=False)
        db.query(TrainingJob).filter(TrainingJob.dataset_id == dataset.id).delete(synchronize_session=False)
        db.query(ModelArtifact).filter(ModelArtifact.dataset_id == dataset.id).delete(synchronize_session=False)

        # 2. Delete dataset record (never delete original raw image files on disk)
        db.delete(dataset)
        db.commit()

    @classmethod
    def scan_dataset(cls, db: Session, dataset_id: str) -> dict:
        dataset = cls.get_dataset_by_id(db, dataset_id)

        # Verify directory is still present
        PathValidator.validate_and_resolve_directory(
            dataset.root_path,
            must_exist=True,
            create_if_missing=False,
        )

        result = DatasetScanner.scan_directory(db, dataset)
        return result

    @classmethod
    def get_dataset_images(
        cls,
        db: Session,
        dataset_id: str,
        is_valid: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedImagesResponse:
        # Validate dataset exists
        cls.get_dataset_by_id(db, dataset_id)

        query = db.query(ImageRecord).filter(ImageRecord.dataset_id == dataset_id)
        if is_valid is not None:
            query = query.filter(ImageRecord.is_valid == is_valid)

        total = query.count()
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size

        items = query.order_by(ImageRecord.created_at.asc()).offset(offset).limit(page_size).all()

        return PaginatedImagesResponse(
            items=[ImageRecordResponse.model_validate(img) for img in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
