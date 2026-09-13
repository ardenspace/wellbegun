# DB schema registry

> **Follow the project’s schema-change contract.** For persisted data needing migration, migrations are the source of truth. Use a roster only for ownership or constraints not already expressed by the schema.

**Migrations folder:** `<path — e.g. migrations/>`

| entity | purpose (one line) | defined in (migration) | ownership notes |
|---|---|---|---|
| `users` | Account root | `<migration file>` | Owned by auth slice; other slices reference, never alter |
| `<entity>` | | | |

<!-- One row per entity. "Ownership notes" says which feature slice may alter it — grade the particular schema decision being changed; ordinary use of an existing schema does not trigger L/XL verification. -->

<!-- Active areas only. Retain public contracts, required current constraints and stable decision keys here; link detailed rationale/history without duplicating it. -->
