#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
stop_pid() {
  local file="$1" label="$2" expected="$3"
  if [[ ! -f "$file" ]]; then echo "$label: not running"; return; fi
  local pid; pid="$(cat "$file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    local command_line
    command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    if [[ "$command_line" == *"$expected"* ]]; then
      kill "$pid" 2>/dev/null || true
      echo "$label: stop signal sent (PID $pid)"
    else
      echo "$label: PID no longer matches expected service; not killing it"
    fi
  else
    echo "$label: stale PID file cleaned"
  fi
  rm -f "$file"
}
stop_pid "$RUNTIME/web.pid" "Website" "http.server 8080"
stop_pid "$RUNTIME/api.pid" "API" "uvicorn main:app"
