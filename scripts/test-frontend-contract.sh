#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HTML="$ROOT/frontend/index.html"
JS="$ROOT/frontend/app.js"
require_text() { grep -Fq -- "$2" "$1" || { echo "FAIL: $3" >&2; exit 1; }; }
require_absent() { ! grep -Fq -- "$2" "$1" || { echo "FAIL: $3" >&2; exit 1; }; }
require_text "$HTML" 'id="overviewServices"' "overview service panel is missing"
require_text "$HTML" 'id="overviewCapabilities"' "overview capability panel is missing"
require_text "$HTML" 'data-page="staticSite"' "Static Site has no dedicated dashboard page"
require_text "$HTML" 'http-equiv="Content-Security-Policy"' "dashboard Content Security Policy is missing"
require_text "$HTML" "connect-src 'self'" "dashboard same-origin API connection policy is missing"
require_text "$JS" 'const IS_LOCAL_HOST = ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname)' "local-host authentication mode is missing"
require_text "$JS" 'const API_BASE = "";' "dashboard does not use same-origin API requests"
require_text "$JS" 'if (!IS_LOCAL_HOST)' "hosted login gate is not restricted to remote dashboard mode"
require_absent "$JS" 'http://127.0.0.1:8000' "browser JavaScript still addresses the backend directly"
require_text "$JS" 'if (page === "staticSite")' "Static Site is not rendered independently"
require_text "$JS" 'port.value = String(site.host_port || 18081)' "Static Site device-test port is not the default"
python3 - "$JS" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1]).read_text(encoding="utf-8")
start = source.index('if (page === "containers") {')
end = source.find('\n    if (page === "', start + 1)
container_code = source[start:end if end >= 0 else len(source)]
if "renderStaticSite" in container_code:
    raise SystemExit("FAIL: Static Site is coupled to the Containers page")
PY
require_text "$JS" 'async function loadOverviewPanels()' "live overview loader is missing"
require_text "$JS" '/api/v1/services' "overview does not query user services"
require_text "$JS" '/api/v1/diagnostics' "overview does not query live diagnostics"
require_text "$JS" 'AbortSignal.timeout(30000)' "diagnostics timeout does not cover bounded capability probes"
require_absent "$HTML" '10:42' "hard-coded sample activity timestamp remains"
require_absent "$HTML" '2.4 GB' "hard-coded sample backup event remains"
require_absent "$HTML" 'L0 31 L20 27' "static sample network graph remains"
echo "Dashboard live-data contract tests passed."
