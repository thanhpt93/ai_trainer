import os
import sys
import json
import time
import subprocess
import base64
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import torch
import torchvision.transforms as transforms
import torchvision.transforms.functional as TF
from PIL import Image
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.domain.models import (
    Project,
    Dataset,
    TrainingJob,
    ModelArtifact,
)
from backend.app.schemas.training_job import (
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingJobStatus,
    SplitConfig,
    TrainingHyperparameters,
    PredictRequest,
    PredictResponse,
    ClassProbability,
    DetectedObject,
    DetectionEvaluationReport,
)
from backend.app.schemas.model_artifact import (
    ExportModelRequest,
    ExportModelResponse,
)
from backend.app.services.classification_dataset_adapter import ClassificationDatasetAdapter
from backend.app.adapters.detection_dataset_adapter import DetectionDatasetAdapter
from backend.app.adapters.detection_evaluator import DetectionEvaluator
from backend.app.services.model_catalog_service import (
    ModelCatalogService,
    IMAGENET_MEAN,
    IMAGENET_STD,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TrainingManager:
    """
    Orchestrates training jobs, validates configurations, manages isolated worker
    subprocesses for classification and object detection, monitors live metrics and logs,
    handles cooperative cancellation and resume, and facilitates evaluation and artifact export.
    """

    @classmethod
    def list_jobs(
        cls,
        db: Session,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TrainingJobResponse]:
        query = db.query(TrainingJob)
        if project_id:
            query = query.filter(TrainingJob.project_id == project_id)
        jobs = query.order_by(TrainingJob.created_at.desc()).limit(limit).all()

        results = []
        for j in jobs:
            cls._sync_job_runtime_state(db, j)
            results.append(TrainingJobResponse.model_validate(j))
        return results

    @classmethod
    def get_job(cls, db: Session, job_id: str) -> TrainingJobResponse:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job '{job_id}' not found.",
            )
        cls._sync_job_runtime_state(db, job)
        return TrainingJobResponse.model_validate(job)

    @classmethod
    def create_job(cls, db: Session, req: TrainingJobCreate) -> TrainingJobResponse:
        project = db.query(Project).filter(Project.id == req.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        dataset = db.query(Dataset).filter(Dataset.id == req.dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        arch = req.hyperparameters.model_architecture
        run_name = req.name or f"{arch}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        is_detection = "Detection" in project.task_type or ModelCatalogService.is_detection_model(arch)
        best_metric_name = "val_map_50" if is_detection else "val_accuracy"

        job = TrainingJob(
            name=run_name,
            project_id=req.project_id,
            dataset_id=req.dataset_id,
            task_type=project.task_type,
            model_architecture=arch,
            device=req.hyperparameters.device,
            status=TrainingJobStatus.QUEUED.value,
            total_epochs=req.hyperparameters.epochs,
            current_epoch=0,
            best_metric_name=best_metric_name,
            configuration_json=json.dumps(
                {
                    "hyperparameters": req.hyperparameters.model_dump(),
                    "split_config": req.split_config.model_dump(),
                }
            ),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return TrainingJobResponse.model_validate(job)

    @classmethod
    def start_job(cls, db: Session, job_id: str) -> TrainingJobResponse:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        if job.status in [TrainingJobStatus.RUNNING.value, TrainingJobStatus.PREPARING.value]:
            return TrainingJobResponse.model_validate(job)

        # Enforce maximum 1 active training job to prevent GPU/system thrashing
        active_job = (
            db.query(TrainingJob)
            .filter(
                TrainingJob.status.in_([TrainingJobStatus.RUNNING.value, TrainingJobStatus.PREPARING.value]),
                TrainingJob.id != job_id,
            )
            .first()
        )
        if active_job:
            if cls._is_pid_alive(active_job.pid):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Another training job '{active_job.name}' ({active_job.id}) is currently running. Please wait for it to finish or cancel it first.",
                )
            else:
                active_job.status = TrainingJobStatus.FAILED.value
                active_job.error_message = "Process exited unexpectedly."
                db.commit()

        job.status = TrainingJobStatus.PREPARING.value
        db.commit()

        # Parse saved config
        cfg_dict = json.loads(job.configuration_json or "{}")
        hparams = TrainingHyperparameters(**cfg_dict.get("hyperparameters", {}))
        split_cfg = SplitConfig(**cfg_dict.get("split_config", {}))

        is_detection = "Detection" in job.task_type or ModelCatalogService.is_detection_model(hparams.model_architecture)

        # Validate dataset and generate split manifest
        if is_detection:
            val_res, split_manifest = DetectionDatasetAdapter.validate_and_prepare_dataset(
                db=db,
                project_id=job.project_id,
                dataset_id=job.dataset_id,
                split_config=split_cfg,
            )
        else:
            val_res, split_manifest = ClassificationDatasetAdapter.validate_and_prepare_dataset(
                db=db,
                project_id=job.project_id,
                dataset_id=job.dataset_id,
                split_config=split_cfg,
            )

        if not val_res.is_valid or not split_manifest:
            job.status = TrainingJobStatus.FAILED.value
            job.error_message = f"Dataset validation failed: {'; '.join(val_res.errors)}"
            db.commit()
            return TrainingJobResponse.model_validate(job)

        # Create isolated run directory
        run_dir = settings.TRAINING_RUNS_DIR / job.id
        run_dir.mkdir(parents=True, exist_ok=True)
        job.checkpoint_dir = str(run_dir)
        job.log_file_path = str(run_dir / "train.log")

        # Prepare worker config payload
        worker_cfg = {
            "job_id": job.id,
            "name": job.name,
            "run_dir": str(run_dir),
            "model_architecture": hparams.model_architecture,
            "pretrained": hparams.pretrained,
            "device": hparams.device,
            "input_size": hparams.input_size,
            "batch_size": hparams.batch_size,
            "epochs": hparams.epochs,
            "learning_rate": hparams.learning_rate,
            "optimizer": hparams.optimizer,
            "weight_decay": hparams.weight_decay,
            "momentum": hparams.momentum,
            "scheduler": hparams.scheduler,
            "early_stopping": hparams.early_stopping,
            "patience": hparams.patience,
            "num_workers": hparams.num_workers,
            "horizontal_flip": hparams.horizontal_flip,
            "rotation_degrees": hparams.rotation_degrees,
            "color_jitter": hparams.color_jitter,
            "confidence_threshold": hparams.confidence_threshold,
            "iou_threshold": hparams.iou_threshold,
            "max_detections": hparams.max_detections,
            "grad_clip": hparams.grad_clip,
            "random_seed": split_cfg.random_seed,
            "class_mapping": split_manifest["class_mapping"],
            "splits": split_manifest["splits"],
            "validation_report": val_res.model_dump(),
        }

        config_path = run_dir / "job_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(worker_cfg, f, indent=2)

        # Select worker module based on task type
        worker_module = (
            "backend.app.workers.detection_worker"
            if is_detection
            else "backend.app.workers.classification_worker"
        )

        repo_root = Path(__file__).resolve().parents[3]
        cmd = [
            sys.executable,
            "-m",
            worker_module,
            "--config",
            str(config_path),
        ]

        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(repo_root),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            job.pid = proc.pid
            job.status = TrainingJobStatus.RUNNING.value
            job.started_at = utc_now()
            db.commit()
            db.refresh(job)
        except Exception as e:
            job.status = TrainingJobStatus.FAILED.value
            job.error_message = f"Failed to spawn worker subprocess: {str(e)}"
            db.commit()

        return TrainingJobResponse.model_validate(job)

    @classmethod
    def resume_job(cls, db: Session, job_id: str) -> TrainingJobResponse:
        """
        Resumes a cancelled, stopped, or failed training job from its latest saved checkpoint.
        """
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        if job.status in [TrainingJobStatus.RUNNING.value, TrainingJobStatus.PREPARING.value]:
            return TrainingJobResponse.model_validate(job)

        if not job.checkpoint_dir:
            raise HTTPException(status_code=400, detail="Job has no checkpoint directory to resume from.")

        run_dir = Path(job.checkpoint_dir)
        latest_cp = run_dir / "latest_checkpoint.pt"
        if not latest_cp.exists():
            latest_cp = run_dir / "best_checkpoint.pt"
        if not latest_cp.exists():
            raise HTTPException(status_code=400, detail="No checkpoint file (latest_checkpoint.pt) found to resume.")

        # Remove cancel flag if exists
        cancel_flag = run_dir / "cancel.requested"
        if cancel_flag.exists():
            try:
                cancel_flag.unlink()
            except Exception:
                pass

        # Remove finished marker
        fin_file = run_dir / "job_finished.json"
        if fin_file.exists():
            try:
                fin_file.unlink()
            except Exception:
                pass

        # Load existing config and add resume_checkpoint
        config_path = run_dir / "job_config.json"
        if not config_path.exists():
            raise HTTPException(status_code=400, detail="job_config.json not found in checkpoint directory.")

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        cfg["resume_checkpoint"] = str(latest_cp)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

        is_detection = "Detection" in job.task_type or ModelCatalogService.is_detection_model(job.model_architecture or "")
        worker_module = (
            "backend.app.workers.detection_worker"
            if is_detection
            else "backend.app.workers.classification_worker"
        )

        repo_root = Path(__file__).resolve().parents[3]
        cmd = [
            sys.executable,
            "-m",
            worker_module,
            "--config",
            str(config_path),
        ]

        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(repo_root),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            job.pid = proc.pid
            job.status = TrainingJobStatus.RUNNING.value
            job.is_cancelled = False
            job.error_message = None
            db.commit()
            db.refresh(job)
        except Exception as e:
            job.status = TrainingJobStatus.FAILED.value
            job.error_message = f"Failed to resume worker subprocess: {str(e)}"
            db.commit()

        return TrainingJobResponse.model_validate(job)

    @classmethod
    def cancel_job(cls, db: Session, job_id: str) -> TrainingJobResponse:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        if job.status not in [TrainingJobStatus.RUNNING.value, TrainingJobStatus.PREPARING.value]:
            return TrainingJobResponse.model_validate(job)

        job.status = TrainingJobStatus.CANCEL_REQUESTED.value
        job.is_cancelled = True
        db.commit()

        # Signal cooperative cancellation via flag file
        if job.checkpoint_dir:
            run_dir = Path(job.checkpoint_dir)
            cancel_flag = run_dir / "cancel.requested"
            try:
                cancel_flag.touch(exist_ok=True)
            except Exception:
                pass

        # Give 2.5s for graceful checkpoint write, then terminate if still running
        time.sleep(1.0)
        if job.pid and cls._is_pid_alive(job.pid):
            time.sleep(1.5)
            if cls._is_pid_alive(job.pid):
                cls._kill_pid(job.pid)

        job.status = TrainingJobStatus.CANCELLED.value
        job.completed_at = utc_now()
        db.commit()
        db.refresh(job)
        return TrainingJobResponse.model_validate(job)

    @classmethod
    def get_job_logs(cls, db: Session, job_id: str, tail_lines: int = 150) -> Dict[str, Any]:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        log_path = Path(job.log_file_path) if job.log_file_path else None
        if not log_path or not log_path.exists():
            return {"job_id": job_id, "logs": [], "total_lines": 0}

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            total = len(lines)
            selected = [l.rstrip("\r\n") for l in lines[-tail_lines:]]
            return {"job_id": job_id, "logs": selected, "total_lines": total}
        except Exception as e:
            return {"job_id": job_id, "logs": [f"Error reading log: {str(e)}"], "total_lines": 1}

    @classmethod
    def get_job_evaluation(cls, db: Session, job_id: str) -> Optional[Dict[str, Any]]:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        if job.evaluation_json:
            try:
                return json.loads(job.evaluation_json)
            except Exception:
                pass

        # Check file
        if job.checkpoint_dir:
            eval_file = Path(job.checkpoint_dir) / "evaluation_results.json"
            if eval_file.exists():
                try:
                    with open(eval_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    job.evaluation_json = json.dumps(data)
                    db.commit()
                    return data
                except Exception:
                    pass
        return None

    @classmethod
    def evaluate_job(
        cls,
        db: Session,
        job_id: str,
        split: str = "val",
        conf_thresh: float = 0.5,
        iou_thresh: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Runs on-demand evaluation of a trained model against validation or test data.
        """
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        if not job.checkpoint_dir:
            raise HTTPException(status_code=400, detail="Job has no checkpoint directory")

        run_dir = Path(job.checkpoint_dir)
        best_cp = run_dir / "best_checkpoint.pt"
        if not best_cp.exists():
            best_cp = run_dir / "latest_checkpoint.pt"
        if not best_cp.exists():
            raise HTTPException(status_code=400, detail="No checkpoint file found for evaluation.")

        cfg_file = run_dir / "job_config.json"
        if not cfg_file.exists():
            raise HTTPException(status_code=400, detail="job_config.json not found")

        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        is_detection = "Detection" in job.task_type or ModelCatalogService.is_detection_model(job.model_architecture or "")
        device = torch.device("cuda" if torch.cuda.is_available() and job.device == "cuda" else "cpu")

        if is_detection:
            class_mapping = cfg.get("class_mapping", [])
            splits = cfg.get("splits", {})
            eval_samples = splits.get(split) or splits.get("val") or splits.get("train", [])

            if not eval_samples:
                raise HTTPException(status_code=400, detail=f"No samples found for split '{split}'")

            input_size = cfg.get("input_size", 800)
            from backend.app.adapters.detection_dataset_adapter import DetectionTorchDataset, detection_collate_fn
            from torch.utils.data import DataLoader

            dataset = DetectionTorchDataset(
                samples=eval_samples,
                input_size=input_size,
                is_train=False,
                horizontal_flip=False,
            )
            loader = DataLoader(dataset, batch_size=2, shuffle=False, collate_fn=detection_collate_fn)

            model, _ = ModelCatalogService.load_checkpoint(
                best_cp,
                architecture=job.model_architecture or "fasterrcnn_resnet50_fpn",
                num_classes=len(class_mapping),
                device=device,
            )
            model.eval()

            predictions = []
            with torch.no_grad():
                for images, _ in loader:
                    images = [img.to(device) for img in images]
                    outputs = model(images)
                    for out in outputs:
                        predictions.append({
                            "boxes": out["boxes"].cpu().numpy().tolist(),
                            "labels": out["labels"].cpu().numpy().tolist(),
                            "scores": out["scores"].cpu().numpy().tolist(),
                        })

            report = DetectionEvaluator.evaluate(
                samples=eval_samples,
                predictions=predictions,
                class_mapping=class_mapping,
                confidence_threshold=conf_thresh,
                iou_threshold=iou_thresh,
                evaluated_split=split,
            )
            report_dict = report.model_dump()

            eval_file = run_dir / "evaluation_results.json"
            with open(eval_file, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2)

            job.evaluation_json = json.dumps(report_dict)
            db.commit()
            return report_dict
        else:
            # Classification evaluation fallback
            report = cls.get_job_evaluation(db, job_id)
            if report:
                return report
            raise HTTPException(status_code=400, detail="Evaluation results not available")

    @classmethod
    def run_inference(
        cls,
        db: Session,
        job_id: str,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        confidence_threshold: float = 0.3,
        iou_threshold: float = 0.5,
    ) -> PredictResponse:
        """
        Runs model inference on an input image using the trained checkpoint weights.
        Supports both classification and object detection tasks.
        """
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        if not job.checkpoint_dir:
            raise HTTPException(status_code=400, detail="Job has no checkpoint directory")

        run_dir = Path(job.checkpoint_dir)
        best_cp = run_dir / "best_checkpoint.pt"
        if not best_cp.exists():
            best_cp = run_dir / "latest_checkpoint.pt"
        if not best_cp.exists():
            raise HTTPException(status_code=400, detail="No valid checkpoint model file found for inference")

        # Load input image
        if image_base64:
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(image_base64)
                img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        elif image_path:
            p = Path(image_path)
            if not p.is_file():
                raise HTTPException(status_code=400, detail=f"Image file not found: {image_path}")
            try:
                img = Image.open(p).convert("RGB")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Cannot open image file: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Either image_path or image_base64 must be provided")

        orig_w, orig_h = img.size
        device = torch.device("cuda" if torch.cuda.is_available() and job.device == "cuda" else "cpu")
        cp_data = torch.load(best_cp, map_location=device)
        class_mapping = cp_data.get("class_mapping", [])
        if not class_mapping:
            raise HTTPException(status_code=400, detail="Model checkpoint does not contain class mapping")

        is_detection = "Detection" in job.task_type or ModelCatalogService.is_detection_model(job.model_architecture or "")

        # ------------------------------------
        # Object Detection Inference Pipeline
        # ------------------------------------
        if is_detection:
            model, _ = ModelCatalogService.load_checkpoint(
                best_cp,
                architecture=job.model_architecture or "fasterrcnn_resnet50_fpn",
                num_classes=len(class_mapping),
                device=device,
            )
            model.eval()

            input_size = 800
            if job.configuration_json:
                try:
                    cfg = json.loads(job.configuration_json)
                    input_size = cfg.get("hyperparameters", {}).get("input_size", 800)
                except Exception:
                    pass

            # Resize and convert to tensor
            img_resized = img.resize((input_size, input_size), Image.Resampling.BILINEAR)
            tensor = TF.to_tensor(img_resized)
            tensor = TF.normalize(tensor, mean=IMAGENET_MEAN, std=IMAGENET_STD)
            tensor = tensor.to(device)

            start_time = time.time()
            with torch.no_grad():
                outputs = model([tensor])
            inference_time_ms = round((time.time() - start_time) * 1000, 2)

            out = outputs[0]
            boxes = out["boxes"].cpu().numpy()
            labels = out["labels"].cpu().numpy()
            scores = out["scores"].cpu().numpy()

            index_to_name = {c["index"]: c["name"] for c in class_mapping}
            index_to_label_id = {c["index"]: c.get("label_id", "") for c in class_mapping}

            scale_x = float(orig_w) / float(input_size)
            scale_y = float(orig_h) / float(input_size)

            detected_objects: List[DetectedObject] = []
            for b, l, s in zip(boxes, labels, scores):
                conf = float(s)
                if conf < confidence_threshold:
                    continue
                # Background class (index 0) is ignored
                if l == 0:
                    continue

                orig_x1 = max(0.0, float(b[0] * scale_x))
                orig_y1 = max(0.0, float(b[1] * scale_y))
                orig_x2 = min(float(orig_w), float(b[2] * scale_x))
                orig_y2 = min(float(orig_h), float(b[3] * scale_y))

                norm_box = [
                    round(orig_x1 / max(1, orig_w), 4),
                    round(orig_y1 / max(1, orig_h), 4),
                    round(orig_x2 / max(1, orig_w), 4),
                    round(orig_y2 / max(1, orig_h), 4),
                ]

                detected_objects.append(
                    DetectedObject(
                        label_id=index_to_label_id.get(int(l), ""),
                        class_name=index_to_name.get(int(l), f"Class_{l}"),
                        class_index=int(l),
                        confidence=round(conf, 4),
                        box=[round(orig_x1, 2), round(orig_y1, 2), round(orig_x2, 2), round(orig_y2, 2)],
                        box_normalized=norm_box,
                    )
                )

            top_pred_class = detected_objects[0].class_name if detected_objects else "No detections"
            top_confidence = detected_objects[0].confidence if detected_objects else 0.0

            return PredictResponse(
                predicted_class=top_pred_class,
                confidence=top_confidence,
                top_probabilities=[],
                inference_time_ms=inference_time_ms,
                device=str(device),
                model_architecture=job.model_architecture or "fasterrcnn_resnet50_fpn",
                task_type="Object Detection",
                detected_objects=detected_objects,
                image_width=orig_w,
                image_height=orig_h,
            )

        # ---------------------------------------
        # Classification Inference Pipeline (P3)
        # ---------------------------------------
        model, _ = ModelCatalogService.load_checkpoint(
            best_cp,
            architecture=job.model_architecture or "resnet18",
            num_classes=len(class_mapping),
            device=device,
        )
        model.eval()

        input_size = 224
        if job.configuration_json:
            try:
                cfg = json.loads(job.configuration_json)
                input_size = cfg.get("hyperparameters", {}).get("input_size", 224)
            except Exception:
                pass

        transform = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

        start_time = time.time()
        tensor = transform(img).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(tensor)
            probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()

        inference_time_ms = round((time.time() - start_time) * 1000, 2)

        top_probs = []
        for item in class_mapping:
            idx = item.get("index", 0)
            cname = item.get("name", f"Class {idx}")
            prob = float(probs[idx]) if idx < len(probs) else 0.0
            top_probs.append(ClassProbability(class_name=cname, probability=round(prob, 4)))

        top_probs.sort(key=lambda x: x.probability, reverse=True)
        pred_class = top_probs[0].class_name if top_probs else "Unknown"
        confidence = top_probs[0].probability if top_probs else 0.0

        return PredictResponse(
            predicted_class=pred_class,
            confidence=confidence,
            top_probabilities=top_probs,
            inference_time_ms=inference_time_ms,
            device=str(device),
            model_architecture=job.model_architecture or "resnet18",
            task_type="Image Classification",
            image_width=orig_w,
            image_height=orig_h,
        )

    @classmethod
    def export_model_artifact(
        cls,
        db: Session,
        job_id: str,
        req: ExportModelRequest,
    ) -> ExportModelResponse:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        if job.status != TrainingJobStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only completed training jobs can be exported to deployment packages.",
            )

        run_dir = Path(job.checkpoint_dir)
        export_dir = run_dir / "export"
        onnx_file = export_dir / "model.onnx"
        manifest_file = export_dir / "export_manifest.json"

        is_detection = "Detection" in job.task_type or ModelCatalogService.is_detection_model(job.model_architecture or "")
        task_str = "Object Detection" if is_detection else "Image Classification"

        # If already exported in worker, return manifest data
        if onnx_file.exists() and manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                m_data = json.load(f)
            onnx_info = m_data.get("exported_files", {}).get("model.onnx", {})

            # Register in ModelArtifact table if not already registered
            art = db.query(ModelArtifact).filter(ModelArtifact.training_job_id == job.id).first()
            if not art:
                art = ModelArtifact(
                    name=job.name or f"model_{job.id[:8]}",
                    task_type=task_str,
                    version="1.0.0",
                    artifact_path=str(onnx_file),
                    framework="PyTorch",
                    export_format="ONNX",
                    metadata_path=str(export_dir / "model_metadata.json"),
                    project_id=job.project_id,
                    dataset_id=job.dataset_id,
                    training_job_id=job.id,
                    model_architecture=job.model_architecture,
                    metrics_summary_json=job.metrics_json,
                    checksum_sha256=onnx_info.get("sha256", ""),
                    file_size_bytes=onnx_info.get("size_bytes", 0),
                    is_exported=True,
                )
                db.add(art)
                db.commit()

            return ExportModelResponse(
                success=True,
                artifact_id=job.id,
                model_name=job.name or "DetectionModel",
                export_dir=str(export_dir),
                onnx_file_path=str(onnx_file),
                manifest_path=str(manifest_file),
                metadata_path=str(export_dir / "model_metadata.json"),
                checksum_sha256=onnx_info.get("sha256", ""),
                file_size_bytes=onnx_info.get("size_bytes", 0),
                verified_with_inference=m_data.get("verified_with_inference", True),
            )

        # Fallback: re-export using best checkpoint
        best_cp = run_dir / "best_checkpoint.pt"
        if not best_cp.exists():
            best_cp = run_dir / "latest_checkpoint.pt"
        if not best_cp.exists():
            raise HTTPException(status_code=400, detail="No valid checkpoint found to export.")

        cp_data = torch.load(best_cp, map_location="cpu")
        class_mapping = cp_data.get("class_mapping", [])
        model, _ = ModelCatalogService.load_checkpoint(
            best_cp,
            architecture=job.model_architecture or ("fasterrcnn_resnet50_fpn" if is_detection else "resnet18"),
            num_classes=len(class_mapping),
        )

        eval_report = cls.get_job_evaluation(db, job.id)
        resp = ModelCatalogService.export_onnx_package(
            model=model,
            output_dir=export_dir,
            model_name=job.name or f"model_{job.id[:8]}",
            architecture=job.model_architecture or ("fasterrcnn_resnet50_fpn" if is_detection else "resnet18"),
            class_mapping=class_mapping,
            input_size=req.input_size,
            dynamic_batch=req.dynamic_batch,
            validation_report=eval_report,
        )

        art = ModelArtifact(
            name=job.name or f"model_{job.id[:8]}",
            task_type=task_str,
            version="1.0.0",
            artifact_path=resp.onnx_file_path,
            framework="PyTorch",
            export_format="ONNX",
            metadata_path=resp.metadata_path,
            project_id=job.project_id,
            dataset_id=job.dataset_id,
            training_job_id=job.id,
            model_architecture=job.model_architecture,
            metrics_summary_json=job.metrics_json,
            checksum_sha256=resp.checksum_sha256,
            file_size_bytes=resp.file_size_bytes,
            is_exported=True,
        )
        db.add(art)
        db.commit()

        return resp

    @classmethod
    def _sync_job_runtime_state(cls, db: Session, job: TrainingJob) -> None:
        """Polls worker filesystem state and updates database status and metrics."""
        if not job.checkpoint_dir:
            return

        run_dir = Path(job.checkpoint_dir)
        if not run_dir.exists():
            return

        # 1. Check live metrics
        metrics_file = run_dir / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                job.current_epoch = m_data.get("current_epoch", job.current_epoch)
                job.best_metric_value = m_data.get("best_val_metric", m_data.get("best_val_accuracy", job.best_metric_value))
                job.metrics_json = json.dumps(m_data.get("history", []))
            except Exception:
                pass

        # 2. Check process completion / finish sentinel
        fin_file = run_dir / "job_finished.json"
        if fin_file.exists():
            try:
                with open(fin_file, "r", encoding="utf-8") as f:
                    fin_data = json.load(f)
                final_status = fin_data.get("status", "COMPLETED")
                if job.status in [TrainingJobStatus.RUNNING.value, TrainingJobStatus.CANCEL_REQUESTED.value, TrainingJobStatus.PREPARING.value]:
                    job.status = final_status
                    job.completed_at = utc_now()
                    job.best_metric_value = fin_data.get("best_val_metric", fin_data.get("best_val_accuracy", job.best_metric_value))
                    db.commit()
            except Exception:
                pass
        elif job.status == TrainingJobStatus.RUNNING.value:
            # Check if PID died unexpectedly
            if job.pid and not cls._is_pid_alive(job.pid):
                job.status = TrainingJobStatus.FAILED.value
                job.completed_at = utc_now()
                job.error_message = "Training worker process exited unexpectedly or was killed."
                db.commit()

        db.commit()

    @staticmethod
    def _is_pid_alive(pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            import psutil
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except Exception:
            return False

    @staticmethod
    def _kill_pid(pid: int) -> None:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/pid", str(pid), "/f", "/t"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.kill(pid, 9)
        except Exception:
            pass
