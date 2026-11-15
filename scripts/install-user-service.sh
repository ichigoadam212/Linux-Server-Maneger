#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_NAME="linuxcore.service"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_FILE="$UNIT_DIR/$UNIT_NAME"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is unavailable; use scripts/linuxcore-supervisor.sh run in this environment." >&2
  exit 1
fi
if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "No reachable systemd user manager was found. This is common in PRoot/Andronix." >&2
  echo "Use scripts/linuxcore-supervisor.sh run in the foreground instead." >&2
  exit 1
fi
case "$ROOT" in
  *[[:space:]]*|*'"'*|*'\\'*|*$'\n'*)
    echo "Repository paths containing whitespace, quotes, or backslashes are not supported by this installer." >&2
    exit 1
    ;;
esac

mkdir -p "$UNIT_DIR"
cat > "$UNIT_FILE" <<UNIT
[Unit]
Description=LinuxCore local Linux server manager
After=default.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=$ROOT
ExecStart=/usr/bin/bash $ROOT/scripts/linuxcore-supervisor.sh run
Restart=on-failure
RestartSec=10
KillSignal=SIGTERM
TimeoutStopSec=15
UMask=0077

[Install]
WantedBy=default.target
UNIT
chmod 600 "$UNIT_FILE"
systemctl --user daemon-reload
systemctl --user enable --now "$UNIT_NAME"
echo "Installed and started $UNIT_NAME."
echo "Check with: systemctl --user status $UNIT_NAME"
echo "This service runs only as the current user; it does not enable Android background execution guarantees."
