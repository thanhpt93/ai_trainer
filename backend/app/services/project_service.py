import re
from pathlib import Path
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.domain.models import (
    Project,
    Dataset,
    ImageRecord,
    ImageAnnotation,
    ClassificationAnnotation,
    ObjectAnnotation,
    TrainingJob,
    ModelArtifact,
    ProjectLabel,
)
from backend.app.schemas.project import ProjectCreate, ProjectUpdate
from backend.app.services.path_validator import PathValidator


def sanitize_filename(name: str) -> str:
    """Sanitize a name for safe directory naming."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return clean.replace(" ", "_") or "project"


class ProjectService:
    """Service handling business rules for Projects."""

    @classmethod
    def create_project(cls, db: Session, project_in: ProjectCreate) -> Project:
        name = project_in.name.strip()
        # Check duplicate name
        existing = db.query(Project).filter(func.lower(Project.name) == name.lower()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A project with the name '{name}' already exists.",
            )

        # Resolve or generate root path
        if project_in.root_path and project_in.root_path.strip():
            root_dir = PathValidator.validate_and_resolve_directory(
                project_in.root_path.strip(),
                must_exist=False,
                create_if_missing=True,
            )
        else:
            folder_name = sanitize_filename(name)
            root_dir = settings.PROJECTS_DEFAULT_DIR / folder_name
            root_dir.mkdir(parents=True, exist_ok=True)

        project = Project(
            name=name,
            description=project_in.description,
            task_type=project_in.task_type.value,
            root_path=str(root_dir),
            is_multi_label=project_in.is_multi_label,
            allow_negative_images=project_in.allow_negative_images,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @classmethod
    def get_projects(
        cls,
        db: Session,
        search: Optional[str] = None,
        task_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Project], int]:
        query = db.query(Project)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                (Project.name.ilike(search_term)) | (Project.description.ilike(search_term))
            )

        if task_type:
            query = query.filter(Project.task_type == task_type)

        total = query.count()
        items = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @classmethod
    def get_project_by_id(cls, db: Session, project_id: str) -> Project:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found.",
            )
        return project

    @classmethod
    def update_project(cls, db: Session, project_id: str, project_in: ProjectUpdate) -> Project:
        project = cls.get_project_by_id(db, project_id)

        if project_in.name is not None:
            new_name = project_in.name.strip()
            if new_name.lower() != project.name.lower():
                existing = db.query(Project).filter(func.lower(Project.name) == new_name.lower()).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"A project with the name '{new_name}' already exists.",
                    )
            project.name = new_name

        if project_in.description is not None:
            project.description = project_in.description

        if project_in.task_type is not None:
            project.task_type = project_in.task_type.value

        if project_in.is_multi_label is not None:
            project.is_multi_label = project_in.is_multi_label

        if project_in.allow_negative_images is not None:
            project.allow_negative_images = project_in.allow_negative_images

        if project_in.root_path is not None and project_in.root_path.strip():
            root_dir = PathValidator.validate_and_resolve_directory(
                project_in.root_path.strip(),
                must_exist=False,
                create_if_missing=True,
            )
            project.root_path = str(root_dir)

        db.commit()
        db.refresh(project)
        return project

    @classmethod
    def delete_project(cls, db: Session, project_id: str) -> None:
        project = cls.get_project_by_id(db, project_id)

        # 1. Terminate any active background training worker processes for this project
        running_jobs = (
            db.query(TrainingJob)
            .filter(
                TrainingJob.project_id == project.id,
                TrainingJob.status.in_(["RUNNING", "PREPARING", "QUEUED"]),
            )
            .all()
        )
        for rj in running_jobs:
            if rj.pid:
                try:
                    import psutil
                    proc = psutil.Process(rj.pid)
                    proc.kill()
                except Exception:
                    pass
            rj.status = "CANCELLED"

        # 2. Find all datasets under this project
        dataset_ids = [d.id for d in db.query(Dataset.id).filter(Dataset.project_id == project.id).all()]
        if dataset_ids:
            # Query all image annotations under these datasets
            image_ann_ids = [
                ia.id
                for ia in db.query(ImageAnnotation.id).filter(ImageAnnotation.dataset_id.in_(dataset_ids)).all()
            ]
            if image_ann_ids:
                # Delete classification and object annotations first to resolve SQLite ON DELETE RESTRICT on project_labels
                db.query(ClassificationAnnotation).filter(
                    ClassificationAnnotation.image_annotation_id.in_(image_ann_ids)
                ).delete(synchronize_session=False)
                db.query(ObjectAnnotation).filter(
                    ObjectAnnotation.image_annotation_id.in_(image_ann_ids)
                ).delete(synchronize_session=False)

            db.query(ImageAnnotation).filter(ImageAnnotation.dataset_id.in_(dataset_ids)).delete(
                synchronize_session=False
            )
            db.query(ImageRecord).filter(ImageRecord.dataset_id.in_(dataset_ids)).delete(synchronize_session=False)

        # 3. Clean up model artifacts associated with the project
        db.query(ModelArtifact).filter(ModelArtifact.project_id == project.id).delete(synchronize_session=False)

        # 4. Clean up training jobs
        db.query(TrainingJob).filter(TrainingJob.project_id == project.id).delete(synchronize_session=False)

        # 5. Clean up datasets
        db.query(Dataset).filter(Dataset.project_id == project.id).delete(synchronize_session=False)

        # 6. Clean up project labels (safe now as child annotations are already deleted)
        db.query(ProjectLabel).filter(ProjectLabel.project_id == project.id).delete(synchronize_session=False)

        # 7. Delete the project record (original raw image files on disk are preserved)
        db.delete(project)
        db.commit()
