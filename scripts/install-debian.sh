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

echo "Installing LinuxCore prerequisites in the current Linux environment."
echo "No Android root access is requested or used."

if ! apt-get update; then
  echo "Package index update failed. Check package-manager permissions and network access."
  exit 1
fi

if ! apt-get install -y python3 python3-venv python3-pip python3-dev build-essential git curl ca-certificates; then
  echo "Package installation failed. This environment must permit apt package installation."
  exit 1
fi

echo
echo "LinuxCore prerequisites installed."
echo "Next: run ./scripts/start.sh from the repository directory."
