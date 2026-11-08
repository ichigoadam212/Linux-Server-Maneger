#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/backend/.venv"
failed=0
printf '%s\n' "LinuxCore environment check"
printf 'Architecture: '; uname -m
printf 'Kernel: '; uname -sr
if ! command -v python3 >/dev/null 2>&1; then echo "Python: missing"; exit 1; fi
printf 'Python: '; python3 --version
if command -v git >/dev/null 2>&1; then printf 'Git: '; git --version; else echo "Git: not installed"; fi
if command -v curl >/dev/null 2>&1; then echo "HTTP client: curl available"; else echo "HTTP client: curl missing"; failed=1; fi
if command -v apt-get >/dev/null 2>&1; then echo "Package manager: apt"; else echo "Package manager: not apt"; fi
if [[ -d "$ROOT/frontend" && -f "$ROOT/backend/main.py" ]]; then echo "Project files: OK"; else echo "Project files: incomplete"; exit 1; fi
if [[ -x "$VENV/bin/python" ]]; then
  if "$VENV/bin/python" -c "import fastapi, uvicorn, psutil, dotenv" >/dev/null 2>&1; then echo "Backend environment: dependencies OK"; else echo "Backend environment: dependencies missing or incomplete"; failed=1; fi
else
  echo "Backend environment: virtual environment not created yet"
fi
if python3 -m pip --version >/dev/null 2>&1; then echo "System pip: available"; else echo "System pip: unavailable (needed only to bootstrap a new venv)"; fi
if [[ "$(uname -m)" != "aarch64" && "$(uname -m)" != "arm64" && "$(uname -m)" != "x86_64" ]]; then echo "Warning: architecture is not one of the expected ARM64/x86_64 targets."; fi
echo "Check complete. This script does not change the system."
exit "$failed"
