from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from backend.app.domain.models import Project, ProjectLabel, ClassificationAnnotation, ObjectAnnotation
from backend.app.schemas.label import LabelCreate, LabelUpdate, LabelResponse
from backend.app.services.project_service import ProjectService


class LabelService:
    """Service handling business rules for Project Labels."""

    @classmethod
    def create_label(cls, db: Session, project_id: str, label_in: LabelCreate) -> LabelResponse:
        # Verify project exists
        ProjectService.get_project_by_id(db, project_id)

        name = label_in.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Label name cannot be empty.",
            )

        # Check duplicate name case-insensitively within the same project
        existing = (
            db.query(ProjectLabel)
            .filter(
                ProjectLabel.project_id == project_id,
                func.lower(ProjectLabel.name) == name.lower(),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A label named '{name}' already exists in this project.",
            )

        label = ProjectLabel(
            project_id=project_id,
            name=name,
            color=label_in.color or "#6366f1",
            description=label_in.description,
        )
        db.add(label)
        db.commit()
        db.refresh(label)

        resp = LabelResponse.model_validate(label)
        resp.annotation_count = 0
        return resp

    @classmethod
    def list_labels(cls, db: Session, project_id: str) -> List[LabelResponse]:
        ProjectService.get_project_by_id(db, project_id)

        labels = (
            db.query(ProjectLabel)
            .filter(ProjectLabel.project_id == project_id)
            .order_by(ProjectLabel.created_at.asc())
            .all()
        )

        results = []
        for lbl in labels:
            # Count references in both classification and object annotations
            cls_count = (
                db.query(ClassificationAnnotation)
                .filter(ClassificationAnnotation.label_id == lbl.id)
                .count()
            )
            obj_count = (
                db.query(ObjectAnnotation)
                .filter(ObjectAnnotation.label_id == lbl.id)
                .count()
            )
            resp = LabelResponse.model_validate(lbl)
            resp.annotation_count = cls_count + obj_count
            results.append(resp)

        return results

    @classmethod
    def get_label_by_id(cls, db: Session, label_id: str) -> ProjectLabel:
        label = db.query(ProjectLabel).filter(ProjectLabel.id == label_id).first()
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Label with ID '{label_id}' not found.",
            )
        return label

    @classmethod
    def update_label(cls, db: Session, label_id: str, label_in: LabelUpdate) -> LabelResponse:
        label = cls.get_label_by_id(db, label_id)

        if label_in.name is not None:
            new_name = label_in.name.strip()
            if not new_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Label name cannot be empty.",
                )
            if new_name.lower() != label.name.lower():
                existing = (
                    db.query(ProjectLabel)
                    .filter(
                        ProjectLabel.project_id == label.project_id,
                        func.lower(ProjectLabel.name) == new_name.lower(),
                    )
                    .first()
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"A label named '{new_name}' already exists in this project.",
                    )
            label.name = new_name

        if label_in.color is not None:
            label.color = label_in.color.strip()

        if label_in.description is not None:
            label.description = label_in.description

        db.commit()
        db.refresh(label)

        cls_count = (
            db.query(ClassificationAnnotation)
            .filter(ClassificationAnnotation.label_id == label.id)
            .count()
        )
        obj_count = (
            db.query(ObjectAnnotation)
            .filter(ObjectAnnotation.label_id == label.id)
            .count()
        )
        resp = LabelResponse.model_validate(label)
        resp.annotation_count = cls_count + obj_count
        return resp

    @classmethod
    def delete_label(cls, db: Session, label_id: str) -> None:
        label = cls.get_label_by_id(db, label_id)

        cls_count = (
            db.query(ClassificationAnnotation)
            .filter(ClassificationAnnotation.label_id == label.id)
            .count()
        )
        obj_count = (
            db.query(ObjectAnnotation)
            .filter(ObjectAnnotation.label_id == label.id)
            .count()
        )
        total_references = cls_count + obj_count

        if total_references > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot delete label '{label.name}' because it is referenced by "
                    f"{total_references} annotation(s). Please delete or reassign those annotations first."
                ),
            )

        db.delete(label)
        db.commit()
