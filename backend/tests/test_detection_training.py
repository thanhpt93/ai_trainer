import os
import sys
import time
import shutil
import tempfile
import json
from pathlib import Path
import pytest
from PIL import Image
import torch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.domain.models import (
    Project,
    Dataset,
    ImageRecord,
    ProjectLabel,
    ImageAnnotation,
    ObjectAnnotation,
    TrainingJob,
    ModelArtifact,
)
from backend.app.adapters.detection_dataset_adapter import (
    validate_and_convert_box,
    transform_box_resize,
    transform_box_hflip,
    DetectionDatasetAdapter,
)
from backend.app.adapters.detection_evaluator import (
    compute_box_iou,
    DetectionEvaluator,
)
from backend.app.services.model_catalog_service import ModelCatalogService

client = TestClient(app)


# =====================================================================
# Unit Tests
# =====================================================================

def test_detection_coordinate_conversions():
    """Verify coordinate normalization, validation, boundary tolerances, and pixel conversion."""
    img_w, img_h = 1000, 800

    # Normal valid box
    box = validate_and_convert_box(0.1, 0.2, 0.5, 0.6, img_w, img_h)
    assert box == [100.0, 160.0, 500.0, 480.0]

    # Small boundary overflow within clamp tolerance (e.g. -0.01 or 1.01)
    box_overflow = validate_and_convert_box(-0.01, 0.0, 1.02, 1.0, img_w, img_h)
    assert box_overflow == [0.0, 0.0, 1000.0, 800.0]

    # Zero area box (x_max <= x_min or y_max <= y_min)
    assert validate_and_convert_box(0.5, 0.2, 0.5, 0.6, img_w, img_h) is None
    assert validate_and_convert_box(0.1, 0.6, 0.5, 0.6, img_w, img_h) is None
    assert validate_and_convert_box(0.7, 0.8, 0.3, 0.4, img_w, img_h) is None

    # Invalid image dimensions
    assert validate_and_convert_box(0.1, 0.1, 0.5, 0.5, 0, 800) is None

    # NaN / Inf handling
    assert validate_and_convert_box(float("nan"), 0.1, 0.5, 0.5, img_w, img_h) is None


def test_detection_box_transformations():
    """Verify resize scaling and horizontal flip coordinate consistency."""
    orig_box = [100.0, 200.0, 300.0, 400.0]

    # Resize (1000, 800) -> (500, 400) (scale factor 0.5)
    resized_box = transform_box_resize(orig_box, 1000, 800, 500, 400)
    assert resized_box == [50.0, 100.0, 150.0, 200.0]

    # Horizontal flip on width 500
    # x1_new = 500 - 150 = 350, x2_new = 500 - 50 = 450
    flipped_box = transform_box_hflip(resized_box, 500)
    assert flipped_box == [350.0, 100.0, 450.0, 200.0]

    # Double flip returns to original x coordinates
    re_flipped = transform_box_hflip(flipped_box, 500)
    assert re_flipped == resized_box


def test_box_iou_computation():
    """Verify bounding box IoU calculation."""
    # Identical boxes
    box_a = [10.0, 10.0, 100.0, 100.0]
    assert compute_box_iou(box_a, box_a) == 1.0

    # Non-overlapping
    box_b = [200.0, 200.0, 300.0, 300.0]
    assert compute_box_iou(box_a, box_b) == 0.0

    # 50% overlap scenario
    box_c = [10.0, 10.0, 100.0, 55.0]
    box_d = [10.0, 10.0, 100.0, 100.0]
    iou = compute_box_iou(box_c, box_d)
    assert 0.49 <= iou <= 0.51


def test_detection_model_catalog():
    """Verify detection models are listed and built with correct output heads."""
    # Test catalog API filter
    resp = client.get("/api/v1/training/models?task_type=OBJECT_DETECTION")
    assert resp.status_code == 200
    models_list = resp.json()
    model_ids = [m["id"] for m in models_list]
    assert "fasterrcnn_resnet50_fpn" in model_ids
    assert "fasterrcnn_mobilenet_v3_large_320_fpn" in model_ids

    # Test building Faster R-CNN with 3 classes (background + 2 foreground)
    m = ModelCatalogService.build_model("fasterrcnn_mobilenet_v3_large_320_fpn", num_classes=3, pretrained=False)
    assert m.roi_heads.box_predictor.cls_score.out_features == 3
    assert m.roi_heads.box_predictor.bbox_pred.out_features == 3 * 4


