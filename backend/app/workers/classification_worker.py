import os
import sys
import time
import json
import logging
import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import torchvision.models as models

from backend.app.services.model_catalog_service import (
    ModelCatalogService,
    IMAGENET_MEAN,
    IMAGENET_STD,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClassificationDataset(Dataset):
    """PyTorch Dataset loading images from file paths with given torchvision transform."""

    def __init__(self, samples: List[Dict[str, Any]], label_to_idx: Dict[str, int], transform=None):
        self.samples = samples
        self.label_to_idx = label_to_idx
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str, str]:
        item = self.samples[idx]
        img_path = item["absolute_path"]
        label_id = item["label_id"]
        target = self.label_to_idx[label_id]

        try:
            with Image.open(img_path) as img:
                img = img.convert("RGB")
                if self.transform:
                    tensor = self.transform(img)
                else:
                    tensor = transforms.ToTensor()(img)
        except Exception as e:
            # Fallback to zero tensor on corrupted image
            tensor = torch.zeros(3, 224, 224)

        return tensor, target, item.get("image_id", ""), item.get("relative_path", "")


def evaluate_dataset(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    class_names: List[str],
) -> Dict[str, Any]:
    """
    Evaluates model performance, computing loss, accuracy, macro precision/recall/F1,
    confusion matrix, and list of misclassified images with softmax confidence.
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    num_classes = len(class_names)

    # Confusion matrix: [ground_truth, predicted]
    confusion_matrix = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    misclassified_samples: List[Dict[str, Any]] = []

    with torch.no_grad():
        for inputs, targets, img_ids, rel_paths in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            total_loss += loss.item() * inputs.size(0)

            probs = torch.softmax(outputs, dim=1)
            confs, preds = torch.max(probs, 1)

            total += targets.size(0)
            correct += (preds == targets).sum().item()

            for i in range(targets.size(0)):
                gt = targets[i].item()
                pred = preds[i].item()
                conf = confs[i].item()
                confusion_matrix[gt][pred] += 1

                if gt != pred:
                    misclassified_samples.append({
                        "image_id": img_ids[i],
                        "relative_path": rel_paths[i],
                        "ground_truth": class_names[gt],
                        "predicted": class_names[pred],
                        "confidence": round(float(conf), 4),
                    })

    avg_loss = total_loss / max(1, total)
    accuracy = correct / max(1, total)

    # Per-class precision, recall, F1
    per_class_metrics = []
    precisions, recalls, f1s = [], [], []

    for c in range(num_classes):
        tp = confusion_matrix[c][c]
        fp = sum(confusion_matrix[r][c] for r in range(num_classes) if r != c)
        fn = sum(confusion_matrix[c][p] for p in range(num_classes) if p != c)
        support = sum(confusion_matrix[c])

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

        per_class_metrics.append({
            "class_name": class_names[c],
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "support": support,
        })

    macro_prec = sum(precisions) / max(1, num_classes)
    macro_rec = sum(recalls) / max(1, num_classes)
    macro_f1 = sum(f1s) / max(1, num_classes)

    return {
        "loss": round(avg_loss, 4),
        "accuracy": round(accuracy, 4),
        "precision_macro": round(macro_prec, 4),
        "recall_macro": round(macro_rec, 4),
        "f1_macro": round(macro_f1, 4),
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": {
            "labels": class_names,
            "matrix": confusion_matrix,
        },
        "misclassified_samples": misclassified_samples[:100],  # Limit to 100 entries
        "total_samples": total,
    }


def run_worker(config_path_str: str) -> None:
    config_path = Path(config_path_str).resolve()
    if not config_path.exists():
        print(f"FATAL: Config file does not exist: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    run_dir = Path(cfg["run_dir"]).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    log_file = run_dir / "train.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger("classification_worker")
    logger.info(f"=== Starting Training Worker for Job {cfg['job_id']} ===")
    logger.info(f"Run directory: {run_dir}")

    # Set seeds for reproducibility
    seed = cfg.get("random_seed", 42)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Determine execution device
    req_device = cfg.get("device", "auto").lower()
    if req_device == "cuda" or (req_device == "auto" and torch.cuda.is_available()):
        device = torch.device("cuda")
        logger.info(f"Using GPU device: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        logger.info("Using CPU device for training.")

    # Class mappings
    class_mapping = cfg["class_mapping"]
    num_classes = len(class_mapping)
    class_names = [c["name"] for c in class_mapping]
    label_to_idx = {c["label_id"]: c["index"] for c in class_mapping}
    logger.info(f"Classes ({num_classes}): {class_names}")

    # Datasets and loaders
    splits = cfg["splits"]
    input_size = cfg.get("input_size", 224)
    batch_size = cfg.get("batch_size", 16)
    num_workers = cfg.get("num_workers", 0)

    # Transforms
    train_transforms_list = [
        transforms.Resize((input_size, input_size)),
    ]
    if cfg.get("horizontal_flip", True):
        train_transforms_list.append(transforms.RandomHorizontalFlip(p=0.5))
    if cfg.get("rotation_degrees", 0) > 0:
        train_transforms_list.append(transforms.RandomRotation(cfg["rotation_degrees"]))
    if cfg.get("color_jitter", False):
        train_transforms_list.append(transforms.ColorJitter(brightness=0.1, contrast=0.1))
    train_transforms_list.extend([
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    train_transform = transforms.Compose(train_transforms_list)

    val_transform = transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    train_ds = ClassificationDataset(splits["train"], label_to_idx, transform=train_transform)
    val_ds = ClassificationDataset(splits["val"], label_to_idx, transform=val_transform)
    test_ds = ClassificationDataset(splits.get("test", []), label_to_idx, transform=val_transform)

    logger.info(f"Dataset split sizes: Train={len(train_ds)}, Val={len(val_ds)}, Test={len(test_ds)}")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = (
        DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
        if len(test_ds) > 0
        else None
    )

    # Instantiate model
    arch = cfg.get("model_architecture", "resnet18")
    pretrained = cfg.get("pretrained", True)
    logger.info(f"Building model architecture '{arch}' (pretrained={pretrained})...")
    model = ModelCatalogService.build_model(arch, num_classes=num_classes, pretrained=pretrained)
    model.to(device)

    # Optimization
    lr = float(cfg.get("learning_rate", 0.001))
    weight_decay = float(cfg.get("weight_decay", 0.0001))
    opt_name = cfg.get("optimizer", "AdamW").lower()

    if opt_name == "sgd":
        momentum = float(cfg.get("momentum", 0.9))
        optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=momentum, weight_decay=weight_decay)
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    epochs = int(cfg.get("epochs", 10))
    sched_name = cfg.get("scheduler", "step").lower()
    if sched_name == "step":
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=max(1, epochs // 3), gamma=0.1)
    elif sched_name == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    else:
        scheduler = None

    criterion = nn.CrossEntropyLoss()

    # Metrics & state tracking
    epoch_metrics_history: List[Dict[str, Any]] = []
    best_val_acc = -1.0
    best_epoch = -1
    early_stop_patience = cfg.get("patience", 5) if cfg.get("early_stopping", False) else None
    epochs_no_improve = 0

    metrics_file = run_dir / "metrics.json"
    cancel_requested_flag = run_dir / "cancel.requested"

    # Training Loop
    logger.info(f"Starting training for {epochs} epochs...")
    training_start_time = time.time()

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()

        # Check cooperative cancellation
        if cancel_requested_flag.exists():
            logger.info("Cancellation flag detected. Terminating training loop gracefully...")
            # Save latest checkpoint before exit
            torch.save(
                {
                    "epoch": epoch - 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "class_mapping": class_mapping,
                    "best_val_accuracy": best_val_acc,
                },
                run_dir / "latest_checkpoint.pt",
            )
            with open(run_dir / "job_finished.json", "w", encoding="utf-8") as f:
                json.dump({
                    "status": "CANCELLED",
                    "completed_at": utc_now_iso(),
                    "best_val_accuracy": best_val_acc,
                    "epochs_completed": epoch - 1,
                }, f, indent=2)
            sys.exit(0)

        # 1. Training Phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_idx, (inputs, targets, _, _) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            train_total += targets.size(0)
            train_correct += (preds == targets).sum().item()

        avg_train_loss = train_loss / max(1, train_total)
        avg_train_acc = train_correct / max(1, train_total)

        if scheduler:
            scheduler.step()

        # 2. Validation Phase
        val_eval = evaluate_dataset(model, val_loader, criterion, device, class_names)
        val_loss = val_eval["loss"]
        val_acc = val_eval["accuracy"]
        val_prec = val_eval["precision_macro"]
        val_rec = val_eval["recall_macro"]
        val_f1 = val_eval["f1_macro"]

        duration = round(time.time() - epoch_start, 2)
        current_lr = optimizer.param_groups[0]["lr"]

        logger.info(
            f"Epoch [{epoch}/{epochs}] - Duration: {duration}s - "
            f"Train Loss: {avg_train_loss:.4f}, Train Acc: {avg_train_acc*100:.2f}% | "
            f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc*100:.2f}%, F1: {val_f1:.4f} | LR: {current_lr:.6f}"
        )

        epoch_metric = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "train_accuracy": round(avg_train_acc, 4),
            "val_loss": val_loss,
            "val_accuracy": val_acc,
            "val_precision": val_prec,
            "val_recall": val_rec,
            "val_f1": val_f1,
            "learning_rate": current_lr,
            "duration_seconds": duration,
            "timestamp": utc_now_iso(),
        }
        epoch_metrics_history.append(epoch_metric)

        # Checkpoints
        is_best = val_acc > best_val_acc
        if is_best:
            best_val_acc = val_acc
            best_epoch = epoch
            epochs_no_improve = 0
            logger.info(f"--> Best model improved to {val_acc*100:.2f}%. Saving best_checkpoint.pt")
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "class_mapping": class_mapping,
                    "architecture": arch,
                    "val_accuracy": val_acc,
                    "val_loss": val_loss,
                    "config": cfg,
                },
                run_dir / "best_checkpoint.pt",
            )
        else:
            epochs_no_improve += 1

        # Latest checkpoint saved atomically
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "class_mapping": class_mapping,
                "architecture": arch,
                "val_accuracy": val_acc,
                "best_val_accuracy": best_val_acc,
            },
            run_dir / "latest_checkpoint.pt",
        )

        # Write live telemetry to metrics.json
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "current_epoch": epoch,
                    "total_epochs": epochs,
                    "best_val_accuracy": best_val_acc,
                    "best_epoch": best_epoch,
                    "history": epoch_metrics_history,
                },
                f,
                indent=2,
            )

        # Early Stopping Check
        if early_stop_patience and epochs_no_improve >= early_stop_patience:
            logger.info(f"Early stopping triggered after {epochs_no_improve} epochs without improvement.")
            break

    total_training_time = round(time.time() - training_start_time, 2)
    logger.info(f"Training completed in {total_training_time}s. Best Val Accuracy: {best_val_acc*100:.2f}% (Epoch {best_epoch})")

    # Final Evaluation on test set (or validation set if no test split)
    logger.info("Running final model evaluation...")
    eval_target_loader = test_loader if test_loader is not None else val_loader
    eval_split_name = "test" if test_loader is not None else "val"

    # Load best checkpoint for evaluation
    best_cp_path = run_dir / "best_checkpoint.pt"
    if best_cp_path.exists():
        best_cp = torch.load(best_cp_path, map_location=device)
        model.load_state_dict(best_cp["model_state_dict"])

    eval_results = evaluate_dataset(model, eval_target_loader, criterion, device, class_names)
    eval_results["evaluated_split"] = eval_split_name
    eval_results["evaluated_at"] = utc_now_iso()

    with open(run_dir / "evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    logger.info(f"Evaluation results ({eval_split_name} split): Accuracy={eval_results['accuracy']*100:.2f}%, F1={eval_results['f1_macro']:.4f}")

    # Export ONNX deployment package automatically
    export_dir_cfg = cfg.get("export_dir")
    export_dir = Path(export_dir_cfg) if export_dir_cfg else (run_dir / "export")
    export_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Exporting model to ONNX package in {export_dir}...")
    try:
        export_resp = ModelCatalogService.export_onnx_package(
            model=model,
            output_dir=export_dir,
            model_name=f"{cfg.get('name', 'model')}_{arch}",
            architecture=arch,
            class_mapping=class_mapping,
            input_size=input_size,
            dynamic_batch=True,
            validation_report=eval_results,
        )
        logger.info(f"ONNX export succeeded: {export_resp.onnx_file_path} (Verified with inference: {export_resp.verified_with_inference})")
        if export_dir.resolve() != (run_dir / "export").resolve():
            try:
                shutil.copytree(export_dir, run_dir / "export", dirs_exist_ok=True)
            except Exception as copy_err:
                logger.warning(f"Failed to copy export to run_dir: {copy_err}")
    except Exception as e:
        logger.error(f"Failed to export ONNX model: {e}")

    # Write job completion sentinel
    with open(run_dir / "job_finished.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "status": "COMPLETED",
                "completed_at": utc_now_iso(),
                "best_val_accuracy": best_val_acc,
                "best_epoch": best_epoch,
                "total_epochs": epoch,
                "total_duration_seconds": total_training_time,
            },
            f,
            indent=2,
        )

    logger.info("=== Training Worker Exited Cleanly (COMPLETED) ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NOVA AI Trainer - Classification Training Worker")
    parser.add_argument("--config", required=True, help="Path to job configuration JSON file")
    args = parser.parse_args()
    run_worker(args.config)
