# NOVA AI Trainer — Model Catalog

This document specifies all model architectures supported by **NOVA AI Trainer**, categorized by vision task.

---

## 1. Object Detection Architectures

| Model ID | Architecture | Backbone | Target Resolution | Supported Devices | Checkpoints | Export Formats |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `fasterrcnn_resnet50_fpn` | Faster R-CNN | ResNet-50 FPN | Dynamic (Default 640×640) | CUDA, CPU | Full (weights, optimizer, scheduler) | ONNX (Opset 14) |
| `fasterrcnn_mobilenet_v3_large_320_fpn` | Faster R-CNN | MobileNetV3 Large FPN | Dynamic (Default 320×320) | CUDA, CPU | Full (weights, optimizer, scheduler) | ONNX (Opset 14) |

### Detection Capabilities
- **Background Class Handling**: Strict reservation of index `0` for `__background__`.
- **Pretrained Weights**: Downloaded and cached via Torchvision weights registry (`ResNet50_Weights.DEFAULT`, `MobileNet_V3_Large_Weights.DEFAULT`).
- **Telemetry Breakdown**: Reports `loss_classifier`, `loss_box_reg`, `loss_objectness`, `loss_rpn_box_reg`.
- **Evaluation**: Integrated standard COCO evaluation via `pycocotools` (`mAP @ 0.50:0.95`, `AP50`, `AP75`, per-class AP).
- **Inference Adapter**: Accepts arbitrary images, scales boxes to target image dimensions, and filters background labels.

---

## 2. Image Classification Architectures

| Model ID | Architecture | Parameter Count | Target Resolution | Supported Devices | Checkpoints | Export Formats |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `resnet18` | ResNet-18 | 11.7 M | 224 × 224 | CUDA, CPU | Full | ONNX (Dynamic Batch) |
| `mobilenet_v3_small` | MobileNetV3-Small | 2.5 M | 224 × 224 | CUDA, CPU | Full | ONNX (Dynamic Batch) |
| `mobilenet_v3_large` | MobileNetV3-Large | 5.4 M | 224 × 224 | CUDA, CPU | Full | ONNX (Dynamic Batch) |
| `resnet50` | ResNet-50 | 25.6 M | 224 × 224 | CUDA, CPU | Full | ONNX (Dynamic Batch) |
| `efficientnet_b0` | EfficientNet-B0 | 5.3 M | 224 × 224 | CUDA, CPU | Full | ONNX (Dynamic Batch) |

---

## 3. Architecture Selection Criteria

- **Choose `fasterrcnn_resnet50_fpn` when**:
  - Objects are small or multi-scale.
  - Localization precision and high mAP are prioritized over training speed.
  - Dedicated GPU hardware (e.g. NVIDIA RTX) is available.
- **Choose `fasterrcnn_mobilenet_v3_large_320_fpn` when**:
  - Fast iteration cycles and low memory footprint are required.
  - Targeting CPU-only edge devices or embedded processors.
