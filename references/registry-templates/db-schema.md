# DB schema registry

> **Rule: schema changes always ride a migration, never a hand edit.** The migrations folder is the source of truth; this roster maps entities to their owners and migrations so nobody re-derives the schema by reading table dumps.

**Migrations folder:** `<path — e.g. migrations/>`

| entity | purpose (one line) | defined in (migration) | ownership notes |
|---|---|---|---|
| `users` | Account root | `<migration file>` | Owned by auth slice; other slices reference, never alter |
| `<entity>` | | | |

<!-- One row per entity. "Ownership notes" says which feature slice may alter it — schema is L/XL territory, so changes outside the owner stop the run. -->
