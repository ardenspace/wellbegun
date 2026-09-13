---
name: wellplan
description: "Use when .wellbegun/spec.md has status: approved and no approved plan exists yet, or when .wellbegun/plan.md is still a draft. Third lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---

# wellplan — foundation-first planning

Turn the approved spec into a phase > step structure where every step carries a contract written **before any implementation exists**. The output is `.wellbegun/plan.md`. This lens **is** the plan-writing stage of the pipeline: if the environment carries other plugins' plan-writing skills, do not invoke them while this skill is active — double-running a stage corrupts it.

## Host and shared resources

Resolve `<plugin-root>` once before reading a bundled resource. In Claude Code it is `${CLAUDE_PLUGIN_ROOT}`. In Codex it is the directory two levels above the directory containing this `SKILL.md`. Use the active host's project instruction file: `CLAUDE.md` in Claude Code and `AGENTS.md` in Codex. Never create the other host's file unless the project already supports both hosts.

**Core principle:** materialize the hard-to-reverse foundations first, while changing them is still cheap. Every later step then starts in a world where the shared thing already exists — and reusing it is easier than hardcoding around it.

## Guard

Use `<plugin-root>/references/selected-inputs.md` for bootstrap, selective inputs
and generated host-instruction guidance (reuse it if already read).

First reconcile explicit session approval with artifact status; update a stale draft flag for that approved scope instead of restarting planning.

- `.wellbegun/spec.md` missing or not `status: approved` → stop and route to wellspec.
- `.wellbegun/plan.md` with `status: approved` → route to wellrun.
- `.wellbegun/plan.md` with `status: draft` → resume.
- `.wellbegun/plan.md` missing → this skill applies: write `plan.md` from the output template with `status: draft` **now**, before decomposing, and fill it in as you go — disk is the anchor.

## Phase decomposition

Create a foundation phase only when the spec calls for actual foundation changes. Materialize planned shared APIs, data structures or tokens before their consumers. Reuse existing code, schemas and enforcement; instantiate only active registries and necessary checks. A CLI or library does not acquire UI registries. Preserve user-owned host instructions and add only relevant entry-reading guidance, without copying decision history.

For delta cycles (`cycle: N`, N > 1), carry the cycle into the plan and plan only additions or changes. An expensive foundation change must be covered by the approved spec; surface a genuinely new decision rather than recreating the existing foundation.

Group remaining work into vertical slices with observable outcomes. Mark each new foundation's producer and consumers, and place an independent gate before its first consumer. L/XL producer verification can satisfy that gate. Phase integration can also satisfy it when it precedes the first consumer and covers the same conditions. Independent color or name edits do not need a propagation gate.

## Step sizing and contract

A step delivers one observable outcome with completion conditions. It is not defined by one agent call, context window or widget; helper and widget edits inside its scope are subtasks. Define the contract before implementation, while allowing new probes or useful test additions during implementation.

For a new cycle with Python, write each contract once in the extractable format
below, inside the human-readable plan. Do not duplicate it as a prose contract.
Keep stable IDs and `scope_id` through renames. Read only “Plan and selected
inputs” in `<plugin-root>/references/runtime-contract.md` when authoring this
format. Existing in-progress legacy plans keep their original format.

```markdown
<!-- wellbegun:contract step-1.1 -->
{"id":"step-1.1","kind":"step","scope_id":"scope-1.1",
 "goal":"Deliver the first observable behavior",
 "completion":[{"id":"works","text":"The specified behavior holds"}],
 "verification":["python3 check.py"],"decisions":[],"registry":[],
 "discretion":"Local implementation details","requires":[],"grade":"basic"}
<!-- /wellbegun:contract -->
```

Replace sample behavior/commands with real completion clauses. Put records in
execution order; use `requires` for prerequisites and `decisions`/`registry`
for stable keys, never copied history. Gate records use `kind:gate`, `grade:fresh`,
and nonempty `producers`/`consumers` arrays; consumers require the gate. Phase and
whole-run records use `kind:phase|whole-run`, fresh, their actual prerequisites,
and explicit composition/release clauses. The bundled `tests/fixtures/plan.md`
is a complete producer/gate/consumer example, not mandatory project scaffolding.

Derive `grade` from the reversal cost of decisions introduced or changed in this step: L/XL → fresh; S/M → basic. Merely using an existing L API is not an L change. An S/M producer at a new propagation boundary still requires an independent gate before consumers. Basic requires contract and affected checks, without a separate verifier. Check breadth follows impact separately from reversal grade.

Commands must be available from previous work or created by this step, never depend on a later step. Observable UI checks are valid; do not split a coherent step just because a visual condition has no exit code. Specify phase integration and whole-run acceptance conditions too. Reuse valid results across step/gate/phase/final review rather than assigning the same full suite to every reviewer. See `<plugin-root>/references/reversibility-grades.md` for decision and verification policy.

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
| 1 | <needed foundation or first journey slice> | 1.1–1.n |
| 2 | <journey slice> | 2.1–2.n |

## Step contracts
<contract per step, with explicit dependencies and propagation gates>

## Integration and release criteria
<phase composition and whole-run completion conditions>

## Run preview
<!-- steps whose tier is fresh, or that introduce/change L/XL decisions — wellrun shows this at briefing as "where the run may stop" -->
| step | tier | touches |
|---|---|---|
```

## Handoff

Show the concrete plan and likely decision stops. Reuse approval already given for this scope; ask only for approval still missing or materially changed scope. Once approved, set `status: approved` and invoke **wellrun**.

New-cycle state initialization in wellrun validates IDs, dependency order and
gate placement before any implementation. Keep begin/spec artifacts in their
existing formats; no whole-project migration is needed.
