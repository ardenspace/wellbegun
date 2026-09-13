#!/usr/bin/env bash
# Structural and runtime validation. One unittest discovery per invocation.
set -u
cd "$(dirname "$0")/.."
fail=0
err() { echo "FAIL: $1"; fail=1; }

# 1. Claude and Codex manifests parse as JSON and agree on the plugin name.
plugin_root="plugins/wellbegun"
for f in .claude-plugin/marketplace.json .agents/plugins/marketplace.json \
  "$plugin_root/.claude-plugin/plugin.json" "$plugin_root/.codex-plugin/plugin.json"; do
  [ -f "$f" ] || { err "$f missing"; continue; }
  python3 -m json.tool "$f" >/dev/null 2>&1 || err "$f is not valid JSON"
done
name=$(python3 -c 'import json;print(json.load(open("plugins/wellbegun/.claude-plugin/plugin.json"))["name"])' 2>/dev/null)
[ "${name:-}" = "wellbegun" ] || err "plugin.json name is '${name:-}', expected 'wellbegun'"
mname=$(python3 -c 'import json;print(json.load(open(".claude-plugin/marketplace.json"))["plugins"][0]["name"])' 2>/dev/null)
[ "${mname:-}" = "${name:-}" ] || err "marketplace.json plugin name '${mname:-}' does not match plugin.json '${name:-}'"
codex_name=$(python3 -c 'import json;print(json.load(open("plugins/wellbegun/.codex-plugin/plugin.json"))["name"])' 2>/dev/null)
[ "${codex_name:-}" = "${name:-}" ] || err "Codex plugin name '${codex_name:-}' does not match Claude plugin name '${name:-}'"
codex_market_name=$(python3 -c 'import json;print(json.load(open(".agents/plugins/marketplace.json"))["plugins"][0]["name"])' 2>/dev/null)
[ "${codex_market_name:-}" = "${name:-}" ] || err "Codex marketplace plugin name '${codex_market_name:-}' does not match plugin name '${name:-}'"
claude_source=$(python3 -c 'import json;print(json.load(open(".claude-plugin/marketplace.json"))["plugins"][0]["source"])' 2>/dev/null)
[ "${claude_source:-}" = "./plugins/wellbegun" ] || err "Claude marketplace source is '${claude_source:-}', expected './plugins/wellbegun'"
codex_source=$(python3 -c 'import json;print(json.load(open(".agents/plugins/marketplace.json"))["plugins"][0]["source"]["path"])' 2>/dev/null)
[ "${codex_source:-}" = "./plugins/wellbegun" ] || err "Codex marketplace source is '${codex_source:-}', expected './plugins/wellbegun'"

# 2. Each skill dir has SKILL.md with matching name and a "Use when" description.
for d in "$plugin_root"/skills/*/; do
  [ -d "$d" ] || continue
  s="${d}SKILL.md"; dirname=$(basename "$d")
  [ -f "$s" ] || { err "$s missing"; continue; }
  head -1 "$s" | grep -q '^---$' || err "$s missing frontmatter"
  grep -q "^name: $dirname$" "$s" || err "$s name does not match directory '$dirname'"
  grep -q '^description: "\?Use when' "$s" || err "$s description must start with 'Use when'"
done

# 3. Skills must not invoke forbidden Superpowers stages or reference sibling plugins.
# (no pipe into while — a piped while runs in a subshell and would drop fail=1)
for f in $(grep -rlE 'superpowers:(brainstorming|writing-plans)' "$plugin_root"/skills/ 2>/dev/null); do
  err "$f invokes a forbidden Superpowers planning skill"
done
for f in $(grep -rlE '\.talpi/|\.loopspace/|pslog' "$plugin_root"/skills/ "$plugin_root"/references/ 2>/dev/null); do
  err "$f references a sibling plugin"
done

[ $fail -eq 0 ] && echo "OK: wellbegun structure valid"
python3 -m unittest discover -s "$plugin_root/tests" || err "runtime tests failed"
exit $fail
