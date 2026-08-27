---
name: wellplan
description: "Use when .wellbegun/spec.md has status: approved and no approved plan exists yet, or when .wellbegun/plan.md is still a draft. Third lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---

# wellplan — foundation-first planning

Turn the approved spec into a phase > step structure where every step carries a contract written **before any implementation exists**. The output is `.wellbegun/plan.md`. This lens **is** the plan-writing stage of the pipeline: if the environment carries other plugins' plan-writing skills, do not invoke them while this skill is active — double-running a stage corrupts it.

**Core principle:** materialize the hard-to-reverse foundations first, while changing them is still cheap. Every later step then starts in a world where the shared thing already exists — and reusing it is easier than hardcoding around it.

## Guard

- `.wellbegun/spec.md` missing or not `status: approved` → stop and route to wellspec.
- `.wellbegun/plan.md` with `status: approved` → route to wellrun.
- `.wellbegun/plan.md` with `status: draft` → resume.
- `.wellbegun/plan.md` missing → this skill applies: write `plan.md` from the output template with `status: draft` **now**, before decomposing, and fill it in as you go — disk is the anchor.

## Phase decomposition

**Phase 1 is fixed — the foundation phase.** It turns the spec's markdown rosters into real code, plus installs the enforcement:

1. DB schema → actual migrations
2. Design tokens → the actual token file
3. Shared components → the minimal set, as real (even if skeletal) components
4. Backend common layers → error envelope, auth, logging in code
5. Enforcement hooks from the spec's enforcement plan → installed and passing (adapt `${CLAUDE_PLUGIN_ROOT}/references/hooks/` scripts to the stack chosen here)
6. Read-first enforcement → each area's registry roster placed next to its code, and that area's CLAUDE.md created (or extended) to say "read the roster before working here" — this is what makes wellrun's rule 2 machine-backed instead of hoped-for

Why this order is non-negotiable: expensive decisions are cheapest to fix before code piles on top of them, and once the foundations exist, every subsequent step begins as "reuse the existing common element" instead of "improvise and clean up later."

**Phase 2 and onward** stack features on that foundation as **vertical slices** — each phase delivers a walkable piece of the core journey from begin.md, end to end.

## Step sizing

A step is: **one subagent, one context window, machine-checkable completion.** If you cannot say what command proves the step done, or you doubt it fits one context, split it.

## The step contract (six items — all required)

```markdown
### Step <phase>.<n>: <name>
1. **Goal:** <one line>
2. **Acceptance criteria:** <observable sentences — things a verifier can watch or run>
3. **Boundary tests:** <executable commands with expected exit codes, fixed NOW, before implementation; the verifier will run exactly these>
4. **Registries to read:** <which area rosters this step must read first>
5. **Verification tier:** fresh | basic
6. **Discretion scope:** <the spec's discretion items that apply to this step>
```

Item 5 is **derived, not chosen**: take the highest reversibility grade among the decisions this step touches — L/XL → `fresh` (context-isolated verifier subagent), S/M → `basic` (lint + boundary tests). Phase 1 steps touch L/XL foundations almost by definition; expect `fresh` there.

Item 3 exists because of timing: acceptance tests written *after* implementation inherit the implementation's blind spots. The plan is the last moment the tests can be honest.

Item 3's form matters as much as its timing: each test is an executable command with an expected exit code (`flutter analyze` → exit 0, `bash scripts/hooks/check-envelope.sh missing-field.json` → exit 2). Prose tests get translated into commands at dispatch time, and translation is where interpretation leaks into an otherwise isolated verifier. A test that can't be written as a command is the step-sizing signal in disguise: the step isn't machine-checkable yet — split or re-specify it.

Item 3 self-check, per step: every file or command the boundary tests reference must be created by an earlier step or by the step itself — a test that presumes a later step's output cannot run when its turn comes.

## Output template

`.wellbegun/plan.md`:

```markdown
---
status: draft
---

# <project> — plan

## Phases
| phase | delivers | steps |
|---|---|---|
| 1 | foundations + enforcement | 1.1–1.n |
| 2 | <journey slice> | 2.1–2.n |

## Step contracts
<six-item contract per step, as above>

## Run preview
<!-- steps whose tier is fresh, or that touch L/XL decisions — wellrun shows this at briefing as "where the run may stop" -->
| step | tier | touches |
|---|---|---|
```

## Handoff

Show the user the plan; point at the run-preview table so they know where stops are likely. On approval, flip to `status: approved` and invoke **wellrun**.
