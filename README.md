# wellbegun

> **Well begun is half done.** — 시작이 반이다.

A dual Claude Code and Codex plugin that plans MVPs around one question: **how hard is this decision to change later?**

## The problem

Shipping an MVP is the easy part. What eats your time is everything after: maintenance, debugging, and untangling decisions that hardened before anyone noticed they were decisions. A database schema, a hardcoded color scattered across forty files, a modal that ignores the shared component — each was cheap to get right at the start and is expensive to fix now.

You can't ship a perfect MVP, and you shouldn't try. But decisions are not equally reversible. Some are two-way doors you can walk back through for free; some are one-way doors that cost a rewrite. wellbegun spends your attention on the one-way doors and deliberately rushes past everything else.

## How it works

Four lenses and a cycle gate, one pipeline — begin → spec → plan → run, then next between cycles:

- **Begin (user lens).** Shapes the MVP in user language: whose problem, one core journey, success criteria, explicit non-goals. Expensive *product* decisions (account model, multi-tenancy, pricing unit) get decided here; expensive *technical* decisions get flagged and queued — not solved.
- **Spec (developer lens).** Resolves the queued decisions with a reversal-cost grade (S/M/L/XL) and a short rationale. Defines the global registries: design tokens, shared components, backend common layers, schema. Cheap decisions are deliberately left blank — marked "implementer's discretion."
- **Plan.** Create only needed foundations and active registries. Every step gets a contract before implementation, with completion clauses, checks and explicit dependencies. New shared foundations have an independent gate before consumers.
- **Run.** Basic work runs directly and reuses an implementer within a verified boundary. Fresh reviews use independent contexts with contracts, code and valid check facts. Failed gates, unanswered questions and unresolved round caps block dependent work.
- **Next (cycle gate).** Triage the request first: small fixes proceed directly; larger work gets an affected-area audit and the appropriate begin/spec entry. Reuse existing authorization to archive completed work and seed the next cycle. Supersede overturned decisions without erasing them.

Composable by design: wellbegun owns the pipeline but delegates implementation techniques to whatever your environment provides (e.g. Superpowers' TDD and debugging skills).

## Install

Claude Code:

```text
/plugin marketplace add ardenspace/wellbegun
/plugin install wellbegun@wellbegun
```

Codex:

```bash
codex plugin marketplace add ardenspace/wellbegun
codex plugin add wellbegun@wellbegun
```

Both installations load the same five skills from `plugins/wellbegun/`; host-specific manifests and instruction-file conventions are kept at the edges.

## Skills

| skill | lens | artifact it produces |
|---|---|---|
| `wellbegin` | Begin (user) | `.wellbegun/begin.md` + expensive decision queue |
| `wellspec` | Spec (developer) | `.wellbegun/spec.md` + `.wellbegun/decisions.md` |
| `wellplan` | Plan | `.wellbegun/plan.md` with step contracts |
| `wellrun` | Run | executed steps, ADR entries, `.wellbegun/pending/` stops |
| `wellnext` | Next (cycle gate) | `.wellbegun/audit.md`, `cycles/NN/` archive, seeded next-cycle artifacts |

The three pipeline artifacts (`begin.md`, `spec.md`, `plan.md`) carry `status: draft` → `status: approved` frontmatter. Reentry reuses stored approval and mode. New runs store progress in `state.json` and unanswered questions in `pending/`; legacy runs retain `run.md` as their progress authority. Top-level artifacts describe the current cycle, completed cycles live under `cycles/<cycle>/` (legacy: `cycles/NN/`), and project decisions/indexes span cycles with superseded records preserved.

## Status

Lean runtime and skill integration passed independent foundation and final review,
with 88 runtime/lifecycle tests and bounded fixed-copy comparisons. The matched
step observations show lower document inputs and fewer model roles; fixed order,
caches and evidence reuse prevent a general execution-time or cost claim.
Seven broader Flutter failures on baseline-identical dogfood code remain reported
separately from the passing workload checks. See the
[validation record](docs/2026-09-12-lean-execution-validation.md) for scope and results.

New cycles use a standard-library Python 3.9+ helper with five commands:
`validate`, `context`, `decision-get`, `transition`, and `render`.
`state.json` schema 2 is authoritative; run.md and optional HANDOFF are derived.
Context selects current contracts/decisions/registry constraints, with a 12KB
default ceiling and explicit overflow sections. `--remember` avoids repeated
same-context bodies and manual receipt copying. Basic completion is one result
write. Archive preserves cycle state, evidence and plan together; project
decisions remain available. Call the installed helper by absolute path with an
absolute project `.wellbegun` root, from any working directory.

Legacy cycles retain their format while using selective decision lookup; only a
new cycle initializes schema 2. Without Python, use explicit manual/legacy
operation, without claims of automated validation or bounded extraction; an
existing schema 2 state needs a Python-capable session to resume. Git and hooks
are optional. No-subagent hosts support basic work; fresh boundaries wait for
an independent session. The helper trusts reported check commands/environment
and declared input files; it is not a sandbox or semantic dependency analyzer.

Run `bash scripts/validate.sh` for structural checks and one runtime unittest
discovery. See [selected-input guidance](plugins/wellbegun/references/selected-inputs.md)
and the [runtime contract](plugins/wellbegun/references/runtime-contract.md) for
command payloads and recovery details.

## License

MIT
