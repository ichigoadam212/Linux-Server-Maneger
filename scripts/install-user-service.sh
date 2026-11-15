#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_NAME="linuxcore.service"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_FILE="$UNIT_DIR/$UNIT_NAME"

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Refusing to install a user service as root; run this script as the LinuxCore owner." >&2
  exit 1
fi
if [[ "$UNIT_DIR" != /* ]]; then
  echo "XDG_CONFIG_HOME must resolve to an absolute path for the systemd user unit directory." >&2
  exit 1
fi
if [[ -e "$UNIT_FILE" || -L "$UNIT_FILE" ]]; then
  echo "Refusing to overwrite an existing $UNIT_FILE; inspect and remove it manually before reinstalling." >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is unavailable; use scripts/linuxcore-supervisor.sh run in this environment." >&2
  exit 1
fi
if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "No reachable systemd user manager was found. This is common in PRoot/Andronix." >&2
  echo "Use scripts/linuxcore-supervisor.sh run in the foreground instead." >&2
  exit 1
fi
if [[ ! "$ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  echo "Repository path contains characters that require systemd unit escaping; move the repository to a simple absolute path." >&2
  exit 1
fi

install -d -m 700 "$UNIT_DIR"
TEMP_UNIT="$(mktemp "$UNIT_DIR/.linuxcore.service.XXXXXX")"
cleanup_temp() { [[ -n "${TEMP_UNIT:-}" && -e "$TEMP_UNIT" ]] && rm -f -- "$TEMP_UNIT"; }
trap cleanup_temp EXIT
cat > "$TEMP_UNIT" <<UNIT
[Unit]
Description=LinuxCore local Linux server manager
After=default.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=$ROOT
ExecStart=/usr/bin/bash $ROOT/scripts/linuxcore-supervisor.sh run
ExecStop=/usr/bin/bash $ROOT/scripts/stop.sh
Restart=on-failure
RestartSec=10
KillSignal=SIGTERM
TimeoutStopSec=15
UMask=0077

[Install]
WantedBy=default.target
UNIT
chmod 600 "$TEMP_UNIT"
if ! ln -- "$TEMP_UNIT" "$UNIT_FILE"; then
  echo "Could not safely create $UNIT_FILE; no existing file was overwritten." >&2
  exit 1
fi
rm -f -- "$TEMP_UNIT"
TEMP_UNIT=""
if ! systemctl --user daemon-reload; then
  rm -f -- "$UNIT_FILE"
  systemctl --user daemon-reload >/dev/null 2>&1 || true
  echo "systemd daemon-reload failed; the newly created unit was rolled back." >&2
  exit 1
fi
if ! systemctl --user enable --now "$UNIT_NAME"; then
  systemctl --user disable --now "$UNIT_NAME" >/dev/null 2>&1 || true
  rm -f -- "$UNIT_FILE"
  systemctl --user daemon-reload >/dev/null 2>&1 || true
  echo "systemd could not enable/start LinuxCore; the new unit was rolled back." >&2
  exit 1
fi
echo "Installed and started $UNIT_NAME."
echo "Check with: systemctl --user status $UNIT_NAME"
echo "For service startup after logout/reboot, a VPS administrator must separately enable user lingering for this account."
echo "This installer does not change login/session policy or enable Android background execution guarantees."
