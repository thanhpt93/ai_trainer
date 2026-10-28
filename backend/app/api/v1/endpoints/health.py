import os
import sys
import psutil
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.schemas.health import (
    HealthResponse,
    SystemInfoResponse,
    DashboardStatsResponse,
    HardwareInfoResponse,
    CUDADeviceInfo,
)
from backend.app.schemas.project import ProjectResponse
from backend.app.domain.models import Project, Dataset, ImageRecord, TrainingJob

router = APIRouter()

# Cache static system info to keep API snappy
_CACHED_CUDA_INFO = None


def get_cuda_status():
    global _CACHED_CUDA_INFO
    if _CACHED_CUDA_INFO is None:
        try:
            import torch
            is_avail = torch.cuda.is_available()
            name = torch.cuda.get_device_name(0) if is_avail else None
            _CACHED_CUDA_INFO = (is_avail, name)
        except Exception:
            _CACHED_CUDA_INFO = (False, None)
    return _CACHED_CUDA_INFO


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """Health check endpoint to verify backend process and database readiness."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        database_connected=db_ok,
        app_data_dir=str(settings.APP_DATA_DIR),
    )


@router.get("/system-info", response_model=SystemInfoResponse)
def get_system_info():
    """Retrieve system, hardware, and environment capabilities."""
    cuda_available, cuda_name = get_cuda_status()
    mem = psutil.virtual_memory()

    return SystemInfoResponse(
        os=f"{os.name} ({sys.platform})",
        python_version=sys.version.split()[0],
        cpu_count=os.cpu_count() or 1,
        memory_total_gb=round(mem.total / (1024**3), 2),
        memory_available_gb=round(mem.available / (1024**3), 2),
        cuda_available=cuda_available,
        cuda_device_name=cuda_name,
        app_data_dir=str(settings.APP_DATA_DIR),
        database_path=str(settings.DATABASE_PATH),
    )


@router.get("/system/hardware", response_model=HardwareInfoResponse)
def get_hardware_info():
    """Detailed hardware and GPU telemetry for training preparation."""
    pytorch_version = "not_installed"
    cuda_available = False
    cuda_version = None
    gpu_devices = []

    try:
        import torch
        pytorch_version = torch.__version__
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            cuda_version = torch.version.cuda
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                free_bytes, total_bytes = torch.cuda.mem_get_info(i)
                gpu_devices.append(
                    CUDADeviceInfo(
                        index=i,
                        name=props.name,
                        total_memory_mb=round(total_bytes / (1024 * 1024), 1),
                        free_memory_mb=round(free_bytes / (1024 * 1024), 1),
                        compute_capability=f"{props.major}.{props.minor}",
                    )
                )
    except Exception:
        pass

    mem = psutil.virtual_memory()
    available_devices = ["cpu"]
    if cuda_available and len(gpu_devices) > 0:
        available_devices.insert(0, "cuda")

    return HardwareInfoResponse(
        os=f"{os.name} ({sys.platform})",
        python_version=sys.version.split()[0],
        pytorch_version=pytorch_version,
        cpu_count_logical=os.cpu_count() or 1,
        cpu_count_physical=psutil.cpu_count(logical=False) or 1,
        system_memory_total_gb=round(mem.total / (1024**3), 2),
        system_memory_available_gb=round(mem.available / (1024**3), 2),
        cuda_available=cuda_available,
        cuda_version=cuda_version,
        gpu_devices=gpu_devices,
        recommended_device="cuda" if cuda_available else "cpu",
        available_devices=available_devices,
    )


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Returns actual persisted counts and recent projects for the dashboard.
    Does not return fabricated training runs or fake metrics.
    """
    total_projects = db.query(Project).count()
    total_datasets = db.query(Dataset).count()
    total_images = db.query(ImageRecord).count()
    
    # Real count of active jobs
    running_jobs = db.query(TrainingJob).filter(
        TrainingJob.status.in_(["RUNNING", "PREPARING"])
    ).count()

    recent = db.query(Project).order_by(Project.updated_at.desc()).limit(5).all()
    recent_responses = []
    for p in recent:
        resp = ProjectResponse.model_validate(p)
        resp.dataset_count = len(p.datasets)
        recent_responses.append(resp)

    return DashboardStatsResponse(
        total_projects=total_projects,
        total_datasets=total_datasets,
        total_indexed_images=total_images,
        running_training_jobs=running_jobs,
        recent_projects=recent_responses,
    )
