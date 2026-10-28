import pytest
from pathlib import Path


def test_classification_and_object_detection_workflow(client, sample_image_dataset):
    # 1. Create Project
    proj_res = client.post(
        "/api/v1/projects",
        json={
            "name": "Annotation Workflow Test",
            "task_type": "Object Detection",
            "is_multi_label": False,
        },
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Create Labels
    lbl1 = client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "Defect", "color": "#ef4444"},
    ).json()
    lbl2 = client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "Component", "color": "#3b82f6"},
    ).json()

    # 3. Create Dataset
    ds_res = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={
            "name": "Dataset For Annotation",
            "root_path": str(sample_image_dataset),
            "scan_immediately": True,
        },
    )
    assert ds_res.status_code == 201
    dataset_id = ds_res.json()["id"]

    # 4. List annotated images
    img_list = client.get(f"/api/v1/datasets/{dataset_id}/annotated-images").json()
    assert img_list["total"] == 3
    assert all(item["status"] == "UNANNOTATED" for item in img_list["items"])

    first_image = img_list["items"][0]
    image_id = first_image["id"]

    # 5. Fetch default annotation
    ann_res = client.get(f"/api/v1/images/{image_id}/annotation")
    assert ann_res.status_code == 200
    assert ann_res.json()["status"] == "UNANNOTATED"

    # 6. Save Object Detection annotation with 2 valid boxes
    save_payload = {
        "task_type": "Object Detection",
        "is_negative": False,
        "objects": [
            {
                "label_id": lbl1["id"],
                "x_min": 0.1,
                "y_min": 0.2,
                "x_max": 0.5,
                "y_max": 0.6,
                "confidence": 1.0,
            },
            {
                "label_id": lbl2["id"],
                "x_min": 0.6,
                "y_min": 0.3,
                "x_max": 0.9,
                "y_max": 0.8,
                "confidence": 0.95,
            },
        ],
    }
    saved_ann = client.put(f"/api/v1/images/{image_id}/annotation", json=save_payload)
    assert saved_ann.status_code == 200
    ann_data = saved_ann.json()
    assert ann_data["status"] == "ANNOTATED"
    assert len(ann_data["objects"]) == 2

    # 7. Check label deletion protection: Deleting referenced lbl1 must fail with 409
    del_lbl_res = client.delete(f"/api/v1/labels/{lbl1['id']}")
    assert del_lbl_res.status_code == 409
    assert "referenced" in del_lbl_res.json()["detail"].lower()

    # 8. Check summary endpoint
    summary = client.get(f"/api/v1/datasets/{dataset_id}/annotation-summary").json()
    assert summary["total_images"] == 3
    assert summary["annotated_images"] == 1
    assert summary["unannotated_images"] == 2
    assert summary["class_distribution"]["Defect"] == 1
    assert summary["class_distribution"]["Component"] == 1
    assert summary["completion_percentage"] > 0

    # 9. Mark second image as confirmed negative
    second_image_id = img_list["items"][1]["id"]
    neg_res = client.post(
        f"/api/v1/images/{second_image_id}/annotation/mark-negative",
        json={"is_negative": True},
    )
    assert neg_res.status_code == 200
    assert neg_res.json()["is_negative"] is True
    assert neg_res.json()["status"] == "ANNOTATED"

    # 10. Mark third image for review
    third_image_id = img_list["items"][2]["id"]
    rev_res = client.post(
        f"/api/v1/images/{third_image_id}/annotation/mark-review",
        json={"needs_review": True},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "NEEDS_REVIEW"

    # 11. Test status filtering:
    # Filter ANNOTATED
    filtered_ann = client.get(f"/api/v1/datasets/{dataset_id}/annotated-images?status=ANNOTATED").json()
    assert filtered_ann["total"] == 2  # image 1 with boxes, image 2 negative

    # Filter NEEDS_REVIEW
    filtered_rev = client.get(f"/api/v1/datasets/{dataset_id}/annotated-images?status=NEEDS_REVIEW").json()
    assert filtered_rev["total"] == 1

    # 12. Test Export to YOLO
    export_yolo = client.post(
        f"/api/v1/datasets/{dataset_id}/export",
        json={"format": "yolo", "include_unannotated": False},
    )
    assert export_yolo.status_code == 200
    yolo_data = export_yolo.json()
    assert Path(yolo_data["export_path"]).exists()
    assert (Path(yolo_data["export_path"]) / "data.yaml").exists()

    # 13. Test Export to COCO
    export_coco = client.post(
        f"/api/v1/datasets/{dataset_id}/export",
        json={"format": "coco", "include_unannotated": True},
    )
    assert export_coco.status_code == 200
    coco_data = export_coco.json()
    coco_json = Path(coco_data["export_path"]) / "annotations.json"
    assert coco_json.exists()
    import json
    with open(coco_json, "r", encoding="utf-8") as f:
        coco_content = json.load(f)
    assert len(coco_content["categories"]) == 2
    assert len(coco_content["annotations"]) >= 2
