import os
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


class PathValidator:
    """Service to safely validate filesystem paths for projects and datasets."""

    DANGEROUS_SYSTEM_ROOTS = {
        "c:\\",
        "c:\\windows",
        "c:\\program files",
        "c:\\program files (x86)",
        "/",
        "/etc",
        "/bin",
        "/usr",
        "/var",
        "/sys",
        "/proc",
    }

    @classmethod
    def validate_and_resolve_directory(
        cls,
        path_str: str,
        must_exist: bool = True,
        create_if_missing: bool = False,
    ) -> Path:
        """
        Validates that a path string is safe, valid, normalized, and accessible.
        
        Args:
            path_str: User-supplied path string
            must_exist: Whether the directory must already exist
            create_if_missing: Whether to create the directory if it does not exist
            
        Returns:
            Resolved absolute Path object
            
        Raises:
            HTTPException with status 400 if validation fails
        """
        if not path_str or not path_str.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path cannot be empty.",
            )

        # Disallow null bytes
        if "\0" in path_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path contains illegal null bytes.",
            )

        try:
            path_obj = Path(path_str).expanduser().resolve()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid path syntax: {str(e)}",
            )

        # Prohibit scanning critical root directories directly
        normalized_str = str(path_obj).lower().rstrip("\\/")
        for root in cls.DANGEROUS_SYSTEM_ROOTS:
            if normalized_str == root.lower().rstrip("\\/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Selection of critical system root '{path_obj}' is prohibited for security.",
                )

        if must_exist:
            if not path_obj.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Directory does not exist: {path_obj}",
                )
            if not path_obj.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Specified path is a file, not a directory: {path_obj}",
                )
            # Verify read access
            if not os.access(str(path_obj), os.R_OK):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission denied: Directory is not readable: {path_obj}",
                )
        elif create_if_missing and not path_obj.exists():
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create directory {path_obj}: {str(e)}",
                )

        return path_obj
