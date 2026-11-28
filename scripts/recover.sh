#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
RUNTIME="$ROOT/.runtime"
BACKUPS="$RUNTIME/backups"
ENV_FILE="$ROOT/backend/.env"
BACKEND_DIR="$ROOT/backend"
umask 077

preflight_error() {
  printf 'Recovery refused: %s\n' "$1" >&2
  exit 1
}

assert_backend_identity() {
  local current_id
  [[ ! -L "$BACKEND_DIR" && -d "$BACKEND_DIR" ]] || return 1
  current_id="$(stat -c '%d:%i' -- "$BACKEND_DIR")" || return 1
  [[ "$current_id" == "$BACKEND_ID" ]]
}

assert_runtime_backup_identity() {
  local runtime_id backup_id
  [[ ! -L "$RUNTIME" && -d "$RUNTIME" ]] || return 1
  runtime_id="$(stat -c '%d:%i' -- "$RUNTIME")" || return 1
  [[ "$runtime_id" == "$RUNTIME_ID" ]] || return 1
  [[ ! -L "$BACKUPS" && -d "$BACKUPS" ]] || return 1
  backup_id="$(stat -c '%d:%i' -- "$BACKUPS")" || return 1
  [[ "$backup_id" == "$BACKUPS_ID" ]]
}

# Pin the backend directory before inspecting its environment file. The
# physical path and device/inode identity are checked again before rollback.
if [[ -L "$BACKEND_DIR" || ! -d "$BACKEND_DIR" ]]; then
  preflight_error "backend must be an existing, real directory."
fi
cd -- "$BACKEND_DIR" || preflight_error "could not enter the backend directory."
BACKEND_PINNED="$(pwd -P)"
if [[ "$BACKEND_PINNED" != "$BACKEND_DIR" || -L "$BACKEND_DIR" ]]; then
  preflight_error "backend directory identity changed during preflight."
fi
BACKEND_ID="$(stat -c '%d:%i' -- .)" || preflight_error "could not identify the backend directory."
if [[ -L .env ]]; then
  preflight_error "backend/.env must not be a symlink."
fi
if [[ -e .env && ! -f .env ]]; then
  preflight_error "backend/.env must be a regular file."
fi
ENV_EXISTED=false
[[ ! -f .env ]] || ENV_EXISTED=true
cd -- "$ROOT" || preflight_error "could not return to the repository root."

# Create or open the runtime directory, then chmod the pinned current
# directory (.) rather than resolving the mutable pathname again.
if [[ -L "$RUNTIME" ]]; then
  preflight_error "the LinuxCore runtime path must not be a symlink."
fi
if [[ ! -e "$RUNTIME" ]]; then
  mkdir -m 700 -- "$RUNTIME" || preflight_error "could not create the private runtime directory."
fi
if [[ ! -d "$RUNTIME" || -L "$RUNTIME" ]]; then
  preflight_error "the LinuxCore runtime path is not a safe directory."
fi
cd -- "$RUNTIME" || preflight_error "could not enter the runtime directory."
RUNTIME_PINNED="$(pwd -P)"
if [[ "$RUNTIME_PINNED" != "$RUNTIME" || -L "$RUNTIME" ]]; then
  preflight_error "runtime directory identity changed during preflight."
fi
chmod 700 -- . || preflight_error "could not secure the runtime directory."
RUNTIME_ID="$(stat -c '%d:%i' -- .)" || preflight_error "could not identify the runtime directory."

# Create/open backups relative to the pinned runtime directory. Once inside,
# chmod . and all backup-file operations remain anchored to this directory
# even if another process later replaces the .runtime/backups pathname.
if [[ -L backups ]]; then
  preflight_error "the LinuxCore backup path must not be a symlink."
fi
if [[ ! -e backups ]]; then
  mkdir -m 700 -- backups || preflight_error "could not create the private backup directory."
fi
if [[ ! -d backups || -L backups ]]; then
  preflight_error "the LinuxCore backup path is not a safe directory."
fi
cd -- backups || preflight_error "could not enter the backup directory."
BACKUPS_PINNED="$(pwd -P)"
if [[ "$BACKUPS_PINNED" != "$BACKUPS" || -L "$BACKUPS" ]]; then
  preflight_error "backup directory identity changed during preflight."
