#!/usr/bin/env bash
set -euo pipefail
echo "LinuxCore local status"
if curl --fail --silent --max-time 2 http://127.0.0.1:8000/api/v1/health; then
  echo
else
  echo "API: offline"
fi
if curl --fail --silent --max-time 2 http://127.0.0.1:8080/ >/dev/null; then
  echo "Website: online at http://127.0.0.1:8080"
else
  echo "Website: offline"
fi
