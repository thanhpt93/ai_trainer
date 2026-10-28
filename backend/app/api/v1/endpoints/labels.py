from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.label import (
    LabelCreate,
    LabelUpdate,
    LabelResponse,
    LabelListResponse,
)
from backend.app.services.label_service import LabelService

router = APIRouter()


@router.get("/projects/{project_id}/labels", response_model=LabelListResponse)
def list_project_labels(project_id: str, db: Session = Depends(get_db)):
    """List all labels defined for a project along with usage count."""
    items = LabelService.list_labels(db, project_id)
    return LabelListResponse(items=items, total=len(items))


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_label(
    project_id: str,
    label_in: LabelCreate,
    db: Session = Depends(get_db),
):
    """Create a new label for a project (enforces case-insensitive uniqueness)."""
    return LabelService.create_label(db, project_id, label_in)


@router.patch("/labels/{label_id}", response_model=LabelResponse)
def update_label(
    label_id: str,
    label_in: LabelUpdate,
    db: Session = Depends(get_db),
):
    """Update label name, color, or description."""
    return LabelService.update_label(db, label_id, label_in)


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_label(label_id: str, db: Session = Depends(get_db)):
    """
    Delete a label.
    Fails with 409 Conflict if referenced by existing annotations to prevent dangling references.
    """
    LabelService.delete_label(db, label_id)
    return None
