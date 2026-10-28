# NOVA AI Trainer — Domain Models & Database Schemas

## 1. Domain Entities & Schemas

### 1.1 Project (`Project`)

Represents a vision engineering project encompassing datasets, labels, annotations, training configurations, and registered models.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `name` | `VARCHAR(255)` | Unique project name (Indexed) |
| `description` | `TEXT` | Optional project summary |
| `task_type` | `VARCHAR(50)` | Computer vision task category |
| `root_path` | `VARCHAR(1024)` | Project storage location on disk |
| `is_multi_label` | `BOOLEAN` | Multi-label support for Classification tasks (Default `False`) |
| `allow_negative_images` | `BOOLEAN` | Whether images can be confirmed as negative/background (Default `True`) |
| `created_at` | `DATETIME` | UTC timestamp of creation |
| `updated_at` | `DATETIME` | UTC timestamp of last update |
| `schema_version`| `INTEGER` | Schema version (Default `1`) |

#### Supported Task Types:
1. `Image Classification`
2. `Object Detection`
3. `Image Segmentation`
4. `OCR`
5. `Anomaly Detection`
6. `Keypoint Detection`
7. `Image Similarity`

---

### 1.2 Dataset (`Dataset`)

Represents an imported or linked image folder.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `project_id` | `VARCHAR(36)` | Foreign Key to `projects.id` (CASCADE) |
| `name` | `VARCHAR(255)` | Human-readable dataset name |
| `description` | `TEXT` | Optional dataset description |
| `root_path` | `VARCHAR(1024)` | Absolute source folder path |
| `format` | `VARCHAR(50)` | Dataset format (`folder_images`, `coco`, `yolo`, `pascal_voc`) |
| `image_count` | `INTEGER` | Total image files found (valid + corrupted) |
| `valid_image_count` | `INTEGER` | Images with valid readable headers |
| `corrupted_image_count` | `INTEGER` | Corrupted / unreadable image files |
| `unsupported_file_count` | `INTEGER` | Non-image files encountered during scan |
| `annotation_count` | `INTEGER` | Annotation records count |
| `is_linked` | `BOOLEAN` | `True` if referencing source directory, `False` if copied |
| `last_scanned_at` | `DATETIME` | Timestamp of most recent folder scan |
| `created_at` | `DATETIME` | Creation timestamp |
| `updated_at` | `DATETIME` | Last modification timestamp |
| `schema_version` | `INTEGER` | Schema version (Default `1`) |

---

### 1.3 Image Record (`ImageRecord`)

Stores metadata for every image discovered during recursive scans. Avoids storing raw image bytes in the database.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `dataset_id` | `VARCHAR(36)` | Foreign Key to `datasets.id` (CASCADE) |
| `relative_path` | `VARCHAR(1024)` | Path relative to dataset root |
| `absolute_path` | `VARCHAR(1024)` | Full normalized path on disk (Indexed) |
| `file_size_bytes` | `INTEGER` | File size in bytes |
| `width` | `INTEGER` | Pixel width (nullable for corrupt files) |
| `height` | `INTEGER` | Pixel height (nullable for corrupt files) |
| `channels` | `INTEGER` | Channel count (e.g. 1, 3, 4) |
| `format` | `VARCHAR(20)` | File format (e.g. `PNG`, `JPEG`, `BMP`) |
| `is_valid` | `BOOLEAN` | Whether header validation succeeded |
| `error_reason` | `VARCHAR(255)` | Reason for unreadability if corrupt |
| `created_at` | `DATETIME` | Scan timestamp |

---

### 1.4 Project Label (`ProjectLabel` - Phase 2)

Defines a class or category scoped to a project.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `project_id` | `VARCHAR(36)` | Foreign Key to `projects.id` (CASCADE) |
| `name` | `VARCHAR(100)` | Label name (case-insensitive unique per project) |
| `color` | `VARCHAR(20)` | Hexadecimal display color (e.g. `#6366f1`) |
| `description` | `TEXT` | Optional class description |
| `created_at` | `DATETIME` | Creation timestamp |

