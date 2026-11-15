#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILED=0
WARNINGS=0

ok() { printf 'OK: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; FAILED=$((FAILED + 1)); }
warn() { printf 'WARN: %s\n' "$1"; WARNINGS=$((WARNINGS + 1)); }

printf '%s\n' "LinuxCore local security checks"

if grep -Fq -- '--host 127.0.0.1' "$ROOT/scripts/start.sh" &&
   grep -Fq -- '--bind 127.0.0.1' "$ROOT/scripts/start.sh"; then
  ok "API and dashboard bind to loopback"
else
  fail "Expected loopback-only API and dashboard bindings"
fi

if [[ -f "$ROOT/scripts/linuxcore-supervisor.sh" &&
      -f "$ROOT/scripts/install-user-service.sh" ]] &&
   grep -Fq 'systemctl --user' "$ROOT/scripts/install-user-service.sh" &&
   ! grep -Eq 'sudo|0\.0\.0\.0' "$ROOT/scripts/linuxcore-supervisor.sh" "$ROOT/scripts/install-user-service.sh"; then
  ok "Optional user service is unprivileged and does not add public bindings"
else
  fail "Supervisor/service installer is missing or exceeds user-level scope"
fi

if grep -Eq 'shell[[:space:]]*=[[:space:]]*True' "$ROOT/backend/main.py"; then
  fail "Shell execution is enabled in backend/main.py"
else
  ok "No subprocess shell=True pattern detected"
fi

if grep -Eq 'allow_origins=.*\*' "$ROOT/backend/main.py"; then
  fail "Wildcard CORS origin detected"
else
  ok "No wildcard CORS origin detected"
fi

if grep -Fq 'http-equiv="Content-Security-Policy"' "$ROOT/frontend/index.html" &&
   grep -Fq "connect-src http://127.0.0.1:8000" "$ROOT/frontend/index.html" &&
   grep -Fq "object-src 'none'" "$ROOT/frontend/index.html"; then
  ok "Dashboard Content Security Policy restricts scripts and API connections"
else
  fail "Dashboard Content Security Policy is missing or incomplete"
fi

if grep -Eq '<script[^>]+src="https?://' "$ROOT/frontend/index.html"; then
  fail "Remote script source detected in dashboard HTML"
else
  ok "Dashboard does not load remote scripts"
fi

if grep -Fq 'DEEPSEEK_API_KEY=' "$ROOT/frontend"/*.js "$ROOT/frontend"/*.html 2>/dev/null; then
  fail "A DeepSeek API key assignment appears in frontend assets"
else
  ok "No DeepSeek API key assignment appears in frontend assets"
fi

if grep -Fqx '.runtime/' "$ROOT/.gitignore"; then
  ok "Runtime state and backup directory is ignored by Git"
else
  fail "Runtime state and backup directory is not ignored by Git"
fi

if command -v git >/dev/null 2>&1; then
  if git -C "$ROOT" ls-files |
      grep -E '(^|/)\.env($|\.|rc$)' |
      grep -Ev '\.env\.example$' >/dev/null; then
    fail "A populated or non-example environment file is tracked by Git"
  else
    ok "No populated environment file is tracked by Git"
  fi
else
  warn "Git is unavailable; tracked-secret check was skipped"
fi

ENV_FILE="$ROOT/backend/.env"
if [[ -f "$ENV_FILE" ]]; then
  if command -v stat >/dev/null 2>&1; then
    MODE="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || true)"
    if [[ "$MODE" =~ ^[0-7]{3,4}$ ]] && (( (8#$MODE & 077) == 0 )); then
      ok "backend/.env has owner-only permissions"
    else
      fail "backend/.env permissions are too broad (expected 600 or stricter)"
    fi
  else
    warn "Could not inspect backend/.env permissions"
  fi
else
  ok "No local backend/.env file is present"
fi

if bash -n "$ROOT"/scripts/*.sh "$ROOT"/scripts/lib/*.sh; then
  ok "Shell scripts pass syntax validation"
else
  fail "Shell script syntax validation failed"
fi

if command -v python3 >/dev/null 2>&1; then
  if python3 -m compileall -q "$ROOT/backend"; then
    ok "Backend Python files compile"
  else
    fail "Backend Python compilation failed"
  fi
else
  fail "python3 is required"
fi

if command -v node >/dev/null 2>&1; then
  if node --check "$ROOT/frontend/app.js"; then
    ok "Frontend JavaScript passes syntax validation"
  else
    fail "Frontend JavaScript syntax validation failed"
  fi
else
  warn "Node.js unavailable; frontend syntax check skipped"
fi

printf '\nSecurity checks: %s failure(s), %s warning(s).\n' "$FAILED" "$WARNINGS"
[[ "$FAILED" -eq 0 ]]