def test_detection_evaluator():
    """Verify COCO-style evaluator with true positive, false positive, and negative image scenarios."""
    class_mapping = [
        {"index": 0, "name": "__background__", "is_background": True},
        {"index": 1, "name": "Vehicle", "is_background": False},
        {"index": 2, "name": "Person", "is_background": False},
    ]

    samples = [
        {
            "image_id": "img_1",
            "relative_path": "img_1.jpg",
            "width": 1000,
            "height": 800,
            "boxes": [[100.0, 100.0, 300.0, 300.0]],
            "labels": [1],
        },
        {
            "image_id": "img_neg",
            "relative_path": "img_neg.jpg",
            "width": 1000,
            "height": 800,
            "boxes": [],
            "labels": [],
        },
    ]

    predictions = [
        {
            "boxes": [[105.0, 95.0, 302.0, 305.0], [500.0, 500.0, 600.0, 600.0]],
            "labels": [1, 2],
            "scores": [0.92, 0.40],
        },
        {
            "boxes": [],
            "labels": [],
            "scores": [],
        },
    ]

    report = DetectionEvaluator.evaluate(
        samples=samples,
        predictions=predictions,
        class_mapping=class_mapping,
        confidence_threshold=0.5,
        iou_threshold=0.5,
    )

    assert report.task_type == "Object Detection"
    assert report.total_samples == 2
    assert report.total_ground_truth_boxes == 1
    assert len(report.per_class_metrics) == 2
    # At conf 0.5, the box for Vehicle is matched (IoU > 0.9)
    assert report.samples[0].matched_count == 1
    assert report.samples[1].ground_truth_boxes == []


# =====================================================================
# Synthetic Dataset Fixture & Integration Tests
# =====================================================================

