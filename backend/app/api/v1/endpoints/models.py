from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.domain.models import ModelArtifact
from backend.app.schemas.model_artifact import (
    ModelArtifactResponse,
    ModelArtifactCreate,
)

router = APIRouter()


@router.get("/", response_model=List[ModelArtifactResponse])
def list_registered_models(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    db: Session = Depends(get_db),
):
    """List all registered and exported model artifacts in the Model Registry."""
    query = db.query(ModelArtifact)
    if project_id:
        query = query.filter(ModelArtifact.project_id == project_id)
    artifacts = query.order_by(ModelArtifact.created_at.desc()).all()
    return [ModelArtifactResponse.model_validate(a) for a in artifacts]


@router.get("/{model_id}", response_model=ModelArtifactResponse)
def get_registered_model(
    model_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details, metrics summary, and export paths of a model artifact."""
    art = db.query(ModelArtifact).filter(ModelArtifact.id == model_id).first()
    if not art:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact '{model_id}' not found.",
        )
    return ModelArtifactResponse.model_validate(art)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registered_model(
    model_id: str,
    db: Session = Depends(get_db),
):
    """Delete a model artifact record from registry."""
    art = db.query(ModelArtifact).filter(ModelArtifact.id == model_id).first()
    if not art:
        raise HTTPException(status_code=404, detail="Model artifact not found.")
    db.delete(art)
    db.commit()
    return None
