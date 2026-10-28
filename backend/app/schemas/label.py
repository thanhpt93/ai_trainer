from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LabelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Label/class name")
    color: str = Field(default="#6366f1", max_length=30, description="Hex color or CSS color string")
    description: Optional[str] = Field(None, max_length=1000, description="Optional class description")


class LabelCreate(LabelBase):
    pass


class LabelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    color: Optional[str] = Field(None, max_length=30)
    description: Optional[str] = Field(None, max_length=1000)


class LabelResponse(LabelBase):
    id: str
    project_id: str
    annotation_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabelListResponse(BaseModel):
    items: List[LabelResponse]
    total: int
