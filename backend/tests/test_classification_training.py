import os
import sys
import time
import shutil
import tempfile
import base64
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.domain.models import (
    Project,
    Dataset,
    ImageRecord,
    ProjectLabel,
    ImageAnnotation,
    ClassificationAnnotation,
    TrainingJob,
    ModelArtifact,
)
from backend.app.services.model_catalog_service import ModelCatalogService

client = TestClient(app)


def test_hardware_endpoint():
    """Verify hardware and device telemetry endpoint."""
    response = client.get("/api/v1/system/hardware")
    assert response.status_code == 200
    data = response.json()
    assert "pytorch_version" in data
    assert "cpu_count_logical" in data
    assert "system_memory_total_gb" in data
    assert "cuda_available" in data
    assert "available_devices" in data
    assert "cpu" in data["available_devices"]


def test_model_catalog_endpoint():
    """Verify model catalog returns supported vision architectures."""
    response = client.get("/api/v1/training/models")
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 2
    model_ids = [m["id"] for m in models]
    assert "resnet18" in model_ids
    assert "mobilenet_v3_small" in model_ids


def test_model_builder():
    """Verify ModelCatalogService correctly adapts classifier head for custom class count."""
    m_resnet = ModelCatalogService.build_model("resnet18", num_classes=5, pretrained=False)
    assert m_resnet.fc.out_features == 5

    m_mobile = ModelCatalogService.build_model("mobilenet_v3_small", num_classes=3, pretrained=False)
    assert m_mobile.classifier[-1].out_features == 3


