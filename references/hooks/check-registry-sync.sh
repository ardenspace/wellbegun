#!/usr/bin/env bash
# Fail when a file exists in a common folder but is absent from its registry roster.
# Adapt PAIRS per project (phase 1). Format: "<common-dir>:<registry-md>"
# Prints violations to stderr and exits 2 — the signal Claude Code PostToolUse hooks feed back to the agent.
set -u
PAIRS=("src/components/shared:src/components/shared/REGISTRY.md")

fail=0
for pair in "${PAIRS[@]}"; do
  dir="${pair%%:*}"; reg="${pair##*:}"
  [ -d "$dir" ] || continue
  for f in "$dir"/*; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    [ "$base" = "$(basename "$reg")" ] && continue
    # Fixed-string match wrapped in backticks so roster prose can't false-pass a filename.
    grep -qF -- "\`$base\`" "$reg" 2>/dev/null || grep -qF -- "/$base" "$reg" 2>/dev/null || {
      echo "FAIL: $base is in $dir but not listed in $reg (list it as \`$base\` or by its path)" >&2
      fail=2
    }
  done
done
exit $fail