---

### 1.5 Image Annotation (`ImageAnnotation` - Phase 2)

Parent annotation container for a single image record.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `image_id` | `VARCHAR(36)` | Foreign Key to `image_records.id` (CASCADE, Unique 1:1) |
| `dataset_id` | `VARCHAR(36)` | Foreign Key to `datasets.id` (CASCADE) |
| `is_annotated` | `BOOLEAN` | `True` once saved with labels, boxes, or negative confirmation |
| `is_negative` | `BOOLEAN` | `True` if confirmed background image without targets |
| `needs_review` | `BOOLEAN` | Quality control review flag |
| `notes` | `TEXT` | Optional annotator comments or guidelines |
| `created_at` | `DATETIME` | Creation timestamp |
| `updated_at` | `DATETIME` | Last update timestamp |

---

### 1.6 Classification Annotation (`ClassificationAnnotation` - Phase 2)

Associates an image with a specific classification label.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `annotation_id` | `VARCHAR(36)` | Foreign Key to `image_annotations.id` (CASCADE) |
| `label_id` | `VARCHAR(36)` | Foreign Key to `project_labels.id` (RESTRICT) |
| `confidence` | `FLOAT` | Confidence score (Default `1.0`) |
| `created_at` | `DATETIME` | Timestamp |

---

### 1.7 Object Annotation (`ObjectAnnotation` - Phase 2)

Normalized 2D bounding box detection coordinates `[0, 1]` relative to image width and height.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `annotation_id` | `VARCHAR(36)` | Foreign Key to `image_annotations.id` (CASCADE) |
| `label_id` | `VARCHAR(36)` | Foreign Key to `project_labels.id` (RESTRICT) |
| `x_min` | `FLOAT` | Normalized left edge `[0.0, 1.0]` |
| `y_min` | `FLOAT` | Normalized top edge `[0.0, 1.0]` |
| `x_max` | `FLOAT` | Normalized right edge `[0.0, 1.0]` |
| `y_max` | `FLOAT` | Normalized bottom edge `[0.0, 1.0]` |
| `confidence` | `FLOAT` | Confidence score (Default `1.0`) |
| `created_at` | `DATETIME` | Timestamp |

---

### 1.8 Training Job (`TrainingJob` - Prepared Schema for Phase 3+)

Captures training job execution parameters and state.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `project_id` | `VARCHAR(36)` | Foreign Key to `projects.id` |
| `dataset_id` | `VARCHAR(36)` | Foreign Key to `datasets.id` |
| `model_id` | `VARCHAR(36)` | Associated model ID |
| `status` | `VARCHAR(50)` | `QUEUED`, `PREPARING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `configuration_json`| `TEXT` | Serialized hyperparameter dictionary |
| `started_at` | `DATETIME` | Execution start timestamp |
| `completed_at` | `DATETIME` | Completion timestamp |
| `error_message`| `TEXT` | Stack trace or failure description |
| `created_at` | `DATETIME` | Job creation timestamp |
| `updated_at` | `DATETIME` | Status update timestamp |

---

### 1.9 Model Artifact (`ModelArtifact` - Prepared Schema for Phase 5+)

Tracks trained model weights and export packages.

| Field | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Primary Key (UUIDv4) |
| `name` | `VARCHAR(255)` | Model artifact name |
| `task_type` | `VARCHAR(50)` | Task type |
| `version` | `VARCHAR(50)` | Semantic version string |
| `artifact_path`| `VARCHAR(1024)` | File path to weights file |
| `framework` | `VARCHAR(50)` | `PyTorch`, `ONNX`, `TensorRT`, etc. |
| `export_format`| `VARCHAR(50)` | Output format (`ONNX`, `Engine`, etc.) |
| `metadata_path`| `VARCHAR(1024)` | Associated class label / hyperparam JSON |
| `created_at` | `DATETIME` | Registration timestamp |
