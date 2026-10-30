import os
from pathlib import Path
from typing import Set
from pydantic import BaseModel, Field


def get_default_app_data_dir() -> Path:
    """Return default application data directory based on OS."""
    override = os.environ.get("NOVA_APP_DATA_DIR")
    if override:
        data_dir = Path(override)
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        data_dir = Path(base) / "NovaAITrainer"
    else:
        data_dir = Path.home() / ".nova_ai_trainer"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class Settings(BaseModel):
    """Application configuration settings."""

    APP_NAME: str = "NOVA AI Trainer"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Network / Host
    HOST: str = "127.0.0.1"  # Loopback only for desktop security
    PORT: int = Field(default_factory=lambda: int(os.environ.get("NOVA_PORT", "8000")))
    
    # Application Paths
    APP_DATA_DIR: Path = Field(default_factory=get_default_app_data_dir)
    
    # Supported image extensions
    SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
    }
    
    # Maximum batch size for database inserts during scans
    SCAN_BATCH_SIZE: int = 500

    @property
    def PROJECT_ROOT(self) -> Path:
        """Root directory of the application / codebase repository."""
        return Path(__file__).resolve().parent.parent.parent.parent

    @property
    def EXPORT_DIR(self) -> Path:
        """Default directory for exported models, located directly in the project directory."""
        override = os.environ.get("NOVA_EXPORT_DIR")
        if override:
            export_path = Path(override)
        else:
            export_path = self.PROJECT_ROOT / "export"
        export_path.mkdir(parents=True, exist_ok=True)
        return export_path

    @property
    def DATABASE_PATH(self) -> Path:
        return self.APP_DATA_DIR / "nova_trainer.db"

    @property
    def DATABASE_URL(self) -> str:
        # SQLite URL with forward slashes
        return f"sqlite:///{self.DATABASE_PATH.as_posix()}"

    @property
    def LOGS_DIR(self) -> Path:
        logs = self.APP_DATA_DIR / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        return logs

    @property
    def PROJECTS_DEFAULT_DIR(self) -> Path:
        projects = self.APP_DATA_DIR / "projects"
        projects.mkdir(parents=True, exist_ok=True)
        return projects

    @property
    def TRAINING_RUNS_DIR(self) -> Path:
        runs = self.APP_DATA_DIR / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        return runs

    @property
    def MODELS_DIR(self) -> Path:
        models_dir = self.APP_DATA_DIR / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir


settings = Settings()
