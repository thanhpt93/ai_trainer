# NOVA AI Trainer — REST API Reference (v1)

Base URL: `http://127.0.0.1:8000/api/v1`  
Interactive OpenAPI UI: `http://127.0.0.1:8000/docs`

---

## 1. Health & System Endpoints

### `GET /health`
Returns health status and database connectivity.

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "app_name": "NOVA AI Trainer",
  "version": "0.2.0",
  "database_connected": true,
  "app_data_dir": "C:\\Users\\admin\\AppData\\Local\\NovaAITrainer"
}
```

### `GET /system-info`
Retrieves platform details, CPU/RAM, and CUDA hardware acceleration info.

### `GET /dashboard/stats`
Returns genuine persisted statistics for the application dashboard.

---

## 2. Project Endpoints

### `GET /projects`
Query parameters:
- `search` (optional string): filter by project name or description
- `task_type` (optional string): filter by task type
- `skip` (int, default `0`)
- `limit` (int, default `100`)

### `POST /projects`
Creates a project. Returns `201 Created` or `409 Conflict` if the name is taken.

**Request Body:**
```json
{
  "name": "Surface Defect Detection",
  "description": "Industrial PCB classification",
  "task_type": "Image Classification",
  "root_path": "C:/Projects/PCB_Vision",
  "is_multi_label": false,
  "allow_negative_images": true
}
```

### `GET /projects/{project_id}`
Retrieves a single project by ID. Returns `404` if not found.

### `PATCH /projects/{project_id}`
Updates project metadata.

### `DELETE /projects/{project_id}`
Deletes the project and cascades dataset metadata in the database. Returns `204 No Content`. Original images on disk are preserved.

### `GET /projects/{project_id}/datasets`
Lists all datasets belonging to a project.

### `POST /projects/{project_id}/datasets`
Imports or links a dataset into the project.

---

## 3. Dataset Endpoints

### `GET /datasets`
Lists all datasets across projects.

### `GET /datasets/{dataset_id}`
Retrieves dataset metadata and scan counts.

### `DELETE /datasets/{dataset_id}`
Deletes dataset metadata and indexed image records. Returns `204 No Content`.

### `POST /datasets/{dataset_id}/scan`
Initiates a recursive folder scan. Discovers supported images, checks integrity, and logs counts.

### `GET /datasets/{dataset_id}/images`
Query parameters:
- `is_valid` (optional boolean): `true` for valid images, `false` for corrupt files
- `page` (int, default `1`)
- `page_size` (int, default `50`)

### `GET /datasets/{dataset_id}/images/{image_id}/file`
Securely streams the physical image file. Validates that the requested image path is strictly within the dataset's validated root path.

---

## 4. Label Management Endpoints (Phase 2)

### `GET /projects/{project_id}/labels`
Lists all labels defined for a project.

### `POST /projects/{project_id}/labels`
Creates a label. Rejects case-insensitive duplicates with `409 Conflict`.

**Request Body:**
```json
{
  "name": "Defect",
  "color": "#ef4444",
  "description": "Scratches or dents on surface"
}
```

### `PUT /labels/{label_id}`
Updates a label's name, color, or description.

### `DELETE /labels/{label_id}`
Deletes a label. Rejects with `409 Conflict` if referenced by any classification or bounding box annotation.

---

## 5. Annotation Studio Endpoints (Phase 2)

### `GET /datasets/{dataset_id}/annotation-summary`
Returns dataset-level progress metrics:
```json
{
  "dataset_id": "...",
  "total_images": 150,
  "annotated_images": 95,
  "unannotated_images": 55,
  "needs_review_count": 4,
  "negative_images_count": 12,
  "completion_percentage": 63.3
}
```

### `GET /datasets/{dataset_id}/annotated-images`
Query parameters:
- `status`: `ALL`, `UNANNOTATED`, `ANNOTATED`, `NEEDS_REVIEW`, `INVALID`
- `search`: filename search filter
- `page`: int (default `1`)
- `page_size`: int (default `50`)

Returns paginated images with thumbnail preview URLs and current annotation statuses.

### `GET /images/{image_id}/annotation`
Loads the current annotations for a specific image, including assigned classification labels and normalized bounding boxes.

### `POST /images/{image_id}/annotation`
Saves or replaces annotations for an image. Enforces single/multi-label rules and coordinate bounds `[0, 1]`.

**Request Body:**
```json
{
  "is_negative": false,
  "needs_review": false,
  "notes": "Clear bounding boxes",
  "label_ids": ["label-uuid-1"],
  "boxes": [
    {
      "label_id": "label-uuid-1",
      "x_min": 0.12,
      "y_min": 0.34,
      "x_max": 0.56,
      "y_max": 0.78,
      "confidence": 1.0
    }
  ]
}
```

### `POST /datasets/{dataset_id}/export`
Exports dataset annotations into machine-readable datasets in user-selected directory.

**Request Body:**
```json
{
  "format": "yolo",
  "output_directory": "C:/Exports/Dataset_YOLO",
  "include_images": true
}
```
Supported formats: `yolo`, `coco`, `pascal_voc`, `csv`, `json`.

---

## 6. Filesystem Helper Endpoint

### `POST /filesystem/validate-path`
Validates a directory path prior to import. Rejects critical system roots (`C:\\`, `C:\\Windows`, etc.).
