#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
BACKUPS="$RUNTIME/backups"
ENV_FILE="$ROOT/backend/.env"
mkdir -p "$BACKUPS"
chmod 700 "$RUNTIME" "$BACKUPS"
umask 077

BACKUP=""
ENV_EXISTED=false

rollback_on_failure() {
  local exit_code=$?
  trap - EXIT
  if [[ "$exit_code" -ne 0 ]]; then
    if [[ "$ENV_EXISTED" == true && -n "$BACKUP" && -f "$BACKUP" ]]; then
      cp -p "$BACKUP" "$ENV_FILE"
      chmod 600 "$ENV_FILE"
      echo "Recovery failed; backend/.env was restored from its backup." >&2
    elif [[ "$ENV_EXISTED" == false ]]; then
      rm -f "$ENV_FILE"
      echo "Recovery failed; any newly created backend/.env was removed." >&2
    fi
  fi
  exit "$exit_code"
}
trap rollback_on_failure EXIT

echo "LinuxCore controlled recovery"
echo "Scope: this repository's local API and dashboard only."

if [[ -f "$ENV_FILE" ]]; then
  ENV_EXISTED=true
  BACKUP="$BACKUPS/backend.env.$(date -u +%Y%m%dT%H%M%SZ).bak"
  cp -p "$ENV_FILE" "$BACKUP"
  chmod 600 "$BACKUP"
  echo "Configuration backup saved at: $BACKUP"
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

trap - EXIT
echo "Recovery checks completed."
echo "No Android settings, system services, firewall rules, or unrelated files were changed."
