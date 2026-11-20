import http.client
import json
import os
from pathlib import Path
import socket

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
        "journal": state / "static-site.transaction.json",
        "pid": state / "static-site.pid",
        "port": state / "static-site.port",
        "log": site / "static-site.log",
        "script": SERVER_SCRIPT,
    }
    def provide_paths():
        deployments._recover_page_transaction(paths)
        return paths
    monkeypatch.setattr(deployments, "_paths", provide_paths)
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
        return response.status, headers, body
    finally:
        connection.close()


def test_deploy_validates_port_and_content_size():
    bad_port = client.post(API + "/deploy", json={"host_port": 80})
    assert bad_port.status_code == 422
    too_large = client.put(API + "/content", json={"content": "x" * 65537})
    assert too_large.status_code == 422
    too_many_utf8_bytes = client.put(API + "/content", json={"content": "é" * 32769})
    assert too_many_utf8_bytes.status_code == 422
    assert client.post(API + "/rollback").status_code == 422


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

    try:
        code, headers, body = request_site(port)
        assert code == 200
        assert b"Your site is running" in body
        assert "default-src 'self'" in headers["Content-Security-Policy"]
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Cache-Control"] == "no-store"
        assert headers["X-Frame-Options"] == "DENY"

        code, _, body = request_site(port, path="/%2e%2e/README.md")
        assert code == 404
        assert b"Not found" in body
        for method in ("POST", "PUT", "DELETE", "OPTIONS", "PATCH", "TRACE", "CONNECT", "BREW"):
            code, method_headers, _ = request_site(port, method=method)
            assert code == 405
            assert "default-src 'self'" in method_headers["Content-Security-Policy"]
            assert method_headers["Allow"] == "GET, HEAD"
        request_site(port, path="/?token=must-not-be-logged")

        saved = client.put(API + "/content", json={"content": "<h1>Updated</h1>"})
        assert saved.status_code == 200, saved.text
        assert request_site(port)[2] == b"<h1>Updated</h1>"
        rolled_back = client.post(API + "/rollback", json={"confirm": True})
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
    finally:
        cleanup = client.post(API + "/action", json={"action": "stop"})
        assert cleanup.status_code in {200, 404}, cleanup.text


def test_port_conflict_cleans_failed_deploy_for_retry(monkeypatch, tmp_path):
    paths = isolated_paths(tmp_path, monkeypatch)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        busy_port = listener.getsockname()[1]
        failed = client.post(API + "/deploy", json={"host_port": busy_port})
        assert failed.status_code == 409, failed.text
        assert not paths["index"].exists()
        assert client.get(API).json()["deployed"] is False

    port = unused_loopback_port()
    deployed = client.post(API + "/deploy", json={"host_port": port})
    assert deployed.status_code == 200, deployed.text
    try:
        assert deployed.json()["status"] == "running"
    finally:
        stopped = client.post(API + "/action", json={"action": "stop"})
        assert stopped.status_code == 200, stopped.text



def test_interrupted_page_transaction_recovers_current_and_backup(monkeypatch, tmp_path):
    paths = isolated_paths(tmp_path, monkeypatch)
    current = "<h1>Current</h1>"
    previous = "<h1>Previous</h1>"
    paths["index"].write_text(current, encoding="utf-8")
    paths["backup"].write_text(previous, encoding="utf-8")
    paths["port"].write_text("18083", encoding="ascii")

    original_write = deployments._atomic_write
    writes = 0

    def fail_once_on_backup(path, content, mode=0o600):
        nonlocal writes
        writes += 1
        if writes == 3:
            raise OSError("simulated interruption before backup replacement")
        return original_write(path, content, mode)

    monkeypatch.setattr(deployments, "_atomic_write", fail_once_on_backup)
    interrupted = client.put(API + "/content", json={"content": "<h1>New</h1>"})
    assert interrupted.status_code == 503
    assert paths["journal"].is_file()

    recovered = client.get(API + "/content")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["content"] == "<h1>New</h1>"
    assert paths["index"].read_text(encoding="utf-8") == "<h1>New</h1>"
    assert paths["backup"].read_text(encoding="utf-8") == current
    assert not paths["journal"].exists()

    rolled_back = client.post(API + "/rollback", json={"confirm": True})
    assert rolled_back.status_code == 200, rolled_back.text
    assert client.get(API + "/content").json()["content"] == current
    assert paths["backup"].read_text(encoding="utf-8") == "<h1>New</h1>"

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
