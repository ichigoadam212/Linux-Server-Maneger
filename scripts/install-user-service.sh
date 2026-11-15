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
if [[ ! "$ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  echo "Repository path contains characters that require systemd unit escaping; move the repository to a simple absolute path." >&2
  exit 1
fi

install -d -m 700 "$UNIT_DIR"
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
ExecStop=/usr/bin/bash $ROOT/scripts/stop.sh
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
