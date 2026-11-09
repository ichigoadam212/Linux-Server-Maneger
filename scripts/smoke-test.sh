#!/usr/bin/env bash
set -euo pipefail

API="http://127.0.0.1:8000/api/v1"
WEB="http://127.0.0.1:8080"

for command_name in curl python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command is missing: $command_name" >&2
    exit 1
  fi
done

check_json() {
  local url="$1"
  local expression="$2"
  local label="$3"
  local body
  if ! body="$(curl --fail --silent --show-error --max-time 5 "$url")"; then
    echo "FAIL: $label endpoint is unavailable: $url" >&2
    exit 1
  fi
  if ! printf '%s' "$body" | python3 -c "$expression"; then
    echo "FAIL: $label returned an unexpected response." >&2
    exit 1
  fi
  echo "OK: $label"
}

check_json "$API/health" \
  'import json,sys; d=json.load(sys.stdin); assert d.get("status") == "ok" and d.get("service") == "linuxcore-api"' \
  "API health"

check_json "$API/metrics" \
  'import json,sys; d=json.load(sys.stdin); assert 0 <= d["cpu_percent"] <= 100 and 0 <= d["memory_percent"] <= 100 and d["cpu_count"] >= 1 and d["disk_total_gb"] > 0' \
  "host metrics"

for endpoint in storage processes network services containers terminal/commands recovery/check ai/status; do
  check_json "$API/$endpoint" \
    'import json,sys; d=json.load(sys.stdin); assert isinstance(d, dict)' \
    "$endpoint"
done

recovery="$(curl --fail --silent --show-error --max-time 5 "$API/recovery/check")"
if ! printf '%s' "$recovery" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("healthy") is True and all(x.get("present") for x in d.get("files", [])) and d.get("dependencies") is True'; then
  echo "FAIL: recovery preflight reports missing files or dependencies." >&2
  exit 1
fi
echo "OK: recovery preflight"

page="$(curl --fail --silent --show-error --max-time 5 "$WEB/")"
if [[ "$page" != *"LINUXCORE"* || "$page" != *"app.js"* ]]; then
  echo "FAIL: dashboard HTML is incomplete." >&2
  exit 1
fi
curl --fail --silent --show-error --max-time 5 "$WEB/app.js" >/dev/null
curl --fail --silent --show-error --max-time 5 "$WEB/styles.css" >/dev/null
echo "OK: dashboard and static assets"

echo
echo "LinuxCore smoke test passed."
echo "No services, containers, settings, or files were changed."
