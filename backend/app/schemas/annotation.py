from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.label import LabelResponse
from backend.app.schemas.project import TaskType


class AnnotationStatus(str, Enum):
    UNANNOTATED = "UNANNOTATED"
    ANNOTATED = "ANNOTATED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INVALID = "INVALID"


class BoundingBoxCreate(BaseModel):
    label_id: str
    x_min: float = Field(..., ge=0.0, le=1.0, description="Normalized top-left X [0, 1]")
    y_min: float = Field(..., ge=0.0, le=1.0, description="Normalized top-left Y [0, 1]")
    x_max: float = Field(..., ge=0.0, le=1.0, description="Normalized bottom-right X [0, 1]")
    y_max: float = Field(..., ge=0.0, le=1.0, description="Normalized bottom-right Y [0, 1]")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class BoundingBoxResponse(BaseModel):
    id: str
    label_id: str
    label_name: str
    label_color: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    confidence: float = 1.0

    model_config = ConfigDict(from_attributes=True)


class ImageAnnotationSaveRequest(BaseModel):
    task_type: TaskType
    is_negative: bool = Field(default=False, description="Mark as confirmed negative image (no target objects)")
    status: Optional[AnnotationStatus] = None
    label_ids: List[str] = Field(default_factory=list, description="Assigned label IDs for classification")
    objects: List[BoundingBoxCreate] = Field(default_factory=list, description="Bounding boxes for object detection")
    notes: Optional[str] = None


class ImageAnnotationResponse(BaseModel):
    id: str
    dataset_id: str
    image_id: str
    task_type: str
    status: AnnotationStatus
    is_negative: bool
    label_ids: List[str] = []
    labels: List[LabelResponse] = []
    objects: List[BoundingBoxResponse] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetAnnotationSummary(BaseModel):
    dataset_id: str
    total_images: int
    annotated_images: int
    unannotated_images: int
    needs_review_images: int
    invalid_images: int
    completion_percentage: float
    class_distribution: Dict[str, int]


class AnnotatedImageItem(BaseModel):
    id: str
    dataset_id: str
    relative_path: str
    file_size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    is_valid: bool
    status: AnnotationStatus
    is_negative: bool
    annotation_count: int
    assigned_labels: List[str]
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class PaginatedAnnotatedImages(BaseModel):
    items: List[AnnotatedImageItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExportFormat(str, Enum):
    YOLO = "yolo"
    COCO = "coco"
    PASCAL_VOC = "pascal_voc"
    CSV = "csv"
    JSON = "json"


class ExportRequest(BaseModel):
    format: ExportFormat
    output_dir: Optional[str] = None
    include_unannotated: bool = False


class ExportResponse(BaseModel):
    export_path: str
    format: str
    total_exported: int
    message: str
