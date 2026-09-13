---
name: wellspec
description: "Use when .wellbegun/begin.md has status: approved and no approved spec exists yet, or when .wellbegun/spec.md is still a draft. Developer lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---

# wellspec — the developer lens

Translate the approved begin document into the solution space: resolve the expensive-decision queue with reversal-cost grades, identify relevant shared contracts and registries, and — just as deliberately — leave the cheap decisions blank. The output is `.wellbegun/spec.md`.

**Core principle:** effort is proportional to reversal cost. A spec that is dense everywhere is as wrong as a spec that is thin everywhere. Dense at the one-way doors, silent at the two-way doors — that asymmetry *is* the spec.

## Shared resources

Resolve `<plugin-root>` once before reading a bundled resource. In Claude Code it is `${CLAUDE_PLUGIN_ROOT}`. In Codex it is the directory two levels above the directory containing this `SKILL.md`. Never resolve bundled resources relative to the user's project directory.

## Guard

Use `<plugin-root>/references/selected-inputs.md` for bootstrap and selective
decision/registry lookup (reuse it if already read in this context).

First reconcile explicit session approval with artifact status; update a stale draft flag for that approved scope instead of restarting planning.

- `.wellbegun/begin.md` missing or not `status: approved` → stop and route to wellbegin.
- `.wellbegun/spec.md` with `status: approved` → route to wellplan.
- `.wellbegun/spec.md` with `status: draft` → resume where the draft stops. If the draft marks a question as `open — asked user`, re-ask it before doing anything else: an interruption never converts a user question into an agent decision.
- `.wellbegun/spec.md` missing → this skill applies: write `spec.md` from the output template with `status: draft` **now**, before step 1, and fill it in as the steps run — disk is the anchor.

**Delta mode:** when begin.md's frontmatter carries `cycle: N` with N > 1, this spec covers the cycle's delta. Copy `cycle: N` into spec.md's frontmatter on creation, and apply the delta branches marked in steps 1–2 below. `.wellbegun/audit.md` (written by wellnext) is an additional input.

## Step 1: Resolve the expensive decision queue

For every entry in begin.md's queue:

1. Grade it with `<plugin-root>/references/reversibility-grades.md` (S/M/L/XL — by reversal cost, not importance).
2. Decide it within existing authority. Record meaningful M and all L/XL with stable key, immutable record ID, status and current constraints per that reference; keep long rationale behind source pointers.
3. **L/XL entries require at least two compared alternatives** before deciding. S needs no ADR; M is recorded only when future work needs the choice.

Who decides: the agent proposes, records, and moves on — the user reviews every L/XL choice (with its rejected alternative) at Handoff before approving. Reuse L/XL approvals already given; until approval, every new L/XL record is a **proposal**, however confident its wording in `decisions.md` looks. Two exceptions that go to the user immediately, not at Handoff: an entry that turns out *product-shaped* (pricing, account model, data ownership — it escaped wellbegin's bundle 5), and an XL where the compared alternatives are genuinely close. When an exception puts a question to the user, mark that queue entry `open — asked user` in the draft spec; only the user's answer closes it (see Guard — an interrupted session must re-ask, never self-answer).

If grading reveals an entry is actually S — it happens — say so and move it to the `## Implementer discretion` section (step 3). It gets **no row** in the Resolved decisions table and no ADR line; the table holds meaningful M and L/XL. The queue coming in expensive does not oblige you to treat it as expensive.

Delta mode only: before recording any resolution, look up only related active decisions and required constraints in `decisions.md`. A conflict is not an error — it is an overturn: record it with the supersede format from `<plugin-root>/references/reversibility-grades.md` (new immutable ID with `supersedes: <old-ID>`, old record marked), and update the active key pointer when the replacement is approved.

## Step 2: Select relevant registries

Mark each applicable area `active | N/A`: design tokens, shared components, backend common layers and DB schema. Use only needed templates from `<plugin-root>/references/registry-templates/`. A CLI needs no UI registry; existing code, types, schema and lint may already express the contract without duplicate markdown.

For active areas, record reuse locations, public contracts, mandatory current constraints and decision keys. Keep rationale and history behind exact source pointers. Materialization is planned only for necessary new foundations. Elements explicitly planned as shared are shared from first use; otherwise first use stays local and the second actual use prompts assessment, not automatic abstraction.

In delta mode, inspect only affected live entries and code; write additions or changed contracts, not a restatement. Assess relevant audit promotion candidates for real reuse and benefit. Similar shapes alone are insufficient.

## Step 3: Leave cheap decisions blank

Add an explicit `## Implementer discretion` section listing what is *deliberately* unspecified — internal state shapes, helper structure, non-shared endpoint details, copy tone. This section is the plugin's signature, not an omission: it tells the run's implementers where they are free, so they neither wait for permission nor invent constraints.

## Step 4: Enforcement plan

Decide which checks from `<plugin-root>/references/hooks/` apply and where they will be wired (the active host's editing-time hook when available, pre-commit, or both — see that folder's README). Write the choices down here; reuse existing effective checks; install a missing applicable check in the plan only when needed, not an action taken now.

## Output template

`.wellbegun/spec.md`:

```markdown
---
status: draft
---

# <project> — spec

## Resolved decisions
<!-- meaningful M and L/XL only; S and ordinary local choices go to discretion -->
| decision | grade | choice | ADR |
|---|---|---|---|
| <question> | L | <choice> | <stable decision key> |

## Registries
<active/N/A areas and only required entries or source pointers>

## Implementer discretion
- <deliberately unspecified area>

## Enforcement plan
- <check> wired as <host editing-time hook / pre-commit / both>, adapted how
```

## Handoff

Show the user the finished spec, then confirm only L/XL choices that still lack approval, using the concrete alternatives — proposed choice vs. rejected alternative, with the one-clause why for each. These are the doors that cannot be cheaply reopened; a table the user scrolls past is not a review. Respect an existing explicit approval of the concrete document; do not re-ask settled decisions. Do not use closed-verdict wording ("decided", "rejected") for anything the user has not yet confirmed — the alternatives in the decision record is a comparison record, not a verdict. M-and-below stay in the table for passive review; they need no per-item question.

If an answer overturns a proposal, update the spec table and decision record before moving on. Only after every new L/XL choice has the required approval, flip to `status: approved` and invoke **wellplan**.
