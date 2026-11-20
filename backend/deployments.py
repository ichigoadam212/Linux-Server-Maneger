"""Rootless static-site deployment controls for LinuxCore.

The feature owns a single Nginx static-site container and named volume. It never
runs a shell, accepts an image name, or binds the site to a public interface.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/apps/static-site", tags=["apps"])
APP_ID = "linuxcore-static-site"
CONTAINER_NAME = "linuxcore-static-site"
VOLUME_NAME = "linuxcore-static-site-data"
IMAGE = "docker.io/library/nginx:alpine"
MANAGED_LABEL = "io.linuxcore.managed=static-site"
APP_LABEL = f"io.linuxcore.app={APP_ID}"
DEFAULT_HTML = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>LinuxCore hosted site</title><h1>Your site is running</h1>
<p>Edit this page from LinuxCore's application manager.</p>
</html>
"""
HEALTH_COMMAND = "wget -q -O /dev/null http://127.0.0.1/ || exit 1"


class DeployRequest(BaseModel):
    host_port: int = Field(ge=1024, le=65535)


class ContentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=65536)


class ActionRequest(BaseModel):
    action: Literal["start", "stop", "restart"]


def _run(argv: list[str], timeout: int = 20) -> dict:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return {"returncode": result.returncode, "stdout": result.stdout[-12000:], "stderr": result.stderr[-3000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": 127, "stdout": "", "stderr": str(exc)[:1000]}


def _runtime():
    if os.geteuid() == 0:
        return None
    podman = shutil.which("podman")
    if podman and _run([podman, "info", "--format", "json"], 8)["returncode"] == 0:
        return "podman", podman
    docker = shutil.which("docker")
    if docker:
        probe = _run([docker, "info", "--format", "{{json .SecurityOptions}}"], 8)
        if probe["returncode"] == 0 and "rootless" in probe["stdout"].lower():
            return "docker", docker
    return None


def _require_runtime():
    runtime = _runtime()
    if not runtime:
        raise HTTPException(status_code=503, detail="Static-site deployment needs accessible rootless Podman or rootless Docker; rootful runtimes are not supported.")
    return runtime


def _paths():
    state_dir = Path(__file__).resolve().parent.parent / ".runtime" / "deployments"
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        state_dir.chmod(0o700)
    except OSError:
        pass
    return state_dir, state_dir / "static-site.previous.html"


def _volume_path(executable: str, runtime_name: str, volume_name: str) -> Path:
    result = _run([executable, "volume", "inspect", volume_name], 8)
    if result["returncode"] != 0:
        raise HTTPException(status_code=502, detail="Could not inspect the LinuxCore site data volume.")
    try:
        info = json.loads(result["stdout"])[0]
        mountpoint = Path(info["Mountpoint"])
        labels = info.get("Labels") or info.get("labels") or {}
        if labels.get("io.linuxcore.app") != APP_ID:
            raise ValueError("volume is not owned by LinuxCore")
        if not mountpoint.is_absolute() or not mountpoint.is_dir() or mountpoint.is_symlink():
            raise ValueError("unsafe volume mountpoint")
        return mountpoint
    except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="The container runtime returned an invalid site volume path.")


def _atomic_write(path: Path, content: str):
    tmp = path.with_name(path.name + ".linuxcore-tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _site_status(runtime_name: str, executable: str):
    result = _run([executable, "inspect", CONTAINER_NAME], 8)
    if result["returncode"] != 0:
        return {"deployed": False}
    try:
        raw = json.loads(result["stdout"])
        item = raw[0] if isinstance(raw, list) else raw
        labels = item.get("Config", {}).get("Labels") or item.get("Config", {}).get("labels") or {}
        if labels.get("io.linuxcore.app") != APP_ID:
            return {"deployed": False, "conflict": True, "reason": "A container with LinuxCore's site name exists but is not owned by this app."}
        state = item.get("State") or item.get("state") or {}
        status = state.get("Status") or state.get("status") or "unknown"
        health = state.get("Health") or state.get("health") or {}
        health_status = health.get("Status") or health.get("status") or "starting"
        ports = item.get("NetworkSettings", {}).get("Ports") or item.get("NetworkSettings", {}).get("ports") or {}
        host_port = None
        bindings = ports.get("80/tcp") or []
        if bindings:
            host_port = bindings[0].get("HostPort") or bindings[0].get("hostPort")
        return {"deployed": True, "name": CONTAINER_NAME, "image": IMAGE, "status": status,
                "health": health_status, "host_port": int(host_port) if host_port else None,
                "url": f"http://127.0.0.1:{host_port}" if host_port else None,
                "volume": VOLUME_NAME, "runtime": runtime_name}
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="Could not read the static-site container status.")


@router.get("")
def get_site():
    runtime = _require_runtime()
    return _site_status(*runtime)


@router.post("/deploy")
def deploy_site(request: DeployRequest):
    runtime_name, executable = _require_runtime()
    current = _site_status(runtime_name, executable)
    if current.get("deployed"):
        raise HTTPException(status_code=409, detail="The LinuxCore static site is already deployed.")
    if current.get("conflict"):
        raise HTTPException(status_code=409, detail=current["reason"])
    state_dir, backup = _paths()
    volume = _run([executable, "volume", "create", "--label", APP_LABEL, VOLUME_NAME], 15)
    if volume["returncode"] != 0:
        raise HTTPException(status_code=502, detail="Could not create the persistent site volume.")
    mountpoint = _volume_path(executable, runtime_name, VOLUME_NAME)
    index_path = mountpoint / "index.html"
    _atomic_write(index_path, DEFAULT_HTML)
    command = [
        executable, "run", "--detach", "--name", CONTAINER_NAME,
        "--label", MANAGED_LABEL, "--label", APP_LABEL,
        "--publish", f"127.0.0.1:{request.host_port}:80",
        "--volume", f"{VOLUME_NAME}:/usr/share/nginx/html:ro",
        "--restart", "unless-stopped",
        "--health-cmd", HEALTH_COMMAND, "--health-interval", "30s",
        "--health-timeout", "5s", "--health-retries", "3",
        IMAGE,
    ]
    result = _run(command, 90)
    if result["returncode"] != 0:
        # The named volume is intentionally retained if deployment fails, so a retry
        # does not discard the initial content or any data already written.
        raise HTTPException(status_code=502, detail=result["stderr"] or "Could not start the static-site container.")
    _atomic_write(backup, DEFAULT_HTML)
    return _site_status(runtime_name, executable)


@router.get("/content")
def get_site_content():
    runtime_name, executable = _require_runtime()
    status = _site_status(runtime_name, executable)
    if not status.get("deployed"):
        raise HTTPException(status_code=404, detail="Deploy the LinuxCore static site before reading its page.")
    mountpoint = _volume_path(executable, runtime_name, VOLUME_NAME)
    try:
        page = (mountpoint / "index.html").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise HTTPException(status_code=502, detail="Could not read the current site page.")
    return {"content": page, "limit": 65536}


@router.put("/content")
def update_site_content(request: ContentRequest):
    runtime_name, executable = _require_runtime()
    status = _site_status(runtime_name, executable)
    if not status.get("deployed"):
        raise HTTPException(status_code=404, detail="Deploy the LinuxCore static site before editing it.")
    mountpoint = _volume_path(executable, runtime_name, VOLUME_NAME)
    index_path = mountpoint / "index.html"
    backup = _paths()[2]
    try:
        old_content = index_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise HTTPException(status_code=502, detail="Could not read the current site page for rollback.")
    _atomic_write(backup, old_content)
    _atomic_write(index_path, request.content)
    return {"ok": True, "rollback_available": True, "url": status.get("url")}


@router.post("/rollback")
def rollback_site():
    runtime_name, executable = _require_runtime()
    status = _site_status(runtime_name, executable)
    if not status.get("deployed"):
        raise HTTPException(status_code=404, detail="Deploy the LinuxCore static site before rolling it back.")
    mountpoint = _volume_path(executable, runtime_name, VOLUME_NAME)
    backup = _paths()[2]
    try:
        previous = backup.read_text(encoding="utf-8")
        current = (mountpoint / "index.html").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise HTTPException(status_code=404, detail="No valid previous site page is available.")
    _atomic_write(backup, current)
    _atomic_write(mountpoint / "index.html", previous)
    return {"ok": True, "rollback_available": True, "url": status.get("url")}


@router.get("/logs")
def site_logs():
    runtime_name, executable = _require_runtime()
    status = _site_status(runtime_name, executable)
    if not status.get("deployed"):
        raise HTTPException(status_code=404, detail="The LinuxCore static site is not deployed.")
    result = _run([executable, "logs", "--tail", "200", CONTAINER_NAME], 10)
    if result["returncode"] != 0:
        raise HTTPException(status_code=502, detail=result["stderr"] or "Could not read site logs.")
    return {"name": CONTAINER_NAME, "lines": result["stdout"], "limit": 200}


@router.post("/action")
def site_action(request: ActionRequest):
    runtime_name, executable = _require_runtime()
    status = _site_status(runtime_name, executable)
    if not status.get("deployed"):
        raise HTTPException(status_code=404, detail="The LinuxCore static site is not deployed.")
    result = _run([executable, request.action, CONTAINER_NAME], 30)
    if result["returncode"] != 0:
        raise HTTPException(status_code=502, detail=result["stderr"] or "Site action failed.")
    return {"ok": True, "action": request.action, **_site_status(runtime_name, executable)}
