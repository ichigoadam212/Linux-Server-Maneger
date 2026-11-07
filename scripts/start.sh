#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
VENV="$ROOT/backend/.venv"
API_URL="http://127.0.0.1:8000/api/v1/health"
WEB_URL="http://127.0.0.1:8080/"

mkdir -p "$RUNTIME"

for command_name in python3 curl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command is missing: $command_name"
    exit 1
  fi
done

if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi

if ! "$VENV/bin/python" -c "import fastapi, uvicorn, psutil, dotenv" >/dev/null 2>&1; then
  if [[ ! -x "$VENV/bin/pip" ]]; then
    echo "Backend dependencies are missing and pip is unavailable in the virtual environment."
    echo "Install the backend requirements once, then rerun this script."
    exit 1
  fi
  "$VENV/bin/pip" install -r "$ROOT/backend/requirements.txt"
fi

wait_for_url() {
  local url="$1"
  local attempts="${2:-20}"
  for ((attempt=1; attempt<=attempts; attempt++)); do
    if curl --fail --silent --max-time 1 "$url" >/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

if curl --fail --silent --max-time 1 "$API_URL" >/dev/null; then
  echo "LinuxCore API is already responding."
else
  (
    cd "$ROOT/backend"
    nohup "$VENV/bin/uvicorn" main:app --host 127.0.0.1 --port 8000 >"$RUNTIME/api.log" 2>&1 &
    echo $! >"$RUNTIME/api.pid"
  )
fi

if curl --fail --silent --max-time 1 "$WEB_URL" >/dev/null; then
  echo "Dashboard is already responding."
else
  nohup python3 -m http.server 8080 --directory "$ROOT/frontend" --bind 127.0.0.1 >"$RUNTIME/web.log" 2>&1 &
  echo $! >"$RUNTIME/web.pid"
fi

api_ready=false
web_ready=false
if wait_for_url "$API_URL" 20; then
  api_ready=true
  echo "API: http://127.0.0.1:8000"
else
  echo "API did not become ready. Check $RUNTIME/api.log"
fi

if wait_for_url "$WEB_URL" 20; then
  web_ready=true
  echo "Website: http://127.0.0.1:8080"
else
  echo "Website did not become ready. Check $RUNTIME/web.log"
fi

echo "Both services bind to localhost only; they are not exposed to your network."
[[ "$api_ready" == true && "$web_ready" == true ]]
