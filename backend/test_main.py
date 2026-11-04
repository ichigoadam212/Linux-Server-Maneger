from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "linuxcore-api"
    assert payload["mode"] == "read-only"
    assert "timestamp" in payload


def test_metrics_endpoint_shape_and_ranges():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    payload = response.json()
    expected = {
        "hostname", "platform", "uptime_seconds", "cpu_percent", "cpu_count",
        "memory_percent", "memory_used_gb", "memory_total_gb", "disk_percent",
        "disk_used_gb", "disk_total_gb", "network_bytes_sent",
        "network_bytes_recv", "timestamp",
    }
    assert expected.issubset(payload)
    assert 0 <= payload["cpu_percent"] <= 100
    assert payload["cpu_count"] >= 1
    assert 0 <= payload["memory_percent"] <= 100
    assert 0 <= payload["disk_percent"] <= 100
    assert payload["memory_total_gb"] > 0
    assert payload["disk_total_gb"] > 0
    assert payload["uptime_seconds"] >= 0


def test_storage_endpoint_is_read_only_inventory():
    response = client.get("/api/v1/storage")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["items"], list)
    for item in payload["items"]:
        assert 0 <= item["percent"] <= 100
        assert item["total_gb"] >= 0


def test_process_endpoint_does_not_return_command_lines():
    response = client.get("/api/v1/processes")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) <= 30
    for item in payload["items"]:
        assert "cmdline" not in item
        assert "environ" not in item


def test_network_endpoint_shape():
    response = client.get("/api/v1/network")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["interfaces"], list)
    for item in payload["interfaces"]:
        assert isinstance(item["is_up"], bool)


def test_unknown_route_returns_404():
    assert client.get("/api/v1/not-a-route").status_code == 404
