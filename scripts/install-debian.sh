#!/usr/bin/env bash
set -euo pipefail
if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer supports Debian/Ubuntu-based Linux environments with apt."
  exit 1
fi
ARCH="$(uname -m)"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" && "$ARCH" != "x86_64" ]]; then
  echo "Unsupported CPU architecture: $ARCH"
  exit 1
fi
if [[ "$(id -u)" -eq 0 ]]; then
  APT=(apt-get)
elif command -v sudo >/dev/null 2>&1; then
  APT=(sudo apt-get)
else
  echo "Package installation needs the Linux environment's package-manager permission."
  echo "No Android root access is requested or used by this script."
  exit 1
fi
"${APT[@]}" update
"${APT[@]}" install -y python3 python3-venv python3-pip python3-dev build-essential git curl ca-certificates
echo
echo "LinuxCore prerequisites installed."
echo "Next: run ./scripts/start.sh from the repository directory."
