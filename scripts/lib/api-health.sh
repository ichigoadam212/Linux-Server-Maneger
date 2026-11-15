# Shared API identity probes used by the startup script and isolated tests.
# API_URL must point to LinuxCore's health endpoint.
source "$(dirname "${BASH_SOURCE[0]}")/api-auth.sh"

api_is_linuxcore() {
  local response http_code body
  response="$(linuxcore_curl --silent --show-error --max-time 1 --write-out $'\n%{http_code}' "$API_URL" 2>/dev/null)" || return 1
  http_code="${response##*$'\n'}"
  body="${response%$'\n'*}"
  [[ "$http_code" == "200" ]] || return 2
  printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); raise SystemExit(0 if d.get("status") == "ok" and d.get("service") == "linuxcore-api" else 1)' >/dev/null 2>&1 && return 0
  return 2
}

wait_for_api() {
  local attempts="${1:-20}"
  local probe_status
  for ((attempt=1; attempt<=attempts; attempt++)); do
    if api_is_linuxcore; then
      return 0
    else
      probe_status=$?
    fi
    if [[ "$probe_status" -eq 2 ]]; then
      return 2
    fi
    sleep 0.5
  done
  return 1
}
