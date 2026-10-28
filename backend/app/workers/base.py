from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel


class WorkerStatus(str, Enum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class ResourceUsage(BaseModel):
    cpu_percent: float
    memory_mb: float
    gpu_memory_mb: Optional[float] = None
    gpu_utilization_percent: Optional[float] = None


class TrainingProgressEvent(BaseModel):
    job_id: str
    epoch: int
    total_epochs: int
    step: int
    total_steps: int
    train_loss: float
    val_loss: Optional[float] = None
    metrics: Dict[str, float] = {}
    resource_usage: Optional[ResourceUsage] = None


class WorkerProcessManager(ABC):
    """
    Contract for managing isolated worker processes for AI training jobs.
    Training jobs run in separate worker processes, not inside the API server.
    """

    @abstractmethod
    def start_worker(self, job_id: str, job_config: Dict[str, Any]) -> bool:
        """Launch an isolated worker subprocess."""
        pass

    @abstractmethod
    def stop_worker(self, job_id: str) -> bool:
        """Terminate a running worker process cleanly."""
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> WorkerStatus:
        """Query worker process status."""
        pass

    @abstractmethod
    def get_resources(self, job_id: str) -> Optional[ResourceUsage]:
        """Query worker CPU/GPU utilization."""
        pass
