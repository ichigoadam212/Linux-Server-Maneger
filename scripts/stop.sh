#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
stop_pid() {
  local file="$1" label="$2"
  if [[ ! -f "$file" ]]; then echo "$label: not running"; return; fi
  local pid; pid="$(cat "$file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    echo "$label: stop signal sent (PID $pid)"
  else
    echo "$label: stale PID file cleaned"
  fi
  rm -f "$file"
}
stop_pid "$RUNTIME/web.pid" "Website"
stop_pid "$RUNTIME/api.pid" "API"
