---
name: wellnext
description: "Use when a wellbegun project has completed its pipeline (approved plan, finished run) and a new chunk of work arrives — a feature list, a flowchart, an n-th development round. Cycle gate: triages work, audits affected areas when needed, archives the finished cycle, and seeds the next one."
---

# wellnext — the cycle gate

Classify incoming work before auditing. Small fixes with no new expensive decision proceed directly with affected checks. For a new cycle, audit relevant areas, reuse existing authorization, archive completed work and seed the selected lens.

## Guard

Resolve `<plugin-root>` as `${CLAUDE_PLUGIN_ROOT}` in Claude Code or two
directories above this SKILL.md's containing directory in Codex. Use
`<plugin-root>/references/selected-inputs.md` for bootstrap and selective lookup
(reuse it if already read); all helper/project paths must be absolute.

First reconcile explicit session approval with artifact status; update a stale draft flag for that approved scope instead of restarting planning.

Before ordinary missing-plan routing, check for an unfinished archive follow-up:
if current state/plan are absent but outgoing begin/spec remain, compare their
cycle with the completed archived state's cycle/returned destination. Finish
only the matching begin/spec/outgoing-audit moves without overwriting files,
then seed the authorized next cycle. Do not guess a match from the latest
directory name alone or initialize state to bypass an uncertain archive.

- `.wellbegun/` missing → not a wellbegun project yet; route to wellbegin.
- `.wellbegun/pending/` non-empty → answers are owed; route to wellrun.
- Schema 2: bootstrap via `context --remember`; only a valid `cursor:complete`
  permits closing. Pending, stopped, drift or unresolved findings route to wellrun.
  Do not infer completion from derived run.md.
- Legacy: missing/unapproved plan or relevant run entries not `[x]` means mid-flight;
  route to the current lens. An approved plan with every record verified and no
  unresolved finding/pending question permits closing in its existing format.

Not every change deserves this gate: bugfixes and small tweaks proceed without wellnext — the installed hooks keep guarding, and the next cycle's audit settles whatever accumulated. wellnext is for chunks of work.

## Step 1: Entry triage

Read the new work (feature list, flowchart, request), the current `begin.md` (identity decisions, non-goals), related active decision entries, relevant items from the outgoing `run.md`'s `## Deferred` section. Use current constraints only. Test two axes:

- **Axis 1 — does it overturn?** The new work contradicts an identity decision or a non-goal in the current begin.md.
- **Axis 2 — does it add a journey?** The new work introduces a user journey the current begin.md does not have, large enough to carry its own failure branches.

| Verdict | Condition |
|---|---|
| **begin entry** (delta begin) | either axis fires |
| **spec entry** | neither fires; the work extends existing journeys |
| **no pipeline** | too small for the pipeline — hooks keep guarding; just do the work |

The axes are deliberately not "does it touch identity": the begin lens's value is the user lens itself (journeys, failure branches, probe angles), so a large development with intact identity still enters at begin.

For **no pipeline**, perform the authorized small change and affected checks immediately; do not audit, archive or seed a cycle first. Otherwise state the entry and evidence, then audit affected areas. Reuse prior authorization to open this cycle; ask only if it is missing or the work introduces an unapproved expensive choice or material scope change.

## Step 2: Relevant-area audit

Only after triage identifies a cycle, inspect affected active registry entries and code. Expand to a whole-project audit only with evidence of broad drift. Skip N/A registries and reuse effective schema/type/lint checks.

Record relevant roster/code drift, applicable enforcement results, and actual reuse opportunities in `.wellbegun/audit.md`. Correct confirmed owned index errors under existing project authority; preserve user changes and do not force a commit or invent a design choice. New public-contract decisions go to wellspec. Run checks for changed areas, reusing valid results. Promotion candidates need actual reuse or an approved shared plan, not similar appearance alone.

## Step 3: Opening procedure (within authorization)

1. **Archive.** For schema 2, invoke the helper below before moving any other
   artifacts. It validates completion and archives plan/state/run, optional
   HANDOFF and cycle evidence together to `cycles/<stored-cycle>/`. On success,
   stamp `closed` in the outgoing begin and move begin/spec and the previous
   cycle's audit, if present, into that same returned destination without
   overwriting any file. Keep this cycle-opening audit at top level (create it
   separately from an outgoing audit if necessary). Before seeding, verify
   those moves; after interruption finish them before overwriting current files.
   Legacy uses the next free zero-padded `cycles/NN/`, preserving its original
   begin/spec/plan/run/audit format and manually confirming all blockers are clear.
   Both paths preserve top-level decisions/indexes/registries and append only a
   needed cycle heading to the original ledger, without converting history.
   Archived files are immutable. Without reliable dates, record unknown.
2. **Seed.** Write the new cycle's first artifact with frontmatter `cycle: N`, `entry: begin|spec`, `opened: YYYY-MM-DD`. Begin entry → seed `begin.md` with `status: draft` from wellbegin's template, plus an inherited-identity section listing the previous cycle's identity decisions. **Spec entry still gets a begin.md** — a thin one, written here with `status: approved` (existing authorization for this entry supplies its approval): the full list of identity decisions carried forward (the top-level begin.md is always the current answer sheet), a summary of this cycle's delta journeys, and an empty expensive-decision queue (spec entry means no product-lens conversation ran to fill it; discoveries during the run still follow wellrun's hidden-decision rule). This keeps wellspec's guard untouched and keeps upstream documents honest.
3. **Route.** Invoke the confirmed entry lens — wellbegin for begin entry, wellspec for spec entry. On a **no pipeline** verdict, complete the requested change directly, without archive or seed.

Schema 2 archive command (`wb_revision` is the latest returned revision):

```sh
python3 "$wb_helper" transition --root "$wb_root" --expected-revision "$wb_revision" --input - <<'JSON'
{"op":"archive"}
JSON
```

If `.archive.json` exists, read only “Cycle archive” in the runtime contract:
resume the same operation with its recorded revision, never delete its marker
or overwrite the destination. After archive, the next approved plan initializes
at revision 0 with a new cycle ID. Do not copy old state/read receipts or inject
archived run/evidence into its packet. Decision lookup remains available between
cycles. With no Python, keep manual/legacy cycles manual; an existing schema 2
archive waits for a Python-capable session.

## audit.md template

```markdown
---
cycle: <N being opened>
date: YYYY-MM-DD
---

# Registry audit — before cycle <N>

## Roster ↔ code drift
- <registry>: <finding, and the roster fix applied> | none

## Enforcement status
- <hook/linter>: pass | FAIL — <what broke>

## Promotion candidates (input to wellspec delta step 2)
- **<candidate>** — seen at <locations>; would join <registry>
```

## Handoff

After routing, this skill's job is done — the entry lens owns the conversation from here. wellnext runs again only when the new cycle completes and the next chunk of work arrives.
