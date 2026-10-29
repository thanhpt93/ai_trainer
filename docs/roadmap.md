# NOVA AI Trainer — Development Roadmap

This document outlines the multi-phase technical roadmap for the **NOVA AI Trainer** standalone desktop platform.

---

## Phase 1: Foundation, Desktop Shell, Project Management & Dataset Import (Completed)

- [x] High-performance standalone desktop architecture (Electron + React 18 + TypeScript + Vite + Zustand + Tailwind CSS).
- [x] Secure local Python backend service (FastAPI, loopback binding only, structured Pydantic v2 schemas).
- [x] SQLite database layer with WAL mode, foreign keys, and SQLAlchemy 2.0 ORM.
- [x] Project CRUD with 7 supported vision task types.
- [x] Dataset import workflow with recursive image folder scanning (JPEG, PNG, BMP, TIFF, WebP).
- [x] Header integrity checks via Pillow without loading full image pixels into memory.
- [x] Paginated image viewer and secure local file streaming.
- [x] Dashboard with genuine persistence metrics.
- [x] Abstract adapter protocols (`BaseTaskAdapter`, `BaseDatasetAdapter`, `BaseModelAdapter`, `BaseTrainingEngine`, `BaseExportAdapter`) and worker lifecycle interfaces (`WorkerProcessManager`).
- [x] Comprehensive test suite with pytest covering backend endpoints and services.

---

## Phase 2: Annotation Data Model & Desktop Annotation Studio (Completed)

