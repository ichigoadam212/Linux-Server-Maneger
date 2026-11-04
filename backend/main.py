from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psutil
import shutil
import platform
from datetime import datetime, timezone

app = FastAPI(title="LinuxCore Server Manager API", version="0.1.0")

# Development only: the dashboard is intended to be served locally alongside this API.
# Do not expose this API to the internet before adding authentication and TLS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "linuxcore-api", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/metrics")
def metrics():
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "cpu_count": psutil.cpu_count() or 1,
        "memory_percent": memory.percent,
        "memory_used_gb": round((memory.total - memory.available) / (1024 ** 3), 1),
        "memory_total_gb": round(memory.total / (1024 ** 3), 1),
        "disk_percent": round(disk.used / disk.total * 100, 1) if disk.total else 0,
        "disk_used_gb": round(disk.used / (1024 ** 3), 1),
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/")
def root():
    return {"name": "LinuxCore Server Manager API", "version": "0.1.0", "docs": "/docs"}
