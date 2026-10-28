import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)
    root_path = Column(String(1024), nullable=False)
    is_multi_label = Column(Boolean, default=False, nullable=False)
    allow_negative_images = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    schema_version = Column(Integer, default=1, nullable=False)

    # Relationships
    datasets = relationship(
        "Dataset",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    labels = relationship(
        "ProjectLabel",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    training_jobs = relationship(
        "TrainingJob",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProjectLabel(Base):
    __tablename__ = "project_labels"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    color = Column(String(30), default="#6366f1", nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_label_name"),
    )

    # Relationships
    project = relationship("Project", back_populates="labels")
    classification_annotations = relationship(
        "ClassificationAnnotation",
        back_populates="label",
        passive_deletes="all",
    )
    object_annotations = relationship(
        "ObjectAnnotation",
        back_populates="label",
        passive_deletes="all",
    )


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    root_path = Column(String(1024), nullable=False)
    format = Column(String(50), default="folder_images", nullable=False)
    image_count = Column(Integer, default=0, nullable=False)
    annotation_count = Column(Integer, default=0, nullable=False)
    valid_image_count = Column(Integer, default=0, nullable=False)
    corrupted_image_count = Column(Integer, default=0, nullable=False)
    unsupported_file_count = Column(Integer, default=0, nullable=False)
    is_linked = Column(Boolean, default=True, nullable=False)
    last_scanned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    schema_version = Column(Integer, default=1, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="datasets")
    images = relationship(
        "ImageRecord",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    annotations = relationship(
        "ImageAnnotation",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    training_jobs = relationship(
        "TrainingJob",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ImageRecord(Base):
    __tablename__ = "image_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relative_path = Column(String(1024), nullable=False)
    absolute_path = Column(String(1024), nullable=False, index=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    format = Column(String(20), nullable=True)
    is_valid = Column(Boolean, default=True, nullable=False)
    error_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="images")
    annotation = relationship(
        "ImageAnnotation",
        back_populates="image",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ImageAnnotation(Base):
    __tablename__ = "image_annotations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_id = Column(
        String(36),
        ForeignKey("image_records.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    task_type = Column(String(50), nullable=False)
    status = Column(String(30), default="UNANNOTATED", nullable=False, index=True)
    is_negative = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    schema_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="annotations")
    image = relationship("ImageRecord", back_populates="annotation")
    classification_labels = relationship(
        "ClassificationAnnotation",
        back_populates="image_annotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    objects = relationship(
        "ObjectAnnotation",
        back_populates="image_annotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ClassificationAnnotation(Base):
    __tablename__ = "classification_annotations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    image_annotation_id = Column(
        String(36),
        ForeignKey("image_annotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label_id = Column(
        String(36),
        ForeignKey("project_labels.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relationships
    image_annotation = relationship("ImageAnnotation", back_populates="classification_labels")
    label = relationship("ProjectLabel", back_populates="classification_annotations")


class ObjectAnnotation(Base):
    __tablename__ = "object_annotations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    image_annotation_id = Column(
        String(36),
        ForeignKey("image_annotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label_id = Column(
        String(36),
        ForeignKey("project_labels.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    x_min = Column(Float, nullable=False)  # Normalized [0, 1]
    y_min = Column(Float, nullable=False)  # Normalized [0, 1]
    x_max = Column(Float, nullable=False)  # Normalized [0, 1]
    y_max = Column(Float, nullable=False)  # Normalized [0, 1]
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    image_annotation = relationship("ImageAnnotation", back_populates="objects")
    label = relationship("ProjectLabel", back_populates="object_annotations")


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=True)
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id = Column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type = Column(String(50), default="Image Classification", nullable=False)
    model_id = Column(String(36), nullable=True)
    model_architecture = Column(String(100), nullable=True)
    device = Column(String(50), default="cpu", nullable=True)
    status = Column(String(50), default="QUEUED", nullable=False, index=True)
    current_epoch = Column(Integer, default=0, nullable=False)
    total_epochs = Column(Integer, default=0, nullable=False)
    best_metric_name = Column(String(50), default="val_accuracy", nullable=True)
    best_metric_value = Column(Float, nullable=True)
    checkpoint_dir = Column(String(1024), nullable=True)
    log_file_path = Column(String(1024), nullable=True)
    configuration_json = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    evaluation_json = Column(Text, nullable=True)
    pid = Column(Integer, nullable=True)
    is_cancelled = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="training_jobs")
    dataset = relationship("Dataset", back_populates="training_jobs")


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    task_type = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False)
    artifact_path = Column(String(1024), nullable=False)
    framework = Column(String(50), nullable=False)
    export_format = Column(String(50), nullable=False)
    metadata_path = Column(String(1024), nullable=True)
    project_id = Column(String(36), nullable=True)
    dataset_id = Column(String(36), nullable=True)
    training_job_id = Column(String(36), nullable=True)
    model_architecture = Column(String(100), nullable=True)
    metrics_summary_json = Column(Text, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    is_exported = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
