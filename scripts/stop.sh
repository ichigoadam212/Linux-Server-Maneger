#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/.runtime"

stop_pid() {
  local file="$1" label="$2" expected="$3"

  if [[ ! -f "$file" ]]; then
    echo "$label: not running (no PID file)"
    return
  fi

  local pid
  pid="$(cat "$file")"
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
    echo "$label: invalid PID file; cleaning stale file"
    rm -f "$file"
    return
  fi

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$label: stale PID file cleaned"
    rm -f "$file"
    return
  fi

  local command_line
  command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  if [[ "$command_line" != *"$expected"* ]]; then
    echo "$label: PID $pid does not match the expected service; left untouched"
    echo "PID file retained for manual inspection: $file"
    return
  fi

  if kill "$pid" 2>/dev/null; then
    echo "$label: stop signal sent (PID $pid)"
    for _ in {1..10}; do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    rm -f "$file"
  else
    echo "$label: could not send stop signal; PID file retained"
  fi
}

stop_pid "$RUNTIME/web.pid" "Website" "http.server 8080"
stop_pid "$RUNTIME/api.pid" "API" "uvicorn main:app"