- [x] Interactive desktop labeling canvas with aspect-ratio preserving zoom (20%-500%), pan, and image-to-screen coordinate normalization (`[0, 1]`).
- [x] Bounding box creation, 8 resize handles (`nw`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w`), move/drag, zero-area prevention, and edge clamping.
- [x] Image Classification annotation (single-label and multi-label modes according to project configuration).
- [x] Negative image verification (flagging confirmed background images with zero targets) and Review flag workflow.
- [x] Project-level label/class management with color presets, descriptions, and reference protection (HTTP 409 Conflict rejection if label is currently in use).
- [x] Dataset annotation summary stats (total, annotated, unannotated, needs review, completion %) and status tab filtering.
- [x] Full keyboard shortcuts (`Ctrl+S`, `Ctrl+Z`, `Ctrl+Y`, `A` / `D`, `Delete` / `Backspace`, `Esc`, `V` / `B` / `H`, numbers `1-9` for class hotkeys, Spacebar pan).
- [x] Complete export engine supporting YOLO (`labels/*.txt` + `data.yaml`), COCO (`annotations.json`), Pascal VOC (`Annotations/*.xml`), CSV, and JSON.
- [x] Comprehensive automated tests (15 backend tests passing in pytest) and clean TypeScript desktop build.

---

## Phase 3: Image Classification Training Pipeline End-to-End (Completed)

- [x] **Classification Dataset Validation & Split Adapter**:
  - Validates dataset integrity against project rules, checks image file readability, and verifies class counts.
  - Generates reproducible, stratified train/validation/test split manifests with configurable random seeds.
  - Detects class imbalance and enforces single-label constraints.
- [x] **Model Catalog & Vision Backbones**:
  - Implemented adapters for ResNet-18, MobileNetV3-Small, ResNet-50, MobileNetV3-Large, and EfficientNet-B0 with custom classifier heads.
  - Supports transfer learning with pretrained weights or training from scratch.
- [x] **Isolated Training Worker & Subprocess Lifecycle**:
  - Independent child worker subprocesses (`python -m backend.app.workers.classification_worker`).
  - Worker crash detection, status transitions (`QUEUED`, `PREPARING`, `RUNNING`, `COMPLETED`, `CANCEL_REQUESTED`, `CANCELLED`, `FAILED`).
  - Cooperative cancellation protocol via filesystem flag with graceful checkpoint persistence.
  - Concurrency management enforcing 1 active worker at a time.
- [x] **Real PyTorch Training Loop & Checkpointing**:
  - Real CrossEntropyLoss and accuracy optimization; AdamW and SGD with momentum.
  - Learning rate schedulers (step, cosine, none).
  - Atomic checkpoint persistence (`latest_checkpoint.pt` and `best_checkpoint.pt`).
- [x] **Post-Training Evaluation & Benchmarks**:
  - Full $N \times N$ confusion matrix computation.
  - Per-class Precision, Recall, F1-Score, and support counts.
  - Misclassified image gallery with ground truth, predicted class, and softmax confidence scores.
- [x] **Model Registry & ONNX Export**:
  - Export to deployment bundles: `model.onnx`, `model_metadata.json`, `labels.json`, `preprocessing.json`, `validation_report.json`, `export_manifest.json`.
  - Dynamic batch dimension configuration.
  - Automated smoke inference verification using ONNX Runtime.
  - SHA-256 package checksum verification.
- [x] **Comprehensive UI Suites**:
  - Training Configuration wizard with hardware telemetry strip.
  - Live Training Monitor page with loss/accuracy curves and streaming worker output logs.
  - Evaluation Studio page with confusion matrix heatmap and misclassification drill-down.
  - Experiment Hub with side-by-side experiment comparisons.
  - Model Registry & Export Hub with versioned deployment bundles.
- [x] **Automated Tests**:
  - 21 backend unit and integration tests passing in PyTorch + CUDA environment.

---

## Phase 4: Object Detection Training Pipeline End-to-End (Completed)

- [x] **Detection Dataset Validation & Split Ingestion**:
  - Validates normalized bounding box coordinates `[0, 1]`, enforces positive area, safe boundary clamping.
  - Explicit negative image support (`is_negative=True` / zero annotations retained as background samples).
  - Stable class mapping reserving index `0` for `__background__` and `1..N` for project labels.
  - Synchronized image and bounding box transforms (aspect ratio resize, horizontal flip).
  - Image-level reproducible train/val/test splitting with class distribution tracking.
- [x] **Model Catalog & Detection Backbones**:
  - `fasterrcnn_resnet50_fpn` (Faster R-CNN with ResNet-50 FPN backbone).
  - `fasterrcnn_mobilenet_v3_large_320_fpn` (Lightweight edge-ready Faster R-CNN).
  - Pretrained torchvision weights integration and cached weight checkpoints.
- [x] **Isolated Detection Worker & Training Subprocess**:
  - Dedicated worker process `backend/app/workers/detection_worker.py`.
  - Real forward and backward passes with 4-part loss tracking (`loss_classifier`, `loss_box_reg`, `loss_objectness`, `loss_rpn_box_reg`).
  - Atomic checkpointing (`latest_checkpoint.pt` and `best_checkpoint.pt`).
  - Cooperative cancellation protocol and checkpoint resume (`POST /api/v1/training/jobs/{job_id}/resume`).
- [x] **COCO Evaluation & Bounding Box Visualizer**:
  - Standard COCO benchmark metrics (`mAP @ 0.50:0.95`, `AP50`, `AP75`, per-class AP) via `pycocotools`.
  - Bipartite IoU matching at operating point ($\tau=0.25$, $\text{IoU}=0.50$) for Precision, Recall, F1.
  - Ground truth vs predicted bounding box visual overlay with color-coded label badges.
- [x] **Model Registry & ONNX Export**:
  - Self-contained deployment bundles: `model.onnx`, `model_metadata.json`, `labels.json`, `preprocessing.json`, `postprocessing.json`, `validation_report.json`, `export_manifest.json`.
  - Automated smoke test verifying inference with `onnxruntime`.
  - Interactive prediction endpoint (`POST /api/v1/training/jobs/{job_id}/predict`).
- [x] **Comprehensive Frontend Updates**:
  - Training Configuration UI supporting Object Detection projects, model filtering, validation preview, and detection hyperparameters.
  - Training Monitor UI with detection loss decomposition and mAP telemetry.
  - Evaluation Studio UI with COCO metric cards, per-class AP table, bounding box inspector, and live detection test playground.
- [x] **Automated Tests**:
  - 8 new detection unit and integration tests (29/29 total tests passing in pytest).

---

## Phase 5: Advanced Model Registry & Deployment Packaging

- [ ] TensorRT and OpenVINO quantization (FP16, INT8 calibration).
- [ ] Latency & throughput benchmarking engine on target CPU / GPU.
- [ ] Direct export bundle packaging for NOVA Machine Vision Platform runtime.

---

## Phase 6: Advanced Vision Tasks & Multi-Backend Support

- [ ] Semantic & Instance Segmentation training pipelines.
- [ ] OCR text recognition and text detection engines.
- [ ] Unsupervised Anomaly detection models for industrial defect inspection.
