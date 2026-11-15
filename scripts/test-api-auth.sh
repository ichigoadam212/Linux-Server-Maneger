#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "\${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT
mkdir -p "$TEST_ROOT/bin" "$TEST_ROOT/repo/backend" "$TEST_ROOT/repo/scripts/lib"

cp "$SOURCE_ROOT/scripts/lib/api-auth.sh" "$TEST_ROOT/repo/scripts/lib/api-auth.sh"
cat > "$TEST_ROOT/bin/curl" <<'CURL'
#!/usr/bin/env bash
if [[ "\${1:-}" == "--config" ]]; then
  config="$2"
  shift 2
  grep -Fq "header = \"Authorization: Bearer $EXPECTED_TOKEN\"" "$config" || exit 71
  printf 'authenticated\\n'
else
  printf 'anonymous\\n'
fi
CURL
chmod +x "$TEST_ROOT/bin/curl"
export PATH="$TEST_ROOT/bin:$PATH"
export LINUXCORE_ROOT="$TEST_ROOT/repo"

# No token means local-only health probes keep their original behavior.
unset LINUXCORE_ACCESS_TOKEN || true
result="$(linuxcore_curl --silent http://127.0.0.1:8000/api/v1/health 2>/dev/null)" 2>/dev/null || true
[[ "$result" == "anonymous" ]] || { echo "FAIL: no-token probe unexpectedly added authentication." >&2; exit 1; }

# Read only the token assignment; never source or execute the environment file.
TOKEN_FROM_FILE="A1_b2-C3_d4-E5_f6-G7_h8-I9_j0-K1_l2-M3_n4"
printf 'LINUXCORE_ACCESS_TOKEN="%s"\\ntouch %s\\n' "$TOKEN_FROM_FILE" "$TEST_ROOT/should-not-exist" > "$TEST_ROOT/repo/backend/.env"
export EXPECTED_TOKEN="$TOKEN_FROM_FILE"
source "$TEST_ROOT/repo/scripts/lib/api-auth.sh"
result="$(linuxcore_curl --silent http://127.0.0.1:8000/api/v1/health)"
[[ "$result" == "authenticated" ]] || { echo "FAIL: .env token was not added to the curl request." >&2; exit 1; }
[[ ! -e "$TEST_ROOT/should-not-exist" ]] || { echo "FAIL: backend/.env was executed." >&2; exit 1; }

# An explicit process environment value takes precedence over the file.
export LINUXCORE_ACCESS_TOKEN="Z9_y8-X7_w6-V5_u4-T3_s2-R1_q0-P9_o8"
export EXPECTED_TOKEN="$LINUXCORE_ACCESS_TOKEN"
result="$(linuxcore_curl --silent http://127.0.0.1:8000/api/v1/health)"
[[ "$result" == "authenticated" ]] || { echo "FAIL: environment token did not override the file token." >&2; exit 1; }

# Weak or non-URL-safe configured tokens fail closed before curl is invoked.
export LINUXCORE_ACCESS_TOKEN="short"
if linuxcore_curl --silent http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
  echo "FAIL: weak access token was accepted by the local probe helper." >&2
  exit 1
fi

echo "Local API auth helper tests passed (no-token, .env parsing, no execution, environment precedence and weak-token refusal)."