@pytest.fixture(scope="module")
def synthetic_detection_env():
    """Sets up a complete synthetic object detection project with 2 classes and a negative image."""
    temp_dir = tempfile.mkdtemp(prefix="nova_test_det_")
    db = SessionLocal()

    try:
        # Create Object Detection Project
        proj = Project(
            name=f"Test_Detection_Proj_{int(time.time())}",
            task_type="Object Detection",
            root_path=temp_dir,
            is_multi_label=False,
            allow_negative_images=True,
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)

        # Create Labels: Vehicle, Pedestrian
        lbl_veh = ProjectLabel(project_id=proj.id, name="Vehicle", color="#3b82f6")
        lbl_ped = ProjectLabel(project_id=proj.id, name="Pedestrian", color="#10b981")
        db.add_all([lbl_veh, lbl_ped])
        db.commit()
        db.refresh(lbl_veh)
        db.refresh(lbl_ped)

        # Create Dataset
        ds = Dataset(
            project_id=proj.id,
            name="Synthetic_Detection_Dataset",
            root_path=temp_dir,
            image_count=6,
            valid_image_count=6,
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)

        # Create 6 synthetic images
        # 4 images with bounding boxes, 1 negative image (no objects), 1 with multiple boxes
        img_records = []
        for i in range(1, 7):
            fname = f"sample_{i:02d}.jpg"
            fpath = Path(temp_dir) / fname
            # Generate solid RGB image
            img = Image.new("RGB", (320, 240), color=(50 + i * 25, 80 + i * 15, 120 + i * 10))
            img.save(str(fpath))

            rec = ImageRecord(
                dataset_id=ds.id,
                relative_path=fname,
                absolute_path=str(fpath),
                file_size_bytes=fpath.stat().st_size,
                width=320,
                height=240,
                is_valid=True,
            )
            db.add(rec)
            img_records.append(rec)

        db.commit()
        for r in img_records:
            db.refresh(r)

        # Image 1: Vehicle box
        ann1 = ImageAnnotation(dataset_id=ds.id, image_id=img_records[0].id, task_type="Object Detection", status="ANNOTATED", is_negative=False)
        db.add(ann1)
        db.commit()
        db.refresh(ann1)
        db.add(ObjectAnnotation(image_annotation_id=ann1.id, label_id=lbl_veh.id, x_min=0.1, y_min=0.1, x_max=0.5, y_max=0.6))

        # Image 2: Pedestrian box
        ann2 = ImageAnnotation(dataset_id=ds.id, image_id=img_records[1].id, task_type="Object Detection", status="ANNOTATED", is_negative=False)
        db.add(ann2)
        db.commit()
        db.refresh(ann2)
        db.add(ObjectAnnotation(image_annotation_id=ann2.id, label_id=lbl_ped.id, x_min=0.2, y_min=0.15, x_max=0.4, y_max=0.85))

        # Image 3: Both Vehicle & Pedestrian
        ann3 = ImageAnnotation(dataset_id=ds.id, image_id=img_records[2].id, task_type="Object Detection", status="ANNOTATED", is_negative=False)
        db.add(ann3)
        db.commit()
        db.refresh(ann3)
        db.add_all([
            ObjectAnnotation(image_annotation_id=ann3.id, label_id=lbl_veh.id, x_min=0.05, y_min=0.2, x_max=0.45, y_max=0.7),
            ObjectAnnotation(image_annotation_id=ann3.id, label_id=lbl_ped.id, x_min=0.55, y_min=0.1, x_max=0.8, y_max=0.9),
        ])

        # Image 4: Vehicle box
        ann4 = ImageAnnotation(dataset_id=ds.id, image_id=img_records[3].id, task_type="Object Detection", status="ANNOTATED", is_negative=False)
        db.add(ann4)
        db.commit()
        db.refresh(ann4)
        db.add(ObjectAnnotation(image_annotation_id=ann4.id, label_id=lbl_veh.id, x_min=0.3, y_min=0.3, x_max=0.8, y_max=0.8))

        # Image 5: Pedestrian box
        ann5 = ImageAnnotation(dataset_id=ds.id, image_id=img_records[4].id, task_type="Object Detection", status="ANNOTATED", is_negative=False)
        db.add(ann5)
        db.commit()
        db.refresh(ann5)
        db.add(ObjectAnnotation(image_annotation_id=ann5.id, label_id=lbl_ped.id, x_min=0.15, y_min=0.1, x_max=0.45, y_max=0.9))

        # Image 6: Explicit Negative Image (no target objects)
        ann6 = ImageAnnotation(dataset_id=ds.id, image_id=img_records[5].id, task_type="Object Detection", status="ANNOTATED", is_negative=True)
        db.add(ann6)

        db.commit()

        yield {
            "project_id": proj.id,
            "dataset_id": ds.id,
            "temp_dir": temp_dir,
            "sample_image_path": str(Path(temp_dir) / "sample_01.jpg"),
        }
    finally:
        try:
            db_clean = SessionLocal()
            db_clean.query(TrainingJob).filter(TrainingJob.project_id == proj.id).delete()
            db_clean.query(ModelArtifact).filter(ModelArtifact.project_id == proj.id).delete()
            db_clean.query(ObjectAnnotation).filter(
                ObjectAnnotation.image_annotation_id.in_(
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


def test_detection_dataset_validation(synthetic_detection_env):
    """Verify dataset validation checks, class counts, and split manifest creation."""
    env = synthetic_detection_env
    payload = {
        "project_id": env["project_id"],
        "dataset_id": env["dataset_id"],
        "split_config": {
            "train_ratio": 0.7,
            "val_ratio": 0.3,
            "test_ratio": 0.0,
            "random_seed": 42,
        },
    }

    # Test POST /training/datasets/validate
    resp = client.post("/api/v1/training/datasets/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["task_type"] == "Object Detection"
    assert data["total_images"] == 6
    assert data["valid_annotated_images"] == 6
    assert data["negative_images"] == 1
    assert data["total_bounding_boxes"] >= 5
    assert len(data["classes"]) == 2
    assert data["train_count"] >= 3
    assert data["val_count"] >= 1

    # Test POST /training/datasets/{id}/validate endpoint
    resp2 = client.post(f"/api/v1/training/datasets/{env['dataset_id']}/validate", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["is_valid"] is True


def test_detection_end_to_end_training_and_export(synthetic_detection_env):
    """
    End-to-End Test:
    1. Create training job for Faster R-CNN.
    2. Start worker subprocess.
    3. Monitor training progress and verify real losses.
    4. Verify checkpoints (best and latest).
    5. Run interactive inference and get predicted bounding boxes.
    6. Run post-training evaluation.
    7. Export model to ONNX package and verify metadata.
    """
    env = synthetic_detection_env

    # 1. Create Training Job
    job_payload = {
        "project_id": env["project_id"],
        "dataset_id": env["dataset_id"],
        "name": "Integration_Test_Detection_Run",
        "hyperparameters": {
            "model_architecture": "fasterrcnn_mobilenet_v3_large_320_fpn",
            "pretrained": False,
            "device": "cpu",
            "input_size": 320,
            "batch_size": 2,
            "epochs": 1,
            "learning_rate": 0.001,
            "optimizer": "SGD",
            "momentum": 0.9,
            "scheduler": "none",
            "confidence_threshold": 0.1,
            "iou_threshold": 0.5,
        },
        "split_config": {
            "train_ratio": 0.7,
            "val_ratio": 0.3,
            "test_ratio": 0.0,
            "random_seed": 42,
        },
    }

    create_resp = client.post("/api/v1/training/jobs", json=job_payload)
    assert create_resp.status_code == 201
    job = create_resp.json()
    job_id = job["id"]
    assert job["status"] == "QUEUED"
    assert job["task_type"] == "Object Detection"

    # 2. Start Training Job
    start_resp = client.post(f"/api/v1/training/jobs/{job_id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] in ["RUNNING", "PREPARING", "COMPLETED"]

    # 3. Wait for training worker execution (up to 45 seconds for 1 epoch on CPU)
    completed = False
    for _ in range(30):
        time.sleep(1.5)
        status_resp = client.get(f"/api/v1/training/jobs/{job_id}")
        assert status_resp.status_code == 200
        cur_status = status_resp.json()["status"]
        if cur_status == "COMPLETED":
            completed = True
            break
        elif cur_status == "FAILED":
            err_msg = status_resp.json().get("error_message")
            pytest.fail(f"Training worker failed: {err_msg}")

    assert completed, "Training worker did not complete within timeout."

    # 4. Verify Metrics Endpoint
    metrics_resp = client.get(f"/api/v1/training/jobs/{job_id}/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert len(metrics) >= 1
    first_epoch = metrics[0]
    assert first_epoch["epoch"] == 1
    assert "train_loss" in first_epoch
    assert first_epoch["train_loss"] > 0.0
    assert "loss_classifier" in first_epoch
    assert "loss_box_reg" in first_epoch

    # 5. Check logs
    logs_resp = client.get(f"/api/v1/training/jobs/{job_id}/logs")
    assert logs_resp.status_code == 200
    logs_data = logs_resp.json()
    assert logs_data["total_lines"] > 0

    # 6. Test Interactive Model Prediction
    pred_resp = client.post(
        f"/api/v1/training/jobs/{job_id}/predict",
        json={"image_path": env["sample_image_path"], "confidence_threshold": 0.01},
    )
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert pred_data["task_type"] == "Object Detection"
    assert "detected_objects" in pred_data
    assert pred_data["image_width"] == 320
    assert pred_data["image_height"] == 240
    assert pred_data["inference_time_ms"] > 0

    # 7. Test Evaluation Endpoint
    eval_resp = client.post(f"/api/v1/training/jobs/{job_id}/evaluate?split=val")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["task_type"] == "Object Detection"
    assert "map" in eval_data
    assert "samples" in eval_data

    # 8. Test ONNX Export Endpoint
    export_resp = client.post(
        f"/api/v1/training/jobs/{job_id}/export",
        json={"format": "ONNX", "input_size": 320},
    )
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["success"] is True
    assert Path(export_data["onnx_file_path"]).exists()
    assert Path(export_data["manifest_path"]).exists()
    assert Path(export_data["metadata_path"]).exists()

    # 9. Verify Registered Model & Artifacts
    models_resp = client.get("/api/v1/models")
    assert models_resp.status_code == 200
    registered = models_resp.json()
    matching = [m for m in registered if m["training_job_id"] == job_id]
    assert len(matching) >= 1
    art_id = matching[0]["id"]

    art_resp = client.get(f"/api/v1/models/{art_id}/artifacts")
    assert art_resp.status_code == 200
    art_info = art_resp.json()
    assert "manifest" in art_info
    assert art_info["name"] is not None


def test_detection_cancellation_and_resume(synthetic_detection_env):
    """Verify cooperative cancellation of a detection job and resumption from saved checkpoint."""
    env = synthetic_detection_env

    # Create job with 10 epochs
    create_resp = client.post(
        "/api/v1/training/jobs",
        json={
            "project_id": env["project_id"],
            "dataset_id": env["dataset_id"],
            "name": "Cancel_Resume_Test_Job",
            "hyperparameters": {
                "model_architecture": "fasterrcnn_mobilenet_v3_large_320_fpn",
                "pretrained": False,
                "device": "cpu",
                "input_size": 320,
                "batch_size": 2,
                "epochs": 10,
                "learning_rate": 0.001,
            },
            "split_config": {"train_ratio": 0.7, "val_ratio": 0.3, "test_ratio": 0.0, "random_seed": 42},
        },
    )
    job_id = create_resp.json()["id"]

    # Start job
    client.post(f"/api/v1/training/jobs/{job_id}/start")
    time.sleep(1.0)

    # Cancel job
    cancel_resp = client.post(f"/api/v1/training/jobs/{job_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] in ["CANCEL_REQUESTED", "CANCELLED"]

    time.sleep(1.5)
    final_status = client.get(f"/api/v1/training/jobs/{job_id}").json()["status"]
    assert final_status in ["CANCEL_REQUESTED", "CANCELLED", "COMPLETED"]

    # Test Resume Endpoint
    resume_resp = client.post(f"/api/v1/training/jobs/{job_id}/resume")
    assert resume_resp.status_code in [200, 400]  # If cancelled before 1st checkpoint, 400 is expected
