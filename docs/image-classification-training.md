# NOVA AI Trainer — Image Classification Training End-to-End

This guide describes the complete workflow for training and deploying deep learning image classification models within **NOVA AI Trainer**.

---

## 1. Overview & Workflow

The image classification training pipeline allows developers to transition seamlessly from labeled dataset items to a production-ready ONNX model:

```
[Phase 2 Labeled Dataset]
          │
          ▼
1. Dataset Validation & Stratified Split
          │
          ▼
2. Architecture Selection (ResNet-18, MobileNetV3, ResNet-50)
          │
          ▼
3. Hyperparameters & Hardware Configuration
          │
          ▼
4. Worker Process Spawn (Isolated PyTorch Subprocess)
          │
    ┌─────┴────────────────┐
    ▼                      ▼
Real-Time Telemetry   Atomic Checkpointing
(Loss/Acc Curves)     (latest.pt & best.pt)
    │                      │
    └─────┬────────────────┘
          ▼
5. Post-Training Evaluation (Confusion Matrix & Class Metrics)
          │
          ▼
6. Deployment Export (ONNX Package + Verification + Manifest)
```

---

## 2. Supported Model Architectures

The Model Catalog provides optimized computer vision backbones from torchvision:

| Model Architecture | Parameter Count | Default Resolution | Best Suited For |
| :--- | :--- | :--- | :--- |
| **ResNet-18** | 11.7 M | 224 × 224 | Fast iterations, general edge inspection |
| **MobileNetV3-Small**| 2.5 M | 224 × 224 | Real-time embedded CPU / Mobile inference |
| **MobileNetV3-Large**| 5.4 M | 224 × 224 | High frame-rate edge deployment |
| **ResNet-50** | 25.6 M | 224 × 224 | Complex feature recognition & high accuracy |
| **EfficientNet-B0** | 5.3 M | 224 × 224 | High accuracy-to-compute efficiency |

---

## 3. Dataset Preparation & Split Strategy

Before training commences, the `ClassificationDatasetAdapter`:
1. Validates that the selected dataset belongs to an `Image Classification` project.
2. Verifies that all image files exist and are readable on disk.
3. Maps Phase 2 database labels into a stable class index mapping (`0..N-1`).
4. Enforces single-label semantics (images with conflicting multiple labels are flagged and excluded).
5. Checks for class count sufficiency (minimum 2 samples per class).
6. Generates a reproducible, stratified train/validation/test split manifest using a user-configurable random seed.

---

## 4. Training Worker Process Isolation

To maintain desktop responsiveness and avoid blocking FastAPI or the Electron renderer:
* Each training job runs inside a dedicated child Python subprocess:
  `python -m backend.app.workers.classification_worker --config <path_to_config.json>`
* Communication occurs via structured filesystem events (`metrics.json`, `events.jsonl`, `train.log`).
* Cooperative cancellation: If the user clicks **Cancel Job**, the system creates a `cancel.requested` flag in the run directory. The worker safely saves the latest checkpoint and exits cleanly.

---

## 5. Post-Training Evaluation

Completed classification jobs produce an evaluation benchmark including:
* **Confusion Matrix**: $N \times N$ matrix indicating actual vs predicted label distributions.
* **Per-Class Metrics**: Precision, Recall, and F1-Score for each individual class.
* **Macro Metrics**: Overall Accuracy, Macro Precision, Macro Recall, Macro F1.
* **Error Analysis Gallery**: List of misclassified test samples with image paths, ground truth labels, predicted labels, and softmax confidence percentages.

---

## 6. Model Export & Verification

The Model Registry exports models into a self-contained bundle ready for downstream deployment:

```text
export_package/
├── model.onnx              # Exported ONNX model graph (dynamic batch support)
├── model_metadata.json     # Architecture, tensors, normalization parameters
├── labels.json             # Class indices, project label IDs, and class names
├── preprocessing.json      # Resize policy, color space (RGB), mean/std
├── validation_report.json  # Accuracy, precision, and confusion matrix summary
└── export_manifest.json    # SHA-256 checksums and file size validations
```

Every exported package is automatically verified by executing a smoke inference run using **ONNX Runtime** and checking numerical consistency against PyTorch predictions.
