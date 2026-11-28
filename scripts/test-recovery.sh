#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_status() {
  local expected="$1" actual="$2" label="$3"
  [[ "$actual" -eq "$expected" ]] || fail "$label: exit status $actual; expected $expected"
}

assert_content() {
  local file="$1" expected="$2" label="$3"
  [[ -f "$file" ]] || fail "$label: expected file is missing"
  [[ "$(cat "$file")" == "$expected" ]] || fail "$label: file content does not match"
}

assert_mode() {
  local file="$1" expected="$2" label="$3"
  local actual
  actual="$(stat -c '%a' "$file")"
  [[ "$actual" == "$expected" ]] || fail "$label: mode $actual; expected $expected"
}

new_fixture() {
  local name="$1"
  FIXTURE="$TEST_ROOT/$name"
  mkdir -p "$FIXTURE/backend" "$FIXTURE/frontend" "$FIXTURE/scripts"
  cp "$SOURCE_ROOT/scripts/recover.sh" "$FIXTURE/scripts/recover.sh"
  touch "$FIXTURE/backend/main.py" "$FIXTURE/frontend/index.html" "$FIXTURE/frontend/app.js"

  cat > "$FIXTURE/scripts/start.sh" <<'START'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
printf 'start\n' >> "$ROOT/.test-calls"
if [[ "${TEST_MUTATE_START:-0}" == "1" ]]; then
  printf 'changed-by-start=1\n' > "$ROOT/backend/.env"
fi
if [[ "${TEST_CREATE_ENV:-0}" == "1" ]]; then
  printf 'created-during-start=1\n' > "$ROOT/backend/.env"
fi
if [[ "${TEST_SWAP_BACKUPS:-0}" == "1" ]]; then
  mv -- "$ROOT/.runtime/backups" "$ROOT/.runtime/backups.original"
  ln -s -- "$TEST_OUTSIDE_BACKUPS" "$ROOT/.runtime/backups"
fi
if [[ "${TEST_SWAP_ENV:-0}" == "1" ]]; then
  rm -f -- "$ROOT/backend/.env"
  ln -s -- "$TEST_OUTSIDE_ENV_DIR" "$ROOT/backend/.env"
fi
exit "${TEST_START_EXIT:-0}"
START

  cat > "$FIXTURE/scripts/status.sh" <<'STATUS'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
printf 'status\n' >> "$ROOT/.test-calls"
if [[ "${TEST_MUTATE_STATUS:-0}" == "1" ]]; then
  printf 'changed-by-status=1\n' > "$ROOT/backend/.env"
fi
exit "${TEST_STATUS_EXIT:-0}"
STATUS
}

run_recovery() {
  local root="$1" start_exit="$2" status_exit="$3"
  local mutate_start="$4" mutate_status="$5" create_env="$6"
  local swap_backups="${7:-0}" outside_backups="${8:-}"
  local swap_env="${9:-0}" outside_env_dir="${10:-}"
  if env \
    TEST_START_EXIT="$start_exit" \
    TEST_STATUS_EXIT="$status_exit" \
    TEST_MUTATE_START="$mutate_start" \
    TEST_MUTATE_STATUS="$mutate_status" \
    TEST_CREATE_ENV="$create_env" \
    TEST_SWAP_BACKUPS="$swap_backups" \
    TEST_OUTSIDE_BACKUPS="$outside_backups" \
    TEST_SWAP_ENV="$swap_env" \
    TEST_OUTSIDE_ENV_DIR="$outside_env_dir" \
    bash "$root/scripts/recover.sh" > "$root/output.log" 2>&1; then
    RUN_STATUS=0
  else
    RUN_STATUS=$?
  fi
}

backup_file() {
  local root="$1"
  find "$root/.runtime/backups" -maxdepth 1 -type f -name '*.bak' -print -quit
}

