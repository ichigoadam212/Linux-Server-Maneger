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
require_text "$HTML" "connect-src http://127.0.0.1:8000" "dashboard API connection policy is missing"
require_text "$JS" 'async function loadOverviewPanels()' "live overview loader is missing"
require_text "$JS" '/api/v1/services' "overview does not query user services"
require_text "$JS" '/api/v1/diagnostics' "overview does not query live diagnostics"
require_text "$JS" 'AbortSignal.timeout(30000)' "diagnostics timeout does not cover bounded capability probes"
require_absent "$HTML" '10:42' "hard-coded sample activity timestamp remains"
require_absent "$HTML" '2.4 GB' "hard-coded sample backup event remains"
require_absent "$HTML" 'L0 31 L20 27' "static sample network graph remains"
echo "Dashboard live-data contract tests passed."
