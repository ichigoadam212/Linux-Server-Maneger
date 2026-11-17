#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_BIN="$(mktemp -d)"
export TEST_BIN
trap 'rm -rf "$TEST_BIN"' EXIT

cat > "$TEST_BIN/curl" <<'CURL'
#!/usr/bin/env bash
case "${FAKE_WEB_MODE:-healthy}" in
  healthy)
    printf '%s\n200' '<!doctype html><html><head><title>LinuxCore | Server Manager</title></head><body><main id="main-content"></main><script src="app.js?v=0.7.1"></script></body></html>'
    ;;
  wrong-site) printf '%s\n200' '<!doctype html><html><title>Other local service</title><body>Welcome</body></html>' ;;
  not-found) printf '%s\n404' '<html><body>Not found</body></html>' ;;
  server-error) printf '%s\n500' '<html><body>Internal error</body></html>' ;;
  alternate-version) printf '%s\n200' '<!doctype html><html><head><title>LinuxCore | Server Manager</title></head><body><main id="main-content"></main><script src="app.js?v=9.9.9"></script></body></html>' ;;
  retry-then-healthy)
    count="$(cat "$TEST_BIN/curl-count" 2>/dev/null || printf '0')"
    count=$((count + 1))
    printf '%s' "$count" > "$TEST_BIN/curl-count"
    if [[ "$count" -lt 3 ]]; then exit 7; fi
    printf '%s\n200' '<!doctype html><html><head><title>LinuxCore | Server Manager</title></head><body><main id="main-content"></main><script src="app.js?v=0.7.1"></script></body></html>'
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
WEB_URL="http://127.0.0.1:8080/"
export WEB_URL

# Avoid delays while keeping the production retry logic unchanged.
sleep() { :; }
source "$ROOT/scripts/lib/web-health.sh"

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

FAKE_WEB_MODE=healthy assert_status 0 web_is_linuxcore
FAKE_WEB_MODE=alternate-version assert_status 0 web_is_linuxcore
FAKE_WEB_MODE=wrong-site assert_status 2 web_is_linuxcore
FAKE_WEB_MODE=not-found assert_status 2 web_is_linuxcore
FAKE_WEB_MODE=server-error assert_status 2 web_is_linuxcore
FAKE_WEB_MODE=unavailable assert_status 1 web_is_linuxcore

FAKE_WEB_MODE=healthy assert_status 0 wait_for_web 1
FAKE_WEB_MODE=wrong-site assert_status 2 wait_for_web 1
FAKE_WEB_MODE=not-found assert_status 2 wait_for_web 1
rm -f "$TEST_BIN/curl-count"
FAKE_WEB_MODE=unavailable assert_status 1 wait_for_web 3
assert_count 3

rm -f "$TEST_BIN/curl-count"
FAKE_WEB_MODE=retry-then-healthy assert_status 0 wait_for_web 3
assert_count 3

printf '%s\n' 'Startup dashboard identity tests passed (10 cases).'
