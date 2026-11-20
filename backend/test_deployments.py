import http.client
import json
import os
from pathlib import Path
import socket
import time

import psutil
from fastapi.testclient import TestClient

import deployments
from main import app

client = TestClient(app)
API = "/api/v1/apps/static-site"
SERVER_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "static_site.py"


def isolated_paths(tmp_path, monkeypatch):
    state = tmp_path / ".runtime" / "deployments"
    site = state / "static-site"
    site.mkdir(mode=0o700, parents=True)
    state.chmod(0o700)
    site.chmod(0o700)
    paths = {
        "state": state,
        "site": site,
        "index": site / "index.html",
        "backup": state / "static-site.previous.html",
        "pid": state / "static-site.pid",
        "port": state / "static-site.port",
        "log": site / "static-site.log",
        "script": SERVER_SCRIPT,
    }
    monkeypatch.setattr(deployments, "_paths", lambda: paths)
    monkeypatch.setattr(deployments, "SCRIPT_PATH", SERVER_SCRIPT)
    return paths


def unused_loopback_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def request_site(port, method="GET", path="/"):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request(method, path, headers={"Host": "127.0.0.1"})
        response = connection.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        peer = connection.sock.getsockname()[0] if connection.sock else None
        return response.status, headers, body, peer
    finally:
        connection.close()


def test_deploy_validates_port_and_content_size():
    bad_port = client.post(API + "/deploy", json={"host_port": 80})
    assert bad_port.status_code == 422
    too_large = client.put(API + "/content", json={"content": "x" * 65537})
    assert too_large.status_code == 422
    too_many_utf8_bytes = client.put(API + "/content", json={"content": "é" * 32769})
    assert too_many_utf8_bytes.status_code == 422


def test_real_loopback_deployment_content_rollback_logs_and_lifecycle(monkeypatch, tmp_path):
    paths = isolated_paths(tmp_path, monkeypatch)
    port = unused_loopback_port()

    deployed = client.post(API + "/deploy", json={"host_port": port})
    assert deployed.status_code == 200, deployed.text
    status = deployed.json()
    assert status["deployed"] is True
    assert status["runtime"] == "python"
    assert status["status"] == "running"
    assert status["health"] == "healthy"
    assert status["url"] == f"http://127.0.0.1:{port}"
    assert status["pid"] != os.getpid()

    code, headers, body, peer = request_site(port)
    assert code == 200
    assert peer == "127.0.0.1"
    assert b"Your site is running" in body
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Frame-Options"] == "DENY"

    code, _, body, _ = request_site(port, path="/%2e%2e/README.md")
    assert code == 404
    assert b"Not found" in body
    assert request_site(port, method="POST")[0] == 405
    assert request_site(port, method="PUT")[0] == 405
    assert request_site(port, method="DELETE")[0] == 405
    assert request_site(port, method="OPTIONS")[0] == 405
    request_site(port, path="/?token=must-not-be-logged")

    saved = client.put(API + "/content", json={"content": "<h1>Updated</h1>"})
    assert saved.status_code == 200, saved.text
    assert request_site(port)[2] == b"<h1>Updated</h1>"
    rolled_back = client.post(API + "/rollback")
    assert rolled_back.status_code == 200, rolled_back.text
    assert b"Your site is running" in request_site(port)[2]
    assert paths["backup"].read_text(encoding="utf-8") == "<h1>Updated</h1>"

    logs = client.get(API + "/logs")
    assert logs.status_code == 200, logs.text
    assert "GET 200" in logs.json()["lines"]
    assert "must-not-be-logged" not in logs.json()["lines"]

    stopped = client.post(API + "/action", json={"action": "stop"})
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["status"] == "stopped"
    assert stopped.json()["deployed"] is True
    try:
        request_site(port)
        raise AssertionError("site still accepts connections after stop")
    except OSError:
        pass

    restarted = client.post(API + "/action", json={"action": "restart"})
    assert restarted.status_code == 200, restarted.text
    assert restarted.json()["status"] == "running"
    assert b"Your site is running" in request_site(port)[2]
    assert client.post(API + "/action", json={"action": "stop"}).status_code == 200


def test_stop_never_signals_a_different_process(monkeypatch, tmp_path):
    paths = isolated_paths(tmp_path, monkeypatch)
    port = unused_loopback_port()
    paths["index"].write_text("<h1>Existing</h1>", encoding="utf-8")
    paths["port"].write_text(str(port), encoding="ascii")
    paths["pid"].write_text(json.dumps({
        "pid": os.getpid(),
        "created": psutil.Process(os.getpid()).create_time(),
    }), encoding="ascii")

    status = client.get(API)
    assert status.status_code == 200
    assert status.json()["deployed"] is True
    assert status.json()["status"] == "stopped"

    stopped = client.post(API + "/action", json={"action": "stop"})
    assert stopped.status_code == 200, stopped.text
    assert psutil.pid_exists(os.getpid())
    assert not paths["pid"].exists()


def test_site_server_rejects_symlink_page(monkeypatch, tmp_path):
    paths = isolated_paths(tmp_path, monkeypatch)
    target = tmp_path / "outside.html"
    target.write_text("secret", encoding="utf-8")
    paths["index"].symlink_to(target)
    paths["port"].write_text("8081", encoding="ascii")

    status = client.get(API)
    assert status.status_code == 200
    assert status.json()["deployed"] is False
    assert status.json()["conflict"] is True
