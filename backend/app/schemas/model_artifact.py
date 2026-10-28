from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class ModelArtifactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    task_type: str = "Image Classification"
    version: str = Field(default="1.0.0")
    artifact_path: str
    framework: str = Field(default="PyTorch")
    export_format: str = Field(default="ONNX")
    metadata_path: Optional[str] = None
    project_id: Optional[str] = None
    dataset_id: Optional[str] = None
    training_job_id: Optional[str] = None
    model_architecture: Optional[str] = None
    metrics_summary_json: Optional[str] = None
    checksum_sha256: Optional[str] = None
    file_size_bytes: int = 0
    is_exported: bool = False


class ModelArtifactResponse(BaseModel):
    id: str
    name: str
    task_type: str
    version: str
    artifact_path: str
    framework: str
    export_format: str
    metadata_path: Optional[str] = None
    project_id: Optional[str] = None
    dataset_id: Optional[str] = None
    training_job_id: Optional[str] = None
    model_architecture: Optional[str] = None
    metrics_summary_json: Optional[str] = None
    checksum_sha256: Optional[str] = None
    file_size_bytes: int = 0
    is_exported: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelCatalogItem(BaseModel):
    id: str
    name: str
    architecture: str
    task_type: str = "Image Classification"
    description: str
    supported_input_sizes: List[int]
    default_input_size: int
    parameters_count_million: float
    pretrained_available: bool
    supported_devices: List[str]
    default_learning_rate: float
    default_batch_size: int
    export_formats: List[str]


class ExportModelRequest(BaseModel):
    format: str = Field(default="ONNX")
    input_size: int = Field(default=224)
    dynamic_batch: bool = Field(default=True)


class ExportModelResponse(BaseModel):
    success: bool
    artifact_id: str
    model_name: str
    export_dir: str
    onnx_file_path: str
    manifest_path: str
    metadata_path: str
    checksum_sha256: str
    file_size_bytes: int
    verified_with_inference: bool
    error: Optional[str] = None
