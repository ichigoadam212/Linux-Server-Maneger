# Shared API identity probes used by the startup script and isolated tests.
# API_URL must point to LinuxCore's health endpoint.
api_is_linuxcore() {
  local body
  body="$(curl --fail --silent --max-time 1 "$API_URL" 2>/dev/null)" || return 1
  printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); raise SystemExit(0 if d.get("status") == "ok" and d.get("service") == "linuxcore-api" else 1)' >/dev/null 2>&1 && return 0
  # A responding endpoint with an unexpected/malformed identity is not ours.
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
    # Fail closed immediately when another service owns the endpoint.
    if [[ "$probe_status" -eq 2 ]]; then
      return 2
    fi
    sleep 0.5
  done
  return 1
}
