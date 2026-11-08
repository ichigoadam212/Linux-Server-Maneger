#!/usr/bin/env bash
set -euo pipefail
echo "LinuxCore local status"
result=0
if curl --fail --silent --max-time 2 http://127.0.0.1:8000/api/v1/health; then
  echo
  echo "API: online"
else
  echo "API: offline"
  result=1
fi
if curl --fail --silent --max-time 2 http://127.0.0.1:8080/ >/dev/null; then
  echo "Website: online at http://127.0.0.1:8080"
else
  echo "Website: offline"
  result=1
fi
exit "$result"
