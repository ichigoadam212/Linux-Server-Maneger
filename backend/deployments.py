"""Loopback-only local static-site deployment controls for LinuxCore."""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Literal

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/apps/static-site", tags=["apps"])
MAX_PAGE_BYTES = 65536
MAX_LOG_BYTES = 262144
DEFAULT_HTML = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>LinuxCore hosted site</title><h1>Your site is running</h1>
<p>Edit this page from LinuxCore's application manager.</p>
</html>
"""
STATE_LOCK = threading.RLock()
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "static_site.py"


class DeployRequest(BaseModel):
    host_port: int = Field(ge=1024, le=65535)


class ContentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=65536)


class ActionRequest(BaseModel):
    action: Literal["start", "stop", "restart"]


def _private_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700, exist_ok=True)
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise HTTPException(status_code=500, detail="Static-site state directory is not a safe directory.")
        if info.st_uid != os.getuid():
            raise HTTPException(status_code=500, detail="Static-site state directory is owned by another user.")
        path.chmod(0o700)
    except HTTPException:
        raise
    except OSError:
        raise HTTPException(status_code=500, detail="Could not create private static-site state.")


def _paths():
    root = Path(__file__).resolve().parent.parent
    runtime_dir = root / ".runtime"
    state_dir = runtime_dir / "deployments"
    site_dir = state_dir / "static-site"
    _private_directory(runtime_dir)
    _private_directory(state_dir)
    _private_directory(site_dir)
    return {
        "state": state_dir,
        "site": site_dir,
        "index": site_dir / "index.html",
        "backup": state_dir / "static-site.previous.html",
        "pid": state_dir / "static-site.pid",
        "port": state_dir / "static-site.port",
        "log": site_dir / "static-site.log",
        "script": SCRIPT_PATH,
    }


def _read_bytes(path: Path, maximum: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError("file is not regular or exceeds its limit")
        with os.fdopen(fd, "rb", closefd=False) as source:
            data = source.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("file exceeds its limit")
        return data
    finally:
        os.close(fd)


def _read_text(path: Path, maximum: int) -> str:
    return _read_bytes(path, maximum).decode("utf-8")


def _atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    parent = path.parent
    fd, temp_name = tempfile.mkstemp(prefix=".linuxcore-", dir=parent)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_path, path)
        try:
            directory_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _remove_metadata(path: Path) -> None:
    try:
        info = path.lstat()
        if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _read_port(paths) -> int | None:
    try:
        port = int(_read_text(paths["port"], 16).strip())
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, ValueError):
        raise HTTPException(status_code=409, detail="Static-site port metadata is invalid.")
    if not 1024 <= port <= 65535:
        raise HTTPException(status_code=409, detail="Static-site port metadata is invalid.")
    return port


def _read_process_metadata(paths):
    try:
        value = json.loads(_read_text(paths["pid"], 2048))
        pid = value["pid"]
        created = value["created"]
        if isinstance(pid, bool) or not isinstance(pid, int) or pid < 2:
            raise ValueError
        if isinstance(created, bool) or not isinstance(created, (float, int)) or created <= 0:
            raise ValueError
        return {"pid": pid, "created": float(created)}
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _same_process(metadata, port: int, site_dir: Path):
    if not metadata:
        return None
    try:
        process = psutil.Process(metadata["pid"])
        if abs(process.create_time() - metadata["created"]) > 0.02:
            return None
        command = process.cmdline()
        expected = [
            str(Path(sys.executable).resolve()),
            str(SCRIPT_PATH.resolve()),
            "run", "--port", str(port), "--site-dir", str(site_dir),
        ]
        if len(command) != len(expected):
            return None
        if Path(command[0]).resolve() != Path(expected[0]).resolve():
            return None
        if Path(command[1]).resolve() != Path(expected[1]).resolve():
            return None
        if command[2:] != expected[2:]:
            return None
        return process
    except (OSError, psutil.Error, IndexError, RuntimeError):
        return None


def _health_check(port: int, timeout: float = 0.35) -> bool:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        connection.request("GET", "/healthz", headers={"Host": "127.0.0.1"})
        response = connection.getresponse()
        body = response.read(64)
        return response.status == 200 and body == b"linuxcore-site-ok"
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def _start_server(paths, port: int):
    if not paths["script"].is_file() or paths["script"].is_symlink():
        raise HTTPException(status_code=503, detail="The fixed static-site server script is unavailable.")
    if not paths["site"].is_dir() or paths["site"].is_symlink():
        raise HTTPException(status_code=503, detail="The private static-site directory is unavailable.")
    old_metadata = _read_process_metadata(paths)
    existing = _same_process(old_metadata, port, paths["site"])
    if existing is not None:
        if _health_check(port):
            return
        _stop_server(paths, port)
    command = [
        str(Path(sys.executable).resolve()), str(paths["script"].resolve()),
        "run", "--port", str(port), "--site-dir", str(paths["site"].resolve()),
    ]
    env = {"PATH": os.defpath, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
            cwd=str(paths["site"]), env=env,
        )
    except OSError:
        raise HTTPException(status_code=503, detail="Could not start the local static-site server.")
    try:
        created = psutil.Process(process.pid).create_time()
    except psutil.Error:
        try:
            process.terminate()
        except OSError:
            pass
        raise HTTPException(status_code=503, detail="Could not verify the local static-site process.")
    metadata = {"pid": process.pid, "created": created}
    _atomic_write(paths["pid"], json.dumps(metadata).encode("ascii"))
    _atomic_write(paths["port"], str(port).encode("ascii"))

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            _remove_metadata(paths["pid"])
            raise HTTPException(status_code=409, detail="The selected site port is unavailable.")
        if _health_check(port):
            return
        time.sleep(0.1)
    _stop_server(paths, port)
    raise HTTPException(status_code=503, detail="The local site server did not become healthy in time.")


def _stop_server(paths, port: int) -> None:
    metadata = _read_process_metadata(paths)
    process = _same_process(metadata, port, paths["site"])
    if process is None:
        _remove_metadata(paths["pid"])
        return
    try:
        process.terminate()
        process.wait(timeout=3)
    except psutil.TimeoutExpired:
        # Revalidate both PID creation time and full argv before the final signal.
        process = _same_process(metadata, port, paths["site"])
        if process is None:
            _remove_metadata(paths["pid"])
            return
        try:
            process.kill()
            process.wait(timeout=2)
        except psutil.TimeoutExpired:
            raise HTTPException(status_code=503, detail="The static-site process did not stop.")
        except psutil.Error:
            raise HTTPException(status_code=503, detail="Could not stop the static-site process.")
    except psutil.NoSuchProcess:
        pass
    except psutil.AccessDenied:
        raise HTTPException(status_code=503, detail="Permission was denied while stopping the static-site process.")
    _remove_metadata(paths["pid"])


def _site_status(paths):
    port = _read_port(paths)
    try:
        _read_bytes(paths["index"], MAX_PAGE_BYTES)
    except FileNotFoundError:
        return {"deployed": False}
    except (OSError, UnicodeError, ValueError):
        return {"deployed": False, "conflict": True,
                "reason": "The site page is not a safe regular file; no process was started or stopped."}
    if port is None:
        return {"deployed": False, "conflict": True,
                "reason": "The site port is missing; deploy the site again after reviewing its files."}
    metadata = _read_process_metadata(paths)
    process = _same_process(metadata, port, paths["site"])
    running = process is not None
    healthy = _health_check(port) if running else False
    return {
        "deployed": True,
        "name": "LinuxCore static site",
        "runtime": "python",
        "status": "running" if running else "stopped",
        "health": "healthy" if healthy else ("unhealthy" if running else "stopped"),
        "host_port": port,
        "url": f"http://127.0.0.1:{port}",
        "pid": metadata["pid"] if running and metadata else None,
    }


@router.get("")
def get_site():
    with STATE_LOCK:
        return _site_status(_paths())


@router.post("/deploy")
def deploy_site(request: DeployRequest):
    with STATE_LOCK:
        paths = _paths()
        current = _site_status(paths)
        if current.get("deployed"):
            raise HTTPException(status_code=409, detail="The LinuxCore static site is already deployed.")
        if current.get("conflict"):
            raise HTTPException(status_code=409, detail=current["reason"])
        if request.host_port < 1024 or request.host_port > 65535:
            raise HTTPException(status_code=422, detail="Port must be between 1024 and 65535.")
        _atomic_write(paths["index"], DEFAULT_HTML.encode("utf-8"))
        _atomic_write(paths["backup"], DEFAULT_HTML.encode("utf-8"))
        _atomic_write(paths["port"], str(request.host_port).encode("ascii"))
        _start_server(paths, request.host_port)
        return _site_status(paths)


@router.get("/content")
def get_site_content():
    with STATE_LOCK:
        paths = _paths()
        status = _site_status(paths)
        if not status.get("deployed"):
            raise HTTPException(status_code=404, detail="Deploy the LinuxCore static site before reading its page.")
        try:
            page = _read_text(paths["index"], MAX_PAGE_BYTES)
        except (OSError, UnicodeError, ValueError):
            raise HTTPException(status_code=409, detail="The current site page is not a valid bounded UTF-8 file.")
        return {"content": page, "limit": MAX_PAGE_BYTES}


@router.put("/content")
def update_site_content(request: ContentRequest):
    if len(request.content.encode("utf-8")) > MAX_PAGE_BYTES:
        raise HTTPException(status_code=422, detail="Page content exceeds the 64 KiB UTF-8 limit.")
    with STATE_LOCK:
        paths = _paths()
        status = _site_status(paths)
        if not status.get("deployed"):
            raise HTTPException(status_code=404, detail="Deploy the LinuxCore static site before editing it.")
        try:
            previous = _read_bytes(paths["index"], MAX_PAGE_BYTES)
        except (OSError, ValueError):
            raise HTTPException(status_code=409, detail="The current site page is not a safe regular file.")
        _atomic_write(paths["backup"], previous)
        _atomic_write(paths["index"], request.content.encode("utf-8"))
        return {"ok": True, "rollback_available": True, "url": status["url"]}


@router.post("/rollback")
def rollback_site():
    with STATE_LOCK:
        paths = _paths()
        status = _site_status(paths)
        if not status.get("deployed"):
            raise HTTPException(status_code=404, detail="Deploy the LinuxCore static site before rolling it back.")
        try:
            previous = _read_bytes(paths["backup"], MAX_PAGE_BYTES)
            current = _read_bytes(paths["index"], MAX_PAGE_BYTES)
        except (OSError, ValueError):
            raise HTTPException(status_code=404, detail="No valid previous site page is available.")
        _atomic_write(paths["backup"], current)
        _atomic_write(paths["index"], previous)
        return {"ok": True, "rollback_available": True, "url": status["url"]}


@router.get("/logs")
def site_logs():
    with STATE_LOCK:
        paths = _paths()
        status = _site_status(paths)
        if not status.get("deployed"):
            raise HTTPException(status_code=404, detail="The LinuxCore static site is not deployed.")
        try:
            raw = _read_bytes(paths["log"], MAX_LOG_BYTES)
        except FileNotFoundError:
            raw = b""
        except (OSError, ValueError):
            raise HTTPException(status_code=409, detail="The static-site log is not a safe bounded file.")
        lines = "\n".join(raw.decode("utf-8", "replace").splitlines()[-200:])[-12000:]
        return {"name": "LinuxCore static site", "lines": lines, "limit": 200}


@router.post("/action")
def site_action(request: ActionRequest):
    with STATE_LOCK:
        paths = _paths()
        status = _site_status(paths)
        if not status.get("deployed"):
            raise HTTPException(status_code=404, detail="The LinuxCore static site is not deployed.")
        port = status["host_port"]
        if request.action == "stop":
            _stop_server(paths, port)
        elif request.action == "restart":
            _stop_server(paths, port)
            _start_server(paths, port)
        else:
            _start_server(paths, port)
        return {"ok": True, "action": request.action, **_site_status(paths)}
