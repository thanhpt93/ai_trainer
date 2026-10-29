# NOVA AI Trainer — Object Detection Model Export & Deployment

This document describes the structure, contracts, and deployment integration of exported object detection model bundles in **NOVA AI Trainer**.

---

## 1. Export Bundle Layout

Exporting a trained object detection model produces a standalone directory in the Model Registry:

```text
export_package/
├── model.onnx              # Exported ONNX compute graph
├── model_metadata.json     # Architecture definition & runtime requirements
├── labels.json             # Model class index to project label mapping
├── preprocessing.json      # Image loading, color space, and normalization parameters
├── postprocessing.json     # Confidence score and NMS IoU filtering thresholds
├── validation_report.json  # Final evaluation benchmark (COCO mAP, AP50, AP75)
└── export_manifest.json    # SHA-256 integrity checksums and file sizes
```

---

## 2. ONNX Graph Specifications

- **Format**: ONNX Opset 14 (compatible with ONNX Runtime 1.14+, TensorRT 8.5+, OpenVINO 2023+).
- **Input Node**:
  - Name: `images`
  - Shape: `[3, Height, Width]` (float32, normalized)
- **Output Nodes**:
  - `boxes`: Shape `[Num_Detections, 4]` (float32 coordinates `[x1, y1, x2, y2]`)
  - `labels`: Shape `[Num_Detections]` (int64 class indices)
  - `scores`: Shape `[Num_Detections]` (float32 probabilities $\in [0, 1]$)

---

## 3. Metadata Contracts

### `labels.json`
Maps internal model class indices to project domain labels:
```json
{
  "background_index": 0,
  "classes": [
    {"index": 0, "id": "__background__", "name": "__background__"},
    {"index": 1, "id": "3b29c0f4-5b4e-4f76-8a7e-128a1c9e89fa", "name": "scratch", "color": "#EF4444"},
    {"index": 2, "id": "9a12c8b1-3e4a-4b91-b1e9-923a4b8c71ef", "name": "dent", "color": "#F59E0B"}
  ]
}
```

### `preprocessing.json`
Specifies required transformations prior to model inference:
```json
{
  "task": "OBJECT_DETECTION",
  "input_size": [640, 640],
  "color_mode": "RGB",
  "normalization": {
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225]
  },
  "interpolation": "BILINEAR"
}
```

### `postprocessing.json`
Specifies operating point filters:
```json
{
  "task": "OBJECT_DETECTION",
  "confidence_threshold": 0.25,
  "nms_iou_threshold": 0.45,
  "max_detections": 100,
  "coordinate_format": "xyxy"
}
```

---

## 4. Automated Smoke Verification

Before any exported bundle is registered as `COMPLETED`:
1. The backend initializes an `onnxruntime.InferenceSession` with the exported `model.onnx`.
2. A synthetic test tensor with input dimensions matching `preprocessing.json` is fed into the session.
3. The runner asserts that the output tensors `boxes`, `labels`, and `scores` are produced with expected dimensions and data types.
4. SHA-256 hashes are computed for all files and written to `export_manifest.json`.

If the smoke inference fails, the export is marked as `FAILED` with detailed diagnostic error logs.
