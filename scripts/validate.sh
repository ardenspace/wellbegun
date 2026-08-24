#!/usr/bin/env bash
# Structural validation for the wellbegun plugin. Exit non-zero on any violation.
set -u
cd "$(dirname "$0")/.."
fail=0
err() { echo "FAIL: $1"; fail=1; }

# 1. Manifests parse as JSON and agree on the plugin name.
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json; do
  [ -f "$f" ] || { err "$f missing"; continue; }
  python3 -m json.tool "$f" >/dev/null 2>&1 || err "$f is not valid JSON"
done
name=$(python3 -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["name"])' 2>/dev/null)
[ "${name:-}" = "wellbegun" ] || err "plugin.json name is '${name:-}', expected 'wellbegun'"

# 2. Each skill dir has SKILL.md with matching name and a "Use when" description.
for d in skills/*/; do
  [ -d "$d" ] || continue
  s="${d}SKILL.md"; dirname=$(basename "$d")
  [ -f "$s" ] || { err "$s missing"; continue; }
  head -1 "$s" | grep -q '^---$' || err "$s missing frontmatter"
  grep -q "^name: $dirname$" "$s" || err "$s name does not match directory '$dirname'"
  grep -q '^description: "\?Use when' "$s" || err "$s description must start with 'Use when'"
done

# 3. Skills must not invoke forbidden Superpowers stages or reference sibling plugins.
# (no pipe into while — a piped while runs in a subshell and would drop fail=1)
for f in $(grep -rlE 'superpowers:(brainstorming|writing-plans)' skills/ 2>/dev/null); do
  err "$f invokes a forbidden Superpowers planning skill"
done
for f in $(grep -rlE '\.talpi/|\.loopspace/|pslog' skills/ references/ 2>/dev/null); do
  err "$f references a sibling plugin"
done

[ $fail -eq 0 ] && echo "OK: wellbegun structure valid"
exit $fail