# 1. Successful recovery keeps the environment file and creates a private backup.
new_fixture "success"
printf 'TOKEN=original-value\n' > "$FIXTURE/backend/.env"
run_recovery "$FIXTURE" 0 0 0 0 0
assert_status 0 "$RUN_STATUS" "successful recovery"
assert_content "$FIXTURE/backend/.env" "TOKEN=original-value" "successful recovery"
BACKUP="$(backup_file "$FIXTURE")"
[[ -n "$BACKUP" ]] || fail "successful recovery: backup was not created"
assert_content "$BACKUP" "TOKEN=original-value" "successful recovery backup"
assert_mode "$BACKUP" 600 "backup file"
assert_mode "$FIXTURE/.runtime" 700 "runtime directory"
assert_mode "$FIXTURE/.runtime/backups" 700 "backup directory"
[[ "$(cat "$FIXTURE/.test-calls")" == $'start\nstatus' ]] || fail "successful recovery did not run start then status"

# 2. A failed start restores the exact pre-recovery environment file.
new_fixture "start-failure"
printf 'TOKEN=original-value\n' > "$FIXTURE/backend/.env"
run_recovery "$FIXTURE" 23 0 1 0 0
assert_status 23 "$RUN_STATUS" "failed start"
assert_content "$FIXTURE/backend/.env" "TOKEN=original-value" "start rollback"
assert_mode "$FIXTURE/backend/.env" 600 "restored environment file"
assert_content "$(backup_file "$FIXTURE")" "TOKEN=original-value" "start rollback backup"
[[ "$(cat "$FIXTURE/.test-calls")" == "start" ]] || fail "status ran after the start script failed"

# 3. A failed recovery removes an environment file created during that run.
new_fixture "new-env-rollback"
run_recovery "$FIXTURE" 17 0 0 0 1
assert_status 17 "$RUN_STATUS" "new environment rollback"
[[ ! -e "$FIXTURE/backend/.env" ]] || fail "new environment file was not removed after failure"
[[ ! -f "$FIXTURE/.test-calls" || "$(cat "$FIXTURE/.test-calls")" == "start" ]] || fail "status ran after the start script failed"

# 4. A failed status check also rolls back environment changes made during recovery.
new_fixture "status-failure"
printf 'TOKEN=original-value\n' > "$FIXTURE/backend/.env"
run_recovery "$FIXTURE" 0 29 0 1 0
assert_status 29 "$RUN_STATUS" "failed status check"
assert_content "$FIXTURE/backend/.env" "TOKEN=original-value" "status rollback"
assert_mode "$FIXTURE/backend/.env" 600 "status-restored environment file"
[[ "$(cat "$FIXTURE/.test-calls")" == $'start\nstatus' ]] || fail "status rollback did not execute both checks"

# 5. Missing required project files fail before either lifecycle script is invoked.
new_fixture "preflight-failure"
printf 'TOKEN=original-value\n' > "$FIXTURE/backend/.env"
rm "$FIXTURE/frontend/app.js"
run_recovery "$FIXTURE" 0 0 0 0 0
assert_status 1 "$RUN_STATUS" "missing-file preflight"
assert_content "$FIXTURE/backend/.env" "TOKEN=original-value" "preflight failure"
[[ ! -f "$FIXTURE/.test-calls" ]] || fail "lifecycle scripts ran despite failed preflight"

# 6. A symlinked runtime directory is rejected before any external path is changed.
new_fixture "runtime-symlink"
OUTSIDE="$TEST_ROOT/outside-runtime"
mkdir -p "$OUTSIDE"
chmod 755 "$OUTSIDE"
ln -s "$OUTSIDE" "$FIXTURE/.runtime"
run_recovery "$FIXTURE" 0 0 0 0 0
assert_status 1 "$RUN_STATUS" "runtime symlink preflight"
assert_mode "$OUTSIDE" 755 "external runtime target"
[[ ! -e "$OUTSIDE/backups" ]] || fail "runtime symlink created an external backup directory"
[[ ! -f "$FIXTURE/.test-calls" ]] || fail "lifecycle scripts ran with a symlinked runtime directory"

