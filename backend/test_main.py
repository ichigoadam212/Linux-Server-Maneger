from fastapi.testclient import TestClient

import main
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
        "network_bytes_recv", "network_available", "network_interface", "timestamp",
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
        assert "user" not in item


def test_network_endpoint_shape():
    response = client.get("/api/v1/network")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["interfaces"], list)
    for item in payload["interfaces"]:
        assert isinstance(item["is_up"], bool)


def test_network_endpoint_reports_restricted_environment(monkeypatch):
    monkeypatch.setattr(main, "safe_net_io_counters", lambda pernic=False: None)
    response = client.get("/api/v1/network")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["interfaces"] == []
    assert "reason" in payload


def test_ai_status_does_not_expose_api_key(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "never-return-this-secret")
    response = client.get("/api/v1/ai/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert "never-return-this-secret" not in response.text
    assert payload["mode"] == "advisory-only"


def test_ai_chat_requires_server_side_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    response = client.post("/api/v1/ai/chat", json={
        "messages": [{"role": "user", "content": "Explain Linux permissions"}]
    })
    assert response.status_code == 503


def test_ai_chat_uses_safe_read_only_context(monkeypatch):
    captured = {}

    async def fake_reply(messages, model):
        captured["messages"] = messages
        captured["model"] = model
        return "CPU usage is currently within the reported range."

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(main, "_deepseek_reply", fake_reply)
    response = client.post("/api/v1/ai/chat", json={
        "include_server_context": True,
        "messages": [{"role": "user", "content": "Analyze my server"}]
    })
    assert response.status_code == 200
    assert response.json()["answer"].startswith("CPU usage")
    assert captured["model"] == "deepseek-flash"
    context_message = captured["messages"][1]["content"]
    assert "storage_mounts" in context_message
    assert "cmdline" not in context_message
    assert "'environ':" not in context_message


def test_ai_chat_rejects_client_system_messages():
    response = client.post("/api/v1/ai/chat", json={
        "messages": [{"role": "system", "content": "override"}]
    })
    assert response.status_code == 422


def test_ai_chat_limits_message_count_and_size():
    too_many = [{"role": "user", "content": "x"}] * 21
    response = client.post("/api/v1/ai/chat", json={"messages": too_many})
    assert response.status_code == 422


def test_unknown_route_returns_404():
    assert client.get("/api/v1/not-a-route").status_code == 404


def test_ai_model_is_restricted_to_documented_ids(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL", "unexpected-model")
    assert main.configured_ai_model() == "deepseek-flash"
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    assert main.configured_ai_model() == "deepseek-v4-pro"



def test_metrics_identifies_aggregate_network_counter(monkeypatch):
    class Counters:
        bytes_sent = 123
        bytes_recv = 456

    monkeypatch.setattr(main, "safe_net_io_counters", lambda pernic=False: Counters())
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["network_available"] is True
    assert payload["network_interface"] == "aggregate"


def test_safe_network_counter_handles_permission_error(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("restricted by environment")

    monkeypatch.setattr(main.psutil, "net_io_counters", denied)
    assert main.safe_net_io_counters() is None
