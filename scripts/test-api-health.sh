#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_BIN="$(mktemp -d)"
export TEST_BIN
trap 'rm -rf "$TEST_BIN"' EXIT

cat > "$TEST_BIN/curl" <<'CURL'
#!/usr/bin/env bash
case "${FAKE_CURL_MODE:-healthy}" in
  healthy) printf '%s\n200' '{"status":"ok","service":"linuxcore-api"}' ;;
  wrong-service) printf '%s\n200' '{"status":"ok","service":"other-api"}' ;;
  wrong-status) printf '%s\n200' '{"status":"degraded","service":"linuxcore-api"}' ;;
  malformed) printf '%s\n200' 'not-json' ;;
  not-found) printf '%s\n404' '{"detail":"not found"}' ;;
  server-error) printf '%s\n500' '{"detail":"internal error"}' ;;
  retry-then-healthy)
    count="$(cat "$TEST_BIN/curl-count" 2>/dev/null || printf '0')"
    count=$((count + 1))
    printf '%s' "$count" > "$TEST_BIN/curl-count"
    if [[ "$count" -lt 3 ]]; then exit 7; fi
    printf '%s\n200' '{"status":"ok","service":"linuxcore-api"}'
    ;;
  unavailable)
    count="$(cat "$TEST_BIN/curl-count" 2>/dev/null || printf '0')"
    count=$((count + 1))
    printf '%s' "$count" > "$TEST_BIN/curl-count"
    exit 7
    ;;
  *) exit 64 ;;
esac
CURL
chmod +x "$TEST_BIN/curl"
PATH="$TEST_BIN:$PATH"
export PATH
API_URL="http://127.0.0.1:8000/api/v1/health"
export API_URL
LINUXCORE_ROOT="$TEST_BIN/empty-root"
mkdir -p "$LINUXCORE_ROOT/backend"
export LINUXCORE_ROOT
unset LINUXCORE_ACCESS_TOKEN || true

# Avoid delays while keeping the production retry logic unchanged.
sleep() { :; }
source "$ROOT/scripts/lib/api-health.sh"

assert_status() {
  local expected="$1"
  shift
  local actual=0
  "$@" || actual=$?
  if [[ "$actual" -ne "$expected" ]]; then
    printf 'FAIL: %s returned %s; expected %s\n' "$*" "$actual" "$expected" >&2
    return 1
  fi
}

assert_count() {
  local expected="$1"
  local actual
  actual="$(cat "$TEST_BIN/curl-count" 2>/dev/null || printf '0')"
  if [[ "$actual" -ne "$expected" ]]; then
    printf 'FAIL: curl called %s times; expected %s\n' "$actual" "$expected" >&2
    return 1
  fi
}

FAKE_CURL_MODE=healthy assert_status 0 api_is_linuxcore
FAKE_CURL_MODE=wrong-service assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=wrong-status assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=malformed assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=not-found assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=server-error assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=unavailable assert_status 1 api_is_linuxcore

FAKE_CURL_MODE=healthy assert_status 0 wait_for_api 1
FAKE_CURL_MODE=wrong-service assert_status 2 wait_for_api 1
FAKE_CURL_MODE=not-found assert_status 2 wait_for_api 1
rm -f "$TEST_BIN/curl-count"
FAKE_CURL_MODE=unavailable assert_status 1 wait_for_api 3
assert_count 3

rm -f "$TEST_BIN/curl-count"
FAKE_CURL_MODE=retry-then-healthy assert_status 0 wait_for_api 3
assert_count 3

printf '%s\n' 'Startup API identity tests passed (12 cases).'
