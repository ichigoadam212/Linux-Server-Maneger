#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap '[[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true; [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true; [[ -n "${FOREIGN_PID:-}" ]] && kill "$FOREIGN_PID" 2>/dev/null || true; rm -rf "$TEST_ROOT"' EXIT
mkdir -p "$TEST_ROOT/bin" "$TEST_ROOT/repo/scripts" "$TEST_ROOT/repo/.runtime"
cp "$SOURCE_ROOT/scripts/stop.sh" "$TEST_ROOT/repo/scripts/stop.sh"

cat > "$TEST_ROOT/bin/ps" <<'PS'
#!/usr/bin/env bash
pid="$2"
if [[ "$pid" == "${FAKE_WEB_PID:-}" ]]; then
  echo "python3 /repo/scripts/local-web.py --directory /repo/frontend --bind 127.0.0.1 --port 8080"
elif [[ "$pid" == "${FAKE_API_PID:-}" ]]; then
  echo "uvicorn main:app --host 127.0.0.1 --port 8000"
else
  echo "unrelated process"
fi
PS
chmod +x "$TEST_ROOT/bin/ps"
export PATH="$TEST_ROOT/bin:$PATH"

fail() { echo "FAIL: $1" >&2; exit 1; }
start_detached_sleep() { bash -c 'sleep 30 >/dev/null 2>&1 & echo $! > "$1"' _ "$1"; }

# Matching LinuxCore-owned PIDs are stopped and their PID files removed.
start_detached_sleep "$TEST_ROOT/web.pid"
start_detached_sleep "$TEST_ROOT/api.pid"
WEB_PID="$(cat "$TEST_ROOT/web.pid")"
API_PID="$(cat "$TEST_ROOT/api.pid")"
export FAKE_WEB_PID="$WEB_PID" FAKE_API_PID="$API_PID"
printf '%s\n' "$WEB_PID" > "$TEST_ROOT/repo/.runtime/web.pid"
printf '%s\n' "$API_PID" > "$TEST_ROOT/repo/.runtime/api.pid"
bash "$TEST_ROOT/repo/scripts/stop.sh" > "$TEST_ROOT/matching.log"
wait "$WEB_PID" 2>/dev/null || true
wait "$API_PID" 2>/dev/null || true
unset WEB_PID API_PID FAKE_WEB_PID FAKE_API_PID
[[ ! -e "$TEST_ROOT/repo/.runtime/web.pid" ]] || fail "web PID file remained after stop"
[[ ! -e "$TEST_ROOT/repo/.runtime/api.pid" ]] || fail "API PID file remained after stop"

# A PID that does not match the expected LinuxCore command is never signalled.
start_detached_sleep "$TEST_ROOT/foreign.pid"
FOREIGN_PID="$(cat "$TEST_ROOT/foreign.pid")"
printf '%s\n' "$FOREIGN_PID" > "$TEST_ROOT/repo/.runtime/web.pid"
if bash "$TEST_ROOT/repo/scripts/stop.sh" > "$TEST_ROOT/mismatch.log" 2>&1; then
  fail "mismatched PID was reported as successfully stopped"
fi
kill -0 "$FOREIGN_PID" 2>/dev/null || fail "mismatched process was terminated"
[[ -f "$TEST_ROOT/repo/.runtime/web.pid" ]] || fail "mismatched PID file was removed"
kill "$FOREIGN_PID" 2>/dev/null || true
wait "$FOREIGN_PID" 2>/dev/null || true
unset FOREIGN_PID

# Invalid and stale PID files are safely cleaned without signalling a process.
printf 'not-a-pid\n' > "$TEST_ROOT/repo/.runtime/web.pid"
bash "$TEST_ROOT/repo/scripts/stop.sh" > /dev/null
[[ ! -e "$TEST_ROOT/repo/.runtime/web.pid" ]] || fail "invalid PID file was not cleaned"
printf '99999999\n' > "$TEST_ROOT/repo/.runtime/api.pid"
bash "$TEST_ROOT/repo/scripts/stop.sh" > /dev/null
[[ ! -e "$TEST_ROOT/repo/.runtime/api.pid" ]] || fail "stale PID file was not cleaned"

echo "LinuxCore stop lifecycle tests passed (matching, mismatched, invalid and stale PID cases)."
