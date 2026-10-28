from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class TrainingJobStatus(str, Enum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class SplitConfig(BaseModel):
    train_ratio: float = Field(default=0.8, ge=0.1, le=0.95)
    val_ratio: float = Field(default=0.1, ge=0.05, le=0.5)
    test_ratio: float = Field(default=0.1, ge=0.0, le=0.5)
    random_seed: int = Field(default=42)
    stratified: bool = Field(default=True)


class TrainingHyperparameters(BaseModel):
    model_architecture: str = Field(default="resnet18")
    pretrained: bool = Field(default=True)
    device: str = Field(default="auto")  # 'auto', 'cpu', 'cuda'
    input_size: int = Field(default=224, ge=32, le=1024)
    batch_size: int = Field(default=16, ge=1, le=512)
    epochs: int = Field(default=10, ge=1, le=1000)
    learning_rate: float = Field(default=0.001, gt=0.0, le=1.0)
    optimizer: str = Field(default="AdamW")  # 'AdamW', 'SGD'
    weight_decay: float = Field(default=0.0001, ge=0.0)
    momentum: float = Field(default=0.9, ge=0.0, le=1.0)
    scheduler: str = Field(default="step")  # 'step', 'cosine', 'none'
    early_stopping: bool = Field(default=False)
    patience: int = Field(default=5, ge=1)
    num_workers: int = Field(default=0, ge=0, le=16)
    horizontal_flip: bool = Field(default=True)
    rotation_degrees: int = Field(default=10, ge=0, le=180)
    color_jitter: bool = Field(default=False)


class DatasetValidationRequest(BaseModel):
    project_id: str
    dataset_id: str
    split_config: SplitConfig = Field(default_factory=SplitConfig)


class ClassItem(BaseModel):
    index: int
    label_id: str
    name: str
    color: str
    count: int


class DatasetValidationResponse(BaseModel):
    is_valid: bool
    project_id: str
    dataset_id: str
    total_images: int
    valid_annotated_images: int
    unannotated_images: int
    invalid_annotations: int
    negative_images: int
    missing_files: int
    classes: List[ClassItem]
    class_imbalance_warning: bool
    train_count: int
    val_count: int
    test_count: int
    split_manifest_id: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class TrainingJobCreate(BaseModel):
    project_id: str
    dataset_id: str
    name: Optional[str] = None
    hyperparameters: TrainingHyperparameters = Field(default_factory=TrainingHyperparameters)
    split_config: SplitConfig = Field(default_factory=SplitConfig)


class EpochMetric(BaseModel):
    epoch: int
    train_loss: float
    train_accuracy: float
    val_loss: Optional[float] = None
    val_accuracy: Optional[float] = None
    val_precision: Optional[float] = None
    val_recall: Optional[float] = None
    val_f1: Optional[float] = None
    learning_rate: float
    duration_seconds: float
    timestamp: str


class ConfusionMatrixData(BaseModel):
    labels: List[str]
    matrix: List[List[int]]


class PerClassMetric(BaseModel):
    class_name: str
    precision: float
    recall: float
    f1_score: float
    support: int


class MisclassifiedImage(BaseModel):
    image_id: str
    relative_path: str
    ground_truth: str
    predicted: str
    confidence: float


class EvaluationReport(BaseModel):
    total_samples: int
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    per_class_metrics: List[PerClassMetric]
    confusion_matrix: ConfusionMatrixData
    misclassified_samples: List[MisclassifiedImage]
    evaluated_at: str


class TrainingJobResponse(BaseModel):
    id: str
    name: Optional[str] = None
    project_id: str
    dataset_id: str
    task_type: str = "Image Classification"
    model_id: Optional[str] = None
    model_architecture: Optional[str] = None
    device: Optional[str] = "cpu"
    status: TrainingJobStatus
    current_epoch: int = 0
    total_epochs: int = 0
    best_metric_name: Optional[str] = "val_accuracy"
    best_metric_value: Optional[float] = None
    checkpoint_dir: Optional[str] = None
    log_file_path: Optional[str] = None
    configuration_json: Optional[str] = None
    metrics_json: Optional[str] = None
    evaluation_json: Optional[str] = None
    pid: Optional[int] = None
    is_cancelled: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
