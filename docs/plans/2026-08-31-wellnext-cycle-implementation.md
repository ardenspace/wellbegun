# wellnext Cycle Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the wellbegun pipeline re-enterable — add the fifth skill `wellnext` (registry audit → entry triage → cycle archive/seed) and teach the four lens skills a delta mode, so a completed project can run 2nd, 3rd, n-th development cycles.

**Architecture:** Skills-only plugin, no build step. `wellnext` is a new skill directory; the four existing skills gain a delta-mode branch switched by `cycle: N` frontmatter (N > 1) on the current cycle's artifacts. Cycle state lives on disk: top-level `.wellbegun/*.md` is always the current cycle, `cycles/NN/` is the immutable archive of finished cycles, `decisions.md` never archives (append-only ledger with supersede marks).

**Tech Stack:** Markdown skills, POSIX shell validation (`scripts/validate.sh`).

**Spec:** `docs/2026-08-31-wellnext-cycle-design.md` — every content requirement below cites it. Executors MUST read it in full before implementing any task. (The spec is Korean; skill output is English per repo convention.)

## Global Constraints

- Skill bodies, references, and this plan are written in **English** (public-distribution convention; design docs stay Korean).
- Every SKILL.md frontmatter has `name:` matching its directory and a `description:` that starts with `Use when`.
- Skills must never instruct calling other plugins' planning-stage skills, and must not reference sibling plugins (talpi/loopspace/pslog). `scripts/validate.sh` enforces both.
- Cross-skill disk interface (do not improvise variants):
  - Current cycle: `.wellbegun/begin.md`, `spec.md`, `plan.md`, `run.md`, `decisions.md`, `audit.md`, `pending/`.
  - Archive: `.wellbegun/cycles/NN/` (zero-padded: `01`, `02`, …).
  - Frontmatter keys: `status: draft|approved`, `cycle: <N>`, `entry: begin|spec`, `opened: YYYY-MM-DD`, `closed: YYYY-MM-DD`.
  - **Delta-mode switch:** an artifact whose frontmatter has `cycle: N` with N > 1. A missing `cycle` key means cycle 1 (backward compatibility — existing projects need no migration), and cycle 1 always runs the skills exactly as today.
- Verification command for all tasks: `bash scripts/validate.sh` → exit 0, prints `OK: wellbegun structure valid`.
- Commit after every task with a conventional-commit message ending in the Claude Code trailer.

---

### Task 1: Supersede format and L/XL index in the grades reference

**Files:**
- Modify: `references/reversibility-grades.md` (append after the current last line, line 35)

**Interfaces:**
- Produces: the supersede line format (`supersedes: [YYYY-MM-DD] <slug>` on the new line, ` (superseded YYYY-MM-DD)` appended to the old line) and the `## L/XL index` / `## Ledger (append-only, chronological)` section names. Tasks 2 and 4 reference these by name.

- [ ] **Step 1: Append the supersede and index sections**

Append to `references/reversibility-grades.md`:

```markdown

## Overturning a decision (supersede)

The ledger is append-only: an overturned decision is marked, never deleted — "why we chose otherwise back then" is evidence for the next overturn. Two edits, always together:

- The new line carries `supersedes: [YYYY-MM-DD] <short-slug>` naming the line it replaces.
- The overturned line gets ` (superseded YYYY-MM-DD)` appended at its end.

```
- [2026-08-24] [XL] account model: none — ship without accounts, team choice stays on device (superseded 2026-09-01)
- [2026-09-01] [XL] account model: email + OAuth login — badges and likes need identity across devices; supersedes: [2026-08-24] account-model; rejected: device-only storage (cannot sync or recover)
```

A cycle that overturns an identity decision or a non-goal MUST record the supersede pair, and the current cycle's `begin.md` must state the new decision — the top-level begin.md is always the current answer sheet; the archive is history.

## The L/XL index

To keep rare expensive decisions findable in a growing ledger, `decisions.md` is structured in two sections:

- `## L/XL index` at the top — one line per **currently valid** L/XL decision, pointing at its ledger line by date and slug.
- `## Ledger (append-only, chronological)` below — every line ever recorded, in order, with `## cycle N` subheaders marking cycle boundaries.

