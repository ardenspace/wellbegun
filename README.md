# wellbegun

> **Well begun is half done.** — 시작이 반이다.

A skill set for coding agents that plans MVPs around one question: **how hard is this decision to change later?**

## The problem

Shipping an MVP is the easy part. What eats your time is everything after: maintenance, debugging, and untangling decisions that hardened before anyone noticed they were decisions. A database schema, a hardcoded color scattered across forty files, a modal that ignores the shared component — each was cheap to get right at the start and is expensive to fix now.

You can't ship a perfect MVP, and you shouldn't try. But decisions are not equally reversible. Some are two-way doors you can walk back through for free; some are one-way doors that cost a rewrite. wellbegun spends your attention on the one-way doors and deliberately rushes past everything else.

## How it works

Four lenses, one pipeline — begin → spec → plan → run:

- **Begin (user lens).** Shapes the MVP in user language: whose problem, one core journey, success criteria, explicit non-goals. Expensive *product* decisions (account model, multi-tenancy, pricing unit) get decided here; expensive *technical* decisions get flagged and queued — not solved.
- **Spec (developer lens).** Resolves the queued decisions with a reversal-cost grade (S/M/L/XL) and a short rationale. Defines the global registries: design tokens, shared components, backend common layers, schema. Cheap decisions are deliberately left blank — marked "implementer's discretion."
- **Plan.** Foundation first: phase 1 turns the registries into real code while changing them is still cheap. Every step gets a contract written *before* implementation exists — acceptance criteria, boundary tests, verification tier.
- **Run.** Subagent-driven execution with fresh-eyes verification: verifiers get the contract and the diff, never the implementer's narrative — blind spots travel through shared context, so the context is what gets isolated. Verification intensity scales with reversal cost. Registry rules are enforced by hooks and linters, not by hoping the model remembers.
- **Next (cycle gate).** When a finished project takes on its next chunk of work, `wellnext` reopens the pipeline: it audits the registries against the actual code (drift, enforcement health, duplication worth promoting), proposes an entry point by rule — overturning an identity decision or adding a new user journey means entering at begin; extending existing journeys means entering at spec — and, once you confirm, archives the finished cycle into `cycles/NN/` and seeds the next one. Decisions overturned along the way are superseded in the ledger, never erased.

Composable by design: wellbegun owns the pipeline but delegates implementation techniques to whatever your environment provides (e.g. Superpowers' TDD and debugging skills).

## Install

In Claude Code:

```
/plugin marketplace add ardenspace/wellbegun
/plugin install wellbegun@wellbegun
```

## Skills

| skill | lens | artifact it produces |
|---|---|---|
| `wellbegin` | Begin (user) | `.wellbegun/begin.md` + expensive decision queue |
| `wellspec` | Spec (developer) | `.wellbegun/spec.md` + `.wellbegun/decisions.md` |
| `wellplan` | Plan | `.wellbegun/plan.md` with step contracts |
| `wellrun` | Run | executed steps, ADR entries, `.wellbegun/pending/` stops |
| `wellnext` | Next (cycle gate) | `.wellbegun/audit.md`, `cycles/NN/` archive, seeded next-cycle artifacts |

The three pipeline artifacts (`begin.md`, `spec.md`, `plan.md`) carry `status: draft` → `status: approved` frontmatter, and every skill gates on its predecessor being approved — the pipeline's state lives on disk, not in conversation memory. The run adds `run.md` (step-by-step running state) and the `pending/` mailbox, whose file existence itself means "a decision is owed." The pipeline is re-enterable: top-level `.wellbegun/` files always describe the current cycle, finished cycles live untouched in `cycles/NN/`, and `decisions.md` spans all cycles as an append-only ledger where overturned decisions are marked superseded, never deleted.

## Status

Implemented; dogfooding on a real project is next. The full design document lives in [`docs/`](docs/) (Korean).

## License

MIT
