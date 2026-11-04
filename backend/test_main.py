from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "linuxcore-api"
    assert "timestamp" in payload


def test_metrics_endpoint_shape_and_ranges():
    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    payload = response.json()

    expected_fields = {
        "hostname",
        "platform",
        "cpu_percent",
        "cpu_count",
        "memory_percent",
        "memory_used_gb",
        "memory_total_gb",
        "disk_percent",
        "disk_used_gb",
        "disk_total_gb",
        "timestamp",
    }
    assert expected_fields.issubset(payload.keys())

    assert isinstance(payload["hostname"], str)
    assert isinstance(payload["platform"], str)
    assert 0 <= payload["cpu_percent"] <= 100
    assert payload["cpu_count"] >= 1
    assert 0 <= payload["memory_percent"] <= 100
    assert 0 <= payload["disk_percent"] <= 100
    assert payload["memory_total_gb"] > 0
    assert payload["disk_total_gb"] > 0


def test_unknown_route_returns_404():
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
