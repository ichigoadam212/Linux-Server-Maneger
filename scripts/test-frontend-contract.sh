#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HTML="$ROOT/frontend/index.html"
JS="$ROOT/frontend/app.js"
require_text() { grep -Fq -- "$2" "$1" || { echo "FAIL: $3" >&2; exit 1; }; }
require_absent() { ! grep -Fq -- "$2" "$1" || { echo "FAIL: $3" >&2; exit 1; }; }
require_text "$HTML" 'id="overviewServices"' "overview service panel is missing"
require_text "$HTML" 'id="overviewCapabilities"' "overview capability panel is missing"
require_text "$HTML" 'http-equiv="Content-Security-Policy"' "dashboard Content Security Policy is missing"
require_text "$HTML" "connect-src 'self'" "dashboard same-origin API connection policy is missing"
require_text "$JS" 'const IS_LOCAL_HOST = ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname)' "local-host authentication mode is missing"
require_text "$JS" 'const API_BASE = "";' "dashboard does not use same-origin API requests"
require_text "$JS" 'if (!IS_LOCAL_HOST)' "hosted login gate is not restricted to remote dashboard mode"
require_absent "$JS" 'http://127.0.0.1:8000' "browser JavaScript still addresses the backend directly"
require_text "$JS" 'async function loadOverviewPanels()' "live overview loader is missing"
require_text "$JS" 'loadingData:"Loading module data…"' "English module loading state is missing"
require_text "$JS" 'loadingData:"جاري تحميل بيانات الوحدة…"' "Arabic module loading state is missing"
require_text "$JS" 'loadingNotice.setAttribute("role", "status")' "module loading state is not announced accessibly"
require_text "$JS" 'loadingNotice.remove()' "module loading state is not cleared after requests"
require_text "$JS" 'response.clone().json()' "API error responses are not parsed safely"
require_text "$JS" 'payload.detail' "API detail messages are not surfaced"
require_text "$JS" 'managedResult.reason?.message' "managed-service API error detail is discarded"
require_text "$JS" 'systemdResult.reason?.message' "systemd API error detail is discarded"
render_module_line="$(grep -n -F 'async function renderModule(page)' "$JS" | head -n 1 | cut -d: -f1)"
[[ -n "$render_module_line" ]] || { echo "FAIL: module renderer is missing" >&2; exit 1; }
render_module_guard_line=$((render_module_line + 1))
[[ "$(sed -n "${render_module_guard_line}p" "$JS")" == *'if (currentPage !== page) return;'* ]] || {
  echo "FAIL: stale module renders are not rejected before changing the UI" >&2
  exit 1
}
require_text "$HTML" 'id="moduleContent" class="module-content" aria-live="polite"' "module updates are not announced accessibly"
require_text "$HTML" 'app.js?v=0.7.3' "frontend cache version was not bumped"
require_text "$JS" '/api/v1/services' "overview does not query user services"
require_text "$JS" '/api/v1/diagnostics' "overview does not query live diagnostics"
require_text "$JS" 'AbortSignal.timeout(30000)' "diagnostics timeout does not cover bounded capability probes"
require_absent "$HTML" '10:42' "hard-coded sample activity timestamp remains"
require_absent "$HTML" '2.4 GB' "hard-coded sample backup event remains"
require_absent "$HTML" 'L0 31 L20 27' "static sample network graph remains"
echo "Dashboard live-data contract tests passed."
