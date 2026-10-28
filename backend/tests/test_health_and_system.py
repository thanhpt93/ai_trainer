def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert "app_name" in data
    assert "version" in data


def test_system_info_endpoint(client):
    response = client.get("/api/v1/system-info")
    assert response.status_code == 200
    data = response.json()
    assert "os" in data
    assert "python_version" in data
    assert "cpu_count" in data
    assert "cuda_available" in data


def test_dashboard_stats_empty(client):
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_projects"] == 0
    assert data["total_datasets"] == 0
    assert data["total_indexed_images"] == 0
    assert data["running_training_jobs"] == 0
    assert isinstance(data["recent_projects"], list)