fi
chmod 700 -- . || preflight_error "could not secure the backup directory."
BACKUPS_ID="$(stat -c '%d:%i' -- .)" || preflight_error "could not identify the backup directory."

BACKUP_NAME=""
BACKUP_FD=""
if [[ "$ENV_EXISTED" == true ]]; then
  assert_backend_identity || preflight_error "backend directory changed before the environment backup."
  BACKUP_NAME="$(mktemp './backend.env.XXXXXXXX.bak')" || preflight_error "could not create a unique environment backup."
  if ! cp -pP -- "$ENV_FILE" "$BACKUP_NAME"; then
    rm -f -- "$BACKUP_NAME"
    preflight_error "could not create the backend/.env backup without following symlinks."
  fi
  if [[ -L "$BACKUP_NAME" || ! -f "$BACKUP_NAME" ]]; then
    rm -f -- "$BACKUP_NAME"
    preflight_error "the environment backup was not created as a regular file."
  fi
  chmod 600 -- "$BACKUP_NAME" || preflight_error "could not secure the environment backup."
  exec {BACKUP_FD}< "$BACKUP_NAME" || preflight_error "could not pin the environment backup for rollback."
  assert_backend_identity || preflight_error "backend directory changed while the environment backup was created."
  echo "Configuration backup saved at: $BACKUPS_PINNED/${BACKUP_NAME#./}"
else
  echo "No backend/.env found; no secret file needed backup."
fi

cd -- "$ROOT" || preflight_error "could not return to the repository root."

BACKUP_READY=false
[[ "$ENV_EXISTED" == false || -n "$BACKUP_FD" ]] && BACKUP_READY=true

rollback_on_failure() {
  local exit_code=$?
  trap - EXIT
  if [[ "$exit_code" -ne 0 && "$RECOVERY_STARTED" == true ]]; then
    if [[ "$ENV_EXISTED" == true && "$BACKUP_READY" == true ]]; then
      if (
        cd -- "$BACKEND_DIR" &&
        [[ "$(pwd -P)" == "$BACKEND_PINNED" && ! -L "$BACKEND_DIR" ]] &&
        [[ "$(stat -c '%d:%i' -- .)" == "$BACKEND_ID" ]] || exit 1
        restore_tmp=""
        cleanup_restore() {
          [[ -z "$restore_tmp" ]] || rm -f -- "$restore_tmp"
        }
        trap cleanup_restore EXIT
        restore_tmp="$(mktemp './.env.recovery.XXXXXXXX')" || exit 1
        cat <&"$BACKUP_FD" > "$restore_tmp" || exit 1
        chmod 600 -- "$restore_tmp" || exit 1
        mv -fT -- "$restore_tmp" .env || exit 1
        restore_tmp=""
        trap - EXIT
      ); then
        echo "Recovery failed; backend/.env was restored from its pinned backup." >&2
      else
        echo "Recovery failed; backend/.env could not be restored safely." >&2
      fi
    elif [[ "$ENV_EXISTED" == false ]]; then
      if (
        cd -- "$BACKEND_DIR" &&
        [[ "$(pwd -P)" == "$BACKEND_PINNED" && ! -L "$BACKEND_DIR" ]] &&
        [[ "$(stat -c '%d:%i' -- .)" == "$BACKEND_ID" ]] &&
        rm -f -- .env
      ); then
        echo "Recovery failed; any newly created backend/.env was removed." >&2
      else
        echo "Recovery failed; backend/.env could not be removed safely." >&2
      fi
    fi
  fi
  exit "$exit_code"
}

RECOVERY_STARTED=false
trap rollback_on_failure EXIT

echo "LinuxCore controlled recovery"
echo "Scope: this repository's local API and dashboard only."

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

RECOVERY_STARTED=true
bash "$ROOT/scripts/start.sh"
if ! assert_runtime_backup_identity; then
  echo "Recovery refused: runtime or backup directory identity changed during startup." >&2
  exit 1
fi
bash "$ROOT/scripts/status.sh"
if ! assert_runtime_backup_identity; then
  echo "Recovery refused: runtime or backup directory identity changed during status validation." >&2
  exit 1
fi

trap - EXIT
echo "Recovery checks completed."
echo "No Android settings, system services, firewall rules, or unrelated files were changed."
