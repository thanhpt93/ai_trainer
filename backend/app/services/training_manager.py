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
)
from backend.app.schemas.model_artifact import (
    ExportModelRequest,
    ExportModelResponse,
)
from backend.app.services.classification_dataset_adapter import ClassificationDatasetAdapter
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
    subprocesses, monitors live metrics and logs, handles cooperative cancellation,
    and facilitates evaluation and artifact export.
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

        # Update dynamic statuses
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
            best_metric_name="val_accuracy",
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
            # Check if active job process is actually alive
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

        # Validate dataset and generate split manifest
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
            "random_seed": split_cfg.random_seed,
            "class_mapping": split_manifest["class_mapping"],
            "splits": split_manifest["splits"],
        }

        config_path = run_dir / "job_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(worker_cfg, f, indent=2)

        # Launch worker subprocess
        repo_root = Path(__file__).resolve().parents[3]
        cmd = [
            sys.executable,
            "-m",
            "backend.app.workers.classification_worker",
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
            return json.loads(job.evaluation_json)

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
    def run_inference(
        cls,
        db: Session,
        job_id: str,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> PredictResponse:
        """
        Runs model inference on an input image using the trained checkpoint weights.
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

        # Load checkpoint and model
        device = torch.device("cuda" if torch.cuda.is_available() and job.device == "cuda" else "cpu")
        cp_data = torch.load(best_cp, map_location=device)
        class_mapping = cp_data.get("class_mapping", [])
        if not class_mapping:
            raise HTTPException(status_code=400, detail="Model checkpoint does not contain class mapping")

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
                    task_type="Image Classification",
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
                model_name=job.name or "ClassificationModel",
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

        # Load checkpoint and export
        cp_data = torch.load(best_cp, map_location="cpu")
        class_mapping = cp_data.get("class_mapping", [])
        model, _ = ModelCatalogService.load_checkpoint(
            best_cp,
            architecture=job.model_architecture or "resnet18",
            num_classes=len(class_mapping),
        )

        eval_report = cls.get_job_evaluation(db, job.id)
        resp = ModelCatalogService.export_onnx_package(
            model=model,
            output_dir=export_dir,
            model_name=job.name or f"model_{job.id[:8]}",
            architecture=job.model_architecture or "resnet18",
            class_mapping=class_mapping,
            input_size=req.input_size,
            dynamic_batch=req.dynamic_batch,
            validation_report=eval_report,
        )

        art = ModelArtifact(
            name=job.name or f"model_{job.id[:8]}",
            task_type="Image Classification",
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
                job.best_metric_value = m_data.get("best_val_accuracy", job.best_metric_value)
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
                    job.best_metric_value = fin_data.get("best_val_accuracy", job.best_metric_value)
                    db.commit()
            except Exception:
                pass
        elif job.status == TrainingJobStatus.RUNNING.value:
            # Check if PID died unexpectedly
            if job.pid and not cls._is_pid_alive(job.pid):
                # Process died without writing job_finished.json -> mark as failed
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
