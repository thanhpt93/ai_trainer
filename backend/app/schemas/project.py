from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TaskType(str, Enum):
    IMAGE_CLASSIFICATION = "Image Classification"
    OBJECT_DETECTION = "Object Detection"
    IMAGE_SEGMENTATION = "Image Segmentation"
    OCR = "OCR"
    ANOMALY_DETECTION = "Anomaly Detection"
    KEYPOINT_DETECTION = "Keypoint Detection"
    IMAGE_SIMILARITY = "Image Similarity"


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Unique project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")
    task_type: TaskType = Field(..., description="Machine learning task type")
    root_path: Optional[str] = Field(None, description="Custom storage location or project root directory")
    is_multi_label: bool = Field(default=False, description="Multi-label classification mode")
    allow_negative_images: bool = Field(default=True, description="Allow images confirmed with 0 objects")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    task_type: Optional[TaskType] = None
    root_path: Optional[str] = None
    is_multi_label: Optional[bool] = None
    allow_negative_images: Optional[bool] = None


class ProjectResponse(ProjectBase):
    id: str
    root_path: str
    created_at: datetime
    updated_at: datetime
    schema_version: int = 1
    dataset_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
