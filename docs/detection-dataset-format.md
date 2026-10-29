# NOVA AI Trainer — Detection Dataset Format Specification

This document defines the schema, coordinate systems, validation rules, and class mapping semantics for object detection datasets in **NOVA AI Trainer**.

---

## 1. Storage & Coordinate Systems

Phase 2 stores bounding box annotations in the SQLite database under `ObjectAnnotation` rows with normalized coordinates:
- `x_min`: Normalized left coordinate $\in [0, 1]$
- `y_min`: Normalized top coordinate $\in [0, 1]$
- `x_max`: Normalized right coordinate $\in [0, 1]$
- `y_max`: Normalized bottom coordinate $\in [0, 1]$

### Coordinate Transformation Formula
When ingesting annotations for training, the detection adapter converts normalized coordinates into absolute pixel coordinates based on the image's original dimensions ($W_{img}, H_{img}$):

$$x_1 = x_{min} \times W_{img}$$
$$y_1 = y_{min} \times H_{img}$$
$$x_2 = x_{max} \times W_{img}$$
$$y_2 = y_{max} \times H_{img}$$

### Clamping & Tolerance Rules
- Slight numerical or rounding variations within $[-0.01, 1.01]$ are clamped safely to $[0, W_{img}]$ and $[0, H_{img}]$.
- Values strictly exceeding $[-0.01, 1.01]$ indicate corrupted or out-of-bounds annotations and are flagged as validation errors.
- Bounding boxes where $x_2 \le x_1$ or $y_2 \le y_1$ are zero-area or inverted boxes and are excluded with a warning.

---

## 2. Negative Images

In object detection workflows, negative images (background images containing zero target objects) are critical for training models to avoid false positive detections.

### Explicit Negative Representation
- An image is treated as a negative training sample if and only if:
  1. `is_negative == True` on the image record, OR
  2. The image has been marked as annotated (`status == "ANNOTATED"` or `is_annotated == True`) with exactly 0 bounding box annotations.
- Unannotated images (`status == "UNANNOTATED"`) are **never** treated as negative images; they are excluded from the training split.
- Negative images produce empty target tensors during training:
  - `boxes`: `torch.zeros((0, 4), dtype=torch.float32)`
  - `labels`: `torch.zeros((0,), dtype=torch.int64)`

---

## 3. Class Index Mapping Convention

Torchvision Faster R-CNN requires reserving class index `0` for the background class. NOVA AI Trainer maps classes as follows:

| Class Index | Label ID | Name | Role |
| :--- | :--- | :--- | :--- |
| `0` | `__background__` | `__background__` | Background class reserved for model internal loss computation |
| `1` | `<project_label_uuid_1>` | `car` | First user-defined foreground class |
| `2` | `<project_label_uuid_2>` | `pedestrian` | Second user-defined foreground class |
| `N` | `<project_label_uuid_N>` | `cyclist` | $N$-th user-defined foreground class |

When exporting or visualizing predictions:
- Background class `0` is ignored in user-facing reports and bounding box visualizers.
- All predictions with class indices $1..N$ are mapped back to their original project label names and colors.

---

## 4. Dataset Validation Report Schema

Calling `POST /api/v1/training/datasets/validate` produces a comprehensive validation report:

```json
{
  "total_scanned_images": 500,
  "eligible_images": 480,
  "excluded_images": 20,
  "valid_annotated_images": 450,
  "explicit_negative_images": 30,
  "unannotated_images": 15,
  "invalid_images": 5,
  "total_bounding_boxes": 1420,
  "number_of_classes": 3,
  "boxes_per_class": {
    "car": 850,
    "pedestrian": 420,
    "cyclist": 150
  },
  "images_per_class": {
    "car": 310,
    "pedestrian": 180,
    "cyclist": 95
  },
  "missing_files": 2,
  "class_mapping": [
    {"class_index": 0, "label_id": "__background__", "name": "__background__"},
    {"class_index": 1, "label_id": "uuid-1", "name": "car", "color": "#3B82F6"},
    {"class_index": 2, "label_id": "uuid-2", "name": "pedestrian", "color": "#10B981"}
  ],
  "warnings": [
    "Image 'img_042.jpg' contains an annotation with zero area and was excluded."
  ],
  "blocking_errors": []
}
```

Training jobs are blocked if `blocking_errors` is non-empty or if eligible images are insufficient for the configured split ratios.
