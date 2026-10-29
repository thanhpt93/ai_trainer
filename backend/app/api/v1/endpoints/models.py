import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.domain.models import ModelArtifact
from backend.app.schemas.model_artifact import (
    ModelArtifactResponse,
    ModelArtifactCreate,
    ExportModelRequest,
    ExportModelResponse,
)
from backend.app.services.training_manager import TrainingManager

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


@router.get("/{model_id}/artifacts")
def get_model_artifact_files(
    model_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve exported file list and metadata details for a registered model."""
    art = db.query(ModelArtifact).filter(ModelArtifact.id == model_id).first()
    if not art:
        raise HTTPException(status_code=404, detail=f"Model artifact '{model_id}' not found.")

    manifest_data = {}
    if art.artifact_path:
        export_dir = Path(art.artifact_path).parent
        manifest_file = export_dir / "export_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
            except Exception:
                pass

    return {
        "model_id": art.id,
        "name": art.name,
        "task_type": art.task_type,
        "artifact_path": art.artifact_path,
        "metadata_path": art.metadata_path,
        "checksum_sha256": art.checksum_sha256,
        "file_size_bytes": art.file_size_bytes,
        "manifest": manifest_data,
    }


@router.post("/{model_id}/export", response_model=ExportModelResponse)
def export_registered_model(
    model_id: str,
    req: ExportModelRequest,
    db: Session = Depends(get_db),
):
    """Export or re-export a registered model to ONNX."""
    art = db.query(ModelArtifact).filter(ModelArtifact.id == model_id).first()
    if not art:
        raise HTTPException(status_code=404, detail=f"Model artifact '{model_id}' not found.")

    if not art.training_job_id:
        raise HTTPException(status_code=400, detail="Model artifact has no associated training job to export from.")

    return TrainingManager.export_model_artifact(db, art.training_job_id, req)


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
