#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export LINUXCORE_ROOT="$ROOT"
source "$ROOT/scripts/lib/api-auth.sh"
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
  local timeout="${4:-5}"
  local body
  if ! body="$(linuxcore_curl --fail --silent --show-error --max-time "$timeout" "$url")"; then
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

check_json "$API/storage" 'import json,sys; d=json.load(sys.stdin); assert isinstance(d.get("items"), list)' "storage inventory"
check_json "$API/processes" 'import json,sys; d=json.load(sys.stdin); assert isinstance(d.get("items"), list); assert all("cmdline" not in p and "command_line" not in p for p in d["items"])' "privacy-filtered process inventory"
check_json "$API/network" 'import json,sys; d=json.load(sys.stdin); assert isinstance(d.get("available"), bool) and isinstance(d.get("interfaces"), list)' "network inventory"
check_json "$API/diagnostics" 'import json,sys; d=json.load(sys.stdin); c=d["capabilities"]; assert isinstance(d.get("host", {}).get("architecture"), str); assert isinstance(c["user_services"]["available"], bool); assert isinstance(c["containers"]["available"], bool); assert isinstance(c["network_counters"]["available"], bool); assert isinstance(c["diagnostic_commands"], dict)' "environment diagnostics" 30
check_json "$API/services" 'import json,sys; d=json.load(sys.stdin); assert isinstance(d.get("available"), bool) and isinstance(d.get("items"), list)' "user-service inventory"
check_json "$API/containers" 'import json,sys; d=json.load(sys.stdin); assert isinstance(d.get("available"), bool) and isinstance(d.get("items"), list)' "rootless container inventory" 30
check_json "$API/terminal/commands" 'import json,sys; d=json.load(sys.stdin); ids={x["id"] for x in d["commands"]}; assert ids <= {"pwd","system","storage","memory","uptime","processes"}' "allowlisted diagnostic commands"
check_json "$API/ai/status" 'import json,sys; d=json.load(sys.stdin); assert d.get("mode") == "advisory-only" and isinstance(d.get("configured"), bool)' "AI privacy status"

recovery="$(linuxcore_curl --fail --silent --show-error --max-time 10 "$API/recovery/check")"
if ! printf '%s' "$recovery" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("healthy") is True and all(x.get("present") for x in d.get("files", [])) and d.get("dependencies") is True'; then
  echo "FAIL: recovery preflight reports missing files or dependencies." >&2
  exit 1
fi
echo "OK: recovery preflight"

page="$(curl --fail --silent --show-error --max-time 5 "$WEB/")"
if [[ "$page" != *"LINUXCORE"* || "$page" != *"app.js"* || "$page" != *"overviewServices"* || "$page" != *"overviewCapabilities"* || "$page" != *"Content-Security-Policy"* ]]; then
  echo "FAIL: dashboard HTML is incomplete or missing live overview panels." >&2
  exit 1
fi
script="$(curl --fail --silent --show-error --max-time 5 "$WEB/app.js")"
if [[ "$script" != *"loadOverviewPanels"* || "$script" != *"/api/v1/diagnostics"* ]]; then
  echo "FAIL: dashboard does not load live overview data." >&2
  exit 1
fi
curl --fail --silent --show-error --max-time 5 "$WEB/styles.css" >/dev/null
echo "OK: dashboard live overview and static assets"

echo
echo "LinuxCore smoke test passed."
echo "No services, containers, settings, or files were changed."
