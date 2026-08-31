# Reversibility grades (S/M/L/XL)

The grading question is always the same: **"If this decision turns out wrong, what does it cost to change?"**

Grade by **reversal cost, not importance**. An important decision that takes five minutes to flip is still S. A boring decision that would force a data migration is L no matter how dull it looks.

## The four grades

| Grade | Reversal cost | Typical examples | How to handle it |
|---|---|---|---|
| **S** | Minutes, inside one file; nobody else notices. | Variable naming, internal helper structure, copy text, a private function's shape. | Implementer decides on the spot. At spec stage: goes to implementer discretion, no record. Mid-run: record one line in `.wellbegun/decisions.md`, like M. |
| **M** | Under a day; touches a few files; no data or API migration. | A component's internal state shape, a response field on a non-shared endpoint, a config default. | Decide, record one line in `.wellbegun/decisions.md`, keep moving. |
| **L** | A mini-project: data backfill, cross-cutting rename, coordinated changes across layers. | DB schema for a core entity, a shared component's API, the error-format contract. | Spec: mandatory alternative comparison. Run: fresh-eyes verification; discovering one mid-implementation stops the run (companion mode). |
| **XL** | A rewrite, or a break users can see. | Account model, multi-tenancy, pricing unit, platform choice, data ownership. | Same as L — and when the decision is product-shaped, it belongs in wellbegin (product identity), not in the spec queue. |

## Grade fast

Grading a decision should take under a minute. It is a sorting gesture, not an analysis. If you are torn between two grades, take the higher one — the cost of over-verifying an M is minutes; the cost of under-verifying an L is the mini-project.

## Mini-ADR line format

Every recorded decision, anywhere in the pipeline, uses the same one-line format in `.wellbegun/decisions.md`:

```
- [YYYY-MM-DD] [grade] <decision> — <why, one clause>; rejected: <alternative, if L/XL>
```

Examples:

```
- [2026-08-24] [M] store timestamps as UTC ISO strings — simplest thing that sorts correctly
- [2026-08-24] [L] single-tenant schema with tenant_id column reserved — cheapest path that keeps the multi-tenant door open; rejected: schema-per-tenant (operational cost too high for MVP)
```

The `rejected:` clause is required for L/XL (the spec lens compares alternatives at those grades) and omitted for S/M.

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
- `## Ledger (append-only, chronological)` below — every line ever recorded, in order, with `## cycle N` headers marking cycle boundaries.

Update the index in the same edit whenever an L/XL decision lands or is superseded: a superseded L/XL leaves the index (its replacement enters), so the index never lists dead decisions.
