#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
mkdir -p "$RUNTIME"
if ! command -v python3 >/dev/null 2>&1; then echo "Python 3 is required. Run ./scripts/install-debian.sh first."; exit 1; fi
if [[ ! -d "$ROOT/backend/.venv" ]]; then python3 -m venv "$ROOT/backend/.venv"; fi
"$ROOT/backend/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
ENV_FILE="$ROOT/backend/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
if [[ -f "$RUNTIME/api.pid" ]] && kill -0 "$(cat "$RUNTIME/api.pid")" 2>/dev/null; then
  echo "LinuxCore API already appears to be running (PID $(cat "$RUNTIME/api.pid"))."
else
  (cd "$ROOT/backend"; nohup "$ROOT/backend/.venv/bin/uvicorn" main:app --host 127.0.0.1 --port 8000 >"$RUNTIME/api.log" 2>&1 & echo $! >"$RUNTIME/api.pid")
fi
if [[ -f "$RUNTIME/web.pid" ]] && kill -0 "$(cat "$RUNTIME/web.pid")" 2>/dev/null; then
  echo "Dashboard already appears to be running (PID $(cat "$RUNTIME/web.pid"))."
else
  nohup python3 -m http.server 8080 --directory "$ROOT/frontend" --bind 127.0.0.1 >"$RUNTIME/web.log" 2>&1 &
  echo $! >"$RUNTIME/web.pid"
fi
sleep 2
if curl --fail --silent http://127.0.0.1:8000/api/v1/health >/dev/null; then echo "API: http://127.0.0.1:8000"; else echo "API did not become ready. Check $RUNTIME/api.log"; fi
if curl --fail --silent http://127.0.0.1:8080/ >/dev/null; then echo "Website: http://127.0.0.1:8080"; else echo "Website did not become ready. Check $RUNTIME/web.log"; fi
echo "Both services bind to localhost only; they are not exposed to your network."
