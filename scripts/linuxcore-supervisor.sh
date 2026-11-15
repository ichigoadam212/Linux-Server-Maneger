#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_SCRIPT="${LINUXCORE_START_SCRIPT:-$ROOT/scripts/start.sh}"
STATUS_SCRIPT="${LINUXCORE_STATUS_SCRIPT:-$ROOT/scripts/status.sh}"
INTERVAL="${LINUXCORE_SUPERVISOR_INTERVAL:-10}"
MAX_FAILURES="${LINUXCORE_SUPERVISOR_MAX_FAILURES:-5}"

valid_positive_integer() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }
if ! valid_positive_integer "$INTERVAL" || (( INTERVAL < 5 || INTERVAL > 300 )); then
  echo "LINUXCORE_SUPERVISOR_INTERVAL must be an integer from 5 to 300 seconds." >&2
  exit 2
fi
if ! valid_positive_integer "$MAX_FAILURES" || (( MAX_FAILURES > 20 )); then
  echo "LINUXCORE_SUPERVISOR_MAX_FAILURES must be an integer from 1 to 20." >&2
  exit 2
fi
[[ -x "$START_SCRIPT" || -f "$START_SCRIPT" ]] || { echo "Start script not found: $START_SCRIPT" >&2; exit 2; }
[[ -x "$STATUS_SCRIPT" || -f "$STATUS_SCRIPT" ]] || { echo "Status script not found: $STATUS_SCRIPT" >&2; exit 2; }

stopping=false
handle_stop() { stopping=true; }
trap handle_stop INT TERM HUP

failures=0
echo "LinuxCore supervisor started (interval=${INTERVAL}s, max_failures=$MAX_FAILURES)."
while [[ "$stopping" == false ]]; do
  if bash "$START_SCRIPT" && bash "$STATUS_SCRIPT"; then
    if (( failures > 0 )); then
      echo "LinuxCore recovered; resetting failure counter."
    fi
    failures=0
  else
    failures=$((failures + 1))
    echo "LinuxCore health/start check failed ($failures/$MAX_FAILURES)." >&2
    if (( failures >= MAX_FAILURES )); then
      echo "LinuxCore supervisor reached its failure limit; exiting for the service manager to apply its restart policy." >&2
      exit 1
    fi
  fi
  sleep "$INTERVAL" &
  wait $! || true
done
echo "LinuxCore supervisor stopped."
