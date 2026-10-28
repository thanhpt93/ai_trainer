from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from backend.app.schemas.project import ProjectResponse


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    database_connected: bool
    app_data_dir: str


class CUDADeviceInfo(BaseModel):
    index: int
    name: str
    total_memory_mb: float
    free_memory_mb: float
    compute_capability: str


class HardwareInfoResponse(BaseModel):
    os: str
    python_version: str
    pytorch_version: str
    cpu_count_logical: int
    cpu_count_physical: Optional[int] = None
    system_memory_total_gb: float
    system_memory_available_gb: float
    cuda_available: bool
    cuda_version: Optional[str] = None
    gpu_devices: List[CUDADeviceInfo] = []
    recommended_device: str
    available_devices: List[str]


class SystemInfoResponse(BaseModel):
    os: str
    python_version: str
    cpu_count: int
    memory_total_gb: Optional[float] = None
    memory_available_gb: Optional[float] = None
    cuda_available: bool
    cuda_device_name: Optional[str] = None
    app_data_dir: str
    database_path: str


class DashboardStatsResponse(BaseModel):
    total_projects: int
    total_datasets: int
    total_indexed_images: int
    running_training_jobs: int
    recent_projects: List[ProjectResponse]
