#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
export TEST_ROOT
trap 'rm -rf "$TEST_ROOT"' EXIT
mkdir -p "$TEST_ROOT/bin" "$TEST_ROOT/config"

cat > "$TEST_ROOT/bin/systemctl" <<'SYSTEMCTL'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  "--user show-environment")
    [[ "${FAKE_SYSTEMD_USER_AVAILABLE:-1}" == "1" ]]
    ;;
  "--user daemon-reload")
    touch "$TEST_ROOT/daemon-reload"
    ;;
  "--user enable --now linuxcore.service")
    touch "$TEST_ROOT/enabled"
    ;;
  *)
    echo "Unexpected systemctl arguments: $*" >&2
    exit 90
    ;;
esac
SYSTEMCTL
chmod +x "$TEST_ROOT/bin/systemctl"

PATH="$TEST_ROOT/bin:$PATH" \
XDG_CONFIG_HOME="$TEST_ROOT/config" \
bash "$SOURCE_ROOT/scripts/install-user-service.sh" >"$TEST_ROOT/install.log"

UNIT_FILE="$TEST_ROOT/config/systemd/user/linuxcore.service"
[[ -f "$UNIT_FILE" ]] || { echo "FAIL: user unit was not created." >&2; exit 1; }
[[ "$(stat -c '%a' "$UNIT_FILE")" == "600" ]] || { echo "FAIL: unit file permissions are not 600." >&2; exit 1; }
[[ "$(stat -c '%a' "$(dirname "$UNIT_FILE")")" == "700" ]] || { echo "FAIL: user unit directory permissions are not 700." >&2; exit 1; }
grep -Fq "Restart=on-failure" "$UNIT_FILE"
grep -Fq "ExecStop=/usr/bin/bash $SOURCE_ROOT/scripts/stop.sh" "$UNIT_FILE"
[[ -f "$TEST_ROOT/daemon-reload" && -f "$TEST_ROOT/enabled" ]] || {
  echo "FAIL: installer did not reload and enable the unit." >&2
  exit 1
}

rm -rf "$TEST_ROOT/config/systemd"
if PATH="$TEST_ROOT/bin:$PATH" \
   XDG_CONFIG_HOME="$TEST_ROOT/config" \
   FAKE_SYSTEMD_USER_AVAILABLE=0 \
   bash "$SOURCE_ROOT/scripts/install-user-service.sh" >"$TEST_ROOT/unavailable.log" 2>&1; then
  echo "FAIL: installer accepted an unavailable systemd user manager." >&2
  exit 1
fi
[[ ! -e "$TEST_ROOT/config/systemd/user/linuxcore.service" ]] || {
  echo "FAIL: installer wrote a unit without a reachable user manager." >&2
  exit 1
}

echo "LinuxCore user-service installer tests passed (unit content, permissions, enablement and unavailable-manager refusal)."
