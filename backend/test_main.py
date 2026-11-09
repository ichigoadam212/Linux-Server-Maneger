from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_fixed_command_runner_uses_argument_vector_and_caps_output(monkeypatch):
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return type("Result", (), {
            "returncode": 0,
            "stdout": "x" * 13000,
            "stderr": "y" * 4000,
        })()

    monkeypatch.setattr(main.subprocess, "run", fake_run)
    result = main.run_fixed_command(["/usr/bin/example", "--version"], timeout=3)

    assert captured["argv"] == ["/usr/bin/example", "--version"]
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["timeout"] == 3
    assert captured["kwargs"].get("shell", False) is False
    assert len(result["stdout"]) == 12000
    assert len(result["stderr"]) == 3000


def test_fixed_command_runner_handles_timeout(monkeypatch):
    def timed_out(*args, **kwargs):
        raise main.subprocess.TimeoutExpired(args[0], kwargs.get("timeout", 1))

    monkeypatch.setattr(main.subprocess, "run", timed_out)
    result = main.run_fixed_command(["/usr/bin/example"], timeout=2)

    assert result["returncode"] == 127
    assert result["stdout"] == ""
    assert "timed out" in result["stderr"].lower()


def test_fixed_command_runner_handles_missing_executable(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("executable not found")

    monkeypatch.setattr(main.subprocess, "run", missing)
    result = main.run_fixed_command(["/missing/example"])

    assert result["returncode"] == 127
    assert result["stdout"] == ""
    assert "executable not found" in result["stderr"]


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


def test_services_report_unavailable_without_user_manager(monkeypatch):
    monkeypatch.setattr(main, "user_systemctl", lambda: None)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["items"] == []


def test_services_parse_user_units(monkeypatch):
    monkeypatch.setattr(main, "user_systemctl", lambda: "/usr/bin/systemctl")
    monkeypatch.setattr(main, "run_fixed_command", lambda *args, **kwargs: {
        "returncode": 0,
        "stdout": "demo.service loaded active running Demo service\n",
        "stderr": "",
    })
    payload = client.get("/api/v1/services").json()
    assert payload["available"] is True
    assert payload["items"][0]["unit"] == "demo.service"
    assert payload["items"][0]["active"] == "active"


def test_service_action_only_targets_discovered_user_unit(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "user_systemctl", lambda: "/usr/bin/systemctl")
    monkeypatch.setattr(main, "list_user_services", lambda: {
        "available": True, "items": [{"unit": "demo.service"}]
    })
    monkeypatch.setattr(main, "run_fixed_command", lambda argv, **kwargs: (
        calls.append(argv) or {"returncode": 0, "stdout": "", "stderr": ""}
    ))
    result = main.service_action("demo.service", main.ServiceAction(action="restart"))
    assert result["ok"] is True
    assert calls == [["/usr/bin/systemctl", "--user", "restart", "demo.service"]]


def test_service_action_handles_manager_disappearing_after_discovery(monkeypatch):
    monkeypatch.setattr(main, "list_user_services", lambda: {
        "available": True, "items": [{"unit": "demo.service"}]
    })
    monkeypatch.setattr(main, "user_systemctl", lambda: None)

    response = client.post(
        "/api/v1/services/demo.service/action",
        json={"action": "restart"},
    )

    assert response.status_code == 503
    assert "became unavailable" in response.json()["detail"]


def test_service_action_rejects_unlisted_unit(monkeypatch):
    monkeypatch.setattr(main, "list_user_services", lambda: {
        "available": True, "items": []
    })
    from fastapi import HTTPException
    try:
        main.service_action("ssh.service", main.ServiceAction(action="stop"))
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("unlisted service must not be controlled")


def test_container_action_only_targets_discovered_rootless_container(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "list_rootless_containers", lambda: {
        "available": True, "items": [{"id": "abc123", "name": "demo", "image": "test"}]
    })
    monkeypatch.setattr(main, "container_runtime", lambda: ("podman", "/usr/bin/podman"))
    monkeypatch.setattr(main, "run_fixed_command", lambda argv, **kwargs: (
        calls.append(argv) or {"returncode": 0, "stdout": "", "stderr": ""}
    ))

    response = client.post(
        "/api/v1/containers/abc123/action",
        json={"action": "restart"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert calls == [["/usr/bin/podman", "restart", "abc123"]]


def test_container_action_rejects_unlisted_container(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "list_rootless_containers", lambda: {
        "available": True, "items": []
    })
    monkeypatch.setattr(main, "container_runtime", lambda: ("podman", "/usr/bin/podman"))
    monkeypatch.setattr(main, "run_fixed_command", lambda *args, **kwargs: calls.append(args))

    response = client.post(
        "/api/v1/containers/not-listed/action",
        json={"action": "stop"},
    )

    assert response.status_code == 404
    assert calls == []


def test_container_action_handles_runtime_disappearing_after_inventory(monkeypatch):
    monkeypatch.setattr(main, "list_rootless_containers", lambda: {
        "available": True, "items": [{"id": "abc123", "name": "demo"}]
    })
    monkeypatch.setattr(main, "container_runtime", lambda: None)

    response = client.post(
        "/api/v1/containers/abc123/action",
        json={"action": "stop"},
    )

    assert response.status_code == 503
    assert "runtime is unavailable" in response.json()["detail"]


def test_terminal_runs_only_fixed_diagnostic_command(monkeypatch):
    calls = []
    monkeypatch.setattr(main.shutil, "which", lambda name: "/usr/bin/free")
    monkeypatch.setattr(main, "run_fixed_command", lambda argv, **kwargs: (
        calls.append(argv) or {"returncode": 0, "stdout": "Mem: 1G", "stderr": ""}
    ))
    result = main.terminal_run(main.TerminalRequest(command="memory"))
    assert result["mode"] == "read-only"
    assert result["output"] == "Mem: 1G"
    assert calls == [["/usr/bin/free", "-h"]]


def test_terminal_rejects_arbitrary_command():
    response = client.post("/api/v1/terminal/run", json={"command": "rm -rf /"})
    assert response.status_code == 422


def test_container_inventory_reports_missing_rootless_runtime(monkeypatch):
    monkeypatch.setattr(main.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(main.shutil, "which", lambda name: None)
    payload = client.get("/api/v1/containers").json()
    assert payload["available"] is False
    assert payload["items"] == []


def test_recovery_check_reports_project_files():
    response = client.get("/api/v1/recovery/check")
    assert response.status_code == 200
    payload = response.json()
    assert "files" in payload
    assert payload["recovery_mode"] == "backup-env-file-check-project-files-and-start-owned-services"



def test_recovery_run_executes_only_project_recovery_script(monkeypatch):
    calls = []

    def fake_run(argv, timeout=8):
        calls.append((argv, timeout))
        return {"returncode": 0, "stdout": "Recovery checks completed.", "stderr": ""}

    monkeypatch.setattr(main, "run_fixed_command", fake_run)
    response = client.post("/api/v1/recovery/run")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert calls[0][0][0] == "bash"
    assert calls[0][0][1].endswith("/scripts/recover.sh")
    assert calls[0][1] == 60


def test_recovery_run_rejects_overlapping_operation():
    assert main.RECOVERY_LOCK.acquire(blocking=False)
    try:
        response = client.post("/api/v1/recovery/run")
        assert response.status_code == 409
        assert "already running" in response.json()["detail"]
    finally:
        main.RECOVERY_LOCK.release()
