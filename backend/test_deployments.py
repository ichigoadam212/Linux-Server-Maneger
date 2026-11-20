import json

from fastapi.testclient import TestClient

import deployments
from main import app

client = TestClient(app)


def test_deploy_rejects_unavailable_rootless_runtime(monkeypatch):
    monkeypatch.setattr(deployments, "_runtime", lambda: None)
    response = client.post("/api/v1/apps/static-site/deploy", json={"host_port": 8081})
    assert response.status_code == 503


def test_deploy_creates_loopback_only_site_and_persistent_volume(monkeypatch, tmp_path):
    mountpoint = tmp_path / "volume"
    mountpoint.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    backup = state_dir / "static-site.previous.html"
    monkeypatch.setattr(deployments, "_runtime", lambda: ("podman", "/usr/bin/podman"))
    monkeypatch.setattr(deployments, "_paths", lambda: (state_dir, backup))
    monkeypatch.setattr(deployments, "_site_status", lambda *args: {"deployed": False})
    calls = []

    def fake_run(argv, timeout=20):
        calls.append(argv)
        if argv[1:3] == ["volume", "inspect"]:
            return {"returncode": 0, "stdout": json.dumps([{"Mountpoint": str(mountpoint), "Labels": {"io.linuxcore.app": deployments.APP_ID}}]), "stderr": ""}
        return {"returncode": 0, "stdout": "ok", "stderr": ""}

    monkeypatch.setattr(deployments, "_run", fake_run)
    response = client.post("/api/v1/apps/static-site/deploy", json={"host_port": 8081})

    assert response.status_code == 200
    command = next(call for call in calls if len(call) > 1 and call[1] == "run")
    assert "--publish" in command
    assert command[command.index("--publish") + 1] == "127.0.0.1:8081:80"
    assert command[command.index("--volume") + 1] == "linuxcore-static-site-data:/usr/share/nginx/html:ro"
    assert command[-1] == deployments.IMAGE
    assert (mountpoint / "index.html").read_text(encoding="utf-8") == deployments.DEFAULT_HTML
    assert backup.read_text(encoding="utf-8") == deployments.DEFAULT_HTML


def test_site_content_update_and_rollback(monkeypatch, tmp_path):
    mountpoint = tmp_path / "volume"
    mountpoint.mkdir()
    index_path = mountpoint / "index.html"
    index_path.write_text("<h1>Before</h1>", encoding="utf-8")
    state_dir = tmp_path / "state"
    backup = state_dir / "static-site.previous.html"
    state_dir.mkdir()
    monkeypatch.setattr(deployments, "_runtime", lambda: ("podman", "/usr/bin/podman"))
    monkeypatch.setattr(deployments, "_paths", lambda: (state_dir, backup))
    monkeypatch.setattr(deployments, "_site_status", lambda *args: {"deployed": True, "url": "http://127.0.0.1:8081"})
    monkeypatch.setattr(deployments, "_run", lambda argv, timeout=20: {
        "returncode": 0,
        "stdout": json.dumps([{"Mountpoint": str(mountpoint), "Labels": {"io.linuxcore.app": deployments.APP_ID}}]),
        "stderr": "",
    })

    updated = client.put("/api/v1/apps/static-site/content", json={"content": "<h1>After</h1>"})
    assert updated.status_code == 200
    assert index_path.read_text(encoding="utf-8") == "<h1>After</h1>"
    assert backup.read_text(encoding="utf-8") == "<h1>Before</h1>"

    rolled_back = client.post("/api/v1/apps/static-site/rollback")
    assert rolled_back.status_code == 200
    assert index_path.read_text(encoding="utf-8") == "<h1>Before</h1>"
    assert backup.read_text(encoding="utf-8") == "<h1>After</h1>"


def test_site_logs_are_bounded_and_read_only(monkeypatch):
    monkeypatch.setattr(deployments, "_runtime", lambda: ("podman", "/usr/bin/podman"))
    monkeypatch.setattr(deployments, "_site_status", lambda *args: {"deployed": True})
    captured = {}

    def fake_run(argv, timeout=20):
        captured["argv"] = argv
        return {"returncode": 0, "stdout": "site log", "stderr": ""}

    monkeypatch.setattr(deployments, "_run", fake_run)
    response = client.get("/api/v1/apps/static-site/logs")
    assert response.status_code == 200
    assert captured["argv"] == ["/usr/bin/podman", "logs", "--tail", "200", deployments.CONTAINER_NAME]
    assert response.json()["lines"] == "site log"


def test_deploy_validates_port_and_content_size():
    bad_port = client.post("/api/v1/apps/static-site/deploy", json={"host_port": 80})
    assert bad_port.status_code == 422
    too_large = client.put("/api/v1/apps/static-site/content", json={"content": "x" * 65537})
    assert too_large.status_code == 422
