import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import numpy as np

from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

from backend.app.schemas.training_job import (
    DetectedObject,
    DetectionSampleVisual,
    PerClassDetectionMetric,
    DetectionEvaluationReport,
)


def compute_box_iou(box1: List[float], box2: List[float]) -> float:
    """Computes IoU between two pixel bounding boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union = area1 + area2 - inter_area
    if union <= 0.0:
        return 0.0
    return float(inter_area / union)


class DetectionEvaluator:
    """
    Evaluator for Object Detection pipelines using standard COCO metrics
    and operating point precision/recall analysis.
    """

    @classmethod
    def evaluate(
        cls,
        samples: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        class_mapping: List[Dict[str, Any]],
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.5,
        evaluated_split: str = "val",
    ) -> DetectionEvaluationReport:
        """
        Runs complete COCO evaluation and generates per-class metrics and sample visuals.
        """
        # Map class indices
        foreground_classes = [c for c in class_mapping if not c.get("is_background", False)]
        index_to_name: Dict[int, str] = {c["index"]: c["name"] for c in foreground_classes}
        index_to_label_id: Dict[int, str] = {c["index"]: c.get("label_id", "") for c in foreground_classes}
        cat_ids = [c["index"] for c in foreground_classes]

        # 1. Build COCO ground-truth data structure
        coco_gt = {
            "images": [],
            "annotations": [],
            "categories": [
                {"id": c["index"], "name": c["name"]}
                for c in foreground_classes
            ],
        }

        ann_id = 1
        total_gt_boxes = 0

        for idx, sample in enumerate(samples, start=1):
            img_id = idx
            w = sample.get("width", 800)
            h = sample.get("height", 600)
            coco_gt["images"].append({
                "id": img_id,
                "file_name": sample.get("relative_path", f"image_{img_id}.jpg"),
                "width": w,
                "height": h,
            })

            boxes = sample.get("boxes", [])
            labels = sample.get("labels", [])
            for b, l in zip(boxes, labels):
                if l not in index_to_name:
                    continue
                # COCO format: [x, y, width, height]
                bw = max(0.0, b[2] - b[0])
                bh = max(0.0, b[3] - b[1])
                coco_gt["annotations"].append({
                    "id": ann_id,
                    "image_id": img_id,
                    "category_id": int(l),
                    "bbox": [float(b[0]), float(b[1]), float(bw), float(bh)],
                    "area": float(bw * bh),
                    "iscrowd": 0,
                })
                ann_id += 1
                total_gt_boxes += 1

        # 2. Build COCO prediction list
        coco_dt = []
        total_pred_boxes = 0

        for idx, pred in enumerate(predictions, start=1):
            img_id = idx
            p_boxes = pred.get("boxes", [])
            p_labels = pred.get("labels", [])
            p_scores = pred.get("scores", [])

            for b, l, s in zip(p_boxes, p_labels, p_scores):
                if l not in index_to_name:
                    continue
                bw = max(0.0, b[2] - b[0])
                bh = max(0.0, b[3] - b[1])
                coco_dt.append({
                    "image_id": img_id,
                    "category_id": int(l),
                    "bbox": [float(b[0]), float(b[1]), float(bw), float(bh)],
                    "score": float(s),
                })
                total_pred_boxes += 1

        # 3. Run COCO evaluation if ground truth has annotations
        map_val = 0.0
        map_50 = 0.0
        map_75 = 0.0
        per_class_coco: Dict[int, Dict[str, float]] = {
            cid: {"ap": 0.0, "ap50": 0.0, "ap75": 0.0} for cid in cat_ids
        }

        if coco_gt["annotations"] and coco_dt:
            try:
                coco_gt_obj = COCO()
                coco_gt_obj.dataset = coco_gt
                coco_gt_obj.createIndex()

                coco_dt_obj = coco_gt_obj.loadRes(coco_dt)

                coco_eval = COCOeval(coco_gt_obj, coco_dt_obj, "bbox")
                coco_eval.evaluate()
                coco_eval.accumulate()
                coco_eval.summarize()

                # stats[0]: AP @ IoU=0.50:0.95
                # stats[1]: AP @ IoU=0.50
                # stats[2]: AP @ IoU=0.75
                if coco_eval.stats is not None and len(coco_eval.stats) >= 3:
                    map_val = float(max(0.0, coco_eval.stats[0]))
                    map_50 = float(max(0.0, coco_eval.stats[1]))
                    map_75 = float(max(0.0, coco_eval.stats[2]))

                # Per-class AP calculation
                for cid in cat_ids:
                    try:
                        c_eval = COCOeval(coco_gt_obj, coco_dt_obj, "bbox")
                        c_eval.params.catIds = [cid]
                        c_eval.evaluate()
                        c_eval.accumulate()
                        c_eval.summarize()
                        if c_eval.stats is not None and len(c_eval.stats) >= 3:
                            per_class_coco[cid] = {
                                "ap": float(max(0.0, c_eval.stats[0])),
                                "ap50": float(max(0.0, c_eval.stats[1])),
                                "ap75": float(max(0.0, c_eval.stats[2])),
                            }
                    except Exception:
                        pass
            except Exception as e:
                print(f"[DetectionEvaluator] COCOeval error: {e}")

        # 4. Operating point evaluation (Precision, Recall, TP, FP, FN matching per image)
        total_tp = 0
        total_fp = 0
        total_fn = 0

        per_class_stats: Dict[int, Dict[str, int]] = {
            cid: {"tp": 0, "fp": 0, "fn": 0, "gt_count": 0, "pred_count": 0}
            for cid in cat_ids
        }

        sample_visuals: List[DetectionSampleVisual] = []

        for idx, (sample, pred) in enumerate(zip(samples, predictions), start=1):
            w = sample.get("width", 800)
            h = sample.get("height", 600)
            gt_boxes = sample.get("boxes", [])
            gt_labels = sample.get("labels", [])

            p_boxes = pred.get("boxes", [])
            p_labels = pred.get("labels", [])
            p_scores = pred.get("scores", [])

            # Filter predictions by confidence threshold
            filtered_preds = []
            for b, l, s in zip(p_boxes, p_labels, p_scores):
                if s >= confidence_threshold and l in index_to_name:
                    filtered_preds.append({"box": b, "label": l, "score": s})

            # Sort filtered predictions by confidence descending
            filtered_preds.sort(key=lambda x: x["score"], reverse=True)

            gt_matched = [False] * len(gt_boxes)
            pred_matched = [False] * len(filtered_preds)
            pred_ious = [0.0] * len(filtered_preds)

            # Match predictions with ground truth boxes (Greedy bipartite matching)
            for p_idx, p in enumerate(filtered_preds):
                best_iou = 0.0
                best_gt_idx = -1
                for g_idx, (gb, gl) in enumerate(zip(gt_boxes, gt_labels)):
                    if gl != p["label"]:
                        continue
                    if gt_matched[g_idx]:
                        continue
                    iou = compute_box_iou(p["box"], gb)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = g_idx

                if best_iou >= iou_threshold and best_gt_idx >= 0:
                    gt_matched[best_gt_idx] = True
                    pred_matched[p_idx] = True
                    pred_ious[p_idx] = round(best_iou, 3)

            img_tp = sum(pred_matched)
            img_fp = len(filtered_preds) - img_tp
            img_fn = len(gt_boxes) - sum(gt_matched)

            total_tp += img_tp
            total_fp += img_fp
            total_fn += img_fn

            # Per class counts
            for gb, gl in zip(gt_boxes, gt_labels):
                if gl in per_class_stats:
                    per_class_stats[gl]["gt_count"] += 1

            for p_idx, p in enumerate(filtered_preds):
                lbl = p["label"]
                if lbl in per_class_stats:
                    per_class_stats[lbl]["pred_count"] += 1
                    if pred_matched[p_idx]:
                        per_class_stats[lbl]["tp"] += 1
                    else:
                        per_class_stats[lbl]["fp"] += 1

            for g_idx, matched in enumerate(gt_matched):
                if not matched and g_idx < len(gt_labels):
                    lbl = gt_labels[g_idx]
                    if lbl in per_class_stats:
                        per_class_stats[lbl]["fn"] += 1

            # Build DetectedObject visual items
            gt_detected_objects = []
            for b, l in zip(gt_boxes, gt_labels):
                cname = index_to_name.get(l, f"Class_{l}")
                lbl_id = index_to_label_id.get(l, "")
                norm_box = [
                    round(b[0] / max(1, w), 4),
                    round(b[1] / max(1, h), 4),
                    round(b[2] / max(1, w), 4),
                    round(b[3] / max(1, h), 4),
                ]
                gt_detected_objects.append(
                    DetectedObject(
                        label_id=lbl_id,
                        class_name=cname,
                        class_index=l,
                        confidence=1.0,
                        box=[round(coord, 2) for coord in b],
                        box_normalized=norm_box,
                        matched_gt=True,
                    )
                )

            pred_detected_objects = []
            for p_idx, p in enumerate(filtered_preds):
                l = p["label"]
                b = p["box"]
                cname = index_to_name.get(l, f"Class_{l}")
                lbl_id = index_to_label_id.get(l, "")
                norm_box = [
                    round(b[0] / max(1, w), 4),
                    round(b[1] / max(1, h), 4),
                    round(b[2] / max(1, w), 4),
                    round(b[3] / max(1, h), 4),
                ]
                pred_detected_objects.append(
                    DetectedObject(
                        label_id=lbl_id,
                        class_name=cname,
                        class_index=l,
                        confidence=round(float(p["score"]), 3),
                        box=[round(coord, 2) for coord in b],
                        box_normalized=norm_box,
                        matched_gt=pred_matched[p_idx],
                        iou=pred_ious[p_idx],
                    )
                )

            sample_visuals.append(
                DetectionSampleVisual(
                    image_id=sample.get("image_id", f"sample_{idx}"),
                    relative_path=sample.get("relative_path", f"sample_{idx}.jpg"),
                    width=w,
                    height=h,
                    ground_truth_boxes=gt_detected_objects,
                    predicted_boxes=pred_detected_objects,
                    matched_count=img_tp,
                    false_positive_count=img_fp,
                    false_negative_count=img_fn,
                )
            )

        # Global precision & recall at operating point
        precision = float(total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
        recall = float(total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 0.0

        # Per-class metrics
        per_class_metrics: List[PerClassDetectionMetric] = []
        for cid in cat_ids:
            cname = index_to_name.get(cid, f"Class_{cid}")
            c_coco = per_class_coco.get(cid, {"ap": 0.0, "ap50": 0.0, "ap75": 0.0})
            c_stats = per_class_stats.get(cid, {"tp": 0, "fp": 0, "fn": 0, "gt_count": 0, "pred_count": 0})
            c_tp = c_stats["tp"]
            c_fp = c_stats["fp"]
            c_fn = c_stats["fn"]
            c_prec = float(c_tp / (c_tp + c_fp)) if (c_tp + c_fp) > 0 else 0.0
            c_rec = float(c_tp / (c_tp + c_fn)) if (c_tp + c_fn) > 0 else 0.0

            per_class_metrics.append(
                PerClassDetectionMetric(
                    class_name=cname,
                    ap=round(c_coco["ap"], 4),
                    ap50=round(c_coco["ap50"], 4),
                    ap75=round(c_coco["ap75"], 4),
                    precision=round(c_prec, 4),
                    recall=round(c_rec, 4),
                    ground_truth_count=c_stats["gt_count"],
                    prediction_count=c_stats["pred_count"],
                )
            )

        report = DetectionEvaluationReport(
            task_type="Object Detection",
            total_samples=len(samples),
            total_ground_truth_boxes=total_gt_boxes,
            total_predicted_boxes=total_pred_boxes,
            map=round(map_val, 4),
            map_50=round(map_50, 4),
            map_75=round(map_75, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            per_class_metrics=per_class_metrics,
            samples=sample_visuals,
            operating_point={
                "confidence_threshold": confidence_threshold,
                "iou_threshold": iou_threshold,
            },
            evaluated_split=evaluated_split,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

        return report
