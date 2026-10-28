import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.training_job import (
    TrainingJobCreate,
    TrainingJobResponse,
    DatasetValidationRequest,
    DatasetValidationResponse,
    EpochMetric,
)
from backend.app.schemas.model_artifact import (
    ModelCatalogItem,
    ExportModelRequest,
    ExportModelResponse,
)
from backend.app.services.model_catalog_service import ModelCatalogService
from backend.app.services.classification_dataset_adapter import ClassificationDatasetAdapter
from backend.app.services.training_manager import TrainingManager

router = APIRouter()


@router.get("/models", response_model=List[ModelCatalogItem])
def list_available_models():
    """Retrieve catalog of supported neural network architectures for classification."""
    return ModelCatalogService.list_models()


@router.post("/datasets/validate", response_model=DatasetValidationResponse)
def validate_dataset_for_training(
    req: DatasetValidationRequest,
    db: Session = Depends(get_db),
):
    """
    Validate annotations, class distributions, file readability, and build
    stratified split ratios before starting a training job.
    """
    resp, _ = ClassificationDatasetAdapter.validate_and_prepare_dataset(
        db=db,
        project_id=req.project_id,
        dataset_id=req.dataset_id,
        split_config=req.split_config,
    )
    return resp


@router.get("/jobs", response_model=List[TrainingJobResponse])
def list_training_jobs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List recent training jobs with live runtime statuses and best metrics."""
    return TrainingManager.list_jobs(db, project_id=project_id, limit=limit)


@router.post("/jobs", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
def create_training_job(
    req: TrainingJobCreate,
    db: Session = Depends(get_db),
):
    """Create and queue a new training job configuration snapshot."""
    return TrainingManager.create_job(db, req)


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
def get_training_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Get status, configuration, and best metrics for a training job."""
    return TrainingManager.get_job(db, job_id)


@router.post("/jobs/{job_id}/start", response_model=TrainingJobResponse)
def start_training_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    """
    Validate dataset and launch isolated worker process for training.
    Returns immediately with RUNNING job status.
    """
    return TrainingManager.start_job(db, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=TrainingJobResponse)
def cancel_training_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Request cooperative cancellation of a running training job."""
    return TrainingManager.cancel_job(db, job_id)


@router.get("/jobs/{job_id}/logs")
def get_training_job_logs(
    job_id: str,
    tail: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Fetch the latest stdout/stderr log lines from the training worker."""
    return TrainingManager.get_job_logs(db, job_id, tail_lines=tail)


@router.get("/jobs/{job_id}/metrics", response_model=List[EpochMetric])
def get_training_job_metrics(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve all epoch metrics (loss, accuracy, F1, lr, duration) for visualization."""
    job = TrainingManager.get_job(db, job_id)
    if not job.metrics_json:
        return []
    try:
        data = json.loads(job.metrics_json)
        return [EpochMetric(**m) for m in data]
    except Exception:
        return []


@router.get("/jobs/{job_id}/evaluations")
def get_training_job_evaluations(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve post-training evaluation metrics, confusion matrix, and misclassifications."""
    data = TrainingManager.get_job_evaluation(db, job_id)
    return data or {"status": "not_evaluated"}


@router.post("/jobs/{job_id}/export", response_model=ExportModelResponse)
def export_training_job_model(
    job_id: str,
    req: ExportModelRequest,
    db: Session = Depends(get_db),
):
    """Export the best trained checkpoint to a validated ONNX deployment package."""
    return TrainingManager.export_model_artifact(db, job_id, req)
