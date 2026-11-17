# Shared dashboard identity probes used by the startup script and isolated tests.
# WEB_URL must point to the local dashboard root page.
web_is_linuxcore() {
  local response http_code body
  response="$(curl --silent --show-error --max-time 1 --write-out $'\n%{http_code}' "$WEB_URL" 2>/dev/null)" || return 1
  http_code="${response##*$'\n'}"
  body="${response%$'\n'*}"
  # A responding HTTP endpoint with a non-success status is not our dashboard.
  [[ "$http_code" == "200" ]] || return 2
  printf '%s' "$body" | python3 -c 'import sys; h=sys.stdin.read(); raise SystemExit(0 if "<title>LinuxCore | Server Manager</title>" in h and "id=\"main-content\"" in h and "app.js" in h else 1)' >/dev/null 2>&1 && return 0
  # A successful response without the expected dashboard markers is not ours.
  return 2
}

wait_for_web() {
  local attempts="${1:-20}"
  local probe_status
  for ((attempt=1; attempt<=attempts; attempt++)); do
    if web_is_linuxcore; then
      return 0
    else
      probe_status=$?
    fi
    # Fail closed immediately when another service owns the dashboard port.
    if [[ "$probe_status" -eq 2 ]]; then
      return 2
    fi
    sleep 0.5
  done
  return 1
}
