import pytest


def test_create_project_success(client):
    payload = {
        "name": "Defect Detection",
        "description": "Industrial surface defect classification",
        "task_type": "Image Classification",
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Defect Detection"
    assert data["task_type"] == "Image Classification"
    assert "id" in data
    assert "root_path" in data


def test_create_duplicate_project_fails(client):
    payload = {
        "name": "Unique Project",
        "task_type": "Object Detection",
    }
    res1 = client.post("/api/v1/projects", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/projects", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_create_project_invalid_task_type(client):
    payload = {
        "name": "Invalid Task Project",
        "task_type": "NonExistentTaskType",
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 422


def test_list_and_filter_projects(client):
    client.post(
        "/api/v1/projects",
        json={"name": "Alpha Classification", "task_type": "Image Classification"},
    )
    client.post(
        "/api/v1/projects",
        json={"name": "Beta Detection", "task_type": "Object Detection"},
    )

    # List all
    res = client.get("/api/v1/projects")
    assert res.status_code == 200
    assert res.json()["total"] >= 2

    # Filter by task_type
    res_filtered = client.get("/api/v1/projects?task_type=Object Detection")
    assert res_filtered.status_code == 200
    items = res_filtered.json()["items"]
    assert all(item["task_type"] == "Object Detection" for item in items)

    # Search by text
    res_search = client.get("/api/v1/projects?search=Alpha")
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1
    assert res_search.json()["items"][0]["name"] == "Alpha Classification"


def test_get_project_by_id(client):
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "Project to Fetch", "task_type": "Image Segmentation"},
    )
    project_id = create_res.json()["id"]

    fetch_res = client.get(f"/api/v1/projects/{project_id}")
    assert fetch_res.status_code == 200
    assert fetch_res.json()["id"] == project_id
    assert fetch_res.json()["name"] == "Project to Fetch"


def test_update_project(client):
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "Original Name", "task_type": "OCR"},
    )
    project_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Renamed Project", "description": "Updated OCR description"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["name"] == "Renamed Project"
    assert data["description"] == "Updated OCR description"


def test_delete_project(client):
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "Project To Delete", "task_type": "Anomaly Detection"},
    )
    project_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/projects/{project_id}")
    assert del_res.status_code == 204

    fetch_res = client.get(f"/api/v1/projects/{project_id}")
    assert fetch_res.status_code == 404
