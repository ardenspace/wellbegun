# Selected inputs and host bootstrap

Resolve the installed plugin root from the current SKILL.md (two directories
above its containing directory), or `CLAUDE_PLUGIN_ROOT` in Claude Code. Use its
absolute `scripts/artifacts.py` path and the absolute project `.wellbegun` path;
the caller's working directory is irrelevant. Never assume the plugin is inside
the project. Examples use shell variables `wb_helper`, `wb_root`, and
`wb_context` populated with these paths and the current host context's stable ID.

For an existing schema 2 execution, bootstrap or resume with:

```sh
python3 "$wb_helper" context --root "$wb_root" --context-id "$wb_context" --remember
```

Use the returned cursor, contract, state, selected constraints and revision.
Do not also read full plan/run/HANDOFF/decisions or inject their history. Reuse
the same ID only within the same host context. A new session gets a new ID and
the bodies again. Follow every advertised `required_sections` and `next_section`
using `context --record ID --section SELECTOR --context-id ID --remember`.
Overflow is routing, not permission to skip constraints. Keep the most recently
returned revision for the next write; `--remember` saves returned reads without
copying receipt JSON or creating receipt files.

Before state exists, or during a legacy cycle, use the current lens's artifact
and only the relevant decision keys:

```sh
python3 "$wb_helper" decision-get --root "$wb_root" --key theme.owner
python3 "$wb_helper" decision-get --root "$wb_root" --domain theme
```

Replace example keys/domains with the actual task's keys. Lookup works without
plan/state. Read mandatory details through the returned section selectors.
Unknown, ambiguous, proposed, superseded or changed-source results need a narrowed
key/source investigation; never substitute a full ledger read or assume no constraint.
Maintain only needed entries in `decisions.index.json`; the runtime contract's
“Plan and selected inputs” section defines their fields and legacy source proofs.
Do not initialize state merely to obtain decisions.

Registry inputs in schema 2 come from the record's selected keys in the context
packet. Before a plan/state exists, select the affected entry in the existing
registry/code by stable key or exact heading and read only that bounded section.
Use a local key/heading search first; do not print an entire long matching row.
N/A needs no registry file. When preparing the plan, put required current entries
in `registry.index.json` and their keys in the contract. Keep decision rationale
behind decision keys rather than repeating it in registry/host instructions.

Preserve legacy artifacts and resume from the relevant current contract/progress
section; no partial state migration. Selective decision lookup is independent of
that format. `validate` reporting `legacy` is routing, not execution validation.
If Python 3.9+ is unavailable, explicitly use this manual/legacy path with bounded
source sections and manual completion/checkpoint checks. Do not create schema 2
state or claim automated validation/bounded extraction. An existing schema 2 run
requires a Python-capable session to mutate its authoritative state; preserve it
until then. Git/hooks are optional. Basic needs no subagent; fresh requires an
independent session and waits at that boundary if none is available.

For generated AGENTS.md/CLAUDE.md instructions and dispatch, preserve user-owned
rules and add only: “Read this record's context with `--remember` through the
installed helper and follow mandatory selectors. Query additional decisions by
key and registries by affected entry; expand only for actual dependencies. Do not
load full decisions/run history.” Resolve the helper on that host instead of
hardcoding a development-machine path. Verifier dispatch uses a new independent
context and `--audience verifier --remember`; give contract/code/commands/valid
check facts only, excluding implementer and previous-verifier narratives. Do not
request or send raw evidence bodies as the default packet.
