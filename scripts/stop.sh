#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
stop_pid() {
  local file="$1" label="$2" expected="$3"
  if [[ ! -f "$file" ]]; then echo "$label: not running (no PID file)"; return 0; fi
  local pid
  pid="$(cat "$file")"
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then echo "$label: invalid PID file; cleaning stale file"; rm -f "$file"; return 0; fi
  if ! kill -0 "$pid" 2>/dev/null; then echo "$label: stale PID file cleaned"; rm -f "$file"; return 0; fi
  local command_line
  command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  if [[ "$command_line" != *"$expected"* ]]; then
    echo "$label: PID $pid does not match the expected service; left untouched"
    echo "PID file retained for manual inspection: $file"
    return 1
  fi
  if ! kill "$pid" 2>/dev/null; then echo "$label: could not send stop signal; PID file retained"; return 1; fi
  for _ in {1..15}; do
    if ! kill -0 "$pid" 2>/dev/null; then rm -f "$file"; echo "$label: stopped (PID $pid)"; return 0; fi
    sleep 0.2
  done
  echo "$label: still running after stop signal; PID file retained"
  return 1
}
result=0
stop_pid "$RUNTIME/web.pid" "Website" "http.server 8080" || result=1
stop_pid "$RUNTIME/api.pid" "API" "uvicorn main:app" || result=1
exit "$result"
