---
name: wellspec
description: "Use when .wellbegun/begin.md has status: approved and no approved spec exists yet, or when .wellbegun/spec.md is still a draft. Developer lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---

# wellspec — the developer lens

Translate the approved begin document into the solution space: resolve the expensive-decision queue with reversal-cost grades, define the global registries as markdown rosters, and — just as deliberately — leave the cheap decisions blank. The output is `.wellbegun/spec.md`.

**Core principle:** effort is proportional to reversal cost. A spec that is dense everywhere is as wrong as a spec that is thin everywhere. Dense at the one-way doors, silent at the two-way doors — that asymmetry *is* the spec.

## Guard

- `.wellbegun/begin.md` missing or not `status: approved` → stop and route to wellbegin.
- `.wellbegun/spec.md` with `status: approved` → route to wellplan.
- `.wellbegun/spec.md` with `status: draft` → resume where the draft stops. If the draft marks a question as `open — asked user`, re-ask it before doing anything else: an interruption never converts a user question into an agent decision.
- `.wellbegun/spec.md` missing → this skill applies: write `spec.md` from the output template with `status: draft` **now**, before step 1, and fill it in as the steps run — disk is the anchor.

## Step 1: Resolve the expensive decision queue

For every entry in begin.md's queue:

1. Grade it with `${CLAUDE_PLUGIN_ROOT}/references/reversibility-grades.md` (S/M/L/XL — by reversal cost, not importance).
2. Decide it, and record a mini-ADR in `.wellbegun/decisions.md` — one line per the mini-ADR line format in that same reference (the format already carries decision, why, and the rejected alternative for L/XL).
3. **L/XL entries require at least two compared alternatives** before deciding. S/M entries take one minute and one line.

Who decides: the agent proposes, records, and moves on — the user reviews every L/XL choice (with its rejected alternative) at Handoff before approving. Until that approval, every recorded L/XL line is a **proposal**, however confident its wording in `decisions.md` looks. Two exceptions that go to the user immediately, not at Handoff: an entry that turns out *product-shaped* (pricing, account model, data ownership — it escaped wellbegin's bundle 5), and an XL where the compared alternatives are genuinely close. When an exception puts a question to the user, mark that queue entry `open — asked user` in the draft spec; only the user's answer closes it (see Guard — an interrupted session must re-ask, never self-answer).

If grading reveals an entry is actually S — it happens — say so and move it to the `## Implementer discretion` section (step 3). It gets **no row** in the Resolved decisions table and no ADR line; the table holds M and above. The queue coming in expensive does not oblige you to treat it as expensive.

## Step 2: Define the global registries

Instantiate the four templates from `${CLAUDE_PLUGIN_ROOT}/references/registry-templates/` as **markdown rosters only**:

- **Design tokens** — translate bundle 6's product character into named tokens with concrete values (this is where "warm, like Linear" becomes `color.accent: #...`).
- **Shared components** — the minimal named set the core journey needs.
- **Backend common layers** — error envelope, auth, logging (and pagination if lists exist).
- **DB schema** — entities and ownership sketch.

Timing rule: rosters only. The real files (token file, component stubs, migrations) are created in wellplan's phase 1, after the stack is fixed. A spec that writes code has jumped its lens.

## Step 3: Leave cheap decisions blank

Add an explicit `## Implementer discretion` section listing what is *deliberately* unspecified — internal state shapes, helper structure, non-shared endpoint details, copy tone. This section is the plugin's signature, not an omission: it tells the run's implementers where they are free, so they neither wait for permission nor invent constraints.

## Step 4: Enforcement plan

Decide which checks from `${CLAUDE_PLUGIN_ROOT}/references/hooks/` apply and where they will be wired (PostToolUse hook, pre-commit, or both — see that folder's README). Write the choices down here; **installation itself becomes a phase 1 step in wellplan**, not an action taken now.

## Output template

`.wellbegun/spec.md`:

```markdown
---
status: draft
---

# <project> — spec

## Resolved decisions
<!-- one row per queue entry resolved at grade M or above; S-downgrades go to Implementer discretion instead -->
| decision | grade | choice | ADR |
|---|---|---|---|
| <question> | L | <choice> | see decisions.md 2026-08-24 |

## Registries
### Design tokens
### Shared components
### Backend common layers
### DB schema

## Implementer discretion
- <deliberately unspecified area>

## Enforcement plan
- <check> wired as <PostToolUse / pre-commit / both>, adapted how
```

## Handoff

Show the user the finished spec, then confirm the L/XL choices **one at a time, each as a choice question** — proposed choice vs. rejected alternative, with the one-clause why for each. These are the doors that cannot be cheaply reopened; a table the user scrolls past is not a review. Do not present them as a batch-approval document, and do not use closed-verdict wording ("decided", "rejected") for anything the user has not yet confirmed — the `rejected:` clause in the ADR line is a comparison record, not a verdict. M-and-below stay in the table for passive review; they need no per-item question.

If an answer overturns a proposal, update the spec table and the ADR line before moving on. Only after every L/XL is confirmed, flip to `status: approved` and invoke **wellplan**.