@pytest.fixture(scope="module")
def synthetic_classification_env():
    """Sets up a complete synthetic classification dataset with 2 classes."""
    temp_dir = tempfile.mkdtemp(prefix="nova_test_cls_")
    db = SessionLocal()

    try:
        # Create Project
        proj = Project(
            name=f"Test_Cls_Project_{int(time.time())}",
            task_type="Image Classification",
            root_path=temp_dir,
            is_multi_label=False,
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)

        # Create Labels
        lbl_cat = ProjectLabel(project_id=proj.id, name="Cat", color="#ef4444")
        lbl_dog = ProjectLabel(project_id=proj.id, name="Dog", color="#3b82f6")
        db.add_all([lbl_cat, lbl_dog])
        db.commit()
        db.refresh(lbl_cat)
        db.refresh(lbl_dog)

        # Create Dataset
        ds = Dataset(
            project_id=proj.id,
            name="Test_Cls_Dataset",
            root_path=temp_dir,
            image_count=8,
            valid_image_count=8,
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)

        # Create 8 synthetic images (4 Cat, 4 Dog)
        images = []
        for i in range(8):
            label_assigned = lbl_cat if i < 4 else lbl_dog
            img_filename = f"img_{i}_{label_assigned.name.lower()}.jpg"
            img_path = Path(temp_dir) / img_filename

            # Create distinct image colors
            color = (255, 100, 100) if i < 4 else (100, 100, 255)
            pil_img = Image.new("RGB", (64, 64), color=color)
            pil_img.save(img_path)

            rec = ImageRecord(
                dataset_id=ds.id,
                relative_path=img_filename,
                absolute_path=str(img_path),
                file_size_bytes=img_path.stat().st_size,
                width=64,
                height=64,
                is_valid=True,
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)

            ann = ImageAnnotation(
                dataset_id=ds.id,
                image_id=rec.id,
                task_type="Image Classification",
                status="ANNOTATED",
            )
            db.add(ann)
            db.commit()
            db.refresh(ann)

            cls_ann = ClassificationAnnotation(
                image_annotation_id=ann.id,
                label_id=label_assigned.id,
            )
            db.add(cls_ann)
            images.append(rec)

        db.commit()

        yield {
            "project_id": proj.id,
            "dataset_id": ds.id,
            "cat_label_id": lbl_cat.id,
            "dog_label_id": lbl_dog.id,
            "temp_dir": temp_dir,
        }
    finally:
        try:
            db_clean = SessionLocal()
            db_clean.query(TrainingJob).filter(TrainingJob.project_id == proj.id).delete()
            db_clean.query(ModelArtifact).filter(ModelArtifact.project_id == proj.id).delete()
            db_clean.query(ClassificationAnnotation).filter(
                ClassificationAnnotation.image_annotation_id.in_(
                    db_clean.query(ImageAnnotation.id).filter(ImageAnnotation.dataset_id == ds.id)
                )
            ).delete(synchronize_session=False)
            db_clean.query(ImageAnnotation).filter(ImageAnnotation.dataset_id == ds.id).delete()
            db_clean.query(ImageRecord).filter(ImageRecord.dataset_id == ds.id).delete()
            db_clean.query(Dataset).filter(Dataset.id == ds.id).delete()
            db_clean.query(ProjectLabel).filter(ProjectLabel.project_id == proj.id).delete()
            db_clean.query(Project).filter(Project.id == proj.id).delete()
            db_clean.commit()
            db_clean.close()
        except Exception:
            pass
        db.close()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_dataset_validation(synthetic_classification_env):
    """Test dataset validation and split manifest generation."""
    env = synthetic_classification_env
    payload = {
        "project_id": env["project_id"],
        "dataset_id": env["dataset_id"],
        "split_config": {
            "train_ratio": 0.75,
            "val_ratio": 0.25,
            "test_ratio": 0.0,
            "random_seed": 42,
            "stratified": True,
        },
    }
    resp = client.post("/api/v1/training/datasets/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["valid_annotated_images"] == 8
    assert len(data["classes"]) == 2
    assert data["train_count"] > 0
    assert data["val_count"] > 0


def test_end_to_end_training_and_export(synthetic_classification_env):
    """
    Real End-to-End Test:
    Create Job -> Start Worker Subprocess -> Monitor completion ->
    Verify Checkpoints & Metrics -> Verify Evaluation -> Interactive Inference -> Export to ONNX.
    """
    env = synthetic_classification_env

    # 1. Create Job
    job_payload = {
        "project_id": env["project_id"],
        "dataset_id": env["dataset_id"],
        "name": "E2E_ResNet18_TestRun",
        "hyperparameters": {
            "model_architecture": "resnet18",
            "pretrained": False,
            "device": "cpu",
            "input_size": 64,
            "batch_size": 2,
            "epochs": 2,
            "learning_rate": 0.01,
            "optimizer": "AdamW",
            "num_workers": 0,
            "horizontal_flip": False,
            "rotation_degrees": 0,
        },
        "split_config": {
            "train_ratio": 0.75,
            "val_ratio": 0.25,
            "test_ratio": 0.0,
            "random_seed": 42,
            "stratified": True,
        },
    }
    create_resp = client.post("/api/v1/training/jobs", json=job_payload)
    assert create_resp.status_code == 201
    job_data = create_resp.json()
    job_id = job_data["id"]
    assert job_data["status"] == "QUEUED"

    # 2. Start Job
    start_resp = client.post(f"/api/v1/training/jobs/{job_id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] in ["RUNNING", "PREPARING"]

    # 3. Poll until COMPLETED or timeout (30 seconds max)
    terminal_status = None
    for _ in range(60):
        time.sleep(0.5)
        status_resp = client.get(f"/api/v1/training/jobs/{job_id}")
        assert status_resp.status_code == 200
        cur_status = status_resp.json()["status"]
        if cur_status in ["COMPLETED", "FAILED", "CANCELLED"]:
            terminal_status = cur_status
            break

    # If it failed, let's see why from logs
    if terminal_status != "COMPLETED":
        log_resp = client.get(f"/api/v1/training/jobs/{job_id}/logs")
        print("\n--- Worker Logs on Failure ---")
        for line in log_resp.json().get("logs", []):
            print(line)

    assert terminal_status == "COMPLETED"

    # 4. Check Checkpoint and Metrics
    metrics_resp = client.get(f"/api/v1/training/jobs/{job_id}/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert len(metrics) == 2
    assert "train_loss" in metrics[0]
    assert "val_accuracy" in metrics[0]

    # 5. Check Evaluations
    eval_resp = client.get(f"/api/v1/training/jobs/{job_id}/evaluations")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert "confusion_matrix" in eval_data
    assert len(eval_data["per_class_metrics"]) == 2

    # 6. Test Interactive Inference / Predict with image file path & base64
    sample_img_path = Path(env["temp_dir"]) / "img_0_cat.jpg"
    pred_resp = client.post(
        f"/api/v1/training/jobs/{job_id}/predict",
        json={"image_path": str(sample_img_path)},
    )
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert "predicted_class" in pred_data
    assert "confidence" in pred_data
    assert len(pred_data["top_probabilities"]) == 2
    assert pred_data["inference_time_ms"] > 0
    assert pred_data["model_architecture"] == "resnet18"

    # Also test base64 prediction
    with open(sample_img_path, "rb") as f:
        b64_str = base64.b64encode(f.read()).decode("utf-8")
    pred_b64_resp = client.post(
        f"/api/v1/training/jobs/{job_id}/predict",
        json={"image_base64": f"data:image/jpeg;base64,{b64_str}"},
    )
    assert pred_b64_resp.status_code == 200
    assert pred_b64_resp.json()["predicted_class"] in ["Cat", "Dog"]

    # 7. Test Model Export to ONNX
    export_payload = {
        "format": "ONNX",
        "input_size": 64,
        "dynamic_batch": True,
    }
    export_resp = client.post(f"/api/v1/training/jobs/{job_id}/export", json=export_payload)
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["success"] is True
    assert Path(export_data["onnx_file_path"]).exists()
    assert Path(export_data["manifest_path"]).exists()
    assert export_data["verified_with_inference"] is True

    # 8. Check Model Registry
    models_resp = client.get(f"/api/v1/models?project_id={env['project_id']}")
    assert models_resp.status_code == 200
    registered = models_resp.json()
    assert len(registered) >= 1
    assert registered[0]["export_format"] == "ONNX"


def test_training_cancellation(synthetic_classification_env):
    """Verify that a running job can be cleanly cancelled."""
    env = synthetic_classification_env
    job_payload = {
        "project_id": env["project_id"],
        "dataset_id": env["dataset_id"],
        "name": "Cancel_TestRun",
        "hyperparameters": {
            "model_architecture": "resnet18",
            "pretrained": False,
            "device": "cpu",
            "input_size": 64,
            "batch_size": 2,
            "epochs": 20,
            "learning_rate": 0.01,
            "optimizer": "AdamW",
            "num_workers": 0,
        },
    }
    create_resp = client.post("/api/v1/training/jobs", json=job_payload)
    job_id = create_resp.json()["id"]

    client.post(f"/api/v1/training/jobs/{job_id}/start")
    time.sleep(0.5)

    cancel_resp = client.post(f"/api/v1/training/jobs/{job_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] in ["CANCEL_REQUESTED", "CANCELLED"]