Update the index in the same edit whenever an L/XL decision lands or is superseded: a superseded L/XL leaves the index (its replacement enters), so the index never lists dead decisions.
```

- [ ] **Step 2: Verify structure and content**

Run: `bash scripts/validate.sh`
Expected: exit 0, `OK: wellbegun structure valid`

Run: `grep -c "supersedes:" references/reversibility-grades.md`
Expected: `2` or more (format definition + example line)

- [ ] **Step 3: Commit**

```bash
git add references/reversibility-grades.md
git commit -m "feat: supersede format and L/XL index rule in grades reference"
```

---

### Task 2: The wellnext skill

**Files:**
- Create: `skills/wellnext/SKILL.md`

**Interfaces:**
- Consumes: the ledger section structure from Task 1 (`## cycle N` subheaders live under the ledger section).
- Produces: `.wellbegun/audit.md` (template below — its `## Promotion candidates` section is consumed by Task 4's wellspec delta mode), the `cycles/NN/` archive procedure, and the seed frontmatter contract (`cycle`, `entry`, `opened`, `status`) consumed by Tasks 3–5.

- [ ] **Step 1: Write `skills/wellnext/SKILL.md`**

Exact content:

````markdown
---
name: wellnext
description: "Use when a wellbegun project has completed its pipeline (approved plan, finished run) and a new chunk of work arrives — a feature list, a flowchart, an n-th development round. Cycle gate of the wellbegun pipeline: audits the registries, proposes an entry point, archives the finished cycle, and seeds the next one."
---

# wellnext — the cycle gate

Open the next cycle of a completed wellbegun project: audit the global registries against the actual code, propose an entry point by rule, and — only after the user confirms — archive the finished cycle into `cycles/NN/` and seed the new cycle's artifacts. This is the only skill that opens or closes cycles; the four lens skills operate inside whatever cycle is current.

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

Read the new work (feature list, flowchart, request), the current `begin.md` (identity decisions, non-goals), `decisions.md`, and the audit. Test two axes:

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

1. **Archive.** Create `cycles/NN/` (zero-padded, next free number). Stamp `closed: YYYY-MM-DD` into the outgoing `begin.md`'s frontmatter — part of the archival act; archived files are immutable afterward. Move `begin.md`, `spec.md`, `plan.md`, `run.md`, and the previous `audit.md` (if any) into the archive. `decisions.md` stays at top level — append a `## cycle N` subheader to its ledger section so entries read in cycle order. Artifacts with no date frontmatter (cycle-1 projects predate it): backfill `opened`/`closed` from git history at archive time.
2. **Seed.** Write the new cycle's first artifact with frontmatter `cycle: N`, `entry: begin|spec`, `opened: YYYY-MM-DD`. Begin entry → seed `begin.md` with `status: draft` from wellbegin's template, plus an inherited-identity section listing the previous cycle's identity decisions. **Spec entry still gets a begin.md** — a thin one, written here with `status: approved` (the user's entry confirmation is its approval): the full list of identity decisions carried forward (the top-level begin.md is always the current answer sheet) and a summary of this cycle's delta journeys. This keeps wellspec's guard untouched and keeps upstream documents honest.
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
````

- [ ] **Step 2: Verify structure**

Run: `bash scripts/validate.sh`
Expected: exit 0 (the `skills/*/` loop picks up `wellnext` automatically; frontmatter checks must pass)

Run: `grep -c "cycles/NN/" skills/wellnext/SKILL.md`
Expected: `2` or more

- [ ] **Step 3: Commit**

```bash
git add skills/wellnext/SKILL.md
git commit -m "feat: wellnext skill — registry audit, entry triage, cycle open/close"
```

---

### Task 3: wellbegin delta mode

**Files:**
- Modify: `skills/wellbegin/SKILL.md` (description line 3; new section before `## Output template`)

**Interfaces:**
- Consumes: `cycle`/`entry` frontmatter contract from Task 2; supersede rule from Task 1.

- [ ] **Step 1: Update the description**

Replace line 3 of `skills/wellbegin/SKILL.md`:

Old:
```
description: "Use when starting a new wellbegun project or shaping a raw MVP idea — before any spec, plan, or code exists, or when .wellbegun/begin.md is still a draft. First lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
```

