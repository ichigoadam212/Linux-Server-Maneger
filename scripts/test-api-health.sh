#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_BIN="$(mktemp -d)"
trap 'rm -rf "$TEST_BIN"' EXIT

cat > "$TEST_BIN/curl" <<'CURL'
#!/usr/bin/env bash
case "${FAKE_CURL_MODE:-healthy}" in
  healthy) printf '%s' '{"status":"ok","service":"linuxcore-api"}' ;;
  wrong-service) printf '%s' '{"status":"ok","service":"other-api"}' ;;
  wrong-status) printf '%s' '{"status":"degraded","service":"linuxcore-api"}' ;;
  malformed) printf '%s' 'not-json' ;;
  unavailable) exit 7 ;;
  *) exit 64 ;;
esac
CURL
chmod +x "$TEST_BIN/curl"
PATH="$TEST_BIN:$PATH"
export PATH
API_URL="http://127.0.0.1:8000/api/v1/health"
export API_URL

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

FAKE_CURL_MODE=healthy assert_status 0 api_is_linuxcore
FAKE_CURL_MODE=wrong-service assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=wrong-status assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=malformed assert_status 2 api_is_linuxcore
FAKE_CURL_MODE=unavailable assert_status 1 api_is_linuxcore

FAKE_CURL_MODE=healthy assert_status 0 wait_for_api 1
FAKE_CURL_MODE=wrong-service assert_status 2 wait_for_api 1
FAKE_CURL_MODE=unavailable assert_status 1 wait_for_api 1

printf '%s\n' 'Startup API identity tests passed (7 cases).'
