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
