from datetime import datetime, timezone
import platform
import shutil
import time

import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LinuxCore Server Manager API", version="0.2.0")

# Local development only. Remote access requires authentication, TLS and auditing.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept"],
)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@app.get("/")
def root():
    return {
        "name": "LinuxCore Server Manager API",
        "version": "0.2.0",
        "mode": "read-only",
        "docs": "/docs",
    }


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "service": "linuxcore-api",
        "mode": "read-only",
        "timestamp": timestamp(),
    }


@app.get("/api/v1/metrics")
def metrics():
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    net = psutil.net_io_counters()
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "uptime_seconds": max(0, int(time.time() - psutil.boot_time())),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "cpu_count": psutil.cpu_count() or 1,
        "memory_percent": memory.percent,
        "memory_used_gb": round((memory.total - memory.available) / (1024 ** 3), 2),
        "memory_total_gb": round(memory.total / (1024 ** 3), 2),
        "disk_percent": round(disk.used / disk.total * 100, 1) if disk.total else 0,
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "network_bytes_sent": net.bytes_sent,
        "network_bytes_recv": net.bytes_recv,
        "timestamp": timestamp(),
    }


@app.get("/api/v1/storage")
def storage():
    items = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        items.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "filesystem": part.fstype,
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "percent": usage.percent,
        })
    return {"items": items, "timestamp": timestamp()}


@app.get("/api/v1/processes")
def processes():
    # Read-only process inventory. Command lines and environment variables are
    # intentionally excluded because they may contain private information.
    items = []
    for proc in psutil.process_iter(["pid", "name", "status", "username", "memory_percent"]):
        try:
            info = proc.info
            items.append({
                "pid": info.get("pid"),
                "name": info.get("name") or "unknown",
                "status": info.get("status") or "unknown",
                "user": info.get("username") or "unknown",
                "memory_percent": round(info.get("memory_percent") or 0, 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    items.sort(key=lambda item: item["memory_percent"], reverse=True)
    return {"items": items[:30], "total_visible": len(items), "timestamp": timestamp()}


@app.get("/api/v1/network")
def network():
    counters = psutil.net_io_counters(pernic=True) or {}
    interfaces = []
    for name, counter in counters.items():
        interfaces.append({
            "name": name,
            "bytes_sent": counter.bytes_sent,
            "bytes_recv": counter.bytes_recv,
            "packets_sent": counter.packets_sent,
            "packets_recv": counter.packets_recv,
            "is_up": bool((psutil.net_if_stats().get(name) or {}).isup),
        })
    return {"interfaces": interfaces, "timestamp": timestamp()}
