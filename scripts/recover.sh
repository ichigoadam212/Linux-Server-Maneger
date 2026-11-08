#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
BACKUPS="$RUNTIME/backups"
mkdir -p "$BACKUPS"
chmod 700 "$RUNTIME" "$BACKUPS"
umask 077

echo "LinuxCore controlled recovery"
echo "Scope: this repository's local API and dashboard only."

if [[ -f "$ROOT/backend/.env" ]]; then
  backup="$BACKUPS/backend.env.$(date -u +%Y%m%dT%H%M%SZ).bak"
  cp -p "$ROOT/backend/.env" "$backup"
  chmod 600 "$backup"
  echo "Configuration backup saved at: $backup"
else
  echo "No backend/.env found; no secret file needed backup."
fi

for required in \
  "$ROOT/backend/main.py" \
  "$ROOT/frontend/index.html" \
  "$ROOT/frontend/app.js" \
  "$ROOT/scripts/start.sh"; do
  if [[ ! -f "$required" ]]; then
    echo "Required project file is missing: $required" >&2
    exit 1
  fi
done

if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  echo "Backend virtual environment is not ready; start.sh will attempt its documented bootstrap."
fi

bash "$ROOT/scripts/start.sh"
bash "$ROOT/scripts/status.sh"

echo "Recovery checks completed."
echo "No Android settings, system services, firewall rules, or unrelated files were changed."
