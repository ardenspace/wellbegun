# Shared component registry

> **Rule: if it renders in two places, it lives here first.** Before building UI, scan this roster. On the roster → reuse it. Not on it but shared-shaped → create it in the shared folder and add the row **in the same commit**.

**Shared component folder:** `<path — e.g. src/components/shared/>`

| name | purpose (one line) | location | use when |
|---|---|---|---|
| `Button` | The only button | `<folder>/Button.tsx` | Any clickable action |
| `Modal` | The only overlay dialog | `<folder>/Modal.tsx` | Any blocking interaction |

<!-- Seed with the minimal set wellspec names; grow one row per new shared component. -->
