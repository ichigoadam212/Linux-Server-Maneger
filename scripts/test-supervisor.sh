#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
export TEST_ROOT
trap 'rm -rf "$TEST_ROOT"' EXIT
mkdir -p "$TEST_ROOT"
cp "$SOURCE_ROOT/scripts/linuxcore-supervisor.sh" "$TEST_ROOT/supervisor.sh"

cat > "$TEST_ROOT/start.sh" <<'START'
#!/usr/bin/env bash
exit 0
START
cat > "$TEST_ROOT/status.sh" <<'STATUS'
#!/usr/bin/env bash
exit 1
STATUS
cat > "$TEST_ROOT/stop.sh" <<'STOP'
#!/usr/bin/env bash
touch "$TEST_ROOT/stop-called"
STOP
chmod +x "$TEST_ROOT/start.sh" "$TEST_ROOT/status.sh" "$TEST_ROOT/stop.sh"

if LINUXCORE_START_SCRIPT="$TEST_ROOT/start.sh" \
   LINUXCORE_STATUS_SCRIPT="$TEST_ROOT/status.sh" \
   LINUXCORE_STOP_SCRIPT="$TEST_ROOT/stop.sh" \
   LINUXCORE_SUPERVISOR_INTERVAL=5 \
   LINUXCORE_SUPERVISOR_MAX_FAILURES=2 \
   bash "$TEST_ROOT/supervisor.sh" run >"$TEST_ROOT/output.log" 2>&1; then
  echo "FAIL: supervisor should exit after its configured consecutive failure limit." >&2
  exit 1
fi
[[ -f "$TEST_ROOT/stop-called" ]] || { echo "FAIL: supervisor did not invoke safe child-service cleanup." >&2; exit 1; }
grep -Fq "reached its failure limit" "$TEST_ROOT/output.log" || {
  echo "FAIL: supervisor did not report its bounded failure exit." >&2
  cat "$TEST_ROOT/output.log" >&2
  exit 1
}

if LINUXCORE_START_SCRIPT="$TEST_ROOT/start.sh" \
   LINUXCORE_STATUS_SCRIPT="$TEST_ROOT/status.sh" \
   LINUXCORE_SUPERVISOR_INTERVAL=4 \
   bash "$TEST_ROOT/supervisor.sh" run >/dev/null 2>&1; then
  echo "FAIL: supervisor accepted an interval below 5 seconds." >&2
  exit 1
fi



# A graceful signal must stop the owned LinuxCore services and exit cleanly.
cat > "$TEST_ROOT/status-ok.sh" <<'STATUS'
#!/usr/bin/env bash
touch "$TEST_ROOT/status-ok-called"
exit 0
STATUS
chmod +x "$TEST_ROOT/status-ok.sh"
rm -f "$TEST_ROOT/stop-called" "$TEST_ROOT/status-ok-called"
LINUXCORE_START_SCRIPT="$TEST_ROOT/start.sh" \
LINUXCORE_STATUS_SCRIPT="$TEST_ROOT/status-ok.sh" \
LINUXCORE_STOP_SCRIPT="$TEST_ROOT/stop.sh" \
LINUXCORE_SUPERVISOR_INTERVAL=5 \
bash "$TEST_ROOT/supervisor.sh" run >"$TEST_ROOT/graceful.log" 2>&1 &
SUPERVISOR_PID=$!
ready=false
for attempt in {1..30}; do
  if [[ -f "$TEST_ROOT/status-ok-called" ]]; then
    ready=true
    break
  fi
  sleep 0.1
done
if [[ "$ready" != true ]]; then
  kill "$SUPERVISOR_PID" 2>/dev/null || true
  wait "$SUPERVISOR_PID" 2>/dev/null || true
  echo "FAIL: supervisor did not reach its healthy monitoring loop." >&2
  cat "$TEST_ROOT/graceful.log" >&2
  exit 1
fi
kill -TERM "$SUPERVISOR_PID"
if ! wait "$SUPERVISOR_PID"; then
  echo "FAIL: supervisor did not exit cleanly after SIGTERM." >&2
  cat "$TEST_ROOT/graceful.log" >&2
  exit 1
fi
[[ -f "$TEST_ROOT/stop-called" ]] || {
  echo "FAIL: supervisor did not invoke safe cleanup after SIGTERM." >&2
  exit 1
}

echo "LinuxCore supervisor tests passed (bounded retries, interval validation and graceful shutdown)."
