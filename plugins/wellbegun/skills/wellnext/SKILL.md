---
name: wellnext
description: "Use when a wellbegun project has completed its pipeline (approved plan, finished run) and a new chunk of work arrives — a feature list, a flowchart, an n-th development round. Cycle gate of the wellbegun pipeline: audits the registries, proposes an entry point, archives the finished cycle, and seeds the next one."
---

# wellnext — the cycle gate

Open the next cycle of a completed wellbegun project: audit the global registries against the actual code, propose an entry point by rule, and — only after the user confirms — archive the finished cycle into `.wellbegun/cycles/NN/` and seed the new cycle's artifacts. This is the only skill that opens or closes cycles; the four lens skills operate inside whatever cycle is current.

**Core principle:** a new cycle starts on an honest ledger. Between cycles, code drifts away from the rosters (out-of-pipeline work, hotfixes), and planning on top of a lying ledger poisons every later lens — so the drift is settled before any new planning happens.

## Guard

- `.wellbegun/` missing → not a wellbegun project yet; route to wellbegin.
- `.wellbegun/pending/` non-empty → answers are owed; route to wellrun.
- `.wellbegun/plan.md` missing or not `status: approved`, or `run.md` has steps not yet `[x]` → the pipeline is mid-flight; route to the stage the artifacts point to.
- `.wellbegun/plan.md` approved and every `run.md` step verified → this skill applies.

Not every change deserves this gate: bugfixes and small tweaks proceed without wellnext — the installed hooks keep guarding, and the next cycle's audit settles whatever accumulated. wellnext is for chunks of work.

## Step 1: Registry audit

Run before triage — its findings are triage evidence. Write results into `.wellbegun/audit.md` (template below) as they land; disk is the anchor.

1. **Roster ↔ code drift.** For each of the four registries (design tokens, shared components, backend common layers, DB schema), compare the roster against the actual code. Two smells: an element that exists in code but not on the roster (out-of-pipeline addition), and a roster entry whose code is gone or changed shape. Update the rosters to match reality **now**, before any new planning, and commit the fixes as part of the audit — the new cycle must not plan on a lying ledger.
2. **Enforcement status.** Run the installed hooks and linters from the spec's enforcement plan over the **whole codebase** (not per-edit) and record pass/fail per check. Broken or missing enforcement is itself a finding; restoring it becomes a step in the new cycle's plan.
3. **Duplication scan.** Look for shared-shaped patterns repeated two or more times outside the common layer: hardcoded values that mirror a token, copy-pasted widget or handler structure, parallel error handling. Record each as a **promotion candidate** — name, locations, which registry it would join. **wellnext finds, never decides:** grading candidates and extending rosters is the developer lens's job; the candidate list is an input to wellspec's delta step 2.

## Step 2: Entry triage

Read the new work (feature list, flowchart, request), the current `begin.md` (identity decisions, non-goals), `decisions.md`, the outgoing `run.md`'s `## Deferred` section (what the last cycle accepted open), and the audit. Test two axes:

- **Axis 1 — does it overturn?** The new work contradicts an identity decision or a non-goal in the current begin.md.
- **Axis 2 — does it add a journey?** The new work introduces a user journey the current begin.md does not have, large enough to carry its own failure branches.

| Verdict | Condition |
|---|---|
| **begin entry** (delta begin) | either axis fires |
| **spec entry** | neither fires; the work extends existing journeys |
| **no pipeline** | too small for the pipeline — hooks keep guarding; just do the work |

The axes are deliberately not "does it touch identity": the begin lens's value is the user lens itself (journeys, failure branches, probe angles), so a large development with intact identity still enters at begin.

Propose exactly one verdict **with evidence** — which decision would be overturned, which journey is new, how much of the new work the audit shows is already covered by existing registry elements — and ask the user to confirm. Proposal plus confirmation, the same philosophy as wellspec's L/XL review; only the user's confirmation opens a cycle.

## Step 3: Opening procedure (after confirmation)

1. **Archive.** Create `.wellbegun/cycles/NN/` (zero-padded, next free number). Stamp `closed: YYYY-MM-DD` into the outgoing `begin.md`'s frontmatter — part of the archival act; archived files are immutable afterward. Move `begin.md`, `spec.md`, `plan.md`, `run.md`, and the previous `audit.md` (if any) into the archive. `decisions.md` stays at top level — append a `## cycle N` header to the ledger so entries read in cycle order. A legacy flat decisions.md (no index or ledger sections yet) gets restructured into the `## L/XL index` + `## Ledger (append-only, chronological)` form first — content unchanged, lines only move. Artifacts with no date frontmatter (cycle-1 projects predate it): backfill `opened`/`closed` from git history at archive time.
2. **Seed.** Write the new cycle's first artifact with frontmatter `cycle: N`, `entry: begin|spec`, `opened: YYYY-MM-DD`. Begin entry → seed `begin.md` with `status: draft` from wellbegin's template, plus an inherited-identity section listing the previous cycle's identity decisions. **Spec entry still gets a begin.md** — a thin one, written here with `status: approved` (the user's entry confirmation is its approval): the full list of identity decisions carried forward (the top-level begin.md is always the current answer sheet), a summary of this cycle's delta journeys, and an empty expensive-decision queue (spec entry means no product-lens conversation ran to fill it; discoveries during the run still follow wellrun's hidden-decision rule). This keeps wellspec's guard untouched and keeps upstream documents honest.
3. **Route.** Invoke the confirmed entry lens — wellbegin for begin entry, wellspec for spec entry. On a **no pipeline** verdict, nothing is archived and nothing is seeded: tell the user the hooks keep guarding, and stop.

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
