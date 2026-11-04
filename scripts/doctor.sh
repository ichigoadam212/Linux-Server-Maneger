#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
printf '%s\n' "LinuxCore environment check"
printf 'Architecture: '; uname -m
printf 'Kernel: '; uname -sr
printf 'Python: '; python3 --version 2>/dev/null || { echo "missing"; exit 1; }
printf 'Git: '; git --version 2>/dev/null || echo "not installed"
if command -v apt-get >/dev/null 2>&1; then echo "Package manager: apt"; else echo "Package manager: not apt"; fi
if [[ -d "$ROOT/frontend" && -f "$ROOT/backend/main.py" ]]; then echo "Project files: OK"; else echo "Project files: incomplete"; exit 1; fi
if [[ "$(uname -m)" != "aarch64" && "$(uname -m)" != "arm64" && "$(uname -m)" != "x86_64" ]]; then
  echo "Warning: architecture is not one of the expected ARM64/x86_64 targets."
fi
echo "Check complete. This script does not change the system."
