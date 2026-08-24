#!/usr/bin/env bash
# Fail when a file exists in a common folder but is absent from its registry roster.
# Adapt PAIRS per project (phase 1). Format: "<common-dir>:<registry-md>"
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
    grep -q "$base" "$reg" 2>/dev/null || {
      echo "FAIL: $base is in $dir but not listed in $reg"
      fail=1
    }
  done
done
exit $fail
