from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class DatasetFormat(str, Enum):
    FOLDER_IMAGES = "folder_images"
    COCO = "coco"
    YOLO = "yolo"
    PASCAL_VOC = "pascal_voc"


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, max_length=2000)
    root_path: str = Field(..., description="Absolute path to the image directory")
    format: DatasetFormat = Field(default=DatasetFormat.FOLDER_IMAGES)
    is_linked: bool = Field(default=True, description="True if referencing source directory, False if copied")


class DatasetCreate(DatasetBase):
    scan_immediately: bool = Field(default=True, description="Whether to scan images immediately upon creation")


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ImageRecordResponse(BaseModel):
    id: str
    dataset_id: str
    relative_path: str
    absolute_path: str
    file_size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    channels: Optional[int] = None
    format: Optional[str] = None
    is_valid: bool
    error_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetResponse(DatasetBase):
    id: str
    project_id: str
    image_count: int = 0
    annotation_count: int = 0
    valid_image_count: int = 0
    corrupted_image_count: int = 0
    unsupported_file_count: int = 0
    last_scanned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    schema_version: int = 1

    model_config = ConfigDict(from_attributes=True)


class DatasetListResponse(BaseModel):
    items: List[DatasetResponse]
    total: int


class DatasetScanResult(BaseModel):
    dataset_id: str
    scanned_files: int
    valid_images: int
    corrupted_images: int
    unsupported_files: int
    duration_seconds: float
    message: str


class PaginatedImagesResponse(BaseModel):
    items: List[ImageRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
