import pytest
from pathlib import Path


def test_import_and_scan_dataset(client, sample_image_dataset):
    # 1. Create a project
    project_res = client.post(
        "/api/v1/projects",
        json={"name": "Vision Dataset Test", "task_type": "Image Classification"},
    )
    assert project_res.status_code == 201
    project_id = project_res.json()["id"]

    # 2. Import dataset with immediate scan
    dataset_payload = {
        "name": "Factory Images",
        "description": "Inspection images from camera 1",
        "root_path": str(sample_image_dataset),
        "format": "folder_images",
        "scan_immediately": True,
    }
    dataset_res = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json=dataset_payload,
    )
    assert dataset_res.status_code == 201
    dataset_data = dataset_res.json()
    dataset_id = dataset_data["id"]

    # Verify counts:
    # 2 valid images (image1.png, subdir/image2.jpg)
    # 1 corrupted image (corrupted.jpg)
    # 1 unsupported file (notes.txt)
    assert dataset_data["valid_image_count"] == 2
    assert dataset_data["corrupted_image_count"] == 1
    assert dataset_data["image_count"] == 3  # total images (valid + corrupt)
    assert dataset_data["unsupported_file_count"] == 1
    assert dataset_data["last_scanned_at"] is not None

    # 3. Query paginated images
    images_res = client.get(f"/api/v1/datasets/{dataset_id}/images?page=1&page_size=10")
    assert images_res.status_code == 200
    images_data = images_res.json()
    assert images_data["total"] == 3
    assert len(images_data["items"]) == 3

    # Check that valid image has dimensions and channels
    valid_items = [item for item in images_data["items"] if item["is_valid"]]
    assert len(valid_items) == 2
    for item in valid_items:
        assert item["width"] is not None
        assert item["height"] is not None
        assert item["channels"] is not None

    # Check corrupted item
    corrupt_items = [item for item in images_data["items"] if not item["is_valid"]]
    assert len(corrupt_items) == 1
    assert corrupt_items[0]["error_reason"] is not None

    # 4. Stream valid image file
    valid_id = valid_items[0]["id"]
    stream_res = client.get(f"/api/v1/datasets/{dataset_id}/images/{valid_id}/file")
    assert stream_res.status_code == 200
    assert len(stream_res.content) > 0

    # 5. Check dashboard stats now reflect real data
    dash_res = client.get("/api/v1/dashboard/stats")
    assert dash_res.status_code == 200
    stats = dash_res.json()
    assert stats["total_projects"] >= 1
    assert stats["total_datasets"] >= 1
    assert stats["total_indexed_images"] >= 3

    # 6. Re-scan endpoint
    rescan_res = client.post(f"/api/v1/datasets/{dataset_id}/scan")
    assert rescan_res.status_code == 200
    scan_info = rescan_res.json()
    assert scan_info["valid_images"] == 2
    assert scan_info["corrupted_images"] == 1
    assert scan_info["unsupported_files"] == 1

    # 7. Delete dataset
    del_res = client.delete(f"/api/v1/datasets/{dataset_id}")
    assert del_res.status_code == 204

    # Verify original files on disk were NOT deleted
    assert (sample_image_dataset / "image1.png").exists()


def test_import_nonexistent_directory(client):
    project_res = client.post(
        "/api/v1/projects",
        json={"name": "Bad Path Project", "task_type": "Image Classification"},
    )
    project_id = project_res.json()["id"]

    res = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={
            "name": "Nonexistent",
            "root_path": "C:/non_existent_folder_xyz_12345",
        },
    )
    assert res.status_code == 400
    assert "does not exist" in res.json()["detail"].lower()


def test_import_restricted_system_root(client):
    project_res = client.post(
        "/api/v1/projects",
        json={"name": "Root Test Project", "task_type": "OCR"},
    )
    project_id = project_res.json()["id"]

    res = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={
            "name": "System Root Dataset",
            "root_path": "C:\\Windows",
        },
    )
    assert res.status_code == 400
    assert "prohibited for security" in res.json()["detail"].lower()
