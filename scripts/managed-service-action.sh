#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-}"
case "$ACTION" in
  start)
    sleep 1
    bash "$ROOT/scripts/start.sh"
    ;;
  stop)
    sleep 1
    bash "$ROOT/scripts/stop.sh"
    ;;
  restart)
    sleep 1
    bash "$ROOT/scripts/stop.sh"
    bash "$ROOT/scripts/start.sh"
    ;;
  *)
    echo "Unsupported LinuxCore lifecycle action." >&2
    exit 2
    ;;
esac