New:
```
description: "Use when starting a new wellbegun project or shaping a raw MVP idea, or when a later cycle's delta begin is in draft (begin.md with cycle: N frontmatter, seeded by wellnext). First lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
```

- [ ] **Step 2: Insert the delta-mode section**

Insert immediately before `## Output template` in `skills/wellbegin/SKILL.md`:

```markdown
## Delta mode (cycle: N > 1)

When begin.md's frontmatter carries `cycle: N` with N > 1 (seeded by wellnext), the subject is this cycle's **delta**, not the whole product. Bundle density shifts; nothing else does — probe angles, closing conditions, and the status table apply unchanged.

- **Bundle 1 (whose problem)** — inheritance check: confirm the previous cycle's answer still holds for the new work; reopen fully only if the new work serves a different user or moment.
- **Bundles 2–4 (journey, success criteria, non-goals)** — full density, scoped to the new work. The new journeys' failure branches live here; this is why large-but-identity-safe work still enters at begin.
- **Bundle 5 (product identity)** — list the previous cycle's decisions, then discuss **only the ones this cycle overturns**. Every overturn is recorded per the supersede format in `${CLAUDE_PLUGIN_ROOT}/references/reversibility-grades.md`, and begin.md keeps the **full current list** of identity decisions — the top-level begin.md is always the current answer sheet; nobody should walk the archive to learn the current identity.
- **Bundle 6 (character and tone)** — inherit and confirm; reopen only if the new work changes how the product should feel.
- **Bundle 7 (tech queue)** — unchanged: every tech smell in the delta conversation gets a queue entry.
```

- [ ] **Step 3: Verify**

Run: `bash scripts/validate.sh`
Expected: exit 0

Run: `grep -c "Delta mode" skills/wellbegin/SKILL.md`
Expected: `1`

- [ ] **Step 4: Commit**

```bash
git add skills/wellbegin/SKILL.md
git commit -m "feat: wellbegin delta mode — cycle-scoped bundles, identity answer sheet"
```

---

### Task 4: wellspec delta mode

**Files:**
- Modify: `skills/wellspec/SKILL.md` (Step 1 addition; Step 2 addition; new paragraph after the Guard)

**Interfaces:**
- Consumes: `.wellbegun/audit.md` `## Promotion candidates` section from Task 2; supersede format and L/XL index from Task 1.

- [ ] **Step 1: Add the delta-mode switch after the Guard section**

Insert immediately after the last Guard bullet (`.wellbegun/spec.md missing → …`) in `skills/wellspec/SKILL.md`:

```markdown
**Delta mode:** when begin.md's frontmatter carries `cycle: N` with N > 1, this spec covers the cycle's delta. Copy `cycle: N` into spec.md's frontmatter on creation, and apply the delta branches marked in steps 1–2 below. `.wellbegun/audit.md` (written by wellnext) is an additional input.
```

- [ ] **Step 2: Add the ADR-conflict check to Step 1**

Append to the end of the `## Step 1: Resolve the expensive decision queue` section (after the paragraph beginning "If grading reveals an entry is actually S"):

```markdown
Delta mode only: before recording any resolution, check it against the existing ADRs in `decisions.md`. A conflict is not an error — it is an overturn: record it with the supersede format from `${CLAUDE_PLUGIN_ROOT}/references/reversibility-grades.md` (new line with `supersedes:`, old line marked), and update the `## L/XL index` in the same edit when the decision is L/XL.
```

- [ ] **Step 3: Add the extension-roster branch to Step 2**

Append to the end of the `## Step 2: Define the global registries` section (after the "Timing rule" paragraph):

```markdown
Delta mode only: the registries already exist as code. Read the live rosters and the actual code first, then write **extension rosters only** — what this cycle adds or changes, never a restatement of what exists. Take the `## Promotion candidates` list from `.wellbegun/audit.md` as input: grade each candidate, then either promote it (add to the extension roster; its materialization becomes a plan phase 1 step) or reject it with one line. Unhandled candidates are an unfinished step 2.
```

- [ ] **Step 4: Verify**

Run: `bash scripts/validate.sh`
Expected: exit 0

Run: `grep -c "Delta mode" skills/wellspec/SKILL.md`
Expected: `3`

- [ ] **Step 5: Commit**

```bash
git add skills/wellspec/SKILL.md
git commit -m "feat: wellspec delta mode — extension rosters, promotion candidates, supersede check"
```

---

### Task 5: wellplan and wellrun delta modes

**Files:**
- Modify: `skills/wellplan/SKILL.md` (addition inside `## Phase decomposition`)
- Modify: `skills/wellrun/SKILL.md` (one paragraph in the `## Running state` section)

