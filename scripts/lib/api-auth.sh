#!/usr/bin/env bash
# Read the optional bearer token without sourcing or executing backend/.env.
# Generated token_urlsafe values are accepted; the secret is passed to curl via
# a private process-substitution config rather than a visible command argument.

linuxcore_load_access_token() {
  local token="${LINUXCORE_ACCESS_TOKEN:-}"
  local env_file="${LINUXCORE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}/backend/.env"
  local line value

  if [[ -z "$token" && -f "$env_file" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      case "$line" in
        LINUXCORE_ACCESS_TOKEN=*)
          value="${line#*=}"
          value="${value%$'\r'}"
          value="${value#"${value%%[![:space:]]*}"}"
          value="${value%"${value##*[![:space:]]}"}"
          if [[ "$value" == \"* && "$value" == *\" ]]; then
            value="${value:1:${#value}-2}"
          elif [[ "$value" == \'* && "$value" == *\' ]]; then
            value="${value:1:${#value}-2}"
          else
            value="${value%%#*}"
            value="${value%"${value##*[![:space:]]}"}"
          fi
          token="$value"
          break
          ;;
      esac
    done < "$env_file"
  fi

  if [[ -n "$token" && ! "$token" =~ ^[A-Za-z0-9_-]{32,}$ ]]; then
    echo "LINUXCORE_ACCESS_TOKEN must be a URL-safe token of at least 32 characters." >&2
    return 2
  fi
  LINUXCORE_ACCESS_TOKEN="$token"
  export LINUXCORE_ACCESS_TOKEN
}

linuxcore_curl() {
  linuxcore_load_access_token || return $?
  if [[ -n "${LINUXCORE_ACCESS_TOKEN:-}" ]]; then
    command curl --config <(printf 'header = "Authorization: Bearer %s"\n' "$LINUXCORE_ACCESS_TOKEN") "$@"
  else
    command curl "$@"
  fi
}
