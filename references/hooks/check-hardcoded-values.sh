#!/usr/bin/env bash
# Flag raw design values outside the token source. Adapt TOKEN_FILE and SEARCH_DIRS per project (phase 1).
set -u
TOKEN_FILE="${TOKEN_FILE:-src/styles/tokens.css}"
SEARCH_DIRS=("${SEARCH_DIRS:-src}")

hits=$(grep -rnE --include='*.{tsx,jsx,ts,js,css,scss,vue,svelte}' \
  '#[0-9a-fA-F]{3,8}\b|(^|[^a-zA-Z0-9-])[0-9]+(px|rem)\b' \
  "${SEARCH_DIRS[@]}" 2>/dev/null | grep -v "$TOKEN_FILE")

if [ -n "$hits" ]; then
  echo "Hardcoded design values found (use tokens from $TOKEN_FILE):"
  echo "$hits"
  exit 1
fi
exit 0