**Interfaces:**
- Consumes: `cycle: N` frontmatter contract from Task 2.

- [ ] **Step 1: Add the delta-foundation branch to wellplan**

Insert in `skills/wellplan/SKILL.md`, immediately after the numbered list in `## Phase decomposition` (after item 6, before the "Why this order is non-negotiable" paragraph):

```markdown
**Delta mode (spec.md frontmatter `cycle: N`, N > 1):** phase 1 is the **delta foundation** — materialize only what the extension rosters add (new migrations, new tokens, new shared components, new common layers), and update the affected rosters, hooks, and area CLAUDE.md files. Copy `cycle: N` into plan.md's frontmatter. Rewriting an existing, live foundation is **not** a plan step: that is an L/XL decision and belongs in the spec's resolved-decisions table — if it is not there, stop and route back to wellspec.
```

- [ ] **Step 2: Add the per-cycle ledger note to wellrun**

In `skills/wellrun/SKILL.md`, append to the end of the `## Running state — .wellbegun/run.md` section (after the paragraph beginning "One line per step"):

```markdown
run.md belongs to its cycle: created at the cycle's first briefing, archived into `cycles/NN/` by wellnext when the next cycle opens. Probes committed by earlier cycles' verifiers are ordinary tests now — the conductor's regression runs pick them up with the rest of the suite, so each cycle's verification starts on top of all previous cycles' work.
```

- [ ] **Step 3: Verify**

Run: `bash scripts/validate.sh`
Expected: exit 0

Run: `grep -c "Delta mode" skills/wellplan/SKILL.md && grep -c "cycles/NN/" skills/wellrun/SKILL.md`
Expected: `1` and `1`

- [ ] **Step 4: Commit**

```bash
git add skills/wellplan/SKILL.md skills/wellrun/SKILL.md
git commit -m "feat: wellplan delta foundation, wellrun per-cycle ledger"
```

---

### Task 6: README — the cycle story

**Files:**
- Modify: `README.md` (pipeline paragraph in `## How it works`; skills table in `## Skills`; new paragraph after the table)

**Interfaces:**
- Consumes: everything above; no downstream consumers.

- [ ] **Step 1: Add wellnext to the lens list**

In `README.md` `## How it works`, after the `- **Run.**` bullet, add:

```markdown
- **Next (cycle gate).** When a finished project takes on its next chunk of work, `wellnext` reopens the pipeline: it audits the registries against the actual code (drift, enforcement health, duplication worth promoting), proposes an entry point by rule — overturning an identity decision or adding a new user journey means entering at begin; extending existing journeys means entering at spec — and, once you confirm, archives the finished cycle into `cycles/NN/` and seeds the next one. Decisions overturned along the way are superseded in the ledger, never erased.
```

- [ ] **Step 2: Add the skills-table row**

In the `## Skills` table, add after the `wellrun` row:

```markdown
| `wellnext` | Next (cycle gate) | `.wellbegun/audit.md`, `cycles/NN/` archive, seeded next-cycle artifacts |
```

- [ ] **Step 3: Update the state paragraph**

Replace the paragraph below the skills table (beginning "The three pipeline artifacts") with:

```markdown
The three pipeline artifacts (`begin.md`, `spec.md`, `plan.md`) carry `status: draft` → `status: approved` frontmatter, and every skill gates on its predecessor being approved — the pipeline's state lives on disk, not in conversation memory. The run adds `run.md` (step-by-step running state) and the `pending/` mailbox, whose file existence itself means "a decision is owed." The pipeline is re-enterable: top-level `.wellbegun/` files always describe the current cycle, finished cycles live untouched in `cycles/NN/`, and `decisions.md` spans all cycles as an append-only ledger where overturned decisions are marked superseded, never deleted.
```

- [ ] **Step 4: Verify**

Run: `bash scripts/validate.sh`
Expected: exit 0

Run: `grep -c "wellnext" README.md`
Expected: `2` or more

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README — wellnext and the cycle story"
```
