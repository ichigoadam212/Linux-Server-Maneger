#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
BACKUPS="$RUNTIME/backups"
ENV_FILE="$ROOT/backend/.env"
BACKEND_DIR="$ROOT/backend"
umask 077

preflight_error() {
  printf 'Recovery refused: %s\n' "$1" >&2
  exit 1
}

# Recovery stores a copy of backend/.env. Never follow a symlink for the
# runtime/backup directories or the environment file.
if [[ -L "$BACKEND_DIR" || ! -d "$BACKEND_DIR" ]]; then
  preflight_error "backend must be an existing, real directory."
fi
if [[ -L "$ENV_FILE" ]]; then
  preflight_error "backend/.env must not be a symlink."
fi
if [[ -e "$ENV_FILE" && ! -f "$ENV_FILE" ]]; then
  preflight_error "backend/.env must be a regular file."
fi
if [[ -L "$RUNTIME" || -L "$BACKUPS" ]]; then
  preflight_error "the LinuxCore runtime and backup paths must not be symlinks."
fi

if [[ ! -e "$RUNTIME" ]]; then
  mkdir -m 700 -- "$RUNTIME" || preflight_error "could not create the private runtime directory."
fi
if [[ ! -d "$RUNTIME" || -L "$RUNTIME" ]]; then
  preflight_error "the LinuxCore runtime path is not a safe directory."
fi
if [[ ! -e "$BACKUPS" ]]; then
  mkdir -m 700 -- "$BACKUPS" || preflight_error "could not create the private backup directory."
fi
if [[ ! -d "$BACKUPS" || -L "$BACKUPS" ]]; then
  preflight_error "the LinuxCore backup path is not a safe directory."
fi
chmod 700 -- "$RUNTIME" "$BACKUPS"

BACKUP=""
ENV_EXISTED=false

rollback_on_failure() {
  local exit_code=$?
  trap - EXIT
  if [[ "$exit_code" -ne 0 ]]; then
    if [[ "$ENV_EXISTED" == true && -n "$BACKUP" && -f "$BACKUP" ]]; then
      local restore_tmp
      if restore_tmp="$(mktemp "$BACKEND_DIR/.env.recovery.XXXXXXXX")" &&
         cp -p -- "$BACKUP" "$restore_tmp" &&
         chmod 600 -- "$restore_tmp" &&
         mv -f -- "$restore_tmp" "$ENV_FILE"; then
        echo "Recovery failed; backend/.env was restored from its backup." >&2
      else
        [[ -z "${restore_tmp:-}" ]] || rm -f -- "$restore_tmp"
        echo "Recovery failed; backend/.env could not be restored safely." >&2
      fi
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
  backup_path="$(mktemp "$BACKUPS/backend.env.XXXXXXXX.bak")"
  if ! cp -p -- "$ENV_FILE" "$backup_path"; then
    rm -f -- "$backup_path"
    echo "Could not create the backend/.env backup." >&2
    exit 1
  fi
  BACKUP="$backup_path"
  chmod 600 -- "$BACKUP"
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
