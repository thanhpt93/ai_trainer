from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


class BaseTaskAdapter(ABC):
    """Abstract adapter defining support for a specific vision task."""

    @property
    @abstractmethod
    def task_name(self) -> str:
        """Name of the task, e.g. 'Image Classification'."""
        pass

    @abstractmethod
    def get_supported_model_architectures(self) -> List[str]:
        """List of supported model architecture names."""
        pass

    @abstractmethod
    def validate_dataset_structure(self, dataset_path: Path) -> Tuple[bool, str]:
        """Validate if the dataset meets task requirements."""
        pass


class BaseDatasetAdapter(ABC):
    """Abstract adapter for dataset parsing and conversion."""

    @abstractmethod
    def parse_annotations(self, root_path: Path) -> Dict[str, Any]:
        """Parse annotations into standardized schema."""
        pass

    @abstractmethod
    def export_to_format(self, output_path: Path, target_format: str) -> None:
        """Export dataset to another format (e.g. YOLO, COCO)."""
        pass


class BaseModelAdapter(ABC):
    """Abstract adapter for AI model definitions and weight handling."""

    @abstractmethod
    def build_model(self, num_classes: int, config: Dict[str, Any]) -> Any:
        """Instantiate model architecture."""
        pass

    @abstractmethod
    def load_weights(self, weights_path: Path) -> None:
        """Load checkpoint weights."""
        pass


class BaseExportAdapter(ABC):
    """Abstract adapter for model export (ONNX, TorchScript, OpenVINO, TensorRT)."""

    @abstractmethod
    def export(
        self,
        model: Any,
        output_file: Path,
        input_shape: tuple,
        dynamic_batch: bool = True,
    ) -> Path:
        """Export model to target format."""
        pass


class BaseTrainingEngine(ABC):
    """Abstract training execution contract."""

    @abstractmethod
    def start_training(self, job_id: str, config: Dict[str, Any]) -> None:
        """Launch training job."""
        pass

    @abstractmethod
    def stop_training(self, job_id: str) -> None:
        """Gracefully interrupt and terminate training."""
        pass
