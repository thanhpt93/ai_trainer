# NOVA AI Trainer — Object Detection Metrics & Evaluation

This document outlines the evaluation methodology, metric definitions, and matching algorithms used in **NOVA AI Trainer** for object detection models.

---

## 1. COCO Benchmark Metrics

Object detection models are evaluated using standard COCO metrics via `pycocotools`:

| Metric | Full Name | Description |
| :--- | :--- | :--- |
| **mAP @ 0.50:0.95** | Mean Average Precision | Primary benchmark metric. Average precision across 10 IoU thresholds from 0.50 to 0.95 in steps of 0.05. |
| **AP50** | Average Precision @ IoU 0.50 | Standard PASCAL VOC-style metric. Evaluates precision when an IoU of $\ge 0.50$ is considered a true positive. |
| **AP75** | Average Precision @ IoU 0.75 | Strict localization benchmark requiring $\ge 0.75$ overlap with ground truth bounding boxes. |
| **AP (Per-Class)** | Per-Class Average Precision | Evaluates detection accuracy on each individual user-defined class across IoU thresholds 0.50:0.95. |

---

## 2. Operating Point Evaluation (Confidence Threshold & NMS)

In addition to multi-threshold integral metrics, NOVA AI Trainer evaluates detection performance at an actionable operating point (default: confidence threshold $\tau = 0.25$, IoU matching threshold $\text{IoU}_{match} = 0.50$):

### Bipartite Matching Algorithm
For each evaluation sample:
1. Ground truth boxes $G$ and predicted boxes $P$ are grouped by class.
2. Predictions are sorted in descending order of confidence score.
3. For each prediction $p_i$, calculate IoU with all unassigned ground truth boxes of the same class:
   $$\text{IoU}(A, B) = \frac{\text{Area}(A \cap B)}{\text{Area}(A \cup B)}$$
4. If $\max_j(\text{IoU}(p_i, g_j)) \ge \text{IoU}_{match}$, the pair $(p_i, g_j)$ is counted as a **True Positive (TP)**, and $g_j$ is marked as matched.
5. If $\max_j(\text{IoU}(p_i, g_j)) < \text{IoU}_{match}$, $p_i$ is counted as a **False Positive (FP)**.
6. Any ground truth boxes remaining unmatched at the end of the procedure are counted as **False Negatives (FN)**.

### Operating Point Metrics
- **Precision**:
  $$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
- **Recall**:
  $$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
- **F1-Score**:
  $$\text{F1} = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

---

## 3. Training Telemetry Loss Components

Faster R-CNN optimizes a composite multi-task objective during training:

$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{classifier}} + \mathcal{L}_{\text{box\_reg}} + \mathcal{L}_{\text{objectness}} + \mathcal{L}_{\text{rpn\_box\_reg}}$$

1. **`loss_classifier`**: Cross-entropy classification loss of the Region of Interest (RoI) classification head.
2. **`loss_box_reg`**: Smooth L1 loss between RoI predicted bounding box delta offsets and ground truth boxes.
3. **`loss_objectness`**: Binary cross-entropy loss of the Region Proposal Network (RPN) distinguishing foreground anchors from background.
4. **`loss_rpn_box_reg`**: Smooth L1 regression loss of RPN candidate bounding boxes.

Tracking all four losses independently allows users to diagnose whether localization (regression) or semantic categorization (classification) is the bottleneck during training.
