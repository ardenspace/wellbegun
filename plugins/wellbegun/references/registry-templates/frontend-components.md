# Shared component registry

> **Reuse the applicable public contract.** Read relevant entries before UI work. Planned shared elements are common from first use; otherwise start local and assess promotion on the second actual use. Similar visuals alone do not require abstraction. Update the entry when its contract changes.

**Shared component folder:** `<path — e.g. src/components/shared/>`

| name | purpose (one line) | location | use when |
|---|---|---|---|
| `Button` | Canonical action button | `<folder>/Button.tsx` | Any clickable action |
| `Modal` | Canonical overlay dialog | `<folder>/Modal.tsx` | Any blocking interaction |

<!-- Seed with the minimal set wellspec names; grow one row per new shared component. -->

<!-- Active areas only. Retain public contracts, required current constraints and stable decision keys here; link detailed rationale/history without duplicating it. -->