# 7. A symlinked backup directory is rejected without changing its target.
new_fixture "backup-symlink"
mkdir -m 700 "$FIXTURE/.runtime"
OUTSIDE="$TEST_ROOT/outside-backups"
mkdir -p "$OUTSIDE"
chmod 755 "$OUTSIDE"
ln -s "$OUTSIDE" "$FIXTURE/.runtime/backups"
run_recovery "$FIXTURE" 0 0 0 0 0
assert_status 1 "$RUN_STATUS" "backup symlink preflight"
assert_mode "$OUTSIDE" 755 "external backup target"
[[ -z "$(find "$OUTSIDE" -mindepth 1 -maxdepth 1 -print -quit)" ]] || fail "backup symlink wrote outside the repository"
[[ ! -f "$FIXTURE/.test-calls" ]] || fail "lifecycle scripts ran with a symlinked backup directory"

# 8. A symlinked environment file is rejected without reading or changing its target.
new_fixture "env-symlink"
OUTSIDE_ENV="$TEST_ROOT/external.env"
printf 'TOKEN=external-value\n' > "$OUTSIDE_ENV"
chmod 644 "$OUTSIDE_ENV"
ln -s "$OUTSIDE_ENV" "$FIXTURE/backend/.env"
run_recovery "$FIXTURE" 0 0 0 0 0
assert_status 1 "$RUN_STATUS" "environment symlink preflight"
assert_content "$OUTSIDE_ENV" "TOKEN=external-value" "external environment target"
assert_mode "$OUTSIDE_ENV" 644 "external environment target"
[[ -L "$FIXTURE/backend/.env" ]] || fail "environment symlink was removed or replaced"
[[ ! -e "$FIXTURE/.runtime" ]] || fail "runtime state was created before environment preflight"

# 9. Replacing the backup path during startup cannot redirect chmod or rollback reads.
new_fixture "backup-path-swap"
printf 'TOKEN=original-value\n' > "$FIXTURE/backend/.env"
OUTSIDE_BACKUPS="$TEST_ROOT/outside-backups-race"
mkdir -m 700 "$OUTSIDE_BACKUPS"
run_recovery "$FIXTURE" 0 0 0 0 0 1 "$OUTSIDE_BACKUPS"
assert_status 1 "$RUN_STATUS" "backup path replacement"
assert_content "$FIXTURE/backend/.env" "TOKEN=original-value" "backup path replacement rollback"
[[ -L "$FIXTURE/.runtime/backups" ]] || fail "backup path replacement fixture did not install its symlink"
[[ -z "$(find "$OUTSIDE_BACKUPS" -mindepth 1 -maxdepth 1 -print -quit)" ]] || fail "backup path replacement wrote outside the repository"
[[ -n "$(find "$FIXTURE/.runtime/backups.original" -maxdepth 1 -type f -name '*.bak' -print -quit)" ]] || fail "pinned backup was not retained in the original directory"
[[ "$(cat "$FIXTURE/.test-calls")" == "start" ]] || fail "status ran after backup path identity changed"

# 10. Rollback replaces a .env symlink-to-directory instead of moving the secret into it.
new_fixture "env-directory-symlink"
printf 'TOKEN=original-value\n' > "$FIXTURE/backend/.env"
OUTSIDE_ENV_DIR="$TEST_ROOT/outside-env-directory"
mkdir -m 700 "$OUTSIDE_ENV_DIR"
run_recovery "$FIXTURE" 23 0 0 0 0 0 "" 1 "$OUTSIDE_ENV_DIR"
assert_status 23 "$RUN_STATUS" "environment symlink-to-directory rollback"
assert_content "$FIXTURE/backend/.env" "TOKEN=original-value" "environment symlink-to-directory rollback"
assert_mode "$FIXTURE/backend/.env" 600 "environment symlink-to-directory restored file"
[[ ! -L "$FIXTURE/backend/.env" ]] || fail "rollback left the environment symlink in place"
[[ -z "$(find "$OUTSIDE_ENV_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]] || fail "rollback moved secret material into the external directory"

printf '%s\n' 'Recovery rollback tests passed (10 isolated scenarios).'
