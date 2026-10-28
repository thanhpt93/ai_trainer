import pytest


def test_label_lifecycle(client):
    # 1. Create a project
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Label Test Project", "task_type": "Object Detection"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Create label
    label_res = client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "Scratch", "color": "#ef4444", "description": "Surface scratch defect"},
    )
    assert label_res.status_code == 201
    label_data = label_res.json()
    assert label_data["name"] == "Scratch"
    assert label_data["color"] == "#ef4444"
    label_id = label_data["id"]

    # 3. Duplicate name (case-insensitive) should fail with 409
    dup_res = client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "scratch", "color": "#3b82f6"},
    )
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]

    # 4. List labels
    list_res = client.get(f"/api/v1/projects/{project_id}/labels")
    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) == 1
    assert list_res.json()["items"][0]["annotation_count"] == 0

    # 5. Update label
    patch_res = client.patch(
        f"/api/v1/labels/{label_id}",
        json={"name": "Deep Scratch", "color": "#dc2626"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Deep Scratch"
    assert patch_res.json()["color"] == "#dc2626"

    # 6. Delete label (unreferenced) -> 204
    del_res = client.delete(f"/api/v1/labels/{label_id}")
    assert del_res.status_code == 204

    # Confirm deletion
    list_res2 = client.get(f"/api/v1/projects/{project_id}/labels")
    assert len(list_res2.json()["items"]) == 0
