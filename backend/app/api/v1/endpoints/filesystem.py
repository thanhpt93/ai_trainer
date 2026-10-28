import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.app.services.path_validator import PathValidator
from backend.app.core.config import settings

router = APIRouter()


class PathValidationRequest(BaseModel):
    path: str


class DirectoryEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class PathValidationResponse(BaseModel):
    is_valid: bool
    resolved_path: str
    exists: bool
    is_directory: bool
    is_readable: bool
    error_message: Optional[str] = None
    subdirectories: List[str] = []
    estimated_image_count: int = 0


@router.post("/validate-path", response_model=PathValidationResponse)
def validate_directory_path(req: PathValidationRequest):
    """
    Validate a directory path and provide quick inspection information.
    Prohibits scanning arbitrary restricted system locations.
    """
    try:
        resolved = PathValidator.validate_and_resolve_directory(
            req.path, must_exist=True, create_if_missing=False
        )
    except HTTPException as e:
        return PathValidationResponse(
            is_valid=False,
            resolved_path=req.path,
            exists=False,
            is_directory=False,
            is_readable=False,
            error_message=e.detail,
        )
    except Exception as e:
        return PathValidationResponse(
            is_valid=False,
            resolved_path=req.path,
            exists=False,
            is_directory=False,
            is_readable=False,
            error_message=str(e),
        )

    # Subdirectories inspection (up to 20 for preview)
    subdirs: List[str] = []
    img_count = 0
    try:
        with os.scandir(str(resolved)) as entries:
            for entry in entries:
                if entry.is_dir() and len(subdirs) < 20:
                    subdirs.append(entry.name)
                elif entry.is_file():
                    suffix = Path(entry.name).suffix.lower()
                    if suffix in settings.SUPPORTED_IMAGE_EXTENSIONS:
                        img_count += 1
    except Exception:
        pass

    return PathValidationResponse(
        is_valid=True,
        resolved_path=str(resolved),
        exists=True,
        is_directory=True,
        is_readable=True,
        subdirectories=subdirs,
        estimated_image_count=img_count,
    )
