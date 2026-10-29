# NOVA AI Trainer — Object Detection Training End-to-End

This guide describes the complete workflow for training, evaluating, and exporting deep learning object detection models within **NOVA AI Trainer**.

---

## 1. Overview & Architecture

The object detection training pipeline integrates seamlessly with the Phase 2 Annotation Studio and extends the Phase 3 training infrastructure with task-aware detection adapters:

```
[Phase 2 Bounding-Box Annotated Dataset]
                     │
                     ▼
1. Detection Dataset Validation & Pre-training Checks
   (Coordinate clamping, negative images, stable class index)
                     │
                     ▼
2. Architecture Selection (Faster R-CNN ResNet-50 / MobileNetV3)
                     │
                     ▼
3. Hyperparameters & Device Selection (CUDA GPU / CPU)
                     │
                     ▼
4. Subprocess Worker Spawn (Isolated PyTorch Subprocess)
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   Real-Time Telemetry      Atomic Checkpointing
(4-Part Loss & COCO mAP)  (latest_checkpoint.pt & best_checkpoint.pt)
        │                         │
        └────────────┬────────────┘
                     ▼
5. Post-Training Evaluation (pycocotools mAP, AP50, AP75, Per-Class AP)
                     │
                     ▼
6. Interactive Bounding Box Visualizer & Error Inspection
                     │
                     ▼
7. Deployment Package Export (ONNX Graph + Metadata + Verification)
```

---

## 2. Supported Detection Architectures

NOVA AI Trainer includes production-tested object detection backbones based on PyTorch and Torchvision:

| Model ID | Architecture | Backbone | Pretrained Weights | Best Suited For |
| :--- | :--- | :--- | :--- | :--- |
| `fasterrcnn_resnet50_fpn` | Faster R-CNN | ResNet-50 FPN | `ResNet50_Weights.DEFAULT` | High accuracy, complex multi-scale scenes, industrial defect detection |
| `fasterrcnn_mobilenet_v3_large_320_fpn` | Faster R-CNN | MobileNetV3 Large FPN | `MobileNet_V3_Large_Weights.DEFAULT` | Real-time edge inference, fast training iterations, resource-constrained environments |

Both architectures:
- Accept RGB images resized dynamically according to configuration (e.g. 640×640 or 320×320).
- Require a background class at `index 0` (`__background__`) followed by user-defined classes at `indices 1..N`.
- Output four distinct loss components during training: classification loss, box regression loss, objectness loss, and RPN box regression loss.
- Predict bounding boxes in `[x1, y1, x2, y2]` pixel coordinates along with integer label IDs and float confidence scores (`0.0` to `1.0`).

---

## 3. Dataset Validation & Annotation Ingestion

Before training begins, `DetectionDatasetAdapter.validate_and_prepare_dataset()` enforces strict validation rules:
1. **Project Task Verification**: Validates that the selected project has `task_type == "OBJECT_DETECTION"`.
2. **File Existence & Integrity**: Scans every image in the dataset to verify that the file exists and image dimensions (`width`, `height`) are readable.
3. **Bounding Box Validation**:
   - Converts normalized coordinates `[0, 1]` to pixel dimensions using original image sizes.
   - Rejects zero-area or negative-area bounding boxes (`x2 <= x1` or `y2 <= y1`).
   - Clamps boundary coordinates with a safety tolerance (`[-0.01, 1.01]`).
   - Verifies that referenced label IDs exist in the active project.
4. **Explicit Negative Images**:
   - Images explicitly flagged as negative (`is_negative=True`) with 0 bounding boxes are retained as valid background training examples.
   - Unannotated images without explicit negative verification are excluded with a warning.
5. **Class Sufficiency & Mapping**:
   - Maps project label UUIDs to sequential class IDs `1..N`.
   - Reserves class `0` for `__background__`.
   - Checks that all classes have at least 2 training instances and alerts on severe class imbalance.

---

## 4. Dataset Splits & Transformation Pipeline

### Split Management
- Dataset splits (`train`, `val`, `test`) are generated at the **image level** (an image never appears in more than one split).
- Uses a deterministic random seed to guarantee reproducibility across repeated experiments.
- Generates a `split_manifest.json` recording exact image allocations.

### Synchronized Transformations
Transformations applied during training must transform bounding boxes in lockstep with the image:
- **Resize**: Rescales `[x1, y1, x2, y2]` proportionally by `width_ratio` and `height_ratio`.
- **Horizontal Flip**: Inverts x coordinates: $x_1' = W - x_2$ and $x_2' = W - x_1$.
- **Normalization**: Applies standard ImageNet mean `[0.485, 0.456, 0.406]` and std `[0.229, 0.224, 0.225]`.

---

## 5. Worker Isolation & Subprocess Lifecycle

Training runs in an independent child process (`backend/app/workers/detection_worker.py`) to prevent blocking the desktop UI or backend server:

### Lifecycle States
`QUEUED` $\to$ `PREPARING` $\to$ `RUNNING` $\to$ `COMPLETED` / `CANCELLED` / `FAILED`

### Checkpoint & Telemetry Contracts
- **`latest_checkpoint.pt`**: Saved atomically every epoch with optimizer state, scheduler state, model weights, and epoch counter.
- **`best_checkpoint.pt`**: Updated whenever validation mAP improves.
- **`metrics.json`**: Real-time snapshot of current epoch, step, learning rate, loss breakdown, and COCO metrics.
- **`train.log`**: Subprocess stdout/stderr logged continuously for real-time streaming in the Desktop UI.

### Cooperative Cancellation & Resume
- To cancel a run, the backend places a `cancel.requested` flag in the run directory. The worker checks for this flag between batches, flushes `latest_checkpoint.pt`, and exits cleanly.
- To resume training from a cancelled or interrupted run, users can call the resume endpoint (`POST /api/v1/training/jobs/{job_id}/resume`) with target additional epochs. The worker loads model weights, optimizer, and scheduler states from `latest_checkpoint.pt` and resumes from the next epoch.

---

## 6. Real-Time Telemetry & Loss Breakdown

During training, detection workers track and report four separate loss components:
- `loss_classifier`: Fast R-CNN classification loss (cross-entropy over class predictions).
- `loss_box_reg`: Fast R-CNN bounding box regression loss (smooth L1 loss).
- `loss_objectness`: Region Proposal Network (RPN) objectness loss (foreground vs background binary cross-entropy).
- `loss_rpn_box_reg`: RPN anchor box regression loss.
- `total_loss`: The composite sum of all four loss terms.

Validation epochs evaluate models using standard COCO metrics: `mAP @ 0.50:0.95`, `AP50`, and `AP75`.

---

## 7. Model Export Package

When training completes, the model catalog generates a production-ready ONNX deployment package:
```text
export_package/
├── model.onnx              # Exported ONNX graph (inputs: [3, H, W], outputs: boxes, labels, scores)
├── model_metadata.json     # Architecture details, parameter count, framework versions
├── labels.json             # Class mapping (0: __background__, 1..N: project classes)
├── preprocessing.json      # Target input resolution, RGB format, ImageNet normalization
├── postprocessing.json     # Default confidence threshold (0.25) and NMS IoU threshold (0.45)
├── validation_report.json  # Final evaluation report (mAP, AP50, AP75, per-class metrics)
└── export_manifest.json    # SHA-256 integrity checksums for every artifact file
```

Every exported package is verified with an automated `onnxruntime` smoke test before being finalized in the Model Registry.
