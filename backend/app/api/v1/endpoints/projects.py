from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from backend.app.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetListResponse,
)
from backend.app.services.project_service import ProjectService
from backend.app.services.dataset_service import DatasetService

router = APIRouter()


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: Optional[str] = Query(None, description="Search by name or description"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Retrieve all projects with optional filtering and pagination."""
    items, total = ProjectService.get_projects(
        db, search=search, task_type=task_type, skip=skip, limit=limit
    )
    result_items = []
    for item in items:
        resp = ProjectResponse.model_validate(item)
        resp.dataset_count = len(item.datasets)
        result_items.append(resp)
    return ProjectListResponse(items=result_items, total=total)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    project = ProjectService.create_project(db, project_in)
    resp = ProjectResponse.model_validate(project)
    resp.dataset_count = 0
    return resp


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get project details by ID."""
    project = ProjectService.get_project_by_id(db, project_id)
    resp = ProjectResponse.model_validate(project)
    resp.dataset_count = len(project.datasets)
    return resp


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str, project_in: ProjectUpdate, db: Session = Depends(get_db)
):
    """Update project details."""
    project = ProjectService.update_project(db, project_id, project_in)
    resp = ProjectResponse.model_validate(project)
    resp.dataset_count = len(project.datasets)
    return resp


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete project and associated dataset metadata."""
    ProjectService.delete_project(db, project_id)
    return None


@router.get("/{project_id}/datasets", response_model=DatasetListResponse)
def list_project_datasets(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List all datasets associated with a specific project."""
    items, total = DatasetService.get_datasets_by_project(
        db, project_id, skip=skip, limit=limit
    )
    return DatasetListResponse(
        items=[DatasetResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post(
    "/{project_id}/datasets",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_dataset(
    project_id: str,
    dataset_in: DatasetCreate,
    db: Session = Depends(get_db),
):
    """Import or link a dataset into a project."""
    dataset = DatasetService.create_dataset(db, project_id, dataset_in)
    return DatasetResponse.model_validate(dataset)
