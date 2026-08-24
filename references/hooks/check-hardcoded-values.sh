#!/usr/bin/env bash
# Flag raw design values outside the token source. Adapt TOKEN_FILE and SEARCH_DIRS per project (phase 1).
# SEARCH_DIRS accepts a space-separated list: SEARCH_DIRS="src app" bash check-hardcoded-values.sh
# Prints violations to stderr and exits 2 — the signal Claude Code PostToolUse hooks feed back to the agent.
set -u
TOKEN_FILE="${TOKEN_FILE:-src/styles/tokens.css}"
read -ra dirs <<< "${SEARCH_DIRS:-src}"

# grep --include does not expand braces; one flag per extension.
includes=()
for ext in tsx jsx ts js css scss vue svelte; do
  includes+=(--include="*.$ext")
done

hits=$(grep -rnE "${includes[@]}" \
  '#[0-9a-fA-F]{3,8}\b|(^|[^a-zA-Z0-9-])[0-9]+(px|rem)\b' \
  "${dirs[@]}" 2>/dev/null | grep -vF "$TOKEN_FILE")

if [ -n "$hits" ]; then
  {
    echo "Hardcoded design values found (use tokens from $TOKEN_FILE):"
    echo "$hits"
  } >&2
  exit 2
fi
exit 0
