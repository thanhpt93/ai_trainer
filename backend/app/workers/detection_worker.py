import os
import sys
import time
import json
import logging
import argparse
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from backend.app.adapters.detection_dataset_adapter import (
    DetectionTorchDataset,
    detection_collate_fn,
)
from backend.app.adapters.detection_evaluator import DetectionEvaluator
from backend.app.services.model_catalog_service import ModelCatalogService


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_worker():
    parser = argparse.ArgumentParser(description="NOVA AI Trainer Object Detection Worker")
    parser.add_argument("--config", type=str, required=True, help="Path to job_config.json")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    job_id = cfg.get("job_id", "unknown_job")
    run_dir = Path(cfg.get("run_dir", config_path.parent)).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    # Setup Logging
    log_file = run_dir / "train.log"
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_file), mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger("DetectionWorker")

    logger.info("=" * 60)
    logger.info(f"Starting Object Detection Training Worker for Job '{job_id}'")
    logger.info("=" * 60)

    # 1. Device Selection
    requested_device = cfg.get("device", "auto").lower()
    if requested_device == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda:0")
    elif requested_device == "auto" and torch.cuda.is_available():
        device = torch.device("cuda:0")
    else:
        device = torch.device("cpu")

    logger.info(f"Execution Device: {device} ({'GPU: ' + torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")

    # 2. Dataset & Splits
    splits = cfg.get("splits", {})
    train_samples = splits.get("train", [])
    val_samples = splits.get("val", [])
    test_samples = splits.get("test", [])
    class_mapping = cfg.get("class_mapping", [])

    if not train_samples:
        logger.error("No training samples provided in job configuration.")
        with open(run_dir / "job_finished.json", "w", encoding="utf-8") as f:
            json.dump({
                "status": "FAILED",
                "completed_at": utc_now_iso(),
                "error": "No training samples provided in job configuration.",
            }, f, indent=2)
        sys.exit(1)

    logger.info(f"Classes (total {len(class_mapping)} with background): {[c['name'] for c in class_mapping]}")
    logger.info(f"Dataset split size: Train={len(train_samples)}, Val={len(val_samples)}, Test={len(test_samples)}")

    input_size = int(cfg.get("input_size", 800))
    batch_size = max(1, int(cfg.get("batch_size", 2)))
    num_workers = int(cfg.get("num_workers", 0))
    horizontal_flip = bool(cfg.get("horizontal_flip", True))
    confidence_thresh = float(cfg.get("confidence_threshold", 0.5))
    iou_thresh = float(cfg.get("iou_threshold", 0.5))
    grad_clip = float(cfg.get("grad_clip", 10.0)) if cfg.get("grad_clip") is not None else None

    train_dataset = DetectionTorchDataset(
        samples=train_samples,
        input_size=input_size,
        is_train=True,
        horizontal_flip=horizontal_flip,
    )
    val_dataset = DetectionTorchDataset(
        samples=val_samples,
        input_size=input_size,
        is_train=False,
        horizontal_flip=False,
    ) if val_samples else None

    test_dataset = DetectionTorchDataset(
        samples=test_samples,
        input_size=input_size,
        is_train=False,
        horizontal_flip=False,
    ) if test_samples else None

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        collate_fn=detection_collate_fn,
        drop_last=False,
    )

    val_loader = (
        DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            collate_fn=detection_collate_fn,
        )
        if val_dataset
        else None
    )

    test_loader = (
        DataLoader(
            test_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            collate_fn=detection_collate_fn,
        )
        if test_dataset
        else None
    )

    # 3. Model Architecture
    arch = cfg.get("model_architecture", "fasterrcnn_resnet50_fpn")
    pretrained = bool(cfg.get("pretrained", True))
    num_classes = len(class_mapping)  # includes background class (index 0)

    logger.info(f"Building detection architecture '{arch}' (pretrained={pretrained}, num_classes={num_classes})...")
    model = ModelCatalogService.build_model(arch, num_classes=num_classes, pretrained=pretrained)

    # Check for resume checkpoint
    start_epoch = 1
    best_val_metric = -1.0
    best_epoch = -1
    resume_checkpoint_path = cfg.get("resume_checkpoint")

    if resume_checkpoint_path and Path(resume_checkpoint_path).exists():
        logger.info(f"Resuming training from checkpoint: {resume_checkpoint_path}")
        try:
            cp = torch.load(resume_checkpoint_path, map_location=device)
            model.load_state_dict(cp["model_state_dict"])
            start_epoch = cp.get("epoch", 0) + 1
            best_val_metric = cp.get("best_val_metric", -1.0)
            logger.info(f"Successfully loaded checkpoint from epoch {start_epoch - 1}. Previous best metric: {best_val_metric}")
        except Exception as e:
            logger.warning(f"Could not load resume checkpoint: {e}. Starting from epoch 1.")

    model.to(device)

    # 4. Optimizer & Scheduler
    lr = float(cfg.get("learning_rate", 0.0005))
    weight_decay = float(cfg.get("weight_decay", 0.0001))
    opt_name = cfg.get("optimizer", "SGD").lower()

    params = [p for p in model.parameters() if p.requires_grad]

    if opt_name == "adamw":
        optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    else:
        momentum = float(cfg.get("momentum", 0.9))
        optimizer = torch.optim.SGD(params, lr=lr, momentum=momentum, weight_decay=weight_decay)

    epochs = int(cfg.get("epochs", 10))
    sched_name = cfg.get("scheduler", "step").lower()
    if sched_name == "step":
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=max(1, epochs // 3), gamma=0.1)
    elif sched_name == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    else:
        scheduler = None

    # Load optimizer state if resuming
    if resume_checkpoint_path and Path(resume_checkpoint_path).exists():
        try:
            cp = torch.load(resume_checkpoint_path, map_location=device)
            if "optimizer_state_dict" in cp:
                optimizer.load_state_dict(cp["optimizer_state_dict"])
        except Exception:
            pass

    # Tracking
    epoch_metrics_history: List[Dict[str, Any]] = []
    metrics_file = run_dir / "metrics.json"
    cancel_requested_flag = run_dir / "cancel.requested"

    logger.info(f"Starting training from epoch {start_epoch} to {epochs}...")
    training_start_time = time.time()

    for epoch in range(start_epoch, epochs + 1):
        epoch_start = time.time()

        # Check cooperative cancellation
        if cancel_requested_flag.exists():
            logger.info("Cancellation flag detected. Saving latest checkpoint and terminating gracefully...")
            torch.save(
                {
                    "epoch": epoch - 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "class_mapping": class_mapping,
                    "architecture": arch,
                    "best_val_metric": best_val_metric,
                },
                run_dir / "latest_checkpoint.pt",
            )
            with open(run_dir / "job_finished.json", "w", encoding="utf-8") as f:
                json.dump({
                    "status": "CANCELLED",
                    "completed_at": utc_now_iso(),
                    "best_val_metric": best_val_metric,
                    "epochs_completed": epoch - 1,
                }, f, indent=2)
            sys.exit(0)

        # -----------------
        # 1. Training Phase
        # -----------------
        model.train()
        train_loss = 0.0
        train_batches = 0
        loss_components_sum: Dict[str, float] = {
            "loss_classifier": 0.0,
            "loss_box_reg": 0.0,
            "loss_objectness": 0.0,
            "loss_rpn_box_reg": 0.0,
        }

        for batch_idx, (images, targets) in enumerate(train_loader):
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            optimizer.zero_grad()
            loss_dict = model(images, targets)

            losses = sum(loss for loss in loss_dict.values())
            loss_val = losses.item()

            if not math.isfinite(loss_val):
                logger.warning(f"Loss is {loss_val}, skipping batch {batch_idx}")
                continue

            losses.backward()
            if grad_clip:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()

            train_loss += loss_val
            train_batches += 1
            for k in loss_components_sum:
                if k in loss_dict:
                    loss_components_sum[k] += float(loss_dict[k].item())

        avg_train_loss = train_loss / max(1, train_batches)
        avg_loss_components = {
            k: round(v / max(1, train_batches), 4)
            for k, v in loss_components_sum.items()
        }

        if scheduler:
            scheduler.step()

        # -------------------
        # 2. Validation Phase
        # -------------------
        val_map = 0.0
        val_map_50 = 0.0
        val_map_75 = 0.0
        val_prec = 0.0
        val_rec = 0.0

        if val_loader and len(val_samples) > 0:
            model.eval()
            val_predictions = []

            with torch.no_grad():
                for images, targets in val_loader:
                    images = [img.to(device) for img in images]
                    outputs = model(images)

                    for out in outputs:
                        boxes = out["boxes"].cpu().numpy().tolist()
                        labels = out["labels"].cpu().numpy().tolist()
                        scores = out["scores"].cpu().numpy().tolist()
                        val_predictions.append({
                            "boxes": boxes,
                            "labels": labels,
                            "scores": scores,
                        })

            # Evaluate with COCO evaluator
            try:
                eval_report = DetectionEvaluator.evaluate(
                    samples=val_samples,
                    predictions=val_predictions,
                    class_mapping=class_mapping,
                    confidence_threshold=confidence_thresh,
                    iou_threshold=iou_thresh,
                    evaluated_split="val",
                )
                val_map = eval_report.map
                val_map_50 = eval_report.map_50
                val_map_75 = eval_report.map_75
                val_prec = eval_report.precision
                val_rec = eval_report.recall
            except Exception as e:
                logger.warning(f"Validation evaluation warning: {e}")

        duration = round(time.time() - epoch_start, 2)
        current_lr = optimizer.param_groups[0]["lr"]

        logger.info(
            f"Epoch [{epoch}/{epochs}] ({duration}s) - "
            f"Train Loss: {avg_train_loss:.4f} "
            f"(cls: {avg_loss_components['loss_classifier']}, box: {avg_loss_components['loss_box_reg']}, "
            f"obj: {avg_loss_components['loss_objectness']}) | "
            f"Val mAP: {val_map:.4f}, mAP@50: {val_map_50:.4f}, Prec: {val_prec:.4f}, Rec: {val_rec:.4f} | "
            f"LR: {current_lr:.6f}"
        )

        epoch_metric = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "train_accuracy": round(val_map_50, 4),  # for generic plot compatibility
            "val_loss": round(avg_train_loss, 4),
            "val_accuracy": round(val_map_50, 4),
            "val_map": val_map,
            "val_map_50": val_map_50,
            "val_map_75": val_map_75,
            "val_precision": val_prec,
            "val_recall": val_rec,
            "val_f1": round(2 * val_prec * val_rec / (val_prec + val_rec + 1e-6), 4),
            "loss_classifier": avg_loss_components["loss_classifier"],
            "loss_box_reg": avg_loss_components["loss_box_reg"],
            "loss_objectness": avg_loss_components["loss_objectness"],
            "loss_rpn_box_reg": avg_loss_components["loss_rpn_box_reg"],
            "learning_rate": current_lr,
            "duration_seconds": duration,
            "timestamp": utc_now_iso(),
        }
        epoch_metrics_history.append(epoch_metric)

        # Best Model Tracking
        # Metric is validation mAP@50 (or negative loss if mAP=0)
        current_metric = val_map_50 if val_loader else -avg_train_loss
        is_best = current_metric > best_val_metric or (best_val_metric <= -999.0 and epoch == start_epoch)

        if is_best:
            best_val_metric = current_metric
            best_epoch = epoch
            logger.info(f"--> Best model improved to metric {best_val_metric:.4f}. Saving best_checkpoint.pt")
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "class_mapping": class_mapping,
                    "architecture": arch,
                    "best_val_metric": best_val_metric,
                    "val_map": val_map,
                    "val_map_50": val_map_50,
                    "val_map_75": val_map_75,
                    "config": cfg,
                },
                run_dir / "best_checkpoint.pt",
            )

        # Save latest checkpoint
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "class_mapping": class_mapping,
                "architecture": arch,
                "best_val_metric": best_val_metric,
                "val_map": val_map,
                "val_map_50": val_map_50,
            },
            run_dir / "latest_checkpoint.pt",
        )

        # Write telemetry to metrics.json
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "current_epoch": epoch,
                    "total_epochs": epochs,
                    "best_val_metric": best_val_metric,
                    "best_epoch": best_epoch,
                    "history": epoch_metrics_history,
                },
                f,
                indent=2,
            )

    total_time = round(time.time() - training_start_time, 2)
    logger.info(f"Training completed in {total_time}s. Best Epoch: {best_epoch} (Metric: {best_val_metric:.4f})")

    # 5. Final Evaluation on Validation or Test Split
    eval_target_samples = test_samples if test_samples else val_samples
    eval_target_loader = test_loader if test_loader else val_loader
    eval_split_name = "test" if test_samples else "val"

    if eval_target_samples and eval_target_loader:
        logger.info(f"Running final benchmark evaluation on '{eval_split_name}' split ({len(eval_target_samples)} images)...")
        best_cp_path = run_dir / "best_checkpoint.pt"
        if best_cp_path.exists():
            cp = torch.load(best_cp_path, map_location=device)
            model.load_state_dict(cp["model_state_dict"])

        model.eval()
        eval_predictions = []

        with torch.no_grad():
            for images, targets in eval_target_loader:
                images = [img.to(device) for img in images]
                outputs = model(images)
                for out in outputs:
                    eval_predictions.append({
                        "boxes": out["boxes"].cpu().numpy().tolist(),
                        "labels": out["labels"].cpu().numpy().tolist(),
                        "scores": out["scores"].cpu().numpy().tolist(),
                    })

        final_report = DetectionEvaluator.evaluate(
            samples=eval_target_samples,
            predictions=eval_predictions,
            class_mapping=class_mapping,
            confidence_threshold=confidence_thresh,
            iou_threshold=iou_thresh,
            evaluated_split=eval_split_name,
        )

        eval_file = run_dir / "evaluation_results.json"
        with open(eval_file, "w", encoding="utf-8") as f:
            json.dump(final_report.model_dump(), f, indent=2)

        logger.info(f"Final Evaluation: mAP={final_report.map:.4f}, mAP@50={final_report.map_50:.4f}, Precision={final_report.precision:.4f}, Recall={final_report.recall:.4f}")

    # 6. Automatic ONNX Export
    logger.info("Exporting trained model to ONNX deployment package...")
    try:
        best_cp_path = run_dir / "best_checkpoint.pt"
        if not best_cp_path.exists():
            best_cp_path = run_dir / "latest_checkpoint.pt"

        if best_cp_path.exists():
            cp = torch.load(best_cp_path, map_location=torch.device("cpu"))
            export_model = ModelCatalogService.build_model(arch, num_classes=num_classes, pretrained=False)
            export_model.load_state_dict(cp["model_state_dict"])

            export_dir = run_dir / "export"
            export_resp = ModelCatalogService.export_detection_onnx_package(
                model=export_model,
                output_dir=export_dir,
                model_name=cfg.get("name", f"detection_{job_id}"),
                architecture=arch,
                class_mapping=class_mapping,
                input_size=input_size,
                validation_report=cfg.get("validation_report"),
            )
            logger.info(f"Model exported successfully: {export_resp.onnx_file_path} (verified: {export_resp.verified_with_inference})")
    except Exception as e:
        logger.warning(f"Automatic ONNX export warning: {e}")

    # 7. Write Job Finished
    with open(run_dir / "job_finished.json", "w", encoding="utf-8") as f:
        json.dump({
            "status": "COMPLETED",
            "completed_at": utc_now_iso(),
            "best_val_metric": best_val_metric,
            "best_epoch": best_epoch,
            "total_epochs": epochs,
        }, f, indent=2)

    logger.info("Training job finished successfully.")


if __name__ == "__main__":
    run_worker()
